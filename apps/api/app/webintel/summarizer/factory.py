from __future__ import annotations

from ...config import settings
from .base import Summarizer
from .template import TemplateSummarizer


def get_summarizer() -> Summarizer:
    provider = (settings.summarizer_provider or "template").lower()
    if provider == "template":
        return TemplateSummarizer()
    if provider == "openrouter":
        from .openrouter import OpenRouterSummarizer

        return OpenRouterSummarizer()
    raise ValueError(f"Unknown SUMMARIZER_PROVIDER: {provider!r}")
