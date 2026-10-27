from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---- Input ------------------------------------------------------------------

class CaseCreate(BaseModel):
    legal_name: str = Field(min_length=1, max_length=512)
    company_number: str | None = None
    company_type: str | None = None
    jurisdiction: str = "us"
    state: str | None = None  # US state/subdivision, e.g. "CA". Narrows the SoS search.
    website: str | None = None
    registered_address: str | None = None
    incorporation_date: str | None = None  # "YYYY-MM-DD"


# ---- Output -----------------------------------------------------------------

class MismatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    field: str
    submitted_value: str | None
    registry_value: str | None
    severity: str
    detail: str | None


class RiskSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    severity: str
    weight: float
    detail: str | None


class DirectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    role: str | None
    appointed_on: str | None
    resigned_on: str | None
    nationality: str | None


class BeneficialOwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    kind: str | None
    natures_of_control: list[str]
    notified_on: str | None
    ceased_on: str | None


class AssessmentOut(BaseModel):
    confidence: float | None  # None = identity not checked / unconfirmed
    decision: str
    matched_company_number: str | None
    summary: str | None
    mismatches: list[MismatchOut] = []


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    legal_name: str
    company_number: str | None
    company_type: str | None
    jurisdiction: str
    website: str | None
    registered_address: str | None
    incorporation_date: str | None
    status: str


class RiskOut(BaseModel):
    overall_risk: int
    rating: str
    decision: str
    explanation: str | None = None
    reason_codes: list[str] = []
    category_scores: dict[str, int] = {}


class CaseOut(BaseModel):
    business: BusinessOut
    assessment: AssessmentOut | None
    risk: RiskOut | None = None
    directors: list[DirectorOut] = []
    beneficial_owners: list[BeneficialOwnerOut] = []
    risk_signals: list[RiskSignalOut] = []


# ---- Feature 3: review queue + analyst actions ------------------------------

class CaseListItem(BaseModel):
    id: str
    legal_name: str
    jurisdiction: str
    status: str
    identity_decision: str | None = None
    identity_confidence: float | None = None
    risk_rating: str | None = None
    overall_risk: int | None = None
    created_at: str


class CaseListOut(BaseModel):
    total: int
    items: list[CaseListItem] = []


class ActionIn(BaseModel):
    action: str  # approve | reject | request_docs | escalate
    notes: str | None = None
    actor: str = "analyst"


class ActionOut(BaseModel):
    business_id: str
    action: str
    notes: str | None
    actor: str
    status: str


# ---- Baselayer-shaped verification report -----------------------------------

class ScoreOut(BaseModel):
    type: str                 # "kyb" | "risk" | "web_presence"
    score: int | None         # 0..100 (higher = better); None when PENDING
    rating: str               # A..F, or "PENDING" when not yet assessable


class RegistrationOut(BaseModel):
    type: str           # domestic | foreign
    state: str | None
    status: str | None
    filing_date: str | None


class BusinessBlock(BaseModel):
    name: str
    structure: str | None
    status: str | None
    months_in_business: int | None
    registrations: list[RegistrationOut] = []
    officers: list[DirectorOut] = []
    beneficial_owners: list[BeneficialOwnerOut] = []


class FootprintBlock(BaseModel):
    verdict: str
    legitimacy_score: int
    web_presence_score: int | None = None
    domain: str | None = None
    domain_age_days: int | None = None
    has_tls: bool | None = None
    social_profiles: list[str] = []
    social_links: dict = {}
    profile_summary: str | None = None
    screenshot_url: str | None = None


class FundingItem(BaseModel):
    round: str | None = None
    amount: str | None = None
    date: str | None = None
    investors: list[str] = []
    source: str | None = None


class NewsItem(BaseModel):
    title: str | None = None
    url: str | None = None
    date: str | None = None


class EnrichmentBlock(BaseModel):
    description: str | None = None
    industry: str | None = None
    hq: str | None = None
    locations: list[str] = []
    employee_range: str | None = None
    founded_year: str | None = None
    founders: list[str] = []
    executives: list[str] = []
    socials: dict = {}
    funding: list[FundingItem] = []
    recent_news: list[NewsItem] = []
    sources: list[str] = []
    # LLM-as-judge (complementary signal, never the decision).
    presence_score: int | None = None
    judge_confidence: str | None = None
    judge_rationale: str | None = None
    narrative: str | None = None


class DecisionOut(BaseModel):
    action: str         # auto_approve | manual_review | provisional_review | reject
    confidence: float | None
    reasoning: str | None


class ReportOut(BaseModel):
    id: str
    state: str = "COMPLETED"
    verified: bool | str                # True | False | "pending"
    business_name_match: str            # EXACT | SIMILAR | PARTIAL | NONE
    business_address_match: str | None
    name_match_score: float | None = None
    tin_matched: bool | None = None     # planned (CompliAPI / IRS)
    scores: list[ScoreOut]
    business: BusinessBlock
    watchlist_hits: list = []           # planned (CompliAPI / OFAC)
    digital_footprint: FootprintBlock | None = None
    enrichment: EnrichmentBlock | None = None
    decision: DecisionOut
    sources: dict = {}
    warnings: list[str] = []


# ---- Feature 2: digital footprint -------------------------------------------

class FootprintOut(BaseModel):
    business_id: str
    website_url: str | None
    final_url: str | None
    http_status: int | None
    domain: str | None
    domain_age_days: int | None
    registrar: str | None
    has_mx: bool | None
    has_tls: bool | None
    title: str | None
    legitimacy_score: int
    web_presence_score: int | None = None
    verdict: str
    summary: str | None
    profile_summary: str | None = None
    social_links: dict = {}
    crawler_source: str | None
    screenshot_url: str | None = None
    enrichment: dict = {}
    judge_confidence: str | None = None
    judge_rationale: str | None = None
    signals: list[RiskSignalOut] = []
