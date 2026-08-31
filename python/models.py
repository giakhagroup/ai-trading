from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import time

class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class SignalStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    ACTIVE = "ACTIVE"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"

class SessionType(str, Enum):
    ATO = "ATO"
    CONTINUOUS = "CONTINUOUS"
    LUNCH = "LUNCH"
    ATC = "ATC"
    NEGOTIATED = "NEGOTIATED"

class IndicatorQuality(str, Enum):
    VALID = "VALID"
    WARMUP = "WARMUP"
    STALE = "STALE"
    MISSING = "MISSING"

class IndicatorProvenance(BaseModel):
    source: str = "LOCAL"
    calculation_version: str = "1.0"
    input_timeframe: str
    calculated_at: int = Field(default_factory=lambda: int(time.time() * 1000))

class IndicatorPayload(BaseModel):
    values: Dict[str, Any]
    quality: IndicatorQuality
    provenance: IndicatorProvenance

class CanonicalCandle(BaseModel):
    event_id: Optional[str] = "event_default"
    provider: Optional[str] = "TradingView"
    provider_symbol: Optional[str] = "UNKNOWN"
    internal_symbol: Optional[str] = "UNKNOWN"
    exchange: Optional[str] = "UNKNOWN"
    asset_class: Optional[str] = "STOCK"
    currency: Optional[str] = "VND"
    timezone: Optional[str] = "Asia/Ho_Chi_Minh"
    timeframe: Optional[str] = "1"

    source_timestamp: Optional[int] = 0
    event_timestamp: Optional[int] = 0
    received_at: Optional[int] = 0
    processed_at: Optional[int] = 0

    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0

    is_closed: bool = False
    sequence: int = 0
    revision: int = 0
    quality_status: str = "REALTIME"
    quality_score: float = 1.0

    session_type: Optional[SessionType] = SessionType.CONTINUOUS
    is_auction: Optional[bool] = False

    # V2.0-010: Attached Studies / Indicator snapshot from TradingView
    indicators: Dict[str, Any] = Field(default_factory=dict)

class CandidateSignal(BaseModel):
    signal_id: str
    strategy_name: str
    symbol: str
    timeframe: str
    direction: SignalDirection
    status: SignalStatus = SignalStatus.CANDIDATE
    
    entry_price: float
    stop_loss: float
    take_profit: float
    
    score: float = 1.0  # V2.0-021: Score vs Probability
    confidence: float = 1.0
    evidence: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: int = Field(default_factory=lambda: int(time.time() * 1000))
    candle_timestamp: int

class RiskDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"

class ValidatedSignal(BaseModel):
    signal: CandidateSignal
    decision: RiskDecision = RiskDecision.APPROVE
    status: SignalStatus = SignalStatus.VALIDATED
    risk_score: float
    risk_reward_ratio: float
    max_position_size: Optional[float] = None
    approved_at: int = Field(default_factory=lambda: int(time.time() * 1000))
    notes: List[str] = Field(default_factory=list)

class RejectedSignal(BaseModel):
    signal: CandidateSignal
    decision: RiskDecision = RiskDecision.REJECT
    status: SignalStatus = SignalStatus.REJECTED
    rejection_reasons: List[str]
    rejected_at: int = Field(default_factory=lambda: int(time.time() * 1000))
