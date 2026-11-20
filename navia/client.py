"""
Navia Trading API Python Client
Official REST API Wrapper for Navia Markets Ltd.
Supports Live Trading and Paper/Simulated Trading modes.
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
import requests

from navia.constants import (
    ACTIVITY_CANCEL_ORDER,
    ACTIVITY_GET_QUOTE,
    ACTIVITY_HOLDINGS,
    ACTIVITY_LIMITS,
    ACTIVITY_MODIFY_ORDER,
    ACTIVITY_ORDER_BOOK,
    ACTIVITY_PLACE_ORDER,
    ACTIVITY_POSITIONS,
    ACTIVITY_SEND_OTP,
    ACTIVITY_TRADE_BOOK,
    ACTIVITY_VERIFY_OTP,
    EXCHANGE_NSE,
    ORDER_TYPE_MARKET,
    PRODUCT_MIS,
    TRANSACTION_BUY,
    TRANSACTION_SELL,
    VALIDITY_DAY,
)

logger = logging.getLogger("NaviaClient")


class NaviaClient:
    """Client for connecting and trading with the Navia Markets Trading API."""

    def __init__(
        self,
        client_code: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        auth_token: Optional[str] = None,
        base_url: str = "https://naviaapt.navia.co.in:9003",
        paper_trading: bool = False,
        timeout: int = 15,
    ):
        """
        Initialize the Navia API Client.

        :param client_code: Navia User ID / UCC (e.g. '12345678')
        :param password: Account login password
        :param api_key: Developer API Key (if provided by dashboard)
        :param auth_token: Existing session AuthToken (if already authenticated)
        :param base_url: Navia API Server Base URL (e.g., https://naviaapt.navia.co.in:9003)
        :param paper_trading: Set True for simulated execution without placing real orders
        :param timeout: HTTP request timeout in seconds
        """
        self.client_code = client_code
        self.password = password
        self.api_key = api_key
        self.auth_token = auth_token or "DEFAULT"
        self.base_url = base_url.rstrip("/")
        self.paper_trading = paper_trading
        self.timeout = timeout
        self.session = requests.Session()

        # Paper trading virtual ledger
        self.virtual_orders: Dict[str, Dict[str, Any]] = {}
        self.virtual_positions: Dict[str, Dict[str, Any]] = {}
        self.virtual_funds: float = 100000.0  # ₹1,00,000 default virtual capital

        logger.info(
            "NaviaClient initialized. Mode: %s",
            "PAPER TRADING (SIMULATION)" if paper_trading else "LIVE TRADING",
        )

    def _get_headers(self) -> Dict[str, str]:
        """Construct standard HTTP headers required by Navia API."""
        headers = {
            "Content-Type": "application/json",
            "AuthToken": self.auth_token if self.auth_token else "DEFAULT",
            "Module": "DEFAULT",
            "Source": "WEB",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _send_request(
        self, activity: str, payload: Optional[Dict[str, Any]] = None, method: str = "POST"
    ) -> Dict[str, Any]:
        """
        Send an HTTP request to the Navia API gateway.

        :param activity: The Activity query parameter (e.g. SendOTP, PlaceOrder)
        :param payload: JSON body dictionary
        :param method: HTTP Method (default: POST)
        :return: JSON response dictionary
        """
        url = f"{self.base_url}/?Activity={activity}"
        headers = self._get_headers()
        body = json.dumps(payload) if payload is not None else "{}"

        logger.debug("Request -> URL: %s, Activity: %s, Body: %s", url, activity, body)

        try:
            if method.upper() == "POST":
                resp = self.session.post(url, headers=headers, data=body, timeout=self.timeout)
            else:
                resp = self.session.get(url, headers=headers, timeout=self.timeout)

            resp.raise_for_status()
            data = resp.json()
            logger.debug("Response <- %s: %s", activity, data)
            return data
        except requests.exceptions.RequestException as e:
            logger.error("HTTP Error during %s: %s", activity, e)
            raise ConnectionError(f"Navia API Connection Error [{activity}]: {e}") from e
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON response from server: %s", resp.text if 'resp' in locals() else '')
            raise ValueError(f"Navia API Invalid Response format: {e}") from e

    # =========================================================================
    # Authentication Endpoints
    # =========================================================================

    def send_otp(self, client_code: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Step 1 of Login: Send OTP to user's registered phone / email.

        :param client_code: Client UCC (defaults to initialized code)
        :param password: Login password (defaults to initialized password)
        :return: Server response dict with RequestID and status
        """
        ucc = client_code or self.client_code
        pwd = password or self.password

        if not ucc or not pwd:
            raise ValueError("Client code (uid) and password (pwd) are required to send OTP.")

        payload = {"uid": ucc, "pwd": pwd}
        response = self._send_request(ACTIVITY_SEND_OTP, payload)

        status = response.get("Status") or ("OK" if response.get("StatusCode") == 0 else "ERROR")
        if status == "OK":
            logger.info("OTP sent successfully for Client: %s", ucc)
        else:
            logger.warning("Failed to send OTP: %s", response.get("Message"))

        return response

    def verify_otp(self, otp: str, client_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Step 2 of Login: Validate OTP / TOTP and generate active session token.

        :param otp: One-Time Password received on SMS/Email or authenticator TOTP
        :param client_code: Client UCC
        :return: Server response dict with session AuthToken
        """
        ucc = client_code or self.client_code
        if not ucc:
            raise ValueError("Client code (uid) is required for OTP verification.")

        payload = {"uid": ucc, "otp": str(otp).strip()}
        response = self._send_request(ACTIVITY_VERIFY_OTP, payload)

        # Extract token from response
        token = (
            response.get("AuthToken")
            or response.get("Token")
            or response.get("token")
            or (response.get("ResponceDataObject") or {}).get("AuthToken")
        )

        if token:
            self.auth_token = token
            logger.info("Authentication successful. Session AuthToken captured.")
        else:
            logger.info("OTP validation response: %s", response.get("Message", "Processed"))

        return response

    def set_auth_token(self, token: str) -> None:
        """Directly set a known active session AuthToken."""
        self.auth_token = token
        logger.info("Session AuthToken set manually.")

    # =========================================================================
    # Order Placement & Management Endpoints
    # =========================================================================

    def place_order(
        self,
        symbol: str,
        exchange: str = EXCHANGE_NSE,
        side: str = TRANSACTION_BUY,
        qty: int = 1,
        product: str = PRODUCT_MIS,
        order_type: str = ORDER_TYPE_MARKET,
        price: float = 0.0,
        trigger_price: float = 0.0,
        validity: str = VALIDITY_DAY,
    ) -> Dict[str, Any]:
        """
        Place an order (Equity, F&O, Commodities).

        :param symbol: Trading symbol (e.g. 'RELIANCE-EQ', 'TCS-EQ', 'NIFTY26NOV24500CE')
        :param exchange: 'NSE', 'BSE', 'NFO', 'MCX'
        :param side: 'B' (BUY) or 'S' (SELL)
        :param qty: Quantity to trade
        :param product: 'MIS' (Intraday), 'CNC' (Delivery), 'NRML'
        :param order_type: 'MKT' (Market), 'LMT' (Limit), 'SL', 'SL-M'
        :param price: Price for limit orders (0.0 for market)
        :param trigger_price: Trigger price for Stop Loss orders
        :param validity: 'DAY' or 'IOC'
        :return: Order response dictionary containing order id/status
        """
        side = side.upper()
        if side in ("BUY", "B"):
            side = TRANSACTION_BUY
        elif side in ("SELL", "S"):
            side = TRANSACTION_SELL

        # If paper trading is active, simulate execution locally
        if self.paper_trading:
            return self._simulate_place_order(
                symbol=symbol,
                exchange=exchange,
                side=side,
                qty=qty,
                product=product,
                order_type=order_type,
                price=price,
            )

        payload = {
            "exch": exchange,
            "tsym": symbol,
            "qty": int(qty),
            "prc": float(price),
            "prd": product,
            "trantype": side,
            "prctyp": order_type,
            "ret": validity,
        }
        if trigger_price > 0:
            payload["trgprc"] = float(trigger_price)

        logger.info("Placing LIVE order: %s %s %d %s @ %s", side, symbol, qty, product, order_type)
        return self._send_request(ACTIVITY_PLACE_ORDER, payload)

    def modify_order(
        self,
        order_id: str,
        qty: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
        trigger_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Modify an open/pending order.

        :param order_id: Order identification number
        :param qty: New quantity (optional)
        :param price: New price (optional)
        :param order_type: New order type (optional)
        :param trigger_price: New trigger price (optional)
        """
        if self.paper_trading:
            return self._simulate_modify_order(order_id, qty, price, order_type)

        payload: Dict[str, Any] = {"orderNumber": str(order_id)}
        if qty is not None:
            payload["qty"] = int(qty)
        if price is not None:
            payload["prc"] = float(price)
        if order_type is not None:
            payload["prctyp"] = order_type
        if trigger_price is not None:
            payload["trgprc"] = float(trigger_price)

        logger.info("Modifying LIVE order: %s", order_id)
        return self._send_request(ACTIVITY_MODIFY_ORDER, payload)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an open/pending order.

        :param order_id: Order identification number
        """
        if self.paper_trading:
            return self._simulate_cancel_order(order_id)

        payload = {"orderNumber": str(order_id)}
        logger.info("Cancelling LIVE order: %s", order_id)
        return self._send_request(ACTIVITY_CANCEL_ORDER, payload)

    # =========================================================================
    # Portfolio, Book & Account Queries
    # =========================================================================

    def get_order_book(self) -> List[Dict[str, Any]]:
        """Fetch the order book (all orders placed today)."""
        if self.paper_trading:
            return list(self.virtual_orders.values())

        resp = self._send_request(ACTIVITY_ORDER_BOOK, {})
        return self._extract_list_data(resp)

    def get_trade_book(self) -> List[Dict[str, Any]]:
        """Fetch the trade book (executed trades today)."""
        if self.paper_trading:
            return [o for o in self.virtual_orders.values() if o.get("status") == "COMPLETE"]

        resp = self._send_request(ACTIVITY_TRADE_BOOK, {})
        return self._extract_list_data(resp)

    def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch current open/day positions."""
        if self.paper_trading:
            return list(self.virtual_positions.values())

        resp = self._send_request(ACTIVITY_POSITIONS, {})
        return self._extract_list_data(resp)

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Fetch long-term portfolio holdings."""
        if self.paper_trading:
            return []

        resp = self._send_request(ACTIVITY_HOLDINGS, {})
        return self._extract_list_data(resp)

    def get_limits(self) -> Dict[str, Any]:
        """Fetch available cash, margin limits, and collateral."""
        if self.paper_trading:
            return {
                "availableCash": self.virtual_funds,
                "usedMargin": sum(
                    abs(p["qty"]) * p["avgPrice"] for p in self.virtual_positions.values()
                ),
                "virtualMode": True,
            }

        return self._send_request(ACTIVITY_LIMITS, {})

    def get_quote(self, symbol: str, exchange: str = EXCHANGE_NSE) -> Dict[str, Any]:
        """
        Fetch market snapshot / quote for a symbol.

        :param symbol: Trading symbol (e.g. 'RELIANCE-EQ')
        :param exchange: Exchange ('NSE', 'BSE', 'NFO')
        """
        payload = {"exch": exchange, "tsym": symbol}
        return self._send_request(ACTIVITY_GET_QUOTE, payload)

    # =========================================================================
    # Helper & Paper Trading Engine
    # =========================================================================

    def _extract_list_data(self, response: Any) -> List[Dict[str, Any]]:
        """Normalize list payload from various Navia response structures."""
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            for key in ("Responce", "Response", "data", "orders", "positions", "holdings"):
                if key in response and isinstance(response[key], list):
                    return response[key]
        return []

    def _simulate_place_order(
        self,
        symbol: str,
        exchange: str,
        side: str,
        qty: int,
        product: str,
        order_type: str,
        price: float,
    ) -> Dict[str, Any]:
        """Simulate order execution in Paper Trading mode."""
        order_id = f"SIM_{uuid.uuid4().hex[:10].upper()}"
        fill_price = price if price > 0 else 1000.0  # Fallback dummy price for simulation

        simulated_order = {
            "orderNumber": order_id,
            "status": "COMPLETE",
            "symbol": symbol,
            "exchange": exchange,
            "side": side,
            "qty": qty,
            "product": product,
            "orderType": order_type,
            "price": fill_price,
            "message": "Order executed in Paper Trading simulation",
        }
        self.virtual_orders[order_id] = simulated_order

        # Update virtual position
        pos_key = f"{exchange}:{symbol}:{product}"
        current_pos = self.virtual_positions.get(
            pos_key,
            {
                "symbol": symbol,
                "exchange": exchange,
                "product": product,
                "qty": 0,
                "avgPrice": 0.0,
                "realizedPnl": 0.0,
            },
        )

        signed_qty = qty if side == TRANSACTION_BUY else -qty
        new_qty = current_pos["qty"] + signed_qty

        if new_qty == 0:
            # Closed position
            pnl = (fill_price - current_pos["avgPrice"]) * (qty if side == TRANSACTION_SELL else -qty)
            current_pos["realizedPnl"] += pnl
            current_pos["qty"] = 0
            current_pos["avgPrice"] = 0.0
        else:
            current_pos["avgPrice"] = fill_price
            current_pos["qty"] = new_qty

        self.virtual_positions[pos_key] = current_pos

        logger.info(
            "[PAPER TRADING] Order %s COMPLETE: %s %d %s @ %.2f. New Pos: %d",
            order_id,
            side,
            qty,
            symbol,
            fill_price,
            new_qty,
        )
        return {"Status": "OK", "StatusCode": 0, "orderNumber": order_id, "status": "COMPLETE"}

    def _simulate_modify_order(
        self,
        order_id: str,
        qty: Optional[int],
        price: Optional[float],
        order_type: Optional[str],
    ) -> Dict[str, Any]:
        if order_id in self.virtual_orders:
            if qty:
                self.virtual_orders[order_id]["qty"] = qty
            if price:
                self.virtual_orders[order_id]["price"] = price
            if order_type:
                self.virtual_orders[order_id]["orderType"] = order_type
            return {"Status": "OK", "StatusCode": 0, "orderNumber": order_id, "message": "Modified"}
        return {"Status": "ERROR", "StatusCode": -1, "message": "Order not found"}

    def _simulate_cancel_order(self, order_id: str) -> Dict[str, Any]:
        if order_id in self.virtual_orders:
            self.virtual_orders[order_id]["status"] = "CANCELLED"
            return {"Status": "OK", "StatusCode": 0, "orderNumber": order_id, "message": "Cancelled"}
        return {"Status": "ERROR", "StatusCode": -1, "message": "Order not found"}
