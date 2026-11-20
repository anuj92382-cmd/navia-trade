"""
Navia WebSocket Client for Real-Time Streaming Data
Provides live tick feeds (LTP, Volume, Bid/Ask) and offline simulation.
"""

import json
import logging
import random
import threading
import time
from typing import Callable, Dict, List, Optional
import websocket

logger = logging.getLogger("NaviaWebSocket")


class NaviaWebSocketClient:
    """WebSocket client for streaming live market quotes from Navia."""

    def __init__(
        self,
        auth_token: str,
        ws_url: str = "wss://naviaapt.navia.co.in:9003/ws",
        on_tick_callback: Optional[Callable[[Dict], None]] = None,
        simulate: bool = False,
    ):
        """
        :param auth_token: Active session AuthToken
        :param ws_url: Navia WebSocket URL
        :param on_tick_callback: Function called on each incoming tick
        :param simulate: If True, generate realistic simulated price ticks for testing
        """
        self.auth_token = auth_token
        self.ws_url = ws_url
        self.on_tick = on_tick_callback
        self.simulate = simulate
        self.subscribed_symbols: List[str] = []

        self.ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._sim_prices: Dict[str, float] = {}

    def subscribe(self, symbols: List[str]) -> None:
        """Subscribe to live market feeds for given symbols."""
        for s in symbols:
            if s not in self.subscribed_symbols:
                self.subscribed_symbols.append(s)
                # Seed base price for simulation
                if s not in self._sim_prices:
                    self._sim_prices[s] = 2500.0 if "RELIANCE" in s else 1000.0

        if self.ws and self.ws.sock and self.ws.sock.connected:
            sub_msg = {
                "action": "subscribe",
                "symbols": symbols,
                "token": self.auth_token,
            }
            self.ws.send(json.dumps(sub_msg))
            logger.info("Subscribed to symbols: %s", symbols)

    def start(self) -> None:
        """Start the WebSocket connection or simulator in a background thread."""
        self._running = True

        if self.simulate:
            logger.info("Starting Simulated WebSocket Tick Generator...")
            self._thread = threading.Thread(target=self._simulator_loop, daemon=True)
            self._thread.start()
            return

        logger.info("Connecting to Navia WebSocket: %s", self.ws_url)
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header={"AuthToken": self.auth_token},
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the WebSocket connection."""
        self._running = False
        if self.ws:
            self.ws.close()
        logger.info("WebSocket stopped.")

    # =========================================================================
    # WebSocket Event Handlers
    # =========================================================================

    def _on_open(self, ws):
        logger.info("WebSocket connected successfully.")
        if self.subscribed_symbols:
            self.subscribe(self.subscribed_symbols)

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if self.on_tick:
                self.on_tick(data)
        except Exception as e:
            logger.error("Error parsing WebSocket message: %s", e)

    def _on_error(self, ws, error):
        logger.error("WebSocket error: %s", error)

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info("WebSocket connection closed. Code: %s, Msg: %s", close_status_code, close_msg)

    # =========================================================================
    # Simulated Tick Generator for Testing
    # =========================================================================

    def _simulator_loop(self) -> None:
        """Generates random walk ticks for testing strategies offline."""
        while self._running:
            for symbol in list(self.subscribed_symbols):
                current_price = self._sim_prices.get(symbol, 1000.0)
                # Random walk: price changes between -0.3% to +0.3%
                delta_pct = random.uniform(-0.003, 0.003)
                new_price = round(current_price * (1 + delta_pct), 2)
                self._sim_prices[symbol] = new_price

                simulated_tick = {
                    "symbol": symbol,
                    "ltp": new_price,
                    "volume": random.randint(100, 5000),
                    "bid": round(new_price - 0.05, 2),
                    "ask": round(new_price + 0.05, 2),
                    "timestamp": time.time(),
                }

                if self.on_tick:
                    self.on_tick(simulated_tick)

            time.sleep(1.0)
