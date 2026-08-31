import math
from typing import Dict, Any, Optional, List
from models import IndicatorQuality, IndicatorProvenance, IndicatorPayload
import time

class IncrementalEMA:
    def __init__(self, period: int):
        self.period = period
        self.multiplier = 2.0 / (period + 1)
        self.prev_ema: Optional[float] = None
        self.history = []

    def update(self, price: float, is_closed: bool = True) -> Optional[float]:
        if math.isnan(price):
            return self.prev_ema

        if self.prev_ema is None:
            if is_closed:
                self.history.append(price)
                if len(self.history) == self.period:
                    self.prev_ema = sum(self.history) / self.period
                    return self.prev_ema
            else:
                tmp_hist = self.history + [price]
                if len(tmp_hist) == self.period:
                    return sum(tmp_hist) / self.period
            return None

        val = (price - self.prev_ema) * self.multiplier + self.prev_ema
        if is_closed:
            self.prev_ema = val
        return val

class IncrementalSMA:
    def __init__(self, period: int):
        self.period = period
        self.history = []

    def update(self, price: float, is_closed: bool = True) -> Optional[float]:
        if math.isnan(price):
            if len(self.history) >= self.period:
                return sum(self.history[-self.period:]) / self.period
            return None

        if is_closed:
            self.history.append(price)
            if len(self.history) > self.period:
                self.history.pop(0)
            if len(self.history) == self.period:
                return sum(self.history) / self.period
        else:
            tmp_hist = self.history + [price]
            if len(tmp_hist) > self.period:
                tmp_hist.pop(0)
            if len(tmp_hist) == self.period:
                return sum(tmp_hist) / self.period
            
        return None

class IncrementalRSI:
    def __init__(self, period: int = 14):
        self.period = period
        self.prev_price: Optional[float] = None
        self.avg_gain: Optional[float] = None
        self.avg_loss: Optional[float] = None
        self.gains = []
        self.losses = []

    def update(self, price: float, is_closed: bool = True) -> Optional[float]:
        if math.isnan(price):
            return self._calc_rsi(self.avg_gain, self.avg_loss)

        if self.prev_price is None:
            if is_closed:
                self.prev_price = price
            return None

        change = price - self.prev_price
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        if self.avg_gain is None:
            if is_closed:
                self.gains.append(gain)
                self.losses.append(loss)
                self.prev_price = price
                if len(self.gains) == self.period:
                    self.avg_gain = sum(self.gains) / self.period
                    self.avg_loss = sum(self.losses) / self.period
                    return self._calc_rsi(self.avg_gain, self.avg_loss)
            else:
                tmp_gains = self.gains + [gain]
                tmp_losses = self.losses + [loss]
                if len(tmp_gains) == self.period:
                    return self._calc_rsi(sum(tmp_gains)/self.period, sum(tmp_losses)/self.period)
            return None

        new_avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
        new_avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period
        
        if is_closed:
            self.avg_gain = new_avg_gain
            self.avg_loss = new_avg_loss
            self.prev_price = price
            
        return self._calc_rsi(new_avg_gain, new_avg_loss)

    def _calc_rsi(self, ag: Optional[float], al: Optional[float]) -> Optional[float]:
        if al is None or ag is None:
            return None
        if al == 0:
            return 100.0
        rs = ag / al
        return 100.0 - (100.0 / (1.0 + rs))

class IncrementalATR:
    def __init__(self, period: int = 14):
        self.period = period
        self.prev_close: Optional[float] = None
        self.curr_atr: Optional[float] = None
        self.tr_history = []

    def update(self, high: float, low: float, close: float, is_closed: bool = True) -> Optional[float]:
        if math.isnan(high) or math.isnan(low) or math.isnan(close):
            return self.curr_atr

        if self.prev_close is None:
            if is_closed:
                self.prev_close = close
                self.tr_history.append(high - low)
            return None

        h_l = high - low
        h_pc = abs(high - self.prev_close)
        l_pc = abs(low - self.prev_close)
        tr = max(h_l, h_pc, l_pc)

        if self.curr_atr is None:
            if is_closed:
                self.tr_history.append(tr)
                self.prev_close = close
                if len(self.tr_history) == self.period:
                    self.curr_atr = sum(self.tr_history) / self.period
                    return self.curr_atr
            else:
                tmp_tr = self.tr_history + [tr]
                if len(tmp_tr) == self.period:
                    return sum(tmp_tr) / self.period
            return None

        new_atr = (self.curr_atr * (self.period - 1) + tr) / self.period
        if is_closed:
            self.curr_atr = new_atr
            self.prev_close = close
        return new_atr

class IncrementalMACD:
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast_ema = IncrementalEMA(fast)
        self.slow_ema = IncrementalEMA(slow)
        self.signal_ema = IncrementalEMA(signal)

    def update(self, price: float, is_closed: bool = True) -> Optional[Dict[str, float]]:
        fast_val = self.fast_ema.update(price, is_closed)
        slow_val = self.slow_ema.update(price, is_closed)

        if fast_val is None or slow_val is None:
            return None

        macd_line = fast_val - slow_val
        signal_line = self.signal_ema.update(macd_line, is_closed)

        if signal_line is None:
            return None

        hist = macd_line - signal_line
        return {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_hist": hist
        }

class TimeframeIndicatorState:
    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        self.ema20 = IncrementalEMA(20)
        self.ema50 = IncrementalEMA(50)
        self.ema200 = IncrementalEMA(200)
        self.rsi14 = IncrementalRSI(14)
        self.atr14 = IncrementalATR(14)
        self.macd = IncrementalMACD(12, 26, 9)
        self.sma20_vol = IncrementalSMA(20)
        
        self.quality: IndicatorQuality = IndicatorQuality.WARMUP
        self.bar_count = 0
        self.last_timestamp = 0

    def update(self, open_p: float, high: float, low: float, close: float, volume: float, timestamp: int, is_closed: bool) -> IndicatorPayload:
        if self.last_timestamp > 0 and timestamp - self.last_timestamp > self._get_tf_ms(self.timeframe) * 1.5:
            # Reconnect gap detected
            # We do NOT interpolate. We mark STALE
            self.quality = IndicatorQuality.STALE
            # Require backfill to reset
        
        if is_closed:
            self.last_timestamp = timestamp
            self.bar_count += 1
        
        e20 = self.ema20.update(close, is_closed)
        e50 = self.ema50.update(close, is_closed)
        e200 = self.ema200.update(close, is_closed)
        rsi = self.rsi14.update(close, is_closed)
        atr = self.atr14.update(high, low, close, is_closed)
        macd_obj = self.macd.update(close, is_closed)
        sma_vol = self.sma20_vol.update(volume, is_closed)

        if self.quality == IndicatorQuality.WARMUP and self.bar_count >= 200:
            self.quality = IndicatorQuality.VALID

        values = {
            "close": close,
            "volume": volume,
            "ema20": round(e20, 4) if e20 is not None else None,
            "ema50": round(e50, 4) if e50 is not None else None,
            "ema200": round(e200, 4) if e200 is not None else None,
            "rsi14": round(rsi, 4) if rsi is not None else None,
            "atr14": round(atr, 4) if atr is not None else None,
            "macd": round(macd_obj["macd"], 4) if macd_obj is not None else None,
            "macd_signal": round(macd_obj["macd_signal"], 4) if macd_obj is not None else None,
            "macd_hist": round(macd_obj["macd_hist"], 4) if macd_obj is not None else None,
            "sma20_vol": round(sma_vol, 4) if sma_vol is not None else None,
            "bar_count": self.bar_count
        }

        provenance = IndicatorProvenance(
            source="LOCAL",
            calculation_version="2.0-incremental",
            input_timeframe=self.timeframe,
            calculated_at=int(time.time() * 1000)
        )

        return IndicatorPayload(
            values=values,
            quality=self.quality,
            provenance=provenance
        )
        
    def backfill(self, highs: List[float], lows: List[float], closes: List[float], volumes: List[float], timestamps: List[int]):
        """Backfill resets the state and applies historical data in bulk"""
        self.__init__(self.timeframe)
        for i in range(len(closes)):
            self.update(0, highs[i], lows[i], closes[i], volumes[i], timestamps[i], is_closed=True)
        if self.bar_count >= 200:
            self.quality = IndicatorQuality.VALID

    def _get_tf_ms(self, tf: str) -> int:
        if tf == "1": return 60000
        if tf == "5": return 300000
        if tf == "15": return 900000
        if tf == "60": return 3600000
        if tf == "D": return 86400000
        return 60000
