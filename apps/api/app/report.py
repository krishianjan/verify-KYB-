"""Builds the customer-facing, Baselayer-shaped verification report.

Presentation layer over our stored data: two letter-graded scores (KYB + Risk),
categorical fuzzy-match fields (entity resolution), a structured decision, and a
source-of-truth map. Pure read — computes nothing new that isn't already stored.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .matching.normalize import address_similarity, company_name_similarity
from .models import (
    BeneficialOwner,
    Business,
    Director,
    IdentityAssessment,
    RegistryRecord,
    RiskScore,
    WebIntel,
)
from .schemas import (
    BusinessBlock,
    DecisionOut,
    EnrichmentBlock,
    FootprintBlock,
    FundingItem,
    NewsItem,
    RegistrationOut,
    ReportOut,
    ScoreOut,
)

_ACTION = {"approve": "auto_approve", "review": "manual_review", "reject": "reject"}


def _letter(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _match_category(sim: float | None) -> str:
    if sim is None:
        return "NONE"
    if sim >= 0.97:
        return "EXACT"
    if sim >= 0.80:
        return "SIMILAR"
    if sim >= 0.50:
        return "PARTIAL"
    return "NONE"


def _months_in_business(incorporation_date: str | None) -> int | None:
    if not incorporation_date:
        return None
    try:
        y, m, d = (int(x) for x in incorporation_date[:10].split("-"))
        today = date.today()
        return max(0, (today.year - y) * 12 + (today.month - m))
    except Exception:  # noqa: BLE001
        return None


def _state_from_jurisdiction(jurisdiction: str | None) -> str | None:
    if not jurisdiction:
        return None
    parts = jurisdiction.split("-", 1)
    return parts[1].upper() if len(parts) == 2 else None


_WARNING_FOR_CODE = {
    "REGISTRY_UNAVAILABLE": "Official registry temporarily unavailable — this "
    "verdict rests on web presence only; re-run the registry check to confirm.",
    "REGISTRY_NOT_FOUND": "No match in the searched registry — entity is "
    "unconfirmed (may be in uncovered jurisdiction or filed under another name). "
    "Provisional, web-evidence only.",
    "REGISTRY_STATE_NOT_PROVIDED": "No state/company number provided — registry "
    "was not searched; assessed on web presence.",
}


def _warnings(db: Session, business_id: str, identity_pending: bool) -> list[str]:
    from .models import RiskSignal

    codes = set(db.scalars(
        select(RiskSignal.code).where(RiskSignal.business_id == business_id)
    ))
    warnings = [msg for code, msg in _WARNING_FOR_CODE.items() if code in codes]
    if identity_pending and not warnings:
        warnings.append("Identity not confirmed against an official registry; "
                        "assessed on web presence only.")
    return warnings


def _enrichment_block(intel) -> EnrichmentBlock | None:
    if intel is None:
        return None
    data = intel.enrichment or {}
    if not data and intel.web_presence_score is None:
        return None
    funding = [FundingItem(**f) for f in data.get("funding", [])
               if isinstance(f, dict)]
    news = [NewsItem(**n) for n in data.get("recent_news", [])
            if isinstance(n, dict)]
    return EnrichmentBlock(
        description=data.get("description"),
        industry=data.get("industry"),
        hq=data.get("hq"),
        locations=data.get("locations", []) or [],
        employee_range=data.get("employee_range"),
        founded_year=data.get("founded_year"),
        founders=data.get("founders", []) or [],
        executives=data.get("executives", []) or [],
        socials=data.get("socials", {}) or {},
        funding=funding,
        recent_news=news,
        sources=data.get("sources", []) or [],
        presence_score=intel.web_presence_score,
        judge_confidence=intel.judge_confidence,
        judge_rationale=intel.judge_rationale,
        narrative=(intel.summary if "Web intelligence:" in (intel.summary or "")
                   else None),
    )


def _social_profiles(db: Session, business_id: str) -> list[str]:
    from .models import RiskSignal

    sig = db.scalars(
        select(RiskSignal).where(
            RiskSignal.business_id == business_id,
            RiskSignal.code == "SOCIAL_PRESENCE",
        )
    ).first()
    if not sig or not sig.detail or ":" not in sig.detail:
        return []
    tail = sig.detail.split(":", 1)[1].strip().rstrip(".")
    return [p.strip() for p in tail.split(",") if p.strip()]


def build_report(db: Session, business: Business) -> ReportOut:
    assessment = db.scalars(
        select(IdentityAssessment).where(IdentityAssessment.business_id == business.id)
        .order_by(IdentityAssessment.created_at.desc())
    ).first()
    reg = db.scalars(
        select(RegistryRecord).where(RegistryRecord.business_id == business.id)
        .order_by(RegistryRecord.fetched_at.desc())
    ).first()
    intel = db.scalars(
        select(WebIntel).where(WebIntel.business_id == business.id)
        .order_by(WebIntel.created_at.desc())
    ).first()
    risk = db.scalars(
        select(RiskScore).where(RiskScore.business_id == business.id)
        .order_by(RiskScore.created_at.desc())
    ).first()
    officers = db.scalars(
        select(Director).where(Director.business_id == business.id)
    ).all()
    ubos = db.scalars(
        select(BeneficialOwner).where(BeneficialOwner.business_id == business.id)
    ).all()

    # None confidence = identity not checked / unconfirmed -> KYB is PENDING,
    # not F0. A registry outage or coverage gap must never read as a failing
    # grade; the verdict rests on web presence until the registry confirms.
    identity_confidence = assessment.confidence if assessment else None
    identity_pending = identity_confidence is None
    overall_risk = risk.overall_risk if risk else 100

    kyb_score = None if identity_pending else round(identity_confidence * 100)
    risk_score = max(0, 100 - overall_risk)
    web_presence = intel.web_presence_score if intel else None

    # Fuzzy-match categories (entity resolution).
    name_sim = (
        company_name_similarity(business.legal_name, reg.company_name) if reg else None
    )
    addr_sim = (
        address_similarity(business.registered_address, reg.registered_address)
        if reg and business.registered_address and reg.registered_address else None
    )

    # Verified if we found it, the name matches well, and it isn't inactive.
    # (Many states — e.g. Delaware — don't publish a status; "unknown" is OK.)
    # When identity wasn't checked, verification is "pending" (tri-state).
    status_l = (reg.company_status or "").lower() if reg else ""
    verified: bool | str
    if identity_pending:
        verified = "pending"
    else:
        verified = bool(
            reg and identity_confidence >= 0.5
            and status_l != "inactive"
            and (name_sim or 0) >= 0.80
        )

    registrations = []
    if reg:
        registrations.append(RegistrationOut(
            type="domestic",
            state=_state_from_jurisdiction(business.jurisdiction),
            status=reg.company_status,
            filing_date=reg.incorporation_date,
        ))

    footprint = None
    if intel:
        socials = intel.socials or {}
        footprint = FootprintBlock(
            verdict=intel.verdict,
            legitimacy_score=intel.legitimacy_score,
            web_presence_score=intel.web_presence_score,
            domain=intel.domain,
            domain_age_days=intel.domain_age_days,
            has_tls=intel.has_tls,
            social_profiles=list(socials.keys()) or _social_profiles(db, business.id),
            social_links=socials,
            profile_summary=intel.profile_summary,
            screenshot_url=intel.screenshot_url,
        )

    # Pending identity -> "provisional_review": the recommendation rests on web
    # evidence only and can never auto-approve until the registry confirms.
    if identity_pending:
        action = "provisional_review"
    elif risk:
        action = _ACTION.get(risk.decision, "manual_review")
    else:
        action = "manual_review"
    decision = DecisionOut(
        action=action,
        confidence=round(identity_confidence, 2) if not identity_pending else None,
        reasoning=(risk.explanation if risk else None),
    )

    sources = {}
    if reg:
        sources["registry"] = {"source": reg.source, "uri": reg.source_uri}
    if intel:
        sources["digital_footprint"] = {"crawler": intel.crawler_source}
        if intel.screenshot_url:
            sources["reputation"] = {"source": "urlscan.io"}

    scores = [
        ScoreOut(type="kyb", score=kyb_score,
                 rating="PENDING" if kyb_score is None else _letter(kyb_score)),
    ]
    # When identity is unconfirmed the risk grade is only a review-band clamp
    # (e.g. 50 -> "F"), which misreads as "bad" for an otherwise-legit business.
    # Present it as PENDING too — the web-presence score carries the real signal.
    if identity_pending:
        scores.append(ScoreOut(type="risk", score=None, rating="PENDING"))
    else:
        scores.append(ScoreOut(type="risk", score=risk_score, rating=_letter(risk_score)))
    if web_presence is not None:
        scores.append(ScoreOut(type="web_presence", score=web_presence,
                               rating=_letter(web_presence)))

    enrichment_block = _enrichment_block(intel)
    warnings = _warnings(db, business.id, identity_pending)

    return ReportOut(
        id=business.id,
        verified=verified,
        business_name_match=_match_category(name_sim),
        business_address_match=_match_category(addr_sim) if addr_sim is not None else None,
        name_match_score=round(name_sim, 2) if name_sim is not None else None,
        tin_matched=None,
        scores=scores,
        business=BusinessBlock(
            name=(reg.company_name if reg else business.legal_name),
            structure=(reg.company_type if reg else business.company_type),
            status=(reg.company_status if reg else None),
            months_in_business=_months_in_business(reg.incorporation_date if reg else None),
            registrations=registrations,
            officers=list(officers),
            beneficial_owners=list(ubos),
        ),
        watchlist_hits=[],
        digital_footprint=footprint,
        enrichment=enrichment_block,
        decision=decision,
        sources=sources,
        warnings=warnings,
    )
