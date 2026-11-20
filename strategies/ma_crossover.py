"""
Moving Average Crossover Algo Trading Strategy (EMA / SMA)
Classic trend-following strategy using Fast and Slow Moving Averages.
"""

from collections import deque
import logging
from typing import Any, Dict
import pandas as pd

from navia.client import NaviaClient
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("MACrossoverStrategy")


class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy:
    - Long Signal: Fast EMA crosses ABOVE Slow EMA
    - Short/Exit Signal: Fast EMA crosses BELOW Slow EMA
    """

    def __init__(
        self,
        client: NaviaClient,
        symbol: str,
        fast_period: int = 9,
        slow_period: int = 21,
        quantity: int = 1,
        exchange: str = "NSE",
        product: str = "MIS",
        stop_loss_pct: float = 1.0,
        take_profit_pct: float = 2.0,
        max_daily_loss: float = 5000.0,
    ):
        super().__init__(
            name=f"EMA_{fast_period}_{slow_period}_Crossover",
            client=client,
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            product=product,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            max_daily_loss=max_daily_loss,
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prices: deque = deque(maxlen=max(slow_period * 3, 100))

        self.prev_fast_ma: float = 0.0
        self.prev_slow_ma: float = 0.0

    def on_tick(self, tick: Dict[str, Any]) -> None:
        """Handle incoming market tick."""
        ltp = float(tick.get("ltp") or tick.get("last_price") or 0.0)
        if ltp <= 0:
            return

        self.last_ltp = ltp
        self.prices.append(ltp)

        # First verify Risk Management (Stop loss / Take profit)
        if self.check_risk_management(ltp):
            return

        # Need sufficient price bars to calculate moving averages
        if len(self.prices) < self.slow_period:
            return

        # Calculate EMAs using pandas
        series = pd.Series(list(self.prices))
        fast_ma = series.ewm(span=self.fast_period, adjust=False).mean().iloc[-1]
        slow_ma = series.ewm(span=self.slow_period, adjust=False).mean().iloc[-1]

        # Log indicator state periodically
        logger.debug(
            "[%s] LTP: %.2f | FastEMA(%d): %.2f | SlowEMA(%d): %.2f | Pos: %d",
            self.symbol,
            ltp,
            self.fast_period,
            fast_ma,
            self.slow_period,
            slow_ma,
            self.current_position,
        )

        # Detect crossover if we have previous values
        if self.prev_fast_ma > 0 and self.prev_slow_ma > 0:
            bullish_cross = (self.prev_fast_ma <= self.prev_slow_ma) and (fast_ma > slow_ma)
            bearish_cross = (self.prev_fast_ma >= self.prev_slow_ma) and (fast_ma < slow_ma)

            # --- Bullish Golden Cross ---
            if bullish_cross:
                logger.info(
                    "🚀 Bullish Crossover detected! Fast EMA (%.2f) > Slow EMA (%.2f)",
                    fast_ma,
                    slow_ma,
                )
                if self.current_position < 0:
                    # Close existing short first
                    self.square_off("Bullish Crossover reversal")
                if self.current_position == 0:
                    self.buy(
                        qty=self.quantity,
                        price=0.0,
                        reason=f"Bullish EMA Crossover ({fast_ma:.2f} > {slow_ma:.2f})",
                    )

            # --- Bearish Death Cross ---
            elif bearish_cross:
                logger.info(
                    "🔻 Bearish Crossover detected! Fast EMA (%.2f) < Slow EMA (%.2f)",
                    fast_ma,
                    slow_ma,
                )
                if self.current_position > 0:
                    # Close existing long first
                    self.square_off("Bearish Crossover reversal")
                if self.current_position == 0:
                    self.sell(
                        qty=self.quantity,
                        price=0.0,
                        reason=f"Bearish EMA Crossover ({fast_ma:.2f} < {slow_ma:.2f})",
                    )

        # Update previous values for next tick
        self.prev_fast_ma = fast_ma
        self.prev_slow_ma = slow_ma
