# verifyKYB  Project Notes (full history & reference)





## 1. Goal & problem

**Problem.** Businesses are easy to create and can look real on paper. Onboarding
flows (banks, fintechs, payment processors) often rely on just a name + website.
Manual KYC/KYB review is slow, inconsistent, and spread across disconnected
vendors. There's no simple open-source starter for the whole workflow.

**Goal.** One open-source KYB (Know Your Business) workflow that, from a single
submission, **verifies a company's legal existence, analyzes its digital
footprint, scores risk explainably, and routes unresolved cases to analysts** 
with a clear verdict out, not a spreadsheet.

**Reference product.** Modeled on **Baselayer** (US KYB vendor): one API call in →
one structured verdict out (two letter grades: KYB + Risk) → auto-approve or
flag → (future) ongoing monitoring.

**Design stance (non-negotiable).** Decisions are **deterministic, rule-based,
and auditable with reason codes** (meets SR 11-7 model risk, FCRA/ECOA adverse
action, EU AI Act expectations). **AI/LLM only explains; it never decides.** ML
is a complementary signal, never the verdict.

---

## 2. The three features (+ ML, + report)

1. **Registry + corporate identity verification** — find the entity in an
   official registry, fuzzy-match name/address, pull status/officers/UBO.
2. **Digital footprint analysis** — crawl the website, domain intelligence
   (WHOIS/RDAP, DNS/MX, TLS), social presence, urlscan reputation, "ghost
   business" signals, and an LLM company profile.
3. **Risk scoring + analyst workflow** — a bank-style weighted scorecard merging
   F1 + F2 into KYB + Risk grades, a review queue, and analyst actions.
4. **Web-intelligence agent** — when the registry can't confirm the entity
   (outage/quota or no match), scrape the open web (site, socials, news,
   funding, location, team), have the LLM parse structured evidence + **judge**
   web presence (complementary score, never the decision), and generate a
   narrative. Gives a real score on web evidence while the registry stays PENDING.
- **ML layer** — IsolationForest anomaly detection + supervised scaffold +
  transformer embeddings (cloned-site detection).
- **Report** — Baselayer-shaped customer output (two grades, match categories,
  decision object, source-of-truth).

---

## 3. Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| API | **FastAPI** + Pydantic v2 | async-ready, typed contracts, auto OpenAPI `/docs` |
| ORM / DB | **SQLAlchemy 2.0** + SQLite (dev) / Postgres (prod) | simple default, swap via `DATABASE_URL` |
| Matching | **rapidfuzz** (+ difflib fallback) | entity resolution / fuzzy name+address |
| Registry (US) | **Apify** actor `clearpath/us-business-entity-search` | all 50 states + DC SoS data |
| Crawling | **httpx + BeautifulSoup** (static) → **Playwright** (JS) → **Apify** (fallback) | tiered, cheap-first |
| Domain intel | **python-whois**, **RDAP** (rdap.org), **dnspython**, stdlib TLS | free, no key |
| Reputation | **urlscan.io** (key) | screenshots + scan history |
| LLM | **OpenRouter** (`openrouter/free`) | summaries/explanations only |
| Vector DB | **ChromaDB** (embedded, local MiniLM embeddings) | cloned-site detection + case memory |
| ML | **scikit-learn** (IsolationForest, LogisticRegression) | anomaly + supervised scaffold |
| Dashboard | **Streamlit** (multipage) | fast analyst/demo UI |
| Queue/async | _not yet_ (sync v1; Celery/Cloud Tasks later) | — |

**External keys** (all in `.env`, gitignored): `APIFY_API_TOKEN`,
`OPENROUTER_API_KEY`, `URLSCAN_API_KEY`, `COMPLIAPI_API_KEY` (registered, not yet
wired). Everything runs offline on `mock`/`template`/`static` providers with no keys.

---

## 4. Repository layout

```
verifyKYB/
├── apps/api/                     FastAPI backend
│   ├── app/
│   │   ├── main.py               app factory, CORS, lifespan (init_db)
│   │   ├── config.py             pydantic-settings; reads repo-root .env
│   │   ├── db.py                 engine/session/Base + dev auto-migration
│   │   ├── models.py             all SQLAlchemy ORM tables
│   │   ├── schemas.py            all Pydantic request/response contracts
│   │   ├── routes.py             every HTTP endpoint
│   │   ├── cases.py              case service: create + assemble CaseOut
│   │   ├── pipelines.py          identity verification pipeline (F1)
│   │   ├── report.py             Baselayer-shaped report builder
│   │   ├── llm.py                shared OpenRouter chat helper
│   │   ├── vectorstore.py        Chroma: business_web + case_memory
│   │   ├── matching/
│   │   │   ├── normalize.py      name/address normalize + fuzzy similarity
│   │   │   └── engine.py         deterministic identity confidence engine
│   │   ├── registry/             registry adapters (FROZEN interface)
│   │   │   ├── dto.py            normalized registry DTOs  [frozen]
│   │   │   ├── base.py           RegistryAdapter ABC  [frozen]
│   │   │   ├── mock.py           offline adapter
│   │   │   ├── us_sos.py         US Secretary of State via Apify
│   │   │   └── factory.py        provider selection
│   │   ├── webintel/             Feature 2 (digital footprint) + Feature 4 (web intel)
│   │   │   ├── dto.py            CrawlResult, DomainInfo, FootprintResult
│   │   │   ├── crawler/          base, mock, static, crawl4ai, playwright, apify, tiered, factory
│   │   │   ├── search/           F4 search providers: base, ddg, crawl4ai, apify, factory
│   │   │   ├── domain.py         WHOIS + RDAP + DNS/MX + TLS
│   │   │   ├── discover.py       website + social discovery
│   │   │   ├── reputation.py     urlscan.io
│   │   │   ├── analyzer.py       deterministic ghost-business signals
│   │   │   ├── profile.py        LLM company profile
│   │   │   ├── enrich.py         F4 web-intelligence structured extraction
│   │   │   ├── judge.py          F4 LLM-as-judge web presence (bounded)
│   │   │   ├── report_text.py    F4 narrative generator
│   │   │   ├── summarizer/       footprint summary (template | openrouter)
│   │   │   └── pipeline.py       footprint + enrichment pipeline (F2+F4)
│   │   └── risk/                 Feature 3 (risk)
│   │       ├── engine.py         weighted scorecard + hard-stops + review triggers
│   │       ├── service.py        gather F1+F2 -> RiskScore + status + memory
│   │       ├── ml.py             IsolationForest anomaly + supervised scaffold
│   │       └── explain.py        plain-English + AI explanations
│   ├── tests/                    test_api, test_engine, test_risk, test_webintel, test_resilience (31 tests)
│   └── scripts/ab_eval.py        A/B harness: A (enrichment off) vs B (on) + invariants
├── dashboard/                    Streamlit analyst console
│   ├── streamlit_app.py          entry + nav + module hot-reload
│   ├── api.py                    backend client (graceful errors)
│   ├── components.py             render_report / render_case / render_footprint
│   └── app_pages/                onboard.py, queue.py, case.py
├── docs/API.md                   API & implementation guide
├── README.md                     overview + run instructions
├── FRONTEND_TASK.md              spec for a production Next.js frontend
├── OUTSOURCE_TASKS.md            frozen-interface tasks for other LLMs
├── requirements.txt              backend deps
└── .env / .env.example           secrets / template
```

---

## 5. Database entities (SQLAlchemy, `models.py`)

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `business` | the submitted case / canonical business | legal_name, company_number, jurisdiction (`us-ca`), website, status, submitted_payload |
| `registry_record` | raw evidence from a registry | source, company_name, company_status, company_type, incorporation_date, registered_address, raw(JSON) |
| `director` | officers/directors | name, role, source, raw |
| `beneficial_owner` | UBO/PSC (UK); US gap | name, kind, natures_of_control |
| `identity_assessment` | F1 result | confidence, decision, matched_company_number, summary |
| `mismatch` | field-level mismatches | field, submitted_value, registry_value, severity |
| `risk_signal` | every signal (identity/web_intel/ml) | code, severity, weight, detail, **source** |
| `web_intel` | F2 footprint result | verdict, legitimacy_score, domain, domain_age_days, has_tls, summary, **profile_summary**, **socials**, screenshot_url, raw |
| `risk_score` | F3 combined result | overall_risk, rating, decision, reason_codes, category_scores, **explanation** |
| `review_action` | analyst decisions | action, notes, actor |
| `audit_event` | immutable event log | event_type, actor, detail(JSON) |

> **Dev migration:** `db.init_db()` runs `create_all` + `_add_missing_columns()`
> (SQLite `ALTER TABLE ADD COLUMN` for new model columns) so additive schema
> changes never 500. Production should use Alembic.

---

## 6. Architecture — the decision pipeline

```
POST /kyb/cases
   │
   ├─ 1. IDENTITY PIPELINE (pipelines.py)                [Feature 1]
   │     • no state/number + registry needs one → skip, mark REGISTRY_STATE_NOT_PROVIDED (→review)
   │     • else resolve candidate: get_company(number) or search(name)
   │         - prefer ACTIVE entities; drop weak matches (token overlap < 0.40)
   │     • fetch officers + PSC; persist registry_record/director/beneficial_owner
   │     • matching/engine.assess_identity → confidence, mismatches, signals, decision
   │
   ├─ 2. RISK (risk/service.compute_and_store_risk)       [Feature 3]
   │     • ML: IsolationForest anomaly (≥8 cases) → ML_ANOMALY; supervised scaffold
   │     • engine.compute_risk: category-weighted (Identity 45 / Footprint 35 / Ownership 20)
   │         - ML bump, REVIEW triggers (clone, no-state → review band 50–65)
   │         - HARD STOPS (registry_not_found, inactive, number_mismatch, unreachable, parked) → ≥80 reject
   │     • store RiskScore + plain explanation; set business.status to combined decision
   │
   └─ returns CaseOut (business, assessment, risk, signals, directors, UBOs)

POST /kyb/cases/{id}/footprint                            [Feature 2]
   • resolve URL: submitted website → discover (email domain / web search) → else context-only
   • crawl (static→playwright→apify) · domain intel (whois/RDAP/DNS/TLS) · urlscan reputation
   • socials: from page links + web search · LLM company profile
   • analyzer.analyze_footprint → ghost signals + legitimacy score + verdict
   • vector cloned-site check (exclude same entity) → CLONED_SITE_MATCH (→review)
   • persist web_intel + web_intel signals → recompute risk

GET /kyb/cases/{id}/report  → Baselayer-shaped verdict (report.py)
GET /kyb/cases  → review queue        POST /kyb/cases/{id}/actions → analyst action
POST /kyb/cases/{id}/explain → on-demand AI narrative    GET …/memory → vector recall
```

### Scoring (two grades, A–F)
- **KYB rating** = government-record match quality = `identity_confidence × 100`.
- **Risk rating** = fraud/compliance safety = `100 − overall_risk` (internal risk).
- Bands: A≥90, B≥80, C≥70, D≥60, else F.
- **Match categories** (entity resolution): EXACT ≥0.97 · SIMILAR ≥0.80 · PARTIAL ≥0.50 · NONE.
- **Decision:** hard stop → reject; review trigger → manual_review; KYB≥B & Risk≥B → auto_approve; else review.

### Three registry states (the resilience fix)
The system distinguishes **VERIFIED-GOOD** / **VERIFIED-BAD** / **NOT-CHECKED**.
"Not-checked" (registry outage/quota via `RegistryUnavailable`, or simply no
match) sets identity `confidence = None` (not `0.0`) and emits
`REGISTRY_UNAVAILABLE` / `REGISTRY_NOT_FOUND` — both **review triggers, never
hard-stops**. The risk engine then skips the identity + ownership categories
(no data ≠ bad data), so an outage can't fabricate a reject. KYB shows
**PENDING**, the decision is **provisional_review**, and the web-intelligence
agent (F4) scores the case on web presence. A registry outage must never be an
adverse action against the customer (SR 11-7 / FCRA-ECOA). Genuine ghosts are
still caught by the web hard-stops (`SITE_UNREACHABLE`, `PARKED_OR_PLACEHOLDER`).
**LLM-as-judge** rates web presence (±15 nudge on the deterministic score) but
a web-only case is capped at provisional review — the LLM never approves/rejects.

---

## 7. Features — what each delivers

**F1 Identity (`pipelines.py`, `matching/`, `registry/`)**
- Resolve against US SoS (Apify), fuzzy name/address match, active-entity
  preference, weak-match rejection, officers + (where published) UBO, mismatches,
  confidence, identity decision. UK Companies House adapter spec'd (not built).

**F2 Digital footprint (`webintel/`)**
- Tiered crawl; WHOIS+RDAP domain age, DNS/MX, TLS; social discovery (page +
  search); urlscan screenshot/reputation; deterministic ghost signals
  (DOMAIN_TOO_NEW, THIN_CONTENT, NO_CONTACT_INFO, NAME_NOT_ON_SITE,
  NO_MAIL_SERVER, PARKED_OR_PLACEHOLDER, SITE_UNREACHABLE, SOCIAL_PRESENCE…);
  legitimacy score + verdict (real/thin/inconsistent/ghost); LLM company profile;
  cloned-site detection via embeddings.

**F3 Risk + workflow (`risk/`, queue/actions routes)**
- Weighted scorecard, hard-stops, review triggers, reason codes, plain + AI
  explanations, ML anomaly signal, review queue with filters, analyst actions
  (approve/reject/request_docs/escalate), audit trail, case memory.

**Report (`report.py`)** — `verified`, two scores, match categories, `business`
block (structure/months_in_business/registrations/officers), `watchlist_hits[]`
(planned), `digital_footprint`, `decision{action,confidence,reasoning}`,
`sources{}` source-of-truth, `warnings[]`.

---

## 8. API endpoints (`routes.py`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | status + active registry provider |
| POST | `/kyb/cases` | create + verify (identity + risk) |
| GET | `/kyb/cases/{id}` | full raw case |
| GET | `/kyb/cases/{id}/report` | customer verdict (Baselayer-shaped) |
| POST | `/kyb/cases/{id}/footprint` | run digital footprint |
| GET | `/kyb/cases/{id}/footprint` | latest footprint |
| GET | `/kyb/cases` | review queue (filters: status, rating, decision) |
| POST | `/kyb/cases/{id}/actions` | analyst action |
| POST | `/kyb/cases/{id}/risk` | recompute risk |
| POST | `/kyb/cases/{id}/explain` | AI explanation (on demand) |
| GET | `/kyb/cases/{id}/memory` | vector case memory |
| POST | `/kyb/cases/{id}/enrich` | on-demand web-intelligence enrichment (F4) |

---

## 9. Providers (swappable, env-driven)

- `REGISTRY_PROVIDER`: `mock` | `companies_house` (spec) | `us_sos`
- `CRAWLER_PROVIDER`: `mock` | `static` | `playwright` | `apify` | `tiered`
- `SUMMARIZER_PROVIDER`: `template` | `openrouter`
- `SEARCH_PROVIDER` (F4): `ddg` (free) | `crawl4ai` (cloud key) | `apify` (SERP)
- `CRAWLER_PROVIDER` also supports `crawl4ai` (open-source, LLM-ready markdown);
  the `tiered` chain is now static → crawl4ai → playwright → apify.
- `ENABLE_ENRICHMENT` toggle; `JUDGE_MODEL` / `JUDGE_MAX_ADJUST` for the judge.
- `ENABLE_VECTOR`, `ENABLE_PLAYWRIGHT` toggles.
- All behind frozen interfaces (`registry/base.py`, `webintel/crawler/base.py`,
  `webintel/summarizer/base.py`) → add a jurisdiction/source without touching risk.

---

## 10. How to run

```bash
# Backend
cd apps/api && pip install -r ../../requirements.txt
uvicorn app.main:app --reload            # http://127.0.0.1:8000/docs

# Dashboard
cd dashboard && pip install -r requirements.txt
streamlit run streamlit_app.py           # http://localhost:8501

# Tests
cd apps/api && python -m pytest tests/ -q   # 23 passing
```
Dev defaults are live (`us_sos` + `tiered` + `openrouter`). For instant offline
testing set `REGISTRY_PROVIDER=mock`. **Always pass a state** for US registry
lookups (nationwide search is slow); or omit it to get a web-presence review.

---

## 11. Known limits & roadmap

**Limits (honest):** US-only registry (Delaware/foreign gaps — SoS can't cover);
US UBO is a public-data gap; synchronous (~30–60s on live lookups); DDG social
search is flaky (page-link extraction is the reliable path); no sanctions/TIN yet;
Apify fallback crawler mapping not live-verified.

**Roadmap (priority):**
1. **Entity-resolution clustering** — cluster near-identical sites, rank to pick
   the real entity vs clones (don't reject clones — disambiguate).
2. **Watchlist/sanctions** (`watchlist_hits[]`) via **CompliAPI** + free OFAC SDN.
3. **OpenCorporates adapter** — DE/foreign/startup coverage.
4. **Async** processing (background + polling) to kill the spinner.
5. NAICS industry prediction; TIN/EIN match; ongoing monitoring; Neo4j network
   risk (shell-ring detection); production **Next.js** frontend (see `FRONTEND_TASK.md`).

---

## 12. Session history (what we did, in order)
1. Scoped MVP; chose build-fresh FastAPI spine; treated external KYB repos as
   reference, not dependencies.
2. Built Feature 1 (identity) with mock + frozen registry interface; verified.
3. Went US-first: wired Apify US SoS adapter (live-verified); handled US UBO gap.
4. Reviewed outsourced work (normalize good/misplaced, tests wrong-contract,
   devops not delivered) — fixed; added CORS.
5. Built Feature 2 (footprint): tiered crawler, domain intel, analyzer, summarizer.
6. Built Feature 3 (risk): scorecard, queue, actions; added ChromaDB vector +
   memory and scikit-learn ML anomaly; chose Chroma over Qdrant/Weaviate, skipped mem0.
7. Built Streamlit dashboard.
8. Hardened: dev auto-migration (no more schema 500s), env fixes, candidate
   token-overlap gate (no false matches), many robustness fixes.
9. Baselayer alignment (Phase A): two A–F scores, fuzzy match categories,
   decision object, `/report` endpoint, card + expandable report, `docs/API.md`.
10. Fixed clone false-positives (same-entity exclusion; clone → review not reject),
    status/decision consistency, AI chain-of-thought leak.
11. Footprint upgrades: active social lookup, RDAP domain age, LLM company
    profile, flexible no-state → web-presence review, AI loading effect.

12. **Registry resilience + Feature 4 (this session).** Diagnosed a live
    `apple inc`/CA F0-reject: Apify hit its monthly hard limit, so F1 never ran,
    yet the system scored the outage as max identity risk → reject. Fixed by
    distinguishing not-checked from verified-bad (`RegistryUnavailable`,
    `confidence=None`, review triggers, ownership skipped when registry absent,
    ML anomaly gated on sparse records). Added **Feature 4**: pluggable web
    search (`webintel/search/`: ddg/crawl4ai/apify), a Crawl4AI crawler backend,
    `enrich.py` (LLM structured extraction), `judge.py` (LLM-as-judge web
    presence, bounded ±15), `report_text.py` (narrative), auto-triggered from
    `create_case` on an unconfirmed registry + a `/enrich` endpoint. Report now
    has a PENDING KYB / provisional_review tri-state + enrichment block;
    dashboard renders it. 8 new resilience tests + `scripts/ab_eval.py` A/B
    harness (31 tests green).

_Backend + demo complete. Next session: production frontend._
