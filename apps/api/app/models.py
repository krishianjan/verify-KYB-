from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---- Status / enum constants (kept as plain strings for portability) --------

class CaseStatus:
    RECEIVED = "received"
    VERIFYING = "verifying"
    AUTO_APPROVED = "auto_approved"
    MANUAL_REVIEW = "manual_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Decision:
    AUTO_APPROVE = "auto_approve"
    MANUAL_REVIEW = "manual_review"
    REJECT = "reject"


class Severity:
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---- Core entities ----------------------------------------------------------

class Business(Base):
    __tablename__ = "business"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    legal_name: Mapped[str] = mapped_column(String(512), index=True)
    company_number: Mapped[str | None] = mapped_column(String(64), index=True)
    company_type: Mapped[str | None] = mapped_column(String(128))
    jurisdiction: Mapped[str] = mapped_column(String(8), default="gb")
    website: Mapped[str | None] = mapped_column(String(512))
    registered_address: Mapped[str | None] = mapped_column(Text)
    incorporation_date: Mapped[str | None] = mapped_column(String(32))

    status: Mapped[str] = mapped_column(String(32), default=CaseStatus.RECEIVED)
    submitted_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    registry_records: Mapped[list["RegistryRecord"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    directors: Mapped[list["Director"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    beneficial_owners: Mapped[list["BeneficialOwner"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    risk_signals: Mapped[list["RiskSignal"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    assessments: Mapped[list["IdentityAssessment"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )


class RegistryRecord(Base):
    """Raw evidence: what an official registry returned for this business."""

    __tablename__ = "registry_record"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("business.id"), index=True)

    source: Mapped[str] = mapped_column(String(64))  # e.g. companies_house
    company_number: Mapped[str | None] = mapped_column(String(64))
    company_name: Mapped[str | None] = mapped_column(String(512))
    company_status: Mapped[str | None] = mapped_column(String(64))
    company_type: Mapped[str | None] = mapped_column(String(128))
    incorporation_date: Mapped[str | None] = mapped_column(String(32))
    registered_address: Mapped[str | None] = mapped_column(Text)
    source_uri: Mapped[str | None] = mapped_column(String(512))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

    fetched_at: Mapped[datetime] = mapped_column(default=_now)

    business: Mapped["Business"] = relationship(back_populates="registry_records")


class Director(Base):
    __tablename__ = "director"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("business.id"), index=True)

    name: Mapped[str] = mapped_column(String(512))
    role: Mapped[str | None] = mapped_column(String(128))
    appointed_on: Mapped[str | None] = mapped_column(String(32))
    resigned_on: Mapped[str | None] = mapped_column(String(32))
    nationality: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str | None] = mapped_column(String(64))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

    business: Mapped["Business"] = relationship(back_populates="directors")


class BeneficialOwner(Base):
    """UBO. In the UK this maps to Persons with Significant Control (PSC)."""

    __tablename__ = "beneficial_owner"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("business.id"), index=True)

    name: Mapped[str] = mapped_column(String(512))
    kind: Mapped[str | None] = mapped_column(String(128))
    natures_of_control: Mapped[list] = mapped_column(JSON, default=list)
    notified_on: Mapped[str | None] = mapped_column(String(32))
    ceased_on: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(String(64))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

    business: Mapped["Business"] = relationship(back_populates="beneficial_owners")


class IdentityAssessment(Base):
    __tablename__ = "identity_assessment"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("business.id"), index=True)

    # Nullable: None means "identity not checked / unconfirmed" (registry
    # unavailable or no match), which is distinct from a low score (0.0).
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    decision: Mapped[str] = mapped_column(String(32), default=Decision.MANUAL_REVIEW)
    matched_company_number: Mapped[str | None] = mapped_column(String(64))
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    business: Mapped["Business"] = relationship(back_populates="assessments")
    mismatches: Mapped[list["Mismatch"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class Mismatch(Base):
    __tablename__ = "mismatch"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("identity_assessment.id"), index=True
    )

    field: Mapped[str] = mapped_column(String(64))
    submitted_value: Mapped[str | None] = mapped_column(Text)
    registry_value: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), default=Severity.MEDIUM)
    detail: Mapped[str | None] = mapped_column(Text)

    assessment: Mapped["IdentityAssessment"] = relationship(back_populates="mismatches")


class RiskSignal(Base):
    __tablename__ = "risk_signal"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("business.id"), index=True)

    code: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), default=Severity.LOW)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=_now)

    business: Mapped["Business"] = relationship(back_populates="risk_signals")


class WebIntel(Base):
    """Digital-footprint assessment for a business (Feature 2)."""

    __tablename__ = "web_intel"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("business.id"), index=True)

    website_url: Mapped[str | None] = mapped_column(String(512))
    final_url: Mapped[str | None] = mapped_column(String(512))
    http_status: Mapped[int | None] = mapped_column()
    domain: Mapped[str | None] = mapped_column(String(255))
    domain_age_days: Mapped[int | None] = mapped_column()
    registrar: Mapped[str | None] = mapped_column(String(255))
    has_mx: Mapped[bool | None] = mapped_column()
    has_tls: Mapped[bool | None] = mapped_column()
    title: Mapped[str | None] = mapped_column(String(512))

    legitimacy_score: Mapped[int] = mapped_column(default=0)
    verdict: Mapped[str] = mapped_column(String(32), default="unknown")
    summary: Mapped[str | None] = mapped_column(Text)
    profile_summary: Mapped[str | None] = mapped_column(Text)
    socials: Mapped[dict] = mapped_column(JSON, default=dict)
    crawler_source: Mapped[str | None] = mapped_column(String(32))
    screenshot_url: Mapped[str | None] = mapped_column(String(512))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

    # Feature 4: web-intelligence enrichment (structured evidence + LLM judge).
    enrichment: Mapped[dict] = mapped_column(JSON, default=dict)
    web_presence_score: Mapped[int | None] = mapped_column()
    judge_confidence: Mapped[str | None] = mapped_column(String(16))
    judge_rationale: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(default=_now)


class RiskScore(Base):
    """Combined inherent-risk rating (identity + footprint). Feature 3."""

    __tablename__ = "risk_score"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("business.id"), index=True)

    overall_risk: Mapped[int] = mapped_column(default=0)      # 0..100 (higher=riskier)
    rating: Mapped[str] = mapped_column(String(16), default="low")   # low|medium|high
    decision: Mapped[str] = mapped_column(String(16), default="review")
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    category_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class ReviewAction(Base):
    """An analyst decision/action on a case. Feature 3."""

    __tablename__ = "review_action"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("business.id"), index=True)

    action: Mapped[str] = mapped_column(String(32))   # approve|reject|request_docs|escalate
    notes: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(128), default="analyst")
    created_at: Mapped[datetime] = mapped_column(default=_now)


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str | None] = mapped_column(
        ForeignKey("business.id"), index=True
    )

    event_type: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(128), default="system")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=_now)
