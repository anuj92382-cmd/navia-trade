"""
Navia Algo Trading - Web Dashboard + Background Trading Engine
Flask web server for Render deployment with live trading status dashboard.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, render_template_string

import config
from navia import NaviaClient, NaviaWebSocketClient
from strategies import MovingAverageCrossoverStrategy, RSIScalperStrategy

# ─── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("NaviaApp")

# ─── Flask App ───────────────────────────────────────────────────────────────
app = Flask(__name__)

# Global state
algo_state = {
    "running": False,
    "strategy": None,
    "symbol": config.DEFAULT_SYMBOL,
    "mode": "PAPER TRADING" if config.PAPER_TRADING else "LIVE TRADING",
    "started_at": None,
    "last_tick": None,
    "last_ltp": 0.0,
    "trades": [],
    "position": 0,
    "realized_pnl": 0.0,
    "unrealized_pnl": 0.0,
    "logs": [],
}

client = None
strategy = None
ws_client = None

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="5">
<title>Navia Algo Trader</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0d1117; color: #c9d1d9; font-family: 'Courier New', monospace; padding: 20px; }
  h1 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; margin-bottom: 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; }
  .card .label { color: #8b949e; font-size: 12px; margin-bottom: 6px; text-transform: uppercase; }
  .card .value { font-size: 22px; font-weight: bold; }
  .green { color: #3fb950; }
  .red { color: #f85149; }
  .blue { color: #58a6ff; }
  .yellow { color: #d29922; }
  .status-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
  .live { background: #3fb95022; border: 1px solid #3fb950; color: #3fb950; }
  .paper { background: #d2992222; border: 1px solid #d29922; color: #d29922; }
  table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; }
  th { background: #21262d; color: #8b949e; padding: 10px 15px; text-align: left; font-size: 12px; text-transform: uppercase; }
  td { padding: 10px 15px; border-top: 1px solid #21262d; font-size: 13px; }
  .footer { margin-top: 20px; color: #8b949e; font-size: 12px; text-align: center; }
</style>
</head>
<body>
<h1>🤖 Navia Algo Trading Dashboard</h1>
<div class="grid">
  <div class="card">
    <div class="label">Status</div>
    <div class="value">
      {% if state.running %}
        <span class="status-badge live">● ACTIVE</span>
      {% else %}
        <span class="status-badge paper">○ IDLE</span>
      {% endif %}
    </div>
  </div>
  <div class="card">
    <div class="label">Mode</div>
    <div class="value {{ 'red' if 'LIVE' in state.mode else 'yellow' }}">{{ state.mode }}</div>
  </div>
  <div class="card">
    <div class="label">Symbol</div>
    <div class="value blue">{{ state.symbol }}</div>
  </div>
  <div class="card">
    <div class="label">Last LTP</div>
    <div class="value">₹{{ "%.2f"|format(state.last_ltp) }}</div>
  </div>
  <div class="card">
    <div class="label">Position</div>
    <div class="value {{ 'green' if state.position > 0 else ('red' if state.position < 0 else '') }}">
      {{ state.position }} lots
    </div>
  </div>
  <div class="card">
    <div class="label">Realized P&L</div>
    <div class="value {{ 'green' if state.realized_pnl >= 0 else 'red' }}">
      ₹{{ "%.2f"|format(state.realized_pnl) }}
    </div>
  </div>
  <div class="card">
    <div class="label">Total Trades</div>
    <div class="value blue">{{ state.trades|length }}</div>
  </div>
  <div class="card">
    <div class="label">Started At</div>
    <div class="value" style="font-size:14px">{{ state.started_at or '—' }}</div>
  </div>
</div>

<h2 style="color:#8b949e; font-size:14px; margin-bottom:10px; text-transform:uppercase;">Recent Trades</h2>
{% if state.trades %}
<table>
  <thead><tr><th>#</th><th>Time</th><th>Side</th><th>Qty</th><th>Price</th><th>Reason</th></tr></thead>
  <tbody>
  {% for t in state.trades[-10:]|reverse %}
    <tr>
      <td>{{ loop.revindex }}</td>
      <td>{{ t.time }}</td>
      <td class="{{ 'green' if t.side == 'BUY' else 'red' }}"><b>{{ t.side }}</b></td>
      <td>{{ t.qty }}</td>
      <td>₹{{ "%.2f"|format(t.price) }}</td>
      <td style="color:#8b949e">{{ t.reason }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
  <p style="color:#8b949e; padding:15px 0;">No trades yet. Strategy is monitoring market...</p>
{% endif %}

<div class="footer">
  Auto-refresh every 5 seconds &nbsp;|&nbsp; Navia Algo Trader v1.0 &nbsp;|&nbsp;
  Last update: {{ state.last_tick or 'Waiting for first tick...' }}
</div>
</body>
</html>
"""


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    """Live trading dashboard."""
    return render_template_string(DASHBOARD_HTML, state=algo_state)


@app.route("/health")
def health():
    """Health check endpoint for Render."""
    return jsonify({
        "status": "ok",
        "running": algo_state["running"],
        "symbol": algo_state["symbol"],
        "mode": algo_state["mode"],
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/state")
def get_state():
    """JSON API for current algo state."""
    return jsonify(algo_state)


@app.route("/api/trades")
def get_trades():
    """JSON API for trade history."""
    return jsonify(algo_state.get("trades", []))


# ─── Background Algo Thread ──────────────────────────────────────────────────

def tick_handler(tick: dict):
    """Shared tick callback: updates dashboard state + forwards to strategy."""
    ltp = float(tick.get("ltp") or tick.get("last_price") or 0.0)
    algo_state["last_ltp"] = ltp
    algo_state["last_tick"] = datetime.now().strftime("%H:%M:%S")

    if strategy:
        strategy.on_tick(tick)
        # Sync strategy state to dashboard
        algo_state["position"] = strategy.current_position
        algo_state["realized_pnl"] = strategy.realized_pnl
        algo_state["unrealized_pnl"] = strategy.unrealized_pnl(ltp)
        algo_state["trades"] = strategy.trades[-50:]   # keep last 50 trades


def start_algo():
    """Initialize and start the algo trading engine in background."""
    global client, strategy, ws_client

    logger.info("Initializing Navia Algo Engine...")

    strategy_name = os.getenv("STRATEGY", "ma").lower()
    symbol = config.DEFAULT_SYMBOL
    exchange = config.DEFAULT_EXCHANGE
    qty = config.DEFAULT_QUANTITY
    is_paper = config.PAPER_TRADING
    simulate_feed = os.getenv("SIMULATE_FEED", "true").lower() in ("true", "1", "yes")

    # Update dashboard state
    algo_state["symbol"] = symbol
    algo_state["mode"] = "PAPER TRADING" if is_paper else "🔴 LIVE TRADING"
    algo_state["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create Navia client
    client = NaviaClient(
        client_code=config.NAVIA_CLIENT_CODE,
        password=config.NAVIA_PASSWORD,
        api_key=config.NAVIA_API_KEY,
        auth_token=config.NAVIA_AUTH_TOKEN,
        base_url=config.NAVIA_BASE_URL,
        paper_trading=is_paper,
    )

    # Create strategy
    if strategy_name == "rsi":
        strategy = RSIScalperStrategy(
            client=client,
            symbol=symbol,
            exchange=exchange,
            quantity=qty,
            product=config.DEFAULT_PRODUCT,
            stop_loss_pct=config.STOP_LOSS_PCT,
            take_profit_pct=config.TAKE_PROFIT_PCT,
            max_daily_loss=config.MAX_DAILY_LOSS,
        )
    else:
        strategy = MovingAverageCrossoverStrategy(
            client=client,
            symbol=symbol,
            exchange=exchange,
            quantity=qty,
            product=config.DEFAULT_PRODUCT,
            stop_loss_pct=config.STOP_LOSS_PCT,
            take_profit_pct=config.TAKE_PROFIT_PCT,
            max_daily_loss=config.MAX_DAILY_LOSS,
        )

    # WebSocket tick feed
    ws_client = NaviaWebSocketClient(
        auth_token=client.auth_token,
        ws_url=config.NAVIA_WS_URL,
        on_tick_callback=tick_handler,
        simulate=simulate_feed,
    )

    strategy.start()
    ws_client.subscribe([symbol])
    ws_client.start()
    algo_state["running"] = True

    logger.info("Algo engine started. Strategy: %s | Symbol: %s", strategy_name.upper(), symbol)

    # Keep thread alive
    while algo_state["running"]:
        time.sleep(5)


# ─── App Startup ─────────────────────────────────────────────────────────────

def launch():
    """Start algo in background thread, then launch Flask server."""
    algo_thread = threading.Thread(target=start_algo, daemon=True)
    algo_thread.start()

    port = int(os.getenv("PORT", 8000))
    logger.info("Starting Flask Dashboard on port %d ...", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    launch()
