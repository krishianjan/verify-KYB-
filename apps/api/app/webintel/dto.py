"""Normalized shapes for the digital-footprint pipeline (Feature 2)."""
from __future__ import annotations

from pydantic import BaseModel


class CrawlResult(BaseModel):
    url: str
    final_url: str | None = None
    status_code: int | None = None
    title: str | None = None
    meta_description: str | None = None
    text: str = ""                 # extracted readable text
    html_len: int = 0
    links: list[str] = []
    emails: list[str] = []
    phones: list[str] = []
    source: str = "unknown"        # which crawler produced this
    ok: bool = False               # True only if usable content was fetched
    error: str | None = None
    raw: dict = {}


class DomainInfo(BaseModel):
    domain: str | None = None
    created: str | None = None     # ISO date string if known
    age_days: int | None = None
    registrar: str | None = None
    nameservers: list[str] = []
    has_a: bool | None = None
    has_mx: bool | None = None
    has_tls: bool | None = None
    error: str | None = None


class FootprintSignal(BaseModel):
    code: str
    severity: str                  # info | low | medium | high
    weight: float
    detail: str


class FootprintResult(BaseModel):
    legitimacy_score: int          # 0..100 (higher = more legitimate)
    verdict: str                   # real | thin | inconsistent | ghost | unknown
    signals: list[FootprintSignal] = []
