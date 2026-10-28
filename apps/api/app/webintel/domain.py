"""Free, local domain intelligence: WHOIS age, DNS (A/MX/NS), TLS presence.

Every lookup is best-effort and degrades gracefully — a failure sets the field
to None rather than raising, so a flaky network never breaks the pipeline.
"""
from __future__ import annotations

import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import urlparse

from .dto import DomainInfo


def _host(url: str) -> str | None:
    if not url:
        return None
    target = url if url.startswith(("http://", "https://")) else f"https://{url}"
    host = urlparse(target).hostname
    if host and host.startswith("www."):
        host = host[4:]
    return host



def get_domain_info(url: str) -> DomainInfo:
    host = _host(url)
    if not host:
        return DomainInfo(error="could not parse hostname")

    info = DomainInfo(domain=host)
    _fill_dns(host, info)
    info.has_tls = _check_tls(host)
    _fill_whois(host, info)
    if info.age_days is None:
        _fill_rdap(host, info)   # more reliable than WHOIS scraping
    return info


def _fill_dns(host: str, info: DomainInfo) -> None:
    try:
        import dns.resolver

        resolver = dns.resolver.Resolver()
        resolver.lifetime = 5.0
        try:
            resolver.resolve(host, "A")
            info.has_a = True
        except Exception:  # noqa: BLE001
            info.has_a = False
        try:
            resolver.resolve(host, "MX")
            info.has_mx = True
        except Exception:  # noqa: BLE001
            info.has_mx = False
        try:
            ns = resolver.resolve(host, "NS")
            info.nameservers = sorted(str(r).rstrip(".") for r in ns)[:10]
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        info.error = f"dns: {exc}"



def _check_tls(host: str) -> bool | None:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=host):
                return True
    except Exception:  # noqa: BLE001
        return False


def _fill_rdap(host: str, info: DomainInfo) -> None:
    """RDAP registration date (free, structured, no key)."""
    try:
        import httpx

        resp = httpx.get(f"https://rdap.org/domain/{host}", timeout=8,
                         follow_redirects=True)
        if resp.status_code != 200:
            return
        data = resp.json()
        for ev in data.get("events", []):
            if ev.get("eventAction") == "registration" and ev.get("eventDate"):
                created = datetime.fromisoformat(
                    ev["eventDate"].replace("Z", "+00:00")
                )
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                info.created = created.date().isoformat()
                info.age_days = (datetime.now(timezone.utc) - created).days
                if not info.registrar:
                    for ent in data.get("entities", []):
                        if "registrar" in (ent.get("roles") or []):
                            info.registrar = _rdap_name(ent)
                return
    except Exception:  # noqa: BLE001
        pass


def _rdap_name(entity: dict) -> str | None:
    try:
        for item in entity.get("vcardArray", [[], []])[1]:
            if item[0] == "fn":
                return item[3]
    except Exception:  # noqa: BLE001
        pass
    return None


def _fill_whois(host: str, info: DomainInfo) -> None:
    try:
        import whois

        data = whois.whois(host)
        created = data.creation_date
        if isinstance(created, list):
            created = created[0] if created else None
        if isinstance(created, datetime):
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            info.created = created.date().isoformat()
            info.age_days = (datetime.now(timezone.utc) - created).days
        registrar = data.registrar
        if isinstance(registrar, list):
            registrar = registrar[0] if registrar else None
        info.registrar = registrar
    except Exception as exc:  # noqa: BLE001
        if not info.error:
            info.error = f"whois: {exc}"
