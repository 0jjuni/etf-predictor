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
