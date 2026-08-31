import time
import asyncio
from typing import Callable, Awaitable

class ScannerCoalescer:
    def __init__(self, scan_callback: Callable[[], Awaitable[None]], debounce_ms: int = 500):
        self.scan_callback = scan_callback
        self.debounce_ms = debounce_ms
        self._last_trigger_time = 0
        self._task = None
        self._pending = False

    def trigger(self):
        """
        Trigger a scan. Coalesces rapid triggers within `debounce_ms`.
        Must be called from an async context or event loop thread.
        """
        self._pending = True
        
        # If there's no active task, start the debouncer loop
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._debounce_loop())

    async def _debounce_loop(self):
        while self._pending:
            self._pending = False
            
            # Wait for the debounce period to accumulate rapid triggers
            await asyncio.sleep(self.debounce_ms / 1000.0)
            
            # If a new trigger arrived during sleep, we loop again to wait.
            # But normally we just execute if we accumulated triggers.
            try:
                await self.scan_callback()
            except Exception as e:
                print(f"[ScannerCoalescer] Error during scan callback: {e}")
