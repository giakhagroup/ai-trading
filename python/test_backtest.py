import unittest
import sys
import os
import time

# Add python root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from models import (
    CanonicalCandle,
    CandidateSignal,
    ValidatedSignal,
    SignalDirection,
    SessionType
)
from engine.indicators import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_macd
)
from engine.mtf_manager import MTFManager
from engine.historical_data_loader import HistoricalDataLoader
from engine.backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    Position
)
from strategies.mtf_trend_pullback import MTFTrendPullbackStrategy
from risk.risk_engine import RiskEngine

class TestTechnicalIndicators(unittest.TestCase):
    def test_sma_ema_calculation(self):
        prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        sma3 = calculate_sma(prices, 3)
        self.assertEqual(sma3[2], 11.0)
        self.assertEqual(sma3[5], 14.0)

        ema3 = calculate_ema(prices, 3)
        self.assertEqual(ema3[2], 11.0)
        self.assertGreater(ema3[5], 13.0)

    def test_rsi_bounds(self):
        # Monotonically increasing prices -> RSI should be high
        up_prices = [float(i) for i in range(100, 130)]
        rsi = calculate_rsi(up_prices, 14)
        self.assertGreater(rsi[-1], 90.0)

        # Monotonically decreasing prices -> RSI should be low
        down_prices = [float(i) for i in range(130, 100, -1)]
        rsi_down = calculate_rsi(down_prices, 14)
        self.assertLess(rsi_down[-1], 10.0)

    def test_atr_positive(self):
        highs = [105.0, 106.0, 108.0, 107.0, 110.0] * 5
        lows = [95.0, 94.0, 96.0, 95.0, 98.0] * 5
        closes = [100.0, 102.0, 101.0, 105.0, 104.0] * 5
        atr = calculate_atr(highs, lows, closes, 5)
        self.assertGreater(atr[-1], 0)


class TestMTFManagerAndCausality(unittest.TestCase):
    def test_look_ahead_bias_prevention(self):
        """
        V2.0-026 Gate:
        Ensure that when evaluating lower timeframe candle at timestamp T,
        higher timeframe candles occurring after T are NOT visible to the engine.
        """
        symbol = "HOSE:FPT"
        mtf = MTFManager(symbol, supported_timeframes=["5", "60"])

        # Feed 3 H1 candles at t=3600, t=7200, t=10800
        for i, t in enumerate([3600, 7200, 10800]):
            c = CanonicalCandle(
                event_id=f"h1_{i}",
                provider="Test",
                provider_symbol=symbol,
                internal_symbol=symbol,
                exchange="HOSE",
                asset_class="STOCK",
                timeframe="60",
                source_timestamp=t,
                open=70000.0 + i * 1000,
                high=71000.0 + i * 1000,
                low=69000.0 + i * 1000,
                close=70500.0 + i * 1000,
                volume=10000
            )
            mtf.on_candle(c)

        # As of timestamp 5000 (between t=3600 and t=7200), only 1 H1 bar should be visible
        h1_bars_at_5000 = mtf.get_candles("60", as_of_timestamp=5000)
        self.assertEqual(len(h1_bars_at_5000), 1)
        self.assertEqual(h1_bars_at_5000[0].source_timestamp, 3600)

        # As of timestamp 8000, exactly 2 H1 bars should be visible
        h1_bars_at_8000 = mtf.get_candles("60", as_of_timestamp=8000)
        self.assertEqual(len(h1_bars_at_8000), 2)
        self.assertEqual(h1_bars_at_8000[-1].source_timestamp, 7200)


class TestBacktestExecutionAndAccounting(unittest.TestCase):
    def test_execution_fees_and_pnl(self):
        """
        V2.0-025: Verify exact calculation of Slippage, Commission, and Tax.
        """
        config = BacktestConfig(
            initial_capital=100_000_000.0,
            commission_rate=0.0015, # 0.15%
            sell_tax_rate=0.0010,   # 0.10%
            slippage_rate=0.0005,   # 0.05%
            max_position_size_pct=0.50 # 50%
        )
        engine = BacktestEngine(config)
        
        signal = CandidateSignal(
            signal_id="sig_test",
            strategy_name="Test",
            symbol="HOSE:FPT",
            timeframe="5",
            direction=SignalDirection.LONG,
            entry_price=100_000.0,
            stop_loss=95_000.0,
            take_profit=110_000.0,
            candle_timestamp=1000
        )
        validated = ValidatedSignal(
            signal=signal,
            risk_score=1.0,
            risk_reward_ratio=2.0
        )
        
        candle_entry = CanonicalCandle(
            event_id="e1",
            internal_symbol="HOSE:FPT",
            timeframe="5",
            source_timestamp=1000,
            open=100_000.0,
            high=101_000.0,
            low=99_000.0,
            close=100_000.0,
            volume=10000
        )
        
        pos = engine.execute_order(validated, candle_entry)
        self.assertIsNotNone(pos)
        
        # Expected Entry Price = 100,000 * 1.0005 = 100,050.0
        self.assertEqual(pos.entry_price, 100_050.0)
        self.assertGreater(pos.shares, 0)
        self.assertEqual(pos.shares % 100, 0) # VN 100-lot round

        # Candle triggers Take Profit
        candle_exit = CanonicalCandle(
            event_id="e2",
            internal_symbol="HOSE:FPT",
            timeframe="5",
            source_timestamp=2000,
            open=105_000.0,
            high=111_000.0, # Breaches TP of 110,000
            low=104_000.0,
            close=110_500.0,
            volume=10000
        )
        engine.update_positions(candle_exit)
        self.assertEqual(len(engine.positions), 0)
        self.assertEqual(len(engine.closed_positions), 1)

        closed = engine.closed_positions[0]
        self.assertEqual(closed.exit_reason, "TAKE_PROFIT")
        self.assertGreater(closed.pnl, 0.0)

        metrics = engine.calculate_metrics()
        self.assertEqual(metrics.total_trades, 1)
        self.assertEqual(metrics.winning_trades, 1)
        self.assertEqual(metrics.win_rate_pct, 100.0)
        self.assertGreater(metrics.net_profit, 0)


class TestFullMTFBacktestSimulation(unittest.TestCase):
    def test_full_mtf_strategy_backtest_run(self):
        """
        Full End-to-End Simulation:
        Generate 1,000 M5 bars + synchronized H1 bars.
        Stream bars into MTFManager, evaluate MTFTrendPullbackStrategy, validate via RiskEngine,
        and execute orders in BacktestEngine.
        """
        symbol = "HOSE:FPT"
        m5_candles, h1_candles = HistoricalDataLoader.generate_synthetic_candles(
            symbol=symbol,
            base_price=70000.0,
            num_m5_bars=4000,
            trend_drift=0.00005,
            volatility=0.003
        )

        mtf = MTFManager(symbol, supported_timeframes=["5", "60"])
        strategy = MTFTrendPullbackStrategy(mtf, htf_timeframe="60", ltf_timeframe="5", rsi_pullback_threshold=100.0)
        risk_engine = RiskEngine(min_rr=1.5, allow_lunch_trades=True)
        engine = BacktestEngine(BacktestConfig(initial_capital=100_000_000.0, max_position_size_pct=0.25))

        h1_index = 0
        h1_count = len(h1_candles)

        # Bar-by-Bar Replay Simulation
        for m5 in m5_candles:
            # Synchronize closed H1 candles up to m5.source_timestamp
            while h1_index < h1_count and h1_candles[h1_index].source_timestamp <= m5.source_timestamp:
                mtf.on_candle(h1_candles[h1_index])
                h1_index += 1

            # Ingest M5 candle
            mtf.on_candle(m5)

            # 1. Update open positions (Check SL/TP)
            engine.update_positions(m5)

            # 2. Strategy evaluation
            candidate = strategy.evaluate(m5)
            if candidate:
                decision = risk_engine.validate(candidate, current_session=SessionType.CONTINUOUS)
                if isinstance(decision, ValidatedSignal):
                    engine.execute_order(decision, m5)

            # 3. Record equity curve snapshot
            engine.record_equity(m5.source_timestamp, {symbol: m5.close})

        metrics = engine.calculate_metrics()
        
        # Output Summary
        print(f"\n==================================================")
        print(f"📊 BACKTEST SIMULATION RESULTS ({symbol} - 4,000 Bars)")
        print(f"==================================================")
        print(f"Initial Capital   : {metrics.initial_capital:,.0f} VND")
        print(f"Final Equity      : {metrics.final_equity:,.0f} VND")
        print(f"Net Profit        : {metrics.net_profit:,.0f} VND ({metrics.net_profit_pct:+.2f}%)")
        print(f"Total Trades      : {metrics.total_trades} (Wins: {metrics.winning_trades}, Losses: {metrics.losing_trades})")
        print(f"Win Rate          : {metrics.win_rate_pct:.2f}%")
        print(f"Profit Factor     : {metrics.profit_factor:.2f}")
        print(f"Max Drawdown      : {metrics.max_drawdown:,.0f} VND ({metrics.max_drawdown_pct:.2f}%)")
        print(f"Sharpe Ratio      : {metrics.sharpe_ratio:.2f}")
        print(f"==================================================\n")

        self.assertGreater(metrics.total_trades, 0, "Strategy should have generated at least 1 trade during 4,000 bars")
        self.assertGreater(metrics.final_equity, 0)

if __name__ == '__main__':
    unittest.main()
