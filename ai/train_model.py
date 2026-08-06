"""
Trains a supervised model that, given the feature set at the moment an
SMMA crossover is detected, predicts whether the signal is a strong
BUY/SELL worth accepting or a weak signal that should be rejected.

Since this is a college project without access to years of tick-level
history, training data is synthesized using domain-informed rules with
noise (e.g. strong volume + tight spread + trend alignment => genuine
signal; low liquidity + high volatility + contradicting momentum =>
false signal). This mirrors how a real model would behave once trained
on real historical crossovers - swap `build_training_data()` for a
loader over your real historical dataset when available.

Run:
    python -m ai.train_model
"""
import numpy as np
import pandas as pd
import joblib
import os

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, "signal_model.joblib")

FEATURES = [
    "smma_fast", "smma_slow", "smma_gap_pct",
    "volume", "momentum", "volatility",
    "bid_qty", "ask_qty", "depth_imbalance",
    "traded_qty_ratio", "liquidity_score",
]


def build_training_data(n=6000, seed=42):
    rng = np.random.default_rng(seed)

    smma_fast = rng.uniform(20, 500, n)
    gap_pct = rng.normal(0, 2.5, n)
    smma_slow = smma_fast - (smma_fast * gap_pct / 100)

    volume = rng.exponential(300000, n)
    momentum = rng.normal(0, 3, n)
    volatility = rng.exponential(1.2, n)
    bid_qty = rng.exponential(900000, n)
    ask_qty = rng.exponential(900000, n)
    depth_imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty + 1)
    traded_qty_ratio = rng.uniform(0.2, 3.0, n)
    liquidity_score = np.clip((bid_qty + ask_qty) / 2_000_000, 0, 3)

    df = pd.DataFrame({
        "smma_fast": smma_fast,
        "smma_slow": smma_slow,
        "smma_gap_pct": gap_pct,
        "volume": volume,
        "momentum": momentum,
        "volatility": volatility,
        "bid_qty": bid_qty,
        "ask_qty": ask_qty,
        "depth_imbalance": depth_imbalance,
        "traded_qty_ratio": traded_qty_ratio,
        "liquidity_score": liquidity_score,
    })

    # domain-informed label: a signal is "accepted" (1) when liquidity is
    # healthy, momentum agrees with direction implied by the gap, and
    # volatility isn't extreme relative to volume support.
    direction = np.sign(df["smma_gap_pct"])
    momentum_agrees = (np.sign(df["momentum"]) == direction).astype(int)

    score = (
        1.4 * momentum_agrees
        + 1.0 * (df["liquidity_score"] > 0.6).astype(int)
        + 0.8 * (df["volume"] > 250000).astype(int)
        + 0.6 * (df["traded_qty_ratio"] > 0.8).astype(int)
        - 1.2 * (df["volatility"] > 2.5).astype(int)
        - 0.5 * (df["depth_imbalance"].abs() > 0.6).astype(int)
        + rng.normal(0, 0.6, n)
    )

    label = (score > 1.2).astype(int)
    return df, label


def train():
    X, y = build_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    if HAS_XGB:
        model = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.08,
            subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
            random_state=42,
        )
    else:
        model = RandomForestClassifier(n_estimators=300, max_depth=8, random_state=42)

    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    print(classification_report(y_test, preds, target_names=["REJECT", "ACCEPT"]))

    joblib.dump({"model": model, "features": FEATURES}, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    return model


if __name__ == "__main__":
    train()
