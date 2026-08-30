from typing import Dict, List, Optional, Any
import math
from models import CanonicalCandle
from engine.indicators import (
    calculate_ema,
    calculate_sma,
    calculate_rsi,
    calculate_atr,
    calculate_macd
)

class TimeframeState:
    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        self.candles: List[CanonicalCandle] = []
        
        # Indicator caches
        self.closes: List[float] = []
        self.highs: List[float] = []
        self.lows: List[float] = []
        self.volumes: List[float] = []
        self.timestamps: List[int] = []
        self.event_ids: List[str] = []

    def append_candle(self, candle: CanonicalCandle):
        self.candles.append(candle)
        self.closes.append(candle.close)
        self.highs.append(candle.high)
        self.lows.append(candle.low)
        self.volumes.append(candle.volume)
        self.timestamps.append(candle.source_timestamp)
        self.event_ids.append(candle.event_id)

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

    def get_indicators(self, timeframe: str, as_of_timestamp: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate and return standard indicator snapshot for a given timeframe as of timestamp T.
        """
        state = self.tf_states.get(timeframe)
        if not state or not state.candles:
            return {}

        if as_of_timestamp is not None:
            idx = 0
            while idx < len(state.timestamps) and state.timestamps[idx] <= as_of_timestamp:
                idx += 1
            closes = state.closes[:idx]
            highs = state.highs[:idx]
            lows = state.lows[:idx]
            volumes = state.volumes[:idx]
            event_ids = state.event_ids[:idx]
        else:
            closes = state.closes
            highs = state.highs
            lows = state.lows
            volumes = state.volumes
            event_ids = state.event_ids

        if not closes:
            return {}

        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50)
        ema200 = calculate_ema(closes, 200)
        rsi14 = calculate_rsi(closes, 14)
        atr14 = calculate_atr(highs, lows, closes, 14)
        macd = calculate_macd(closes, 12, 26, 9)
        sma20_vol = calculate_sma(volumes, 20)

        latest_idx = len(closes) - 1
        latest_candle = state.candles[latest_idx]
        tv_inds = latest_candle.indicators or {}

        def safe_val(arr: List[float], fallback_key: str) -> Optional[float]:
            # Use TV indicator if available
            if fallback_key in tv_inds and tv_inds[fallback_key] is not None:
                return float(tv_inds[fallback_key])
            if not arr or latest_idx >= len(arr):
                return None
            val = arr[latest_idx]
            return None if math.isnan(val) else round(val, 4)

        return {
            "close": closes[latest_idx],
            "volume": volumes[latest_idx],
            "ema20": safe_val(ema20, "ema20"),
            "ema50": safe_val(ema50, "ema50"),
            "ema200": safe_val(ema200, "ema200"),
            "rsi14": safe_val(rsi14, "rsi14"),
            "atr14": safe_val(atr14, "atr14"),
            "macd": safe_val(macd["macd"] if macd else [], "macd"),
            "macd_signal": safe_val(macd["signal"] if macd else [], "macd_signal"),
            "macd_hist": safe_val(macd["hist"] if macd else [], "macd_hist"),
            "sma20_vol": safe_val(sma20_vol, "sma20_vol"),
            "bar_count": len(closes),
            "event_id": event_ids[latest_idx] if latest_idx < len(event_ids) else "unknown_event_id"
        }

    def get_trend_state(self, timeframe: str = "60", as_of_timestamp: Optional[int] = None) -> str:
        """
        Determine higher-timeframe trend state:
        - UPTREND: Close > EMA20 > EMA50
        - DOWNTREND: Close < EMA20 < EMA50
        - SIDEWAYS / NEUTRAL
        """
        inds = self.get_indicators(timeframe, as_of_timestamp)
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
