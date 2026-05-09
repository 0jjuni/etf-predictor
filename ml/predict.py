"""Ad-hoc inference: load the saved artifact and predict for one or all ETFs.

This is for local exploration. The Streamlit app reads predictions from
Supabase rather than re-running inference per request.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from ml.config import MODEL_FILENAME
from ml.data import fetch_etf_universe, fetch_history
from ml.features import add_features, build_windows


def load_model(artifact_dir: str | Path = "artifacts") -> dict:
    return joblib.load(Path(artifact_dir) / MODEL_FILENAME)


def predict_symbol(symbol: str, bundle: dict) -> float | None:
    df = add_features(fetch_history(symbol))
    _, _, today_x = build_windows(df, rise_threshold=bundle["rise_threshold"])
    if today_x is None:
        return None
    return float(bundle["model"].predict_proba(today_x[np.newaxis, :])[0, 1])


def predict_all(bundle: dict) -> list[tuple[str, str, float]]:
    universe = fetch_etf_universe()
    out: list[tuple[str, str, float]] = []
    for row in universe.itertuples(index=False):
        try:
            p = predict_symbol(row.Symbol, bundle)
        except Exception:
            continue
        if p is not None:
            out.append((row.Symbol, row.Name, p))
    out.sort(key=lambda r: r[2], reverse=True)
    return out
