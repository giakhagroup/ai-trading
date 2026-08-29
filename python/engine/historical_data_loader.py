from typing import List, Tuple, Optional
import numpy as np
import pandas as pd
import time
from models import CanonicalCandle

class HistoricalDataLoader:
    """
    V2.0-027: Historical Dataset Loader & Synthetic Multi-Timeframe Generator
    """
    @staticmethod
    def generate_synthetic_candles(
        symbol: str = "HOSE:FPT",
        base_price: float = 70000.0,
        num_m5_bars: int = 1000,
        trend_drift: float = 0.0003, # Mild upward trend
        volatility: float = 0.004,
        start_timestamp: int = 1700000000
    ) -> Tuple[List[CanonicalCandle], List[CanonicalCandle]]:
        """
        Generates realistic synchronized M5 and H1 candles with geometric Brownian motion + pullbacks.
        Returns (m5_candles, h1_candles).
        """
        np.random.seed(42)
        
        m5_candles: List[CanonicalCandle] = []
        h1_candles: List[CanonicalCandle] = []
        
        current_price = base_price
        curr_time = start_timestamp
        
        m5_in_h1 = 12 # 12 * 5m = 60m
        h1_open = current_price
        h1_high = current_price
        h1_low = current_price
        h1_vol = 0.0
        h1_start_time = curr_time

        for i in range(num_m5_bars):
            # Geometric Brownian motion step with occasional pullbacks
            shock = np.random.normal(0, volatility)
            if i % 80 in range(25, 35): # Periodic pullback
                shock -= 0.006
            elif i % 80 in range(35, 45): # Reversal recovery
                shock += 0.008

            step_return = trend_drift + shock
            open_p = current_price
            close_p = open_p * (1.0 + step_return)
            
            intra_high = max(open_p, close_p) * (1.0 + abs(np.random.normal(0, 0.0015)))
            intra_low = min(open_p, close_p) * (1.0 - abs(np.random.normal(0, 0.0015)))
            volume = float(np.random.randint(10000, 150000))
            
            candle_m5 = CanonicalCandle(
                event_id=f"{symbol}-M5-{curr_time}",
                provider="HistoricalData",
                provider_symbol=symbol,
                internal_symbol=symbol,
                exchange=symbol.split(':')[0] if ':' in symbol else "HOSE",
                asset_class="STOCK",
                timeframe="5",
                source_timestamp=curr_time,
                event_timestamp=curr_time,
                received_at=curr_time,
                processed_at=curr_time,
                open=round(open_p, 1),
                high=round(intra_high, 1),
                low=round(intra_low, 1),
                close=round(close_p, 1),
                volume=volume,
                is_closed=True
            )
            m5_candles.append(candle_m5)
            
            # Aggregate H1
            h1_high = max(h1_high, intra_high)
            h1_low = min(h1_low, intra_low)
            h1_vol += volume
            
            # Close H1 bar every 12 M5 bars
            if (i + 1) % m5_in_h1 == 0:
                candle_h1 = CanonicalCandle(
                    event_id=f"{symbol}-H1-{h1_start_time}",
                    provider="HistoricalData",
                    provider_symbol=symbol,
                    internal_symbol=symbol,
                    exchange=symbol.split(':')[0] if ':' in symbol else "HOSE",
                    asset_class="STOCK",
                    timeframe="60",
                    source_timestamp=curr_time, # End of H1 bar timestamp
                    event_timestamp=curr_time,
                    received_at=curr_time,
                    processed_at=curr_time,
                    open=round(h1_open, 1),
                    high=round(h1_high, 1),
                    low=round(h1_low, 1),
                    close=round(close_p, 1),
                    volume=h1_vol,
                    is_closed=True
                )
                h1_candles.append(candle_h1)
                
                # Reset next H1
                h1_open = close_p
                h1_high = close_p
                h1_low = close_p
                h1_vol = 0.0
                h1_start_time = curr_time + 300
                
            current_price = close_p
            curr_time += 300 # 5 minutes in seconds
            
        return m5_candles, h1_candles

    @staticmethod
    def load_from_csv(file_path: str, symbol: str, timeframe: str) -> List[CanonicalCandle]:
        """Load candles from standard CSV format (timestamp/time, open, high, low, close, volume)."""
        df = pd.read_csv(file_path)
        candles: List[CanonicalCandle] = []
        
        for _, row in df.iterrows():
            ts = int(row.get('timestamp', row.get('time', 0)))
            c = CanonicalCandle(
                event_id=f"{symbol}-{timeframe}-{ts}",
                provider="CSV",
                provider_symbol=symbol,
                internal_symbol=symbol,
                exchange="HOSE",
                asset_class="STOCK",
                timeframe=timeframe,
                source_timestamp=ts,
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row.get('volume', 0)),
                is_closed=True
            )
            candles.append(c)
        return candles
