"""Search-provider selection (env-driven priority chain) with a DDG fallback.

SEARCH_PROVIDER is a comma-separated priority list, e.g. "firecrawl,crawl4ai".
Each named provider is tried in order; the free DuckDuckGo provider is always
appended last so enrichment always has a search path.
"""
from __future__ import annotations

from ...config import settings
from .base import SearchProvider
from .chain import ChainSearch
from .ddg import DdgSearch


def _build(name: str) -> SearchProvider | None:
    name = name.strip().lower()
    if name == "ddg":
        return DdgSearch()
    if name == "crawl4ai" and settings.crawl4ai_api_key:
        from .crawl4ai import Crawl4aiSearch

        return Crawl4aiSearch()
    if name == "firecrawl" and settings.firecrawl_api_key:
        from .firecrawl import FirecrawlSearch

        return FirecrawlSearch()
    if name == "apify" and settings.apify_api_token:
        from .apify import ApifySearch

        return ApifySearch()
    return None


def get_search_provider() -> SearchProvider:
    names = [n for n in (settings.search_provider or "ddg").split(",") if n.strip()]
    providers: list[SearchProvider] = []
    for n in names:
        p = _build(n)
        if p is not None:
            providers.append(p)
    # DDG is always the final, free fallback.
    if not any(isinstance(p, DdgSearch) for p in providers):
        providers.append(DdgSearch())
    return ChainSearch(providers)
