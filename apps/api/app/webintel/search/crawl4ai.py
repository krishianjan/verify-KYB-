"""Crawl4AI cloud search provider (needs a verified CRAWL4AI_API_KEY).

Uses the hosted GET `/search` endpoint (JSON results). Free tier: 1,000 credits
/month. If the key is missing/unverified (401) or the call fails/returns nothing,
it transparently falls back to the free DuckDuckGo provider so enrichment always
has results.
"""
from __future__ import annotations

import httpx

from ...config import settings
from .base import SearchHit, SearchProvider
from .ddg import DdgSearch


class Crawl4aiSearch(SearchProvider):
    source = "crawl4ai"

    def __init__(self, timeout: int = 20) -> None:
        self._timeout = timeout
        self._key = settings.crawl4ai_api_key
        self._base = settings.crawl4ai_base_url.rstrip("/")
        self._fallback = DdgSearch()

    def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        if not query:
            return []
        hits = self._cloud_search(query, max_results) if self._key else []
        if hits:
            return hits
        # Not verified yet / rate-limited / empty -> free fallback.
        return self._fallback.search(query, max_results)

    def _cloud_search(self, query: str, max_results: int) -> list[SearchHit]:
        try:
            resp = httpx.get(
                f"{self._base}/search",
                params={"q": query, "limit": max_results},
                headers={"Authorization": f"Bearer {self._key}"},
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:  # noqa: BLE001
            return []
        return _rows_to_hits(data, max_results, self.source)


def _rows_to_hits(data, max_results: int, source: str) -> list[SearchHit]:
    # Accept a few plausible shapes: {results:[...]}, {data:[...]}, or a bare list.
    if isinstance(data, dict):
        rows = data.get("results") or data.get("data") or data.get("organic") or []
    elif isinstance(data, list):
        rows = data
    else:
        rows = []
    hits: list[SearchHit] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        url = r.get("url") or r.get("link") or r.get("href")
        if not url:
            continue
        hits.append(SearchHit(
            url=url,
            title=r.get("title") or r.get("name"),
            snippet=r.get("snippet") or r.get("description") or r.get("text"),
            source=source,
        ))
        if len(hits) >= max_results:
            break
    return hits
