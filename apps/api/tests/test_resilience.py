"""Feature 1/3/4 resilience tests: registry outages and missing matches must
NEVER become an adverse (reject) verdict, and the LLM layer must degrade safely.

Run from apps/api with::  python -m pytest tests/test_resilience.py -v
"""
from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="verifykyb-test-resilience-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["REGISTRY_PROVIDER"] = "mock"
os.environ["ENABLE_VECTOR"] = "false"
os.environ["ENABLE_ENRICHMENT"] = "false"  # keep create_case offline (no fallback)

import pytest
from fastapi.testclient import TestClient

from app.registry.base import RegistryAdapter, RegistryUnavailable
from app.risk.engine import compute_risk


# ---- risk-engine invariants ------------------------------------------------

def test_registry_outage_is_not_a_reject():
    # Identity unknown (None) + strong web presence + the outage signal.
    r = compute_risk(
        identity_confidence=None, web_legitimacy=95,
        signal_codes=["REGISTRY_UNAVAILABLE"], officers_count=0,
        psc_supported=False, ownership_known=False, web_presence_score=95,
    )
    assert r.decision == "review"      # never reject
    assert r.rating == "medium"
    assert "identity" not in r.category_scores   # unknown, not scored as risk


def test_registry_not_found_routes_to_review_not_reject():
    r = compute_risk(
        identity_confidence=None, web_legitimacy=80,
        signal_codes=["REGISTRY_NOT_FOUND"], officers_count=0,
        psc_supported=False, ownership_known=False, web_presence_score=80,
    )
    assert r.decision == "review"
    assert r.rating != "high"


def test_no_ownership_penalty_when_registry_absent():
    # ownership_known=False -> 0 officers must NOT become WEAK_OWNERSHIP_DATA.
    r = compute_risk(
        identity_confidence=None, web_legitimacy=70, signal_codes=[],
        officers_count=0, psc_supported=False, ownership_known=False,
    )
    assert "ownership" not in r.category_scores
    assert "WEAK_OWNERSHIP_DATA" not in r.reason_codes


def test_web_only_case_never_auto_approves():
    # Even a near-perfect web presence cannot auto-approve without the registry.
    r = compute_risk(
        identity_confidence=None, web_legitimacy=99,
        signal_codes=["REGISTRY_NOT_FOUND"], officers_count=3,
        psc_supported=False, ownership_known=False, web_presence_score=99,
    )
    assert r.decision != "approve"


def test_real_registry_confirmed_still_approves():
    # Guardrail didn't break the happy path.
    r = compute_risk(
        identity_confidence=1.0, web_legitimacy=95,
        signal_codes=["NO_VERIFIED_UBO"], officers_count=2,
        psc_supported=False, ownership_known=True,
    )
    assert r.decision == "approve"


# ---- LLM JSON parsing degrades safely --------------------------------------

def test_llm_json_parser_handles_fences_and_junk():
    from app.llm import _parse_json_object

    assert _parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert _parse_json_object('noise {"b": 2} trailing') == {"b": 2}
    assert _parse_json_object("not json at all") is None
    assert _parse_json_object("[1,2,3]") is None   # not an object


# ---- search provider falls back to free DDG --------------------------------

def test_search_factory_falls_back_to_ddg(monkeypatch):
    from app.webintel.search import factory
    from app.webintel.search.chain import ChainSearch
    from app.webintel.search.ddg import DdgSearch

    # A named provider with no key is dropped; DDG is always the final fallback.
    monkeypatch.setattr(factory.settings, "search_provider", "crawl4ai")
    monkeypatch.setattr(factory.settings, "crawl4ai_api_key", None)
    monkeypatch.setattr(factory.settings, "firecrawl_api_key", None)
    provider = factory.get_search_provider()
    assert isinstance(provider, ChainSearch)
    assert any(isinstance(p, DdgSearch) for p in provider._providers)


# ---- end-to-end: an outage yields PENDING, not F0/reject -------------------

class _UnavailableAdapter(RegistryAdapter):
    source = "fake_unavailable"
    supports_psc = False
    requires_subdivision = False

    def search(self, query, jurisdiction):
        raise RegistryUnavailable("Monthly usage hard limit exceeded")

    def get_company(self, company_number):
        raise RegistryUnavailable("Monthly usage hard limit exceeded")

    def get_officers(self, company_number):
        return []

    def get_psc(self, company_number):
        return []


@pytest.fixture()
def client():
    from app import models  # noqa: F401
    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def test_outage_case_is_pending_not_rejected(client: TestClient, monkeypatch):
    from app import cases

    monkeypatch.setattr(cases, "get_registry_adapter", _UnavailableAdapter)
    created = client.post(
        "/kyb/cases", json={"legal_name": "Apple Inc", "state": "CA"}
    ).json()
    cid = created["business"]["id"]

    assert created["assessment"]["confidence"] is None        # not-checked
    assert created["business"]["status"] == "manual_review"   # not rejected
    assert created["risk"]["decision"] == "review"            # not reject
    codes = {s["code"] for s in created["risk_signals"]}
    assert "REGISTRY_UNAVAILABLE" in codes

    report = client.get(f"/kyb/cases/{cid}/report").json()
    assert report["verified"] == "pending"
    kyb = next(s for s in report["scores"] if s["type"] == "kyb")
    assert kyb["rating"] == "PENDING" and kyb["score"] is None
    assert report["decision"]["action"] == "provisional_review"
    assert any("registry" in w.lower() for w in report["warnings"])
