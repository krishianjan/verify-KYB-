"""Deterministic, no-LLM summarizer. Always available (no key needed)."""
from __future__ import annotations

from ..dto import CrawlResult, DomainInfo, FootprintResult
from .base import Summarizer

_VERDICT_LEAD = {
    "real": "The online footprint looks consistent with a real, operating business.",
    "thin": "The business appears real but has a thin online footprint.",
    "inconsistent": "The online footprint is inconsistent with the registered business.",
    "ghost": "Strong 'ghost business' indicators — the online presence looks fake or absent.",
    "unknown": "The online footprint could not be assessed.",
}


class TemplateSummarizer(Summarizer):
    def summarize(self, company_name, crawl, domain, footprint) -> str:
        lead = _VERDICT_LEAD.get(footprint.verdict, _VERDICT_LEAD["unknown"])
        parts = [f"{lead} Web legitimacy score {footprint.legitimacy_score}/100."]
        if domain.age_days is not None:
            parts.append(f"Domain age ~{domain.age_days} days.")
        reasons = [f"{s.code} ({s.severity})" for s in footprint.signals
                   if s.severity in ("high", "medium")]
        if reasons:
            parts.append("Key signals: " + ", ".join(reasons) + ".")
        return " ".join(parts)
