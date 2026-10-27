"""Digital-footprint pipeline: crawl -> domain intel -> analyze -> summarize.

Runs on a business that has a website, persists a WebIntel record plus web risk
signals, and writes audit events. Depends only on the crawler/summarizer
interfaces, so backends swap freely.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AuditEvent, Business, RegistryRecord, RiskSignal, WebIntel
from ..vectorstore import add_memory, find_similar_web, recall_memory, upsert_web
from .analyzer import analyze_footprint
from .crawler import WebCrawler
from .discover import discover_socials, discover_website, socials_from_links
from .domain import get_domain_info
from .dto import CrawlResult, DomainInfo
from .enrich import enrich_company
from .judge import blend_presence, judge_web_presence
from .profile import company_profile
from .report_text import generate_intel_report
from .reputation import get_reputation
from .search import get_search_provider
from .summarizer import Summarizer


def run_footprint_pipeline(
    db: Session, business: Business, crawler: WebCrawler, summarizer: Summarizer
) -> WebIntel:
    _audit(db, business.id, "footprint.started", {"website": business.website})

    # Website is optional: use the submitted one, else try to discover a site
    # from the registry context (business email domain) or a web search.
    target_url = business.website
    discovered = False
    if not target_url:
        rec = db.scalars(
            select(RegistryRecord)
            .where(RegistryRecord.business_id == business.id)
            .order_by(RegistryRecord.fetched_at.desc())
        ).first()
        target_url = discover_website(business.legal_name, rec.raw if rec else {})
        discovered = bool(target_url)

    memory = recall_memory(business.id)

    if not target_url:
        # No site found — enrich from web search + LLM profile for review.
        socials = discover_socials(business.legal_name)
        profile = company_profile(business.legal_name, "", None, socials)
        ctx = "No website found; profile built from web search" + (
            " and social presence." if socials else " and name only."
        )
        if memory:
            ctx += " Prior context: " + " ".join(memory[:2])
        enr = _run_enrichment(business, None, socials, crawler,
                              deterministic_score=50)
        presence = enr["web_presence_score"] if enr else None
        if enr and enr["narrative"]:
            ctx = enr["narrative"]
        intel = WebIntel(
            business_id=business.id, website_url=None, verdict="unknown",
            legitimacy_score=50, summary=ctx, profile_summary=profile,
            socials=(enr["enrichment"].get("socials") if enr else socials) or socials,
            crawler_source="none",
            enrichment=enr["enrichment"] if enr else {},
            web_presence_score=presence,
            judge_confidence=enr["judge"].confidence if enr else None,
            judge_rationale=enr["judge"].rationale if enr else None,
        )
        db.add(intel)
        if socials:
            db.add(RiskSignal(
                business_id=business.id, code="SOCIAL_PRESENCE", severity="info",
                weight=0.0, source="web_intel",
                detail="Social profiles found: " + ", ".join(socials) + ".",
            ))
        db.add(RiskSignal(
            business_id=business.id, code="NO_WEBSITE", severity="low",
            weight=0.2, detail="No website provided or discovered.",
            source="web_intel",
        ))
        db.flush()
        add_memory(business.id, "Footprint: no website found; context-only.")
        _audit(db, business.id, "footprint.context_only", {"memory": len(memory)})
        db.commit()
        db.refresh(intel)
        return intel

    crawl: CrawlResult = crawler.fetch(target_url)
    domain: DomainInfo = get_domain_info(target_url)
    reputation = get_reputation(domain.domain)
    # Socials from the page itself (reliable) + web search (best-effort).
    socials = socials_from_links(crawl.links)
    for k, v in discover_socials(business.legal_name).items():
        socials.setdefault(k, v)
    footprint = analyze_footprint(business.legal_name, crawl, domain)
    summary = summarizer.summarize(business.legal_name, crawl, domain, footprint)
    if discovered:
        summary = f"[Website auto-discovered: {target_url}] {summary}"
    if memory:
        summary = f"{summary}\n\nPrior context: {memory[0]}"
    profile = company_profile(business.legal_name, crawl.text, crawl.title, socials)

    # Web-intelligence enrichment + LLM web-presence judge (complementary signal).
    enr = _run_enrichment(business, target_url, socials, crawler,
                          deterministic_score=footprint.legitimacy_score,
                          seed_text=crawl.text)
    presence = enr["web_presence_score"] if enr else None
    if enr:
        socials = enr["enrichment"].get("socials") or socials
        if enr["narrative"]:
            summary = f"{summary}\n\nWeb intelligence: {enr['narrative']}"

    intel = WebIntel(
        business_id=business.id,
        website_url=target_url,
        final_url=crawl.final_url,
        http_status=crawl.status_code,
        domain=domain.domain,
        domain_age_days=domain.age_days,
        registrar=domain.registrar,
        has_mx=domain.has_mx,
        has_tls=domain.has_tls,
        title=crawl.title,
        legitimacy_score=footprint.legitimacy_score,
        web_presence_score=presence,
        verdict=footprint.verdict,
        summary=summary,
        profile_summary=profile,
        socials=socials,
        crawler_source=crawl.source,
        screenshot_url=reputation.screenshot,
        enrichment=enr["enrichment"] if enr else {},
        judge_confidence=enr["judge"].confidence if enr else None,
        judge_rationale=enr["judge"].rationale if enr else None,
        raw={
            "crawl": crawl.model_dump(exclude={"raw"}),
            "domain": domain.model_dump(),
            "reputation": reputation.model_dump(),
        },
    )
    db.add(intel)

    social_persisted = False
    for s in footprint.signals:
        # Web-searched socials override the on-site "none".
        if s.code == "NO_SOCIAL_PRESENCE" and socials:
            continue
        if s.code == "SOCIAL_PRESENCE":
            social_persisted = True
        db.add(RiskSignal(
            business_id=business.id, code=s.code, severity=s.severity,
            weight=s.weight, detail=s.detail, source="web_intel",
        ))
    if socials and not social_persisted:
        db.add(RiskSignal(
            business_id=business.id, code="SOCIAL_PRESENCE", severity="info",
            weight=0.0, source="web_intel",
            detail="Social profiles found: " + ", ".join(sorted(socials)) + ".",
        ))
    if reputation.checked and not reputation.error and reputation.total == 0:
        db.add(RiskSignal(
            business_id=business.id, code="URLSCAN_NO_HISTORY", severity="info",
            weight=0.1, detail="Domain has no public urlscan.io scan history.",
            source="web_intel",
        ))

    # Vector-DB cloned/templated-site detection (shell-network signal).
    # Exclude the SAME entity (same normalized name or same domain) so prior
    # records of this business don't count as clones of itself.
    if crawl.ok and crawl.text:
        from ..matching.normalize import normalize_company_name

        my_name = normalize_company_name(business.legal_name)
        my_domain = (domain.domain or "").lower()
        clone = None
        for m in find_similar_web(crawl.text, exclude_business_id=business.id):
            if m["distance"] > settings.dup_distance_threshold:
                continue
            meta = m.get("metadata") or {}
            same_name = normalize_company_name(meta.get("legal_name", "")) == my_name
            same_domain = (meta.get("domain") or "").lower() == my_domain and my_domain
            if same_name or same_domain:
                continue  # a prior record of the same business, not a clone
            clone = m
            break
        if clone is not None:
            other = (clone.get("metadata") or {}).get("legal_name") or clone["business_id"]
            db.add(RiskSignal(
                business_id=business.id, code="CLONED_SITE_MATCH", severity="high",
                weight=1.0, source="web_intel",
                detail=(f"Website near-identical to a different business "
                        f"'{other}' (distance {clone['distance']:.3f}) — "
                        f"needs analyst disambiguation."),
            ))
        upsert_web(business.id, crawl.text,
                   {"legal_name": business.legal_name, "domain": domain.domain or ""})
    db.flush()

    add_memory(business.id, f"Footprint: {footprint.verdict} "
               f"({footprint.legitimacy_score}/100) for {domain.domain}.")
    _audit(db, business.id, "footprint.completed", {
        "verdict": footprint.verdict,
        "score": footprint.legitimacy_score,
        "crawler": crawl.source,
        "discovered_website": discovered,
        "signals": [s.code for s in footprint.signals],
    })
    db.commit()
    db.refresh(intel)
    return intel


def _run_enrichment(
    business: Business,
    website: str | None,
    socials: dict,
    crawler: WebCrawler,
    deterministic_score: int,
    seed_text: str | None = None,
) -> dict | None:
    """Gather web intelligence, judge web presence, and blend the score.

    Safe: returns None on any failure (disabled, no LLM, network) so the
    footprint pipeline continues on its deterministic result.
    """
    if not settings.enable_enrichment:
        return None
    try:
        search = get_search_provider()
        data = enrich_company(
            business.legal_name, website, socials, search, crawler,
            seed_text=seed_text,
        )
        evidence = data.model_dump()
        judgment = judge_web_presence(evidence)
        presence = blend_presence(deterministic_score, judgment)
        narrative = generate_intel_report(
            business.legal_name, evidence, judgment.model_dump()
        )
        return {
            "enrichment": evidence,
            "web_presence_score": presence,
            "judge": judgment,
            "narrative": narrative,
        }
    except Exception:  # noqa: BLE001 - enrichment must never break the pipeline
        return None


def _audit(db: Session, business_id: str, event_type: str, detail: dict) -> None:
    db.add(AuditEvent(business_id=business_id, event_type=event_type,
                      actor="system", detail=detail))
    db.flush()
