// TypeScript mirror of apps/api/app/schemas.py — keep in sync with the backend.

export type Decision = "auto_approve" | "manual_review" | "reject";
export type ReportAction =
  | "auto_approve"
  | "manual_review"
  | "provisional_review"
  | "reject";
export type Severity = "info" | "low" | "medium" | "high";
export type MatchCategory = "EXACT" | "SIMILAR" | "PARTIAL" | "NONE";

export interface CaseCreate {
  legal_name: string;
  state?: string | null;
  company_number?: string | null;
  company_type?: string | null;
  website?: string | null;
  registered_address?: string | null;
  incorporation_date?: string | null;
  jurisdiction?: string;
}

export interface Mismatch {
  field: string;
  submitted_value: string | null;
  registry_value: string | null;
  severity: Severity;
  detail: string | null;
}

export interface RiskSignal {
  code: string;
  severity: Severity;
  weight: number;
  detail: string | null;
}

export interface Director {
  name: string;
  role: string | null;
  appointed_on: string | null;
  resigned_on: string | null;
  nationality: string | null;
}

export interface BeneficialOwner {
  name: string;
  kind: string | null;
  natures_of_control: string[];
  notified_on: string | null;
  ceased_on: string | null;
}

export interface Assessment {
  confidence: number | null; // null = identity not checked / unconfirmed
  decision: Decision;
  matched_company_number: string | null;
  summary: string | null;
  mismatches: Mismatch[];
}

export interface Business {
  id: string;
  legal_name: string;
  company_number: string | null;
  company_type: string | null;
  jurisdiction: string;
  website: string | null;
  registered_address: string | null;
  incorporation_date: string | null;
  status: string;
}

export interface RiskOut {
  overall_risk: number;
  rating: string; // low | medium | high
  decision: string; // approve | review | reject
  explanation: string | null;
  reason_codes: string[];
  category_scores: Record<string, number>;
}

export interface CaseOut {
  business: Business;
  assessment: Assessment | null;
  risk: RiskOut | null;
  directors: Director[];
  beneficial_owners: BeneficialOwner[];
  risk_signals: RiskSignal[];
}

export interface ScoreOut {
  type: "kyb" | "risk" | "web_presence";
  score: number | null; // null when PENDING
  rating: string; // A..F or "PENDING"
}

export interface FundingItem {
  round: string | null;
  amount: string | null;
  date: string | null;
  investors: string[];
  source: string | null;
}

export interface NewsItem {
  title: string | null;
  url: string | null;
  date: string | null;
}

export interface EnrichmentBlock {
  description: string | null;
  industry: string | null;
  hq: string | null;
  locations: string[];
  employee_range: string | null;
  founded_year: string | null;
  founders: string[];
  executives: string[];
  socials: Record<string, string>;
  funding: FundingItem[];
  recent_news: NewsItem[];
  sources: string[];
  presence_score: number | null;
  judge_confidence: string | null;
  judge_rationale: string | null;
  narrative: string | null;
}

export interface FootprintBlock {
  verdict: string;
  legitimacy_score: number;
  web_presence_score: number | null;
  domain: string | null;
  domain_age_days: number | null;
  has_tls: boolean | null;
  social_profiles: string[];
  social_links: Record<string, string>;
  profile_summary: string | null;
  screenshot_url: string | null;
}

export interface DecisionOut {
  action: ReportAction;
  confidence: number | null;
  reasoning: string | null;
}

export interface RegistrationOut {
  type: string;
  state: string | null;
  status: string | null;
  filing_date: string | null;
}

export interface BusinessBlock {
  name: string;
  structure: string | null;
  status: string | null;
  months_in_business: number | null;
  registrations: RegistrationOut[];
  officers: Director[];
  beneficial_owners: BeneficialOwner[];
}

export interface ReportOut {
  id: string;
  state: string;
  verified: boolean | "pending";
  business_name_match: MatchCategory;
  business_address_match: MatchCategory | null;
  name_match_score: number | null;
  tin_matched: boolean | null;
  scores: ScoreOut[];
  business: BusinessBlock;
  watchlist_hits: unknown[];
  digital_footprint: FootprintBlock | null;
  enrichment: EnrichmentBlock | null;
  decision: DecisionOut;
  sources: Record<string, unknown>;
  warnings: string[];
}

export interface FootprintOut {
  business_id: string;
  website_url: string | null;
  final_url: string | null;
  http_status: number | null;
  domain: string | null;
  domain_age_days: number | null;
  registrar: string | null;
  has_mx: boolean | null;
  has_tls: boolean | null;
  title: string | null;
  legitimacy_score: number;
  web_presence_score: number | null;
  verdict: string;
  summary: string | null;
  profile_summary: string | null;
  social_links: Record<string, string>;
  crawler_source: string | null;
  screenshot_url: string | null;
  enrichment: Record<string, unknown>;
  judge_confidence: string | null;
  judge_rationale: string | null;
  signals: RiskSignal[];
}

export interface CaseListItem {
  id: string;
  legal_name: string;
  jurisdiction: string;
  status: string;
  identity_decision: string | null;
  identity_confidence: number | null;
  risk_rating: string | null;
  overall_risk: number | null;
  created_at: string;
}

export interface CaseListOut {
  total: number;
  items: CaseListItem[];
}
