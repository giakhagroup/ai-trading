import unittest
import time
import sys
import os

# Add python dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from models import (
    CandidateSignal,
    SignalDirection,
    SignalStatus,
    SessionType,
    ValidatedSignal,
    RejectedSignal,
    CanonicalCandle
)
from strategies.rsi_breakout import RSIBreakoutStrategy
from risk.risk_engine import RiskEngine

class TestQuantAndRiskEngine(unittest.TestCase):
    def test_rsi_breakout_strategy_generates_candidate(self):
        strategy = RSIBreakoutStrategy(rsi_oversold=35.0)
        
        candle = CanonicalCandle(
            event_id="test-1",
            provider="TradingView",
            provider_symbol="HOSE:FPT",
            internal_symbol="HOSE:FPT",
            exchange="HOSE",
            asset_class="STOCK",
            timeframe="1",
            source_timestamp=int(time.time()),
            event_timestamp=int(time.time()),
            received_at=int(time.time()),
            processed_at=int(time.time()),
            open=72000,
            high=72500,
            low=71800,
            close=72300,
            volume=100000,
            indicators={"RSI": 28.5}
        )
        
        signal = strategy.evaluate(candle)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.direction, SignalDirection.LONG)
        self.assertEqual(signal.symbol, "HOSE:FPT")
        self.assertEqual(signal.entry_price, 72300)
        self.assertGreater(signal.take_profit, signal.entry_price)

    def test_risk_engine_validates_healthy_signal(self):
        risk_engine = RiskEngine(min_rr=1.5, allow_lunch_trades=False)
        
        candidate = CandidateSignal(
            signal_id="sig_test_1",
            strategy_name="RSI_Breakout_Strategy",
            symbol="HOSE:FPT",
            timeframe="1",
            direction=SignalDirection.LONG,
            entry_price=100.0,
            stop_loss=98.0,      # Risk = 2.0
            take_profit=104.0,   # Reward = 4.0 (R:R = 2.0 >= 1.5)
            candle_timestamp=int(time.time())
        )
        
        decision = risk_engine.validate(candidate, current_session=SessionType.CONTINUOUS)
        self.assertIsInstance(decision, ValidatedSignal)
        self.assertEqual(decision.risk_reward_ratio, 2.0)

    def test_risk_engine_rejects_poor_rr_and_lunch_session(self):
        risk_engine = RiskEngine(min_rr=1.5, allow_lunch_trades=False)
        
        # Low R:R candidate
        candidate_low_rr = CandidateSignal(
            signal_id="sig_test_2",
            strategy_name="RSI_Breakout_Strategy",
            symbol="HOSE:FPT",
            timeframe="1",
            direction=SignalDirection.LONG,
            entry_price=100.0,
            stop_loss=98.0,      # Risk = 2.0
            take_profit=101.0,   # Reward = 1.0 (R:R = 0.5 < 1.5)
            candle_timestamp=int(time.time())
        )
        decision = risk_engine.validate(candidate_low_rr, current_session=SessionType.CONTINUOUS)
        self.assertIsInstance(decision, RejectedSignal)
        self.assertTrue(any("R:R ratio" in r for r in decision.rejection_reasons))

        # Valid R:R but inside LUNCH session
        candidate_valid_rr = CandidateSignal(
            signal_id="sig_test_3",
            strategy_name="RSI_Breakout_Strategy",
            symbol="HOSE:FPT",
            timeframe="1",
            direction=SignalDirection.LONG,
            entry_price=100.0,
            stop_loss=98.0,
            take_profit=105.0,
            candle_timestamp=int(time.time())
        )
        decision_lunch = risk_engine.validate(candidate_valid_rr, current_session=SessionType.LUNCH)
        self.assertIsInstance(decision_lunch, RejectedSignal)
        self.assertTrue(any("LUNCH" in r for r in decision_lunch.rejection_reasons))

if __name__ == '__main__':
    unittest.main()
