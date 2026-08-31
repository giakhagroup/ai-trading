import asyncio
from models import CanonicalCandle
from engine.scanner.market_state_store import MarketStateStore
from engine.scanner.scanner_coalescer import ScannerCoalescer

class CandleIngestionService:
    def __init__(self, state_store: MarketStateStore, coalescer: ScannerCoalescer):
        self.state_store = state_store
        self.coalescer = coalescer

    async def ingest_candle(self, candle_dict: dict):
        try:
            candle = CanonicalCandle(**candle_dict)
        except Exception as e:
            print(f"[CandleIngestionService] Invalid candle payload: {e}")
            return

        manager = self.state_store.get_manager(candle.internal_symbol)
        
        # 1. Update MTF State
        manager.on_candle(candle)

        # 2. Trigger scanner ONLY if candle is closed
        # Note: in Phase 5A, we rely on event-driven coalescing. 
        # A single closed candle triggers a coalesced scan.
        is_closed = candle_dict.get('is_closed', True)  # If not provided, assume True for backwards compat in tests
        
        # Checking timeframe? Typically we want to scan when lower timeframe (15m) closes or 60m closes.
        if is_closed:
            self.coalescer.trigger()
