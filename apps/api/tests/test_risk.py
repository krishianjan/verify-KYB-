"""Tests for Feature 3: combined risk engine + queue + analyst actions.

Run from apps/api with::  python -m pytest tests/test_risk.py -v
"""
from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="verifykyb-test-risk-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["REGISTRY_PROVIDER"] = "mock"
os.environ["ENABLE_VECTOR"] = "false"
os.environ["ENABLE_ENRICHMENT"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.risk.engine import compute_risk


# ---- pure risk-engine unit tests -------------------------------------------

def test_clean_business_is_low_risk():
    r = compute_risk(identity_confidence=1.0, web_legitimacy=95,
                     signal_codes=["NO_VERIFIED_UBO"], officers_count=2,
                     psc_supported=False)
    assert r.rating == "low"
    assert r.decision == "approve"
    assert r.overall_risk <= 30


def test_dissolved_company_hard_stops_to_high():
    r = compute_risk(identity_confidence=0.4, web_legitimacy=None,
                     signal_codes=["COMPANY_INACTIVE"], officers_count=1,
                     psc_supported=True)
    assert r.rating == "high"
    assert r.decision == "reject"
    assert r.overall_risk >= 80
    assert "COMPANY_INACTIVE" in r.reason_codes


def test_cloned_site_triggers_manual_review_not_reject():
    # Clones are disambiguated by an analyst, not auto-rejected.
    r = compute_risk(identity_confidence=0.9, web_legitimacy=80,
                     signal_codes=["CLONED_SITE_MATCH"], officers_count=1,
                     psc_supported=False)
    assert r.decision == "review"
    assert r.rating == "medium"
    assert "CLONED_SITE_MATCH" in r.reason_codes


def test_no_state_routes_to_review_not_reject():
    r = compute_risk(identity_confidence=0.3, web_legitimacy=None,
                     signal_codes=["REGISTRY_STATE_NOT_PROVIDED"], officers_count=0,
                     psc_supported=False)
    assert r.decision == "review"
    assert r.rating == "medium"


def test_weighted_medium_risk():
    r = compute_risk(identity_confidence=0.55, web_legitimacy=40,
                     signal_codes=[], officers_count=1, psc_supported=False)
    assert r.rating in ("medium", "high")
    assert "identity" in r.category_scores
    assert "footprint" in r.category_scores


# ---- queue + analyst action integration ------------------------------------

@pytest.fixture()
def client():
    from app import models  # noqa: F401
    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def test_queue_and_actions_flow(client: TestClient):
    created = client.post(
        "/kyb/cases", json={"legal_name": "ACME TRADING LTD", "company_number": "01234567"}
    ).json()
    cid = created["business"]["id"]
    assert created["risk"] is not None

    listing = client.get("/kyb/cases?limit=10").json()
    assert listing["total"] >= 1
    assert any(it["id"] == cid for it in listing["items"])

    # analyst approves
    act = client.post(f"/kyb/cases/{cid}/actions",
                      json={"action": "approve", "notes": "ok", "actor": "alice"})
    assert act.status_code == 200
    assert act.json()["status"] == "approved"

    # invalid action rejected
    bad = client.post(f"/kyb/cases/{cid}/actions", json={"action": "nuke"})
    assert bad.status_code == 400

    # recompute risk endpoint
    rk = client.post(f"/kyb/cases/{cid}/risk")
    assert rk.status_code == 200
    assert rk.json()["rating"] in ("low", "medium", "high")
