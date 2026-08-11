"""
Builds the complete analysis payload for a single stock row, combining:
  - raw indicators/depth (strategy.indicators)
  - crossover-triggered AI verdict (ai.predictor), when applicable
  - always-on AI Generalized Recommendation (ai.generalized)
  - derived "expanded row" metrics (buying/selling pressure, confluence, etc.)
"""
from ai import predictor, generalized


def _pressure_scores(ind: dict):
    bid_qty, ask_qty = ind["bid_qty"] or 0, ind["ask_qty"] or 0
    total = bid_qty + ask_qty + 1
    buying_pressure = round(bid_qty / total * 100, 1)
    selling_pressure = round(ask_qty / total * 100, 1)
    return buying_pressure, selling_pressure


def _liquidity_score(ind: dict):
    bid_qty, ask_qty = ind["bid_qty"] or 0, ind["ask_qty"] or 0
    return round(min((bid_qty + ask_qty) / 2_000_000, 3) * 33.3, 1)  # 0-100 scale


def build_row_analysis(ind: dict) -> dict:
    rec = generalized.recommend(ind)
    buying, selling = _pressure_scores(ind)
    liquidity_score = _liquidity_score(ind)

    crossover_signal = None
    if ind.get("crossover") in ("BUY", "SELL"):
        crossover_signal = predictor.predict(ind)

    ai_confidence = crossover_signal["confidence"] if crossover_signal else rec["probability"]

    trade_quality = round(
        (ai_confidence * 0.4) + (liquidity_score * 0.35) + (max(0, 100 - abs(ind["volatility"]) * 20) * 0.25), 1
    )
    trade_quality = min(trade_quality, 100)

    # confluence: how many independent factors agree with the recommended action
    factors_aligned = 0
    total_factors = 4
    if rec["trend"] == "Uptrend" and rec["action"] == "BUY":
        factors_aligned += 1
    if rec["trend"] == "Downtrend" and rec["action"] == "SELL":
        factors_aligned += 1
    if liquidity_score > 50:
        factors_aligned += 1
    if (ind["momentum"] > 0) == (rec["action"] == "BUY"):
        factors_aligned += 1
    confluence_score = round(factors_aligned / total_factors * 100, 1)

    opportunity_rating = round((trade_quality * 0.5 + confluence_score * 0.5) / 20, 1)  # 0-5 stars

    # numbers only on the wire - no reason/explanation text sent to the UI
    crossover_signal_public = None
    if crossover_signal:
        crossover_signal_public = {
            "signal_type": crossover_signal["signal_type"],
            "accepted": crossover_signal["accepted"],
            "confidence": crossover_signal["confidence"],
        }

    return {
        "symbol": ind["symbol"],
        "ltp": ind["ltp"],
        "bid_price": ind["bid_price"],
        "bid_qty": ind["bid_qty"],
        "ask_price": ind["ask_price"],
        "ask_qty": ind["ask_qty"],
        "smma_fast": round(ind["smma_fast"], 2) if ind["smma_fast"] else None,
        "smma_slow": round(ind["smma_slow"], 2) if ind["smma_slow"] else None,
        "traded_qty_5m": ind["traded_qty_5m"],
        "traded_qty_20m": ind["traded_qty_20m"],
        "traded_qty_60m": ind["traded_qty_60m"],
        "avg_ltp_20m": round(ind["avg_ltp_20m"], 2),
        "avg_ltp_60m": round(ind["avg_ltp_60m"], 2),

        "action": rec["action"],
        "probability": rec["probability"],
        "risk": rec["risk"],
        "trend": rec["trend"],

        "crossover_signal": crossover_signal_public,  # None, or {signal_type, accepted, confidence}

        "ai_confidence": ai_confidence,
        "trade_quality": trade_quality,
        "momentum": round(ind["momentum"], 2),
        "buying_pressure": buying,
        "selling_pressure": selling,
        "liquidity_score": liquidity_score,
        "opportunity_rating": opportunity_rating,
        "confluence_score": confluence_score,
    }
