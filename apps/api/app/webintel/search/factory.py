"""Search-provider selection (env-driven), with a safe DDG fallback.

A chosen provider that can't initialize or isn't configured (missing key) falls
back to the free DuckDuckGo provider so enrichment always has a search path.
"""
from __future__ import annotations

from ...config import settings
from .base import SearchProvider
from .ddg import DdgSearch


def get_search_provider() -> SearchProvider:
    provider = (settings.search_provider or "ddg").lower()

    if provider == "crawl4ai" and settings.crawl4ai_api_key:
        from .crawl4ai import Crawl4aiSearch

        return Crawl4aiSearch()
    if provider == "apify" and settings.apify_api_token:
        from .apify import ApifySearch

        return ApifySearch()
    return DdgSearch()
