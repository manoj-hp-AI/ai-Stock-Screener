from pydantic import BaseModel
from typing import Optional


class CrossoverSignal(BaseModel):
    symbol: str
    signal_type: str
    accepted: bool
    confidence: float
    reason: str
    smma_fast: float
    smma_slow: float


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
    ai_confidence: float
    trade_quality: float
    momentum: float
    buying_pressure: float
    selling_pressure: float
    liquidity_score: float
    opportunity_rating: float
    confluence_score: float
    ai_explanation: str


class LongTermPick(BaseModel):
    symbol: str
    qualified: bool
    promoter_holding: float
    fii_holding: float
    dii_holding: float
    retail_holding: float
    retail_q1: float
    retail_q2: float
    retail_q3: float
    ownership_trend: str
    reason: str
