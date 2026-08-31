import json
import os
from typing import List, Dict, Optional
from engine.mtf_manager import MTFManager
from engine.scanner.scanner_types import ScanResult
from models import IndicatorQuality

class MarketScanner:
    def __init__(self, mtf_managers: Dict[str, MTFManager], universe_path: str = "data/universes/vn30_2026.json"):
        """
        mtf_managers: A dictionary mapping symbol to its MTFManager instance.
        """
        self.mtf_managers = mtf_managers
        self.universe = self._load_universe(universe_path)

    def _load_universe(self, path: str) -> List[str]:
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("symbols", [])
        except Exception:
            return []

    def scan(self, as_of_timestamp: Optional[int] = None, timeframe: str = "1H") -> List[ScanResult]:
        results = []
        for symbol in self.universe:
            manager = self.mtf_managers.get(symbol)
            if not manager:
                continue
            
            # Use as_of_timestamp to prevent look-ahead bias
            payload_1h = manager.get_indicators(timeframe, as_of_timestamp=as_of_timestamp)
            if not payload_1h or payload_1h.quality in (IndicatorQuality.STALE, IndicatorQuality.MISSING, IndicatorQuality.WARMUP):
                print(f"[DEBUG Scanner] Skipping {symbol} because 1H quality is {payload_1h.quality if payload_1h else 'None'}")
                continue
            inds_1h = payload_1h.values
            if not inds_1h.get("close"):
                print(f"[DEBUG Scanner] Skipping {symbol} because close is missing")
                continue

            payload_15m = manager.get_indicators("15", as_of_timestamp=as_of_timestamp)
            inds_15m = payload_15m.values if payload_15m else {}
            
            # The event_id was removed from indicator values in Phase 3. 
            # We will use correlation_id from somewhere else, or just fake it.
            correlation_id = f"{symbol}-{as_of_timestamp or 'now'}"

            result = self._evaluate_symbol(symbol, inds_1h, inds_15m, manager, as_of_timestamp, correlation_id)
            if result:
                results.append(result)
            else:
                print(f"[DEBUG Scanner] _evaluate_symbol returned None for {symbol}")

        # Deterministic Ranking: score DESC, symbol ASC
        results.sort(key=lambda x: (-x.score, x.symbol))
        return results

    def _evaluate_symbol(self, symbol: str, inds_1h: dict, inds_15m: dict, manager: MTFManager, as_of_timestamp: Optional[int], correlation_id: str) -> Optional[ScanResult]:
        close = inds_1h.get("close")
        vol = inds_1h.get("volume", 0)
        ema20 = inds_1h.get("ema20")
        ema50 = inds_1h.get("ema50")
        ema200 = inds_1h.get("ema200")
        rsi = inds_1h.get("rsi14")
        sma20_vol = inds_1h.get("sma20_vol")

        if close is None or ema20 is None or ema50 is None or ema200 is None or rsi is None:
            return None

        # 1. Trend Score (30%)
        trend_score = 50
        trend_state = "SIDEWAYS"
        if close > ema20 and ema20 > ema50 and ema50 > ema200:
            trend_score = 100
            trend_state = "UPTREND"
        elif close < ema20 and ema20 < ema50 and ema50 < ema200:
            trend_score = 0
            trend_state = "DOWNTREND"

        # 2. Momentum Score (30%)
        momentum_score = 30
        if rsi > 70:
            momentum_score = 100
        elif 50 <= rsi <= 70:
            momentum_score = 70
        elif rsi < 30:
            momentum_score = 0

        # 3. Volume/RVOL Score (20%)
        rvol = (vol / sma20_vol) if sma20_vol and sma20_vol > 0 else 0
        rvol_score = 0
        if rvol >= 2.0:
            rvol_score = 100
        elif 1.0 <= rvol < 2.0:
            rvol_score = 50

        # 4. MTF Alignment Score (20%)
        mtf_score = 0
        trend_1h = manager.get_trend_state(timeframe="1H", as_of_timestamp=as_of_timestamp)
        # Assuming we can use 15m as the lower timeframe
        trend_15m = manager.get_trend_state(timeframe="15", as_of_timestamp=as_of_timestamp)
        
        if trend_1h == trend_15m and trend_1h in ["UPTREND", "DOWNTREND"]:
            mtf_score = 100
        elif trend_1h == trend_15m and trend_1h == "SIDEWAYS":
            mtf_score = 50

        # Calculate total weighted score
        total_score = (trend_score * 0.3) + (momentum_score * 0.3) + (rvol_score * 0.2) + (mtf_score * 0.2)

        matched = []
        if trend_score == 100: matched.append("STRONG_UPTREND")
        if momentum_score == 100: matched.append("STRONG_MOMENTUM")
        if rvol_score == 100: matched.append("HIGH_RVOL")
        if mtf_score == 100: matched.append("MTF_ALIGNED")

        return ScanResult(
            symbol=symbol,
            correlation_id=correlation_id,
            score=round(total_score, 2),
            trend=trend_state,
            momentum=round(rsi, 2),
            rvol=round(rvol, 2),
            matched_criteria=matched,
            close=close,
            volume=vol,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200
        )
