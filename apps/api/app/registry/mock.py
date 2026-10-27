"""
Offline mock adapter so the whole pipeline runs with zero API keys.

It fabricates deterministic, plausible registry data from the query so you can
exercise matching, scoring, decisions, and the API end-to-end today. Swap to
the real Companies House adapter by setting REGISTRY_PROVIDER=companies_house.
"""
from __future__ import annotations

import hashlib

from .base import RegistryAdapter
from .dto import (
    RegistryCompanyProfile,
    RegistryCompanySummary,
    RegistryOfficer,
    RegistryPSC,
)

# A few canned companies keyed by a normalized-ish name substring.
_CANNED: dict[str, dict] = {
    "acme": {
        "company_number": "01234567",
        "company_name": "ACME TRADING LTD",
        "company_status": "active",
        "company_type": "ltd",
        "incorporation_date": "2015-06-01",
        "registered_address": "1 Example Street, London, EC1A 1AA",
    },
    "ghost": {
        "company_number": "09999999",
        "company_name": "GHOST HOLDINGS LTD",
        "company_status": "dissolved",
        "company_type": "ltd",
        "incorporation_date": "2023-11-20",
        "registered_address": "Flat 2, 10 Nowhere Road, London, N1 1AA",
    },
}


def _synth_number(seed: str) -> str:
    h = hashlib.sha1(seed.lower().encode()).hexdigest()
    return str(int(h[:8], 16) % 100_000_000).zfill(8)


def _lookup(query: str) -> dict:
    q = query.lower()
    for key, data in _CANNED.items():
        if key in q:
            return data
    num = _synth_number(query)
    return {
        "company_number": num,
        "company_name": query.strip().upper(),
        "company_status": "active",
        "company_type": "ltd",
        "incorporation_date": "2019-03-15",
        "registered_address": "25 Market Place, Manchester, M1 1AA",
    }


class MockRegistryAdapter(RegistryAdapter):
    source = "mock"

    def search(self, query: str, jurisdiction: str) -> list[RegistryCompanySummary]:
        d = _lookup(query)
        return [
            RegistryCompanySummary(
                company_number=d["company_number"],
                company_name=d["company_name"],
                company_status=d["company_status"],
                address=d["registered_address"],
                source=self.source,
            )
        ]

    def get_company(self, company_number: str) -> RegistryCompanyProfile | None:
        for d in _CANNED.values():
            if d["company_number"] == company_number:
                return self._profile(d)
        # Unknown number: synthesize an active profile so number-based flows work.
        return self._profile(
            {
                "company_number": company_number,
                "company_name": f"COMPANY {company_number} LTD",
                "company_status": "active",
                "company_type": "ltd",
                "incorporation_date": "2019-03-15",
                "registered_address": "25 Market Place, Manchester, M1 1AA",
            }
        )

    def get_officers(self, company_number: str) -> list[RegistryOfficer]:
        return [
            RegistryOfficer(
                name="SMITH, John",
                role="director",
                appointed_on="2019-03-15",
                nationality="British",
            )
        ]

    def get_psc(self, company_number: str) -> list[RegistryPSC]:
        if company_number == _CANNED["ghost"]["company_number"]:
            return []  # ghost company => no PSC, triggers a risk signal
        return [
            RegistryPSC(
                name="SMITH, John",
                kind="individual-person-with-significant-control",
                natures_of_control=["ownership-of-shares-75-to-100-percent"],
                notified_on="2019-03-15",
            )
        ]

    def _profile(self, d: dict) -> RegistryCompanyProfile:
        return RegistryCompanyProfile(
            company_number=d["company_number"],
            company_name=d["company_name"],
            company_status=d["company_status"],
            company_type=d["company_type"],
            incorporation_date=d["incorporation_date"],
            registered_address=d["registered_address"],
            source=self.source,
            source_uri=None,
            raw=d,
        )
