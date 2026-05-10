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

# Each entry maps a feature column name to the FDR symbol we use.
# Failures are tolerated; a missing column is filled with 0 in features.
MARKET_SOURCES: dict[str, str] = {
    "Market_KR": "069500",     # KODEX 200 (Korean market proxy)
    "Market_US500": "US500",   # S&P 500 (US large cap)
    "Market_NASDAQ": "IXIC",   # Nasdaq Composite (proxies Nasdaq 100)
    "Market_USDKRW": "USD/KRW",  # Won/Dollar — affects KR-listed US ETFs
}


def _safe_pct_change(symbol: str) -> pd.Series:
    try:
        df = fdr.DataReader(symbol)
    except Exception:
        return pd.Series(dtype=float)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    return df["Close"].pct_change().fillna(0.0)


def fetch_market_context() -> pd.DataFrame:
    """Daily-return DataFrame for several market proxies, indexed by date.

    Columns: Market_KR, Market_US500, Market_NASDAQ, Market_USDKRW.
    Each is filled independently — if a single source fails (FDR symbol
    missing, network blip), that column comes back as an empty series and
    the join in features.py fills missing dates with 0.
    """
    series_map: dict[str, pd.Series] = {}
    for col, sym in MARKET_SOURCES.items():
        s = _safe_pct_change(sym)
        if not s.empty:
            series_map[col] = s
    if not series_map:
        return pd.DataFrame()
    return pd.concat(series_map, axis=1)


def fetch_market_series() -> pd.Series:
    """Backwards-compat alias kept for older callers — returns just the KR
    column from `fetch_market_context()`."""
    df = fetch_market_context()
    if df.empty or "Market_KR" not in df.columns:
        return pd.Series(dtype=float)
    return df["Market_KR"].rename("Market_change")
