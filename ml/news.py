"""Best-effort news fetcher for recommended ETFs.

Uses Google News' public RSS endpoint — no API key, no quota you'll hit at
this volume (≤ a few dozen calls per day). All failures are swallowed and
return [] so a flaky network never breaks the training run.
"""
from __future__ import annotations

import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Final

log = logging.getLogger("etf.news")

USER_AGENT: Final = (
    "Mozilla/5.0 (compatible; etf-predictor/0.1; "
    "+https://github.com/0jjuni/etf-predictor)"
)
TIMEOUT_SECS: Final = 8
MAX_ITEMS: Final = 5


def _build_url(query: str) -> str:
    q = urllib.parse.quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"


def fetch_news(query: str, *, max_items: int = MAX_ITEMS) -> list[dict]:
    """Top recent news items for a query string. Returns [] on any failure."""
    if not query:
        return []
    req = urllib.request.Request(_build_url(query), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
            body = resp.read()
    except Exception as e:  # noqa: BLE001 — best-effort, never propagate
        log.warning("news fetch failed for %r: %s", query, e)
        return []

    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        log.warning("news parse failed for %r: %s", query, e)
        return []

    items: list[dict] = []
    for node in root.findall(".//item")[:max_items]:
        items.append(
            {
                "title": (node.findtext("title") or "").strip(),
                "url": (node.findtext("link") or "").strip(),
                "source": (node.findtext("source") or "").strip(),
                "published": (node.findtext("pubDate") or "").strip(),
            }
        )
    return [i for i in items if i["url"] and i["title"]]
