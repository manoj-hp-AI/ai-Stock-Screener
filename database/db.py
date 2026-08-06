"""
SQLite persistence layer.

Tables:
  ticks       - raw tick history per symbol (used to compute rolling windows)
  signals     - AI-evaluated crossover signals (buy/sell/rejected) with confidence
  ownership   - promoter/FII/DII/retail holding snapshots used by Developer Strategy
"""
import sqlite3
import os
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "market_data.db")

_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            ltp REAL NOT NULL,
            bid_price REAL,
            bid_qty INTEGER,
            ask_price REAL,
            ask_qty INTEGER,
            traded_qty INTEGER,
            timestamp REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,       -- BUY / SELL
            accepted INTEGER NOT NULL,       -- 1 accepted, 0 rejected
            confidence REAL,
            reason TEXT,
            smma_fast REAL,
            smma_slow REAL,
            timestamp REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ownership (
            symbol TEXT PRIMARY KEY,
            promoter_holding REAL,
            fii_holding REAL,
            dii_holding REAL,
            retail_holding REAL,
            retail_q1 REAL,
            retail_q2 REAL,
            retail_q3 REAL
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_ticks_symbol_ts ON ticks(symbol, timestamp)")

    conn.commit()
    conn.close()


def insert_tick(tick: dict):
    with _lock:
        conn = get_conn()
        conn.execute(
            """INSERT INTO ticks (symbol, ltp, bid_price, bid_qty, ask_price, ask_qty, traded_qty, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tick["symbol"], tick["ltp"], tick["bid_price"], tick["bid_qty"],
             tick["ask_price"], tick["ask_qty"], tick["traded_qty"], tick["timestamp"])
        )
        conn.commit()
        conn.close()


def get_recent_ticks(symbol: str, seconds: float, limit: int = 5000):
    import time
    since = time.time() - seconds
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM ticks WHERE symbol = ? AND timestamp >= ? ORDER BY timestamp ASC LIMIT ?",
        (symbol, since, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_signal(sig: dict):
    with _lock:
        conn = get_conn()
        conn.execute(
            """INSERT INTO signals (symbol, signal_type, accepted, confidence, reason, smma_fast, smma_slow, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sig["symbol"], sig["signal_type"], int(sig["accepted"]), sig["confidence"],
             sig["reason"], sig["smma_fast"], sig["smma_slow"], sig["timestamp"])
        )
        conn.commit()
        conn.close()


def upsert_ownership(row: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO ownership (symbol, promoter_holding, fii_holding, dii_holding,
                                retail_holding, retail_q1, retail_q2, retail_q3)
        VALUES (:symbol, :promoter_holding, :fii_holding, :dii_holding,
                :retail_holding, :retail_q1, :retail_q2, :retail_q3)
        ON CONFLICT(symbol) DO UPDATE SET
            promoter_holding=excluded.promoter_holding,
            fii_holding=excluded.fii_holding,
            dii_holding=excluded.dii_holding,
            retail_holding=excluded.retail_holding,
            retail_q1=excluded.retail_q1,
            retail_q2=excluded.retail_q2,
            retail_q3=excluded.retail_q3
    """, row)
    conn.commit()
    conn.close()


def get_ownership(symbol: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM ownership WHERE symbol = ?", (symbol,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_ownership():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM ownership").fetchall()
    conn.close()
    return [dict(r) for r in rows]
