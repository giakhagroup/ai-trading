from typing import Dict, List, Optional, Any
import math
from models import CanonicalCandle, IndicatorPayload, IndicatorQuality, IndicatorProvenance
from engine.indicator_engine import TimeframeIndicatorState

class TimeframeState:
    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        self.candles: List[CanonicalCandle] = []
        
        self.indicator_state = TimeframeIndicatorState(timeframe)
        self.latest_payload: Optional[IndicatorPayload] = None

    def append_candle(self, candle: CanonicalCandle):
        self.candles.append(candle)
        # We only pass is_closed=True if the candle is actually closed, 
        # or if it's a historical candle being backfilled.
        # But wait, MTFManager gets called on every tick.
        # So we pass is_closed=candle.is_closed.
        self.latest_payload = self.indicator_state.update(
            candle.open, candle.high, candle.low, candle.close, candle.volume, candle.source_timestamp, candle.is_closed
        )

    def get_latest_candle(self) -> Optional[CanonicalCandle]:
        return self.candles[-1] if self.candles else None


class MTFManager:
    """
    V2.0-026 & V2.0-027: Multi-Timeframe Manager
    Enforces cross-timeframe synchronization without look-ahead bias.
    """
    def __init__(self, symbol: str, supported_timeframes: List[str] = None):
        self.symbol = symbol
        self.supported_timeframes = supported_timeframes or ["1", "5", "15", "60", "D"]
        self.tf_states: Dict[str, TimeframeState] = {
            tf: TimeframeState(tf) for tf in self.supported_timeframes
        }

    def on_candle(self, candle: CanonicalCandle):
        """Register an incoming candle for its timeframe."""
        tf = str(candle.timeframe)
        if tf not in self.tf_states:
            self.tf_states[tf] = TimeframeState(tf)
        
        self.tf_states[tf].append_candle(candle)

    def get_candles(self, timeframe: str, as_of_timestamp: Optional[int] = None) -> List[CanonicalCandle]:
        """
        Get closed candles for a given timeframe.
        If as_of_timestamp is provided, ensures only candles closed <= as_of_timestamp are returned.
        """
        state = self.tf_states.get(timeframe)
        if not state:
            return []
            
        if as_of_timestamp is None:
            return state.candles
            
        # Binary search or filter for causality (look-ahead bias prevention)
        valid_candles = [
            c for c in state.candles if c.source_timestamp <= as_of_timestamp
        ]
        return valid_candles

    def get_indicators(self, timeframe: str, as_of_timestamp: Optional[int] = None) -> Optional[IndicatorPayload]:
        """
        Return the precalculated indicator payload for a given timeframe.
        Note: If as_of_timestamp is in the past, it currently returns None
        as the incremental state only holds the latest. For backtesting,
        we would replay tick by tick, so latest is always correct.
        """
        state = self.tf_states.get(timeframe)
        if not state or not state.candles:
            return None

        # For strict historical querying (not fully supported by pure incremental yet without full replay)
        if as_of_timestamp is not None:
            latest = state.get_latest_candle()
            if latest and latest.source_timestamp > as_of_timestamp:
                print(f"Returning None because {latest.source_timestamp} > {as_of_timestamp}"); return None

        return state.latest_payload

    def get_trend_state(self, timeframe: str = "60", as_of_timestamp: Optional[int] = None) -> str:
        """
        Determine higher-timeframe trend state:
        - UPTREND: Close > EMA20 > EMA50
        - DOWNTREND: Close < EMA20 < EMA50
        - SIDEWAYS / NEUTRAL
        """
        payload = self.get_indicators(timeframe, as_of_timestamp)
        if not payload or payload.quality in (IndicatorQuality.STALE, IndicatorQuality.MISSING, IndicatorQuality.WARMUP):
            return "UNKNOWN"
            
        inds = payload.values
        close = inds.get("close")
        ema20 = inds.get("ema20")
        ema50 = inds.get("ema50")

        if close is None or ema20 is None or ema50 is None:
            return "UNKNOWN"

        if close > ema20 and ema20 > ema50:
            return "UPTREND"
        elif close < ema20 and ema20 < ema50:
            return "DOWNTREND"
        return "SIDEWAYS"
