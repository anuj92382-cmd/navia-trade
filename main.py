"""
Main Algorithmic Trading Runner for Navia API
Executes automated trading strategies with real-time risk controls.
"""

import argparse
import logging
import signal
import sys
import time

import config
from navia import NaviaClient, NaviaWebSocketClient
from strategies import MovingAverageCrossoverStrategy, RSIScalperStrategy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("NaviaAlgoRunner")


def parse_args():
    parser = argparse.ArgumentParser(description="Navia Algorithmic Trading Runner")
    parser.add_argument(
        "--strategy",
        choices=["ma", "rsi"],
        default="ma",
        help="Strategy to run: 'ma' (Moving Average Crossover) or 'rsi' (RSI Scalper)",
    )
    parser.add_argument(
        "--symbol",
        default=config.DEFAULT_SYMBOL,
        help=f"Trading symbol (default: {config.DEFAULT_SYMBOL})",
    )
    parser.add_argument(
        "--exchange",
        default=config.DEFAULT_EXCHANGE,
        help=f"Exchange (default: {config.DEFAULT_EXCHANGE})",
    )
    parser.add_argument(
        "--qty",
        type=int,
        default=config.DEFAULT_QUANTITY,
        help=f"Order quantity per trade (default: {config.DEFAULT_QUANTITY})",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable LIVE TRADING with real money (default is Paper Trading)",
    )
    parser.add_argument(
        "--simulate-feed",
        action="store_true",
        default=False,
        help="Simulate market tick data (useful for testing outside market hours)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    is_paper_trading = not args.live if args.live else config.PAPER_TRADING

    print("\n" + "=" * 65)
    print("🤖 NAVIA ALGO TRADING ENGINE")
    print("=" * 65)
    print(f"Strategy:       {args.strategy.upper()}")
    print(f"Symbol:         {args.symbol} ({args.exchange})")
    print(f"Quantity:       {args.qty}")
    print(f"Mode:           {'🔴 LIVE TRADING (REAL MONEY)' if not is_paper_trading else '🟢 PAPER TRADING (SIMULATION)'}")
    print(f"Stop Loss:      {config.STOP_LOSS_PCT}%")
    print(f"Take Profit:    {config.TAKE_PROFIT_PCT}%")
    print(f"Max Daily Loss: ₹{config.MAX_DAILY_LOSS}")
    print("=" * 65 + "\n")

    # Initialize Navia Client
    client = NaviaClient(
        client_code=config.NAVIA_CLIENT_CODE,
        password=config.NAVIA_PASSWORD,
        api_key=config.NAVIA_API_KEY,
        auth_token=config.NAVIA_AUTH_TOKEN,
        base_url=config.NAVIA_BASE_URL,
        paper_trading=is_paper_trading,
    )

    # Initialize Selected Strategy
    if args.strategy == "ma":
        strategy = MovingAverageCrossoverStrategy(
            client=client,
            symbol=args.symbol,
            exchange=args.exchange,
            quantity=args.qty,
            product=config.DEFAULT_PRODUCT,
            stop_loss_pct=config.STOP_LOSS_PCT,
            take_profit_pct=config.TAKE_PROFIT_PCT,
            max_daily_loss=config.MAX_DAILY_LOSS,
        )
    elif args.strategy == "rsi":
        strategy = RSIScalperStrategy(
            client=client,
            symbol=args.symbol,
            exchange=args.exchange,
            quantity=args.qty,
            product=config.DEFAULT_PRODUCT,
            stop_loss_pct=config.STOP_LOSS_PCT,
            take_profit_pct=config.TAKE_PROFIT_PCT,
            max_daily_loss=config.MAX_DAILY_LOSS,
        )
    else:
        logger.error("Unknown strategy: %s", args.strategy)
        sys.exit(1)

    # Initialize WebSocket Streaming Client
    use_simulated_feed = args.simulate_feed or is_paper_trading
    ws_client = NaviaWebSocketClient(
        auth_token=client.auth_token,
        ws_url=config.NAVIA_WS_URL,
        on_tick_callback=strategy.on_tick,
        simulate=use_simulated_feed,
    )

    # Graceful shutdown handler
    def handle_exit_signal(sig, frame):
        logger.info("\nReceived shutdown signal. Stopping Algo Trading safely...")
        ws_client.stop()
        strategy.stop()
        logger.info("Algo Trading stopped cleanly. Good bye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)

    # Start Strategy and Feed
    strategy.start()
    ws_client.subscribe([args.symbol])
    ws_client.start()

    logger.info("Algo trading is active and monitoring market ticks. Press Ctrl+C to stop.")

    try:
        while strategy.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_exit_signal(None, None)


if __name__ == "__main__":
    main()
