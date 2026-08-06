"""
Runs on a timer: pulls the latest indicators for every symbol in the
universe, applies the price + liquidity screening filters from the
assignment spec, builds the full AI analysis for surviving rows, and
evaluates the Developer Strategy long-term picks. Returns the full
payload to be broadcast over WebSocket.
"""
import time
from utils.stock_universe import NSE_UNIVERSE
from utils.config import CONFIG
from strategy import indicators as ind_mod
from strategy import developer_strategy
from ai import analysis as analysis_mod
from database import db


def run_screen():
    screening_cfg = CONFIG["screening"]
    ind_cfg = CONFIG["indicators"]

    rows = []
    signals_fired = []

    for stock in NSE_UNIVERSE:
        symbol = stock["symbol"]
        ind = ind_mod.compute_indicators_for_symbol(
            symbol, ind_cfg["smma_fast"], ind_cfg["smma_slow"]
        )
        if ind is None:
            continue

        # --- Screening filters ---
        if not (screening_cfg["min_ltp"] <= ind["ltp"] <= screening_cfg["max_ltp"]):
            continue
        if not (ind["bid_qty"] >= screening_cfg["min_bid_qty"]):
            continue
        if not (ind["ask_qty"] >= screening_cfg["min_ask_qty"]):
            continue

        row = analysis_mod.build_row_analysis(ind)
        rows.append(row)

        if row["crossover_signal"] is not None:
            sig = row["crossover_signal"]
            db.insert_signal({
                "symbol": symbol,
                "signal_type": sig["signal_type"],
                "accepted": sig["accepted"],
                "confidence": sig["confidence"],
                "reason": sig["reason"],
                "smma_fast": row["smma_fast"] or 0,
                "smma_slow": row["smma_slow"] or 0,
                "timestamp": time.time(),
            })
            signals_fired.append(sig)

    # Developer Strategy - long-term picks (rule based, independent of live screen)
    ownership_rows = db.get_all_ownership()
    long_term = developer_strategy.evaluate_all(ownership_rows)

    return {
        "type": "screen_update",
        "timestamp": time.time(),
        "rows": rows,
        "signals_fired": signals_fired,
        "long_term_picks": long_term,
    }
