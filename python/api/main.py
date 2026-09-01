import time
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel

from engine.scanner.market_state_store import MarketStateStore
from engine.scanner.scanner_coalescer import ScannerCoalescer
from engine.scanner.candle_ingestion_service import CandleIngestionService
from engine.scanner.market_scanner import MarketScanner

import os
import threading
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Trading Gateway API - Phase 8B")

# Initialize Domain Services
state_store = MarketStateStore(["15", "60"])
scanner = MarketScanner(state_store.managers, "data/universes/vn30_2026.json")

# Initialize Alert System
from alert.outbox_models import OutboxRepository
from alert.alert_policy import AlertPolicy
from alert.rate_limiter import RateLimiter
from alert.telegram_adapter import TelegramAdapter
from alert.alert_outbox_worker import AlertOutboxWorker

outbox_repo = OutboxRepository("data/outbox.db")
alert_policy = AlertPolicy(outbox_repo)
telegram_adapter = TelegramAdapter()
rate_limiter = RateLimiter()
outbox_worker = AlertOutboxWorker(outbox_repo, telegram_adapter, rate_limiter)
worker_thread = None

@app.on_event("startup")
def startup_event():
    global worker_thread
    print("[AlertSystem] Starting Outbox Worker...")
    worker_thread = threading.Thread(target=outbox_worker.start, daemon=True)
    worker_thread.start()

@app.on_event("shutdown")
def shutdown_event():
    print("[AlertSystem] Stopping Outbox Worker...")
    outbox_worker.stop()
    if worker_thread:
        worker_thread.join(timeout=2)

# In-memory storage for latest scan results
latest_scan_results = []
last_scan_time = 0

async def perform_scan():
    global latest_scan_results, last_scan_time
    # Use current time as correlation timestamp
    now = int(time.time() * 1000)
    print(f"[Scanner] Performing scan on {len(scanner.universe)} symbols at {now}...")
    
    # Run the CPU-bound scan in the default threadpool to not block async IO
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, scanner.scan, now, "60")
    
    latest_scan_results = results
    last_scan_time = now
    print(f"[Scanner] Scan complete. Yielded {len(results)} valid signals.")
    
    # Phase 8B: Pass to Alert Policy
    event = alert_policy.evaluate_and_emit(results, current_time=int(now/1000))
    if event:
        print(f"[AlertSystem] Emitted AlertEvent {event.signal_id} with {len(event.payload['items'])} items")

coalescer = ScannerCoalescer(scan_callback=perform_scan, debounce_ms=1000)
ingestion_service = CandleIngestionService(state_store, coalescer)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/events/candle")
async def receive_candle(request: Request):
    payload = await request.json()
    await ingestion_service.ingest_candle(payload)
    return {"status": "received"}

@app.get("/scanner/results")
async def get_scanner_results():
    return {
        "timestamp": last_scan_time,
        "count": len(latest_scan_results),
        "results": [r.__dict__ for r in latest_scan_results]
    }
