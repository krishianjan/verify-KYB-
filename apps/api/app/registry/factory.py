from __future__ import annotations

from ..config import settings
from .base import RegistryAdapter
from .mock import MockRegistryAdapter


def get_registry_adapter() -> RegistryAdapter:
    provider = (settings.registry_provider or "mock").lower()

    if provider == "mock":
        return MockRegistryAdapter()

    if provider == "companies_house":
        # Imported lazily so the app still boots if the adapter file isn't
        # present yet.
        from .companies_house import CompaniesHouseAdapter

        return CompaniesHouseAdapter()

    if provider == "us_sos":
        from .us_sos import UsSosAdapter

        return UsSosAdapter()

    raise ValueError(f"Unknown REGISTRY_PROVIDER: {provider!r}")
