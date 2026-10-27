"""OpenRouter-backed summarizer (OpenAI-compatible chat API).

The LLM is given the deterministic evidence + signals and asked only to explain
the verdict in plain English. It never changes the score or decision. Falls
back to the template summary on any error so the pipeline never breaks.
"""
from __future__ import annotations

import json

from ...config import settings
from ...llm import clean_summary, openrouter_chat
from ..dto import CrawlResult, DomainInfo, FootprintResult
from .base import Summarizer
from .template import TemplateSummarizer

_SYSTEM = (
    "You are a KYB analyst assistant. You are given deterministic evidence and "
    "risk signals about a business's website and domain. Explain, in 2-4 "
    "sentences, why the footprint received its verdict and score. Be factual and "
    "reference the signals. Do NOT invent facts or change the verdict/score. "
    "Output ONLY the final explanation as plain prose — no preamble, and do NOT "
    "show any analysis, steps, drafts, or your reasoning."
)


class OpenRouterSummarizer(Summarizer):
    def __init__(self) -> None:
        self._fallback = TemplateSummarizer()
        self._key = settings.openrouter_api_key

    def summarize(self, company_name, crawl, domain, footprint) -> str:
        if not self._key:
            return self._fallback.summarize(company_name, crawl, domain, footprint)

        evidence = {
            "company_name": company_name,
            "verdict": footprint.verdict,
            "legitimacy_score": footprint.legitimacy_score,
            "domain": {
                "age_days": domain.age_days, "registrar": domain.registrar,
                "has_mx": domain.has_mx, "has_tls": domain.has_tls,
            },
            "site": {
                "ok": crawl.ok, "title": crawl.title,
                "text_len": len(crawl.text),
                "emails": crawl.emails[:3], "phones": crawl.phones[:3],
            },
            "signals": [{"code": s.code, "severity": s.severity, "detail": s.detail}
                        for s in footprint.signals],
        }
        text = clean_summary(openrouter_chat(_SYSTEM, json.dumps(evidence), max_tokens=600))
        return text or self._fallback.summarize(company_name, crawl, domain, footprint)
