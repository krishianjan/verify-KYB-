"""Summarizer interface. The LLM only EXPLAINS the deterministic result."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..dto import CrawlResult, DomainInfo, FootprintResult


class Summarizer(ABC):
    @abstractmethod
    def summarize(
        self,
        company_name: str,
        crawl: CrawlResult,
        domain: DomainInfo,
        footprint: FootprintResult,
    ) -> str:
        """Return a short human-readable explanation of the footprint verdict."""
