"""
Simulated live market data feed.

Generates realistic-looking ticks (random-walk LTP, bid/ask depth,
traded quantity) for the configured stock universe, at a fixed
interval, and periodically injects an SMMA crossover by nudging the
price trend so the AI/crossover pipeline has real signals to evaluate.

This lets the whole application run end-to-end without a live broker
connection.
"""
import random
import time
import threading
from utils.stock_universe import NSE_UNIVERSE
from database import db


class MockFeed:
    def __init__(self, on_tick, interval_seconds: float = 2.0):
        self.on_tick = on_tick
        self.interval = interval_seconds
        self._running = False
        self._thread = None
        self._state = {
            s["symbol"]: {"price": s["base_price"], "trend": random.choice([-1, 1]), "trend_ticks_left": random.randint(20, 60)}
            for s in NSE_UNIVERSE
        }

    def _next_price(self, symbol):
        st = self._state[symbol]

        # occasionally flip trend direction to create crossovers over time
        st["trend_ticks_left"] -= 1
        if st["trend_ticks_left"] <= 0:
            st["trend"] *= -1
            st["trend_ticks_left"] = random.randint(20, 60)

        drift = st["trend"] * random.uniform(0.05, 0.35)
        noise = random.uniform(-0.4, 0.4)
        st["price"] = max(1.0, st["price"] + drift + noise)
        return round(st["price"], 2)

    def _generate_tick(self, symbol):
        ltp = self._next_price(symbol)
        spread = round(ltp * random.uniform(0.0005, 0.002), 2)
        bid_price = round(ltp - spread, 2)
        ask_price = round(ltp + spread, 2)

        # keep quantities in a range that regularly straddles the 10,00,000 liquidity filter
        bid_qty = random.randint(200_000, 2_000_000)
        ask_qty = random.randint(200_000, 2_000_000)
        traded_qty = random.randint(1_000, 50_000)

        return {
            "symbol": symbol,
            "ltp": ltp,
            "bid_price": bid_price,
            "bid_qty": bid_qty,
            "ask_price": ask_price,
            "ask_qty": ask_qty,
            "traded_qty": traded_qty,
            "timestamp": time.time(),
        }

    def _run(self):
        while self._running:
            for s in NSE_UNIVERSE:
                tick = self._generate_tick(s["symbol"])
                db.insert_tick(tick)
                self.on_tick(tick)
            time.sleep(self.interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False


def seed_ownership_data():
    """Seeds plausible promoter/FII/DII/retail holding snapshots so the
    Developer Strategy section has data to evaluate immediately."""
    for s in NSE_UNIVERSE:
        symbol = s["symbol"]
        promoter = round(random.uniform(35, 75), 1)
        fii = round(random.uniform(0.5, 8), 2)
        retail = round(random.uniform(15, 45), 1)
        dii = round(max(0, 100 - promoter - fii - retail - random.uniform(0, 10)), 1)
        q1 = round(retail + random.uniform(-4, 4), 1)
        q2 = round(retail + random.uniform(-4, 4), 1)
        q3 = round(retail + random.uniform(-4, 4), 1)

        db.upsert_ownership({
            "symbol": symbol,
            "promoter_holding": promoter,
            "fii_holding": fii,
            "dii_holding": dii,
            "retail_holding": retail,
            "retail_q1": q1,
            "retail_q2": q2,
            "retail_q3": q3,
        })
