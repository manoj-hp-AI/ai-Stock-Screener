"""
Wraps the trained model to turn a detected SMMA crossover + live feature
snapshot into a final AI decision: accepted BUY/SELL with a confidence
percentage, or a rejected weak signal — plus a human-readable explanation.
"""
import os
import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signal_model.joblib")

_bundle = None


def _load():
    global _bundle
    if _bundle is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                "No trained model found. Run `python -m ai.train_model` first."
            )
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def _build_feature_row(ind: dict):
    smma_fast = ind["smma_fast"]
    smma_slow = ind["smma_slow"]
    gap_pct = (smma_fast - smma_slow) / smma_slow * 100 if smma_slow else 0.0

    bid_qty = ind["bid_qty"] or 1
    ask_qty = ind["ask_qty"] or 1
    depth_imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty + 1)
    liquidity_score = min((bid_qty + ask_qty) / 2_000_000, 3)
    volume = ind["traded_qty_60m"] or 1
    traded_qty_ratio = (ind["traded_qty_5m"] * 12) / (volume + 1) if volume else 0.0

    return {
        "smma_fast": smma_fast,
        "smma_slow": smma_slow,
        "smma_gap_pct": gap_pct,
        "volume": volume,
        "momentum": ind["momentum"],
        "volatility": ind["volatility"],
        "bid_qty": bid_qty,
        "ask_qty": ask_qty,
        "depth_imbalance": depth_imbalance,
        "traded_qty_ratio": traded_qty_ratio,
        "liquidity_score": liquidity_score,
    }


def _explain(feat: dict, accepted: bool, confidence: float, direction: str) -> str:
    parts = []

    if feat["liquidity_score"] > 0.6:
        parts.append("strong bid/ask depth")
    else:
        parts.append("thin order-book liquidity")

    momentum_aligned = (feat["momentum"] > 0 and direction == "BUY") or (feat["momentum"] < 0 and direction == "SELL")
    parts.append("momentum confirms direction" if momentum_aligned else "momentum diverges from signal direction")

    if feat["volatility"] > 2.5:
        parts.append("volatility is elevated")
    else:
        parts.append("volatility is within normal range")

    if abs(feat["depth_imbalance"]) > 0.6:
        parts.append("order book is heavily skewed on one side")

    verdict = "accepted" if accepted else "rejected as a weak signal"
    return f"{direction} crossover {verdict} ({confidence:.1f}% confidence): " + "; ".join(parts) + "."


def predict(indicators: dict) -> dict:
    """
    indicators: output of strategy.indicators.compute_indicators_for_symbol,
                must have a non-null `crossover` field ('BUY' or 'SELL').
    """
    direction = indicators["crossover"]
    if direction not in ("BUY", "SELL"):
        return None

    bundle = _load()
    model, feature_names = bundle["model"], bundle["features"]

    feat = _build_feature_row(indicators)
    X = np.array([[feat[f] for f in feature_names]])

    proba = model.predict_proba(X)[0]
    accept_proba = float(proba[1])
    accepted = accept_proba >= 0.5
    confidence = accept_proba * 100 if accepted else (1 - accept_proba) * 100

    return {
        "symbol": indicators["symbol"],
        "signal_type": direction,
        "accepted": accepted,
        "confidence": round(confidence, 1),
        "reason": _explain(feat, accepted, confidence, direction),
        "smma_fast": indicators["smma_fast"],
        "smma_slow": indicators["smma_slow"],
    }
