"""Gather Feature 1 + Feature 2 evidence and compute/store a combined RiskScore."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    AuditEvent,
    Business,
    Director,
    IdentityAssessment,
    RiskScore,
    RiskSignal,
    WebIntel,
)
from ..vectorstore import add_memory
from .engine import compute_risk
from .explain import plain_explanation
from .ml import anomaly_check, supervised_reject_probability


def compute_and_store_risk(db: Session, business: Business) -> RiskScore:
    _refresh_ml_signals(db, business)
    assessment = db.scalars(
        select(IdentityAssessment)
        .where(IdentityAssessment.business_id == business.id)
        .order_by(IdentityAssessment.created_at.desc())
    ).first()
    identity_confidence = assessment.confidence if assessment else None

    intel = db.scalars(
        select(WebIntel)
        .where(WebIntel.business_id == business.id)
        .order_by(WebIntel.created_at.desc())
    ).first()
    web_legitimacy = intel.legitimacy_score if intel else None
    web_presence_score = intel.web_presence_score if intel else None

    officers_count = db.scalar(
        select(func.count()).select_from(Director).where(
            Director.business_id == business.id
        )
    ) or 0

    codes = list(
        db.scalars(
            select(RiskSignal.code).where(RiskSignal.business_id == business.id)
        )
    )

    psc_supported = not (business.jurisdiction or "").lower().startswith("us")

    # Ownership is only knowable when the registry was actually checked. A None
    # identity confidence means not-checked/unconfirmed, so 0 officers is "not
    # fetched", not "has none".
    ownership_known = identity_confidence is not None

    result = compute_risk(
        identity_confidence=identity_confidence,
        web_legitimacy=web_legitimacy,
        signal_codes=codes,
        officers_count=officers_count,
        psc_supported=psc_supported,
        ownership_known=ownership_known,
        web_presence_score=web_presence_score,
    )

    score = RiskScore(
        business_id=business.id,
        overall_risk=result.overall_risk,
        rating=result.rating,
        decision=result.decision,
        reason_codes=result.reason_codes,
        category_scores=result.category_scores,
        explanation=plain_explanation(
            result.rating, result.decision, result.reason_codes
        ),
    )
    db.add(score)

    # Keep the case status in sync with the COMBINED decision (not just identity),
    # so the workflow state never contradicts the recommendation.
    business.status = {
        "approve": "auto_approved",
        "review": "manual_review",
        "reject": "rejected",
    }.get(result.decision, "manual_review")

    db.add(AuditEvent(
        business_id=business.id, event_type="risk.computed", actor="system",
        detail={"overall_risk": result.overall_risk, "rating": result.rating,
                "decision": result.decision, "reasons": result.reason_codes},
    ))
    db.flush()

    add_memory(
        business.id,
        f"Risk rating {result.rating}; recommended {result.decision}. "
        f"Reasons: {', '.join(result.reason_codes) or 'none'}.",
    )
    return score


def _refresh_ml_signals(db: Session, business: Business) -> None:
    """Recompute ML signals (idempotent): clear prior ml-source signals, re-add."""
    for s in db.scalars(
        select(RiskSignal).where(
            RiskSignal.business_id == business.id, RiskSignal.source == "ml"
        )
    ).all():
        db.delete(s)
    db.flush()

    # Skip anomaly detection when identity is unconfirmed: the feature vector is
    # structurally incomplete (no registry fields), so IsolationForest would
    # flag it as an outlier purely because of missing data, not actual risk.
    assessment = db.scalars(
        select(IdentityAssessment)
        .where(IdentityAssessment.business_id == business.id)
        .order_by(IdentityAssessment.created_at.desc())
    ).first()
    if assessment is not None and assessment.confidence is None:
        return

    is_anom, score = anomaly_check(db, business)
    if is_anom:
        db.add(RiskSignal(
            business_id=business.id, code="ML_ANOMALY", severity="medium",
            weight=0.5, source="ml",
            detail=f"Statistical outlier vs business population (IsolationForest "
                   f"score {score:.3f}).",
        ))

    prob = supervised_reject_probability(db, business)
    if prob is not None and prob >= 0.7:
        db.add(RiskSignal(
            business_id=business.id, code="ML_SUPERVISED_HIGH", severity="info",
            weight=0.0, source="ml",
            detail=f"Supervised model (analyst-label trained) P(reject)={prob:.2f}.",
        ))
    db.flush()
