import time
import numpy as np
import pandas as pd
from typing import List

# --- Python Incremental (List-based) ---
def python_ema_incremental(prices: List[float], prev_ema: float, period: int) -> float:
    multiplier = 2.0 / (period + 1)
    return (prices[-1] - prev_ema) * multiplier + prev_ema

# --- NumPy Incremental (Array-based ring buffer) ---
class NumpyEMA:
    def __init__(self, period: int):
        self.period = period
        self.multiplier = 2.0 / (period + 1)
        self.prev_ema = None
        self.history = []
        
    def update(self, new_price: float) -> float:
        if self.prev_ema is None:
            self.history.append(new_price)
            if len(self.history) == self.period:
                self.prev_ema = sum(self.history) / self.period
            return float('nan')
            
        self.prev_ema = (new_price - self.prev_ema) * self.multiplier + self.prev_ema
        return self.prev_ema

# --- Pandas-TA (Full dataframe) ---
try:
    import pandas_ta as ta
    has_pandas_ta = True
except ImportError:
    has_pandas_ta = False

def run_benchmark():
    SYMBOLS = 100
    TIMEFRAMES = 5
    SERIES = SYMBOLS * TIMEFRAMES
    TICKS = 1000  # Number of realtime ticks
    HISTORY_LEN = 500  # Initial history
    
    print(f"Benchmarking {SERIES} series for {TICKS} ticks...")
    
    # 1. Setup mock data
    np.random.seed(42)
    mock_histories = [np.random.rand(HISTORY_LEN).tolist() for _ in range(SERIES)]
    mock_ticks = [np.random.rand(TICKS).tolist() for _ in range(SERIES)]
    
    # --- Benchmark Numpy Incremental ---
    start = time.time()
    numpy_engines = [NumpyEMA(14) for _ in range(SERIES)]
    # Warmup
    for i, hist in enumerate(mock_histories):
        for p in hist:
            numpy_engines[i].update(p)
            
    # Tick loop
    for tick_idx in range(TICKS):
        for i in range(SERIES):
            numpy_engines[i].update(mock_ticks[i][tick_idx])
            
    numpy_time = time.time() - start
    print(f"Numpy Incremental Time: {numpy_time:.4f} seconds")
    
    # --- Benchmark Pandas-TA Full Series ---
    if has_pandas_ta:
        start = time.time()
        dfs = [pd.DataFrame({"close": hist.copy()}) for hist in mock_histories]
        
        for tick_idx in range(TICKS):
            for i in range(SERIES):
                # Append row and compute full EMA
                dfs[i].loc[len(dfs[i])] = {"close": mock_ticks[i][tick_idx]}
                dfs[i].ta.ema(length=14, append=True)
                
        pandas_ta_time = time.time() - start
        print(f"Pandas-TA (Full recompute) Time: {pandas_ta_time:.4f} seconds")
    else:
        print("Pandas-TA not installed, skipping.")

    # --- Benchmark Python Full Series (Current system) ---
    def calc_ema_full(prices, period):
        if len(prices) < period: return [float('nan')] * len(prices)
        mult = 2.0 / (period + 1)
        res = [float('nan')] * len(prices)
        res[period-1] = sum(prices[:period])/period
        for i in range(period, len(prices)):
            res[i] = (prices[i] - res[i-1]) * mult + res[i-1]
        return res
        
    start = time.time()
    python_histories = [hist.copy() for hist in mock_histories]
    for tick_idx in range(TICKS):
        for i in range(SERIES):
            python_histories[i].append(mock_ticks[i][tick_idx])
            # Trim to avoid memory explosion
            if len(python_histories[i]) > 1000:
                python_histories[i] = python_histories[i][-500:]
            calc_ema_full(python_histories[i], 14)
            
    python_full_time = time.time() - start
    print(f"Current Python Full Recompute Time: {python_full_time:.4f} seconds")

if __name__ == '__main__':
    run_benchmark()
