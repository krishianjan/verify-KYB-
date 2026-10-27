"""Crawl4AI cloud scrape backend (needs a verified CRAWL4AI_API_KEY).

POSTs to the hosted `/scrape` endpoint and returns the page as clean,
LLM-ready markdown — no local browser install required. Returns ok=False on any
failure (401 before verification, rate limit, network) so the tiered chain falls
through to the next crawler.
"""
from __future__ import annotations

import re

import httpx

from ...config import settings
from ..dto import CrawlResult
from .base import WebCrawler

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4})")


class Crawl4aiCloudCrawler(WebCrawler):
    source = "crawl4ai_cloud"

    def __init__(self, timeout: int = 60) -> None:
        self._timeout = timeout
        self._key = settings.crawl4ai_api_key
        self._base = settings.crawl4ai_base_url.rstrip("/")

    def fetch(self, url: str) -> CrawlResult:
        if not self._key:
            return CrawlResult(url=url, source=self.source, ok=False,
                               error="no CRAWL4AI_API_KEY")
        target = url if url.startswith(("http://", "https://")) else f"https://{url}"
        try:
            resp = httpx.post(
                f"{self._base}/scrape",
                headers={"Authorization": f"Bearer {self._key}",
                         "Content-Type": "application/json"},
                json={"url": target},
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                return CrawlResult(url=url, source=self.source, ok=False,
                                   error=f"HTTP {resp.status_code}")
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            return CrawlResult(url=url, source=self.source, ok=False, error=str(exc))

        md = data.get("markdown") or data.get("content") or ""
        if isinstance(md, dict):  # some shapes nest markdown
            md = md.get("fit_markdown") or md.get("raw_markdown") or ""
        md = re.sub(r"\n{3,}", "\n\n", str(md)).strip()
        meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        title = data.get("title") or meta.get("title")
        links = data.get("links") or []
        if isinstance(links, dict):
            links = [x for grp in links.values() for x in (grp or [])]
        links = [l.get("href") if isinstance(l, dict) else l for l in links]

        emails = sorted(set(_EMAIL_RE.findall(md)))[:20]
        phones = sorted({p.strip() for p in _PHONE_RE.findall(md)
                         if len(re.sub(r"\D", "", p)) >= 7})[:20]

        return CrawlResult(
            url=url,
            final_url=data.get("url") or target,
            status_code=data.get("status_code"),
            title=title,
            text=md,
            html_len=len(data.get("html", "") or ""),
            links=[l for l in links if l][:100],
            emails=emails,
            phones=phones,
            source=self.source,
            ok=len(md) > 0,
        )
