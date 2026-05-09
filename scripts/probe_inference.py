"""Quick diagnostic: train a fresh model on the latest data and inspect the
predicted probability distribution across all current ETFs.

Useful when the daily run ends with `0 predictions above threshold` and you
want to see how close (or far) the model came.

Run: uv run python -u scripts/probe_inference.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from ml.config import PROB_THRESHOLD
from ml.data import fetch_etf_universe
from ml.train import build_dataset, fetch_universe_histories, train_model

log = logging.getLogger("etf.probe")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> int:
    universe = fetch_etf_universe()
    log.info("Universe: %d symbols", len(universe))
    histories = fetch_universe_histories(universe, desc="fdr")

    X, y, today_rows = build_dataset(histories, universe)
    if not today_rows:
        log.error("no inference rows")
        return 1
    log.info("Training fresh model on %s samples (positive rate=%.4f)", X.shape, y.mean())

    model, _ = train_model(X, y)

    X_today = np.vstack([r[2] for r in today_rows])
    proba = model.predict_proba(X_today)[:, 1]

    log.info("Inference rows: %d", len(proba))
    log.info("Probability distribution:")
    for q in (0, 50, 75, 90, 95, 99, 100):
        log.info("  p%02d = %.4f", q, np.percentile(proba, q))
    log.info("mean=%.4f  std=%.4f", proba.mean(), proba.std())

    bins = [0.0, 0.3, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.0]
    counts, _ = np.histogram(proba, bins=bins)
    log.info("Histogram:")
    bar_max = max(counts.max(), 1)
    for lo, hi, n in zip(bins[:-1], bins[1:], counts):
        bar = "#" * int(int(n) / bar_max * 40) if n else ""
        log.info("  [%.2f, %.2f)  %5d  %s", lo, hi, int(n), bar)

    n_above = int((proba >= PROB_THRESHOLD).sum())
    log.info(
        "Above PROB_THRESHOLD=%.2f: %d ETFs (would be recommended today)",
        PROB_THRESHOLD,
        n_above,
    )

    log.info("Top 15 by probability:")
    order = np.argsort(-proba)[:15]
    for idx in order:
        sym, name, _ = today_rows[idx]
        log.info("  %s  %.4f  %s", sym, proba[idx], name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
