"""Human-readable explanations of a risk result.

`plain_explanation` is deterministic and instant (stored on every score).
`ai_explanation` optionally asks the LLM for a friendlier narrative on demand.
Neither changes the decision — they only describe it.
"""
from __future__ import annotations

import json

from ..llm import clean_summary, openrouter_chat

# Engineer code -> plain English.
REASON_LABELS: dict[str, str] = {
    "REGISTRY_NOT_FOUND": "No matching company was found in the official registry",
    "COMPANY_INACTIVE": "The company is dissolved or inactive on the registry",
    "NUMBER_MISMATCH": "The submitted company number doesn't match the registry",
    "LOW_IDENTITY_CONFIDENCE": "The submitted details only weakly match the registry",
    "WEAK_WEB_FOOTPRINT": "The business has a weak or suspicious online presence",
    "WEAK_OWNERSHIP_DATA": "Limited information on directors/owners is available",
    "CLONED_SITE_MATCH": "The website closely matches another business (possible shell)",
    "SITE_UNREACHABLE": "The business website could not be reached",
    "PARKED_OR_PLACEHOLDER": "The website is a parked or placeholder page",
    "ML_ANOMALY": "The profile is unusual compared with other businesses",
}

_RATING_WORDS = {"low": "low risk", "medium": "medium risk", "high": "high risk"}
_DECISION_WORDS = {
    "approve": "can be auto-approved",
    "review": "should go to an analyst for manual review",
    "reject": "should be rejected",
}


def friendly_reasons(codes: list[str]) -> list[str]:
    return [REASON_LABELS.get(c, c.replace("_", " ").title()) for c in codes]


def plain_explanation(rating: str, decision: str, reason_codes: list[str]) -> str:
    lead = _RATING_WORDS.get(rating, "unrated")
    rec = _DECISION_WORDS.get(decision, "needs review")
    text = f"This business is {lead} and {rec}."
    reasons = friendly_reasons(reason_codes)
    if reasons:
        text += " Key factors: " + "; ".join(reasons) + "."
    else:
        text += " No concerns were flagged."
    return text


def ai_explanation(
    legal_name: str, rating: str, decision: str, overall_risk: int,
    reason_codes: list[str], category_scores: dict,
) -> str:
    """LLM narrative for a non-technical reader. Falls back to plain text."""
    fallback = plain_explanation(rating, decision, reason_codes)
    evidence = {
        "business": legal_name, "rating": rating, "decision": decision,
        "overall_risk": overall_risk,
        "factors": friendly_reasons(reason_codes),
        "category_risk": category_scores,
    }
    system = (
        "You are a KYB analyst writing for a non-technical reader. In 2-3 plain "
        "sentences, explain why this business received its risk rating and what "
        "the reviewer should do. Be factual; do NOT change the rating or decision, "
        "and do NOT invent facts beyond the given factors. Output ONLY the final "
        "explanation as plain prose — no preamble, no steps, no reasoning."
    )
    return clean_summary(openrouter_chat(system, json.dumps(evidence))) or fallback
