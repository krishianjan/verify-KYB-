# Verify KYB

Open-source KYB (Know Your Business) verification platform for fintech, merchant onboarding, compliance, AML, business due diligence, and company risk assessment.

<img width="1376" height="768" alt="KYB_project_Image" src="https://github.com/user-attachments/assets/06f1c082-0c5a-4705-aeef-361384eeb57f" />








verifyKYB is a real-world KYB project for identifying and verifying businesses, merchants, and companies before onboarding them into financial products, payment systems, banking workflows, and risk review pipelines. It combines company verification, digital footprint analysis, risk scoring, and AI-assisted review to help teams automate KYB checks with explainable decision-making.

This repository is designed for developers, fintech teams, compliance professionals, risk analysts, and builders who want an open-source foundation for KYB software, merchant onboarding workflows, business verification systems, and AI-powered compliance automation.

---

## Why this project matters

KYB (Know Your Business) is one of the most important compliance workflows in fintech, payments, banking, and merchant onboarding. Companies need to verify that the businesses they onboard are legitimate, operational, and low risk.

Traditional KYB processes are often:
- manual
- inconsistent
- slow
- fragmented across tools
- difficult to scale
- hard to explain to auditors and analysts

verifyKYB solves this by combining:
- registry-based verification
- digital footprint checks
- reputation and domain intelligence
- risk scoring
- report generation
- analyst review workflows
- AI-assisted explainability

This makes it useful for:
- fintech startups
- payment platforms
- banking partners
- merchant onboarding teams
- compliance operations
- AML and KYC workflows
- vendor due diligence
- business verification tools
- risk screening systems

---

## What is KYB?

KYB stands for Know Your Business. It is the process of verifying the identity, legitimacy, ownership, and risk of a business before accepting it as a customer, merchant, vendor, or partner.

Common KYB use cases include:
- merchant onboarding
- fintech business verification
- payment partner screening
- supplier due diligence
- vendor risk assessment
- AML and sanctions screening support
- compliance review
- business identity validation
- company risk scoring

## Project goals

verifyKYB aims to provide a practical open-source workflow for:

1. verifying company identity
2. checking legal existence and registration
3. gathering company and merchant data
4. crawling and evaluating digital footprint
5. scoring risk and compliance signals
6. generating explainable KYB reports
7. routing uncertain cases for analyst review
8. creating reusable foundations for AI-driven compliance systems

---

## Core features

### 1. Company and merchant verification
- identify business entities
- verify legal registration
- resolve company names and addresses
- assess match quality
- detect mismatches and inconsistencies

### 2. Registry-based checks
- official business registry lookups
- legal status verification
- company metadata extraction
- officers and directors review
- beneficial ownership signals where available

### 3. Digital footprint analysis
- domain and website verification
- WHOIS / RDAP checks
- DNS and TLS insights
- social presence detection
- website legitimacy analysis
- ghost business signal detection
- business profile synthesis

### 4. Risk scoring
- weighted risk model
- explainable reason codes
- review triggers
- deterministic scoring
- risk grade generation
- confidence-based decisions

### 5. Analyst workflow
- review queue
- escalation paths
- manual decision support
- audit trail
- approval / reject / request documents workflows

### 6. AI-powered explanation layer
- structured explanations for human readers
- narrative summaries
- AI-generated reasoning
- evidence-backed explainability
- assistive analysis for analysts

### 7. Report generation
- KYB report output
- business summary
- transparency on sources
- risk findings
- match quality and evidence summary

### 8. AI agent architecture
This project is designed to be expanded into agentic workflows for:
- background data collection
- company enrichment
- web intelligence gathering
- structured evidence extraction
- explanation and summarization
- automated next-step recommendations

---

## Why this repo is useful for AI and automation

This project is intended to support:
- AI agents for compliance workflows
- rule-based verification pipelines
- autonomous research agents
- structured evidence extraction
- AI-assisted risk reviews
- LLM explanations with deterministic decision control

Important design principle:
- AI explains and supports the review
- the final decision remains auditable and rule-based
- the workflow is not dependent on opaque black-box decisions

This is important for real-world compliance and finance environments where traceability matters.

---

## Typical architecture

The system is structured around a pipeline:

1. Receive business submission
2. Validate submitted company or merchant information
3. Run registry and identity checks
4. Gather digital footprint data
5. Review domain, web presence, and business signals
6. Compute risk using deterministic scoring
7. Generate explainable result and report
8. Route uncertain cases to analyst review

```text
Submission
   ↓
Identity verification
   ↓
Digital footprint analysis
   ↓
Risk scoring engine
   ↓
Report generation
   ↓
Manual review / approval / reject
```

---

## Tech stack

| Layer | Technology |
|------|------------|
| API | FastAPI |
| Validation | Pydantic |
| Database | SQLAlchemy + SQLite / Postgres |
| Matching | rapidfuzz |
| Web scraping | httpx, BeautifulSoup, Playwright |
| Domain intelligence | python-whois, RDAP, dnspython |
| Reputation checks | urlscan.io |
| AI / LLM support | OpenRouter |
| Vector memory | ChromaDB |
| Machine learning | scikit-learn |
| Dashboard | Streamlit |
| Async / background tasks | extendable for future rollout |

---

## Main project goals

verifyKYB is meant to be:
- open source
- practical
- production-minded
- explainable
- modular
- extendable
- relevant to real fintech and compliance workflows
- useful for learning and building real business verification systems

---

## Example KYB workflow

A typical verification flow looks like this:

1. Business submits company or merchant details
2. System checks the legal existence of the business
3. Data is matched against registry information
4. Company name, address, and ownership are compared
5. Domain and website are reviewed
6. Reputation and footprint signals are computed
7. Risk score is generated
8. A KYB report is produced
9. If there are uncertain signals, the case is routed for analyst review

---

## Repository vision

This repository is intended as a strong open-source foundation for:

- KYB verification platforms
- merchant onboarding software
- business identity systems
- financial compliance tooling
- AI-assisted due diligence
- fintech startup projects
- risk scoring dashboards
- startup compliance automation
- real-world KYB agent workflows

---

## Why this repo can stand out

This project is valuable because it sits at the intersection of:
- fintech
- compliance
- automation
- AI
- merchant onboarding
- corporate verification
- risk scoring
- open-source engineering

That makes it attractive for:
- open-source contributors
- fintech builders
- product teams
- startups
- compliance engineers
- risk analysts
- developers exploring business verification systems

---

## Quick start

```bash
git clone https://github.com/krishianjan/verify-KYB-.git
cd verify-KYB-
```

Then install dependencies and run the application according to the local environment configuration.

```bash
pip install -r requirements.txt
```

Run the API:

```bash
cd apps/api
uvicorn app.main:app --reload
```

Visit:
- Swagger docs: http://127.0.0.1:8000/docs

Run the dashboard:

```bash
cd dashboard
streamlit run streamlit_app.py
```

---

## Project structure

```text
verifyKYB/
├── apps/
│   └── api/
│       ├── app/
│       ├── tests/
│       └── scripts/
├── dashboard/
├── docs/
├── README.md
├── requirements.txt
├── FRONTEND_TASK.md
├── OUTSOURCE_TASKS.md
├── .env.example
└── ...
```

---

## Use cases

### Fintech
- verify merchants before onboarding
- evaluate compliance risk before releasing accounts
- review payment and business customers

### Banking
- support business onboarding workflows
- reduce manual verification burden
- assess operational legitimacy

### Risk and compliance teams
- monitor business risk
- review suspicious onboarding cases
- create explainable intervention workflows

### Startups
- build KYB features without starting from zero
- prototype merchant onboarding systems
- create a compliance workflow foundation

---

## AI and compliance alignment

This repository is designed to respect real-world compliance needs:

- deterministic decisions where possible
- explainable output
- reason codes and evidence
- analyst review for unresolved cases
- AI assistance without replacing auditable decision logic

This is essential for serious financial and compliance products.

---

## Roadmap

Planned improvements include:

- stronger registry integration
- more jurisdictions and country adapters
- better entity matching
- sanctions and watchlist checks
- improved risk scoring
- enhanced analyst review flow
- AI-powered evidence summarization
- real-time monitoring and periodic re-checks
- production dashboard and frontend
- API-first architecture for easier integration

---

## Contribution

Contributions are welcome.

You can help by:
- improving registry matching
- enhancing risk scoring
- improving data collection and scraping
- improving report quality
- adding better onboarding flows
- building analytics and dashboards
- adding tests
- documenting architecture
- expanding use cases

---

## FAQ

### What is KYB?
KYB stands for Know Your Business. It is the process of verifying the identity and legitimacy of a business before onboarding it.

### Why is KYB important?
KYB helps reduce fraud, financial crime, onboarding risk, and bad business relationships.

### Is this project only for fintech?
No. It is useful for any business that needs to assess the legitimacy and risk of a company, merchant, partner, or vendor.

### Is this AI-powered?
It can be enhanced with AI-assisted explanations, summaries, and evidence extraction, but the decision logic remains auditable and rule-based.

### Is this open source?
Yes. The repository is designed as an open-source KYB project and starter framework.

---

## Keywords

KYB, Know Your Business, KYB verification, open-source KYB, merchant onboarding, fintech compliance, AML, company verification, business verification, merchant verification, due diligence, risk scoring, risk assessment, AI KYB, KYB agents, compliance automation, fintech risk, company risk, business onboarding, Open-source fintech tools, financial compliance automation, KYB platform, AI-assisted KYB, open-source compliance project, business onboarding workflow, merchant risk scoring

---

## Final note

verifyKYB is a practical, real-world open-source project for anyone building around KYB, fintech compliance, merchant onboarding, company verification, and business due diligence workflows.

The goal is not just to build a demo. The goal is to create a useful, extensible, searchable, and production-minded KYB foundation that can evolve into a serious compliance and risk automation platform.

If you want this project to be discovered by people looking for KYB, fintech compliance, merchant onboarding, and AI-powered business verification, this README structure and keyword strategy matter just as much as the code itself.
