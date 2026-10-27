"""Discover a candidate website for a business when none was provided.

Order: (1) a domain from the registry's business email, (2) a best-effort
DuckDuckGo search on the legal name. Returns a URL or None; always safe.
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

import httpx

_GENERIC_EMAIL = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com",
    "icloud.com", "proton.me", "protonmail.com", "live.com", "msn.com",
}
# Substrings of hosts we never treat as a business's own site.
_SKIP_HOSTS = (
    "facebook", "linkedin", "twitter", "x.com", "instagram", "youtube",
    "wikipedia", "bloomberg", "crunchbase", "dnb.com", "opencorporates",
    "yelp", "glassdoor", "indeed", "duckduckgo", "google", "bing.com",
)
_UA = "verifyKYB-footprint/1.0 (+https://example.com; compliance verification)"


def discover_website(legal_name: str, registry_raw: dict | None) -> str | None:
    dom = _domain_from_email(registry_raw)
    if dom:
        return f"https://{dom}"
    return _duckduckgo_first_site(legal_name)


def _domain_from_email(registry_raw: dict | None) -> str | None:
    email = (registry_raw or {}).get("businessEmail")
    if isinstance(email, str) and "@" in email:
        domain = email.split("@")[-1].strip().lower()
        if domain and domain not in _GENERIC_EMAIL and "." in domain:
            return domain
    return None


_SOCIAL_HOSTS = {
    "linkedin": "linkedin.com/company",
    "x": "x.com",
    "twitter": "twitter.com",
    "instagram": "instagram.com",
    "facebook": "facebook.com",
}


_LINK_HOSTS = {
    "linkedin": "linkedin.com", "x": "x.com", "twitter": "twitter.com",
    "instagram": "instagram.com", "facebook": "facebook.com", "youtube": "youtube.com",
}


def socials_from_links(links: list[str]) -> dict[str, str]:
    """Extract social profile URLs already present on the crawled site."""
    out: dict[str, str] = {}
    for link in links or []:
        low = (link or "").lower()
        for plat, host in _LINK_HOSTS.items():
            if host in low:
                key = "x" if plat == "twitter" else plat
                url = link if link.startswith("http") else "https://" + link.lstrip("/")
                out.setdefault(key, url)
    return out


def discover_socials(legal_name: str) -> dict[str, str]:
    """Search the web for the company's social profiles. {platform: url}."""
    found: dict[str, str] = {}
    if not legal_name:
        return found
    for platform, host in _SOCIAL_HOSTS.items():
        key = "x" if platform == "twitter" else platform
        if key in found:
            continue
        url = _duckduckgo_site_hit(legal_name, host)
        if url:
            found[key] = url
    return found


def _duckduckgo_site_hit(name: str, host: str) -> str | None:
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": f'"{name}" site:{host}'},
            headers={"User-Agent": _UA},
            timeout=12,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        for enc in re.findall(r'uddg=([^&"]+)', resp.text):
            url = unquote(enc)
            if host.split("/")[0] in (urlparse(url).hostname or "").lower():
                return url
        return None
    except Exception:  # noqa: BLE001
        return None


def _duckduckgo_first_site(query: str) -> str | None:
    if not query:
        return None
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": _UA},
            timeout=15,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        # Result links look like //duckduckgo.com/l/?uddg=<encoded target>&...
        for enc in re.findall(r'uddg=([^&"]+)', resp.text):
            url = unquote(enc)
            host = (urlparse(url).hostname or "").lower()
            if not host or any(s in host for s in _SKIP_HOSTS):
                continue
            if url.startswith("http"):
                return url
        return None
    except Exception:  # noqa: BLE001
        return None
