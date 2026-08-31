import unittest
import asyncio
import time
from typing import List

from engine.scanner.market_state_store import MarketStateStore
from engine.scanner.scanner_coalescer import ScannerCoalescer
from engine.scanner.candle_ingestion_service import CandleIngestionService
from engine.scanner.market_scanner import MarketScanner
from engine.mtf_manager import MTFManager
from models import CanonicalCandle

class TestPhase5AScanner(unittest.IsolatedAsyncioTestCase):

    async def test_p5_002_fastapi_endpoint_contract(self):
        """P5-002: Verify the endpoint contract accepts CanonicalCandle JSON."""
        # Using FastAPI TestClient
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Valid payload
        valid_payload = {
            "event_id": "test_1",
            "provider": "TV",
            "provider_symbol": "HOSE:FPT",
            "internal_symbol": "HOSE:FPT",
            "exchange": "HOSE",
            "asset_class": "STOCK",
            "timeframe": "15",
            "source_timestamp": 1000000,
            "open": 100,
            "high": 110,
            "low": 90,
            "close": 105,
            "volume": 1000,
            "is_closed": True
        }
        
        response = client.post("/events/candle", json=valid_payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "received"})

    async def test_p5_003_candle_ingestion_isolates_symbols(self):
        """P5-003: CandleIngestionService isolates states per symbol."""
        store = MarketStateStore(["15"])
        
        # Dummy coalescer
        class DummyCoalescer:
            def trigger(self): pass
        
        service = CandleIngestionService(store, DummyCoalescer())
        
        await service.ingest_candle({
            "event_id": "1", "provider": "TV", "provider_symbol": "FPT", "internal_symbol": "FPT",
            "exchange": "HOSE", "asset_class": "STOCK", "timeframe": "15", "source_timestamp": 1000,
            "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000, "is_closed": True
        })
        
        await service.ingest_candle({
            "event_id": "2", "provider": "TV", "provider_symbol": "VIC", "internal_symbol": "VIC",
            "exchange": "HOSE", "asset_class": "STOCK", "timeframe": "15", "source_timestamp": 1000,
            "open": 50, "high": 55, "low": 45, "close": 52, "volume": 2000, "is_closed": True
        })
        
        fpt_mgr = store.get_manager("FPT")
        vic_mgr = store.get_manager("VIC")
        
        self.assertEqual(len(store.managers), 2)
        fpt_payload = fpt_mgr.get_indicators("15")
        vic_payload = vic_mgr.get_indicators("15")
        
        self.assertEqual(fpt_payload.values["close"], 105)
        self.assertEqual(vic_payload.values["close"], 52)

    async def test_p5_004_event_driven_coalescing(self):
        """P5-004: Event-driven coalescing ensures scanner is not over-triggered."""
        scan_counts = 0
        async def dummy_scan():
            nonlocal scan_counts
            scan_counts += 1
            
        coalescer = ScannerCoalescer(dummy_scan, debounce_ms=100)
        
        # Trigger 5 times rapidly
        for _ in range(5):
            coalescer.trigger()
            
        await asyncio.sleep(0.2) # Wait for debounce
        
        # Should only execute ONCE despite 5 triggers
        self.assertEqual(scan_counts, 1)
        
        # Trigger again later
        coalescer.trigger()
        await asyncio.sleep(0.2)
        self.assertEqual(scan_counts, 2)

    async def test_p5_007_ignore_is_closed_false_for_scanner(self):
        """P5-007: Ignore is_closed=false for scanner triggers."""
        scan_counts = 0
        async def dummy_scan():
            nonlocal scan_counts
            scan_counts += 1
            
        coalescer = ScannerCoalescer(dummy_scan, debounce_ms=10)
        store = MarketStateStore(["15"])
        service = CandleIngestionService(store, coalescer)
        
        # Send 3 unclosed candles
        for i in range(3):
            await service.ingest_candle({
                "event_id": str(i), "provider": "TV", "provider_symbol": "FPT", "internal_symbol": "FPT",
                "exchange": "HOSE", "asset_class": "STOCK", "timeframe": "15", "source_timestamp": 1000 + i,
                "open": 100, "high": 110, "low": 90, "close": 105 + i, "volume": 1000, "is_closed": False
            })
            
        await asyncio.sleep(0.05)
        # Should be 0 triggers
        self.assertEqual(scan_counts, 0)
        
        # Send 1 closed candle
        await service.ingest_candle({
            "event_id": "close", "provider": "TV", "provider_symbol": "FPT", "internal_symbol": "FPT",
            "exchange": "HOSE", "asset_class": "STOCK", "timeframe": "15", "source_timestamp": 2000,
            "open": 100, "high": 110, "low": 90, "close": 108, "volume": 1000, "is_closed": True
        })
        
        await asyncio.sleep(0.05)
        # Should trigger exactly once
        self.assertEqual(scan_counts, 1)

    async def test_p5_005_scanner_skips_invalid_quality(self):
        """P5-005: Scanner skips symbols with STALE/MISSING or WARMUP quality."""
        store = MarketStateStore(["60", "15"])
        scanner = MarketScanner(store.managers, "data/universes/vn30_2026.json")
        scanner.universe = ["HOSE:FPT"]
        
        fpt = store.get_manager("HOSE:FPT")
        # Send only 1 candle -> Quality will be WARMUP (needs 200)
        fpt.on_candle(CanonicalCandle(
            event_id="1", provider="TV", provider_symbol="HOSE:FPT", internal_symbol="HOSE:FPT",
            exchange="HOSE", asset_class="STOCK", timeframe="60", source_timestamp=1000,
            open=100, high=110, low=90, close=105, volume=1000, is_closed=True
        ))
        
        results = scanner.scan()
        # Should be empty because quality is WARMUP
        self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main()
