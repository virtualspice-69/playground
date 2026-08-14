"""Turns an approved Signal into orders, and tracks resulting positions.

Position state persists to state/positions.json (gitignored) so open
positions and their protective levels survive a process restart.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from .kraken_client import KrakenClient
from .risk_manager import RiskManager
from .strategy import Signal

logger = logging.getLogger("kraken_agent.executor")

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")
POSITIONS_FILE = os.path.join(STATE_DIR, "positions.json")


@dataclass
class Position:
    symbol: str
    direction: str
    amount: float
    entry_price: float
    stop_price: float
    take_profit_price: float
    opened_at: str
    dry_run: bool


class Executor:
    def __init__(self, client: KrakenClient, risk: RiskManager):
        self.client = client
        self.risk = risk
        self.positions: list[Position] = self._load_positions()

    def _load_positions(self) -> list[Position]:
        if os.path.exists(POSITIONS_FILE):
            try:
                with open(POSITIONS_FILE, "r") as f:
                    raw = json.load(f)
                return [Position(**p) for p in raw]
            except (json.JSONDecodeError, OSError, TypeError):
                logger.warning("Could not read positions state file, starting fresh")
        return []

    def _save_positions(self) -> None:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(POSITIONS_FILE, "w") as f:
            json.dump([asdict(p) for p in self.positions], f, indent=2)

    def open_position_for_symbol(self, symbol: str) -> Optional[Position]:
        for p in self.positions:
            if p.symbol == symbol:
                return p
        return None

    def execute_signal(
        self,
        symbol: str,
        signal: Signal,
        price: float,
        atr_pct: Optional[float],
        equity: float,
    ) -> Optional[Position]:
        if not signal.actionable:
            return None

        if self.open_position_for_symbol(symbol) is not None:
            logger.info("Skipping %s: position already open", symbol)
            return None

        if not self.risk.can_open_new_position(len(self.positions), equity):
            logger.info(
                "Skipping %s: risk manager declined new position (halted or max concurrent reached)",
                symbol,
            )
            return None

        amount = self.risk.position_size_base_units(equity, price, atr_pct)
        if amount <= 0:
            logger.info("Skipping %s: computed position size is zero", symbol)
            return None

        side = "buy" if signal.direction == "long" else "sell"
        stop_side = "sell" if signal.direction == "long" else "buy"

        logger.info(
            "Signal for %s: direction=%s confidence=%.3f amount=%.6f reasons=%s",
            symbol,
            signal.direction,
            signal.confidence,
            amount,
            signal.reasons,
        )

        entry_receipt = self.client.create_market_order(symbol, side, amount)
        stop_price = self.risk.stop_loss_price(price, signal.direction)
        take_profit_price = self.risk.take_profit_price(price, signal.direction)

        self.client.create_stop_loss_order(symbol, stop_side, amount, stop_price)

        position = Position(
            symbol=symbol,
            direction=signal.direction,
            amount=amount,
            entry_price=price,
            stop_price=stop_price,
            take_profit_price=take_profit_price,
            opened_at=datetime.now(timezone.utc).isoformat(),
            dry_run=entry_receipt.dry_run,
        )
        self.positions.append(position)
        self._save_positions()
        return position

    def close_position(self, symbol: str, price: float) -> Optional[Position]:
        position = self.open_position_for_symbol(symbol)
        if position is None:
            return None

        side = "sell" if position.direction == "long" else "buy"
        self.client.create_market_order(symbol, side, position.amount)

        self.positions = [p for p in self.positions if p.symbol != symbol]
        self._save_positions()
        logger.info("Closed position %s at ~%.4f", symbol, price)
        return position

    def check_protective_levels(self, symbol: str, price: float) -> Optional[str]:
        """Returns 'stop' or 'take_profit' if the current price has crossed
        the position's protective level for that symbol, else None. Actual
        order placement for the exit is left to close_position(); this only
        evaluates whether the level was hit, since exchange-side stop
        orders may not always be supported for every pair/account tier.
        """
        position = self.open_position_for_symbol(symbol)
        if position is None:
            return None
        if position.direction == "long":
            if price <= position.stop_price:
                return "stop"
            if price >= position.take_profit_price:
                return "take_profit"
        else:
            if price >= position.stop_price:
                return "stop"
            if price <= position.take_profit_price:
                return "take_profit"
        return None
