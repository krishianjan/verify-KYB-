"""Tiered crawler: try free crawlers first, fall back to paid ones.

A page is 'good enough' if ok=True and it has more than `min_text` chars.
Otherwise we advance to the next crawler. Returns the best result seen.
"""
from __future__ import annotations

from ..dto import CrawlResult
from .base import WebCrawler


class TieredCrawler(WebCrawler):
    source = "tiered"

    def __init__(self, crawlers: list[WebCrawler], min_text: int = 200) -> None:
        if not crawlers:
            raise ValueError("TieredCrawler needs at least one crawler")
        self._crawlers = crawlers
        self._min_text = min_text

    def fetch(self, url: str) -> CrawlResult:
        best: CrawlResult | None = None
        for crawler in self._crawlers:
            result = crawler.fetch(url)
            if result.ok and len(result.text) >= self._min_text:
                return result
            # keep the most informative partial result as a fallback
            if best is None or len(result.text) > len(best.text):
                best = result
        return best  # type: ignore[return-value]
