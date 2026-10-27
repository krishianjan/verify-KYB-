# verifyKYB dashboard (Streamlit)

Temporary analyst console for exercising the API — onboard a business, view the
combined risk + identity + footprint, and run the analyst review queue/actions.

## Run
1. Start the backend (in `apps/api`):
   ```bash
   cd ../apps/api && uvicorn app.main:app --reload
   ```
2. Start the dashboard (from this folder):
   ```bash
   pip install -r requirements.txt
   streamlit run streamlit_app.py
   ```
   Opens http://localhost:8501

Point at a non-default backend with `VERIFYKYB_API_BASE=http://host:port`.

## Pages
- **Onboard** — submit a business (name, state, number, website) → identity + risk.
- **Case detail** — risk score, signals, identity, directors/UBOs; run digital
  footprint (crawl + domain + urlscan screenshot + AI summary); analyst actions
  (approve / reject / request docs / escalate); case memory.
- **Review queue** — filterable list of cases; open any into Case detail.

Real data flows when the backend runs with `REGISTRY_PROVIDER=us_sos`,
`CRAWLER_PROVIDER=tiered`, `SUMMARIZER_PROVIDER=openrouter` (the defaults in `.env`).
