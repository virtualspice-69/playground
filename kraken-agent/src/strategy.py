"""Confluence-based signal generation.

Design goal from spec: "execute trades only when the probability of profit
is overwhelmingly high." This is implemented as a strict confluence
requirement — each indicator casts a directional vote (bullish / bearish /
neutral), and a trade signal is only produced when a large supermajority of
voters agree AND the weighted confidence score clears a high configurable
threshold. A single strong indicator can never overrule the rest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .liquidation_heatmap import HeatmapSignal

# (name, weight) — weights sum to 1.0 across the seven required signal
# sources named in the strategy spec.
WEIGHTS = {
    "ema_trend": 0.20,
    "rsi": 0.12,
    "macd": 0.18,
    "bollinger": 0.12,
    "roc": 0.13,
    "kdj": 0.15,
    "heatmap": 0.10,
}

MIN_AGREEMENT_VOTERS = 5  # of 7 non-heatmap+heatmap sources
RSI_OVERBOUGHT = 70.0
RSI_OVERSOLD = 30.0
MIN_ROC_MAGNITUDE = 0.15  # percent; below this ROC is treated as noise


@dataclass
class Signal:
    direction: Optional[str]  # "long" | "short" | None
    confidence: float  # 0.0..1.0
    votes: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)

    @property
    def actionable(self) -> bool:
        return self.direction is not None


def _vote_ema_trend(row: pd.Series) -> int:
    bullish = row["ema_fast"] > row["ema_slow"] > row["ema_trend"] and row["close"] > row["ema_trend"]
    bearish = row["ema_fast"] < row["ema_slow"] < row["ema_trend"] and row["close"] < row["ema_trend"]
    if bullish:
        return 1
    if bearish:
        return -1
    return 0


def _vote_rsi(row: pd.Series, ema_vote: int) -> int:
    r = row["rsi"]
    if ema_vote > 0 and r < RSI_OVERBOUGHT:
        return 1
    if ema_vote < 0 and r > RSI_OVERSOLD:
        return -1
    if r <= RSI_OVERSOLD:
        return 1  # oversold reversal potential
    if r >= RSI_OVERBOUGHT:
        return -1  # overbought reversal potential
    return 0


def _vote_macd(prev: pd.Series, row: pd.Series) -> int:
    crossed_up = prev["macd"] <= prev["macd_signal"] and row["macd"] > row["macd_signal"]
    crossed_down = prev["macd"] >= prev["macd_signal"] and row["macd"] < row["macd_signal"]
    if crossed_up and row["macd_hist"] > 0:
        return 1
    if crossed_down and row["macd_hist"] < 0:
        return -1
    if row["macd"] > row["macd_signal"] and row["macd_hist"] > 0:
        return 1
    if row["macd"] < row["macd_signal"] and row["macd_hist"] < 0:
        return -1
    return 0


def _vote_bollinger(row: pd.Series) -> int:
    if pd.isna(row["bb_upper"]) or pd.isna(row["bb_lower"]):
        return 0
    if row["close"] <= row["bb_lower"]:
        return 1  # mean-reversion long
    if row["close"] >= row["bb_upper"]:
        return -1  # mean-reversion short
    return 0


def _vote_roc(row: pd.Series) -> int:
    r = row["roc"]
    if pd.isna(r) or abs(r) < MIN_ROC_MAGNITUDE:
        return 0
    return 1 if r > 0 else -1


def _vote_kdj(prev: pd.Series, row: pd.Series) -> int:
    golden_cross = prev["k"] <= prev["d"] and row["k"] > row["d"] and row["k"] < 50
    death_cross = prev["k"] >= prev["d"] and row["k"] < row["d"] and row["k"] > 50
    if golden_cross:
        return 1
    if death_cross:
        return -1
    if row["j"] < 0:
        return 1  # deeply oversold
    if row["j"] > 100:
        return -1  # deeply overbought
    return 0


def _vote_heatmap(signal: HeatmapSignal) -> float:
    # continuous, scaled by the provider's own confidence in the reading
    return signal.bias * signal.confidence


def evaluate(
    indicator_df: pd.DataFrame,
    heatmap_signal: HeatmapSignal,
    min_confidence: float = 0.8,
) -> Signal:
    """Evaluate the latest fully-formed candle for a trade signal.

    indicator_df must already have indicators.compute_all() applied and at
    least 2 rows (needs a previous row for crossover detection).
    """
    if len(indicator_df) < 2:
        return Signal(direction=None, confidence=0.0, reasons=["insufficient history"])

    row = indicator_df.iloc[-1]
    prev = indicator_df.iloc[-2]

    votes = {}
    votes["ema_trend"] = _vote_ema_trend(row)
    votes["rsi"] = _vote_rsi(row, votes["ema_trend"])
    votes["macd"] = _vote_macd(prev, row)
    votes["bollinger"] = _vote_bollinger(row)
    votes["roc"] = _vote_roc(row)
    votes["kdj"] = _vote_kdj(prev, row)
    heatmap_vote = _vote_heatmap(heatmap_signal)

    weighted_score = sum(WEIGHTS[k] * v for k, v in votes.items())
    weighted_score += WEIGHTS["heatmap"] * heatmap_vote

    non_neutral_votes = {k: v for k, v in votes.items() if v != 0}
    if heatmap_vote != 0:
        non_neutral_votes["heatmap"] = 1 if heatmap_vote > 0 else -1

    direction_sign = 1 if weighted_score > 0 else (-1 if weighted_score < 0 else 0)
    agreeing = sum(1 for v in non_neutral_votes.values() if v == direction_sign)

    reasons = [f"{k}={v}" for k, v in votes.items()]
    reasons.append(f"heatmap_bias={heatmap_signal.bias:.2f} heatmap_conf={heatmap_signal.confidence:.2f}")
    reasons.append(f"weighted_score={weighted_score:.3f} agreeing={agreeing}/{len(non_neutral_votes)}")

    confidence = min(1.0, abs(weighted_score))

    if (
        direction_sign != 0
        and agreeing >= MIN_AGREEMENT_VOTERS
        and confidence >= min_confidence
    ):
        direction = "long" if direction_sign > 0 else "short"
        return Signal(direction=direction, confidence=confidence, votes=votes, reasons=reasons)

    return Signal(direction=None, confidence=confidence, votes=votes, reasons=reasons)
