"""Firecrawl scrape backend (needs FIRECRAWL_API_KEY).

POSTs to `/v2/scrape` and returns the page as clean markdown — no local browser
needed. Returns ok=False on any failure so the tiered chain falls through.
"""
from __future__ import annotations

import re

import httpx

from ...config import settings
from ..dto import CrawlResult
from .base import WebCrawler

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4})")


class FirecrawlCrawler(WebCrawler):
    source = "firecrawl"

    def __init__(self, timeout: int = 60) -> None:
        self._timeout = timeout
        self._key = settings.firecrawl_api_key
        self._base = settings.firecrawl_base_url.rstrip("/")

    def fetch(self, url: str) -> CrawlResult:
        if not self._key:
            return CrawlResult(url=url, source=self.source, ok=False,
                               error="no FIRECRAWL_API_KEY")
        target = url if url.startswith(("http://", "https://")) else f"https://{url}"
        try:
            resp = httpx.post(
                f"{self._base}/v2/scrape",
                headers={"Authorization": f"Bearer {self._key}",
                         "Content-Type": "application/json"},
                json={"url": target, "formats": ["markdown", "links"]},
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                return CrawlResult(url=url, source=self.source, ok=False,
                                   error=f"HTTP {resp.status_code}")
            body = resp.json()
        except Exception as exc:  # noqa: BLE001
            return CrawlResult(url=url, source=self.source, ok=False, error=str(exc))

        data = body.get("data") if isinstance(body.get("data"), dict) else body
        md = re.sub(r"\n{3,}", "\n\n", str(data.get("markdown") or "")).strip()
        meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        title = meta.get("title")
        status = meta.get("statusCode")
        links = data.get("links") or []
        if not isinstance(links, list):
            links = []
        emails = sorted(set(_EMAIL_RE.findall(md)))[:20]
        phones = sorted({p.strip() for p in _PHONE_RE.findall(md)
                         if len(re.sub(r"\D", "", p)) >= 7})[:20]

        return CrawlResult(
            url=url,
            final_url=meta.get("sourceURL") or target,
            status_code=status,
            title=title,
            text=md,
            links=[l for l in links if isinstance(l, str)][:100],
            emails=emails,
            phones=phones,
            source=self.source,
            ok=len(md) > 0,
        )
