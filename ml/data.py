"""ETF universe + price history loaders, wrapping FinanceDataReader."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import FinanceDataReader as fdr
import pandas as pd

from ml.config import EXCLUDE_NAME_PATTERN

KST = ZoneInfo("Asia/Seoul")


def fetch_etf_universe() -> pd.DataFrame:
    """KR ETF list, dropping synthetic/leveraged/futures/inverse names."""
    etf = fdr.StockListing("ETF/KR")
    mask = ~etf["Name"].str.contains(EXCLUDE_NAME_PATTERN, regex=True, na=False)
    return etf.loc[mask, ["Symbol", "Name"]].reset_index(drop=True)


def fetch_history(symbol: str, *, now: datetime | None = None) -> pd.DataFrame:
    """OHLCV history for a single symbol.

    If called before KRX close (15:30 KST) we drop the last row, which may
    contain incomplete intraday data echoed by the source.
    """
    df = fdr.DataReader(symbol)
    now = now or datetime.now(KST)
    if now.hour < 18:
        df = df.iloc[:-1]
    return df


def trim_to_cutoff(df: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Return rows strictly before `cutoff` (exclusive). cutoff should already be
    timezone-naive at midnight; FDR's index is also naive daily."""
    return df.loc[df.index < cutoff]


def closes_around(df: pd.DataFrame, target: pd.Timestamp) -> tuple[float, float] | None:
    """Look up close[target] and the previous trading day's close.

    Returns None if target isn't in the index, or if there is no prior row.
    """
    if target not in df.index:
        return None
    target_pos = df.index.get_loc(target)
    if target_pos == 0:
        return None
    return float(df["Close"].iloc[target_pos - 1]), float(df["Close"].iloc[target_pos])


def recent_trading_dates(df: pd.DataFrame, n: int) -> list[pd.Timestamp]:
    """The last n trading dates from a reference history (most recent first)."""
    return list(df.index[-n:][::-1])


KOSPI200_PROXY_SYMBOL = "069500"  # KODEX 200 — index proxy for market regime


def fetch_market_series() -> pd.Series:
    """Daily return of the KODEX 200 ETF, used as a market regime feature.
    Returns an empty Series on any error so callers can gracefully fall back."""
    try:
        df = fdr.DataReader(KOSPI200_PROXY_SYMBOL)
    except Exception:
        return pd.Series(dtype=float)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    series = df["Close"].pct_change().fillna(0.0)
    series.name = "Market_change"
    return series
