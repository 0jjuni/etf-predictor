"""Daily training entry point. Run once per day before market open.

Steps:
  1. Pull the ETF universe and per-symbol histories from FDR.
  2. Build sliding-window features and labels.
  3. Fit XGBoost on the full set, log a held-out classification report.
  4. Predict today's row for every ETF and keep those with prob >= threshold.
  5. Write predictions to Supabase and persist the model artifact.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import numpy as np
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from tqdm import tqdm
from xgboost import XGBClassifier

from app.db import insert_predictions
from ml.config import (
    MODEL_FILENAME,
    PROB_THRESHOLD,
    RISE_THRESHOLD,
    WINDOW,
    XGB_PARAMS,
)
from ml.data import KST, fetch_etf_universe, fetch_history
from ml.features import add_features, build_windows

log = logging.getLogger("etf.train")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "artifacts"))


def _target_date(now: datetime) -> str:
    """The trading date our predictions apply to."""
    base = now if now.hour < 18 else now + timedelta(days=1)
    return base.date().isoformat()


def collect_dataset() -> tuple[np.ndarray, np.ndarray, list[tuple[str, str, np.ndarray]]]:
    universe = fetch_etf_universe()
    log.info("ETF universe: %d symbols", len(universe))

    X_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    today_rows: list[tuple[str, str, np.ndarray]] = []

    for row in tqdm(universe.itertuples(index=False), total=len(universe), desc="fetch"):
        try:
            df = fetch_history(row.Symbol)
            df = add_features(df)
            X, y, today_x = build_windows(df, rise_threshold=RISE_THRESHOLD)
        except Exception as e:  # noqa: BLE001 — we want to skip any flaky symbol
            log.warning("skip %s (%s): %s", row.Symbol, row.Name, e)
            continue

        if len(X) > 0:
            X_parts.append(X)
            y_parts.append(y)
        if today_x is not None:
            today_rows.append((row.Symbol, row.Name, today_x))

    if not X_parts:
        raise RuntimeError("No training samples produced — check FDR/network")

    return np.vstack(X_parts), np.concatenate(y_parts), today_rows


def train_and_report(X: np.ndarray, y: np.ndarray) -> XGBClassifier:
    log.info("Training set: %s, positive rate=%.4f", X.shape, y.mean())

    train_x, test_x, train_y, test_y = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = XGBClassifier(**XGB_PARAMS)
    model.fit(train_x, train_y)

    log.info(
        "Holdout report (threshold=0.5):\n%s",
        classification_report(test_y, model.predict(test_x)),
    )
    proba = model.predict_proba(test_x)[:, 1]
    log.info(
        "Holdout report (threshold=%.2f):\n%s",
        PROB_THRESHOLD,
        classification_report(test_y, (proba >= PROB_THRESHOLD).astype(int)),
    )

    log.info("Refitting on full dataset")
    model.fit(X, y)
    return model


def predict_today(
    model: XGBClassifier,
    today_rows: list[tuple[str, str, np.ndarray]],
) -> list[dict]:
    if not today_rows:
        return []
    X_today = np.vstack([row[2] for row in today_rows])
    proba = model.predict_proba(X_today)[:, 1]
    target_date = _target_date(datetime.now(KST))

    out: list[dict] = []
    for (symbol, name, _), p in zip(today_rows, proba):
        if p >= PROB_THRESHOLD:
            out.append(
                {
                    "target_date": target_date,
                    "symbol": symbol,
                    "name": name,
                    "probability": float(p),
                    "rise_threshold": RISE_THRESHOLD,
                }
            )
    out.sort(key=lambda r: r["probability"], reverse=True)
    return out


def save_model(model: XGBClassifier) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / MODEL_FILENAME
    joblib.dump({"model": model, "window": WINDOW, "rise_threshold": RISE_THRESHOLD}, path)
    log.info("Saved model -> %s (%.1f MB)", path, path.stat().st_size / 1e6)
    return path


def main() -> None:
    X, y, today_rows = collect_dataset()
    model = train_and_report(X, y)
    save_model(model)

    preds = predict_today(model, today_rows)
    log.info("Predictions above threshold: %d", len(preds))
    for p in preds[:20]:
        log.info("  %s %s  prob=%.3f", p["symbol"], p["name"], p["probability"])

    if preds:
        insert_predictions(preds)
        log.info("Wrote %d predictions to Supabase", len(preds))
    else:
        log.info("No predictions above threshold; nothing written")


if __name__ == "__main__":
    main()
