"""Combined risk engine (Feature 3).

Merges Feature 1 (identity) and Feature 2 (digital footprint) into one
explainable inherent-risk rating, modeled on bank/AML KYB risk scorecards:

  * category-weighted sub-scores (identity / footprint / ownership),
  * weights renormalized over whatever data is available,
  * hard-stop override rules that force High regardless of the weighted score,
  * risk bands -> recommended decision, with reason codes for auditability.

Deterministic by design — no ML/AI in the decision path.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Signals that force a High rating / reject outcome no matter the score.
# NOTE: REGISTRY_NOT_FOUND is deliberately NOT here — a missing registry match
# is "unconfirmed", not proof of fraud, so it routes to review (below). Genuine
# ghosts are still caught by the web hard-stops (unreachable / parked).
HARD_STOP_CODES = {
    "COMPANY_INACTIVE",
    "NUMBER_MISMATCH",
    "SITE_UNREACHABLE",
    "PARKED_OR_PLACEHOLDER",
}

# Signals that force manual review (not auto-reject). Clones need analyst
# disambiguation; a missing state / unavailable registry / no match all mean we
# could not CONFIRM the entity, so the case is reviewed against web presence
# rather than rejected — an outage or coverage gap must never be an adverse
# action against the customer.
REVIEW_TRIGGER_CODES = {
    "CLONED_SITE_MATCH",
    "REGISTRY_STATE_NOT_PROVIDED",
    "REGISTRY_UNAVAILABLE",
    "REGISTRY_NOT_FOUND",
}

# Category weights (renormalized over categories that have data).
_WEIGHTS = {"identity": 0.45, "footprint": 0.35, "ownership": 0.20}


@dataclass
class RiskResult:
    overall_risk: int                       # 0..100 (higher = riskier)
    rating: str                             # low | medium | high
    decision: str                           # approve | review | reject
    reason_codes: list[str] = field(default_factory=list)
    category_scores: dict[str, int] = field(default_factory=dict)


def compute_risk(
    identity_confidence: float | None,
    web_legitimacy: int | None,
    signal_codes: list[str],
    officers_count: int,
    psc_supported: bool,
    ownership_known: bool = True,
    web_presence_score: int | None = None,
) -> RiskResult:
    codes = set(signal_codes)
    categories: dict[str, int] = {}
    reasons: list[str] = []

    # --- Identity & registry (45%) -----------------------------------------
    # None = identity not checked (registry unavailable / no match). We skip the
    # category entirely so "unknown" never reads as "maximum identity risk".
    if identity_confidence is not None:
        identity_risk = round((1.0 - identity_confidence) * 100)
        categories["identity"] = identity_risk
        if identity_risk > 50:
            reasons.append("LOW_IDENTITY_CONFIDENCE")

    # --- Digital footprint (35%) -------------------------------------------
    # Prefer the LLM-judge-adjusted web-presence score when available; fall back
    # to the deterministic legitimacy score.
    legit = web_presence_score if web_presence_score is not None else web_legitimacy
    if legit is not None:
        footprint_risk = max(0, min(100, 100 - int(legit)))
        categories["footprint"] = footprint_risk
        if footprint_risk > 50:
            reasons.append("WEAK_WEB_FOOTPRINT")

    # --- Ownership & structure (20%) ---------------------------------------
    # Only scored when the registry was actually checked. If identity is
    # unconfirmed (unavailable / not found), 0 officers means "not fetched", not
    # "has none" — penalizing it would turn missing data into risk.
    if ownership_known:
        ownership_risk = 15
        if officers_count == 0:
            ownership_risk += 45
        if psc_supported and "NO_PSC" in codes:
            ownership_risk += 25
        if "NO_VERIFIED_UBO" in codes:
            ownership_risk += 5
        ownership_risk = min(100, ownership_risk)
        categories["ownership"] = ownership_risk
        if ownership_risk > 50:
            reasons.append("WEAK_OWNERSHIP_DATA")

    # --- Weighted overall (renormalized over available categories) ---------
    total_w = sum(_WEIGHTS[c] for c in categories)
    overall = (
        round(sum(_WEIGHTS[c] * s for c, s in categories.items()) / total_w)
        if total_w > 0
        else 100
    )

    # --- ML complementary signal (bump, not override) ----------------------
    if "ML_ANOMALY" in codes:
        overall = min(100, overall + 15)
        if "ML_ANOMALY" not in reasons:
            reasons.append("ML_ANOMALY")

    # --- Review triggers (force manual review, never auto-approve/reject) ---
    review = sorted(codes & REVIEW_TRIGGER_CODES)
    if review:
        overall = min(max(overall, 50), 65)   # clamp into the review band
        reasons = review + [r for r in reasons if r not in review]

    # --- Hard-stop overrides -----------------------------------------------
    hit = sorted(codes & HARD_STOP_CODES)
    if hit:
        overall = max(overall, 80)
        reasons = hit + [r for r in reasons if r not in hit]

    overall = max(0, min(100, overall))
    rating, decision = _band(overall)

    # High-severity signal codes always surface as reasons (capped list).
    for code in sorted(codes):
        if code in HARD_STOP_CODES and code not in reasons:
            reasons.append(code)

    return RiskResult(
        overall_risk=overall,
        rating=rating,
        decision=decision,
        reason_codes=reasons[:8],
        category_scores=categories,
    )


def _band(risk: int) -> tuple[str, str]:
    if risk <= 30:
        return "low", "approve"
    if risk <= 65:
        return "medium", "review"
    return "high", "reject"
