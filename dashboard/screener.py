"""
Runs on a timer: pulls the latest indicators for every symbol in the
universe, applies the price + liquidity screening filters from the
assignment spec, builds the full AI analysis for surviving rows, and
evaluates the Developer Strategy long-term picks (approved only, with
that stock's live performance numbers attached). Returns the full
payload to be broadcast over WebSocket.
"""
import time
from utils.stock_universe import NSE_UNIVERSE
from utils.config import CONFIG
from strategy import indicators as ind_mod
from strategy import developer_strategy
from ai import analysis as analysis_mod
from ai import generalized
from database import db


def run_screen():
    screening_cfg = CONFIG["screening"]
    ind_cfg = CONFIG["indicators"]

    all_indicators = {}
    rows = []
    signals_fired = []

    for stock in NSE_UNIVERSE:
        symbol = stock["symbol"]
        ind = ind_mod.compute_indicators_for_symbol(
            symbol, ind_cfg["smma_fast"], ind_cfg["smma_slow"]
        )
        if ind is None:
            continue

        all_indicators[symbol] = ind

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

    # Developer Strategy - rule based, independent of the live screen filters.
    # Only symbols that pass every rule are returned ("approved"); each
    # approved row is enriched with that stock's current live performance
    # numbers so the Developer Strategy tab is a performance view, not a
    # holdings/ownership view.
    ownership_rows = db.get_all_ownership()
    evaluated = developer_strategy.evaluate_all(ownership_rows)

    long_term = []
    for pick in evaluated:
        if not pick["qualified"]:
            continue

        symbol = pick["symbol"]
        ind = all_indicators.get(symbol)
        if ind is None:
            continue

        rec = generalized.recommend(ind)

        long_term.append({
            "symbol": symbol,
            "status": "WELL POSITIONED",
            "ltp": ind["ltp"],
            "action": rec["action"],
            "trend": rec["trend"],
            "ai_confidence": rec["probability"],
            "risk": rec["risk"],
            "momentum": round(ind["momentum"], 2),
            "avg_ltp_20m": round(ind["avg_ltp_20m"], 2),
            "avg_ltp_60m": round(ind["avg_ltp_60m"], 2),
            "traded_qty_60m": ind["traded_qty_60m"],
        })

    return {
        "type": "screen_update",
        "timestamp": time.time(),
        "rows": rows,
        "signals_fired": signals_fired,
        "long_term_picks": long_term,
    }
