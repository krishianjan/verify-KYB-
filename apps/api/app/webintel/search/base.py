"""FROZEN CONTRACT — the web-search provider interface (Feature 4).

A provider turns a query into ranked result rows. Implementations must NEVER
raise for ordinary failures (rate limit, network, empty) — return [] so the
enrichment agent degrades gracefully and the factory can fall back.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class SearchHit(BaseModel):
    url: str
    title: str | None = None
    snippet: str | None = None
    source: str = "unknown"      # which provider produced this row


class SearchProvider(ABC):
    source: str = "unknown"

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        """Free-text web search. Return [] on any failure."""
