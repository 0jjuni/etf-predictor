"""Smoke tests for the feature pipeline — run with `pytest`."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.config import WINDOW
from ml.features import FEATURE_COLS, add_features, build_windows


def _synthetic_history(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    close = 10000 + np.cumsum(rng.normal(0, 50, n))
    high = close + np.abs(rng.normal(0, 20, n))
    low = close - np.abs(rng.normal(0, 20, n))
    volume = rng.integers(50_000, 1_000_000, n)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame(
        {"Close": close, "High": high, "Low": low, "Volume": volume},
        index=dates,
    )
    df["Change"] = df["Close"].pct_change().fillna(0)
    return df


def test_build_windows_shapes() -> None:
    df = add_features(_synthetic_history(300))
    X, y, dates, today_x = build_windows(df, rise_threshold=1.025)

    expected_features = WINDOW * len(FEATURE_COLS)
    assert X.ndim == 2
    assert X.shape[1] == expected_features
    assert y.shape[0] == X.shape[0]
    assert dates.shape[0] == X.shape[0]
    assert today_x is not None and today_x.shape == (expected_features,)


def test_build_windows_short_history_returns_no_today() -> None:
    df = add_features(_synthetic_history(50))
    X, y, dates, today_x = build_windows(df, rise_threshold=1.025)
    assert X.shape[0] == 0
    assert y.shape[0] == 0
    assert dates.shape[0] == 0
    assert today_x is None


def test_add_features_includes_market() -> None:
    df = _synthetic_history(150)
    market = df["Close"].pct_change().fillna(0).rename("Market_change")
    out = add_features(df, market=market)
    assert "Market_change" in out.columns
    assert "MACD_hist" in out.columns
    assert "BB_pctB" in out.columns
    assert len(out) > 0
