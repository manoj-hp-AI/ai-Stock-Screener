"""
Technical indicator calculations.

SMMA (Smoothed Moving Average) formula:
    SMMA[0] = SMA(period) of the first `period` values
    SMMA[i] = (SMMA[i-1] * (period - 1) + price[i]) / period

Crossover:
    BUY  -> SMMA_fast crosses from below to above SMMA_slow
    SELL -> SMMA_fast crosses from above to below SMMA_slow
"""
import numpy as np
import time
from database import db


def compute_smma(prices: list, period: int) -> list:
    if len(prices) < period:
        return [None] * len(prices)

    smma = [None] * (period - 1)
    seed = sum(prices[:period]) / period
    smma.append(seed)

    prev = seed
    for price in prices[period:]:
        val = (prev * (period - 1) + price) / period
        smma.append(val)
        prev = val

    return smma


def detect_crossover(smma_fast: list, smma_slow: list) -> str:
    """Returns 'BUY', 'SELL', or None based on the last two points."""
    if len(smma_fast) < 2 or len(smma_slow) < 2:
        return None
    f_prev, f_now = smma_fast[-2], smma_fast[-1]
    s_prev, s_now = smma_slow[-2], smma_slow[-1]
    if None in (f_prev, f_now, s_prev, s_now):
        return None

    if f_prev <= s_prev and f_now > s_now:
        return "BUY"
    if f_prev >= s_prev and f_now < s_now:
        return "SELL"
    return None


def compute_indicators_for_symbol(symbol: str, fast_period: int, slow_period: int, lookback_seconds: float = 3600 * 6):
    """
    Pulls tick history for a symbol and computes:
      - SMMA fast/slow series + crossover signal
      - traded qty over 5/20/60 min windows
      - average LTP over 20/60 min windows
      - latest market depth (bid/ask price & qty)
    """
    ticks = db.get_recent_ticks(symbol, lookback_seconds)
    if not ticks:
        return None

    prices = [t["ltp"] for t in ticks]
    smma_fast = compute_smma(prices, fast_period)
    smma_slow = compute_smma(prices, slow_period)
    crossover = detect_crossover(smma_fast, smma_slow)

    now = time.time()
    latest = ticks[-1]

    def window_stats(minutes):
        cutoff = now - minutes * 60
        window = [t for t in ticks if t["timestamp"] >= cutoff]
        traded_qty = sum(t["traded_qty"] for t in window) if window else 0
        avg_ltp = float(np.mean([t["ltp"] for t in window])) if window else latest["ltp"]
        return traded_qty, avg_ltp

    traded_5, _ = window_stats(5)
    traded_20, avg_20 = window_stats(20)
    traded_60, avg_60 = window_stats(60)

    # momentum: % change of LTP over the last N ticks (proxy for short-term momentum)
    momentum = 0.0
    if len(prices) >= 10:
        momentum = (prices[-1] - prices[-10]) / prices[-10] * 100

    volatility = float(np.std(prices[-30:])) if len(prices) >= 5 else 0.0

    return {
        "symbol": symbol,
        "ltp": latest["ltp"],
        "bid_price": latest["bid_price"],
        "bid_qty": latest["bid_qty"],
        "ask_price": latest["ask_price"],
        "ask_qty": latest["ask_qty"],
        "smma_fast": smma_fast[-1],
        "smma_slow": smma_slow[-1],
        "crossover": crossover,
        "traded_qty_5m": traded_5,
        "traded_qty_20m": traded_20,
        "traded_qty_60m": traded_60,
        "avg_ltp_20m": avg_20,
        "avg_ltp_60m": avg_60,
        "momentum": momentum,
        "volatility": volatility,
        "timestamp": now,
    }
