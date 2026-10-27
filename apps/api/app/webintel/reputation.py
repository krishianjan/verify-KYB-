"""urlscan.io reputation enrichment (optional — only runs if a key is set).

Uses the fast, synchronous Search API (existing scans) rather than submitting a
new scan (which is async). Returns whether the domain has public scan history
and the latest screenshot/result links for the analyst UI. Degrades gracefully.
"""
from __future__ import annotations

import httpx
from pydantic import BaseModel

from ..config import settings


class ReputationInfo(BaseModel):
    checked: bool = False
    total: int = 0
    screenshot: str | None = None
    result_url: str | None = None
    error: str | None = None


def get_reputation(domain: str | None) -> ReputationInfo:
    if not settings.urlscan_api_key or not domain:
        return ReputationInfo(checked=False)
    try:
        resp = httpx.get(
            f"{settings.urlscan_base_url}/search/",
            params={"q": f"domain:{domain}", "size": 1},
            headers={"API-Key": settings.urlscan_api_key},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        info = ReputationInfo(checked=True, total=int(data.get("total", len(results))))
        if results:
            info.screenshot = results[0].get("screenshot")
            info.result_url = results[0].get("result")
        return info
    except Exception as exc:  # noqa: BLE001
        return ReputationInfo(checked=True, error=str(exc))
