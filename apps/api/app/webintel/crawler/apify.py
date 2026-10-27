"""Apify fallback crawler (uses the existing APIFY_API_TOKEN).

Used only when the free StaticCrawler fails or returns thin content — Apify is
paid per run. Uses the `apify/website-content-crawler` actor. The output field
mapping is defensive; verify once against a live run before relying on it (same
discipline as the us_sos adapter).
"""
from __future__ import annotations

from ...config import settings
from ..dto import CrawlResult
from .base import WebCrawler


class ApifyCrawler(WebCrawler):
    source = "apify"

    def __init__(self) -> None:
        if not settings.apify_api_token:
            raise RuntimeError("APIFY_API_TOKEN is not set.")
        from apify_client import ApifyClient

        self._client = ApifyClient(settings.apify_api_token)
        self._actor = settings.apify_crawler_actor

    def fetch(self, url: str) -> CrawlResult:
        target = url if url.startswith(("http://", "https://")) else f"https://{url}"
        run_input = {
            "startUrls": [{"url": target}],
            "maxCrawlPages": 1,
            "crawlerType": "cheerio",
        }
        try:
            run = self._client.actor(self._actor).call(run_input=run_input)
            status = run.get("status") if isinstance(run, dict) else getattr(run, "status", None)
            if run is None or status != "SUCCEEDED":
                return CrawlResult(url=url, source=self.source, ok=False,
                                   error=f"run status {status}")
            ds_id = (run.get("defaultDatasetId") if isinstance(run, dict)
                     else getattr(run, "default_dataset_id", None))
            items = list(self._client.dataset(ds_id).iterate_items())
        except Exception as exc:  # noqa: BLE001
            return CrawlResult(url=url, source=self.source, ok=False, error=str(exc))

        if not items:
            return CrawlResult(url=url, source=self.source, ok=False, error="no items")

        it = items[0]
        meta = it.get("metadata") or {}
        text = it.get("text") or it.get("markdown") or ""
        return CrawlResult(
            url=url,
            final_url=it.get("url") or target,
            status_code=200,
            title=meta.get("title") or it.get("title"),
            meta_description=meta.get("description"),
            text=text,
            html_len=len(it.get("html") or ""),
            links=it.get("links") or [],
            source=self.source,
            ok=bool(text),
            raw=it,
        )
