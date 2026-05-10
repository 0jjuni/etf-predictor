"""Daily training entry point + reusable building blocks for backfill.

Live flow (`python -m ml.train`):
  1. Fetch ETF universe and per-symbol histories from FDR.
  2. Build sliding-window features and labels using all available history.
  3. Train/test split, fit XGBoost, compute the holdout precision/recall curve.
  4. Refit on full data, predict today's row for every ETF.
  5. Write predictions + model_metrics to Supabase, persist the model artifact.
  6. Resolve any past predictions whose target_date close is now known.

The reusable functions are also called from `scripts/backfill.py` to walk
the model forward through historical dates one at a time.
"""
from __future__ import annotations

import logging
import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from tqdm import tqdm
from xgboost import XGBClassifier

from app.db import (
    fetch_pending_outcomes,
    insert_predictions,
    update_prediction_outcome,
    upsert_daily_probabilities,
    upsert_model_metrics,
)
from ml.config import (
    MODEL_FILENAME,
    PROB_THRESHOLD,
    RISE_THRESHOLD,
    THRESHOLD_GRID,
    WINDOW,
    XGB_PARAMS,
)
from ml.data import (
    KST,
    closes_around,
    fetch_etf_universe,
    fetch_history,
    trim_to_cutoff,
)
from ml.features import add_features, build_windows
from ml.news import fetch_news

log = logging.getLogger("etf.train")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "artifacts"))


def _target_date_str(now: datetime) -> str:
    """Next trading date the prediction applies to.

    KRX is closed on weekends. We don't track public holidays here — those days
    just produce a "0 picks today" naturally because the FDR history won't
    advance past the previous trading day.
    """
    base = now.date() if now.hour < 18 else (now + timedelta(days=1)).date()
    while base.weekday() >= 5:  # 5=Sat, 6=Sun
        base += timedelta(days=1)
    return base.isoformat()


# --------------------------------------------------------------------------- #
# Reusable building blocks
# --------------------------------------------------------------------------- #

def fetch_universe_histories(
    universe: pd.DataFrame,
    *,
    desc: str = "fetch",
    max_workers: int = 16,
) -> dict[str, pd.DataFrame]:
    """Fetch FDR history for every symbol. Skips symbols that error out.

    HTTP-bound, so we use a thread pool. Tunable via the FDR_WORKERS env
    var; defaults to 16. Returns a dict keyed by Symbol — DataFrames are
    raw FDR output (no early-hours trimming).
    """
    workers = int(os.environ.get("FDR_WORKERS", max_workers))
    out: dict[str, pd.DataFrame] = {}

    # FDR uses urllib/requests under the hood with no timeout — a single
    # slow remote can wedge a worker thread forever. Set a global socket
    # timeout for the duration of this call so any hung HTTPS connection
    # raises and the symbol is skipped.
    timeout_s = float(os.environ.get("FDR_TIMEOUT", "20"))
    prev_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout_s)

    def _one(symbol: str, name: str) -> tuple[str, str, pd.DataFrame | None, str | None]:
        try:
            return symbol, name, fetch_history(symbol), None
        except Exception as e:  # noqa: BLE001
            return symbol, name, None, repr(e)

    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [
                ex.submit(_one, row.Symbol, row.Name)
                for row in universe.itertuples(index=False)
            ]
            for fut in tqdm(as_completed(futures), total=len(futures), desc=desc):
                sym, name, df, err = fut.result()
                if df is not None:
                    out[sym] = df
                else:
                    log.warning("skip fetch %s (%s): %s", sym, name, err)
    finally:
        socket.setdefaulttimeout(prev_timeout)

    return out


def build_dataset(
    histories: dict[str, pd.DataFrame],
    universe: pd.DataFrame,
    *,
    cutoff: pd.Timestamp | None = None,
) -> tuple[np.ndarray, np.ndarray, list[tuple[str, str, np.ndarray]]]:
    """Sliding-window features over the universe.

    If `cutoff` is given, every history is first trimmed to rows strictly
    before that timestamp — used by backfill to prevent target-date leakage.
    """
    X_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    today_rows: list[tuple[str, str, np.ndarray]] = []

    for row in universe.itertuples(index=False):
        df = histories.get(row.Symbol)
        if df is None:
            continue
        try:
            if cutoff is not None:
                df = trim_to_cutoff(df, cutoff)
            df = add_features(df)
            X, y, today_x = build_windows(df, rise_threshold=RISE_THRESHOLD)
        except Exception as e:  # noqa: BLE001
            log.warning("skip build %s (%s): %s", row.Symbol, row.Name, e)
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
    """Cumulative precision/recall/f1 at each threshold in THRESHOLD_GRID."""
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


def train_model(X: np.ndarray, y: np.ndarray) -> tuple[XGBClassifier, dict]:
    """Train on 80% of (X, y), report on the holdout, then refit on full data.

    Returns (model fit on full X/y, holdout dict with curve + summary stats).
    """
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

    log.info("Refitting on full dataset")
    model.fit(X, y)

    return model, {
        "test_size": int(len(test_y)),
        "positive_rate": float(test_y.mean()),
        "curve": curve,
    }


def make_predictions(
    model: XGBClassifier,
    today_rows: list[tuple[str, str, np.ndarray]],
    target_date: str,
) -> list[dict]:
    """Filter ETFs whose probability clears PROB_THRESHOLD and shape DB rows."""
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


def compute_all_probabilities(
    model: XGBClassifier,
    today_rows: list[tuple[str, str, np.ndarray]],
    target_date: str,
) -> list[dict]:
    """Probability for EVERY ETF — used by the browse-all-ETFs UI tab."""
    if not today_rows:
        return []
    X_today = np.vstack([row[2] for row in today_rows])
    proba = model.predict_proba(X_today)[:, 1]
    return [
        {
            "target_date": target_date,
            "symbol": symbol,
            "name": name,
            "probability": float(p),
        }
        for (symbol, name, _), p in zip(today_rows, proba)
    ]


def _precision_at_band(prob: float, curve: list[dict]) -> float | None:
    """Highest threshold the prob crosses; return its precision (None if below grid)."""
    sorted_curve = sorted(curve, key=lambda r: r["threshold"])
    best: float | None = None
    for row in sorted_curve:
        if prob >= row["threshold"]:
            best = row.get("precision")
        else:
            break
    return best


def compute_fallback_picks(
    model: XGBClassifier,
    today_rows: list[tuple[str, str, np.ndarray]],
    holdout_curve: list[dict],
    *,
    max_picks: int = 2,
) -> list[dict]:
    """Top-N highest-proba ETFs to surface when nothing crosses PROB_THRESHOLD.

    Walks down THRESHOLD_GRID from PROB_THRESHOLD - 0.05 until at least one ETF
    crosses; reports each pick's precision at the *band* (highest crossed
    threshold) so users see the calibrated quality of the recommendation.

    Returns [] if today_rows is empty.
    """
    from ml.config import THRESHOLD_GRID

    if not today_rows:
        return []
    X = np.vstack([r[2] for r in today_rows])
    proba = model.predict_proba(X)[:, 1]

    descending = sorted(
        [t for t in THRESHOLD_GRID if t < PROB_THRESHOLD], reverse=True
    )
    chosen_threshold: float | None = None
    chosen_indices: list[int] = []
    for t in descending:
        idxs = [i for i, p in enumerate(proba) if p >= t]
        if idxs:
            chosen_threshold = t
            chosen_indices = sorted(idxs, key=lambda i: -proba[i])[:max_picks]
            break

    if not chosen_indices:
        return []

    picks: list[dict] = []
    for idx in chosen_indices:
        sym, name, _ = today_rows[idx]
        p = float(proba[idx])
        picks.append(
            {
                "symbol": sym,
                "name": name,
                "probability": p,
                "precision_band": _precision_at_band(p, holdout_curve),
                "fallback_threshold": chosen_threshold,
            }
        )
    return picks


def attach_outcomes(
    predictions: list[dict],
    histories: dict[str, pd.DataFrame],
    target_date: str,
) -> list[dict]:
    """If close[target_date] is already in histories, fill outcome columns
    on each prediction in place. Returns the same list for chaining."""
    target = pd.Timestamp(target_date)
    for row in predictions:
        df = histories.get(row["symbol"])
        if df is None:
            continue
        cd = closes_around(df, target)
        if cd is None:
            continue
        prev_close, target_close = cd
        change = target_close / prev_close - 1
        row["actual_close_prev"] = prev_close
        row["actual_close_target"] = target_close
        row["actual_change"] = float(change)
        row["outcome"] = bool(change >= row["rise_threshold"] - 1)
        row["resolved_at"] = datetime.now(KST).isoformat()
    return predictions


def resolve_pending(histories: dict[str, pd.DataFrame]) -> int:
    """Fill outcome columns on any predictions where outcome is still null
    and we now have close[target_date]. Returns the number resolved."""
    pending = fetch_pending_outcomes()
    if not pending:
        return 0

    resolved = 0
    for row in pending:
        df = histories.get(row["symbol"])
        if df is None:
            continue
        cd = closes_around(df, pd.Timestamp(row["target_date"]))
        if cd is None:
            continue
        prev_close, target_close = cd
        change = target_close / prev_close - 1
        update_prediction_outcome(
            prediction_id=row["id"],
            actual_close_prev=prev_close,
            actual_close_target=target_close,
            actual_change=float(change),
            outcome=bool(change >= row["rise_threshold"] - 1),
        )
        resolved += 1
    log.info("Resolved %d/%d pending outcomes", resolved, len(pending))
    return resolved


def save_model(model: XGBClassifier) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / MODEL_FILENAME
    joblib.dump({"model": model, "window": WINDOW, "rise_threshold": RISE_THRESHOLD}, path)
    log.info("Saved model -> %s (%.1f MB)", path, path.stat().st_size / 1e6)
    return path


# --------------------------------------------------------------------------- #
# Daily entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    target_date = _target_date_str(datetime.now(KST))
    log.info("Target date: %s", target_date)

    universe = fetch_etf_universe()
    log.info("ETF universe: %d symbols", len(universe))
    histories = fetch_universe_histories(universe)

    X, y, today_rows = build_dataset(histories, universe)
    model, holdout = train_model(X, y)
    save_model(model)

    all_proba = compute_all_probabilities(model, today_rows, target_date)
    upsert_daily_probabilities(all_proba)
    log.info("Wrote %d daily_probabilities rows", len(all_proba))

    preds = make_predictions(model, today_rows, target_date)
    log.info("Predictions above threshold: %d", len(preds))
    for p in preds[:20]:
        log.info("  %s %s  prob=%.3f", p["symbol"], p["name"], p["probability"])

    fallback: list[dict] = []
    if not preds:
        fallback = compute_fallback_picks(model, today_rows, holdout["curve"])
        for fp in fallback:
            fp["news_json"] = fetch_news(fp["name"])
        log.info(
            "Fallback picks (display-only): %d at threshold=%s",
            len(fallback),
            fallback[0]["fallback_threshold"] if fallback else None,
        )

    upsert_model_metrics(
        target_date=target_date,
        test_size=holdout["test_size"],
        positive_rate=holdout["positive_rate"],
        curve=holdout["curve"],
        fallback_picks=fallback or None,
    )

    if preds:
        for pred in preds:
            pred["news_json"] = fetch_news(pred["name"])
        insert_predictions(preds)
        log.info("Wrote %d predictions to Supabase", len(preds))

    resolve_pending(histories)


if __name__ == "__main__":
    main()
