"""Feature engineering for the ETF predictor.

Per-day signals computed from OHLCV. The full feature vector for a sample is
the flattened sliding window of these signals over WINDOW days.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.config import MOMENTUM_PERIOD, RSI_PERIOD, WINDOW

# The feature columns (in the order the windowed vector is laid out). Adding
# or reordering cols requires retraining; the model expects a fixed shape.
FEATURE_COLS: tuple[str, ...] = (
    "Change",
    "RSI",
    "Momentum",
    "MACD_hist",
    "BB_pctB",
    "BB_bw",
    "Stoch_K",
    "ATR_norm",
    "Vol_ratio",
    "SMA5_ratio",
    "SMA20_ratio",
    "Market_KR",
    "Market_US500",
    "Market_NASDAQ",
    "Market_USDKRW",
)

MARKET_COLS: tuple[str, ...] = (
    "Market_KR",
    "Market_US500",
    "Market_NASDAQ",
    "Market_USDKRW",
)


def add_rsi(df: pd.DataFrame, period: int = RSI_PERIOD) -> pd.DataFrame:
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = (100 - 100 / (1 + rs)).fillna(50.0)
    return df


def _macd_hist(close: pd.Series) -> pd.Series:
    """MACD histogram normalized by close so it's comparable across ETFs at
    different price levels (a 500-won histogram on a 100k ETF means very
    different from a 500-won histogram on a 5k ETF)."""
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return (hist / close.replace(0, np.nan)).fillna(0.0)


def _bollinger(close: pd.Series, period: int = 20, k: float = 2.0):
    sma = close.rolling(period, min_periods=period).mean()
    std = close.rolling(period, min_periods=period).std()
    upper = sma + k * std
    lower = sma - k * std
    width = (upper - lower).replace(0, np.nan)
    pct_b = (close - lower) / width
    bw = width / sma.replace(0, np.nan)
    return pct_b.fillna(0.5), bw.fillna(0.0), sma


def _stochastic_k(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if "Low" not in df.columns or "High" not in df.columns:
        return pd.Series(50.0, index=df.index)
    low_n = df["Low"].rolling(period, min_periods=period).min()
    high_n = df["High"].rolling(period, min_periods=period).max()
    span = (high_n - low_n).replace(0, np.nan)
    k = 100.0 * (df["Close"] - low_n) / span
    return k.fillna(50.0)


def _atr_norm(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if "High" not in df.columns or "Low" not in df.columns:
        return pd.Series(0.0, index=df.index)
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            (df["High"] - df["Low"]).abs(),
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period, min_periods=period).mean()
    return (atr / df["Close"].replace(0, np.nan)).fillna(0.0)


def _volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    if "Volume" not in df.columns:
        return pd.Series(1.0, index=df.index)
    vol = df["Volume"].astype(float)
    vol_avg = vol.rolling(period, min_periods=period).mean().replace(0, np.nan)
    return (vol / vol_avg).fillna(1.0).clip(upper=10.0)


def add_features(
    df: pd.DataFrame,
    *,
    market: pd.Series | pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute all feature columns and drop rows with any NaN.

    `market` may be either:
      - DataFrame with columns from MARKET_COLS (preferred)
      - Series of daily returns (legacy: treated as Market_KR for
        backwards compatibility)
      - None
    Missing market dates and missing columns are filled with 0.
    """
    df = df.copy()
    df = add_rsi(df)
    # Percent-change momentum (was raw price diff before — different ETFs at
    # different price levels were not comparable).
    df["Momentum"] = df["Close"].pct_change(periods=MOMENTUM_PERIOD).fillna(0.0)
    df["MACD_hist"] = _macd_hist(df["Close"])
    pct_b, bw, sma20 = _bollinger(df["Close"])
    df["BB_pctB"] = pct_b
    df["BB_bw"] = bw
    df["Stoch_K"] = _stochastic_k(df)
    df["ATR_norm"] = _atr_norm(df)
    df["Vol_ratio"] = _volume_ratio(df)
    sma5 = df["Close"].rolling(5, min_periods=5).mean()
    df["SMA5_ratio"] = (df["Close"] / sma5 - 1).fillna(0.0)
    df["SMA20_ratio"] = (df["Close"] / sma20 - 1).fillna(0.0)

    # Broadcast market columns (zero-fill anything missing).
    market_df: pd.DataFrame | None = None
    if isinstance(market, pd.Series):
        market_df = market.to_frame(name="Market_KR")
    elif isinstance(market, pd.DataFrame):
        market_df = market

    for col in MARKET_COLS:
        if market_df is not None and col in market_df.columns:
            df[col] = (
                market_df[col].reindex(df.index).fillna(0.0).astype(float)
            )
        else:
            df[col] = 0.0

    needed = ["Close", *FEATURE_COLS]
    return df[needed].dropna()


def build_windows(
    df: pd.DataFrame,
    *,
    rise_threshold: float,
    window: int = WINDOW,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
    """Slice rolling windows from a single ETF's feature-enriched history.

    Returns:
        X: (n_samples, window * len(FEATURE_COLS)) feature matrix
        y: (n_samples,) bool labels
        dates: (n_samples,) target dates as YYYY-MM-DD strings
        today_x: features for the latest available window (for inference)
    """
    feats = df[list(FEATURE_COLS)].to_numpy(dtype=np.float64)
    closes = df["Close"].to_numpy(dtype=np.float64)
    index = df.index

    n_features_per_day = len(FEATURE_COLS)
    if len(feats) < window:
        return (
            np.empty((0, window * n_features_per_day)),
            np.empty((0,), dtype=bool),
            np.empty((0,), dtype=object),
            None,
        )

    today_x = feats[-window:].flatten()

    n = len(feats) - window
    if n <= 0:
        return (
            np.empty((0, window * n_features_per_day)),
            np.empty((0,), dtype=bool),
            np.empty((0,), dtype=object),
            today_x,
        )

    X = np.empty((n, window * n_features_per_day), dtype=np.float64)
    y = np.empty(n, dtype=bool)
    dates = np.empty(n, dtype=object)
    for j in range(n):
        X[j] = feats[j : j + window].flatten()
        y[j] = closes[j + window - 1] * rise_threshold < closes[j + window]
        dates[j] = pd.Timestamp(index[j + window]).strftime("%Y-%m-%d")

    return X, y, dates, today_x
