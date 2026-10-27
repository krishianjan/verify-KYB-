from __future__ import annotations

from ...config import settings
from .base import WebCrawler
from .mock import MockCrawler
from .static import StaticCrawler


def get_crawler() -> WebCrawler:
    provider = (settings.crawler_provider or "mock").lower()

    if provider == "mock":
        return MockCrawler()
    if provider == "static":
        return StaticCrawler(timeout=settings.crawl_timeout_seconds)
    if provider == "playwright":
        from .playwright_crawler import PlaywrightCrawler

        return PlaywrightCrawler(timeout=settings.crawl_timeout_seconds)
    if provider == "apify":
        from .apify import ApifyCrawler

        return ApifyCrawler()
    if provider == "crawl4ai":
        from .crawl4ai import Crawl4aiCrawler

        return Crawl4aiCrawler(timeout=settings.crawl_timeout_seconds)
    if provider == "crawl4ai_cloud":
        from .crawl4ai_cloud import Crawl4aiCloudCrawler

        return Crawl4aiCloudCrawler()
    if provider == "firecrawl":
        from .firecrawl import FirecrawlCrawler

        return FirecrawlCrawler()
    if provider == "tiered":
        # static (free) -> Firecrawl/Crawl4AI cloud (markdown, no local browser)
        # -> local Crawl4AI/Playwright for JS sites -> Apify backstop.
        from .tiered import TieredCrawler

        chain: list[WebCrawler] = [StaticCrawler(timeout=settings.crawl_timeout_seconds)]
        import importlib.util

        if settings.firecrawl_api_key:
            from .firecrawl import FirecrawlCrawler

            chain.append(FirecrawlCrawler())
        if settings.crawl4ai_api_key:
            from .crawl4ai_cloud import Crawl4aiCloudCrawler

            chain.append(Crawl4aiCloudCrawler())
        if importlib.util.find_spec("crawl4ai") is not None:
            from .crawl4ai import Crawl4aiCrawler

            chain.append(Crawl4aiCrawler(timeout=settings.crawl_timeout_seconds))
        if settings.enable_playwright:
            try:
                from .playwright_crawler import PlaywrightCrawler

                chain.append(PlaywrightCrawler(timeout=settings.crawl_timeout_seconds))
            except Exception:  # noqa: BLE001  (playwright not installed)
                pass
        if settings.apify_api_token:
            from .apify import ApifyCrawler

            chain.append(ApifyCrawler())
        return TieredCrawler(chain)

    raise ValueError(f"Unknown CRAWLER_PROVIDER: {provider!r}")
