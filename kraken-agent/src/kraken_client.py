"""Thin wrapper around ccxt's Kraken client.

Centralizes the DRY_RUN safety switch: order-placing methods log the order
they would submit and return a synthetic receipt instead of calling the
exchange whenever dry_run is True. Market-data and balance reads always hit
the real API since they are non-destructive.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import ccxt
import pandas as pd

logger = logging.getLogger("kraken_agent.client")


@dataclass
class OrderReceipt:
    symbol: str
    side: str
    amount: float
    order_type: str
    price: Optional[float]
    dry_run: bool
    raw: Optional[dict] = None


class KrakenClient:
    def __init__(self, api_key: str, api_secret: str, dry_run: bool = True):
        self.dry_run = dry_run
        self._exchange = ccxt.kraken(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
            }
        )

    def fetch_ohlcv_df(
        self, symbol: str, timeframe: str = "15m", limit: int = 300
    ) -> pd.DataFrame:
        raw = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(
            raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("timestamp")
        return df

    def fetch_balance_usd_equity(self) -> float:
        """Best-effort total account equity in USD-equivalent terms.

        Sums free+used balances for assets that have a direct */USD market,
        converting via last trade price. Assets without a USD market are
        skipped rather than guessed at.
        """
        balance = self._exchange.fetch_balance()
        total = balance.get("total", {})
        equity = 0.0
        for asset, amount in total.items():
            if not amount:
                continue
            if asset in ("USD", "ZUSD"):
                equity += float(amount)
                continue
            symbol = f"{asset}/USD"
            try:
                ticker = self._exchange.fetch_ticker(symbol)
                price = ticker.get("last") or ticker.get("close")
                if price:
                    equity += float(amount) * float(price)
            except ccxt.BaseError:
                logger.debug("No USD market for %s, skipping in equity calc", asset)
        return equity

    def create_market_order(
        self, symbol: str, side: str, amount: float
    ) -> OrderReceipt:
        if self.dry_run:
            logger.info(
                "[DRY RUN] would place %s market order: %s amount=%s",
                side,
                symbol,
                amount,
            )
            return OrderReceipt(
                symbol=symbol,
                side=side,
                amount=amount,
                order_type="market",
                price=None,
                dry_run=True,
            )
        raw = self._exchange.create_order(symbol, "market", side, amount)
        return OrderReceipt(
            symbol=symbol,
            side=side,
            amount=amount,
            order_type="market",
            price=raw.get("price"),
            dry_run=False,
            raw=raw,
        )

    def create_stop_loss_order(
        self, symbol: str, side: str, amount: float, stop_price: float
    ) -> OrderReceipt:
        if self.dry_run:
            logger.info(
                "[DRY RUN] would place %s stop order: %s amount=%s stop=%s",
                side,
                symbol,
                amount,
                stop_price,
            )
            return OrderReceipt(
                symbol=symbol,
                side=side,
                amount=amount,
                order_type="stop-loss",
                price=stop_price,
                dry_run=True,
            )
        raw = self._exchange.create_order(
            symbol,
            "stop-loss",
            side,
            amount,
            params={"stopPrice": stop_price},
        )
        return OrderReceipt(
            symbol=symbol,
            side=side,
            amount=amount,
            order_type="stop-loss",
            price=stop_price,
            dry_run=False,
            raw=raw,
        )

    def sleep_for_rate_limit(self) -> None:
        time.sleep(self._exchange.rateLimit / 1000.0)
