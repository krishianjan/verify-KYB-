"""Offline mock crawler so Feature 2 runs with zero keys/network.

Fabricates a rich page for normal URLs and a thin/ghost page when the URL
contains 'ghost' or 'thin', so the analyzer's signals can be exercised.
"""
from __future__ import annotations

from ..dto import CrawlResult
from .base import WebCrawler


class MockCrawler(WebCrawler):
    source = "mock"

    def fetch(self, url: str) -> CrawlResult:
        low = url.lower()
        if "ghost" in low or "thin" in low:
            return CrawlResult(
                url=url, final_url=url, status_code=200, title="Welcome",
                meta_description=None, text="Welcome to our website. Coming soon.",
                html_len=200, links=[], emails=[], phones=[],
                source=self.source, ok=True,
            )
        return CrawlResult(
            url=url, final_url=url, status_code=200,
            title="ACME Trading Ltd — Industrial Supplies",
            meta_description="ACME Trading Ltd supplies industrial parts since 2015.",
            text=(
                "ACME Trading Ltd is a UK supplier of industrial components and "
                "fasteners, trading since 2015. We serve manufacturers across the "
                "UK and Europe with same-day dispatch, a dedicated account team, "
                "and ISO-certified quality processes. Contact us at "
                "info@acme-trading.example or call +44 20 7946 0000. Our registered "
                "office is 1 Example Street, London EC1A 1AA. On our About page you "
                "can read our company history, meet the leadership team, and view "
                "the services and product categories we offer, including bearings, "
                "seals, tooling, and custom fabrication. Frequently asked questions "
                "cover shipping, returns, trade accounts, and bulk pricing."
            ),
            html_len=8000,
            links=["/about", "/contact", "/services", "/team"],
            emails=["info@acme-trading.example"],
            phones=["+44 20 7946 0000"],
            source=self.source, ok=True,
        )
