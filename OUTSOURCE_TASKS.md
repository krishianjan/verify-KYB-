# Outsourcing tasks (paste each block into another LLM)

These are isolated, frozen-interface tasks. Each prompt is self-contained — the
other LLM does **not** need the rest of the repo. The returned code must match
the contracts below exactly so it drops straight into verifyKYB.

Priority order: **Task 1 (Companies House)** unblocks real data. Task 2 improves
match quality. Tasks 3–4 harden the project.

---

## TASK 1 — UK Companies House registry adapter  [HIGH PRIORITY]

> You are writing ONE Python file for a FastAPI KYB project. It implements a
> registry adapter against the UK Companies House public API. Do not invent
> other files. Output only `companies_house.py`.
>
> ### Frozen contract you must satisfy
> The file lives at `apps/api/app/registry/companies_house.py` and must define
> `class CompaniesHouseAdapter(RegistryAdapter)`. The base class and the DTOs
> already exist and must be imported exactly like this:
>
> ```python
> from .base import RegistryAdapter, RegistryError
> from .dto import (
>     RegistryCompanyProfile,
>     RegistryCompanySummary,
>     RegistryOfficer,
>     RegistryPSC,
> )
> ```
>
> The DTOs (Pydantic v2 models) have these fields — return EXACTLY these shapes:
>
> ```python
> RegistryCompanySummary(company_number: str, company_name: str,
>     company_status: str|None, address: str|None, source: str)
> RegistryCompanyProfile(company_number: str, company_name: str,
>     company_status: str|None, company_type: str|None,
>     incorporation_date: str|None,  # "YYYY-MM-DD"
>     registered_address: str|None, source: str, source_uri: str|None, raw: dict)
> RegistryOfficer(name: str, role: str|None, appointed_on: str|None,
>     resigned_on: str|None, nationality: str|None, raw: dict)
> RegistryPSC(name: str, kind: str|None, natures_of_control: list[str],
>     notified_on: str|None, ceased_on: str|None, raw: dict)
> ```
>
> The abstract methods to implement (ALL SYNCHRONOUS — no async):
> ```python
> def search(self, query: str, jurisdiction: str) -> list[RegistryCompanySummary]
> def get_company(self, company_number: str) -> RegistryCompanyProfile | None
> def get_officers(self, company_number: str) -> list[RegistryOfficer]
> def get_psc(self, company_number: str) -> list[RegistryPSC]
> ```
> Set class attribute `source = "companies_house"`.
>
> ### Config
> Read settings from the project's config object:
> ```python
> from ..config import settings
> # settings.companies_house_api_key: str | None
> # settings.companies_house_base_url: str  (default https://api.company-information.service.gov.uk)
> ```
> In `__init__`, raise `RegistryError` if the API key is missing.
>
> ### Companies House API facts
> - Base URL: `https://api.company-information.service.gov.uk`
> - Auth: HTTP Basic. API key is the USERNAME, password is EMPTY string.
>   With httpx: `httpx.Client(auth=(api_key, ""))`.
> - Endpoints:
>   - `GET /search/companies?q={query}&items_per_page=20`
>     → `{"items": [{"company_number","title","company_status","address_snippet"}]}`
>   - `GET /company/{company_number}`
>     → `{"company_name","company_number","company_status","type",
>         "date_of_creation","registered_office_address": {address parts}}`
>   - `GET /company/{company_number}/officers`
>     → `{"items": [{"name","officer_role","appointed_on","resigned_on","nationality"}]}`
>   - `GET /company/{company_number}/persons-with-significant-control`
>     → `{"items": [{"name","kind","natures_of_control":[...],"notified_on","ceased_on"}]}`
> - Rate limit: 600 requests / 5 min; a 429 means slow down.
>
> ### Mapping rules
> - `title` → `company_name`; `type` → `company_type`;
>   `date_of_creation` → `incorporation_date`.
> - `registered_office_address` is an OBJECT. Join its non-empty parts
>   (address_line_1, address_line_2, locality, region, postal_code, country)
>   into one comma-separated string for `registered_address` / `address`.
> - Put the full upstream JSON dict into `raw`.
> - Set `source_uri` to the human company page:
>   `https://find-and-update.company-information.service.gov.uk/company/{number}`
>
> ### Behavior & robustness
> - Reuse a single `httpx.Client` (timeout ~15s). A `close()` method is fine.
> - `get_company`: return `None` on HTTP 404; raise `RegistryError` on 401/403
>   (bad key) and on 5xx/network errors.
> - `get_officers` / `get_psc`: return `[]` on 404 or empty `items`.
> - On 429, retry up to 3 times with exponential backoff (e.g. 2s, 4s, 8s);
>   raise `RegistryError` if still limited.
> - Use `from __future__ import annotations`. Type-hint everything. No print().
>
> Output the complete `companies_house.py` only.

---

## TASK 2 — Production-grade name/address normalization  [MEDIUM]

> Rewrite ONE Python file: `apps/api/app/matching/normalize.py`. It provides
> normalization + fuzzy similarity for company names and addresses used by a KYB
> matching engine. Keep these FOUR function signatures EXACTLY (names, args,
> return types are a frozen contract — other modules import them):
>
> ```python
> def normalize_company_name(name: str) -> str: ...
> def company_name_similarity(a: str, b: str) -> float: ...   # 0.0..1.0
> def normalize_address(addr: str) -> str: ...
> def address_similarity(a: str, b: str) -> float: ...        # 0.0..1.0
> ```
>
> Requirements:
> - You MAY use `rapidfuzz` (add to requirements if so) and Python stdlib only.
> - `normalize_company_name`: lowercase, strip punctuation/accents, collapse
>   whitespace, and remove a comprehensive set of company-type suffixes/legal
>   forms (ltd, limited, llc, llp, plc, inc, corp, co, gmbh, sarl, sa, pte,
>   bv, ag, oy, ab, pvt, "and"/"&" normalization, etc.). Handle "the" prefix.
> - `company_name_similarity`: token-set-aware fuzzy ratio on the normalized
>   forms, returning 1.0 for exact normalized equality. Robust to word order.
> - `normalize_address`: lowercase, strip punctuation, normalize common UK
>   abbreviations (st→street, rd→road, ave→avenue), and extract/keep the UK
>   postcode. Collapse whitespace.
> - `address_similarity`: fuzzy ratio on normalized forms; weight postcode match
>   heavily (if both have a postcode and they match, floor the score at ~0.7; if
>   they mismatch, cap it).
> - Pure functions, deterministic, no I/O, no network. `from __future__ import
>   annotations`. Include a short docstring per function.
>
> Output the complete file only.

---

## TASK 3 — Test suite  [MEDIUM]

> Write pytest tests for a FastAPI KYB app. Create `apps/api/tests/test_api.py`
> and `apps/api/tests/test_engine.py`.
>
> Facts:
> - App factory: `from app.main import app`.
> - IMPORTANT: the DB tables are created in the FastAPI lifespan, so the
>   TestClient MUST be used as a context manager or tables won't exist:
>   `with TestClient(app) as c: ...`. Use a pytest fixture that yields the
>   client inside a `with` block, and point `DATABASE_URL` at a temp sqlite file
>   (set the env var BEFORE importing app, or monkeypatch settings).
> - Endpoints: `POST /kyb/cases` (201) and `GET /kyb/cases/{id}` (200/404),
>   `GET /health`.
> - With the default mock registry:
>   - `{"legal_name":"ACME TRADING LTD","company_number":"01234567"}` →
>     decision `auto_approve`, confidence ~1.0, 1 director, 1 UBO.
>   - `{"legal_name":"GHOST HOLDINGS LTD","company_number":"09999999"}` →
>     decision `reject`, risk signals include `COMPANY_INACTIVE` and `NO_PSC`.
>   - A clearly different legal_name vs a supplied matching number → a
>     `legal_name` mismatch and decision `reject`.
> - For `test_engine.py`: import `assess_identity`, `SubmittedBusiness` from
>   `app.matching` and the DTOs from `app.registry.dto`. Unit-test the engine
>   directly (no HTTP): a perfect match → confidence 1.0 / auto_approve; a
>   dissolved `company_status` → a high-severity `COMPANY_INACTIVE` signal and
>   confidence capped at 0.40; `profile=None` → `REGISTRY_NOT_FOUND` + reject.
>
> Keep tests independent and fast. Output both files.

---

## TASK 4 — DevOps (Docker + Postgres + Alembic)  [LOW / later]

> Create deployment scaffolding for a FastAPI + SQLAlchemy 2.0 app whose package
> is `apps/api/app` (module path `app.main:app`), Python 3.11.
>
> Produce:
> 1. `apps/api/Dockerfile` — slim python:3.11, installs `requirements.txt`
>    (at repo root, copied in), runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
> 2. `deployments/docker-compose.yml` — services: `api` (build from apps/api,
>    env from .env, port 8000) and `db` (postgres:16, volume, healthcheck,
>    POSTGRES_USER/PASSWORD/DB=verifykyb). api depends_on db healthy.
>    Set `DATABASE_URL=postgresql+psycopg://verifykyb:verifykyb@db:5432/verifykyb`.
> 3. Alembic setup: `apps/api/alembic.ini`, `apps/api/alembic/env.py` wired to
>    `from app.db import Base` and `from app import models` with
>    `target_metadata = Base.metadata`, reading the URL from env/settings.
>    Include a one-line note on generating the first migration.
>
> SQLAlchemy models use `Mapped[...]` declarative style on a `DeclarativeBase`
> subclass named `Base` in `app/db.py`. Output each file clearly labeled.
