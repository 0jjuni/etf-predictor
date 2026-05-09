"""Supabase client + read/write helpers for the predictions table.

Two access modes:
  - service-role key  (training job, RLS bypassed) — env: SUPABASE_SERVICE_KEY
  - anon key          (Streamlit UI, read-only)    — env: SUPABASE_ANON_KEY

Both use the same SUPABASE_URL.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

PREDICTIONS_TABLE = "predictions"
METRICS_TABLE = "model_metrics"


def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


@lru_cache(maxsize=2)
def _client(role: str) -> Client:
    url = _require("SUPABASE_URL")
    key = _require("SUPABASE_SERVICE_KEY") if role == "service" else _require("SUPABASE_ANON_KEY")
    return create_client(url, key)


def insert_predictions(rows: list[dict]) -> None:
    """Upsert today's predictions. Idempotent on (target_date, symbol)."""
    if not rows:
        return
    _client("service").table(PREDICTIONS_TABLE).upsert(
        rows, on_conflict="target_date,symbol"
    ).execute()


def fetch_latest_predictions(limit: int = 100) -> list[dict]:
    """Read the most recent target_date's predictions, sorted by probability."""
    client = _client("anon")
    latest = (
        client.table(PREDICTIONS_TABLE)
        .select("target_date")
        .order("target_date", desc=True)
        .limit(1)
        .execute()
    )
    if not latest.data:
        return []
    target_date = latest.data[0]["target_date"]

    rows = (
        client.table(PREDICTIONS_TABLE)
        .select("*")
        .eq("target_date", target_date)
        .order("probability", desc=True)
        .limit(limit)
        .execute()
    )
    return rows.data or []


def upsert_model_metrics(
    target_date: str,
    test_size: int,
    positive_rate: float,
    curve: list[dict],
) -> None:
    """Write the holdout threshold curve for one training run."""
    _client("service").table(METRICS_TABLE).upsert(
        {
            "target_date": target_date,
            "test_size": int(test_size),
            "positive_rate": float(positive_rate),
            "metrics_json": curve,
        },
        on_conflict="target_date",
    ).execute()


def fetch_latest_model_metrics() -> dict | None:
    """Most recent model_metrics row, or None if not populated yet."""
    rows = (
        _client("anon")
        .table(METRICS_TABLE)
        .select("*")
        .order("target_date", desc=True)
        .limit(1)
        .execute()
    )
    return rows.data[0] if rows.data else None


def fetch_history_for(symbol: str, limit: int = 60) -> list[dict]:
    rows = (
        _client("anon")
        .table(PREDICTIONS_TABLE)
        .select("*")
        .eq("symbol", symbol)
        .order("target_date", desc=True)
        .limit(limit)
        .execute()
    )
    return rows.data or []


def fetch_pending_outcomes() -> list[dict]:
    """Predictions whose outcome column hasn't been filled in yet."""
    rows = (
        _client("service")
        .table(PREDICTIONS_TABLE)
        .select("id,target_date,symbol,rise_threshold")
        .is_("outcome", "null")
        .order("target_date")
        .execute()
    )
    return rows.data or []


def update_prediction_outcome(
    *,
    prediction_id: int,
    actual_close_prev: float,
    actual_close_target: float,
    actual_change: float,
    outcome: bool,
) -> None:
    """Fill outcome columns on a single prediction row by primary key."""
    from datetime import datetime, timezone

    _client("service").table(PREDICTIONS_TABLE).update(
        {
            "actual_close_prev": float(actual_close_prev),
            "actual_close_target": float(actual_close_target),
            "actual_change": float(actual_change),
            "outcome": bool(outcome),
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", prediction_id).execute()


def fetch_resolved_history(limit: int = 500) -> list[dict]:
    """Past predictions whose outcomes are already known. UI history tab."""
    rows = (
        _client("anon")
        .table(PREDICTIONS_TABLE)
        .select("*")
        .not_.is_("outcome", "null")
        .order("target_date", desc=True)
        .order("probability", desc=True)
        .limit(limit)
        .execute()
    )
    return rows.data or []
