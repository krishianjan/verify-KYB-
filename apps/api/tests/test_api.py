"""HTTP-level API tests for the KYB service (mock registry).

Run from apps/api with::  python -m pytest tests/ -v

The API returns a NESTED CaseOut:
    {
      "business":   {"id", "status", ...},
      "assessment": {"confidence", "decision", "mismatches":[...]},
      "directors":  [...],
      "beneficial_owners": [...],
      "risk_signals": [{"code","severity",...}],
    }
"""
from __future__ import annotations

import os
import tempfile

# Point DB at a throwaway sqlite file BEFORE importing the app. Env vars take
# precedence over the repo .env in pydantic-settings.
_TMP = tempfile.mkdtemp(prefix="verifykyb-test-api-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["REGISTRY_PROVIDER"] = "mock"
os.environ["ENABLE_VECTOR"] = "false"  # keep tests offline/fast (no embedding model)
os.environ["ENABLE_ENRICHMENT"] = "false"  # no live web search/LLM in unit tests

import pytest
from fastapi.testclient import TestClient


def _decision(body: dict) -> str:
    return str(body["assessment"]["decision"]).lower()


def _confidence(body: dict) -> float:
    return float(body["assessment"]["confidence"])


def _signal_codes(body: dict) -> list[str]:
    return [s["code"] for s in body.get("risk_signals", [])]


@pytest.fixture()
def client():
    from app import models  # noqa: F401  (register models on Base.metadata)
    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:  # `with` is mandatory: lifespan sets up tables
        yield c


@pytest.fixture()
def acme_case(client: TestClient) -> dict:
    resp = client.post(
        "/kyb/cases",
        json={"legal_name": "ACME TRADING LTD", "company_number": "01234567"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_health_returns_200(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_acme_auto_approves_with_full_confidence(acme_case: dict):
    assert _decision(acme_case) == "auto_approve"
    assert _confidence(acme_case) >= 0.95
    assert len(acme_case["directors"]) == 1
    assert len(acme_case["beneficial_owners"]) == 1
    # Feature 3: every case carries a combined risk score.
    assert acme_case["risk"] is not None
    assert acme_case["risk"]["rating"] == "low"


def test_ghost_business_rejects_inactive_and_no_psc(client: TestClient):
    resp = client.post(
        "/kyb/cases",
        json={"legal_name": "GHOST HOLDINGS LTD", "company_number": "09999999"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert _decision(body) == "reject"
    codes = _signal_codes(body)
    assert "COMPANY_INACTIVE" in codes, codes
    assert "NO_PSC" in codes, codes


def test_wrong_legal_name_rejects_on_mismatch(client: TestClient):
    resp = client.post(
        "/kyb/cases",
        json={"legal_name": "TOTALLY DIFFERENT NAME INC", "company_number": "01234567"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert _decision(body) == "reject"
    mismatch_fields = [m["field"] for m in body["assessment"]["mismatches"]]
    assert "legal_name" in mismatch_fields, mismatch_fields


def test_get_case_round_trips(client: TestClient, acme_case: dict):
    case_id = acme_case["business"]["id"]
    resp = client.get(f"/kyb/cases/{case_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["business"]["id"] == case_id
    assert _decision(body) == "auto_approve"
    assert _confidence(body) == pytest.approx(_confidence(acme_case), abs=1e-9)


def test_missing_case_returns_404(client: TestClient):
    assert client.get("/kyb/cases/nonexistent-xyz").status_code == 404


def test_report_is_baselayer_shaped(client: TestClient, acme_case: dict):
    cid = acme_case["business"]["id"]
    r = client.get(f"/kyb/cases/{cid}/report")
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["verified"] is True
    assert {s["type"] for s in rep["scores"]} == {"kyb", "risk"}
    for s in rep["scores"]:
        assert s["rating"] in ("A", "B", "C", "D", "F")
        assert 0 <= s["score"] <= 100
    assert rep["business_name_match"] == "EXACT"   # ACME exact name
    assert rep["decision"]["action"] == "auto_approve"
    assert "reasoning" in rep["decision"]
    assert "registry" in rep["sources"]
