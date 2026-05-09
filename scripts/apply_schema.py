"""One-off schema applier. Reads SUPABASE_URL/DB_PASSWORD from env and runs db/schema.sql.

Run via: uv run --with "psycopg[binary]" python scripts/apply_schema.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

load_dotenv()

PROJECT_REF = urlparse(os.environ["SUPABASE_URL"]).hostname.split(".")[0]
PASSWORD = os.environ["DB_PASSWORD"]

SCHEMA = Path("db/schema.sql").read_text(encoding="utf-8")


def connect(use_pooler: bool):
    if use_pooler:
        return psycopg.connect(
            host="aws-0-ap-northeast-2.pooler.supabase.com",
            port=5432,
            user=f"postgres.{PROJECT_REF}",
            password=PASSWORD,
            dbname="postgres",
            sslmode="require",
        )
    return psycopg.connect(
        host=f"db.{PROJECT_REF}.supabase.co",
        port=5432,
        user="postgres",
        password=PASSWORD,
        dbname="postgres",
        sslmode="require",
    )


POOLER_HOSTS = [
    "aws-0-ap-northeast-2.pooler.supabase.com",
    "aws-1-ap-northeast-2.pooler.supabase.com",
    "aws-0-ap-northeast-1.pooler.supabase.com",
    "aws-1-ap-northeast-1.pooler.supabase.com",
]


def connect_pooler(host: str):
    return psycopg.connect(
        host=host,
        port=5432,
        user=f"postgres.{PROJECT_REF}",
        password=PASSWORD,
        dbname="postgres",
        sslmode="require",
        connect_timeout=10,
    )


def main() -> int:
    last_err: Exception | None = None
    attempts: list = [("direct", lambda: connect(False))]
    attempts += [(f"pooler:{h}", lambda h=h: connect_pooler(h)) for h in POOLER_HOSTS]
    for label, mk in attempts:
        try:
            print(f"--> connecting via {label}...")
            with mk() as conn:
                with conn.cursor() as cur:
                    cur.execute(SCHEMA)
                    cur.execute(
                        "select count(*) from information_schema.tables "
                        "where table_schema='public' and table_name='predictions'"
                    )
                    (n,) = cur.fetchone()
                conn.commit()
            print(f"OK schema applied. predictions table exists: {bool(n)}")
            return 0
        except Exception as e:
            last_err = e
            print(f"FAIL {type(e).__name__}: {e}")
    print(f"All attempts failed. Last error: {last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
