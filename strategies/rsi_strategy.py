"""
RSI (Relative Strength Index) Intraday Momentum Strategy
Buys when oversold conditions recover and sells when overbought conditions reverse.
"""

from collections import deque
import logging
from typing import Any, Dict
import pandas as pd

from navia.client import NaviaClient
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("RSIStrategy")


class RSIScalperStrategy(BaseStrategy):
    """
    RSI Momentum Strategy:
    - Long Signal: RSI drops below oversold (e.g. 30) then bounces back above 30
    - Short Signal: RSI rises above overbought (e.g. 70) then drops back below 70
    """

    def __init__(
        self,
        client: NaviaClient,
        symbol: str,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        quantity: int = 1,
        exchange: str = "NSE",
        product: str = "MIS",
        stop_loss_pct: float = 0.8,
        take_profit_pct: float = 1.5,
        max_daily_loss: float = 5000.0,
    ):
        super().__init__(
            name=f"RSI_{rsi_period}_Scalper",
            client=client,
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            product=product,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            max_daily_loss=max_daily_loss,
        )
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.prices: deque = deque(maxlen=max(rsi_period * 5, 150))
        self.prev_rsi: float = 50.0

    def calculate_rsi(self) -> float:
        """Compute RSI from historical price window using Wilder's formula."""
        if len(self.prices) < self.rsi_period + 1:
            return 50.0

        series = pd.Series(list(self.prices))
        delta = series.diff()

        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1 / self.rsi_period, min_periods=self.rsi_period).mean()
        avg_loss = loss.ewm(alpha=1 / self.rsi_period, min_periods=self.rsi_period).mean()

        rs = avg_gain / avg_loss
        rsi_series = 100 - (100 / (1 + rs))
        return float(rsi_series.iloc[-1])

    def on_tick(self, tick: Dict[str, Any]) -> None:
        """Handle incoming market tick and evaluate RSI triggers."""
        ltp = float(tick.get("ltp") or tick.get("last_price") or 0.0)
        if ltp <= 0:
            return

        self.last_ltp = ltp
        self.prices.append(ltp)

        # Check Stop Loss / Target
        if self.check_risk_management(ltp):
            return

        if len(self.prices) < self.rsi_period + 1:
            return

        rsi = self.calculate_rsi()
        logger.debug("[%s] LTP: %.2f | RSI: %.2f | Position: %d", self.symbol, ltp, rsi, self.current_position)

        # Bullish recovery: Previous RSI was below oversold, now crossing back above
        if self.prev_rsi <= self.oversold and rsi > self.oversold:
            if self.current_position <= 0:
                logger.info("🟢 RSI Bullish Recovery: %.2f crossed above %.2f", rsi, self.oversold)
                if self.current_position < 0:
                    self.square_off("RSI Oversold reversal")
                self.buy(qty=self.quantity, reason=f"RSI bounced from oversold ({rsi:.1f})")

        # Bearish reversal: Previous RSI was above overbought, now dropping back below
        elif self.prev_rsi >= self.overbought and rsi < self.overbought:
            if self.current_position >= 0:
                logger.info("🔴 RSI Bearish Reversal: %.2f dropped below %.2f", rsi, self.overbought)
                if self.current_position > 0:
                    self.square_off("RSI Overbought reversal")
                self.sell(qty=self.quantity, reason=f"RSI dropped from overbought ({rsi:.1f})")

        self.prev_rsi = rsi
