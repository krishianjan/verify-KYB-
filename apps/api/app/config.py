from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = verifyKYB/ (this file is apps/api/app/config.py)
_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ROOT / ".env"), extra="ignore")

    app_name: str = "verifyKYB API"
    environment: str = "dev"

    # Comma-separated list of allowed browser origins for CORS. In production set
    # this to your deployed frontend URL, e.g. "https://verify-kyb.vercel.app".
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Database. SQLite by default so the app runs with zero setup.
    # For Postgres: postgresql+psycopg://user:pass@host:5432/verifykyb
    database_url: str = "sqlite:///./verifykyb.db"

    # Registry provider: "mock" (offline) | "companies_house" (UK) | "us_sos" (US)
    registry_provider: str = "mock"

    # UK Companies House
    companies_house_api_key: str | None = None
    companies_house_base_url: str = "https://api.company-information.service.gov.uk"

    # US Secretary of State (via Apify actor)
    apify_api_token: str | None = None
    apify_us_sos_actor: str = "clearpath/us-business-entity-search"
    apify_match_mode: str = "contains"       # contains | exact | starts
    apify_max_results_per_state: int = 5     # cap per state -> controls cost
    apify_include_liens: bool = False        # UCC liens (extra cost); off for v1
    registry_retry: int = 1                  # extra attempts on transient failure

    # --- Feature 2: digital footprint analysis ---
    # Crawler: mock (offline) | static (free) | apify | tiered (static -> apify)
    crawler_provider: str = "mock"
    crawl_timeout_seconds: int = 20
    enable_playwright: bool = True           # JS-render tier in the tiered chain
    apify_crawler_actor: str = "apify/website-content-crawler"
    domain_age_red_flag_days: int = 90       # younger domain -> risk signal

    # Summarizer: template (no LLM) | openrouter
    summarizer_provider: str = "template"
    openrouter_api_key: str | None = None
    openrouter_model: str = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # urlscan.io reputation enrichment (optional)
    urlscan_api_key: str | None = None
    urlscan_base_url: str = "https://urlscan.io/api/v1"

    # CompliAPI — watchlist / sanctions / verification (Phase B)
    compliapi_api_key: str | None = None

    # --- Feature 4: web intelligence / enrichment agent ---
    # Runs when the registry is unavailable/not-found or on-demand. Scrapes the
    # open web, has the LLM parse evidence + judge web presence (never decides).
    enable_enrichment: bool = True
    # Web search provider(s) for enrichment. Comma-separated PRIORITY LIST —
    # each is tried until one returns results; free DDG is always the final
    # fallback. e.g. "firecrawl,crawl4ai,ddg" | "crawl4ai" | "ddg" | "apify".
    search_provider: str = "ddg"
    apify_serp_actor: str = "apify/google-search-scraper"
    crawl4ai_api_key: str | None = None
    crawl4ai_base_url: str = "https://api.crawl4ai.com"
    firecrawl_api_key: str | None = None
    firecrawl_base_url: str = "https://api.firecrawl.dev"
    enrichment_max_queries: int = 6          # targeted SERP queries per company
    enrichment_max_pages: int = 5            # pages scraped + fed to the LLM
    enrichment_char_cap: int = 12000         # evidence bundle size cap (chars)
    # LLM-as-judge: separate model override + how far it may move the score.
    judge_model: str | None = None           # defaults to openrouter_model
    judge_max_adjust: int = 15               # ± cap on the web-presence score

    # --- Feature 3: risk + vector store / memory ---
    enable_vector: bool = True
    chroma_path: str = "./chroma_store"
    # Cosine distance below this => two sites considered near-duplicates.
    dup_distance_threshold: float = 0.15

    # Default jurisdiction for incoming cases (ISO 3166-1 alpha-2, lowercase)
    default_jurisdiction: str = "gb"

    # Decision thresholds on identity confidence (0..1)
    auto_approve_threshold: float = 0.85
    manual_review_threshold: float = 0.50

    # Matching: minimum name similarity (0..1) before NAME_MISMATCH is raised
    name_match_threshold: float = 0.80
    address_match_threshold: float = 0.60
    # A name-search candidate whose token overlap (Jaccard) with the query is
    # below this is treated as "not found" rather than matched to an unrelated
    # entity (e.g. "google" vs "360 Virtual Tours by Google LLC" = 0.2).
    candidate_min_token_overlap: float = 0.40


settings = Settings()
