"""Liquidation heatmap signal providers.

Kraken's own API does not expose aggregated cross-exchange liquidation
clusters, so this data (when used at all) comes from a third party such as
Coinglass. The strategy is designed to degrade gracefully: if no provider
is configured, `NullHeatmapProvider` returns a neutral reading rather than
raising, so the rest of the confluence score still works.

Signal contract: `get_signal(symbol)` returns a dict with:
  - bias: -1.0 (bearish / long-liquidation-heavy above price) .. +1.0
    (bullish / short-liquidation-heavy above price)
  - confidence: 0.0..1.0, how much weight this reading deserves
  - nearest_wall_pct: distance to the nearest large liquidation cluster,
    as a percent of current price, or None if unknown
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class HeatmapSignal:
    bias: float
    confidence: float
    nearest_wall_pct: Optional[float] = None


class LiquidationHeatmapProvider:
    def get_signal(self, symbol: str) -> HeatmapSignal:
        raise NotImplementedError


class NullHeatmapProvider(LiquidationHeatmapProvider):
    """Used when no heatmap data source is configured."""

    def get_signal(self, symbol: str) -> HeatmapSignal:
        return HeatmapSignal(bias=0.0, confidence=0.0, nearest_wall_pct=None)


class CoinglassHeatmapProvider(LiquidationHeatmapProvider):
    """Fetches liquidation heatmap data from Coinglass.

    Requires LIQUIDATION_HEATMAP_API_KEY. Network failures are treated as
    "no data" (neutral, zero-confidence signal) rather than raised, so a
    flaky third-party feed can never itself trigger a bad trade.
    """

    BASE_URL = "https://open-api.coinglass.com/public/v2/liquidation_heatmap"

    def __init__(self, api_key: str, timeout_seconds: float = 5.0):
        self._api_key = api_key
        self._timeout = timeout_seconds

    def get_signal(self, symbol: str) -> HeatmapSignal:
        try:
            resp = requests.get(
                self.BASE_URL,
                params={"symbol": symbol.replace("/", "")},
                headers={"coinglassSecret": self._api_key},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            payload = resp.json().get("data", {})
        except (requests.RequestException, ValueError):
            return HeatmapSignal(bias=0.0, confidence=0.0, nearest_wall_pct=None)

        bias = float(payload.get("bias", 0.0))
        confidence = float(payload.get("confidence", 0.0))
        nearest_wall_pct = payload.get("nearest_wall_pct")
        bias = max(-1.0, min(1.0, bias))
        confidence = max(0.0, min(1.0, confidence))
        return HeatmapSignal(
            bias=bias,
            confidence=confidence,
            nearest_wall_pct=nearest_wall_pct,
        )


def build_provider_from_env() -> LiquidationHeatmapProvider:
    provider_name = os.getenv("LIQUIDATION_HEATMAP_PROVIDER", "none").strip().lower()
    if provider_name == "coinglass":
        api_key = os.getenv("LIQUIDATION_HEATMAP_API_KEY", "").strip()
        if not api_key:
            return NullHeatmapProvider()
        return CoinglassHeatmapProvider(api_key=api_key)
    return NullHeatmapProvider()
