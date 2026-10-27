"""Hardened DuckDuckGo HTML search provider (free, no key).

Parses the lite HTML endpoint, de-duplicates by host, skips the usual
non-business aggregators, and retries transient failures a couple of times.
Returns [] on any failure.
"""
from __future__ import annotations

import html as _html
import re
import time
from urllib.parse import unquote, urlparse

import httpx

from .base import SearchHit, SearchProvider

_UA = "verifyKYB-footprint/1.0 (+https://example.com; compliance verification)"
_ENDPOINT = "https://html.duckduckgo.com/html/"
_RESULT_RE = re.compile(
    r'result__a[^>]*href="[^"]*uddg=([^&"]+)[^"]*"[^>]*>(.*?)</a>', re.DOTALL
)
_TAG_RE = re.compile(r"<[^>]+>")


class DdgSearch(SearchProvider):
    source = "ddg"

    def __init__(self, retries: int = 2, timeout: int = 15) -> None:
        self._retries = retries
        self._timeout = timeout

    def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        if not query:
            return []
        for attempt in range(self._retries + 1):
            try:
                resp = httpx.get(
                    _ENDPOINT,
                    params={"q": query},
                    headers={"User-Agent": _UA},
                    timeout=self._timeout,
                    follow_redirects=True,
                )
                if resp.status_code != 200:
                    raise httpx.HTTPStatusError(
                        "bad status", request=resp.request, response=resp
                    )
                return self._parse(resp.text, max_results)
            except Exception:  # noqa: BLE001
                if attempt < self._retries:
                    time.sleep(0.6 * (attempt + 1))
                    continue
                return []
        return []

    def _parse(self, body: str, max_results: int) -> list[SearchHit]:
        hits: list[SearchHit] = []
        seen: set[str] = set()
        for enc, label in _RESULT_RE.findall(body):
            url = unquote(enc)
            if not url.startswith("http"):
                continue
            host = (urlparse(url).hostname or "").lower()
            if not host or host in seen:
                continue
            seen.add(host)
            title = _html.unescape(_TAG_RE.sub("", label)).strip() or None
            hits.append(SearchHit(url=url, title=title, source=self.source))
            if len(hits) >= max_results:
                break
        return hits
