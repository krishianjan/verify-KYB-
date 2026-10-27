"""FROZEN CONTRACT — the web crawler interface.

Implementations fetch ONE url and return a CrawlResult. They must never raise
for ordinary failures (timeouts, 404, JS walls) — return ok=False with an error
string so the tiered chain can fall through to the next crawler.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..dto import CrawlResult


class WebCrawler(ABC):
    source: str = "unknown"

    @abstractmethod
    def fetch(self, url: str) -> CrawlResult:
        """Fetch and extract a single page. Return ok=False on failure."""
