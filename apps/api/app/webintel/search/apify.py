"""Apify SERP search provider (optional, reuses APIFY_API_TOKEN).

Runs a Google-search actor and reads organic rows from the run dataset. Returns
[] on any failure so the factory can fall back to DDG.
"""
from __future__ import annotations

from ...config import settings
from .base import SearchHit, SearchProvider


class ApifySearch(SearchProvider):
    source = "apify"

    def __init__(self) -> None:
        self._token = settings.apify_api_token
        self._actor = getattr(
            settings, "apify_serp_actor", "apify/google-search-scraper"
        )
        self._client = None
        if self._token:
            try:
                from apify_client import ApifyClient

                self._client = ApifyClient(self._token)
            except Exception:  # noqa: BLE001
                self._client = None

    def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        if not (query and self._client):
            return []
        try:
            run = self._client.actor(self._actor).call(run_input={
                "queries": query,
                "maxPagesPerQuery": 1,
                "resultsPerPage": max_results,
            })
            ds_id = run.get("defaultDatasetId") if isinstance(run, dict) \
                else getattr(run, "default_dataset_id", None)
            items = list(self._client.dataset(ds_id).iterate_items())
        except Exception:  # noqa: BLE001
            return []

        hits: list[SearchHit] = []
        for page in items:
            for r in (page.get("organicResults") or []):
                url = r.get("url")
                if not url:
                    continue
                hits.append(SearchHit(
                    url=url, title=r.get("title"),
                    snippet=r.get("description"), source=self.source,
                ))
                if len(hits) >= max_results:
                    return hits
        return hits
