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
