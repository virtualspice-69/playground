"""Risk controls: daily drawdown kill-switch, position sizing, and
per-trade protective levels.

State (today's starting equity, halted flag) persists to a small JSON file
under state/ so a restart mid-day doesn't reset the drawdown counter and
accidentally lift a halt.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("kraken_agent.risk")

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")
STATE_FILE = os.path.join(STATE_DIR, "risk_state.json")


@dataclass
class RiskConfig:
    max_daily_drawdown_pct: float
    max_position_size_pct: float
    max_concurrent_positions: int
    stop_loss_pct: float
    take_profit_pct: float


class RiskManager:
    def __init__(self, config: RiskConfig):
        self.config = config
        self._state = self._load_state()

    def _load_state(self) -> dict:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Could not read risk state file, starting fresh")
        return {"date": None, "start_equity": None, "halted": False}

    def _save_state(self) -> None:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(self._state, f)

    def _today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def sync_day(self, current_equity: float) -> None:
        today = self._today_str()
        if self._state.get("date") != today:
            logger.info(
                "New UTC trading day (%s); resetting daily drawdown baseline to equity=%.2f",
                today,
                current_equity,
            )
            self._state = {
                "date": today,
                "start_equity": current_equity,
                "halted": False,
            }
            self._save_state()

    def current_drawdown_pct(self, current_equity: float) -> float:
        start = self._state.get("start_equity")
        if not start:
            return 0.0
        return max(0.0, (start - current_equity) / start * 100.0)

    def check_and_update_halt(self, current_equity: float) -> bool:
        """Returns True if trading is halted for the rest of the day."""
        drawdown = self.current_drawdown_pct(current_equity)
        if drawdown >= self.config.max_daily_drawdown_pct:
            if not self._state.get("halted"):
                logger.warning(
                    "Daily drawdown %.2f%% >= limit %.2f%%. Halting new entries for the day.",
                    drawdown,
                    self.config.max_daily_drawdown_pct,
                )
            self._state["halted"] = True
            self._save_state()
        return bool(self._state.get("halted"))

    def can_open_new_position(self, open_positions_count: int, current_equity: float) -> bool:
        if self.check_and_update_halt(current_equity):
            return False
        if open_positions_count >= self.config.max_concurrent_positions:
            return False
        return True

    def position_size_base_units(
        self, equity: float, price: float, atr_pct: Optional[float]
    ) -> float:
        """Volatility-adjusted position size in base-asset units.

        Sizes down (never up) when recent volatility (ATR as % of price)
        is elevated, using a simple inverse scaling capped at the
        configured max position size.
        """
        base_allocation_usd = equity * (self.config.max_position_size_pct / 100.0)

        if atr_pct and atr_pct > 0:
            # Reference volatility of 1.0% ATR; scale down proportionally
            # above that, never scale up above the configured max.
            reference_atr_pct = 0.01
            vol_scale = min(1.0, reference_atr_pct / atr_pct)
        else:
            vol_scale = 1.0

        allocation_usd = base_allocation_usd * vol_scale
        if price <= 0:
            return 0.0
        return allocation_usd / price

    def stop_loss_price(self, entry_price: float, direction: str) -> float:
        pct = self.config.stop_loss_pct / 100.0
        if direction == "long":
            return entry_price * (1.0 - pct)
        return entry_price * (1.0 + pct)

    def take_profit_price(self, entry_price: float, direction: str) -> float:
        pct = self.config.take_profit_pct / 100.0
        if direction == "long":
            return entry_price * (1.0 + pct)
        return entry_price * (1.0 - pct)
