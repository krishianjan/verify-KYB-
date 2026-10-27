# Frontend build task (paste into v0 / Lovable / bolt.new / Cursor)

Paste the block below into a vibe-coding tool. It's written against the REAL
verifyKYB API contract so the UI wires straight to our backend.

---

> Build a KYB (Know Your Business) web app frontend with **Next.js (App Router) +
> TypeScript + Tailwind + shadcn/ui**. Clean, professional fintech/compliance
> look — think a risk-analyst console. Light and dark mode.
>
> It talks to a REST API at `http://127.0.0.1:8000` (CORS is already enabled for
> `http://localhost:3000`). Put the base URL in `NEXT_PUBLIC_API_BASE_URL`.
>
> ## Screens
>
> ### 1. Onboarding ( `/` )
> A form to submit a business for verification. Fields:
> - `legal_name` (text, required)
> - `state` (US state dropdown, 50 states + DC; optional but recommended — e.g. "CA")
> - `company_number` (text, optional)
> - `company_type` (text, optional)
> - `website` (url, optional)
> - `registered_address` (textarea, optional)
> - `incorporation_date` (date, optional)
>
> On submit → `POST /kyb/cases` with a JSON body of those fields. Show a loading
> state (the lookup can take 10–60s — it hits live registries). Then render the
> **Result view** (below) from the response.
>
> ### 2. Result view (component, reused on `/` and `/cases/[id]`)
> Render a `CaseOut` object:
> - A big **decision badge**: `auto_approve` = green, `manual_review` = amber,
>   `reject` = red. Show `assessment.confidence` as a 0–100% meter.
> - `assessment.summary` as a one-line explanation.
> - **Business card**: legal_name, jurisdiction, status, matched_company_number,
>   website, registered_address.
> - **Mismatches table** (`assessment.mismatches`): field, submitted_value,
>   registry_value, severity.
> - **Risk signals list** (`risk_signals`): color-code by severity
>   (info=gray, low=blue, medium=amber, high=red); show code + detail.
> - **Directors** (`directors`) and **Beneficial owners** (`beneficial_owners`)
>   as simple lists (may be empty — show "none on record").
> - A copyable case id (`business.id`).
>
> ### 3. Case lookup ( `/cases/[id]` )
> `GET /kyb/cases/{id}` → render the Result view. 404 → "Case not found".
>
> ### 4. Review queue ( `/queue` )  — build the UI; endpoint is COMING SOON
> A table of cases for analysts: columns = legal_name, jurisdiction, decision
> badge, confidence, status, created date, and a "Review" link to
> `/cases/[id]`. Add filter chips by decision (all / manual_review / reject /
> auto_approve). For now, **mock the list client-side** behind a
> `getCases()` function so it's trivial to swap to `GET /kyb/cases` later.
> On the case detail page, add analyst action buttons (Approve / Reject /
> Request documents / Escalate) with an optional notes textarea — wire them to a
> `postAction(caseId, action, notes)` stub for now (endpoint coming).
>
> ## API contracts (authoritative)
>
> `POST /kyb/cases`  (201)
> Request:
> ```json
> { "legal_name": "38 TESLA, LLC", "state": "CA", "company_number": null,
>   "company_type": null, "website": null, "registered_address": null,
>   "incorporation_date": null }
> ```
> Response `CaseOut`:
> ```json
> {
>   "business": {
>     "id": "hex-string", "legal_name": "38 TESLA, LLC", "company_number": null,
>     "company_type": "Limited Liability Company", "jurisdiction": "us-ca",
>     "website": null, "registered_address": "…", "incorporation_date": null,
>     "status": "auto_approved"
>   },
>   "assessment": {
>     "confidence": 1.0, "decision": "auto_approve",
>     "matched_company_number": "201300810165",
>     "summary": "Matched '38 TESLA, LLC' …",
>     "mismatches": [
>       { "field": "legal_name", "submitted_value": "…", "registry_value": "…",
>         "severity": "high", "detail": "…" }
>     ]
>   },
>   "directors": [
>     { "name": "SMITH, John", "role": "director", "appointed_on": "2019-03-15",
>       "resigned_on": null, "nationality": null }
>   ],
>   "beneficial_owners": [
>     { "name": "…", "kind": "…", "natures_of_control": ["…"],
>       "notified_on": "…", "ceased_on": null }
>   ],
>   "risk_signals": [
>     { "code": "NO_VERIFIED_UBO", "severity": "info", "weight": 0.0, "detail": "…" }
>   ]
> }
> ```
>
> `GET /kyb/cases/{id}` (200) → same `CaseOut`.  404 if not found.
>
> Enum values:
> - `assessment.decision`: `auto_approve` | `manual_review` | `reject`
> - `business.status`: `received` | `verifying` | `auto_approved` | `manual_review` | `approved` | `rejected`
> - `risk_signals[].severity` / `mismatches[].severity`: `info` | `low` | `medium` | `high`
>
> ## Requirements
> - TypeScript types for `CaseOut` and its parts.
> - A single `lib/api.ts` with `createCase()`, `getCase(id)`, `getCases()` (stub),
>   `postAction()` (stub), reading the base URL from env.
> - Graceful error + loading states. No backend code — frontend only.
> - Keep it a clean, demoable analyst console.

---

## Endpoints I (backend) will add so the queue/actions become real
- `GET /kyb/cases?decision=&status=&limit=` → list for the queue.
- `POST /kyb/cases/{id}/actions` → `{ "action": "approve|reject|request_docs|escalate", "notes": "…", "actor": "…" }` → records a ReviewAction + AuditEvent and updates status.

When those ship, the frontend just swaps its `getCases()` / `postAction()` stubs
for real fetches — shapes above are final.
