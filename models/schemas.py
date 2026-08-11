from pydantic import BaseModel
from typing import Optional


class CrossoverSignal(BaseModel):
    signal_type: str
    accepted: bool
    confidence: float


class StockRow(BaseModel):
    symbol: str
    ltp: float
    bid_price: Optional[float]
    bid_qty: Optional[int]
    ask_price: Optional[float]
    ask_qty: Optional[int]
    smma_fast: Optional[float]
    smma_slow: Optional[float]
    traded_qty_5m: int
    traded_qty_20m: int
    traded_qty_60m: int
    avg_ltp_20m: float
    avg_ltp_60m: float
    action: str
    probability: float
    risk: str
    trend: str
    crossover_signal: Optional[CrossoverSignal] = None
    ai_confidence: float
    trade_quality: float
    momentum: float
    buying_pressure: float
    selling_pressure: float
    liquidity_score: float
    opportunity_rating: float
    confluence_score: float


class LongTermPick(BaseModel):
    symbol: str
    status: str          # always "WELL POSITIONED" - only rule-qualified picks are returned
    ltp: float
    action: str
    trend: str
    ai_confidence: float
    risk: str
    momentum: float
    avg_ltp_20m: float
    avg_ltp_60m: float
    traded_qty_60m: int

