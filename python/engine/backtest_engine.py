from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import math
from dataclasses import dataclass, field
import numpy as np

from models import (
    CanonicalCandle,
    CandidateSignal,
    ValidatedSignal,
    SignalDirection,
    SignalStatus
)
from risk.risk_engine import RiskEngine

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Position:
    position_id: str
    symbol: str
    direction: SignalDirection
    shares: float
    entry_price: float
    entry_time: int
    stop_loss: float
    take_profit: float
    commission_paid: float
    
    # State
    is_open: bool = True
    exit_price: Optional[float] = None
    exit_time: Optional[int] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0

@dataclass
class BacktestConfig:
    initial_capital: float = 100_000_000.0 # 100M VND
    commission_rate: float = 0.0015        # 0.15% per trade
    sell_tax_rate: float = 0.0010          # 0.10% tax on sell
    slippage_rate: float = 0.0005          # 0.05% slippage
    max_position_size_pct: float = 0.30    # 30% capital per trade
    allow_pyramiding: bool = False

@dataclass
class BacktestResult:
    config: BacktestConfig
    initial_capital: float
    final_equity: float
    net_profit: float
    net_profit_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    payoff_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: List[Position]
    equity_curve: List[Dict[str, Any]]

class BacktestEngine:
    """
    V2.0-025, V2.0-026 & V2.0-027: High-Fidelity Backtest Execution Engine
    """
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.reset()

    def reset(self):
        self.cash = self.config.initial_capital
        self.positions: List[Position] = []
        self.closed_positions: List[Position] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.trade_counter = 0

    def get_open_position(self, symbol: str) -> Optional[Position]:
        for pos in self.positions:
            if pos.symbol == symbol and pos.is_open:
                return pos
        return None

    def execute_order(
        self,
        validated_signal: ValidatedSignal,
        candle: CanonicalCandle
    ) -> Optional[Position]:
        """Execute entry based on a Validated Signal using next tick/open or current close with slippage."""
        symbol = validated_signal.signal.symbol
        if not self.config.allow_pyramiding and self.get_open_position(symbol):
            return None # Already in position for this symbol

        raw_price = validated_signal.signal.entry_price
        direction = validated_signal.signal.direction
        
        # Apply Slippage
        if direction == SignalDirection.LONG:
            exec_price = raw_price * (1.0 + self.config.slippage_rate)
        else:
            exec_price = raw_price * (1.0 - self.config.slippage_rate)

        # Position Sizing
        allocated_cash = self.cash * self.config.max_position_size_pct
        if allocated_cash < 1_000_000: # Minimum position size 1M VND
            return None

        # Round shares to lot of 100 for VN stock
        shares = math.floor((allocated_cash / exec_price) / 100.0) * 100
        if shares <= 0:
            return None

        trade_cost = shares * exec_price
        commission = trade_cost * self.config.commission_rate
        total_spent = trade_cost + commission

        if total_spent > self.cash:
            return None

        self.cash -= total_spent
        self.trade_counter += 1
        
        pos = Position(
            position_id=f"pos_{self.trade_counter}_{symbol}",
            symbol=symbol,
            direction=direction,
            shares=shares,
            entry_price=exec_price,
            entry_time=candle.source_timestamp,
            stop_loss=validated_signal.signal.stop_loss,
            take_profit=validated_signal.signal.take_profit,
            commission_paid=commission
        )
        self.positions.append(pos)
        return pos

    def update_positions(self, candle: CanonicalCandle):
        """Check open positions against candle High/Low/Close for TP, SL, or trailing exit."""
        for pos in list(self.positions):
            if not pos.is_open or pos.symbol != candle.internal_symbol:
                continue

            exit_price = None
            exit_reason = None

            if pos.direction == SignalDirection.LONG:
                # Check Stop Loss first (Low breaches SL)
                if candle.low <= pos.stop_loss:
                    exit_price = pos.stop_loss * (1.0 - self.config.slippage_rate)
                    exit_reason = "STOP_LOSS"
                # Check Take Profit (High reaches TP)
                elif candle.high >= pos.take_profit:
                    exit_price = pos.take_profit * (1.0 - self.config.slippage_rate)
                    exit_reason = "TAKE_PROFIT"
            else: # SHORT
                if candle.high >= pos.stop_loss:
                    exit_price = pos.stop_loss * (1.0 + self.config.slippage_rate)
                    exit_reason = "STOP_LOSS"
                elif candle.low <= pos.take_profit:
                    exit_price = pos.take_profit * (1.0 + self.config.slippage_rate)
                    exit_reason = "TAKE_PROFIT"

            if exit_price and exit_reason:
                self._close_position(pos, exit_price, candle.source_timestamp, exit_reason)

    def _close_position(self, pos: Position, exit_price: float, exit_time: int, reason: str):
        pos.is_open = False
        pos.exit_price = exit_price
        pos.exit_time = exit_time
        pos.exit_reason = reason

        gross_proceeds = pos.shares * exit_price
        exit_commission = gross_proceeds * self.config.commission_rate
        exit_tax = gross_proceeds * self.config.sell_tax_rate if pos.direction == SignalDirection.LONG else 0.0
        
        net_proceeds = gross_proceeds - exit_commission - exit_tax
        pos.commission_paid += exit_commission + exit_tax

        if pos.direction == SignalDirection.LONG:
            pos.pnl = net_proceeds - (pos.shares * pos.entry_price) - (pos.commission_paid - exit_commission - exit_tax)
        else:
            pos.pnl = (pos.shares * pos.entry_price) - net_proceeds - pos.commission_paid

        pos.pnl_pct = (pos.pnl / (pos.shares * pos.entry_price)) * 100.0

        self.cash += net_proceeds
        self.positions.remove(pos)
        self.closed_positions.append(pos)

    def record_equity(self, timestamp: int, current_prices: Dict[str, float]):
        """Record portfolio equity curve snapshot."""
        unrealized_pnl = 0.0
        for pos in self.positions:
            price = current_prices.get(pos.symbol, pos.entry_price)
            if pos.direction == SignalDirection.LONG:
                unrealized_pnl += (price - pos.entry_price) * pos.shares
            else:
                unrealized_pnl += (pos.entry_price - price) * pos.shares

        current_equity = self.cash + unrealized_pnl + sum(p.shares * p.entry_price for p in self.positions)
        self.equity_curve.append({
            "timestamp": timestamp,
            "cash": round(self.cash, 2),
            "equity": round(current_equity, 2),
            "open_positions": len(self.positions)
        })

    def calculate_metrics(self) -> BacktestResult:
        """Calculate comprehensive performance metrics from closed positions and equity curve."""
        initial_cap = self.config.initial_capital
        final_eq = self.equity_curve[-1]["equity"] if self.equity_curve else self.cash
        net_profit = final_eq - initial_cap
        net_profit_pct = (net_profit / initial_cap) * 100.0

        total_trades = len(self.closed_positions)
        winning_trades = [p for p in self.closed_positions if p.pnl > 0]
        losing_trades = [p for p in self.closed_positions if p.pnl <= 0]

        n_win = len(winning_trades)
        n_loss = len(losing_trades)
        win_rate = (n_win / total_trades * 100.0) if total_trades > 0 else 0.0

        total_gain = sum(p.pnl for p in winning_trades)
        total_loss = abs(sum(p.pnl for p in losing_trades))

        profit_factor = (total_gain / total_loss) if total_loss > 0 else (99.0 if total_gain > 0 else 0.0)
        avg_win = (total_gain / n_win) if n_win > 0 else 0.0
        avg_loss = (total_loss / n_loss) if n_loss > 0 else 0.0
        payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

        # Drawdown calculation
        equities = [e["equity"] for e in self.equity_curve] if self.equity_curve else [initial_cap, final_eq]
        peak = equities[0]
        max_dd = 0.0
        max_dd_pct = 0.0

        for eq in equities:
            if eq > peak:
                peak = eq
            dd = peak - eq
            dd_pct = (dd / peak * 100.0) if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        # Sharpe Ratio (annualized assuming 250 trading days)
        returns = []
        for i in range(1, len(equities)):
            returns.append((equities[i] - equities[i-1]) / equities[i-1])
            
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = (np.mean(returns) / np.std(returns)) * math.sqrt(250 * 50) # Approx intra-day scaling
        else:
            sharpe = 0.0

        return BacktestResult(
            config=self.config,
            initial_capital=initial_cap,
            final_equity=round(final_eq, 2),
            net_profit=round(net_profit, 2),
            net_profit_pct=round(net_profit_pct, 2),
            total_trades=total_trades,
            winning_trades=n_win,
            losing_trades=n_loss,
            win_rate_pct=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            payoff_ratio=round(payoff_ratio, 2),
            max_drawdown=round(max_dd, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            sharpe_ratio=round(sharpe, 2),
            trades=self.closed_positions,
            equity_curve=self.equity_curve
        )
