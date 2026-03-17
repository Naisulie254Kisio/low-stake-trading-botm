"""
tests/test_bot.py - Unit tests for the Deriv trading bot.

These tests exercise the Martingale stake management and result-handling
logic without requiring a real WebSocket connection.
"""

import sys
import os
import types
import unittest

# ---------------------------------------------------------------------------
# Stub out external dependencies so we can import bot.py without installing
# websockets or having a .env file present.
# ---------------------------------------------------------------------------

# Stub websockets module
ws_stub = types.ModuleType("websockets")
sys.modules.setdefault("websockets", ws_stub)

# Stub dotenv module
dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", dotenv_stub)

# Provide minimal environment variables so config.py can be imported
os.environ.setdefault("DERIV_API_TOKEN", "test_token")
os.environ.setdefault("DERIV_APP_ID", "1089")

# Now it is safe to import our modules
import config  # noqa: E402
from bot import DerivBot  # noqa: E402


class TestMartingaleStakeLogic(unittest.TestCase):
    """Tests for the Martingale loss-recovery stake management."""

    def _make_bot(self) -> DerivBot:
        return DerivBot()

    def _win_contract(self, profit: float = 0.87) -> dict:
        return {"profit": profit, "is_sold": True}

    def _loss_contract(self, profit: float = -1.0) -> dict:
        return {"profit": profit, "is_sold": True}

    # ------------------------------------------------------------------

    def test_initial_stake_is_one_usd(self):
        bot = self._make_bot()
        self.assertEqual(bot._stake, 1.0)

    def test_win_resets_stake_to_initial(self):
        bot = self._make_bot()
        # Simulate a loss first to raise the stake
        bot._handle_result(self._loss_contract())
        self.assertGreater(bot._stake, config.INITIAL_STAKE)
        # Now simulate a win — stake must go back to INITIAL_STAKE
        bot._handle_result(self._win_contract())
        self.assertEqual(bot._stake, config.INITIAL_STAKE)

    def test_loss_doubles_stake(self):
        bot = self._make_bot()
        bot._handle_result(self._loss_contract())
        self.assertAlmostEqual(bot._stake, config.INITIAL_STAKE * config.LOSS_MULTIPLIER)

    def test_consecutive_losses_double_each_time(self):
        bot = self._make_bot()
        expected = config.INITIAL_STAKE
        for i in range(4):
            bot._handle_result(self._loss_contract())
            expected = round(expected * config.LOSS_MULTIPLIER, 2)
            self.assertAlmostEqual(bot._stake, expected, places=2,
                                   msg=f"Stake wrong after loss #{i + 1}")

    def test_win_resets_consecutive_losses_counter(self):
        bot = self._make_bot()
        for _ in range(3):
            bot._handle_result(self._loss_contract())
        self.assertEqual(bot._consecutive_losses, 3)
        bot._handle_result(self._win_contract())
        self.assertEqual(bot._consecutive_losses, 0)

    def test_wins_and_losses_are_counted(self):
        bot = self._make_bot()
        bot._handle_result(self._win_contract())
        bot._handle_result(self._loss_contract())
        bot._handle_result(self._win_contract())
        self.assertEqual(bot._wins, 2)
        self.assertEqual(bot._losses, 1)
        self.assertEqual(bot._total_trades, 3)

    def test_profit_accumulates_correctly(self):
        bot = self._make_bot()
        bot._handle_result(self._win_contract(profit=0.87))
        bot._handle_result(self._loss_contract(profit=-1.0))
        self.assertAlmostEqual(bot._profit, -0.13, places=5)

    def test_stake_sequence_win_loss_win(self):
        """W → L → W: stake should go 1 → 1 → 2 → 1."""
        bot = self._make_bot()
        self.assertEqual(bot._stake, 1.0)
        bot._handle_result(self._win_contract())
        self.assertEqual(bot._stake, 1.0)   # win resets
        bot._handle_result(self._loss_contract())
        self.assertEqual(bot._stake, 2.0)   # loss doubles
        bot._handle_result(self._win_contract())
        self.assertEqual(bot._stake, 1.0)   # win resets


class TestConfig(unittest.TestCase):
    """Sanity-checks for configuration values."""

    def test_initial_stake_is_one(self):
        self.assertEqual(config.INITIAL_STAKE, 1.0)

    def test_loss_multiplier_is_two(self):
        self.assertEqual(config.LOSS_MULTIPLIER, 2.0)

    def test_contract_type_is_digitover(self):
        self.assertEqual(config.CONTRACT_TYPE, "DIGITOVER")

    def test_barrier_is_two(self):
        self.assertEqual(config.DIGIT_BARRIER, "2")

    def test_currency_is_usd(self):
        self.assertEqual(config.CURRENCY, "USD")

    def test_max_consecutive_losses_positive(self):
        self.assertGreater(config.MAX_CONSECUTIVE_LOSSES, 0)


if __name__ == "__main__":
    unittest.main()
