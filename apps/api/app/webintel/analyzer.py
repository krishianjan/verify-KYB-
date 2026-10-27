"""Deterministic 'ghost business' analyzer.

Turns crawl + domain evidence into explainable signals, a 0..100 web
legitimacy score, and a verdict. No AI here — these drive the risk decision and
must be auditable. The LLM summarizer only narrates what this produces.
"""
from __future__ import annotations

from ..config import settings
from ..matching.normalize import normalize_company_name
from .dto import CrawlResult, DomainInfo, FootprintResult, FootprintSignal

_SEV_PENALTY = {"high": 35, "medium": 15, "low": 5, "info": 0}
_PLACEHOLDER_MARKERS = (
    "coming soon", "under construction", "domain for sale", "buy this domain",
    "parked", "default web page", "index of /",
)
_SOCIAL_HOSTS = (
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com",
    "youtube.com", "tiktok.com",
)


def _social_platforms(links: list[str]) -> list[str]:
    found: set[str] = set()
    for link in links:
        low = (link or "").lower()
        for host in _SOCIAL_HOSTS:
            if host in low:
                found.add(host.split(".")[0])
    return sorted(found)


def analyze_footprint(
    company_name: str, crawl: CrawlResult, domain: DomainInfo
) -> FootprintResult:
    signals: list[FootprintSignal] = []

    def sig(code: str, severity: str, detail: str, weight: float = 1.0) -> None:
        signals.append(
            FootprintSignal(code=code, severity=severity, weight=weight, detail=detail)
        )

    # --- Reachability / content -------------------------------------------
    if not crawl.ok:
        sig("SITE_UNREACHABLE", "high",
            f"Website could not be fetched ({crawl.error or 'no content'}).")
    else:
        text_low = crawl.text.lower()
        if any(m in text_low for m in _PLACEHOLDER_MARKERS):
            sig("PARKED_OR_PLACEHOLDER", "high",
                "Site looks like a parked/placeholder page.")
        if len(crawl.text) < 500:
            sig("THIN_CONTENT", "medium",
                f"Very little page content ({len(crawl.text)} chars).")
        if not crawl.emails and not crawl.phones:
            sig("NO_CONTACT_INFO", "medium",
                "No email or phone contact found on the site.")
        if not _name_present(company_name, crawl):
            sig("NAME_NOT_ON_SITE", "medium",
                f"Registered name '{company_name}' not found on the website.")
        socials = _social_platforms(crawl.links)
        if not socials:
            sig("NO_SOCIAL_PRESENCE", "low",
                "No links to social media profiles found on the site.")
        else:
            sig("SOCIAL_PRESENCE", "info",
                "Social profiles linked: " + ", ".join(socials) + ".")

    # --- Domain intelligence ----------------------------------------------
    if domain.age_days is not None:
        if domain.age_days < 30:
            sig("DOMAIN_TOO_NEW", "high",
                f"Domain registered only {domain.age_days} days ago.")
        elif domain.age_days < settings.domain_age_red_flag_days:
            sig("DOMAIN_RECENT", "medium",
                f"Domain is young ({domain.age_days} days old).")
    else:
        sig("DOMAIN_AGE_UNKNOWN", "info", "Could not determine domain age.")

    if domain.has_mx is False:
        sig("NO_MAIL_SERVER", "medium",
            "Domain has no MX record (cannot receive email).")
    if domain.has_tls is False:
        sig("NO_TLS", "low", "Site has no valid HTTPS/TLS.")

    # --- Score + verdict ---------------------------------------------------
    penalty = sum(_SEV_PENALTY.get(s.severity, 0) for s in signals)
    score = max(0, min(100, 100 - penalty))
    verdict = _verdict(score, signals)

    return FootprintResult(legitimacy_score=score, verdict=verdict, signals=signals)


def _name_present(company_name: str, crawl: CrawlResult) -> bool:
    norm = normalize_company_name(company_name)
    tokens = [t for t in norm.split() if len(t) > 2]
    if not tokens:
        return True  # nothing meaningful to look for
    haystack = f"{crawl.title or ''} {crawl.meta_description or ''} {crawl.text}".lower()
    hits = sum(1 for t in tokens if t in haystack)
    return hits >= max(1, len(tokens) // 2)  # at least half the name tokens present


def _verdict(score: int, signals: list[FootprintSignal]) -> str:
    codes = {s.code for s in signals}
    if "SITE_UNREACHABLE" in codes or "PARKED_OR_PLACEHOLDER" in codes:
        return "ghost"
    highs = sum(1 for s in signals if s.severity == "high")
    if highs >= 2 or score < 30:
        return "ghost"
    if "NAME_NOT_ON_SITE" in codes and score < 70:
        return "inconsistent"
    if score >= 75:
        return "real"
    if score >= 50:
        return "thin"
    return "inconsistent"
