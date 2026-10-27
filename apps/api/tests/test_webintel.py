"""Tests for Feature 2 (digital footprint). No live network: the analyzer is
pure, and the pipeline test stubs domain intel + uses the mock crawler.

Run from apps/api with::  python -m pytest tests/test_webintel.py -v
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{tempfile.mkdtemp(prefix='verifykyb-test-webintel-')}/test.db",
)
os.environ["ENABLE_VECTOR"] = "false"  # keep tests offline/fast (no embedding model)
os.environ["ENABLE_ENRICHMENT"] = "false"  # no live web search/LLM in unit tests

from app.webintel.analyzer import analyze_footprint
from app.webintel.dto import CrawlResult, DomainInfo


def _codes(fp) -> list[str]:
    return [s.code for s in fp.signals]


def test_analyzer_flags_ghost_site():
    crawl = CrawlResult(url="x", status_code=200, title="Welcome",
                        text="Welcome. Coming soon.", ok=True)
    dom = DomainInfo(domain="x", age_days=5, has_mx=False, has_tls=False)
    fp = analyze_footprint("ACME TRADING LTD", crawl, dom)
    assert fp.verdict == "ghost"
    assert fp.legitimacy_score == 0
    assert "DOMAIN_TOO_NEW" in _codes(fp)
    assert "PARKED_OR_PLACEHOLDER" in _codes(fp)


def test_analyzer_passes_real_site():
    text = ("ACME Trading Ltd supplies industrial components since 2015. "
            "Email info@acme.example phone +44 20 7946 0000. About team services. ") * 4
    crawl = CrawlResult(url="x", status_code=200, title="ACME Trading Ltd", text=text,
                        emails=["info@acme.example"], phones=["+44 20 7946 0000"],
                        links=["https://facebook.com/acme"], ok=True)
    dom = DomainInfo(domain="x", age_days=2000, has_mx=True, has_tls=True)
    fp = analyze_footprint("ACME TRADING LTD", crawl, dom)
    assert fp.verdict == "real"
    assert fp.legitimacy_score >= 90
    assert "SOCIAL_PRESENCE" in _codes(fp)


def test_analyzer_detects_missing_social():
    crawl = CrawlResult(url="x", status_code=200, title="ACME Trading Ltd",
                        text="ACME Trading Ltd " * 60, links=["/about", "/contact"],
                        emails=["info@acme.example"], ok=True)
    dom = DomainInfo(domain="x", age_days=2000, has_mx=True, has_tls=True)
    fp = analyze_footprint("ACME TRADING LTD", crawl, dom)
    assert "NO_SOCIAL_PRESENCE" in _codes(fp)


def test_footprint_pipeline_persists(monkeypatch):
    from app import models  # noqa: F401
    from app.db import Base, SessionLocal, engine
    from app.models import Business, RiskSignal, WebIntel
    from app.webintel import pipeline as pl
    from app.webintel.crawler.mock import MockCrawler
    from app.webintel.summarizer.template import TemplateSummarizer

    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(
        pl, "get_domain_info",
        lambda url: DomainInfo(domain="acme-trading.example", age_days=2000,
                               has_mx=True, has_tls=True),
    )
    monkeypatch.setattr(pl, "discover_socials", lambda name: {})
    monkeypatch.setattr(pl, "company_profile", lambda *a, **k: None)

    db = SessionLocal()
    try:
        biz = Business(legal_name="ACME TRADING LTD",
                       website="https://acme-trading.example")
        db.add(biz)
        db.commit()
        db.refresh(biz)

        intel = pl.run_footprint_pipeline(db, biz, MockCrawler(), TemplateSummarizer())
        assert intel.verdict == "real"
        assert intel.legitimacy_score >= 90
        assert db.get(WebIntel, intel.id) is not None
        sigs = db.query(RiskSignal).filter_by(
            business_id=biz.id, source="web_intel").all()
        assert all(s.source == "web_intel" for s in sigs)
    finally:
        db.close()


def test_footprint_without_website_is_context_only(monkeypatch):
    """No website + none discovered -> context-only 'unknown', not an error/ghost."""
    from app.db import Base, SessionLocal, engine
    from app.models import Business, WebIntel
    from app.webintel import pipeline as pl
    from app.webintel.crawler.mock import MockCrawler
    from app.webintel.summarizer.template import TemplateSummarizer

    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(pl, "discover_website", lambda name, raw: None)
    monkeypatch.setattr(pl, "discover_socials", lambda name: {})
    monkeypatch.setattr(pl, "company_profile", lambda *a, **k: None)

    db = SessionLocal()
    try:
        biz = Business(legal_name="NO SITE LLC")  # no website
        db.add(biz)
        db.commit()
        db.refresh(biz)
        intel = pl.run_footprint_pipeline(db, biz, MockCrawler(), TemplateSummarizer())
        assert intel.verdict == "unknown"
        assert intel.website_url is None
        assert intel.legitimacy_score == 50
    finally:
        db.close()
