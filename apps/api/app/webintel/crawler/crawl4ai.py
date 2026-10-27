"""Crawl4AI crawler backend (open-source, LLM-ready markdown).

Uses the `crawl4ai` library (``pip install crawl4ai`` + ``crawl4ai-setup``) to
render JS-heavy pages and return clean markdown — ideal for feeding the LLM
enrichment step. Lazy-imported like the Apify adapter so the app boots without
it; returns ok=False (never raises) so the tiered chain can fall through.
"""
from __future__ import annotations

import asyncio
import re

from ..dto import CrawlResult
from .base import WebCrawler

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4})")


class Crawl4aiCrawler(WebCrawler):
    source = "crawl4ai"

    def __init__(self, timeout: int = 30) -> None:
        self._timeout = timeout

    def fetch(self, url: str) -> CrawlResult:
        target = url if url.startswith(("http://", "https://")) else f"https://{url}"
        try:
            return _run(self._afetch(target, url))
        except Exception as exc:  # noqa: BLE001
            return CrawlResult(url=url, source=self.source, ok=False, error=str(exc))

    async def _afetch(self, target: str, original: str) -> CrawlResult:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler() as crawler:
            res = await crawler.arun(url=target)

        markdown = _as_text(getattr(res, "markdown", None)) or ""
        md = re.sub(r"\n{3,}", "\n\n", markdown).strip()
        title = None
        meta = getattr(res, "metadata", None)
        if isinstance(meta, dict):
            title = meta.get("title")
        links = _links(getattr(res, "links", None))
        emails = sorted(set(_EMAIL_RE.findall(md)))[:20]
        phones = sorted(
            {p.strip() for p in _PHONE_RE.findall(md)
             if len(re.sub(r"\D", "", p)) >= 7}
        )[:20]
        status = getattr(res, "status_code", None)
        ok = bool(getattr(res, "success", True)) and len(md) > 0

        return CrawlResult(
            url=original,
            final_url=getattr(res, "url", target),
            status_code=status,
            title=title,
            text=md,
            html_len=len(getattr(res, "html", "") or ""),
            links=links[:100],
            emails=emails,
            phones=phones,
            source=self.source,
            ok=ok,
        )


def _as_text(markdown) -> str:
    if markdown is None:
        return ""
    if isinstance(markdown, str):
        return markdown
    # crawl4ai may return a MarkdownGenerationResult object.
    for attr in ("fit_markdown", "raw_markdown", "markdown"):
        val = getattr(markdown, attr, None)
        if isinstance(val, str) and val:
            return val
    return str(markdown)


def _links(links) -> list[str]:
    out: list[str] = []
    if isinstance(links, dict):
        for group in links.values():
            for item in group or []:
                href = item.get("href") if isinstance(item, dict) else item
                if href:
                    out.append(href)
    return out


def _run(coro):
    """Run an async coroutine from sync code, even if a loop already exists."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
