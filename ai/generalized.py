"""
AI Generalized Recommendations.

Unlike the crossover-triggered predictor (ai/predictor.py), this scores
EVERY stock currently on the screened dashboard - not just ones with an
active crossover - producing a continuous Buy / Sell / Avoid view with
probability, risk, reason and trend. It reuses the same trained model's
"accept probability" as a proxy for conviction, applied to the stock's
current (not necessarily crossing) SMMA relationship.
"""
from ai.predictor import _load, _build_feature_row
import numpy as np


def recommend(indicators: dict) -> dict:
    bundle = _load()
    model, feature_names = bundle["model"], bundle["features"]

    feat = _build_feature_row(indicators)
    X = np.array([[feat[f] for f in feature_names]])
    proba = float(model.predict_proba(X)[0][1])

    smma_fast = indicators["smma_fast"] or 0
    smma_slow = indicators["smma_slow"] or 0
    trend = "Uptrend" if smma_fast > smma_slow else "Downtrend"

    if proba >= 0.65 and trend == "Uptrend":
        action, risk = "BUY", "Low" if feat["volatility"] < 1.5 else "Medium"
    elif proba >= 0.65 and trend == "Downtrend":
        action, risk = "SELL", "Low" if feat["volatility"] < 1.5 else "Medium"
    elif proba < 0.4:
        action, risk = "AVOID", "High"
    else:
        action, risk = "AVOID", "Medium"

    reason_bits = []
    reason_bits.append(f"trend is {trend.lower()}")
    reason_bits.append("healthy liquidity" if feat["liquidity_score"] > 0.6 else "weak liquidity")
    reason_bits.append("momentum supportive" if (indicators["momentum"] > 0) == (trend == "Uptrend") else "momentum conflicting")
    if feat["volatility"] > 2.5:
        reason_bits.append("high volatility")

    return {
        "symbol": indicators["symbol"],
        "action": action,
        "probability": round(proba * 100, 1),
        "risk": risk,
        "trend": trend,
        "reason": ", ".join(reason_bits).capitalize() + ".",
    }
