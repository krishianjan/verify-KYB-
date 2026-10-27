"""
Identity verification pipeline.

Orchestrates: candidate resolution -> evidence fetch -> persistence ->
matching/scoring -> decision -> audit. Depends only on the RegistryAdapter
interface, never a concrete provider.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .config import settings
from .matching import SubmittedBusiness, assess_identity
from .matching.normalize import company_name_similarity, normalize_company_name
from .models import (
    AuditEvent,
    BeneficialOwner,
    Business,
    CaseStatus,
    Decision,
    Director,
    IdentityAssessment,
    Mismatch,
    RegistryRecord,
    RiskSignal,
)
from .registry.base import RegistryAdapter, RegistryError, RegistryUnavailable
from .registry.dto import RegistryCompanyProfile


def run_identity_pipeline(
    db: Session, business: Business, adapter: RegistryAdapter
) -> IdentityAssessment:
    _audit(db, business.id, "pipeline.started", {"provider": adapter.source})
    business.status = CaseStatus.VERIFYING
    db.flush()

    # No state/number for a registry that needs one: skip the slow nationwide
    # search and route to web-presence review (not a reject).
    has_subdivision = "-" in (business.jurisdiction or "")
    if (getattr(adapter, "requires_subdivision", False)
            and not business.company_number and not has_subdivision):
        assessment = IdentityAssessment(
            business_id=business.id, confidence=None,
            decision=Decision.MANUAL_REVIEW,
            summary="No state or company number provided; registry not searched. "
                    "Identity pending; reviewed against web presence.",
        )
        db.add(assessment)
        db.add(RiskSignal(
            business_id=business.id, code="REGISTRY_STATE_NOT_PROVIDED",
            severity="medium", weight=0.5, source="identity_engine",
            detail="No state/number provided; official registry not searched.",
        ))
        business.status = CaseStatus.MANUAL_REVIEW
        db.flush()
        _audit(db, business.id, "pipeline.skipped_no_state", {})
        return assessment

    try:
        profile = _resolve_company(adapter, business)
    except RegistryUnavailable as exc:
        # We never got to check the entity (quota/limit/network). This is
        # NOT-CHECKED, not evidence of fraud: confidence is unknown (None),
        # route to review, and flag for the web-intelligence fallback.
        _audit(db, business.id, "registry.unavailable", {"error": str(exc)})
        assessment = IdentityAssessment(
            business_id=business.id,
            confidence=None,
            decision=Decision.MANUAL_REVIEW,
            summary="Registry temporarily unavailable; entity not checked. "
                    "Assessed on web presence pending a registry re-check.",
        )
        db.add(assessment)
        db.add(RiskSignal(
            business_id=business.id, code="REGISTRY_UNAVAILABLE",
            severity="medium", weight=0.5, source="identity_engine",
            detail=f"Official registry could not be reached: {exc}",
        ))
        business.status = CaseStatus.MANUAL_REVIEW
        db.flush()
        return assessment
    except RegistryError as exc:
        _audit(db, business.id, "registry.error", {"error": str(exc)})
        business.status = CaseStatus.MANUAL_REVIEW
        assessment = IdentityAssessment(
            business_id=business.id,
            confidence=None,
            decision=Decision.MANUAL_REVIEW,
            summary=f"Registry error: {exc}",
        )
        db.add(assessment)
        db.add(RiskSignal(
            business_id=business.id, code="REGISTRY_UNAVAILABLE",
            severity="medium", weight=0.5, source="identity_engine",
            detail=f"Registry call failed: {exc}",
        ))
        db.flush()
        return assessment

    officers = adapter.get_officers(profile.company_number) if profile else []
    pscs = adapter.get_psc(profile.company_number) if profile else []

    if profile is not None:
        _persist_evidence(db, business, adapter, profile, officers, pscs)

    result = assess_identity(
        submitted=SubmittedBusiness(
            legal_name=business.legal_name,
            company_number=business.company_number,
            registered_address=business.registered_address,
            incorporation_date=business.incorporation_date,
        ),
        profile=profile,
        officers=officers,
        pscs=pscs,
        psc_supported=adapter.supports_psc,
    )

    assessment = IdentityAssessment(
        business_id=business.id,
        confidence=result.confidence,
        decision=result.decision,
        matched_company_number=result.matched_company_number,
        summary=result.summary,
    )
    db.add(assessment)
    db.flush()

    for m in result.mismatches:
        db.add(
            Mismatch(
                assessment_id=assessment.id,
                field=m.field,
                submitted_value=m.submitted_value,
                registry_value=m.registry_value,
                severity=m.severity,
                detail=m.detail,
            )
        )
    for s in result.signals:
        db.add(
            RiskSignal(
                business_id=business.id,
                code=s.code,
                severity=s.severity,
                weight=s.weight,
                detail=s.detail,
                source="identity_engine",
            )
        )

    business.status = _status_for(result.decision)
    db.flush()

    _audit(
        db,
        business.id,
        "pipeline.completed",
        {
            "confidence": result.confidence,
            "decision": result.decision,
            "mismatches": len(result.mismatches),
            "signals": [s.code for s in result.signals],
        },
    )
    return assessment


def _resolve_company(
    adapter: RegistryAdapter, business: Business
) -> RegistryCompanyProfile | None:
    # Prefer an exact company-number lookup when supplied.
    if business.company_number:
        profile = adapter.get_company(business.company_number)
        if profile is not None:
            return profile
        # Fall through to name search if the number didn't resolve.

    summaries = adapter.search(business.legal_name, business.jurisdiction)
    if not summaries:
        return None

    # Prefer an ACTIVE entity with a strong name match over a dissolved/tangential
    # one (e.g. don't pick "360 Virtual Tours by Google LLC" (dissolved) for "Google").
    def _rank(s):
        sim = company_name_similarity(business.legal_name, s.company_name)
        active = 1 if (s.company_status or "").lower() == "active" else 0
        return (active, sim)

    best = max(summaries, key=_rank)

    # If the applicant gave no company number and the best match shares too few
    # name tokens, this is not a confident match — report "not found" rather than
    # attach to an unrelated entity (e.g. "google" -> "360 Virtual Tours by Google").
    if not business.company_number:
        if _token_overlap(business.legal_name, best.company_name) < \
                settings.candidate_min_token_overlap:
            return None

    return adapter.get_company(best.company_number)


def _token_overlap(a: str, b: str) -> float:
    ta = set(normalize_company_name(a).split())
    tb = set(normalize_company_name(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _persist_evidence(db, business, adapter, profile, officers, pscs) -> None:
    db.add(
        RegistryRecord(
            business_id=business.id,
            source=adapter.source,
            company_number=profile.company_number,
            company_name=profile.company_name,
            company_status=profile.company_status,
            company_type=profile.company_type,
            incorporation_date=profile.incorporation_date,
            registered_address=profile.registered_address,
            source_uri=profile.source_uri,
            raw=profile.raw or {},
        )
    )
    for o in officers:
        db.add(
            Director(
                business_id=business.id,
                name=o.name,
                role=o.role,
                appointed_on=o.appointed_on,
                resigned_on=o.resigned_on,
                nationality=o.nationality,
                source=adapter.source,
                raw=o.raw or {},
            )
        )
    for p in pscs:
        db.add(
            BeneficialOwner(
                business_id=business.id,
                name=p.name,
                kind=p.kind,
                natures_of_control=p.natures_of_control or [],
                notified_on=p.notified_on,
                ceased_on=p.ceased_on,
                source=adapter.source,
                raw=p.raw or {},
            )
        )
    db.flush()


def _status_for(decision: str) -> str:
    return {
        Decision.AUTO_APPROVE: CaseStatus.AUTO_APPROVED,
        Decision.MANUAL_REVIEW: CaseStatus.MANUAL_REVIEW,
        Decision.REJECT: CaseStatus.REJECTED,
    }.get(decision, CaseStatus.MANUAL_REVIEW)


def _audit(db: Session, business_id: str | None, event_type: str, detail: dict) -> None:
    db.add(
        AuditEvent(
            business_id=business_id,
            event_type=event_type,
            actor="system",
            detail=detail,
        )
    )
    db.flush()
