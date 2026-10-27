"""
FROZEN CONTRACT — do not change field names/types without updating the core.

These are the normalized shapes every registry adapter must return, regardless
of the upstream registry's native format. Adapters translate provider JSON ->
these DTOs. The matching engine and pipeline depend only on these.
"""
from __future__ import annotations

from pydantic import BaseModel


class RegistryCompanySummary(BaseModel):
    """A single search hit."""

    company_number: str
    company_name: str
    company_status: str | None = None          # active | dissolved | liquidation | ...
    address: str | None = None
    source: str                                # e.g. "companies_house"


class RegistryCompanyProfile(BaseModel):
    """Full company profile."""

    company_number: str
    company_name: str
    company_status: str | None = None
    company_type: str | None = None
    incorporation_date: str | None = None      # ISO date string "YYYY-MM-DD"
    registered_address: str | None = None
    source: str
    source_uri: str | None = None
    raw: dict = {}                             # full upstream payload for evidence


class RegistryOfficer(BaseModel):
    """A director / officer."""

    name: str
    role: str | None = None
    appointed_on: str | None = None
    resigned_on: str | None = None
    nationality: str | None = None
    raw: dict = {}


class RegistryPSC(BaseModel):
    """Person with Significant Control (UBO)."""

    name: str
    kind: str | None = None
    natures_of_control: list[str] = []
    notified_on: str | None = None
    ceased_on: str | None = None
    raw: dict = {}
