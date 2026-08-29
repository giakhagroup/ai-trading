from typing import List, Dict
import numpy as np

def calculate_sma(prices: List[float], period: int) -> List[float]:
    """Calculate Simple Moving Average (SMA)."""
    if len(prices) < period or period <= 0:
        return [float('nan')] * len(prices)
    
    result = [float('nan')] * (period - 1)
    window_sum = sum(prices[:period])
    result.append(window_sum / period)
    
    for i in range(period, len(prices)):
        window_sum += prices[i] - prices[i - period]
        result.append(window_sum / period)
        
    return result

def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average (EMA)."""
    if len(prices) < period or period <= 0:
        return [float('nan')] * len(prices)
    
    multiplier = 2.0 / (period + 1)
    result = [float('nan')] * len(prices)
    
    # Initialize first EMA with SMA of first 'period' elements
    first_sma = sum(prices[:period]) / period
    result[period - 1] = first_sma
    
    for i in range(period, len(prices)):
        prev_ema = result[i - 1]
        result[i] = (prices[i] - prev_ema) * multiplier + prev_ema
        
    return result

def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index (RSI - Wilder's Smoothing)."""
    if len(prices) <= period or period <= 0:
        return [float('nan')] * len(prices)
    
    result = [float('nan')] * len(prices)
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change >= 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))
            
    if len(gains) < period:
        return result
    
    # Initial averages
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))
        
    for i in range(period + 1, len(prices)):
        gain = gains[i - 1]
        loss = losses[i - 1]
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - (100.0 / (1.0 + rs))
            
    return result

def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    """Calculate Average True Range (ATR)."""
    n = len(closes)
    if n < 2 or period <= 0:
        return [float('nan')] * n
        
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        h_l = highs[i] - lows[i]
        h_pc = abs(highs[i] - closes[i - 1])
        l_pc = abs(lows[i] - closes[i - 1])
        tr.append(max(h_l, h_pc, l_pc))
        
    if n < period:
        return [float('nan')] * n
        
    result = [float('nan')] * n
    # Initial ATR
    curr_atr = sum(tr[:period]) / period
    result[period - 1] = curr_atr
    
    for i in range(period, n):
        curr_atr = (curr_atr * (period - 1) + tr[i]) / period
        result[i] = curr_atr
        
    return result

def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
    """Calculate MACD Line, Signal Line, and Histogram."""
    fast_ema = calculate_ema(prices, fast)
    slow_ema = calculate_ema(prices, slow)
    
    macd_line = []
    for f, s in zip(fast_ema, slow_ema):
        if np.isnan(f) or np.isnan(s):
            macd_line.append(float('nan'))
        else:
            macd_line.append(f - s)
            
    # Filter valid macd points for signal calculation
    valid_macd_indices = [i for i, v in enumerate(macd_line) if not np.isnan(v)]
    signal_line = [float('nan')] * len(prices)
    
    if len(valid_macd_indices) >= signal:
        valid_macd_values = [macd_line[i] for i in valid_macd_indices]
        valid_signal = calculate_ema(valid_macd_values, signal)
        for idx, sig_val in zip(valid_macd_indices, valid_signal):
            signal_line[idx] = sig_val
            
    hist = []
    for m, s in zip(macd_line, signal_line):
        if np.isnan(m) or np.isnan(s):
            hist.append(float('nan'))
        else:
            hist.append(m - s)
            
    return {
        "macd": macd_line,
        "signal": signal_line,
        "hist": hist
    }
