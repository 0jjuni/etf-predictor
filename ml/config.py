"""Project-wide constants. Override via env vars where useful."""
from __future__ import annotations

import os

WINDOW: int = 100
RSI_PERIOD: int = 14
MOMENTUM_PERIOD: int = 10

RISE_THRESHOLD: float = 1.025
PROB_THRESHOLD: float = 0.70

# Holdout precision/recall is reported at these thresholds and saved per-day to
# Supabase so the UI can show a precision band for each predicted ETF.
THRESHOLD_GRID: list[float] = [round(0.50 + 0.05 * i, 2) for i in range(10)]

EXCLUDE_NAME_PATTERN: str = "합성|레버리지|선물|인버스"

MODEL_FILENAME: str = "etf_xgb.joblib"

XGB_PARAMS: dict = {
    "tree_method": "hist",
    "device": os.environ.get("XGB_DEVICE", "cpu"),
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "n_jobs": -1,
    "eval_metric": "logloss",
}

KST_TRAIN_HOUR: int = 8
