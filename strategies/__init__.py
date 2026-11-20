"""
Algorithmic Trading Strategies Package
"""

from strategies.base_strategy import BaseStrategy
from strategies.ma_crossover import MovingAverageCrossoverStrategy
from strategies.rsi_strategy import RSIScalperStrategy

__all__ = [
    "BaseStrategy",
    "MovingAverageCrossoverStrategy",
    "RSIScalperStrategy",
]
