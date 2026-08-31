from typing import Dict, List
from engine.mtf_manager import MTFManager

class MarketStateStore:
    def __init__(self, supported_timeframes: List[str] = None):
        if supported_timeframes is None:
            supported_timeframes = ["1", "5", "15", "60"]
        self.supported_timeframes = supported_timeframes
        self.managers: Dict[str, MTFManager] = {}

    def get_manager(self, symbol: str) -> MTFManager:
        if symbol not in self.managers:
            self.managers[symbol] = MTFManager(symbol, self.supported_timeframes)
        return self.managers[symbol]

    def all_managers(self) -> List[MTFManager]:
        return list(self.managers.values())
