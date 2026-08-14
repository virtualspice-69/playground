"""Technical indicator calculations used by the strategy engine.

All functions take/return pandas Series or DataFrames indexed the same as
the input OHLCV candles and use only pandas/numpy so the project has no
compiled-dependency (e.g. TA-Lib) requirement.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss == 0: all-gains window -> RSI 100 (or 50 if avg_gain is
    # also 0, i.e. no movement at all).
    out = out.where(avg_loss != 0.0, np.where(avg_gain > 0.0, 100.0, 50.0))
    return pd.Series(out, index=series.index).fillna(50.0)


def bollinger_bands(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    mid = series.rolling(window=period).mean()
    std = series.rolling(window=period).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid.replace(0.0, np.nan)
    return pd.DataFrame(
        {"bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "bb_width": width}
    )


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "macd_signal": signal_line, "macd_hist": hist}
    )


def roc(series: pd.Series, period: int = 12) -> pd.Series:
    return (series - series.shift(period)) / series.shift(period).replace(
        0.0, np.nan
    ) * 100.0


def kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 9,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> pd.DataFrame:
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low).replace(
        0.0, np.nan
    ) * 100.0
    rsv = rsv.fillna(50.0)
    k = rsv.ewm(alpha=1.0 / k_smooth, adjust=False).mean()
    d = k.ewm(alpha=1.0 / d_smooth, adjust=False).mean()
    j = 3 * k - 2 * d
    return pd.DataFrame({"k": k, "d": d, "j": j})


def atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the full indicator set on an OHLCV DataFrame.

    Expects columns: open, high, low, close, volume.
    """
    out = df.copy()
    out["ema_fast"] = ema(out["close"], 12)
    out["ema_slow"] = ema(out["close"], 26)
    out["ema_trend"] = ema(out["close"], 50)
    out["rsi"] = rsi(out["close"], 14)
    out = out.join(bollinger_bands(out["close"], 20, 2.0))
    out = out.join(macd(out["close"], 12, 26, 9))
    out["roc"] = roc(out["close"], 12)
    out = out.join(kdj(out["high"], out["low"], out["close"], 9, 3, 3))
    out["atr"] = atr(out["high"], out["low"], out["close"], 14)
    out["atr_pct"] = out["atr"] / out["close"].replace(0.0, np.nan)
    return out
