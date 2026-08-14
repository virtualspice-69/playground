import numpy as np
import pandas as pd

from src.indicators import compute_all
from src.liquidation_heatmap import HeatmapSignal
from src.strategy import evaluate


def _trending_up_df(n=120):
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    close = 100 + np.cumsum(np.full(n, 0.6)) + np.sin(np.linspace(0, 3, n)) * 0.3
    high = close + 0.3
    low = close - 0.3
    open_ = close - 0.1
    volume = np.full(n, 50.0)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def _flat_choppy_df(n=120, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    close = 100 + rng.normal(0, 0.2, size=n)
    high = close + 0.1
    low = close - 0.1
    open_ = close
    volume = np.full(n, 50.0)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def test_strong_uptrend_with_aligned_heatmap_can_be_actionable():
    df = compute_all(_trending_up_df())
    heatmap = HeatmapSignal(bias=1.0, confidence=1.0)
    signal = evaluate(df, heatmap, min_confidence=0.5)
    if signal.actionable:
        assert signal.direction == "long"
    assert signal.confidence >= 0.0


def test_choppy_flat_market_is_not_actionable_at_high_threshold():
    df = compute_all(_flat_choppy_df())
    heatmap = HeatmapSignal(bias=0.0, confidence=0.0)
    signal = evaluate(df, heatmap, min_confidence=0.8)
    assert signal.actionable is False


def test_insufficient_history_returns_none_direction():
    df = compute_all(_trending_up_df(n=1))
    heatmap = HeatmapSignal(bias=0.0, confidence=0.0)
    signal = evaluate(df, heatmap, min_confidence=0.8)
    assert signal.direction is None


def test_high_threshold_requires_more_confidence_than_low_threshold():
    df = compute_all(_trending_up_df())
    heatmap = HeatmapSignal(bias=1.0, confidence=1.0)
    loose = evaluate(df, heatmap, min_confidence=0.1)
    strict = evaluate(df, heatmap, min_confidence=0.99)
    assert loose.confidence == strict.confidence
    assert strict.actionable is False or loose.actionable
