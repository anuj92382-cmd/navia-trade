"""
Navia Trading API Constants
Defines standard parameters, exchanges, product types, and order types.
"""

# Exchanges
EXCHANGE_NSE = "NSE"
EXCHANGE_BSE = "BSE"
EXCHANGE_NFO = "NFO"
EXCHANGE_MCX = "MCX"
EXCHANGE_CDS = "CDS"

# Transaction Types
TRANSACTION_BUY = "B"
TRANSACTION_SELL = "S"

# Product Types
PRODUCT_CNC = "CNC"    # Cash and Carry (Delivery for Equity)
PRODUCT_MIS = "MIS"    # Margin Intraday Square-off
PRODUCT_NRML = "NRML"  # Normal (F&O / Commodity overnight)
PRODUCT_CO = "CO"      # Cover Order
PRODUCT_BO = "BO"      # Bracket Order

# Order Types (Price Types)
ORDER_TYPE_MARKET = "MKT"  # Market Order
ORDER_TYPE_LIMIT = "LMT"   # Limit Order
ORDER_TYPE_SL = "SL"       # Stop-Loss Limit
ORDER_TYPE_SLM = "SL-M"    # Stop-Loss Market

# Validity / Retention
VALIDITY_DAY = "DAY"
VALIDITY_IOC = "IOC"       # Immediate or Cancel

# API Activity Endpoints
ACTIVITY_SEND_OTP = "SendOTP"
ACTIVITY_VERIFY_OTP = "VerifyOTP"
ACTIVITY_PLACE_ORDER = "PlaceOrder"
ACTIVITY_MODIFY_ORDER = "ModifyOrder"
ACTIVITY_CANCEL_ORDER = "CancelOrder"
ACTIVITY_ORDER_BOOK = "OrderBook"
ACTIVITY_TRADE_BOOK = "TradeBook"
ACTIVITY_POSITIONS = "Positions"
ACTIVITY_HOLDINGS = "Holdings"
ACTIVITY_LIMITS = "Limits"
ACTIVITY_GET_QUOTE = "GetQuote"
