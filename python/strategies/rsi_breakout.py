import uuid
from typing import Optional
from models import CanonicalCandle, CandidateSignal, SignalDirection
from strategies.base import IStrategy

class RSIBreakoutStrategy(IStrategy):
    """
    Example Strategy:
    Uses TradingView's attached RSI study indicator.
    - Long condition: RSI crosses above 50 (or is oversold < 30 turning up) and close > open.
    - Short condition: RSI > 70 or crosses below 50.
    """
    def __init__(self, rsi_oversold: float = 35.0, rsi_overbought: float = 70.0):
        self._name = "RSI_Breakout_Strategy"
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, candle: CanonicalCandle) -> Optional[CandidateSignal]:
        # Check if indicators are attached from TradingView study
        rsi_val = candle.indicators.get("RSI")
        if rsi_val is None:
            # Fallback or check if 'Plot' or direct study value is passed
            rsi_val = candle.indicators.get("Plot")

        if rsi_val is None:
            return None

        # Simple condition demonstration:
        # LONG if RSI < 35 (Oversold reversal candidate)
        if rsi_val <= self.rsi_oversold and candle.close >= candle.open:
            entry = candle.close
            stop_loss = candle.low * 0.98  # 2% stop loss
            risk = entry - stop_loss
            take_profit = entry + (risk * 2.0) # 1:2 R:R target

            return CandidateSignal(
                signal_id=f"sig_{uuid.uuid4().hex[:8]}",
                strategy_name=self.name,
                symbol=candle.internal_symbol,
                timeframe=candle.timeframe,
                direction=SignalDirection.LONG,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                score=0.85,
                confidence=0.9,
                evidence={
                    "rsi": rsi_val,
                    "candle_close": candle.close,
                    "condition": "RSI_Oversold_Bullish_Candle"
                },
                candle_timestamp=candle.source_timestamp
            )

        return None
