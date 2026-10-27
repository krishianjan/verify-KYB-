"""
FROZEN CONTRACT — the registry adapter interface.

Every jurisdiction/provider implements this. The pipeline is written against
this ABC and never against a concrete provider. All methods are SYNCHRONOUS.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .dto import (
    RegistryCompanyProfile,
    RegistryCompanySummary,
    RegistryOfficer,
    RegistryPSC,
)


class RegistryError(Exception):
    """Raised for unrecoverable registry failures (auth, bad request, parse)."""


class RegistryUnavailable(RegistryError):
    """Raised when the registry could not be reached or refused service for a
    transient reason (quota/usage limit, rate limit, timeout, network, 5xx).

    This is deliberately distinct from a hard ``RegistryError`` and from a
    clean "no match": it means we DID NOT get to check the entity. The pipeline
    treats it as *not-checked* (confidence unknown, route to review + web
    presence), never as evidence the business is fake.
    """


class RegistryAdapter(ABC):
    #: short identifier stored on evidence records, e.g. "companies_house"
    source: str = "unknown"

    #: Whether this jurisdiction exposes beneficial-owner / PSC data. US SoS
    #: registries do not, so absence of UBO there is a data gap, not a red flag.
    supports_psc: bool = True

    #: Whether a subdivision (e.g. US state) is required to search efficiently.
    #: When True and none is given, the pipeline skips the registry and routes
    #: to web-presence review instead of a slow nationwide sweep.
    requires_subdivision: bool = False

    @abstractmethod
    def search(self, query: str, jurisdiction: str) -> list[RegistryCompanySummary]:
        """Search companies by free-text name. Return [] if none."""

    @abstractmethod
    def get_company(self, company_number: str) -> RegistryCompanyProfile | None:
        """Fetch a full profile by number. Return None if not found."""

    @abstractmethod
    def get_officers(self, company_number: str) -> list[RegistryOfficer]:
        """Return active+resigned officers. Return [] if none/unsupported."""

    @abstractmethod
    def get_psc(self, company_number: str) -> list[RegistryPSC]:
        """Return persons with significant control. Return [] if none/unsupported."""
