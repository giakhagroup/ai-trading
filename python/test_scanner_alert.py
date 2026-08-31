import os
import time
import pytest
import sqlite3
import shutil
from unittest.mock import patch, MagicMock

from models import CanonicalCandle, IndicatorPayload, IndicatorQuality, IndicatorProvenance
from engine.mtf_manager import MTFManager
from engine.scanner.scanner_types import ScanResult
from engine.scanner.market_scanner import MarketScanner

from alert.outbox_models import OutboxRepository, AlertEvent, AlertStatus
from alert.rate_limiter import RateLimiter
from alert.telegram_adapter import TelegramAdapter
from alert.alert_outbox_worker import AlertOutboxWorker

TEST_DB = "data/test_outbox.db"
UNIVERSE_PATH = "data/universes/vn30_2026.json"

@pytest.fixture(autouse=True)
def cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

# ==============================================================================
# PHASE 4 TESTS: SCANNER & SCORING
# ==============================================================================

def test_scanner_universe_loading():
    scanner = MarketScanner({}, universe_path=UNIVERSE_PATH)
    assert len(scanner.universe) == 30
    assert "HOSE:FPT" in scanner.universe

def test_scanner_scoring_and_ranking():
    # Setup MTF managers for two symbols
    m1 = MTFManager("HOSE:AAA")
    m2 = MTFManager("HOSE:BBB")
    
    # We simulate indicators instead of raw candles to test the normalization
    # HOSE:AAA: Strong uptrend, High RSI, High RVOL
    with patch.object(m1, 'get_indicators') as mock_inds_1:
        mock_inds_1.side_effect = lambda tf, as_of_timestamp: IndicatorPayload(
            values={
                "close": 100, "volume": 2000, "sma20_vol": 1000,
                "ema20": 90, "ema50": 80, "ema200": 70,  # UPTREND -> 100
                "rsi14": 75,  # >70 -> 100
            },
            quality=IndicatorQuality.VALID,
            provenance=IndicatorProvenance(input_timeframe=tf)
        ) if tf == "1H" else None
        with patch.object(m1, 'get_trend_state') as mock_trend_1:
            mock_trend_1.return_value = "UPTREND" # Matches 1H and 15m -> MTF 100

            # HOSE:BBB: Downtrend, Low RSI, Low RVOL
            with patch.object(m2, 'get_indicators') as mock_inds_2:
                mock_inds_2.side_effect = lambda tf, as_of_timestamp: IndicatorPayload(
                    values={
                        "close": 50, "volume": 500, "sma20_vol": 1000,
                        "ema20": 60, "ema50": 70, "ema200": 80,  # DOWNTREND -> 0
                        "rsi14": 20,  # <30 -> 0
                    },
                    quality=IndicatorQuality.VALID,
                    provenance=IndicatorProvenance(input_timeframe=tf)
                ) if tf == "1H" else None
                with patch.object(m2, 'get_trend_state') as mock_trend_2:
                    mock_trend_2.return_value = "DOWNTREND"

                    scanner = MarketScanner({
                        "HOSE:AAA": m1,
                        "HOSE:BBB": m2,
                    }, universe_path="dummy.json")
                    scanner.universe = ["HOSE:AAA", "HOSE:BBB"]

                    results = scanner.scan()

                    assert len(results) == 2
                    
                    # AAA should have score (100*0.3 + 100*0.3 + 100*0.2 + 100*0.2) = 100
                    assert results[0].symbol == "HOSE:AAA"
                    assert results[0].score == 100.0
                    assert results[0].trend == "UPTREND"

                    # BBB should have score (0*0.3 + 0*0.3 + 0*0.2 + 100*0.2) = 20
                    assert results[1].symbol == "HOSE:BBB"
                    assert results[1].score == 20.0

def test_scanner_deterministic_ranking():
    m1 = MTFManager("HOSE:ZZZ")
    m2 = MTFManager("HOSE:AAA")
    
    # Both have exactly the same score
    def fake_inds(tf, as_of_timestamp):
        return IndicatorPayload(
            values={
                "close": 100, "volume": 1000, "sma20_vol": 1000,
                "ema20": 100, "ema50": 100, "ema200": 100, "rsi14": 50
            },
            quality=IndicatorQuality.VALID,
            provenance=IndicatorProvenance(input_timeframe=tf)
        ) if tf == "1H" else None
        
    with patch.object(m1, 'get_indicators', side_effect=fake_inds), \
         patch.object(m2, 'get_indicators', side_effect=fake_inds), \
         patch.object(m1, 'get_trend_state', return_value="SIDEWAYS"), \
         patch.object(m2, 'get_trend_state', return_value="SIDEWAYS"):

        scanner = MarketScanner({"HOSE:ZZZ": m1, "HOSE:AAA": m2}, universe_path="dummy")
        scanner.universe = ["HOSE:ZZZ", "HOSE:AAA"]
        results = scanner.scan()

        assert len(results) == 2
        # Score tie -> sort by symbol ASC
        assert results[0].symbol == "HOSE:AAA"
        assert results[1].symbol == "HOSE:ZZZ"
        assert results[0].score == results[1].score


def test_scanner_look_ahead_bias():
    manager = MTFManager("HOSE:FPT", supported_timeframes=["1H"])
    
    # Add candle at T=1000
    manager.on_candle(CanonicalCandle(
        symbol="HOSE:FPT", timeframe="1H", source_timestamp=1000,
        open=10, high=10, low=10, close=10, volume=100
    ))
    # Add future candle at T=2000
    manager.on_candle(CanonicalCandle(
        symbol="HOSE:FPT", timeframe="1H", source_timestamp=2000,
        open=20, high=20, low=20, close=20, volume=100
    ))
    
    scanner = MarketScanner({"HOSE:FPT": manager}, universe_path="dummy")
    scanner.universe = ["HOSE:FPT"]
    
    # Call scan at T=1000. The manager's indicators must NOT include T=2000 data.
    # The scan gets payload via manager.get_indicators("1H", as_of_timestamp=1000)
    # The incremental engine state has already been updated with T=2000
    # But because we ask for as_of_timestamp=1000, and we don't support history yet, it returns None.
    # Therefore it skips.
    results = scanner.scan(as_of_timestamp=1000)
    assert len(results) == 0

# ==============================================================================
# PHASE 5 TESTS: OUTBOX, RATE LIMITER, RETRY
# ==============================================================================

def test_outbox_persistence_and_unique():
    repo = OutboxRepository(TEST_DB)
    
    e1 = AlertEvent(signal_id="sig_1", destination="chat_1", payload={"data": 1})
    e2 = AlertEvent(signal_id="sig_1", destination="chat_1", payload={"data": 2})
    
    # Insert first
    assert repo.add_event(e1) == True
    
    # Insert duplicate (same signal_id and destination)
    assert repo.add_event(e2) == False
    
    # Verify persistence
    repo2 = OutboxRepository(TEST_DB)
    events = repo2.get_pending_events()
    assert len(events) == 1
    assert events[0].signal_id == "sig_1"
    assert events[0].payload["data"] == 1

def test_outbox_worker_transitions_and_jitter():
    repo = OutboxRepository(TEST_DB)
    repo.add_event(AlertEvent(signal_id="sig_1", destination="chat_1", payload={}))
    
    adapter = TelegramAdapter()
    adapter.bot_token = "dummy"
    rate_limiter = RateLimiter()
    worker = AlertOutboxWorker(repo, adapter, rate_limiter, max_retries=3, base_delay=1.0)
    worker.running = True
    
    # Mock Telegram to fail with network error (returns False, 0)
    with patch.object(adapter, 'send_message', return_value=(False, 0, {})):
        worker._process_outbox()
        
    events = repo.get_pending_events(limit=100) # next_retry_at is in future, so it won't be returned by default if we don't cheat
    
    # Manually query DB to check status
    with sqlite3.connect(TEST_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, retry_count, next_retry_at FROM outbox_events WHERE signal_id='sig_1'")
        row = cursor.fetchone()
        
        assert row[0] == "RETRYING"
        assert row[1] == 1
        # Delay should be: base(1) * 2^0 + jitter(0-1) = 1 to 2 seconds
        # So next_retry_at should be roughly int(time.time()) + 1 or 2
        delay = row[2] - int(time.time())
        assert 0 <= delay <= 2

def test_telegram_429_retry_after():
    repo = OutboxRepository(TEST_DB)
    repo.add_event(AlertEvent(signal_id="sig_2", destination="chat_1", payload={}))
    
    adapter = TelegramAdapter()
    adapter.bot_token = "dummy"
    worker = AlertOutboxWorker(repo, adapter, RateLimiter())
    worker.running = True
    
    # Mock Telegram to return HTTP 429 with retry_after=5
    with patch.object(adapter, 'send_message', return_value=(False, 5, {"error": "Too Many Requests"})):
        worker._process_outbox()
        
    with sqlite3.connect(TEST_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, retry_count, next_retry_at FROM outbox_events WHERE signal_id='sig_2'")
        row = cursor.fetchone()
        
        assert row[0] == "RETRYING"
        assert row[1] == 1
        # It must respect retry_after=5 exactly
        delay = row[2] - int(time.time())
        assert delay >= 4 and delay <= 6

def test_outbox_dead_letter():
    repo = OutboxRepository(TEST_DB)
    repo.add_event(AlertEvent(signal_id="sig_3", destination="chat_1", payload={}, retry_count=2, status=AlertStatus.RETRYING))
    
    adapter = TelegramAdapter()
    adapter.bot_token = "dummy"
    worker = AlertOutboxWorker(repo, adapter, RateLimiter(), max_retries=3)
    worker.running = True
    
    # Mock Telegram to fail
    with patch.object(adapter, 'send_message', return_value=(False, 0, {})):
        worker._process_outbox()
        
    with sqlite3.connect(TEST_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, retry_count FROM outbox_events WHERE signal_id='sig_3'")
        row = cursor.fetchone()
        
        # Max retries hit, should transition to FAILED
        assert row[0] == "FAILED"
        assert row[1] == 3
