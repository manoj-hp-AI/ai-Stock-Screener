"""
Angel One SmartAPI integration - direct, minimal, no custom wrapper class.

============================================================================
 ADD YOUR ANGEL ONE API CREDENTIALS IN config.json (NOT in this file):

    {
      "mode": "LIVE",
      "angel_one": {
        "api_key":     "YOUR_API_KEY",
        "client_id":   "YOUR_CLIENT_ID",
        "password":    "YOUR_LOGIN_PIN",
        "totp_secret": "YOUR_TOTP_SECRET"
      }
    }

 Copy config.sample.json -> config.json, fill in the "angel_one" block
 above, set "mode": "LIVE", then run the app normally (python main.py).
============================================================================

This module uses the official `smartapi-python` SDK directly - login,
instrument lookup, and the live WebSocket feed - with no extra
abstraction layer on top.
"""
import pyotp
import threading
import time
import requests

from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from database import db


def login(creds: dict):
    """
    creds = config["angel_one"]  (api_key, client_id, password, totp_secret)
    Returns (smart_connect_obj, jwt_token, feed_token)
    """
    obj = SmartConnect(api_key=creds["api_key"])
    totp = pyotp.TOTP(creds["totp_secret"]).now()

    session = obj.generateSession(creds["client_id"], creds["password"], totp)
    if not session.get("status"):
        raise RuntimeError(f"Angel One login failed: {session}")

    jwt_token = session["data"]["jwtToken"]
    feed_token = obj.getfeedToken()
    return obj, jwt_token, feed_token


def get_instrument_tokens(symbols: list) -> dict:
    """
    Downloads Angel One's NSE instrument master and returns
    {symbol: token} for the requested symbols.
    """
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    wanted = {s.upper() for s in symbols}
    tokens = {}
    for row in data:
        if row.get("exch_seg") == "NSE":
            name = row.get("name", "").upper()
            if name in wanted:
                tokens[name] = row["token"]
    return tokens


def _map_tick(message: dict) -> dict:
    """
    Maps a SmartWebSocketV2 SNAP_QUOTE message to the tick schema used
    by database.db.insert_tick(). Field names below follow Angel One's
    documented SNAP_QUOTE payload - verify against your SDK version's
    docs/examples if Angel One changes their schema.
    """
    depth = message.get("best_5_buy_data", [{}])
    depth_ask = message.get("best_5_sell_data", [{}])

    return {
        "symbol": message.get("trading_symbol", message.get("token", "UNKNOWN")),
        "ltp": message.get("last_traded_price", 0) / 100,   # Angel One sends paise
        "bid_price": (depth[0].get("price", 0) / 100) if depth else None,
        "bid_qty": depth[0].get("quantity") if depth else None,
        "ask_price": (depth_ask[0].get("price", 0) / 100) if depth_ask else None,
        "ask_qty": depth_ask[0].get("quantity") if depth_ask else None,
        "traded_qty": message.get("volume_trade_for_the_day", 0),
        "timestamp": time.time(),
    }


def start_feed(jwt_token: str, feed_token: str, creds: dict, tokens: list, on_tick=None):
    """
    Opens the SmartWebSocketV2 feed for the given instrument tokens and
    writes every tick to the database. Runs in a background thread.
    """
    ws = SmartWebSocketV2(jwt_token, creds["api_key"], creds["client_id"], feed_token)

    correlation_id = "screener"
    mode = 3  # SNAP_QUOTE - includes LTP, volume, and market depth
    token_list = [{"exchangeType": 1, "tokens": tokens}]

    def on_open(wsapp):
        ws.subscribe(correlation_id, mode, token_list)

    def on_data(wsapp, message):
        tick = _map_tick(message)
        db.insert_tick(tick)
        if on_tick:
            on_tick(tick)

    def on_error(wsapp, error):
        print("Angel One websocket error:", error)

    def on_close(wsapp):
        print("Angel One websocket closed")

    ws.on_open = on_open
    ws.on_data = on_data
    ws.on_error = on_error
    ws.on_close = on_close

    thread = threading.Thread(target=ws.connect, daemon=True)
    thread.start()
    return thread
