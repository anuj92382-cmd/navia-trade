"""
Configuration Module for Navia Algo Trading System.
Loads credentials and trading parameters from environment variables or .env file.
"""

import os
from pathlib import Path


def load_env_file(dotenv_path: str = ".env") -> None:
    """Simple parser to load .env file without external dependencies."""
    path = Path(dotenv_path)
    if not path.is_file():
        return

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("\"'").strip()
            if key and key not in os.environ:
                os.environ[key] = val


# Load .env file if available
load_env_file()

# Navia Account Credentials
NAVIA_CLIENT_CODE = os.getenv("NAVIA_CLIENT_CODE", "")
NAVIA_PASSWORD = os.getenv("NAVIA_PASSWORD", "")
NAVIA_API_KEY = os.getenv("NAVIA_API_KEY", "")
NAVIA_AUTH_TOKEN = os.getenv("NAVIA_AUTH_TOKEN", "")

# Server Endpoints
NAVIA_BASE_URL = os.getenv("NAVIA_BASE_URL", "https://naviaapt.navia.co.in:9003")
NAVIA_WS_URL = os.getenv("NAVIA_WS_URL", "wss://naviaapt.navia.co.in:9003/ws")

# Execution Mode: Set to False for REAL LIVE TRADING
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() in ("true", "1", "yes")

# Default Algo Strategy Parameters
DEFAULT_EXCHANGE = os.getenv("DEFAULT_EXCHANGE", "NSE")
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "RELIANCE-EQ")
DEFAULT_QUANTITY = int(os.getenv("DEFAULT_QUANTITY", "1"))
DEFAULT_PRODUCT = os.getenv("DEFAULT_PRODUCT", "MIS")  # MIS (Intraday) or CNC (Delivery)

# Risk Management
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "1.0"))      # 1% Stop Loss
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "2.0"))  # 2% Profit Target
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "5000.0")) # Max ₹5,000 loss limit
