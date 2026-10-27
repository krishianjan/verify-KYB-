"""Case service: create a case, run the identity pipeline, assemble responses."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    AuditEvent,
    BeneficialOwner,
    Business,
    Director,
    IdentityAssessment,
    RiskScore,
    RiskSignal,
)
from .pipelines import run_identity_pipeline
from .registry import get_registry_adapter
from .schemas import (
    AssessmentOut,
    BusinessOut,
    CaseCreate,
    CaseOut,
    RiskOut,
)


def _compose_jurisdiction(jurisdiction: str | None, state: str | None) -> str:
    """Carry the US state inside the jurisdiction string, e.g. 'us-ca'.

    Keeps the frozen RegistryAdapter.search(query, jurisdiction) interface intact
    while letting the us_sos adapter narrow by state. Non-US jurisdictions (e.g.
    'gb') are returned unchanged.
    """
    base = (jurisdiction or "us").strip().lower().split("-")[0]
    if state:
        return f"{base}-{state.strip().lower()}"
    return base


def create_case(db: Session, payload: CaseCreate) -> Business:
    business = Business(
        legal_name=payload.legal_name,
        company_number=payload.company_number,
        company_type=payload.company_type,
        jurisdiction=_compose_jurisdiction(payload.jurisdiction, payload.state),
        website=payload.website,
        registered_address=payload.registered_address,
        incorporation_date=payload.incorporation_date,
        submitted_payload=payload.model_dump(),
    )
    db.add(business)
    db.flush()

    db.add(
        AuditEvent(
            business_id=business.id,
            event_type="case.received",
            actor="system",
            detail={"legal_name": business.legal_name},
        )
    )
    db.flush()

    adapter = get_registry_adapter()
    run_identity_pipeline(db, business, adapter)

    from .risk import compute_and_store_risk

    compute_and_store_risk(db, business)
    db.commit()  # persist identity + risk before any (best-effort) fallback

    # Registry couldn't confirm the entity (unavailable/limit or no match):
    # fall back to the web-intelligence agent so the case gets a real score on
    # web evidence instead of a verdict built on missing data. Best-effort —
    # a failure here rolls back only the fallback, never the committed identity.
    if _needs_web_fallback(db, business):
        try:
            from .webintel import get_crawler, get_summarizer, run_footprint_pipeline

            run_footprint_pipeline(db, business, get_crawler(), get_summarizer())
            compute_and_store_risk(db, business)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()

    db.refresh(business)
    return business


# Identity signals that mean "registry did not confirm the entity" and should
# trigger the web-intelligence fallback.
_WEB_FALLBACK_CODES = {"REGISTRY_UNAVAILABLE", "REGISTRY_NOT_FOUND",
                       "REGISTRY_STATE_NOT_PROVIDED"}


def _needs_web_fallback(db: Session, business: Business) -> bool:
    from .config import settings

    if not settings.enable_enrichment:
        return False
    codes = set(db.scalars(
        select(RiskSignal.code).where(RiskSignal.business_id == business.id)
    ))
    return bool(codes & _WEB_FALLBACK_CODES)


def get_case_out(db: Session, business_id: str) -> CaseOut | None:
    business = db.get(Business, business_id)
    if business is None:
        return None

    assessment = db.scalars(
        select(IdentityAssessment)
        .where(IdentityAssessment.business_id == business_id)
        .order_by(IdentityAssessment.created_at.desc())
    ).first()

    directors = db.scalars(
        select(Director).where(Director.business_id == business_id)
    ).all()
    owners = db.scalars(
        select(BeneficialOwner).where(BeneficialOwner.business_id == business_id)
    ).all()
    signals = db.scalars(
        select(RiskSignal).where(RiskSignal.business_id == business_id)
    ).all()

    assessment_out = None
    if assessment is not None:
        assessment_out = AssessmentOut(
            confidence=assessment.confidence,
            decision=assessment.decision,
            matched_company_number=assessment.matched_company_number,
            summary=assessment.summary,
            mismatches=assessment.mismatches,
        )

    risk = db.scalars(
        select(RiskScore)
        .where(RiskScore.business_id == business_id)
        .order_by(RiskScore.created_at.desc())
    ).first()
    risk_out = (
        RiskOut(
            overall_risk=risk.overall_risk,
            rating=risk.rating,
            decision=risk.decision,
            explanation=risk.explanation,
            reason_codes=risk.reason_codes or [],
            category_scores=risk.category_scores or {},
        )
        if risk is not None
        else None
    )

    return CaseOut(
        business=BusinessOut.model_validate(business),
        assessment=assessment_out,
        risk=risk_out,
        directors=list(directors),
        beneficial_owners=list(owners),
        risk_signals=list(signals),
    )
