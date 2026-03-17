"""
main.py - Entry point for the Deriv trading bot.

Run with:
    python main.py
"""

import asyncio
import logging
import sys

import config
from bot import DerivBot

logging.basicConfig(
    level=logging.INFO,
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
    stream=sys.stdout,
)


async def _main() -> None:
    bot = DerivBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(_main())
