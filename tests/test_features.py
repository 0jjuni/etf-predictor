"""Smoke tests for the feature pipeline — run with `pytest`."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.config import WINDOW
from ml.features import add_features, build_windows


def _synthetic_history(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    close = 10000 + np.cumsum(rng.normal(0, 50, n))
    df = pd.DataFrame({"Close": close})
    df["Change"] = df["Close"].pct_change().fillna(0)
    return df


def test_build_windows_shapes() -> None:
    df = add_features(_synthetic_history(200))
    X, y, today_x = build_windows(df, rise_threshold=1.025)

    assert X.ndim == 2
    assert X.shape[1] == WINDOW * 3
    assert y.shape[0] == X.shape[0]
    assert today_x is not None and today_x.shape == (WINDOW * 3,)


def test_build_windows_short_history_returns_no_today() -> None:
    df = add_features(_synthetic_history(50))
    X, y, today_x = build_windows(df, rise_threshold=1.025)
    assert X.shape[0] == 0
    assert y.shape[0] == 0
    assert today_x is None
