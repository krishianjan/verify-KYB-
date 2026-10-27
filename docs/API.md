# verifyKYB — API & Implementation Guide

A single API call verifies a business against official registries, analyzes its
digital footprint, scores risk, and returns one structured verdict.

Base URL (local): `http://127.0.0.1:8000` · Interactive docs: `/docs`
Auth: none in v1 (add an API key/gateway before production).

---

## Quickstart

```bash
curl -s -X POST http://127.0.0.1:8000/kyb/cases \
  -H 'content-type: application/json' \
  -d '{"legal_name":"ACME PAYMENTS LLC","state":"DE"}'
# -> returns a case with identity verification + combined risk

# Customer-facing report (two letter grades, match categories, decision):
curl -s http://127.0.0.1:8000/kyb/cases/<id>/report
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/kyb/cases` | Create + verify a business (identity + risk). |
| GET  | `/kyb/cases/{id}` | Full case (raw assessment, signals, directors). |
| GET  | `/kyb/cases/{id}/report` | **Customer report** (Baselayer-shaped). |
| POST | `/kyb/cases/{id}/footprint` | Run digital-footprint analysis. |
| POST | `/kyb/cases/{id}/explain` | AI plain-English explanation (on demand). |
| GET  | `/kyb/cases` | Review queue (filter: status, rating, decision). |
| POST | `/kyb/cases/{id}/actions` | Analyst action (approve/reject/request_docs/escalate). |
| POST | `/kyb/cases/{id}/risk` | Recompute the combined risk score. |
| GET  | `/kyb/cases/{id}/memory` | Prior findings (vector memory). |

### POST /kyb/cases — request
```json
{ "legal_name": "ACME PAYMENTS LLC", "state": "DE",
  "company_number": null, "website": "https://acme.example",
  "registered_address": null, "incorporation_date": null }
```
`state` strongly recommended for US (narrows the registry search; a nationwide
search is slow). `website` optional — footprint can auto-discover one.

### GET /kyb/cases/{id}/report — response (the customer verdict)
```json
{
  "id": "…", "state": "COMPLETED", "verified": true,
  "business_name_match": "SIMILAR", "business_address_match": "EXACT",
  "name_match_score": 0.94, "tin_matched": null,
  "scores": [
    { "type": "kyb",  "score": 86, "rating": "B" },
    { "type": "risk", "score": 92, "rating": "A" }
  ],
  "business": {
    "name": "ACME PAYMENTS LLC", "structure": "LLC", "status": "active",
    "months_in_business": 42,
    "registrations": [{ "type": "domestic", "state": "DE",
                        "status": "active", "filing_date": "2021-06-15" }],
    "officers": [{ "name": "JOHN SMITH", "title": "MANAGER" }]
  },
  "watchlist_hits": [],
  "digital_footprint": { "verdict": "real", "legitimacy_score": 88,
    "domain": "acme.example", "domain_age_days": 1520, "has_tls": true,
    "social_profiles": ["linkedin"], "screenshot_url": "…" },
  "decision": { "action": "auto_approve", "confidence": 0.86,
                "reasoning": "Matched an active DE LLC (SIMILAR name, EXACT address)…" },
  "sources": { "registry": { "source": "us_sos", "uri": "…" },
               "digital_footprint": { "crawler": "static" },
               "reputation": { "source": "urlscan.io" } },
  "warnings": []
}
```

## How the two scores work

- **KYB rating (A–F)** — *how well the business matches official government
  records.* Driven by whether it was found, the fuzzy name/address match quality,
  and registration completeness. Derived from identity confidence.
- **Risk rating (A–F)** — *how likely it is to be fraud / compliance risk.*
  Driven by the deterministic risk engine (digital footprint, ownership data,
  anomaly detection, hard-stop signals). Shown as `100 − internal risk`.

Letter bands: A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, else F.

### Match categories (entity resolution)
Fuzzy name/address similarity is bucketed:
`EXACT` ≥ 0.97 · `SIMILAR` ≥ 0.80 · `PARTIAL` ≥ 0.50 · `NONE` < 0.50.

## Decision logic (recommended)
```
no confident registry match        -> reject ("not found")
company inactive / number mismatch  -> reject (hard stop)
watchlist hit                        -> reject (planned: CompliAPI/OFAC)
KYB >= B and Risk >= B               -> auto_approve
otherwise                            -> manual_review
```

## Design principles
- **Deterministic, auditable decisions** — the risk engine and signals are
  rule-based with reason codes; the LLM only writes explanations, never the
  verdict. (Meets explainability expectations: SR 11-7, FCRA/ECOA, EU AI Act.)
- **Provider abstraction** — registries and crawlers sit behind frozen
  interfaces; adding a jurisdiction or data source doesn't touch the risk layer.
- **Source of truth** — every report carries a `sources` map so each fact is
  traceable to its origin.

## Status / roadmap
- Live: US Secretary-of-State (Apify), digital footprint (crawl + domain + urlscan),
  risk engine, review queue, analyst actions, vector memory, ML anomaly.
- Planned: watchlist/sanctions (`watchlist_hits`, CompliAPI/OFAC), TIN/EIN match,
  NAICS industry prediction, OpenCorporates coverage (DE/foreign), ongoing monitoring.
