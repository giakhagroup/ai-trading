from pydantic import BaseModel, Field
from typing import List, Optional

class ScanResult(BaseModel):
    symbol: str
    correlation_id: str
    score: float = Field(..., ge=0, le=100)
    trend: str  # "UPTREND", "DOWNTREND", "SIDEWAYS", "UNKNOWN"
    momentum: float  # e.g., RSI value
    rvol: Optional[float] = None
    matched_criteria: List[str] = []
    
    # Optional fields for deeper analysis
    close: float
    volume: float
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    ema200: Optional[float] = None

    # Phase 8A specific fields for alert thresholding
    total_score: float = 0
    trend_score: float = 0
    momentum_score: float = 0
    mtf_score: float = 0
    trend_state: str = "UNKNOWN"
    data_quality: str = "VALID"
