"""Unit tests for the matching engine — no HTTP, no DB.

Run from apps/api with::  python -m pytest tests/test_engine.py -v

assess_identity(submitted, profile, officers, pscs, psc_supported=True) returns
an AssessmentResult(confidence, decision, matched_company_number, summary,
mismatches, signals).
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{tempfile.mkdtemp(prefix='verifykyb-test-engine-')}/test.db",
)

from app.matching import SubmittedBusiness, assess_identity
from app.registry.mock import MockRegistryAdapter


def _acme():
    """Canonical healthy profile + officers + pscs from the mock registry."""
    reg = MockRegistryAdapter()
    profile = reg.get_company("01234567")
    assert profile is not None
    return profile, reg.get_officers("01234567"), reg.get_psc("01234567")


def _codes(result) -> list[str]:
    return [s.code for s in result.signals]


def _severities(result, code: str) -> list[str]:
    return [s.severity for s in result.signals if s.code == code]


def test_perfect_match_auto_approves_at_full_confidence():
    profile, officers, pscs = _acme()
    submitted = SubmittedBusiness(
        legal_name=profile.company_name,
        company_number=profile.company_number,
        registered_address=profile.registered_address,
    )
    result = assess_identity(submitted, profile, officers, pscs)
    assert result.decision == "auto_approve"
    assert result.confidence >= 0.99, result.confidence


def test_dissolved_company_high_severity_inactive_and_caps_confidence():
    profile, officers, pscs = _acme()
    profile = profile.model_copy(update={"company_status": "dissolved"})
    submitted = SubmittedBusiness(
        legal_name=profile.company_name,
        company_number=profile.company_number,
    )
    result = assess_identity(submitted, profile, officers, pscs)
    assert "COMPANY_INACTIVE" in _codes(result), _codes(result)
    assert "high" in _severities(result, "COMPANY_INACTIVE")
    assert result.confidence <= 0.40, result.confidence
    assert result.decision != "auto_approve"


def test_missing_profile_is_unconfirmed_not_rejected():
    # A missing registry match means "unconfirmed", not proof of fraud. We route
    # to review with confidence=None (not-checked) and flag REGISTRY_NOT_FOUND,
    # rather than auto-rejecting on absence of a match.
    submitted = SubmittedBusiness(legal_name="NOWHERE LTD", company_number="00000000")
    result = assess_identity(submitted, None, [], [])
    assert result.decision == "manual_review"
    assert result.confidence is None
    assert "REGISTRY_NOT_FOUND" in _codes(result), _codes(result)


def test_mismatched_legal_name_rejects():
    profile, officers, pscs = _acme()
    submitted = SubmittedBusiness(
        legal_name="TOTALLY DIFFERENT NAME INC",
        company_number=profile.company_number,
    )
    result = assess_identity(submitted, profile, officers, pscs)
    assert "NAME_MISMATCH" in _codes(result), _codes(result)
    assert result.decision == "reject"


def test_us_no_psc_is_not_penalized_when_unsupported():
    """psc_supported=False -> NO_VERIFIED_UBO (info), not NO_PSC (penalty)."""
    profile, officers, _ = _acme()
    submitted = SubmittedBusiness(
        legal_name=profile.company_name,
        company_number=profile.company_number,
    )
    result = assess_identity(submitted, profile, officers, [], psc_supported=False)
    assert "NO_VERIFIED_UBO" in _codes(result), _codes(result)
    assert "NO_PSC" not in _codes(result)
