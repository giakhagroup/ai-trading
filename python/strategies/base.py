from abc import ABC, abstractmethod
from typing import Optional
from models import CanonicalCandle, CandidateSignal

class IStrategy(ABC):
    """
    V2.0-027: Strategy Contract for both Live and Backtest
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, candle: CanonicalCandle) -> Optional[CandidateSignal]:
        """
        Takes incoming canonical candle (with indicators) and optionally emits a CandidateSignal.
        """
        pass
