# low-stake-trading-botm

A low-stake trading bot for [Deriv](https://deriv.com) written in Python.

## Strategy

| Parameter | Value |
|-----------|-------|
| Contract type | **DIGITOVER** – last digit of the tick must be **> 2** (digits 3–9, ~70 % probability) |
| Initial stake | **1 USD** |
| Loss recovery | **Martingale** – stake is doubled after every loss, reset to 1 USD after a win |
| Safety cap | Bot stops automatically after **6 consecutive losses** |

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env and set DERIV_API_TOKEN to your real or demo API token
# Obtain one at https://app.deriv.com/account/api-token
```

### 3. Run the bot

```bash
python main.py
```

## File layout

```
main.py          – entry point
bot.py           – core trading logic (WebSocket, Martingale)
config.py        – all tuneable parameters
requirements.txt – Python dependencies
.env.example     – template for environment variables
tests/           – unit tests (no live API required)
```

## Running tests

```bash
python -m pytest tests/ -v
```

## Risk warning

Trading involves risk. The Martingale strategy can lead to rapid drawdown
during long losing streaks. Always test on a **demo account** first and never
risk money you cannot afford to lose.
