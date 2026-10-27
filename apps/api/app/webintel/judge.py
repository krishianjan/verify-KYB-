"""LLM-as-judge for web presence (Feature 4).

Given the structured enrichment evidence, the model rates how strongly the open
web supports that this is a real, operating business — a 0..100 score with a
confidence level and short reason codes.

GUARDRAIL: this is a COMPLEMENTARY signal, never the decision. Its score can only
nudge the deterministic footprint score within ±judge_max_adjust, and a case
resting on web presence alone is capped at provisional review upstream (the
risk engine's review-trigger clamp). The LLM never approves/rejects.
"""
from __future__ import annotations

import json

from pydantic import BaseModel

from ..config import settings
from ..llm import openrouter_json

_VALID_CONF = {"low", "medium", "high"}


class WebJudgment(BaseModel):
    presence_score: int          # 0..100 (higher = stronger real-business presence)
    confidence: str              # low | medium | high
    reason_codes: list[str] = []
    rationale: str | None = None
    llm_used: bool = False


_SYSTEM = (
    "You are a KYB analyst judging a company's WEB PRESENCE only (not making an "
    "approve/reject decision). From the structured evidence, rate 0-100 how "
    "strongly the open web supports that this is a real, operating business: "
    "consistent identity across sources, substantive description, locations, "
    "team, credible news/funding, and matching socials raise it; thin, "
    "contradictory, or absent evidence lowers it. Base it ONLY on the evidence. "
    "Return JSON: {presence_score:int 0-100, confidence:'low'|'medium'|'high', "
    "reason_codes:[SHORT_UPPERCASE_CODES], rationale:'<=2 sentences'}."
)


def judge_web_presence(evidence: dict) -> WebJudgment:
    parsed = openrouter_json(_SYSTEM, json.dumps(evidence, default=str),
                             max_tokens=500, model=settings.judge_model)
    if not parsed or "presence_score" not in parsed:
        return WebJudgment(presence_score=0, confidence="low", llm_used=False)
    try:
        score = int(round(float(parsed["presence_score"])))
    except Exception:  # noqa: BLE001
        return WebJudgment(presence_score=0, confidence="low", llm_used=False)
    conf = str(parsed.get("confidence", "low")).lower()
    if conf not in _VALID_CONF:
        conf = "low"
    codes = parsed.get("reason_codes")
    codes = [str(c) for c in codes][:8] if isinstance(codes, list) else []
    return WebJudgment(
        presence_score=max(0, min(100, score)),
        confidence=conf,
        reason_codes=codes,
        rationale=parsed.get("rationale"),
        llm_used=True,
    )


def blend_presence(deterministic: int, judgment: WebJudgment) -> int:
    """Move the deterministic footprint score toward the judge's score, but no
    more than ±judge_max_adjust. If the LLM wasn't used, keep deterministic."""
    if not judgment.llm_used:
        return deterministic
    cap = settings.judge_max_adjust
    delta = judgment.presence_score - deterministic
    delta = max(-cap, min(cap, delta))
    return max(0, min(100, deterministic + delta))
