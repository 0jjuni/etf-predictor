"""Daily training entry point. Run once per day before market open.

Steps:
  1. Pull the ETF universe and per-symbol histories from FDR.
  2. Build sliding-window features and labels.
  3. Train/test split, fit XGBoost, compute the holdout precision/recall curve.
  4. Refit on the full set, predict today's row for every ETF.
  5. Write predictions + model_metrics to Supabase, persist the model artifact.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from tqdm import tqdm
from xgboost import XGBClassifier

from app.db import insert_predictions, upsert_model_metrics
from ml.config import (
    MODEL_FILENAME,
    PROB_THRESHOLD,
    RISE_THRESHOLD,
    THRESHOLD_GRID,
    WINDOW,
    XGB_PARAMS,
)
from ml.data import KST, fetch_etf_universe, fetch_history
from ml.features import add_features, build_windows

log = logging.getLogger("etf.train")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "artifacts"))


def _target_date(now: datetime) -> str:
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
        except Exception as e:  # noqa: BLE001 — skip any flaky symbol
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


def compute_threshold_curve(y_true: np.ndarray, proba: np.ndarray) -> list[dict]:
    """Cumulative precision/recall/f1 at each threshold in THRESHOLD_GRID.

    For each T: keep predictions with proba >= T, count TP/FP/FN against y_true.
    A user reading the table can think "if the app only surfaces picks with
    confidence >= T, this is the precision they should expect."
    """
    y_true = y_true.astype(bool)
    rows: list[dict] = []
    total_positives = int(y_true.sum())

    for t in THRESHOLD_GRID:
        pred = proba >= t
        n_pred = int(pred.sum())
        tp = int((pred & y_true).sum())
        fp = n_pred - tp
        fn = total_positives - tp
        precision = tp / n_pred if n_pred else None
        recall = tp / total_positives if total_positives else None
        if precision is None or recall is None or (precision + recall) == 0:
            f1 = None
        else:
            f1 = 2 * precision * recall / (precision + recall)
        rows.append(
            {
                "threshold": t,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support_total": n_pred,
                "support_positive": tp,
            }
        )
    return rows


def split_train_evaluate(X: np.ndarray, y: np.ndarray) -> tuple[XGBClassifier, dict]:
    log.info("Training set: %s, positive rate=%.4f", X.shape, y.mean())

    train_x, test_x, train_y, test_y = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = XGBClassifier(**XGB_PARAMS)
    model.fit(train_x, train_y)

    proba = model.predict_proba(test_x)[:, 1]
    log.info(
        "Holdout report (threshold=0.5):\n%s",
        classification_report(test_y, model.predict(test_x)),
    )
    log.info(
        "Holdout report (threshold=%.2f):\n%s",
        PROB_THRESHOLD,
        classification_report(test_y, (proba >= PROB_THRESHOLD).astype(int)),
    )

    curve = compute_threshold_curve(test_y, proba)
    for row in curve:
        prec = row["precision"]
        log.info(
            "  T=%.2f  prec=%s  rec=%s  support=%d",
            row["threshold"],
            f"{prec:.3f}" if prec is not None else "n/a",
            f"{row['recall']:.3f}" if row["recall"] is not None else "n/a",
            row["support_total"],
        )

    holdout = {
        "test_size": int(len(test_y)),
        "positive_rate": float(test_y.mean()),
        "curve": curve,
    }
    return model, holdout


def predict_today(
    model: XGBClassifier,
    today_rows: list[tuple[str, str, np.ndarray]],
    target_date: str,
) -> list[dict]:
    if not today_rows:
        return []
    X_today = np.vstack([row[2] for row in today_rows])
    proba = model.predict_proba(X_today)[:, 1]

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
    target_date = _target_date(datetime.now(KST))
    log.info("Target date: %s", target_date)

    X, y, today_rows = collect_dataset()
    model, holdout = split_train_evaluate(X, y)

    log.info("Refitting on full dataset")
    model.fit(X, y)
    save_model(model)

    upsert_model_metrics(
        target_date=target_date,
        test_size=holdout["test_size"],
        positive_rate=holdout["positive_rate"],
        curve=holdout["curve"],
    )
    log.info("Wrote model_metrics for %s", target_date)

    preds = predict_today(model, today_rows, target_date)
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
