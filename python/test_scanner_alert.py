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
from alert.alert_policy import AlertPolicy

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
# PHASE 4 TESTS: SCANNER & SCORING (Keep these as they are good)
# ==============================================================================

def test_scanner_universe_loading():
    scanner = MarketScanner({}, universe_path=UNIVERSE_PATH)
    assert len(scanner.universe) == 30
    assert "HOSE:FPT" in scanner.universe

# ==============================================================================
# PHASE 8A TESTS: ALERT POLICY & OUTBOX
# ==============================================================================

def test_outbox_persistence_and_unique():
    repo = OutboxRepository(TEST_DB)
    
    e1 = AlertEvent(signal_id="sig_1", destination="chat_1", payload={"data": 1}, rule_version="v1.0")
    e2 = AlertEvent(signal_id="sig_1", destination="chat_1", payload={"data": 2}, rule_version="v1.0")
    
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

def test_alert_policy_score_thresholds():
    repo = OutboxRepository(TEST_DB)
    policy = AlertPolicy(repo)
    
    r1 = ScanResult(symbol="HOSE:A", correlation_id="1", score=79, trend="UPTREND", momentum=90, close=100, volume=1000, total_score=79, trend_score=100, momentum_score=0, mtf_score=0, trend_state="UPTREND", data_quality="VALID")
    r2 = ScanResult(symbol="HOSE:B", correlation_id="2", score=85, trend="UPTREND", momentum=90, close=100, volume=1000, total_score=85, trend_score=79, momentum_score=0, mtf_score=0, trend_state="UPTREND", data_quality="VALID")
    r3 = ScanResult(symbol="HOSE:C", correlation_id="3", score=85, trend="UPTREND", momentum=90, close=100, volume=1000, total_score=85, trend_score=85, momentum_score=0, mtf_score=0, trend_state="UPTREND", data_quality="VALID")
    
    event = policy.evaluate_and_emit([r1, r2, r3], current_time=1000)
    
    assert event is not None
    # Only C meets both thresholds (total>=80, trend>=80)
    assert len(event.payload["items"]) == 1
    assert event.payload["items"][0]["symbol"] == "HOSE:C"

def test_alert_policy_stale_or_missing_quality_is_ignored():
    repo = OutboxRepository(TEST_DB)
    policy = AlertPolicy(repo)
    
    r1 = ScanResult(symbol="HOSE:A", correlation_id="1", score=100, trend="UPTREND", momentum=90, close=100, volume=1000, total_score=100, trend_score=100, momentum_score=0, mtf_score=0, trend_state="UPTREND", data_quality="STALE")
    r2 = ScanResult(symbol="HOSE:B", correlation_id="2", score=100, trend="UPTREND", momentum=90, close=100, volume=1000, total_score=100, trend_score=100, momentum_score=0, mtf_score=0, trend_state="UPTREND", data_quality="MISSING")
    
    event = policy.evaluate_and_emit([r1, r2], current_time=1000)
    assert event is None

def test_alert_policy_summary_size_and_ranking():
    repo = OutboxRepository(TEST_DB)
    policy = AlertPolicy(repo)
    
    results = [
        ScanResult(symbol=f"HOSE:{i}", correlation_id=str(i), score=80+i, trend="UPTREND", momentum=90, close=100, volume=1000, total_score=80+i, trend_score=100, momentum_score=0, mtf_score=0, trend_state="UPTREND", data_quality="VALID")
        for i in range(10)
    ]
    
    event = policy.evaluate_and_emit(results, current_time=1000)
    assert event is not None
    assert len(event.payload["items"]) == 3  # SUMMARY_SIZE
    
    # Should pick the top 3 by total_score (i=9, 8, 7 which have score 89, 88, 87)
    symbols = [item["symbol"] for item in event.payload["items"]]
    assert "HOSE:9" in symbols
    assert "HOSE:8" in symbols
    assert "HOSE:7" in symbols

def test_alert_policy_cooldown():
    repo = OutboxRepository(TEST_DB)
    policy = AlertPolicy(repo)
    
    r1 = ScanResult(symbol="HOSE:A", correlation_id="1", score=100, trend="UPTREND", momentum=90, close=100, volume=1000, total_score=100, trend_score=100, momentum_score=0, mtf_score=0, trend_state="UPTREND", data_quality="VALID")
    
    # 1. First time emits
    e1 = policy.evaluate_and_emit([r1], current_time=1000)
    assert e1 is not None
    assert e1.payload["items"][0]["symbol"] == "HOSE:A"
    
    # 2. Second time shortly after -> Ignored due to cooldown
    e2 = policy.evaluate_and_emit([r1], current_time=2000)
    assert e2 is None
    
    # 3. After 4 hours (14400 seconds) -> Emits again
    e3 = policy.evaluate_and_emit([r1], current_time=1000 + 4*3600 + 1)
    assert e3 is not None
    assert e3.payload["items"][0]["symbol"] == "HOSE:A"

def test_alert_policy_idempotency_15m():
    repo = OutboxRepository(TEST_DB)
    policy = AlertPolicy(repo)
    
    r1 = ScanResult(symbol="HOSE:A", correlation_id="1", score=100, trend="UPTREND", momentum=90, close=100, volume=1000, total_score=100, trend_score=100, momentum_score=0, mtf_score=0, trend_state="UPTREND", data_quality="VALID")
    
    # Same 15m block (e.g., 901 and 910)
    # The signal ID generated should be identical!
    e1 = policy.evaluate_and_emit([r1], current_time=901)
    # Clear cooldown manually so we can test idempotency key block
    repo.update_cooldowns(["HOSE:A"], 0)
    e2 = policy.evaluate_and_emit([r1], current_time=910)
    
    # Both evaluate, but the second one returns an event that is a DUPLICATE in Outbox.
    # Actually evaluate_and_emit tries to add_event. If duplicate, it still returns the event but add_event was False.
    # Let's check outbox size.
    assert len(repo.get_pending_events()) == 1

def test_outbox_worker_telegram_mock():
    repo = OutboxRepository(TEST_DB)
    policy = AlertPolicy(repo)
    
    r1 = ScanResult(symbol="HOSE:FPT", correlation_id="1", score=95, trend="UPTREND", momentum=90, close=100, volume=1000, total_score=95, trend_score=100, momentum_score=0, mtf_score=0, trend_state="UPTREND", data_quality="VALID")
    policy.evaluate_and_emit([r1], current_time=1000)
    
    adapter = TelegramAdapter()
    adapter.bot_token = ""  # Mock mode
    rate_limiter = RateLimiter()
    worker = AlertOutboxWorker(repo, adapter, rate_limiter, max_retries=3, base_delay=1.0)
    worker.running = True
    
    # Process queue
    worker._process_outbox()
    
    # Event should be marked as SENT
    events = repo.get_pending_events()
    assert len(events) == 0  # No pending events left
    
    with sqlite3.connect(TEST_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM outbox_events")
        status = cursor.fetchone()[0]
        assert status == "SENT"
