"""Walk-forward backfill of the last N trading days.

For each historical target_date D (oldest first):
  1. Trim every ETF's history to rows strictly before D.
  2. Build features + labels and train a fresh XGBoost on that.
  3. Predict for D using the most recent window in the trimmed history.
  4. Look up the actual close on D (already known) to fill outcome fields.
  5. Upsert predictions and model_metrics.

This is **walk-forward without leakage**: the model used to predict D is
trained only on data strictly before D.

Run locally — the daily GH Actions cron should NOT run this.

  $env:XGB_DEVICE = "cuda"   # if you have a GPU
  uv run python scripts/backfill.py --days 7

Required env vars in .env:
  SUPABASE_URL, SUPABASE_SERVICE_KEY
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make `app`, `ml` importable when run as `python scripts/backfill.py`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from app.db import insert_predictions, upsert_daily_probabilities, upsert_model_metrics
from ml.data import fetch_etf_universe, recent_trading_dates
from ml.train import (
    attach_outcomes,
    build_dataset,
    compute_all_probabilities,
    compute_fallback_picks,
    fetch_universe_histories,
    make_predictions,
    train_model,
)

log = logging.getLogger("etf.backfill")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REFERENCE_SYMBOL = "069500"  # KODEX 200 — present in any reasonable backfill range


def _trading_dates(histories: dict[str, pd.DataFrame], days: int) -> list[pd.Timestamp]:
    ref = histories.get(REFERENCE_SYMBOL)
    if ref is None:
        # Fallback: use whichever ETF has the longest history
        ref = max(histories.values(), key=len)
    return list(reversed(recent_trading_dates(ref, days)))  # oldest first


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="number of trading days to backfill")
    args = parser.parse_args()

    log.info("Fetching ETF universe...")
    universe = fetch_etf_universe()
    log.info("Universe: %d symbols", len(universe))

    log.info("Fetching all histories from FDR (this is the slow part)...")
    histories = fetch_universe_histories(universe, desc="fdr")

    target_dates = _trading_dates(histories, args.days)
    log.info("Backfilling target dates: %s", [d.date().isoformat() for d in target_dates])

    for D in target_dates:
        target_str = D.date().isoformat()
        log.info("=" * 70)
        log.info("Backfill %s", target_str)

        X, y, today_rows = build_dataset(histories, universe, cutoff=D)
        log.info("  dataset: %s, positive rate=%.4f", X.shape, y.mean())

        model, holdout = train_model(X, y)

        all_proba = compute_all_probabilities(model, today_rows, target_str)
        upsert_daily_probabilities(all_proba)
        log.info("  daily_probabilities written: %d", len(all_proba))

        preds = make_predictions(model, today_rows, target_str)
        attach_outcomes(preds, histories, target_str)

        fallback: list[dict] = []
        if not preds:
            fallback = compute_fallback_picks(model, today_rows, holdout["curve"])

        upsert_model_metrics(
            target_date=target_str,
            test_size=holdout["test_size"],
            positive_rate=holdout["positive_rate"],
            curve=holdout["curve"],
            fallback_picks=fallback or None,
        )
        log.info("  model_metrics written (fallback=%d)", len(fallback))

        if preds:
            hits = sum(1 for p in preds if p.get("outcome"))
            log.info(
                "  predictions=%d  hits=%d  empirical_precision=%.3f",
                len(preds),
                hits,
                hits / len(preds),
            )
            insert_predictions(preds)
        else:
            log.info(
                "  no predictions above threshold (fallback picks: %s)",
                [f"{p['symbol']}@{p['probability']:.3f}" for p in fallback],
            )


if __name__ == "__main__":
    main()
