"""LLM company profile from web presence — a reviewable summary for analysts.

Produces plain text covering what the company does, HQ/location, employee size,
and industry, grounded ONLY in the crawled site + discovered socials.

The profile is requested as JSON ({"profile": "..."}) and the text is sanitized,
so weaker/"reasoning" models can't leak their chain-of-thought, step lists, or
prompt scaffolding into the output — the reviewer sees only the final summary.
Returns None if no LLM key or nothing to summarize (caller falls back).
"""
from __future__ import annotations

import json

from ..llm import clean_summary, openrouter_chat

_SYSTEM = (
    "You are a KYB analyst. From the provided website text and social links, "
    "write a short company profile for a reviewer: what the business does, its "
    "HQ/location, approximate employee size, and industry. Use ONLY the given "
    "evidence; if a detail isn't present, say 'not found'. Output ONLY the final "
    "3-5 sentence profile as plain prose — no preamble, no bullet lists, and do "
    "NOT show any analysis, steps, drafts, or your reasoning."
)


def company_profile(legal_name: str, site_text: str, title: str | None,
                    socials: dict[str, str]) -> str | None:
    if not (site_text or socials):
        return None
    evidence = {
        "legal_name": legal_name,
        "website_title": title,
        "website_text": (site_text or "")[:3500],
        "social_profiles": socials,
    }
    return clean_summary(openrouter_chat(_SYSTEM, json.dumps(evidence), max_tokens=700))
