"""
A representative slice of NSE-listed symbols to scan.

In LIVE mode, broker/angel_one.py pulls the full instrument list
from Angel One's instrument master file at runtime and this list is
only used as a fallback. In SIMULATE mode this is the universe the
mock feed generates ticks for.
"""

NSE_UNIVERSE = [
    {"symbol": "TATAMOTORS", "token": "3456", "base_price": 165.0},
    {"symbol": "IDEA", "token": "14366", "base_price": 14.2},
    {"symbol": "YESBANK", "token": "11915", "base_price": 24.5},
    {"symbol": "SUZLON", "token": "13786", "base_price": 68.0},
    {"symbol": "PNB", "token": "10666", "base_price": 112.0},
    {"symbol": "IOC", "token": "1624", "base_price": 178.0},
    {"symbol": "SAIL", "token": "2963", "base_price": 132.0},
    {"symbol": "BANKBARODA", "token": "4668", "base_price": 245.0},
    {"symbol": "NHPC", "token": "17921", "base_price": 88.0},
    {"symbol": "GAIL", "token": "4717", "base_price": 205.0},
    {"symbol": "NATIONALUM", "token": "6364", "base_price": 195.0},
    {"symbol": "ONGC", "token": "2475", "base_price": 265.0},
    {"symbol": "RVNL", "token": "9552", "base_price": 420.0},
    {"symbol": "HUDCO", "token": "20825", "base_price": 210.0},
    {"symbol": "IRFC", "token": "24040", "base_price": 155.0},
    {"symbol": "CANBK", "token": "2555", "base_price": 108.0},
    {"symbol": "UNIONBANK", "token": "10794", "base_price": 128.0},
    {"symbol": "TATASTEEL", "token": "3499", "base_price": 158.0},
    {"symbol": "VEDL", "token": "3063", "base_price": 445.0},
    {"symbol": "ZOMATO", "token": "5097", "base_price": 245.0},
]
