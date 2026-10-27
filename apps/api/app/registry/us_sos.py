"""
US Secretary of State registry adapter (via the Apify
`clearpath/us-business-entity-search` actor).

Covers all 50 states + DC. One actor run per lookup; we narrow to a single
state when the case carries one (jurisdiction "us-ca" -> state "CA"), which is
dramatically cheaper than the default 51-state sweep.

The actor returns FULL entity records (not search rows), so `search()` caches
them on the instance and `get_company()`/`get_officers()` read from that cache
within the same case. US registries publish no beneficial-ownership data, so
`supports_psc = False` and `get_psc()` always returns [].
"""
from __future__ import annotations

import time

from ..config import settings
from .base import RegistryAdapter, RegistryError, RegistryUnavailable
from .dto import (
    RegistryCompanyProfile,
    RegistryCompanySummary,
    RegistryOfficer,
    RegistryPSC,
)

# Substrings in an Apify failure that mean "transient / we never got to check",
# not "this business is fake". These route the case to review + web presence.
_TRANSIENT_MARKERS = (
    "usage hard limit", "monthly usage", "hard limit", "limit exceeded",
    "quota", "rate limit", "too many requests", "429", "timeout", "timed out",
    "connection", "temporarily", "unavailable", "503", "502", "504",
    "did not succeed",
)


def _is_transient(message: str) -> bool:
    low = (message or "").lower()
    return any(tok in low for tok in _TRANSIENT_MARKERS)

# status free-text -> canonical vocabulary the matching engine understands.
_BAD_STATUS = (
    "dissolved", "inactive", "forfeited", "revoked", "terminated", "expired",
    "withdrawn", "cancel", "delinquent", "suspend", "void", "merged", "closed",
    "defunct", "administratively", "permanently",
)
_GOOD_STATUS = (
    "active", "good standing", "exists", "current", "valid", "registered",
    "live", "in existence",
)


def _norm_status(raw) -> str | None:
    if not raw:
        return None
    s = str(raw).lower()
    if any(tok in s for tok in _BAD_STATUS):
        return "inactive"
    if any(tok in s for tok in _GOOD_STATUS):
        return "active"
    return None


def _addr(obj) -> str | None:
    if not obj:
        return None
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        return None
    if obj.get("full"):
        return obj["full"]
    parts = [obj.get(k) for k in ("street", "city", "state", "zip", "country")]
    joined = ", ".join(str(p) for p in parts if p)
    return joined or None


class UsSosAdapter(RegistryAdapter):
    source = "us_sos"
    supports_psc = False
    requires_subdivision = True

    def __init__(self) -> None:
        if not settings.apify_api_token:
            raise RegistryError("APIFY_API_TOKEN is not set.")
        # Imported here so the app boots even if apify-client isn't installed.
        from apify_client import ApifyClient

        self._client = ApifyClient(settings.apify_api_token)
        self._actor = settings.apify_us_sos_actor
        self._cache: dict[str, dict] = {}  # entityId -> raw record (per case)

    # -- RegistryAdapter -----------------------------------------------------

    def search(self, query: str, jurisdiction: str) -> list[RegistryCompanySummary]:
        state = _state_from_jurisdiction(jurisdiction)
        run_input: dict = {
            "companyName": query,
            "matchMode": settings.apify_match_mode,
            "maxResultsPerState": settings.apify_max_results_per_state,
            "includeDetails": True,
            "includeLiens": settings.apify_include_liens,
        }
        if state:
            run_input["states"] = [state]

        run = self._call_actor(run_input)

        status = _run_field(run, "status", "status")
        if run is None or status != "SUCCEEDED":
            # A non-SUCCEEDED run means we didn't get a usable answer; treat it
            # as transient (not-checked) rather than "business is fake".
            raise RegistryUnavailable(f"Apify run did not succeed: {status}")

        ds_id = _run_field(run, "default_dataset_id", "defaultDatasetId")
        items = list(self._client.dataset(ds_id).iterate_items())

        summaries: list[RegistryCompanySummary] = []
        for it in items:
            eid = it.get("entityId")
            if not eid:
                continue
            # When a state was requested, drop stray cross-state rows.
            if state and (it.get("state") or "").upper() != state:
                continue
            self._cache[str(eid)] = it
            summaries.append(
                RegistryCompanySummary(
                    company_number=str(eid),
                    company_name=it.get("legalName") or "",
                    company_status=_norm_status(it.get("status")),
                    address=_addr(it.get("principalAddress")),
                    source=self.source,
                )
            )
        return summaries

    def _call_actor(self, run_input: dict):
        """Run the Apify actor with a bounded retry. Classify failures:
        transient (quota/limit/network) -> RegistryUnavailable; everything else
        -> RegistryError."""
        attempts = max(1, settings.registry_retry + 1)
        last_exc: Exception | None = None
        for i in range(attempts):
            try:
                return self._client.actor(self._actor).call(run_input=run_input)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if _is_transient(str(exc)):
                    # Quota/limit won't clear on retry; bail out immediately.
                    if any(t in str(exc).lower()
                           for t in ("limit", "quota", "usage")):
                        raise RegistryUnavailable(
                            f"Apify actor call failed: {exc}") from exc
                    if i < attempts - 1:
                        time.sleep(0.5 * (i + 1))
                        continue
                    raise RegistryUnavailable(
                        f"Apify actor call failed: {exc}") from exc
                raise RegistryError(f"Apify actor call failed: {exc}") from exc
        # Exhausted retries on a transient error.
        raise RegistryUnavailable(f"Apify actor call failed: {last_exc}")

    def get_company(self, company_number: str) -> RegistryCompanyProfile | None:
        it = self._cache.get(str(company_number))
        if it is None:
            return None
        agent = it.get("registeredAgent")
        agent_addr = agent.get("address") if isinstance(agent, dict) else None
        return RegistryCompanyProfile(
            company_number=str(it.get("entityId")),
            company_name=it.get("legalName") or "",
            company_status=_norm_status(it.get("status")),
            company_type=it.get("entityType"),
            incorporation_date=_iso_date(it.get("formationDate")),
            registered_address=_addr(it.get("principalAddress")) or _addr(agent_addr),
            source=self.source,
            source_uri=it.get("sourceUrl"),
            raw=it,
        )

    def get_officers(self, company_number: str) -> list[RegistryOfficer]:
        it = self._cache.get(str(company_number))
        if it is None:
            return []
        officers: list[RegistryOfficer] = []
        for off in it.get("officers") or []:
            if isinstance(off, str):
                officers.append(RegistryOfficer(name=off, raw={"raw": off}))
                continue
            if not isinstance(off, dict):
                continue
            officers.append(
                RegistryOfficer(
                    name=off.get("name") or "",
                    role=off.get("title") or off.get("role"),
                    appointed_on=None,
                    resigned_on=None,
                    nationality=None,
                    raw=off,
                )
            )
        return officers

    def get_psc(self, company_number: str) -> list[RegistryPSC]:
        # US registries do not publish beneficial ownership. See supports_psc.
        return []


def _run_field(run, attr: str, key: str):
    """Read a field from an Apify run result, which may be a dict or an object
    depending on the installed apify-client version."""
    if run is None:
        return None
    if isinstance(run, dict):
        return run.get(key)
    return getattr(run, attr, None)


def _state_from_jurisdiction(jurisdiction: str | None) -> str | None:
    """'us-ca' -> 'CA'; 'us' / None -> None (triggers all-states fallback)."""
    if not jurisdiction:
        return None
    parts = jurisdiction.strip().lower().split("-", 1)
    if len(parts) == 2 and parts[1]:
        return parts[1].upper()
    return None


def _iso_date(value: str | None) -> str | None:
    if not value:
        return None
    return str(value)[:10]
