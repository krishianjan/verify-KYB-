# verifyKYB

Open-source KYB (Know Your Business) platform. **Feature 1: Business registry +
corporate identity verification.**

Submit a business → the identity pipeline resolves it against an official
registry, pulls directors + UBOs (PSC), compares submitted vs registry data,
and returns an explainable confidence score with a decision
(`auto_approve` / `manual_review` / `reject`).

## Status
- [x] Feature 1 — registry + identity verification (US live via Apify SoS)
- [x] Feature 2 — digital footprint analysis (crawl + domain intel + ghost signals)
- [x] Feature 3 — combined risk engine + review queue + analyst actions + vector/memory
- [x] ML risk layer — IsolationForest anomaly detection + supervised (analyst-label) scaffold
- [x] Streamlit analyst dashboard (`dashboard/`) — onboard, case detail, review queue

## Feature 3 — combined risk + analyst workflow
Bank/AML-style weighted risk scorecard (Identity 45% / Footprint 35% /
Ownership 20%) with hard-stop overrides and reason codes. Merges F1 + F2.
- `POST /kyb/cases/{id}/risk` — (re)compute the combined `RiskScore`.
- `GET /kyb/cases?status=&rating=&decision=&limit=` — analyst review queue.
- `POST /kyb/cases/{id}/actions` — `approve|reject|request_docs|escalate` (+notes).
- `GET /kyb/cases/{id}/memory` — prior findings (vector memory).
- Vector DB (Chroma, local MiniLM embeddings) powers `CLONED_SITE_MATCH`
  detection (shell-network red flag) and case memory.

## Feature 2 — digital footprint (ghost-business detection)
`POST /kyb/cases/{id}/footprint` crawls the business website, runs domain
intelligence (WHOIS age, DNS/MX, TLS), computes deterministic ghost-business
signals + a 0–100 legitimacy score and a verdict (`real`/`thin`/`inconsistent`/
`ghost`), and writes an LLM (or template) explanation. `GET` returns the latest.

Config (`.env`):
- `CRAWLER_PROVIDER`: `mock` | `static` (free) | `apify` | `tiered` (static→apify fallback)
- `SUMMARIZER_PROVIDER`: `template` (no key) | `openrouter` (+`OPENROUTER_API_KEY`)

Design: evidence + signals are deterministic/auditable; the LLM only narrates.
```bash
curl -s -X POST http://127.0.0.1:8000/kyb/cases/<id>/footprint | python -m json.tool
```

## Architecture
```
apps/api/app/
  main.py            FastAPI app
  config.py          settings (env-driven)
  db.py              SQLAlchemy engine/session/Base
  models.py          ORM: business, director, beneficial_owner, registry_record,
                     identity_assessment, mismatch, risk_signal, audit_event
  schemas.py         Pydantic request/response contracts
  registry/          registry adapters (FROZEN interface)
    dto.py           normalized DTOs  [FROZEN]
    base.py          RegistryAdapter ABC  [FROZEN]
    mock.py          offline adapter (no API key)
    factory.py       provider selection
    companies_house.py   <- OUTSOURCED (drop-in)
  matching/
    normalize.py     name/address normalization  [OUTSOURCE target, frozen sigs]
    engine.py        deterministic confidence + decision engine  [CORE]
  pipelines.py       identity pipeline orchestration  [CORE]
  cases.py           case service
  routes.py          HTTP API
```

The pipeline depends only on `registry/base.py` — adding a jurisdiction means
adding one adapter, nothing else changes.

## Run (zero setup — uses mock registry + SQLite)
```bash
cd apps/api
pip install -r ../../requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs

### Try it
```bash
# Clean match -> auto_approve
curl -s -X POST http://127.0.0.1:8000/kyb/cases \
  -H 'content-type: application/json' \
  -d '{"legal_name":"ACME TRADING LTD","company_number":"01234567"}' | python -m json.tool

# Dissolved company -> reject
curl -s -X POST http://127.0.0.1:8000/kyb/cases \
  -H 'content-type: application/json' \
  -d '{"legal_name":"GHOST HOLDINGS LTD","company_number":"09999999"}' | python -m json.tool
```

## Switch to real US data (Secretary of State, all 50 states + DC)
Live and working via the Apify `clearpath/us-business-entity-search` actor.
1. Put `APIFY_API_TOKEN=...` in `.env`.
2. Set `REGISTRY_PROVIDER=us_sos`.
3. Restart. Submit a case with a `state` to keep it to one registry (cheap):
```bash
curl -s -X POST http://127.0.0.1:8000/kyb/cases \
  -H 'content-type: application/json' \
  -d '{"legal_name":"38 TESLA, LLC","state":"CA"}' | python -m json.tool
```

### Cost / usage notes
- One actor run per lookup. Always pass `state` → searches 1 registry, not 51.
- Results are capped per state (`APIFY_MAX_RESULTS_PER_STATE`, default 5).
- Keep `REGISTRY_PROVIDER=mock` during development to avoid actor-run costs.
- **US UBO gap:** US registries publish no beneficial-owner data. The adapter
  sets `supports_psc = False`; officers are used as a proxy and the case carries
  a `NO_VERIFIED_UBO` info signal (not a penalty). Officer coverage itself
  varies by state — some states publish officers/managers, some don't.

## Switch to real UK data (later)
1. Get a free API key: https://developer.company-information.service.gov.uk/
2. In `.env`: set `REGISTRY_PROVIDER=companies_house` and `COMPANIES_HOUSE_API_KEY=...`
3. Restart. (Requires the `companies_house.py` adapter — see OUTSOURCE_TASKS.md.)
