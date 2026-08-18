# AI-Powered Stock Market Screening & Analysis System

A real-time NSE stock screening dashboard with SMMA crossover detection,
an AI module that accepts/rejects trading signals with a confidence
score and explanation, a rule-based "Developer Strategy" long-term
stock picker, and a modern live-updating web dashboard — built for a
college assignment.

## What's included

| Requirement | Where it lives |
|---|---|
| NSE screening (₹30–₹500 LTP) | `dashboard/screener.py` |
| Liquidity filter (bid/ask qty > 10,00,000) | `dashboard/screener.py` |
| SMMA(20) / SMMA(120) + crossover detection | `strategy/indicators.py` |
| Traded qty over 5/20/60 min | `strategy/indicators.py` |
| Avg LTP over 20/60 min | `strategy/indicators.py` |
| Market depth (bid/ask price & qty) | `strategy/indicators.py`, dashboard table |
| Real-time WebSocket dashboard | `dashboard/manager.py`, `main.py`, `static/js/app.js` |
| AI accept/reject + confidence + explanation | `ai/predictor.py` |
| AI model training (XGBoost / RandomForest) | `ai/train_model.py` |
| Developer Strategy (rule-based long-term picks) | `strategy/developer_strategy.py` |
| AI Generalized Recommendations (Buy/Sell/Avoid) | `ai/generalized.py` |
| Expandable row analytics (confidence, quality, pressure, confluence...) | `ai/analysis.py` |
| Dashboard UI (search, sort, pagination, badges, dark/light) | `templates/index.html`, `static/` |

## Important note on live data

This project ships with a **market data simulator** (`broker/mock_feed.py`)
enabled by default (`mode: "SIMULATE"` in `config.sample.json`), so the
entire application — screening, indicators, AI, dashboard — runs and
updates live without needing a broker account.

The **only** external broker integration in this project is Angel One
SmartAPI, implemented directly (no extra wrapper classes) in
`broker/angel_one.py` — login via `pyotp` TOTP, instrument-master
lookup, and a `SmartWebSocketV2` live feed subscription.

### Where to add your Angel One API credentials

1. Copy `config.sample.json` to `config.json`.
2. Fill in the `angel_one` block:

```json
{
  "mode": "LIVE",
  "angel_one": {
    "api_key":     "YOUR_API_KEY",
    "client_id":   "YOUR_CLIENT_ID",
    "password":    "YOUR_LOGIN_PIN",
    "totp_secret": "YOUR_TOTP_SECRET"
  }
}
```

3. Run the app normally (`python main.py`). `main.py` will detect
   `"mode": "LIVE"` and call `broker/angel_one.py`'s `login()` and
   `start_feed()` automatically — no other code changes required.

`config.json` is git-ignored so your credentials never get committed.

**Note:** the tick field mapping in `broker/angel_one.py`'s `_map_tick()`
follows Angel One's documented SNAP_QUOTE payload structure, but wasn't
tested against a live connection in this environment (no network access
to Angel One's servers here) — double check field names against your
SDK version's docs on your first live run.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Train the AI model (creates ai/signal_model.joblib)
python -m ai.train_model

# Run the app
python main.py
# or
uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000** in your browser.

## Project structure

```
stock_screener/
├── main.py                  # FastAPI app, startup, WebSocket endpoint
├── config.sample.json       # Config template (copy to config.json to customize)
├── requirements.txt
├── build.spec                # PyInstaller spec
├── broker/
│   ├── angel_one.py          # Angel One SmartAPI integration (only broker used)
│   └── mock_feed.py         # Built-in market data simulator
├── strategy/
│   ├── indicators.py        # SMMA, crossover, rolling windows
│   └── developer_strategy.py# Rule-based long-term picks
├── ai/
│   ├── train_model.py       # Trains XGBoost/RandomForest classifier
│   ├── predictor.py         # Crossover -> accept/reject + confidence + reason
│   ├── generalized.py       # Always-on Buy/Sell/Avoid recommendation
│   └── analysis.py          # Builds full expanded-row analytics payload
├── dashboard/
│   ├── manager.py           # WebSocket connection manager
│   └── screener.py          # Screening engine (filters + orchestration)
├── database/
│   └── db.py                 # SQLite schema + access functions
├── models/
│   └── schemas.py            # Pydantic response models
├── utils/
│   ├── config.py
│   └── stock_universe.py    # Symbol list scanned by the app
├── static/
│   ├── css/style.css
│   └── js/app.js
└── templates/
    └── index.html
```

## Building a standalone executable

```bash
pip install pyinstaller
pyinstaller build.spec
```

The executable will be created in `dist/ai_stock_screener`. Note that the
SQLite database (`market_data.db`) is created next to the executable at
runtime, not bundled.

## Retraining the AI model on real data

`ai/train_model.py` currently trains on a synthetic-but-domain-informed
dataset (`build_training_data()`), since real historical NSE tick data
with labelled crossover outcomes wasn't available in this environment.
Swap that function for a loader over your own historical dataset (same
`FEATURES` list) to retrain on real market history — the rest of the
pipeline (prediction, confidence scoring, explanations) needs no changes.




## Known limitations (by design, per assignment scope)

- No authentication/login system (per assignment constraints).
- No Docker/Kubernetes/Redis/Celery — single-process FastAPI app with
  a background asyncio task driving the screen + WebSocket broadcast.
- Ownership data (promoter/FII/DII/retail holdings) is seeded with
  realistic sample values (`broker/mock_feed.seed_ownership_data`) since
  no live shareholding-pattern data source was available; replace with
  a real data source (e.g. NSE corporate filings) for production use.
