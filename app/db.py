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
