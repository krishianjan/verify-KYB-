"""Firecrawl search provider (needs FIRECRAWL_API_KEY).

Uses Firecrawl's hosted `/v2/search` endpoint (returns {data:{web:[...]}}).
Returns [] on any failure so the provider chain can fall through to the next.
"""
from __future__ import annotations

import httpx

from ...config import settings
from .base import SearchHit, SearchProvider


class FirecrawlSearch(SearchProvider):
    source = "firecrawl"

    def __init__(self, timeout: int = 25) -> None:
        self._timeout = timeout
        self._key = settings.firecrawl_api_key
        self._base = settings.firecrawl_base_url.rstrip("/")

    def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        if not (query and self._key):
            return []
        try:
            resp = httpx.post(
                f"{self._base}/v2/search",
                headers={"Authorization": f"Bearer {self._key}",
                         "Content-Type": "application/json"},
                json={"query": query, "limit": max_results},
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:  # noqa: BLE001
            return []
        return _rows_to_hits(data, max_results, self.source)


def _rows_to_hits(data, max_results: int, source: str) -> list[SearchHit]:
    # Firecrawl shapes seen: {data:[...]}, {data:{web:[...]}}, or a bare list.
    rows = []
    if isinstance(data, dict):
        d = data.get("data")
        if isinstance(d, dict):
            rows = d.get("web") or d.get("results") or []
        elif isinstance(d, list):
            rows = d
        else:
            rows = data.get("results") or []
    elif isinstance(data, list):
        rows = data
    hits: list[SearchHit] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        url = r.get("url") or r.get("link")
        if not url:
            continue
        hits.append(SearchHit(
            url=url,
            title=r.get("title") or r.get("name"),
            snippet=r.get("description") or r.get("snippet"),
            source=source,
        ))
        if len(hits) >= max_results:
            break
    return hits
