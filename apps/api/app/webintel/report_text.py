"""LLM narrative for the web-intelligence report (Feature 4).

Turns the structured enrichment evidence + the web-presence judgment into a
short, readable "what the web says" narrative for a reviewer. Explanatory only —
it restates gathered evidence and the judge's reasoning; it makes no decision.

Requested as JSON ({"report": "..."}) and sanitized so the model can't leak its
chain-of-thought or prompt steps. Returns None if no LLM key or nothing to say.
"""
from __future__ import annotations

import json

from ..config import settings
from ..llm import clean_summary, openrouter_chat

_SYSTEM = (
    "You are a  Sr. KYB analyst writing the 'digital presence' section of a review. "
    "From the structured evidence and the web-presence judgment, write a concise "
    "briefing (4-6 sentences) covering what the company does, where it is based, "
    "its size/team, any funding or notable news, and how coherent its online "
    "presence looks. Use ONLY the given data; if something is missing, omit it — "
    "do not speculate or invent figures. End with one sentence noting the "
    "legal/registry verification is still pending and this is web evidence only. "
    "Output ONLY the final briefing as plain prose — no preamble, no bullet "
    "lists, and do NOT show any analysis, steps, drafts, or your reasoning."
)


def generate_intel_report(legal_name: str, enrichment: dict, judgment: dict) -> str | None:
    if not (enrichment or judgment):
        return None
    payload = {
        "legal_name": legal_name,
        "evidence": enrichment,
        "web_presence_judgment": judgment,
    }
    return clean_summary(
        openrouter_chat(_SYSTEM, json.dumps(payload, default=str), max_tokens=600,
                        model=settings.judge_model)
    )
