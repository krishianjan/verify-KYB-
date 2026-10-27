"""
Identity matching + confidence engine (deterministic, explainable).

Compares a submitted business profile against the registry profile/officers/PSC
and produces: a confidence score (0..1), field-level mismatches, derived risk
signals, and a decision (auto_approve | manual_review | reject).

No AI here by design — risk decisions must be deterministic and auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import settings
from ..models import Decision, Severity
from ..registry.dto import (
    RegistryCompanyProfile,
    RegistryOfficer,
    RegistryPSC,
)
from .normalize import (
    address_similarity,
    company_name_similarity,
)

# Canonical inactive states that should never auto-approve. Adapters normalize
# provider-specific status text into this vocabulary (US SoS -> "inactive").
_INACTIVE_STATES = {
    "dissolved", "liquidation", "closed", "converted-closed", "removed", "inactive",
}


@dataclass
class MismatchResult:
    field: str
    submitted_value: str | None
    registry_value: str | None
    severity: str
    detail: str


@dataclass
class SignalResult:
    code: str
    severity: str
    weight: float
    detail: str


@dataclass
class SubmittedBusiness:
    """Thin input view so the engine doesn't depend on the ORM object."""

    legal_name: str
    company_number: str | None = None
    registered_address: str | None = None
    incorporation_date: str | None = None


@dataclass
class AssessmentResult:
    confidence: float | None
    decision: str
    matched_company_number: str | None
    summary: str
    mismatches: list[MismatchResult] = field(default_factory=list)
    signals: list[SignalResult] = field(default_factory=list)


def assess_identity(
    submitted: SubmittedBusiness,
    profile: RegistryCompanyProfile | None,
    officers: list[RegistryOfficer],
    pscs: list[RegistryPSC],
    psc_supported: bool = True,
) -> AssessmentResult:
    mismatches: list[MismatchResult] = []
    signals: list[SignalResult] = []

    # No registry match found. This is NOT proof the business is fake — the
    # entity may be in a registry we don't cover (Delaware/foreign), filed under
    # a different legal name, or the search was too narrow. Treat identity as
    # UNKNOWN (confidence None), flag it, and route to review + web presence
    # rather than auto-rejecting on absence of a match.
    if profile is None:
        signals.append(
            SignalResult(
                code="REGISTRY_NOT_FOUND",
                severity=Severity.MEDIUM,
                weight=0.5,
                detail="No matching company found in the searched registry; "
                       "entity unconfirmed (not necessarily non-existent).",
            )
        )
        return AssessmentResult(
            confidence=None,
            decision=Decision.MANUAL_REVIEW,
            matched_company_number=None,
            summary="No registry match found; identity unconfirmed. "
                    "Assessed on web presence pending further registry coverage.",
            mismatches=mismatches,
            signals=signals,
        )

    # Weighted components. Weights are only counted when the field is available
    # to compare, then renormalized so confidence stays on 0..1.
    components: list[tuple[float, float]] = []  # (weight, score 0..1)

    # --- Name ---------------------------------------------------------------
    name_sim = company_name_similarity(submitted.legal_name, profile.company_name)
    components.append((0.40, name_sim))
    if name_sim < settings.name_match_threshold:
        mismatches.append(
            MismatchResult(
                field="legal_name",
                submitted_value=submitted.legal_name,
                registry_value=profile.company_name,
                severity=Severity.HIGH if name_sim < 0.5 else Severity.MEDIUM,
                detail=f"Name similarity {name_sim:.2f} below "
                f"threshold {settings.name_match_threshold:.2f}.",
            )
        )
        signals.append(
            SignalResult(
                code="NAME_MISMATCH",
                severity=Severity.HIGH if name_sim < 0.5 else Severity.MEDIUM,
                weight=round(1.0 - name_sim, 3),
                detail="Submitted legal name differs from registry name.",
            )
        )

    # --- Company number (only if the applicant supplied one) ----------------
    if submitted.company_number:
        num_match = _norm_num(submitted.company_number) == _norm_num(
            profile.company_number
        )
        components.append((0.20, 1.0 if num_match else 0.0))
        if not num_match:
            mismatches.append(
                MismatchResult(
                    field="company_number",
                    submitted_value=submitted.company_number,
                    registry_value=profile.company_number,
                    severity=Severity.HIGH,
                    detail="Submitted company number does not match registry.",
                )
            )
            signals.append(
                SignalResult(
                    code="NUMBER_MISMATCH",
                    severity=Severity.HIGH,
                    weight=0.8,
                    detail="Company number mismatch.",
                )
            )

    # --- Status (active?) ---------------------------------------------------
    status = (profile.company_status or "").lower()
    if status == "active":
        components.append((0.20, 1.0))
    elif status in _INACTIVE_STATES:
        components.append((0.20, 0.0))
        signals.append(
            SignalResult(
                code="COMPANY_INACTIVE",
                severity=Severity.HIGH,
                weight=1.0,
                detail=f"Company status is '{status}'.",
            )
        )
        mismatches.append(
            MismatchResult(
                field="company_status",
                submitted_value=None,
                registry_value=status,
                severity=Severity.HIGH,
                detail="Company is not active on the registry.",
            )
        )
    else:
        # Status unknown/unpublished: don't score it either way, flag softly.
        signals.append(
            SignalResult(
                code="STATUS_UNKNOWN",
                severity=Severity.LOW,
                weight=0.1,
                detail="Registry did not publish a usable company status.",
            )
        )

    # --- Address (only if supplied) ----------------------------------------
    if submitted.registered_address and profile.registered_address:
        addr_sim = address_similarity(
            submitted.registered_address, profile.registered_address
        )
        components.append((0.10, addr_sim))
        if addr_sim < settings.address_match_threshold:
            mismatches.append(
                MismatchResult(
                    field="registered_address",
                    submitted_value=submitted.registered_address,
                    registry_value=profile.registered_address,
                    severity=Severity.MEDIUM,
                    detail=f"Address similarity {addr_sim:.2f} below "
                    f"threshold {settings.address_match_threshold:.2f}.",
                )
            )
            signals.append(
                SignalResult(
                    code="ADDRESS_MISMATCH",
                    severity=Severity.LOW,
                    weight=round(1.0 - addr_sim, 3),
                    detail="Submitted address differs from registry address.",
                )
            )

    # --- Incorporation date (only if supplied) ------------------------------
    if submitted.incorporation_date and profile.incorporation_date:
        date_match = submitted.incorporation_date[:10] == profile.incorporation_date[:10]
        components.append((0.10, 1.0 if date_match else 0.0))
        if not date_match:
            mismatches.append(
                MismatchResult(
                    field="incorporation_date",
                    submitted_value=submitted.incorporation_date,
                    registry_value=profile.incorporation_date,
                    severity=Severity.MEDIUM,
                    detail="Incorporation date differs from registry.",
                )
            )

    # --- UBO / PSC presence -------------------------------------------------
    if not pscs:
        if psc_supported:
            signals.append(
                SignalResult(
                    code="NO_PSC",
                    severity=Severity.MEDIUM,
                    weight=0.3,
                    detail="No persons with significant control (UBO) on record.",
                )
            )
        else:
            # Jurisdiction publishes no UBO data (e.g. US). Not a red flag;
            # recorded so the case is explicit about the gap.
            signals.append(
                SignalResult(
                    code="NO_VERIFIED_UBO",
                    severity=Severity.INFO,
                    weight=0.0,
                    detail="Jurisdiction does not publish beneficial-owner data; "
                    "officers used as a proxy.",
                )
            )
    if not officers:
        signals.append(
            SignalResult(
                code="NO_OFFICERS",
                severity=Severity.MEDIUM,
                weight=0.3,
                detail="No directors/officers on record.",
            )
        )

    confidence = _weighted(components)

    # High-severity signals cap the confidence so a single hard fail can't
    # be averaged away by otherwise-good fields.
    if any(s.severity == Severity.HIGH for s in signals):
        confidence = min(confidence, 0.40)

    decision = _decide(confidence)
    summary = _summarize(profile, confidence, decision, mismatches, signals)

    return AssessmentResult(
        confidence=round(confidence, 4),
        decision=decision,
        matched_company_number=profile.company_number,
        summary=summary,
        mismatches=mismatches,
        signals=signals,
    )


def _weighted(components: list[tuple[float, float]]) -> float:
    total_w = sum(w for w, _ in components)
    if total_w <= 0:
        return 0.0
    return sum(w * s for w, s in components) / total_w


def _decide(confidence: float) -> str:
    if confidence >= settings.auto_approve_threshold:
        return Decision.AUTO_APPROVE
    if confidence >= settings.manual_review_threshold:
        return Decision.MANUAL_REVIEW
    return Decision.REJECT


def _norm_num(num: str | None) -> str:
    return (num or "").strip().lstrip("0").lower()


def _summarize(profile, confidence, decision, mismatches, signals) -> str:
    bits = [
        f"Matched '{profile.company_name}' ({profile.company_number}), "
        f"status={profile.company_status}.",
        f"Confidence {confidence:.2f} -> {decision}.",
    ]
    if mismatches:
        bits.append(f"{len(mismatches)} field mismatch(es).")
    highs = [s.code for s in signals if s.severity == Severity.HIGH]
    if highs:
        bits.append("High-risk signals: " + ", ".join(highs) + ".")
    return " ".join(bits)
