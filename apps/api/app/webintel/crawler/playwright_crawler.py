"""Playwright crawler for JS-heavy sites (real headless Chromium).

Slower and heavier than StaticCrawler, so it sits between static and Apify in
the tiered chain: used only when the static fetch returns thin/empty content.
Requires `pip install playwright` + `playwright install chromium`.
"""
from __future__ import annotations

import re

from ..dto import CrawlResult
from .base import WebCrawler
from .static import _EMAIL_RE, _PHONE_RE, _UA, _extract


class PlaywrightCrawler(WebCrawler):
    source = "playwright"

    def __init__(self, timeout: int = 25) -> None:
        self._timeout_ms = timeout * 1000

    def fetch(self, url: str) -> CrawlResult:
        target = url if url.startswith(("http://", "https://")) else f"https://{url}"
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=_UA)
                try:
                    resp = page.goto(
                        target, wait_until="domcontentloaded",
                        timeout=self._timeout_ms,
                    )
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:  # noqa: BLE001
                        pass
                    status = resp.status if resp else None
                    final_url = page.url
                    html = page.content()
                finally:
                    browser.close()
        except Exception as exc:  # noqa: BLE001
            return CrawlResult(url=url, source=self.source, ok=False, error=str(exc))

        title, meta_desc, text, links = _extract(html, final_url)
        emails = sorted(set(_EMAIL_RE.findall(html)))[:20]
        phones = sorted(
            {p.strip() for p in _PHONE_RE.findall(text)
             if len(re.sub(r"\D", "", p)) >= 7}
        )[:20]

        return CrawlResult(
            url=url, final_url=final_url, status_code=status, title=title,
            meta_description=meta_desc, text=text, html_len=len(html),
            links=links[:100], emails=emails, phones=phones,
            source=self.source, ok=bool(text),
        )
