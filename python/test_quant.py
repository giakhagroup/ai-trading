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
    CanonicalCandle,
    RiskDecision
)
from strategies.rsi_breakout import RSIBreakoutStrategy
from risk.risk_engine import RiskEngine

class TestStrategyLogic(unittest.TestCase):
    def setUp(self):
        self.strategy = RSIBreakoutStrategy(rsi_oversold=35.0, rsi_overbought=70.0)

    def test_oversold_green_candle_emits_long_candidate(self):
        """Candle with RSI <= 35 and Close >= Open must generate LONG candidate"""
        candle = CanonicalCandle(
            event_id="test-green-oversold",
            provider="TradingView",
            provider_symbol="HOSE:FPT",
            internal_symbol="HOSE:FPT",
            exchange="HOSE",
            asset_class="STOCK",
            timeframe="1",
            source_timestamp=1700000000,
            open=72000,
            high=72500,
            low=71500,
            close=72300, # Green candle
            volume=10000,
            indicators={"RSI": 32.0} # Oversold
        )
        signal = self.strategy.evaluate(candle)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.direction, SignalDirection.LONG)
        self.assertEqual(signal.status, SignalStatus.CANDIDATE)
        self.assertEqual(signal.entry_price, 72300)
        self.assertEqual(signal.stop_loss, 71500 * 0.98)
        self.assertGreater(signal.take_profit, signal.entry_price)
        self.assertEqual(signal.evidence.get("condition"), "RSI_Oversold_Bullish_Candle")

    def test_oversold_red_candle_does_not_emit_candidate(self):
        """Candle with RSI <= 35 but Close < Open (still falling) must NOT trigger early LONG"""
        candle = CanonicalCandle(
            event_id="test-red-oversold",
            open=73000,
            high=73000,
            low=71500,
            close=72000, # Red candle
            volume=10000,
            indicators={"RSI": 30.0}
        )
        signal = self.strategy.evaluate(candle)
        self.assertIsNone(signal)

    def test_neutral_rsi_does_not_emit_candidate(self):
        """RSI in normal range (e.g. 50) must not emit any candidate signal"""
        candle = CanonicalCandle(
            event_id="test-neutral",
            open=72000,
            high=72500,
            low=71900,
            close=72200,
            volume=10000,
            indicators={"RSI": 52.0}
        )
        signal = self.strategy.evaluate(candle)
        self.assertIsNone(signal)

    def test_missing_indicator_gracefully_returns_none(self):
        """Candle without RSI indicator attached must not crash and return None"""
        candle = CanonicalCandle(
            event_id="test-no-indicator",
            open=72000,
            close=72200,
            indicators={}
        )
        signal = self.strategy.evaluate(candle)
        self.assertIsNone(signal)


class TestRiskEngineBoundaries(unittest.TestCase):
    def setUp(self):
        self.risk_engine = RiskEngine(min_rr=1.5, allow_lunch_trades=False, max_loss_pct=0.07)

    def test_valid_long_trade_approved(self):
        """Valid LONG with R:R = 2.0 (>= 1.5) during CONTINUOUS session should be Approved"""
        candidate = CandidateSignal(
            signal_id="sig_long_ok",
            strategy_name="RSI_Breakout_Strategy",
            symbol="HOSE:TCB",
            timeframe="5",
            direction=SignalDirection.LONG,
            entry_price=50.0,
            stop_loss=48.0,      # Risk = 2.0 (4%) <= 7% max loss
            take_profit=54.0,   # Reward = 4.0 -> R:R = 2.0
            candle_timestamp=1700000000
        )
        decision = self.risk_engine.validate(candidate, current_session=SessionType.CONTINUOUS)
        self.assertIsInstance(decision, ValidatedSignal)
        self.assertEqual(decision.decision, RiskDecision.APPROVE)
        self.assertEqual(decision.status, SignalStatus.VALIDATED)
        self.assertEqual(decision.risk_reward_ratio, 2.0)

    def test_valid_short_trade_approved(self):
        """Valid SHORT with R:R = 2.0 should be Approved"""
        candidate = CandidateSignal(
            signal_id="sig_short_ok",
            strategy_name="Short_Strategy",
            symbol="VN30F1M",
            timeframe="1",
            direction=SignalDirection.SHORT,
            entry_price=1000.0,
            stop_loss=1010.0,    # Risk = 10.0
            take_profit=980.0,   # Reward = 20.0 -> R:R = 2.0
            candle_timestamp=1700000000
        )
        decision = self.risk_engine.validate(candidate, current_session=SessionType.CONTINUOUS)
        self.assertIsInstance(decision, ValidatedSignal)
        self.assertEqual(decision.risk_reward_ratio, 2.0)

    def test_reject_when_rr_below_minimum(self):
        """Signal with R:R < 1.5 must be REJECTED"""
        candidate = CandidateSignal(
            signal_id="sig_poor_rr",
            strategy_name="Scalp",
            symbol="HOSE:HPG",
            timeframe="1",
            direction=SignalDirection.LONG,
            entry_price=30.0,
            stop_loss=29.0,      # Risk = 1.0
            take_profit=31.2,   # Reward = 1.2 -> R:R = 1.2 < 1.5
            candle_timestamp=1700000000
        )
        decision = self.risk_engine.validate(candidate, current_session=SessionType.CONTINUOUS)
        self.assertIsInstance(decision, RejectedSignal)
        self.assertEqual(decision.status, SignalStatus.REJECTED)
        self.assertTrue(any("lower than minimum required" in r for r in decision.rejection_reasons))

    def test_reject_when_sl_on_wrong_side(self):
        """LONG signal with Stop Loss above Entry must be REJECTED"""
        candidate = CandidateSignal(
            signal_id="sig_inverted_sl",
            strategy_name="BuggyStrategy",
            symbol="HOSE:VNM",
            timeframe="1",
            direction=SignalDirection.LONG,
            entry_price=70.0,
            stop_loss=72.0,      # Bug: SL > Entry
            take_profit=80.0,
            candle_timestamp=1700000000
        )
        decision = self.risk_engine.validate(candidate, current_session=SessionType.CONTINUOUS)
        self.assertIsInstance(decision, RejectedSignal)
        self.assertTrue(any("Stop Loss must be lower than Entry price" in r for r in decision.rejection_reasons))

    def test_reject_excessive_stoploss_distance(self):
        """Signal with SL distance exceeding max_loss_pct (7%) must be REJECTED"""
        candidate = CandidateSignal(
            signal_id="sig_huge_risk",
            strategy_name="HighRiskStrategy",
            symbol="HOSE:VIC",
            timeframe="15",
            direction=SignalDirection.LONG,
            entry_price=100.0,
            stop_loss=90.0,      # Risk = 10.0 (10% > 7%)
            take_profit=130.0,  # Reward = 30.0 (R:R = 3.0)
            candle_timestamp=1700000000
        )
        decision = self.risk_engine.validate(candidate, current_session=SessionType.CONTINUOUS)
        self.assertIsInstance(decision, RejectedSignal)
        self.assertTrue(any("exceeds maximum allowable risk limit" in r for r in decision.rejection_reasons))

    def test_reject_during_special_sessions(self):
        """Signals during LUNCH, ATO, or ATC must be REJECTED"""
        candidate = CandidateSignal(
            signal_id="sig_session_test",
            strategy_name="Breakout",
            symbol="HOSE:FPT",
            timeframe="1",
            direction=SignalDirection.LONG,
            entry_price=100.0,
            stop_loss=98.0,
            take_profit=106.0,
            candle_timestamp=1700000000
        )
        # Test Lunch rejection
        res_lunch = self.risk_engine.validate(candidate, current_session=SessionType.LUNCH)
        self.assertIsInstance(res_lunch, RejectedSignal)
        self.assertTrue(any("LUNCH" in r for r in res_lunch.rejection_reasons))

        # Test ATO rejection
        res_ato = self.risk_engine.validate(candidate, current_session=SessionType.ATO)
        self.assertIsInstance(res_ato, RejectedSignal)
        self.assertTrue(any("ATO" in r for r in res_ato.rejection_reasons))

        # Test ATC rejection
        res_atc = self.risk_engine.validate(candidate, current_session=SessionType.ATC)
        self.assertIsInstance(res_atc, RejectedSignal)
        self.assertTrue(any("ATC" in r for r in res_atc.rejection_reasons))


class TestDataSerialization(unittest.TestCase):
    def test_canonical_candle_roundtrip_dict(self):
        """Test CanonicalCandle serialization and deserialization integrity"""
        candle = CanonicalCandle(
            event_id="evt_123",
            provider="TradingView",
            provider_symbol="HOSE:MWG",
            internal_symbol="HOSE:MWG",
            exchange="HOSE",
            asset_class="STOCK",
            currency="VND",
            timeframe="5",
            source_timestamp=1700000000,
            open=55000.0,
            high=56000.0,
            low=54500.0,
            close=55800.0,
            volume=500000.0,
            indicators={"RSI": 45.2, "EMA20": 55100.0}
        )
        data = candle.model_dump()
        self.assertEqual(data["internal_symbol"], "HOSE:MWG")
        self.assertEqual(data["indicators"]["RSI"], 45.2)

        restored = CanonicalCandle(**data)
        self.assertEqual(restored.close, 55800.0)
        self.assertEqual(restored.indicators["EMA20"], 55100.0)

if __name__ == '__main__':
    unittest.main()
