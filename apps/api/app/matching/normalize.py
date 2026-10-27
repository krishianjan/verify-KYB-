"""Normalization and fuzzy similarity utilities for KYB matching.

Pure, deterministic helpers used by the matching engine to compare company
names and addresses. No I/O, no network access, no global mutable state.

``rapidfuzz`` is the preferred similarity backend; if it is unavailable the
module falls back to :mod:`difflib` so the functions still work.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

try:  # pragma: no cover - exercised indirectly in prod
    from rapidfuzz import fuzz as _rf

    def _token_set_ratio(a: str, b: str) -> float:
        return float(_rf.token_set_ratio(a, b))

    def _token_sort_ratio(a: str, b: str) -> float:
        return float(_rf.token_sort_ratio(a, b))

except ImportError:  # pragma: no cover - difflib fallback
    from difflib import SequenceMatcher

    def _ratio(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio() * 100.0

    def _token_set_ratio(a: str, b: str) -> float:
        ta = " ".join(sorted(a.split()))
        tb = " ".join(sorted(b.split()))
        return _ratio(ta, tb)

    def _token_sort_ratio(a: str, b: str) -> float:
        ta = " ".join(sorted(a.split()))
        tb = " ".join(sorted(b.split()))
        return _ratio(ta, tb)


__all__ = [
    "normalize_company_name",
    "company_name_similarity",
    "normalize_address",
    "address_similarity",
]


# ---------------------------------------------------------------------------
# Compiled regexes and lookup tables
# ---------------------------------------------------------------------------

_WS_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

# Trailing tokens stripped from a normalized company name. "and" is also
# stripped when it is trailing (e.g. "Smith and Co" -> "smith").
_COMPANY_TRAILING_TOKENS: frozenset[str] = frozenset(
    {
        # Common anglophone forms
        "ltd", "limited", "llc", "llp", "lp", "plc", "pllc",
        "inc", "incorporated", "corp", "corporation",
        "co", "company",
        # EU / EEA
        "gmbh", "sarl", "sas", "sa", "srl", "spa",
        "bv", "nv", "ag", "oy", "oyj", "ab", "as", "aps",
        "se", "kk", "kg", "sro",
        # APAC / MENA
        "pte", "pvt", "private", "pty", "sdn", "bhd",
        "dmcc", "fze", "fzco",
        # LATAM / Iberia
        "ltda", "sl", "slu", "eirl", "unipessoal",
        # Poland
        "spzoo", "zoo",
        # Conjunction that becomes meaningless when trailing
        "and",
    }
)

# UK address token abbreviations -> expanded long form.
_ADDRESS_ABBREV: dict[str, str] = {
    "st": "street", "str": "street",
    "rd": "road",
    "ave": "avenue", "av": "avenue",
    "blvd": "boulevard",
    "dr": "drive",
    "ln": "lane",
    "ct": "court",
    "pl": "place",
    "sq": "square",
    "hwy": "highway",
    "pkwy": "parkway",
    "cres": "crescent",
    "terr": "terrace",
    "gdns": "gardens", "gdn": "garden",
    "cl": "close",
    "gr": "grove",
    "mt": "mount",
    "n": "north", "s": "south", "e": "east", "w": "west",
    "ne": "north east", "nw": "north west",
    "se": "south east", "sw": "south west",
    "apt": "apartment",
    "fl": "floor",
    "flt": "flat",
    "bldg": "building",
    "hse": "house",
}

# UK postcode, including the GIR 0AA special case. Case-insensitive.
_UK_POSTCODE_RE = re.compile(
    r"\b(?:gir\s*0aa|[a-z]{1,2}\d[a-z\d]?\s*\d[a-z]{2})\b",
    re.IGNORECASE,
)

# US ZIP (5-digit; ZIP+4 collapses to the 5-digit prefix after normalization).
_US_ZIP_RE = re.compile(r"\b\d{5}\b")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_accents(s: str) -> str:
    """Return ``s`` with combining diacritics removed via NFKD."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def _postcode_from_normalized(s: str) -> Optional[str]:
    """Extract a canonical postcode/ZIP (UK first, then US 5-digit ZIP)."""
    if not s:
        return None
    match = _UK_POSTCODE_RE.search(s)
    if match:
        return _WS_RE.sub("", match.group(0)).upper()
    zip_match = _US_ZIP_RE.search(s)
    if zip_match:
        return zip_match.group(0)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_company_name(name: str) -> str:
    """Normalize a company name for fuzzy matching.

    Applies Unicode accent stripping, lowercasing, ampersand expansion
    (``&`` -> ``and``), punctuation removal, a leading-``the`` strip, and
    removal of a comprehensive set of trailing legal-form tokens
    (``ltd``, ``llc``, ``gmbh``, ``sarl``, ``pte``, ...). Whitespace is
    collapsed. Returns an empty string for empty/blank input.
    """
    if not name:
        return ""
    s = _strip_accents(name).lower().replace("&", " and ")
    s = _NON_ALNUM_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    if not s:
        return ""

    tokens = s.split()
    if tokens and tokens[0] == "the":
        tokens = tokens[1:]

    # Strip trailing legal-form tokens, but always keep at least one token.
    while len(tokens) > 1 and tokens[-1] in _COMPANY_TRAILING_TOKENS:
        tokens.pop()

    return " ".join(tokens)


def company_name_similarity(a: str, b: str) -> float:
    """Return a 0.0..1.0 similarity score between two company names.

    Uses token-set-aware fuzzy matching on the normalized forms, making
    the score robust to word order and legal-form suffix variance. Exact
    normalized equality returns ``1.0``; an empty side returns ``0.0``.
    """
    na = normalize_company_name(a)
    nb = normalize_company_name(b)
    if na == nb:
        return 1.0
    if not na or not nb:
        return 0.0
    return max(0.0, min(1.0, _token_set_ratio(na, nb) / 100.0))


def normalize_address(addr: str) -> str:
    """Normalize a UK address for fuzzy matching.

    Lowercases, strips accents and punctuation, expands common UK
    abbreviations (``st`` -> ``street``, ``rd`` -> ``road``, ``ave`` ->
    ``avenue``, ...), and moves any detected UK postcode to the end of the
    string in canonical ``outward inward`` form. Whitespace is collapsed.
    """
    if not addr:
        return ""

    raw = _strip_accents(addr).lower()

    # Extract and remove the postcode before abbreviation expansion so that
    # tokens like "st1" are not rewritten as "street1".
    postcode = ""
    match = _UK_POSTCODE_RE.search(raw)
    if match:
        postcode = _WS_RE.sub(" ", match.group(0).strip())
        raw = raw[: match.start()] + " " + raw[match.end():]

    s = _NON_ALNUM_RE.sub(" ", raw)
    s = _WS_RE.sub(" ", s).strip()

    expanded: list[str] = []
    for tok in s.split():
        expansion = _ADDRESS_ABBREV.get(tok)
        if expansion is None:
            expanded.append(tok)
        else:
            expanded.extend(expansion.split())

    if postcode:
        expanded.extend(postcode.split())

    return " ".join(expanded)


def address_similarity(a: str, b: str) -> float:
    """Return a 0.0..1.0 similarity score between two UK addresses.

    Uses order-robust fuzzy matching on the normalized forms, treating the
    postcode as a high-weight signal: when both sides yield a postcode that
    matches, the score is floored at ``0.7``; when both yield postcodes
    that differ, the score is capped at ``0.5``.
    """
    na = normalize_address(a)
    nb = normalize_address(b)
    if na == nb:
        return 1.0
    if not na or not nb:
        return 0.0

    score = max(0.0, min(1.0, _token_sort_ratio(na, nb) / 100.0))

    pa = _postcode_from_normalized(na)
    pb = _postcode_from_normalized(nb)
    if pa and pb:
        if pa == pb:
            score = max(score, 0.7)
        else:
            score = min(score, 0.5)

    return score