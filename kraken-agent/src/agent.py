"""Entry point for the Kraken multi-indicator trading agent.

Defaults to DRY_RUN=true (see .env.example). Live trading requires the
operator to explicitly set DRY_RUN=false after reviewing dry-run behavior,
and to supply their own Kraken API credentials via environment variables —
this code never hardcodes or transmits credentials anywhere else.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

from .executor import Executor
from .indicators import compute_all
from .kraken_client import KrakenClient
from .liquidation_heatmap import build_provider_from_env
from .risk_manager import RiskConfig, RiskManager
from .strategy import evaluate

logger = logging.getLogger("kraken_agent")


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def load_config() -> dict:
    load_dotenv()
    return {
        "api_key": os.getenv("KRAKEN_API_KEY", ""),
        "api_secret": os.getenv("KRAKEN_API_SECRET", ""),
        "dry_run": _env_bool("DRY_RUN", True),
        "symbols": [s.strip() for s in os.getenv("TRADING_SYMBOLS", "BTC/USD").split(",") if s.strip()],
        "timeframe": os.getenv("TIMEFRAME", "15m"),
        "poll_interval_seconds": _env_int("POLL_INTERVAL_SECONDS", 60),
        "min_signal_confidence": _env_float("MIN_SIGNAL_CONFIDENCE", 0.8),
        "risk": RiskConfig(
            max_daily_drawdown_pct=_env_float("MAX_DAILY_DRAWDOWN_PCT", 2.0),
            max_position_size_pct=_env_float("MAX_POSITION_SIZE_PCT", 5.0),
            max_concurrent_positions=_env_int("MAX_CONCURRENT_POSITIONS", 3),
            stop_loss_pct=_env_float("STOP_LOSS_PCT", 1.5),
            take_profit_pct=_env_float("TAKE_PROFIT_PCT", 3.0),
        ),
    }


def build_components(config: dict):
    if not config["dry_run"] and (not config["api_key"] or not config["api_secret"]):
        raise SystemExit(
            "DRY_RUN=false but KRAKEN_API_KEY / KRAKEN_API_SECRET are not set. "
            "Refusing to start in live mode without credentials."
        )

    client = KrakenClient(
        api_key=config["api_key"],
        api_secret=config["api_secret"],
        dry_run=config["dry_run"],
    )
    risk = RiskManager(config["risk"])
    executor = Executor(client=client, risk=risk)
    heatmap_provider = build_provider_from_env()
    return client, risk, executor, heatmap_provider


def run_cycle(config: dict, client: KrakenClient, risk: RiskManager, executor: Executor, heatmap_provider) -> None:
    try:
        equity = client.fetch_balance_usd_equity()
    except Exception:
        logger.exception("Failed to fetch account balance; skipping this cycle")
        return

    risk.sync_day(equity)
    drawdown = risk.current_drawdown_pct(equity)
    logger.info("Equity=%.2f USD, daily drawdown=%.2f%%", equity, drawdown)

    for symbol in config["symbols"]:
        try:
            df = client.fetch_ohlcv_df(symbol, timeframe=config["timeframe"], limit=300)
            if len(df) < 60:
                logger.info("Not enough candle history yet for %s, skipping", symbol)
                continue

            indicator_df = compute_all(df)
            price = float(indicator_df["close"].iloc[-1])
            atr_pct = float(indicator_df["atr_pct"].iloc[-1]) if "atr_pct" in indicator_df else None

            existing = executor.open_position_for_symbol(symbol)
            if existing is not None:
                hit = executor.check_protective_levels(symbol, price)
                if hit is not None:
                    logger.info("%s: %s level hit at price=%.4f, closing position", symbol, hit, price)
                    executor.close_position(symbol, price)
                continue

            heatmap_signal = heatmap_provider.get_signal(symbol)
            signal = evaluate(indicator_df, heatmap_signal, min_confidence=config["min_signal_confidence"])

            if signal.actionable:
                executor.execute_signal(symbol, signal, price, atr_pct, equity)
            else:
                logger.debug("%s: no actionable signal (confidence=%.3f)", symbol, signal.confidence)

            client.sleep_for_rate_limit()
        except Exception:
            logger.exception("Error processing %s this cycle; continuing with next symbol", symbol)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Kraken multi-indicator trading agent")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single evaluation cycle and exit, instead of looping forever.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config()
    logger.info(
        "Starting kraken_agent: dry_run=%s symbols=%s timeframe=%s",
        config["dry_run"],
        config["symbols"],
        config["timeframe"],
    )
    if not config["dry_run"]:
        logger.warning(
            "LIVE TRADING MODE ENABLED. Real orders will be placed with real funds."
        )

    client, risk, executor, heatmap_provider = build_components(config)

    if args.once:
        run_cycle(config, client, risk, executor, heatmap_provider)
        return 0

    while True:
        run_cycle(config, client, risk, executor, heatmap_provider)
        time.sleep(config["poll_interval_seconds"])


if __name__ == "__main__":
    sys.exit(main())
