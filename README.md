# VerifyKYB


<img width="1376" height="768" alt="KYB_project_Image" src="https://github.com/user-attachments/assets/06f1c082-0c5a-4705-aeef-361384eeb57f" />






**Open-source KYB (Know Your Business) verification platform.** One submission in →
one clear, explainable answer out: *is this business real, how confident are we,
and what should happen next* — approve, review, or reject — with the evidence and
reasons attached. When official records can't confirm a business, a **digital
agent** gathers web evidence so the case never stalls.

**Live demo:** https://verify-kyb-gules.vercel.app/
> Hosted on a free tier that sleeps when idle — the **first request can take ~50s**
> to wake the server, then it's fast. If a web section looks empty, the instance
> was asleep; reload once.

---

## Run it locally (2 minutes, no API keys)

The system runs **fully offline by default** (`REGISTRY_PROVIDER=mock`) — no keys,
no external calls.

```bash
git clone https://github.com/krishianjan/verify-KYB-.git
cd verify-KYB-
pip install -r requirements.txt

cd apps/api
uvicorn app.main:app --reload
# API + Swagger docs: http://127.0.0.1:8000/docs
```

Optional analyst dashboard (separate terminal, backend must be running):
```bash
cd dashboard
pip install -r requirements.txt
streamlit run streamlit_app.py            # http://localhost:8501
```

Run the test suite:
```bash
cd apps/api
python -m pytest tests/ -q                # 31 passing
```

---

## Sample inputs → expected outputs

With the default mock registry (offline), these are deterministic:

```bash
# 1) Clean match -> auto_approve
curl -s -X POST http://127.0.0.1:8000/kyb/cases \
  -H 'content-type: application/json' \
  -d '{"legal_name":"ACME TRADING LTD","company_number":"01234567"}'
#    -> decision: auto_approve, KYB grade A, high confidence

# 2) Dissolved / ghost company -> reject
curl -s -X POST http://127.0.0.1:8000/kyb/cases \
  -H 'content-type: application/json' \
  -d '{"legal_name":"GHOST HOLDINGS LTD","company_number":"09999999"}'
#    -> decision: reject, reason codes attached

# 3) No state / records can't confirm -> digital agent runs
curl -s -X POST http://127.0.0.1:8000/kyb/cases \
  -H 'content-type: application/json' \
  -d '{"legal_name":"amazon"}'
#    -> KYB: PENDING, decision: provisional_review, web-presence score from the agent

# Read the full customer-facing report for any case id returned above:
curl -s http://127.0.0.1:8000/kyb/cases/<id>/report | python -m json.tool
```

To use real US data instead of mock, set `REGISTRY_PROVIDER=us_sos` and
`APIFY_API_TOKEN=...` in `.env`, then submit with a state:
`{"legal_name":"38 TESLA, LLC","state":"CA"}` → auto_approve.

---

## The problem

Banks, fintechs, and payment providers must verify that a business is real before
onboarding it — but they often start with just a name and a website. If that can't
be verified properly, a fake or shell business gets approved, leading to fraud,
chargebacks, and compliance penalties. Doing the check by hand is slow and
inconsistent, and the evidence is scattered across many separate tools.

The hardest moment is when **official records can't confirm a business** — no
state was given, the company is new or foreign, or the data provider is down. Most
systems either dead-end at "not found" or (worse) treat "we couldn't check" as
"this is bad" and falsely reject a real business.

## The solution

verifyKYB turns one business submission into one structured, explainable decision:

- **Software makes every decision** — the records match, the risk score, the rules.
  This keeps the outcome consistent, reproducible, and auditable.
- **AI only reads and explains** — it turns messy web pages into a clean summary
  and scores online presence within strict bounds. It **never approves or rejects**.
- **A person handles the rest** — anything the rules can't settle goes to an
  analyst, with the evidence in front of them.

When records can't confirm a business, the **digital agent** searches the open web,
reads the top pages, and returns a short sourced profile (location, HQ, industry,
recent news, socials) plus a bounded web-presence score — so the case keeps moving
instead of stalling or falsely rejecting.

---

## How the decision works (request → decision pipeline)

```text
POST /kyb/cases
   │
   ├─ 1. Identity verification
   │     • resolve the business in an official registry
   │     • fuzzy name/address match (rapidfuzz); grade EXACT/SIMILAR/PARTIAL/NONE
   │     • persist records, officers, owners, mismatches → identity confidence
   │
   ├─ 2. Risk engine (deterministic)
   │     • weighted scorecard: Identity 45% / Footprint 35% / Ownership 20%
   │     • hard stops (inactive, not-found-but-checked, number mismatch, parked site)
   │     • review triggers (registry unavailable, no state, cloned site)
   │     • optional ML anomaly signal (never a hard stop)
   │
   ├─ 3. Digital footprint / web-intelligence agent  (POST …/footprint, …/enrich)
   │     • crawl website + domain intel (WHOIS/RDAP, DNS/MX, TLS), reputation, socials
   │     • agent: web search → read pages → LLM extracts structured profile
   │     • LLM-as-judge web-presence score, bounded (±15) — never decides
   │
   └─ Explainable report → Approve / Review / Reject → analyst queue + audit trail
```

### Scoring
- **Two grades, A–F:** **KYB** = records-match quality (`identity_confidence × 100`);
  **Risk** = `100 − overall_risk`.
- **Bands:** A: 90–100 · B: 80–89 · C: 70–79 · D: 60–69 · F: below 60.
- **PENDING** (not F) when records can't confirm — a *state*, not a failing grade.
- **Match categories:** EXACT ≥ 0.97 · SIMILAR ≥ 0.80 · PARTIAL ≥ 0.50 · NONE below 0.50.
- **Decision:** hard stop → reject · review trigger → manual/provisional review ·
  KYB ≥ B and Risk ≥ B → auto_approve · otherwise review.

---

## Key design decisions & trade-offs

**1. Deterministic rules decide; AI only explains.**
Regulated onboarding decisions must be reproducible and defensible (SR 11-7 model
risk, FCRA/ECOA adverse action, EU AI Act). An LLM's answer changes between runs,
can invent facts, and can't cite a record — so "the model said so" is not a
defensible decline. *Trade-off:* more engineering than a single LLM call, but the
output is auditable. AI is fenced to extraction, summaries, and a bounded
web-presence judge.

**2. Three-state verification: good / bad / not-checked.**
The core resilience decision. A failed or missing registry lookup sets
confidence to *null* (not 0) and emits a **review trigger, never a hard stop**;
the identity/ownership categories are skipped when there's no data. *Why:* a
registry outage or coverage gap must never become an adverse action against a real
business. (This fixed a real bug: a live lookup once returned a reject only because
the data provider had hit its monthly quota.)

**3. Build fresh, treat existing KYB repos as reference, not dependencies.**
Studied commercial products and open-source projects, found no complete,
explainable open-source workflow, and built a clean spine instead of forking.
*Trade-off:* more upfront work, but no inherited constraints and full control of
the decision logic.

**4. Frozen adapter interfaces for every external source.**
Registries, crawlers, searchers, and summarizers sit behind fixed contracts
(`registry/base.py`, `webintel/crawler/base.py`, etc.). Adding a jurisdiction or
data source never touches the risk engine. *Trade-off:* a little abstraction now
for easy extension later.

**5. Cheap-first, tiered data gathering.**
Crawler tier: static (httpx + BeautifulSoup) → Crawl4AI → Playwright → Apify.
Search chain: Firecrawl → Crawl4AI → DuckDuckGo (always the free fallback).
Domain intel (WHOIS/RDAP/DNS/TLS) is free/local. *Why:* minimize cost and latency;
only escalate to paid/heavy tooling when needed.

**6. US-first registry; UK spec'd, not built.**
US via the Apify Secretary-of-State actor (all 50 states + DC). *Trade-off /
limitation:* Delaware and foreign entities are gaps SoS data can't cover, and the
**US publishes no beneficial-owner data** (FinCEN BOI isn't public) — officers are
used as a proxy and a non-penalizing `NO_VERIFIED_UBO` signal is set.

**7. LLM output is fenced and sanitized.**
The model returns content only (never chain-of-thought), a `clean_summary()`
sanitizer strips any leaked reasoning, and the judge can move a score by at most
±15. *Why:* prevents prompt/CoT leakage and stops the AI from ever driving the
verdict. (Pin `OPENROUTER_MODEL` to an instruct model like `openai/gpt-4o-mini`;
the rotating `openrouter/free` alias can route to reasoning models that return
empty content.)

**8. Synchronous v1.**
A live lookup runs inline (~40–120s with external calls). *Trade-off:* simpler to
reason about and test; background processing + polling is the planned next step to
remove the wait.

**9. SQLite for dev, Postgres for prod.**
Dev uses SQLite with additive auto-migration (new columns added on startup, no
manual migration during iteration). Production targets Postgres via `DATABASE_URL`
with Alembic. *Note:* on a free hosting tier, SQLite lives on an ephemeral disk, so
cases don't survive a restart — attach Postgres for a persistent demo.

**Alternatives considered and rejected:** a single LLM making the decision
(not auditable); SEC EDGAR for ownership (covers only public companies, not the
small-business target); mem0 for memory (stateless deterministic pipelines +
Postgres already suffice); Qdrant/Weaviate over Chroma (embedded Chroma is enough
for cloned-site detection + case memory at this scale).

---

## Features

- **Company & merchant verification** — entity resolution, legal-status checks,
  fuzzy name/address matching, mismatch detection.
- **Registry checks** — official lookups, metadata, officers/directors, ownership
  signals where published.
- **Digital footprint** — website/domain verification, WHOIS/RDAP, DNS/TLS, social
  presence, ghost-business signals, legitimacy score.
- **Web-intelligence agent** — web search → scrape → LLM structured extraction →
  bounded web-presence judge → narrative, with sources.
- **Risk scoring** — weighted deterministic scorecard, reason codes, hard stops,
  review triggers.
- **Analyst workflow** — review queue, approve/reject/request-docs/escalate,
  audit trail.
- **Explainable reports** — two A–F grades, match quality, decision + reasoning,
  source-of-truth map.
- **ML signal** — IsolationForest anomaly detection (complements, never replaces
  the rules) + supervised scaffold from analyst labels.

---

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | status + active registry provider |
| POST | `/kyb/cases` | create + verify (identity + risk) |
| GET  | `/kyb/cases/{id}` | full raw case |
| GET  | `/kyb/cases/{id}/report` | customer-facing report (two grades, decision) |
| POST | `/kyb/cases/{id}/footprint` | run digital footprint |
| GET  | `/kyb/cases/{id}/footprint` | latest footprint |
| POST | `/kyb/cases/{id}/enrich` | run the web-intelligence agent |
| GET  | `/kyb/cases` | analyst review queue (filters: status, rating, decision) |
| POST | `/kyb/cases/{id}/actions` | analyst action |
| POST | `/kyb/cases/{id}/risk` | recompute risk |
| POST | `/kyb/cases/{id}/explain` | on-demand AI explanation |
| GET  | `/kyb/cases/{id}/memory` | vector case memory |

---

## Configuration (`.env`)

Everything runs offline on defaults; set these only to use live providers. Copy
`.env.example` to `.env`. **Never commit `.env`** (it's gitignored).

| Variable | Default | Notes |
|----------|---------|-------|
| `REGISTRY_PROVIDER` | `mock` | `mock` \| `us_sos` \| `companies_house` (spec) |
| `CRAWLER_PROVIDER` | `tiered` | `mock` \| `static` \| `playwright` \| `apify` \| `tiered` |
| `SUMMARIZER_PROVIDER` | `template` | `template` (no key) \| `openrouter` |
| `SEARCH_PROVIDER` | `ddg` | priority list, e.g. `firecrawl,crawl4ai,ddg` |
| `OPENROUTER_MODEL` | — | use `openai/gpt-4o-mini` (avoid `openrouter/free`) |
| `OPENROUTER_API_KEY` | — | for LLM summaries/enrichment |
| `APIFY_API_TOKEN` | — | US Secretary-of-State lookups |
| `FIRECRAWL_API_KEY` | — | web search/scrape |
| `URLSCAN_API_KEY` | — | reputation/screenshots |
| `ENABLE_ENRICHMENT` | `true` | run the web-intelligence agent |
| `ENABLE_VECTOR` | — | Chroma cloned-site detection (can OOM on 512MB hosts) |
| `JUDGE_MAX_ADJUST` | `15` | ± cap on the web-presence judge |
| `ENRICHMENT_MAX_QUERIES` / `_PAGES` | `6` / `5` | agent breadth |
| `DATABASE_URL` | SQLite | set to Postgres for production/persistence |
| `CORS_ORIGINS` | — | allowed frontend origins in production |

---

## Project structure

```text
verifyKYB/
├── apps/api/                 FastAPI backend
│   └── app/
│       ├── main.py           app factory, CORS, lifespan
│       ├── config.py         env-driven settings
│       ├── db.py             engine/session + dev auto-migration
│       ├── models.py         ORM tables
│       ├── schemas.py        Pydantic request/response contracts
│       ├── routes.py         HTTP API
│       ├── pipelines.py      identity verification pipeline
│       ├── report.py         customer-facing report builder
│       ├── llm.py            shared OpenRouter helper (fenced + sanitized)
│       ├── matching/         normalize.py + engine.py (fuzzy + confidence)
│       ├── registry/         registry adapters (frozen interface)
│       ├── webintel/         footprint + web-intelligence agent
│       │   ├── search/       search providers (ddg/firecrawl/crawl4ai/apify + chain)
│       │   ├── crawler/      tiered crawlers
│       │   ├── enrich.py     the agent: structured extraction
│       │   ├── judge.py      bounded LLM-as-judge web-presence score
│       │   └── pipeline.py   footprint + enrichment orchestration
│       └── risk/             engine.py + service.py + ml.py + explain.py
├── dashboard/                Streamlit analyst console
├── docs/                     API & implementation notes
├── requirements.txt
└── .env.example
```

---

## Database model

The **business case** is the central entity, linked to registry records, officers,
beneficial owners, identity assessments, field-level mismatches, web intelligence,
risk signals, risk scores, analyst actions, and audit events. This separates
**source evidence** from **assessment results**, **risk reasoning**, and **human
decisions**, which keeps every case traceable and explainable. SQLAlchemy ORM;
SQLite in dev (additive auto-migration), Postgres + Alembic for production.

---

## Limitations (honest)

- US-only registry today; Delaware and foreign entities are coverage gaps.
- US beneficial-ownership data isn't public (officers used as a proxy).
- Synchronous lookups (~40–120s with live providers); no background processing yet.
- Sanctions/watchlist and TIN/EIN matching are placeholders, not wired.
- DuckDuckGo search is flaky from data-center IPs; page-link extraction is the
  reliable social path.
- Free hosting tier: cold starts (~50s) and an ephemeral database (cases reset on
  restart) — use Postgres for a persistent deployment.

## Roadmap

Entity-resolution clustering (rank clones vs. the real entity); sanctions/OFAC +
TIN checks; OpenCorporates adapter for DE/foreign coverage; async background
processing + polling; ongoing monitoring/re-checks; network-risk graph
(shell-ring detection).

---

## How AI was used

AI coding assistants (Claude Code, Cursor, GitHub Copilot) were used for
scaffolding, refactoring, and reviewing. The workflow, architecture, data model,
risk weights, and hard-stop rules were designed and owned by the author; AI was
directed to implement and refine supporting code against those requirements, and
every change was reviewed and tested. The product itself uses an LLM **only to read
and summarize web evidence and to produce a bounded web-presence score — it never
approves or rejects a business.** The 31 passing tests validate *tested behavior*,
not real-world fraud-detection accuracy or compliance outcomes.

## Contributing

Contributions welcome — registry adapters (new jurisdictions), entity matching,
risk scoring, scraping/enrichment quality, report clarity, tests, and docs.


