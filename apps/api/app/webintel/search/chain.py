"""Priority-chain search: try each provider in order, return the first with hits.

Lets SEARCH_PROVIDER be a list like "firecrawl,crawl4ai,ddg" so paid providers
are tried first and free DDG is the guaranteed fallback.
"""
from __future__ import annotations

from .base import SearchHit, SearchProvider


class ChainSearch(SearchProvider):
    source = "chain"

    def __init__(self, providers: list[SearchProvider]) -> None:
        self._providers = providers

    def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        for p in self._providers:
            try:
                hits = p.search(query, max_results)
            except Exception:  # noqa: BLE001
                hits = []
            if hits:
                return hits
        return []
