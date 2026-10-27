from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import cases
from .config import settings
from .db import get_db
from .models import (
    AuditEvent,
    Business,
    CaseStatus,
    IdentityAssessment,
    ReviewAction,
    RiskScore,
    RiskSignal,
    WebIntel,
)
from .risk import compute_and_store_risk
from .schemas import (
    ActionIn,
    ActionOut,
    CaseCreate,
    CaseListItem,
    CaseListOut,
    CaseOut,
    FootprintOut,
    ReportOut,
    RiskOut,
)
from .vectorstore import recall_memory
from .webintel import get_crawler, get_summarizer, run_footprint_pipeline

router = APIRouter()

_ACTION_STATUS = {
    "approve": CaseStatus.APPROVED,
    "reject": CaseStatus.REJECTED,
    "request_docs": CaseStatus.MANUAL_REVIEW,
    "escalate": CaseStatus.MANUAL_REVIEW,
}


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "registry_provider": settings.registry_provider,
    }


@router.post("/kyb/cases", response_model=CaseOut, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)) -> CaseOut:
    business = cases.create_case(db, payload)
    out = cases.get_case_out(db, business.id)
    if out is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Case created but not retrievable")
    return out


@router.get("/kyb/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db)) -> CaseOut:
    out = cases.get_case_out(db, case_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return out


@router.get("/kyb/cases/{case_id}/report", response_model=ReportOut)
def get_report(case_id: str, db: Session = Depends(get_db)) -> ReportOut:
    business = db.get(Business, case_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Case not found")
    from .report import build_report

    return build_report(db, business)


@router.post("/kyb/cases/{case_id}/footprint", response_model=FootprintOut)
def run_footprint(case_id: str, db: Session = Depends(get_db)) -> FootprintOut:
    business = db.get(Business, case_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Case not found")
    intel = run_footprint_pipeline(db, business, get_crawler(), get_summarizer())
    # Footprint evidence changed -> recompute the combined risk score.
    compute_and_store_risk(db, business)
    db.commit()
    return _footprint_out(db, intel)


@router.post("/kyb/cases/{case_id}/enrich", response_model=FootprintOut)
def run_enrich(case_id: str, db: Session = Depends(get_db)) -> FootprintOut:
    """On-demand web-intelligence enrichment: scrape the open web, parse + judge
    presence, and recompute risk. Same engine as /footprint, named for the
    analyst-driven 'check the web' action."""
    business = db.get(Business, case_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Case not found")
    intel = run_footprint_pipeline(db, business, get_crawler(), get_summarizer())
    compute_and_store_risk(db, business)
    db.commit()
    return _footprint_out(db, intel)


@router.get("/kyb/cases", response_model=CaseListOut)
def list_cases(
    status: str | None = None,
    rating: str | None = None,
    decision: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> CaseListOut:
    stmt = select(Business).order_by(Business.created_at.desc())
    if status:
        stmt = stmt.where(Business.status == status)
    items: list[CaseListItem] = []
    for b in db.scalars(stmt.limit(500)).all():
        assessment = db.scalars(
            select(IdentityAssessment)
            .where(IdentityAssessment.business_id == b.id)
            .order_by(IdentityAssessment.created_at.desc())
        ).first()
        risk = db.scalars(
            select(RiskScore)
            .where(RiskScore.business_id == b.id)
            .order_by(RiskScore.created_at.desc())
        ).first()
        if rating and (risk is None or risk.rating != rating):
            continue
        if decision and (risk is None or risk.decision != decision):
            continue
        items.append(CaseListItem(
            id=b.id, legal_name=b.legal_name, jurisdiction=b.jurisdiction,
            status=b.status,
            identity_decision=assessment.decision if assessment else None,
            identity_confidence=assessment.confidence if assessment else None,
            risk_rating=risk.rating if risk else None,
            overall_risk=risk.overall_risk if risk else None,
            created_at=b.created_at.isoformat(),
        ))
        if len(items) >= limit:
            break
    return CaseListOut(total=len(items), items=items)


@router.post("/kyb/cases/{case_id}/actions", response_model=ActionOut)
def analyst_action(
    case_id: str, payload: ActionIn, db: Session = Depends(get_db)
) -> ActionOut:
    business = db.get(Business, case_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Case not found")
    action = payload.action.lower()
    if action not in _ACTION_STATUS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Use one of: {', '.join(_ACTION_STATUS)}",
        )
    db.add(ReviewAction(
        business_id=business.id, action=action, notes=payload.notes,
        actor=payload.actor,
    ))
    business.status = _ACTION_STATUS[action]
    db.add(AuditEvent(
        business_id=business.id, event_type="review.action", actor=payload.actor,
        detail={"action": action, "notes": payload.notes},
    ))
    db.commit()
    return ActionOut(
        business_id=business.id, action=action, notes=payload.notes,
        actor=payload.actor, status=business.status,
    )


@router.post("/kyb/cases/{case_id}/risk", response_model=RiskOut)
def recompute_risk(case_id: str, db: Session = Depends(get_db)) -> RiskOut:
    business = db.get(Business, case_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Case not found")
    score = compute_and_store_risk(db, business)
    db.commit()
    return RiskOut(
        overall_risk=score.overall_risk, rating=score.rating,
        decision=score.decision, explanation=score.explanation,
        reason_codes=score.reason_codes or [],
        category_scores=score.category_scores or {},
    )


@router.get("/kyb/cases/{case_id}/memory")
def case_memory(case_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Business, case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"business_id": case_id, "notes": recall_memory(case_id)}


@router.post("/kyb/cases/{case_id}/explain")
def explain_case(case_id: str, db: Session = Depends(get_db)) -> dict:
    business = db.get(Business, case_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Case not found")
    risk = db.scalars(
        select(RiskScore).where(RiskScore.business_id == case_id)
        .order_by(RiskScore.created_at.desc())
    ).first()
    if risk is None:
        raise HTTPException(status_code=404, detail="No risk score to explain")
    from .risk.explain import ai_explanation

    text = ai_explanation(
        business.legal_name, risk.rating, risk.decision, risk.overall_risk,
        risk.reason_codes or [], risk.category_scores or {},
    )
    return {"business_id": case_id, "explanation": text}


@router.get("/kyb/cases/{case_id}/footprint", response_model=FootprintOut)
def get_footprint(case_id: str, db: Session = Depends(get_db)) -> FootprintOut:
    intel = db.scalars(
        select(WebIntel)
        .where(WebIntel.business_id == case_id)
        .order_by(WebIntel.created_at.desc())
    ).first()
    if intel is None:
        raise HTTPException(status_code=404, detail="No footprint for this case")
    return _footprint_out(db, intel)


def _footprint_out(db: Session, intel: WebIntel) -> FootprintOut:
    signals = db.scalars(
        select(RiskSignal).where(
            RiskSignal.business_id == intel.business_id,
            RiskSignal.source == "web_intel",
        )
    ).all()
    return FootprintOut(
        business_id=intel.business_id,
        website_url=intel.website_url,
        final_url=intel.final_url,
        http_status=intel.http_status,
        domain=intel.domain,
        domain_age_days=intel.domain_age_days,
        registrar=intel.registrar,
        has_mx=intel.has_mx,
        has_tls=intel.has_tls,
        title=intel.title,
        legitimacy_score=intel.legitimacy_score,
        web_presence_score=intel.web_presence_score,
        verdict=intel.verdict,
        summary=intel.summary,
        profile_summary=intel.profile_summary,
        social_links=intel.socials or {},
        crawler_source=intel.crawler_source,
        screenshot_url=intel.screenshot_url,
        enrichment=intel.enrichment or {},
        judge_confidence=intel.judge_confidence,
        judge_rationale=intel.judge_rationale,
        signals=list(signals),
    )
