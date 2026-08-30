import uvicorn
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List
import logging

from models import CanonicalCandle, CandidateSignal, ValidatedSignal, RejectedSignal, SessionType
from engine.mtf_manager import MTFManager
from engine.scanner.market_scanner import MarketScanner
from engine.scanner.scanner_types import ScanResult
from alert.outbox_models import OutboxRepository, AlertEvent
from alert.alert_outbox_worker import AlertOutboxWorker
from alert.telegram_adapter import TelegramAdapter
from alert.rate_limiter import RateLimiter
import threading
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QuantEngine")

app = FastAPI(title="AI Trading Python Quant & Risk Engine", version="2.0.0")

# Initialize Engine Components
mtf_managers: Dict[str, MTFManager] = {}
scanner = MarketScanner(mtf_managers=mtf_managers)
outbox_repo = OutboxRepository(db_path="data/outbox.db")
telegram_adapter = TelegramAdapter()
rate_limiter = RateLimiter()

outbox_worker = AlertOutboxWorker(
    repository=outbox_repo,
    adapter=telegram_adapter,
    rate_limiter=rate_limiter
)

# Start outbox worker in a background thread
worker_thread = threading.Thread(target=outbox_worker.start, daemon=True)
worker_thread.start()

@app.get("/health")
def health():
    return {
        "status": "online",
        "strategies": [s.name for s in strategies],
        "risk_engine": "active"
    }

@app.post("/events/candle")
def on_candle_event(candle: CanonicalCandle):
    """
    Receives Canonical Candle stream (with TradingView indicators) from Node.js Gateway.
    Executes Strategy pipeline -> Candidate Signals -> Risk Engine -> Validated Signals.
    """
    logger.info(f"Received candle: {candle.internal_symbol} {candle.timeframe} Close={candle.close} Indicators={candle.indicators}")
    
    results = {
        "candidates": [],
        "validated": [],
        "rejected": []
    }

    symbol = candle.provider_symbol
    
    # 1. Update MTF Manager
    if symbol not in mtf_managers:
        mtf_managers[symbol] = MTFManager(symbol=symbol)
    
    mtf_managers[symbol].on_candle(candle)

    # 2. Trigger Scan if candle is closed (Rollover)
    if candle.is_closed:
        logger.info(f"Candle closed for {symbol}, triggering Market Scanner...")
        scan_results = scanner.scan(as_of_timestamp=candle.source_timestamp, timeframe=candle.timeframe)
        
        logger.info(f"Scanner produced {len(scan_results)} results.")
        for res in scan_results:
            logger.info(f"Scanner result for {res.symbol}: Score={res.score}, Trend={res.trend}")
            # Simple threshold to trigger alert
            if res.score >= 70:
                alert_id = f"ALERT-{res.symbol}-{candle.source_timestamp}"
                # The chat_id should be fetched from config/env, here we use a dummy or predefined one
                chat_id = "-100203002"  # Mock or real chat_id here
                
                alert_event = AlertEvent(
                    signal_id=alert_id,
                    destination=chat_id,
                    payload=res.model_dump(),
                    created_at=int(time.time())
                )
                added = outbox_repo.add_event(alert_event)
                if added:
                    logger.info(f"Enqueued High-Score Scanner Alert for {res.symbol} (Score: {res.score})")
                results["validated"].append(res.model_dump())
    
    return results

@app.get("/signals/validated")
def get_validated_signals():
    return []

@app.get("/signals/rejected")
def get_rejected_signals():
    return []

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
