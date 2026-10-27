"""Free, no-browser crawler: httpx fetch + BeautifulSoup extraction.

Handles the majority of business websites (static or server-rendered). The
tiered chain falls back to Apify when this returns ok=False or thin content.
"""
from __future__ import annotations

import re

import httpx

from ..dto import CrawlResult
from .base import WebCrawler

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4})")
_UA = "verifyKYB-footprint/1.0 (+https://example.com; compliance verification)"


class StaticCrawler(WebCrawler):
    source = "static"

    def __init__(self, timeout: int = 20) -> None:
        self._timeout = timeout

    def fetch(self, url: str) -> CrawlResult:
        target = url if url.startswith(("http://", "https://")) else f"https://{url}"
        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": _UA},
            ) as client:
                resp = client.get(target)
        except Exception as exc:  # noqa: BLE001
            return CrawlResult(url=url, source=self.source, ok=False, error=str(exc))

        html = resp.text or ""
        title, meta_desc, text, links = _extract(html, str(resp.url))
        emails = sorted(set(_EMAIL_RE.findall(html)))[:20]
        phones = sorted({p.strip() for p in _PHONE_RE.findall(text) if len(re.sub(r"\D", "", p)) >= 7})[:20]

        return CrawlResult(
            url=url,
            final_url=str(resp.url),
            status_code=resp.status_code,
            title=title,
            meta_description=meta_desc,
            text=text,
            html_len=len(html),
            links=links[:100],
            emails=emails,
            phones=phones,
            source=self.source,
            ok=resp.status_code == 200 and len(text) > 0,
        )


def _extract(html: str, base_url: str) -> tuple[str | None, str | None, str, list[str]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    meta = soup.find("meta", attrs={"name": "description"})
    meta_desc = (meta.get("content") or "").strip() if meta else None

    text = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
    links = [a.get("href") for a in soup.find_all("a", href=True)]
    return title, meta_desc, text, [l for l in links if l]
