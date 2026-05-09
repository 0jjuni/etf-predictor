"""Feature engineering for the ETF predictor."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.config import MOMENTUM_PERIOD, RSI_PERIOD, WINDOW


def add_rsi(df: pd.DataFrame, period: int = RSI_PERIOD) -> pd.DataFrame:
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = (100 - 100 / (1 + rs)).fillna(50.0)
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_rsi(df)
    df["Momentum"] = df["Close"].diff(periods=MOMENTUM_PERIOD)
    return df.dropna()


def build_windows(
    df: pd.DataFrame,
    *,
    rise_threshold: float,
    window: int = WINDOW,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Slice rolling windows from a single ETF's history.

    Returns:
        X: (n_samples, window * 3) feature matrix
        y: (n_samples,) bool labels — next-day close > rise_threshold * today's close
        today_x: (window * 3,) features ending at the latest row, for inference.
                 None if there isn't enough history.
    """
    feats = df[["Change", "RSI", "Momentum"]].to_numpy()
    closes = df["Close"].to_numpy()

    if len(feats) < window:
        return np.empty((0, window * 3)), np.empty((0,), dtype=bool), None

    today_x = feats[-window:].flatten()

    n = len(feats) - window
    X = np.empty((n, window * 3), dtype=np.float64)
    y = np.empty(n, dtype=bool)
    for j in range(n):
        X[j] = feats[j : j + window].flatten()
        y[j] = closes[j + window - 1] * rise_threshold < closes[j + window]
    return X, y, today_x
