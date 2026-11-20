"""
Base Algorithmic Trading Strategy
Provides state tracking, position sizing, risk management (Stop Loss & Target),
and lifecycle hooks for algorithmic strategies.
"""

from abc import ABC, abstractmethod
import logging
import time
from typing import Any, Dict, List, Optional

from navia.client import NaviaClient
from navia.constants import (
    EXCHANGE_NSE,
    ORDER_TYPE_MARKET,
    PRODUCT_MIS,
    TRANSACTION_BUY,
    TRANSACTION_SELL,
)

logger = logging.getLogger("BaseStrategy")


class BaseStrategy(ABC):
    """Abstract Base Class for all Algo Trading Strategies."""

    def __init__(
        self,
        name: str,
        client: NaviaClient,
        symbol: str,
        exchange: str = EXCHANGE_NSE,
        quantity: int = 1,
        product: str = PRODUCT_MIS,
        stop_loss_pct: float = 1.0,     # Stop loss % (e.g. 1.0%)
        take_profit_pct: float = 2.0,   # Profit target % (e.g. 2.0%)
        max_daily_loss: float = 5000.0, # Circuit breaker max loss in ₹
    ):
        self.name = name
        self.client = client
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.product = product
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_daily_loss = max_daily_loss

        # Position and PnL state
        self.current_position: int = 0  # > 0 for Long, < 0 for Short, 0 for Flat
        self.entry_price: float = 0.0
        self.last_ltp: float = 0.0
        self.realized_pnl: float = 0.0
        self.trades: List[Dict[str, Any]] = []
        self.is_running: bool = False

    def start(self) -> None:
        """Initialize and start the strategy."""
        self.is_running = True
        logger.info(
            "Strategy [%s] STARTED for %s:%s | Qty: %d | SL: %.1f%% | Target: %.1f%%",
            self.name,
            self.exchange,
            self.symbol,
            self.quantity,
            self.stop_loss_pct,
            self.take_profit_pct,
        )
        self.on_start()

    def stop(self) -> None:
        """Stop the strategy and square off open positions."""
        self.is_running = False
        logger.info("Strategy [%s] STOPPING...", self.name)
        if self.current_position != 0:
            logger.info("Auto squaring-off open position: %d", self.current_position)
            self.square_off("Strategy stopped")
        self.on_stop()
        self.print_summary()

    def on_start(self) -> None:
        """Hook called when strategy starts."""
        pass

    def on_stop(self) -> None:
        """Hook called when strategy stops."""
        pass

    @abstractmethod
    def on_tick(self, tick: Dict[str, Any]) -> None:
        """
        Hook called on every incoming market tick.
        Must be implemented by subclasses to calculate indicators and generate signals.
        """
        pass

    # =========================================================================
    # Trade Execution Helpers
    # =========================================================================

    def buy(self, qty: Optional[int] = None, price: float = 0.0, reason: str = "") -> Optional[Dict]:
        """Execute a BUY order."""
        if not self.is_running:
            logger.warning("Cannot buy: Strategy is stopped.")
            return None

        order_qty = qty or self.quantity
        logger.info("SIGNAL BUY: %s | Qty: %d | Reason: %s", self.symbol, order_qty, reason)

        try:
            resp = self.client.place_order(
                symbol=self.symbol,
                exchange=self.exchange,
                side=TRANSACTION_BUY,
                qty=order_qty,
                product=self.product,
                order_type=ORDER_TYPE_MARKET if price == 0.0 else "LMT",
                price=price,
            )

            fill_price = price if price > 0 else self.last_ltp
            self._record_trade(side="BUY", qty=order_qty, price=fill_price, reason=reason)
            self.current_position += order_qty
            self.entry_price = fill_price
            return resp
        except Exception as e:
            logger.error("Failed to execute BUY order: %s", e)
            return None

    def sell(self, qty: Optional[int] = None, price: float = 0.0, reason: str = "") -> Optional[Dict]:
        """Execute a SELL order."""
        if not self.is_running:
            logger.warning("Cannot sell: Strategy is stopped.")
            return None

        order_qty = qty or self.quantity
        logger.info("SIGNAL SELL: %s | Qty: %d | Reason: %s", self.symbol, order_qty, reason)

        try:
            resp = self.client.place_order(
                symbol=self.symbol,
                exchange=self.exchange,
                side=TRANSACTION_SELL,
                qty=order_qty,
                product=self.product,
                order_type=ORDER_TYPE_MARKET if price == 0.0 else "LMT",
                price=price,
            )

            fill_price = price if price > 0 else self.last_ltp
            self._record_trade(side="SELL", qty=order_qty, price=fill_price, reason=reason)
            self.current_position -= order_qty
            self.entry_price = fill_price
            return resp
        except Exception as e:
            logger.error("Failed to execute SELL order: %s", e)
            return None

    def square_off(self, reason: str = "Manual square-off") -> None:
        """Close current position to 0."""
        if self.current_position > 0:
            self.sell(qty=self.current_position, reason=f"Square-off ({reason})")
        elif self.current_position < 0:
            self.buy(qty=abs(self.current_position), reason=f"Square-off ({reason})")

    # =========================================================================
    # Risk Management & Guardrails
    # =========================================================================

    def check_risk_management(self, current_price: float) -> bool:
        """
        Check Stop Loss, Take Profit, and Max Daily Loss.
        Returns True if a risk exit was triggered.
        """
        if self.current_position == 0 or self.entry_price == 0:
            return False

        # Calculate unrealized P&L percentage
        if self.current_position > 0:  # Long
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # Short
            pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100

        # Stop Loss Triggered
        if pnl_pct <= -self.stop_loss_pct:
            logger.warning(
                "STOP LOSS HIT for %s: PnL %.2f%% <= -%.1f%% (Entry: %.2f, Current: %.2f)",
                self.symbol,
                pnl_pct,
                self.stop_loss_pct,
                self.entry_price,
                current_price,
            )
            self.square_off(f"Stop Loss Triggered (-{self.stop_loss_pct}%)")
            return True

        # Take Profit Triggered
        if pnl_pct >= self.take_profit_pct:
            logger.info(
                "TAKE PROFIT HIT for %s: PnL +%.2f%% >= +%.1f%% (Entry: %.2f, Current: %.2f)",
                self.symbol,
                pnl_pct,
                self.take_profit_pct,
                self.entry_price,
                current_price,
            )
            self.square_off(f"Take Profit Triggered (+{self.take_profit_pct}%)")
            return True

        # Max Daily Loss circuit breaker
        if (self.realized_pnl + self.unrealized_pnl(current_price)) <= -self.max_daily_loss:
            logger.critical(
                "MAX DAILY LOSS LIMIT BREACHED (-₹%.2f). Halting Strategy!",
                self.max_daily_loss,
            )
            self.square_off("Max Daily Loss Limit Breached")
            self.stop()
            return True

        return False

    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate current unrealized P&L in currency."""
        if self.current_position == 0 or self.entry_price == 0:
            return 0.0
        return (current_price - self.entry_price) * self.current_position

    def _record_trade(self, side: str, qty: int, price: float, reason: str) -> None:
        """Internal ledger of executed trades."""
        trade = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "side": side,
            "qty": qty,
            "price": price,
            "reason": reason,
        }
        self.trades.append(trade)

    def print_summary(self) -> None:
        """Print summary of strategy performance."""
        print("\n" + "=" * 50)
        print(f"📊 Strategy Performance Summary: {self.name}")
        print("=" * 50)
        print(f"Symbol:               {self.symbol} ({self.exchange})")
        print(f"Total Trades:         {len(self.trades)}")
        print(f"Final Position:       {self.current_position}")
        print(f"Realized P&L:         ₹{self.realized_pnl:.2f}")
        print("=" * 50 + "\n")
