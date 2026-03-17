"""
config.py - Central configuration for the Deriv trading bot.

All tuneable parameters live here so that bot.py stays clean.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Deriv API credentials
# ---------------------------------------------------------------------------
API_TOKEN: str = os.environ["DERIV_API_TOKEN"]
APP_ID: str = os.getenv("DERIV_APP_ID", "1089")

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
WS_URL: str = f"wss://ws.binaryws.com/websockets/v3?app_id={APP_ID}"

# ---------------------------------------------------------------------------
# Trade parameters
# ---------------------------------------------------------------------------
# Symbol to trade on (volatility index 100 ticks — available 24/7 on demo/live)
SYMBOL: str = "R_100"

# Duration of each contract (in ticks)
DURATION: int = 1
DURATION_UNIT: str = "t"

# "DIGITOVER" = last digit of the tick must be strictly above DIGIT_BARRIER
CONTRACT_TYPE: str = "DIGITOVER"
DIGIT_BARRIER: str = "2"

# Currency
CURRENCY: str = "USD"

# ---------------------------------------------------------------------------
# Staking / loss-recovery (Martingale) parameters
# ---------------------------------------------------------------------------
# Initial stake in USD
INITIAL_STAKE: float = 1.0

# Multiplier applied to the stake after each loss
LOSS_MULTIPLIER: float = 2.0

# Maximum consecutive losses before the bot stops to protect the account
MAX_CONSECUTIVE_LOSSES: int = 6

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
