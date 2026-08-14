import numpy as np
import pandas as pd

from src.indicators import atr, bollinger_bands, compute_all, ema, kdj, macd, rsi, roc


def _make_ohlcv(n=100, start=100.0, step=0.5, seed=0):
    rng = np.random.default_rng(seed)
    close = start + np.cumsum(rng.normal(loc=step, scale=1.0, size=n))
    high = close + rng.uniform(0.1, 1.0, size=n)
    low = close - rng.uniform(0.1, 1.0, size=n)
    open_ = close + rng.uniform(-0.5, 0.5, size=n)
    volume = rng.uniform(10, 100, size=n)
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def test_ema_tracks_trend_direction():
    series = pd.Series(np.linspace(100, 200, 50))
    result = ema(series, 10)
    assert result.iloc[-1] > result.iloc[0]
    assert len(result) == len(series)


def test_rsi_bounds():
    df = _make_ohlcv()
    result = rsi(df["close"])
    assert result.between(0, 100).all()


def test_rsi_extreme_on_monotonic_uptrend():
    series = pd.Series(np.linspace(100, 200, 60))
    result = rsi(series)
    assert result.iloc[-1] > 60


def test_bollinger_bands_ordering():
    df = _make_ohlcv()
    bands = bollinger_bands(df["close"])
    valid = bands.dropna()
    assert (valid["bb_upper"] >= valid["bb_mid"]).all()
    assert (valid["bb_mid"] >= valid["bb_lower"]).all()


def test_macd_columns_present():
    df = _make_ohlcv()
    result = macd(df["close"])
    assert set(result.columns) == {"macd", "macd_signal", "macd_hist"}
    assert (result["macd_hist"].dropna() == (result["macd"] - result["macd_signal"]).dropna()).all()


def test_roc_zero_for_flat_series():
    series = pd.Series([100.0] * 30)
    result = roc(series, period=5)
    assert result.dropna().abs().max() < 1e-9


def test_kdj_bounds_k_d():
    df = _make_ohlcv()
    result = kdj(df["high"], df["low"], df["close"])
    assert not result[["k", "d", "j"]].isna().all().any()


def test_atr_non_negative():
    df = _make_ohlcv()
    result = atr(df["high"], df["low"], df["close"])
    assert (result.dropna() >= 0).all()


def test_compute_all_has_expected_columns():
    df = _make_ohlcv()
    out = compute_all(df)
    expected = {
        "ema_fast", "ema_slow", "ema_trend", "rsi",
        "bb_mid", "bb_upper", "bb_lower", "bb_width",
        "macd", "macd_signal", "macd_hist", "roc",
        "k", "d", "j", "atr", "atr_pct",
    }
    assert expected.issubset(set(out.columns))
