import uuid
from typing import Optional
from models import CanonicalCandle, CandidateSignal, SignalDirection, SignalStatus
from strategies.base import IStrategy
from engine.mtf_manager import MTFManager

class MTFTrendPullbackStrategy(IStrategy):
    """
    V2.0-027: Multi-Timeframe Trend Pullback Strategy
    - Higher Timeframe (H1): Defines macro trend (Close > EMA20 > EMA50)
    - Lower Timeframe (M5): Finds high-probability pullback entry (RSI <= 42 & Bullish reversal bar)
    - Dynamic Risk: Stop Loss placed at swing low / 1.5 ATR, Target R:R = 1:2.0
    """
    def __init__(
        self,
        mtf_manager: MTFManager,
        htf_timeframe: str = "60",
        ltf_timeframe: str = "5",
        rsi_pullback_threshold: float = 42.0
    ):
        self._name = "MTF_Trend_Pullback_Strategy"
        self.mtf = mtf_manager
        self.htf = htf_timeframe
        self.ltf = ltf_timeframe
        self.rsi_threshold = rsi_pullback_threshold

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, candle: CanonicalCandle) -> Optional[CandidateSignal]:
        # Only evaluate trigger bars on the lower execution timeframe
        if str(candle.timeframe) != self.ltf:
            return None

        # 1. Query Macro Trend on Higher Timeframe (strictly as of candle.source_timestamp)
        htf_trend = self.mtf.get_trend_state(self.htf, as_of_timestamp=candle.source_timestamp)
        if htf_trend != "UPTREND":
            return None # Filter: Do not enter if HTF is not clear uptrend

        # 2. Query Lower Timeframe indicators
        ltf_inds = self.mtf.get_indicators(self.ltf, as_of_timestamp=candle.source_timestamp)
        rsi = ltf_inds.get("rsi14")
        atr = ltf_inds.get("atr14") or (candle.high - candle.low)

        if rsi is None or atr is None:
            return None

        # 3. Pullback Entry Condition:
        # RSI in dip/pullback zone AND current candle is a bullish reversal (Green bar)
        if rsi <= self.rsi_threshold and candle.close >= candle.open:
            entry = candle.close
            
            # Dynamic Stop Loss calculation (Swing low or 1.5 * ATR)
            sl_distance = max(entry - candle.low, 1.5 * atr)
            stop_loss = round(entry - sl_distance, 1)
            risk = entry - stop_loss
            
            if risk <= 0:
                return None
                
            # 1:2.0 Reward-to-Risk Target
            take_profit = round(entry + (risk * 2.0), 1)

            return CandidateSignal(
                signal_id=f"mtf_sig_{uuid.uuid4().hex[:8]}",
                strategy_name=self.name,
                symbol=candle.internal_symbol,
                timeframe=candle.timeframe,
                direction=SignalDirection.LONG,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                score=0.90,
                confidence=0.92,
                evidence={
                    "htf_trend": htf_trend,
                    "htf_timeframe": self.htf,
                    "ltf_rsi": rsi,
                    "ltf_atr": round(atr, 2),
                    "setup": "HTF_Uptrend_LTF_Pullback_Bullish_Reversal"
                },
                candle_timestamp=candle.source_timestamp
            )

        return None
