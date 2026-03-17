"""
bot.py - Core Deriv trading bot.

Strategy
--------
* Contract type : DIGITOVER (last digit of tick must be > barrier)
* Barrier       : 2  (i.e. last digit must be 3-9, probability 70%)
* Initial stake : 1 USD
* Loss recovery : Martingale — stake is doubled after each loss and reset
                  to the initial value after a win.
* Safety cap    : the bot halts automatically after MAX_CONSECUTIVE_LOSSES
                  consecutive losses to prevent runaway drawdown.


Usage
-----
Instantiate DerivBot and call ``await bot.run()``.  See main.py for the
recommended entry point.
"""

import asyncio
import json
import logging
import sys
from typing import Optional

import websockets

import config

logger = logging.getLogger(__name__)


class DerivBot:
    """Asyncio-based Deriv trading bot with Martingale loss recovery."""

    def __init__(self) -> None:
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._stake: float = config.INITIAL_STAKE
        self._consecutive_losses: int = 0
        self._total_trades: int = 0
        self._wins: int = 0
        self._losses: int = 0
        self._profit: float = 0.0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Connect to Deriv, authorise, then trade indefinitely."""
        logger.info("Connecting to %s …", config.WS_URL)
        async with websockets.connect(config.WS_URL) as ws:
            self._ws = ws
            await self._authorize()
            logger.info("Authorisation successful. Starting trading loop …")
            await self._trading_loop()

    # ------------------------------------------------------------------
    # WebSocket helpers
    # ------------------------------------------------------------------

    async def _send(self, payload: dict) -> dict:
        """Send *payload* and return the first response that matches its
        ``msg_type`` (passthrough / subscription messages are discarded)."""
        await self._ws.send(json.dumps(payload))
        req_id = payload.get("req_id", 1)
        while True:
            raw = await self._ws.recv()
            response = json.loads(raw)
            if response.get("req_id") == req_id or "error" in response:
                return response
            # Discard unrelated streaming messages (e.g. tick stream)

    # ------------------------------------------------------------------
    # Authorisation
    # ------------------------------------------------------------------

    async def _authorize(self) -> None:
        payload = {
            "authorize": config.API_TOKEN,
            "req_id": 1,
        }
        response = await self._send(payload)
        if "error" in response:
            code = response["error"].get("code", "unknown")
            msg = response["error"].get("message", "")
            raise RuntimeError(f"Authorisation failed [{code}]: {msg}")
        email = response.get("authorize", {}).get("email", "<unknown>")
        balance = response.get("authorize", {}).get("balance", "?")
        currency = response.get("authorize", {}).get("currency", "")
        logger.info("Logged in as %s — balance: %s %s", email, balance, currency)

    # ------------------------------------------------------------------
    # Trading loop
    # ------------------------------------------------------------------

    async def _trading_loop(self) -> None:
        while True:
            if self._consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
                logger.warning(
                    "Reached %d consecutive losses. Stopping to protect account.",
                    config.MAX_CONSECUTIVE_LOSSES,
                )
                self._print_summary()
                break

            logger.info(
                "Placing trade #%d — stake: %.2f %s | DIGITOVER %s on %s",
                self._total_trades + 1,
                self._stake,
                config.CURRENCY,
                config.DIGIT_BARRIER,
                config.SYMBOL,
            )

            buy_response = await self._buy_contract()
            if buy_response is None:
                # Non-fatal error already logged; wait and retry
                await asyncio.sleep(2)
                continue

            contract_id = buy_response["buy"]["contract_id"]
            buy_price = float(buy_response["buy"]["buy_price"])
            logger.info("Contract purchased — id: %s, cost: %.2f", contract_id, buy_price)

            result = await self._wait_for_settlement(contract_id)
            if result is None:
                await asyncio.sleep(2)
                continue

            self._handle_result(result)

            # Small pause between trades
            await asyncio.sleep(1)

    # ------------------------------------------------------------------
    # Contract purchase
    # ------------------------------------------------------------------

    async def _buy_contract(self) -> Optional[dict]:
        payload = {
            "buy": "1",  # "1" means buy a new contract (not a proposal)
            "price": self._stake,
            "parameters": {
                "amount": self._stake,
                "basis": "stake",
                "contract_type": config.CONTRACT_TYPE,
                "currency": config.CURRENCY,
                "duration": config.DURATION,
                "duration_unit": config.DURATION_UNIT,
                "symbol": config.SYMBOL,
                "barrier": config.DIGIT_BARRIER,
            },
            "req_id": 2,
        }
        response = await self._send(payload)
        if "error" in response:
            code = response["error"].get("code", "unknown")
            msg = response["error"].get("message", "")
            logger.error("Buy failed [%s]: %s", code, msg)
            return None
        return response

    # ------------------------------------------------------------------
    # Settlement polling
    # ------------------------------------------------------------------

    async def _wait_for_settlement(self, contract_id: int) -> Optional[dict]:
        """Poll the contract until it settles and return the final status."""
        payload = {
            "proposal_open_contract": 1,
            "contract_id": contract_id,
            "subscribe": 1,
            "req_id": 3,
        }
        await self._ws.send(json.dumps(payload))

        while True:
            raw = await self._ws.recv()
            response = json.loads(raw)

            if "error" in response:
                code = response["error"].get("code", "unknown")
                msg = response["error"].get("message", "")
                logger.error("Settlement error [%s]: %s", code, msg)
                return None

            if response.get("msg_type") != "proposal_open_contract":
                continue

            contract = response.get("proposal_open_contract", {})
            if contract.get("is_settleable") or contract.get("is_sold"):
                # Unsubscribe from the stream
                forget_id = response.get("subscription", {}).get("id")
                if forget_id:
                    await self._ws.send(
                        json.dumps({"forget": forget_id, "req_id": 4})
                    )
                return contract

    # ------------------------------------------------------------------
    # Result handling & Martingale logic
    # ------------------------------------------------------------------

    def _handle_result(self, contract: dict) -> None:
        self._total_trades += 1
        profit = float(contract.get("profit", 0))
        self._profit += profit

        if profit > 0:
            self._wins += 1
            self._consecutive_losses = 0
            logger.info(
                "WIN  — profit: +%.2f | total P&L: %.2f | consecutive losses reset",
                profit,
                self._profit,
            )
            # Reset stake to initial value after a win
            self._stake = config.INITIAL_STAKE
        else:
            self._losses += 1
            self._consecutive_losses += 1
            logger.info(
                "LOSS — profit: %.2f | total P&L: %.2f | consecutive losses: %d",
                profit,
                self._profit,
                self._consecutive_losses,
            )
            # Double the stake for the next trade (Martingale recovery)
            self._stake = round(self._stake * config.LOSS_MULTIPLIER, 2)
            logger.info(
                "Stake increased to %.2f %s for next trade",
                self._stake,
                config.CURRENCY,
            )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _print_summary(self) -> None:
        logger.info(
            "=== SESSION SUMMARY === "
            "Trades: %d | Wins: %d | Losses: %d | Net P&L: %.2f %s",
            self._total_trades,
            self._wins,
            self._losses,
            self._profit,
            config.CURRENCY,
        )
