"""Small OpenRouter chat helper (shared). Returns None on any failure."""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import settings


def openrouter_chat(
    system: str, user: str, max_tokens: int = 700, model: str | None = None
) -> str | None:
    if not settings.openrouter_api_key:
        return None
    try:
        resp = httpx.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": model or settings.openrouter_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": max_tokens,
            },
            timeout=45,
        )
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        # Only the final answer (`content`) — never the model's `reasoning`
        # (chain-of-thought), which would leak the prompt/instructions.
        return (msg.get("content") or "").strip() or None
    except Exception:  # noqa: BLE001
        return None


# Markers that signal a model leaked its chain-of-thought / prompt scaffolding
# instead of just answering. Used to salvage the final text when it happens.
_COT_MARKERS = (
    "analyze the request", "analyze the provided", "extract required",
    "extract the required", "draft the profile", "constraint check",
    "step 1", "step 2", "let me ", "first, i", "here is the", "here's the",
    "**analyze", "1. **", "2. **", "3. **", "4. **",
)
_DRAFT_RE = re.compile(r"(?:final|draft)\s*(?:profile|answer|version)?\s*\d*\s*[:\-]\s*",
                       re.IGNORECASE)


def clean_summary(text: str | None) -> str | None:
    """Salvage a clean summary if a model leaked reasoning/scaffolding.

    JSON extraction normally isolates the final answer; this is a safety net for
    the cases where the text still arrives wrapped in analysis. Returns None if
    nothing usable remains.
    """
    if not text:
        return None
    s = text.strip()
    low = s.lower()
    if any(m in low for m in _COT_MARKERS):
        # Prefer text after an explicit "Final/Draft:" marker.
        m = list(_DRAFT_RE.finditer(s))
        if m:
            s = s[m[-1].end():].strip()
        else:
            # Else keep only clean prose lines (drop numbered/bold "analysis").
            kept = [
                ln for ln in s.splitlines()
                if ln.strip()
                and not ln.lstrip().startswith(("*", "-", "#"))
                and not re.match(r"^\s*\d+\.", ln)
                and not any(mk in ln.lower() for mk in _COT_MARKERS)
            ]
            s = " ".join(kept).strip()
    s = s.strip().strip("*").strip()
    return s or None


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def openrouter_json(
    system: str, user: str, max_tokens: int = 1200, model: str | None = None
) -> dict[str, Any] | None:
    """Ask the model for JSON and parse it robustly. Returns None on any failure
    (no key, network, or unparseable output) so callers degrade gracefully.

    The LLM here only structures/judges evidence — it never makes the decision.
    """
    raw = openrouter_chat(
        system + "\n\nRespond with ONLY a single valid JSON object. No prose, "
        "no markdown fences.",
        user,
        max_tokens=max_tokens,
        model=model,
    )
    if not raw:
        return None
    return _parse_json_object(raw)


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    for candidate in _json_candidates(raw):
        try:
            data = json.loads(candidate)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(data, dict):
            return data
    return None


def _json_candidates(raw: str):
    text = raw.strip()
    yield text
    m = _FENCE_RE.search(text)
    if m:
        yield m.group(1)
    # First {...} span as a last resort.
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        yield text[start : end + 1]
