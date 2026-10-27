"""Web-intelligence enrichment (Feature 4).

When the registry can't confirm an entity, gather what the open web knows:
search -> scrape top pages to text/markdown -> have the LLM parse ONE structured,
evidence-grounded profile (description, industry, HQ/locations, team size,
founders/executives, socials, funding/news). Evidence-only: the model is told to
write "not found" rather than guess, and never to estimate financial figures.

Pure data gathering + structuring. It makes no risk decision — that stays in the
deterministic engine; see judge.py for the complementary web-presence score.
"""
from __future__ import annotations

import json
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ..config import settings
from ..llm import openrouter_json
from .crawler import WebCrawler
from .discover import _SKIP_HOSTS
from .search import SearchProvider

# Hosts worth keeping even though they're "aggregators": they carry real,
# citable facts (news, filings, profiles) for enrichment.
_KEEP_HOSTS = (
    "crunchbase", "bloomberg", "reuters", "techcrunch", "forbes", "wsj",
    "linkedin", "sec.gov", "wikipedia", "prnewswire", "businesswire",
)


class FundingItem(BaseModel):
    round: str | None = None
    amount: str | None = None
    date: str | None = None
    investors: list[str] = []
    source: str | None = None


class NewsItem(BaseModel):
    title: str | None = None
    url: str | None = None
    date: str | None = None


class EnrichmentData(BaseModel):
    description: str | None = None
    industry: str | None = None
    hq: str | None = None
    locations: list[str] = []
    employee_range: str | None = None
    founded_year: str | None = None
    founders: list[str] = []
    executives: list[str] = []
    socials: dict = {}
    funding: list[FundingItem] = []
    recent_news: list[NewsItem] = []
    sources: list[str] = []
    llm_used: bool = False


_SYSTEM = (
    "You are a KYB research analyst. From the provided web excerpts about a "
    "company, extract a single factual profile. Use ONLY the given evidence. "
    "If a field is not supported by the evidence, use null or an empty list — "
    "never guess. Do NOT estimate revenue or financial figures. For funding or "
    "news items, include the source URL they came from. Keep text concise. "
    "Return a JSON object with keys: description, industry, hq, locations[], "
    "employee_range, founded_year, founders[], executives[], socials{}, "
    "funding[{round,amount,date,investors[],source}], "
    "recent_news[{title,url,date}]."
)


def _queries(legal_name: str) -> list[str]:
    n = legal_name.strip()
    qs = [
        n,
        f'"{n}" headquarters location',
        f'"{n}" number of employees',
        f'"{n}" founders OR CEO OR executives',
        f'"{n}" funding OR investment OR raised',
        f'"{n}" news',
    ]
    return qs[: settings.enrichment_max_queries]


def _usable_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    if any(k in host for k in _KEEP_HOSTS):
        return True
    return not any(s in host for s in _SKIP_HOSTS)


def enrich_company(
    legal_name: str,
    website: str | None,
    socials: dict[str, str],
    search: SearchProvider,
    crawler: WebCrawler,
    seed_text: str | None = None,
) -> EnrichmentData:
    # 1) Collect candidate URLs from targeted searches (+ the known website).
    urls: list[str] = []
    seen_hosts: set[str] = set()

    def _add(url: str, allow_any: bool = False) -> None:
        host = (urlparse(url).hostname or "").lower()
        if not host or host in seen_hosts:
            return
        if not allow_any and not _usable_host(url):
            return
        seen_hosts.add(host)
        urls.append(url)

    # Only queue the site for scraping if we don't already have its text.
    if website and not seed_text:
        _add(website, allow_any=True)
    for q in _queries(legal_name):
        for hit in search.search(q, max_results=3):
            _add(hit.url)
        if len(urls) >= settings.enrichment_max_pages:
            break

    urls = urls[: settings.enrichment_max_pages]

    # 2) Scrape each candidate to text/markdown; build a capped evidence bundle.
    sources: list[str] = []
    bundle: list[str] = []
    total = 0
    cap = settings.enrichment_char_cap
    if seed_text:
        chunk = seed_text[: cap // 2]
        bundle.append(f"SOURCE: {website or 'submitted site'}\n{chunk}")
        total += len(chunk)
        if website:
            sources.append(website)
    for url in urls:
        if total >= cap:
            break
        if url in sources:
            continue
        crawl = crawler.fetch(url)
        if not (crawl.ok and crawl.text):
            continue
        remaining = cap - total
        chunk = crawl.text[: min(3000, remaining)]
        bundle.append(f"SOURCE: {crawl.final_url or url}\n{chunk}")
        total += len(chunk)
        sources.append(url)

    if not bundle:
        return EnrichmentData(socials=dict(socials), sources=sources, llm_used=False)

    # 3) Structured extraction via the LLM (evidence-only; may be unavailable).
    evidence = {"legal_name": legal_name, "excerpts": "\n\n---\n\n".join(bundle)}
    parsed = openrouter_json(_SYSTEM, json.dumps(evidence),
                             max_tokens=1400, model=settings.judge_model)
    if not parsed:
        return EnrichmentData(socials=dict(socials), sources=sources, llm_used=False)

    data = _coerce(parsed)
    # Merge discovered socials (on-site/searched) under anything the LLM found.
    merged = dict(socials)
    merged.update({k: v for k, v in (data.socials or {}).items() if v})
    data.socials = merged
    data.sources = sources
    data.llm_used = True
    return data


def _coerce(parsed: dict) -> EnrichmentData:
    """Build EnrichmentData from loosely-typed LLM JSON, dropping bad rows."""
    def _list(key):
        v = parsed.get(key)
        return v if isinstance(v, list) else []

    funding = []
    for f in _list("funding"):
        if isinstance(f, dict):
            try:
                funding.append(FundingItem(**{
                    k: f.get(k) for k in
                    ("round", "amount", "date", "source")
                } | {"investors": f.get("investors") or []}))
            except Exception:  # noqa: BLE001
                continue
    news = []
    for n in _list("recent_news"):
        if isinstance(n, dict):
            try:
                news.append(NewsItem(title=n.get("title"), url=n.get("url"),
                                     date=n.get("date")))
            except Exception:  # noqa: BLE001
                continue
    socials = parsed.get("socials")
    return EnrichmentData(
        description=parsed.get("description"),
        industry=parsed.get("industry"),
        hq=parsed.get("hq"),
        locations=_list("locations"),
        employee_range=parsed.get("employee_range"),
        founded_year=(str(parsed["founded_year"])
                      if parsed.get("founded_year") is not None else None),
        founders=_list("founders"),
        executives=_list("executives"),
        socials=socials if isinstance(socials, dict) else {},
        funding=funding,
        recent_news=news,
    )
