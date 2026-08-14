# Kraken Multi-Indicator Trading Agent

A quantitative trading agent for Kraken, built for high-confluence,
low-frequency entries with strict risk controls. Implements the strategy
spec: EMA, RSI, Bollinger Bands, MACD, ROC, KDJ, and an optional
liquidation-heatmap overlay, combined into a single weighted confluence
score. A trade is only taken when a large supermajority of signals agree
**and** the weighted confidence score clears a high configurable threshold
(default 0.8 of 1.0).

## Safety model — read this first

- **`DRY_RUN=true` by default.** In dry-run, the agent fetches real market
  data and computes real signals, but every order-placing call is logged
  and skipped instead of sent to Kraken. Nothing here places a live order
  until you explicitly set `DRY_RUN=false`.
- **No withdrawal permission, ever.** The Kraken API key you create for
  this bot should only have Query Funds, Query Open Orders & Trades,
  Create & Modify Orders, and Cancel/Close Orders. Never grant Withdraw
  Funds to an automated trading key.
- **Secrets never touch git.** Credentials are read from environment
  variables (or a local `.env`, which is gitignored). Nothing in this
  codebase hardcodes or transmits a key anywhere except to `kraken.com`
  via the official `ccxt` client.
- **Daily drawdown kill-switch.** Once realized-plus-open equity drops
  `MAX_DAILY_DRAWDOWN_PCT` below the day's starting equity (UTC calendar
  day), the agent stops opening new positions for the rest of that day.
  Existing positions can still be closed.
- **This process is not a hosted service.** It's a script you run. For
  continuous operation you need to host it yourself (a VPS, a small
  always-on server, a container) — it will not run 24/7 inside an
  ephemeral CI/agent session.

## Setup

1. **Create a Kraken Pro API key**: Kraken web app → Settings → API →
   Add key. Grant exactly: Query Funds, Query Open Orders & Trades,
   Create & Modify Orders, Cancel/Close Orders. Leave Withdraw Funds
   unchecked. If your account tier supports IP allow-listing, restrict
   the key to the IP address of the machine that will run this bot.

2. **Install dependencies** (Python 3.10+):

   ```bash
   cd kraken-agent
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure**:

   ```bash
   cp .env.example .env
   # edit .env: paste your Kraken key/secret, review risk parameters,
   # leave DRY_RUN=true for now.
   ```

4. **(Optional) Liquidation heatmap**: if you have a Coinglass API key,
   set `LIQUIDATION_HEATMAP_PROVIDER=coinglass` and
   `LIQUIDATION_HEATMAP_API_KEY=...` in `.env`. Otherwise leave
   `LIQUIDATION_HEATMAP_PROVIDER=none` — the strategy runs fine without
   it, just with one fewer confluence input (that weight effectively
   drops out of the score).

## Running

Single evaluation cycle (good for checking behavior before trusting a
long-running loop):

```bash
python -m src.agent --once
```

Continuous loop (polls every `POLL_INTERVAL_SECONDS`):

```bash
python -m src.agent
```

Watch the logs. In dry-run, you should see `[DRY RUN] would place ...`
lines whenever a high-confidence signal fires, with no real orders sent.

## Going live

Only after you've watched dry-run output over some real market conditions
and are comfortable with the signal frequency and risk parameters:

1. Set `DRY_RUN=false` in `.env`.
2. Start with small `MAX_POSITION_SIZE_PCT` and a tight
   `MAX_DAILY_DRAWDOWN_PCT` until you've observed real fills.
3. Run it somewhere you can monitor (logs, alerting) — this is a
   fire-and-forget script, not a supervised service, unless you add that
   supervision yourself.

## How the signal is built

Each indicator casts a vote of `-1` (bearish), `0` (neutral), or `+1`
(bullish) on the latest closed candle:

| Signal | Rule (summary) |
|---|---|
| EMA trend | 12/26/50 EMA stack alignment + price vs 50-EMA |
| RSI(14) | Momentum confirmation, flags overbought/oversold reversal zones |
| MACD(12,26,9) | Signal-line crossover direction + histogram sign |
| Bollinger Bands(20,2) | Mean-reversion extremes at the bands |
| ROC(12) | Rate-of-change direction, filtered for noise |
| KDJ(9,3,3) | K/D golden/death cross plus J-value exhaustion |
| Liquidation heatmap | Optional third-party bias, weighted by its own confidence |

Votes are combined with fixed weights (`src/strategy.py::WEIGHTS`, sum to
1.0). A signal is only actionable when at least 5 of the 7 non-neutral
votes agree with the dominant direction **and** the weighted score meets
`MIN_SIGNAL_CONFIDENCE`. This is deliberately strict — the spec calls for
trading only when probability of profit is "overwhelmingly high," which
here means broad indicator agreement, not any single strong signal.

## Risk management (`src/risk_manager.py`)

- **Position sizing**: base allocation is `MAX_POSITION_SIZE_PCT` of
  current equity, scaled down (never up) as ATR-based volatility rises
  above a 1% reference.
- **Stop-loss / take-profit**: fixed percentage levels per trade
  (`STOP_LOSS_PCT`, `TAKE_PROFIT_PCT`), placed as an exchange stop order
  on entry and also checked each cycle as a backstop.
- **Daily drawdown halt**: tracked against the UTC day's starting equity,
  persisted to `state/risk_state.json` so a restart mid-day doesn't reset
  the counter.
- **Concurrency cap**: `MAX_CONCURRENT_POSITIONS` limits how many symbols
  can have open positions at once.

## Project layout

```
kraken-agent/
  src/
    indicators.py           EMA, RSI, Bollinger, MACD, ROC, KDJ, ATR
    liquidation_heatmap.py  Pluggable heatmap provider (Coinglass / none)
    kraken_client.py        ccxt wrapper, DRY_RUN-aware order placement
    strategy.py             Confluence scoring -> Signal
    risk_manager.py         Drawdown kill-switch, sizing, SL/TP levels
    executor.py             Signal -> orders -> tracked positions
    agent.py                Config loading + main loop / CLI entry point
  tests/                    pytest unit tests for indicators/risk/strategy
  .env.example              All configuration knobs, documented
```

## Running tests

```bash
pip install -r requirements.txt pytest
python -m pytest tests/ -v
```

## Known limitations

- Kraken has no native liquidation-heatmap endpoint; that signal is
  optional and comes from a third party if you configure one.
- `fetch_balance_usd_equity` approximates equity by converting each held
  asset via its `*/USD` ticker; assets without a direct USD market are
  skipped rather than estimated.
- This is not investment advice, and no automated strategy eliminates
  the risk of loss — the risk controls here bound *how much* can be lost
  before the agent stops trading, not whether any individual trade wins.
