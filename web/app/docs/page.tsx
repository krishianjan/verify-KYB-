import { Suspense } from "react";
import Link from "next/link";
import { DocShell } from "@/components/docs/doc-shell";
import { CodeBlock } from "@/components/docs/code-block";

export const metadata = { title: "Documentation — verifyKYB" };

export default function DocsPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-6xl px-5 py-12" />}>
      <DocShell>
        <article className="max-w-2xl space-y-10">
          <header>
            <h1 className="text-3xl font-semibold tracking-tight">Documentation</h1>
            <p className="mt-3 text-muted-foreground">
              What verifyKYB does, how the workflow runs, and the words we use —
              in plain language.
            </p>
          </header>

          <Section id="overview" title="Overview">
            <P>
              <strong>KYB</strong> (Know Your Business) is the business version of
              KYC: before you let a company open an account, take payments, or
              borrow, you confirm it is real, legally registered, and not obviously
              risky. verifyKYB does that from a single submission and returns one
              explainable verdict — two letter grades and a recommended decision.
            </P>
            <P>
              You give us a legal name (and ideally a US state). We check official
              registries, analyze the company&apos;s online presence, optionally
              gather web intelligence, score the risk against a bank-style
              scorecard, and hand back a report you can act on or route to an
              analyst.
            </P>
          </Section>

          <Section id="waterfall" title="The waterfall">
            <P>
              The platform is a <em>waterfall</em>: each step builds on the one
              before it. A verified case unlocks the deeper checks.
            </P>
            <Steps
              steps={[
                ["Business Search", "Submit name + state. We query Secretary-of-State registries (all 50 states + DC)."],
                ["Identity Verification", "Fuzzy-match the name/address, prefer active entities, pull officers, score confidence, list mismatches."],
                ["Digital Footprint", "Crawl the site; read domain age, DNS/MX, TLS, reputation; raise ‘ghost-business’ signals; score legitimacy."],
                ["Web Intelligence", "If the registry can’t confirm the entity, scrape the open web (location, team, funding, news) and let an LLM judge the presence."],
                ["Risk & Review", "Merge everything into a weighted risk rating with reason codes; route to the review queue; record analyst actions."],
                ["Report", "Two A–F grades (KYB + Risk), match categories, a decision object, and a source-of-truth map."],
              ]}
            />
          </Section>

          <Section id="features" title="Features">
            <Feature tag="F1" name="Registry & identity">
              US Secretary-of-State lookups via an Apify actor, deterministic fuzzy
              matching (rapidfuzz), active-entity preference, officers, and a 0–1
              confidence with field-level mismatches. When the registry can&apos;t
              be reached or finds no match, identity is marked{" "}
              <strong>pending</strong> (not failed) and the case routes to review.
            </Feature>
            <Feature tag="F2" name="Digital footprint">
              Tiered crawling (static → Crawl4AI/Playwright → Apify), WHOIS/RDAP
              domain age, DNS/MX, TLS, urlscan reputation, and deterministic signals
              (domain too new, thin content, no contact info, parked page…) that
              produce a 0–100 legitimacy score and a verdict.
            </Feature>
            <Feature tag="F4" name="Web intelligence">
              An agent runs targeted web searches, scrapes the top pages to
              markdown, and an LLM extracts a structured profile (industry, HQ,
              team size, founders, funding, news) — evidence-only. A second LLM{" "}
              <em>judges</em> web presence as a complementary score. It never makes
              the decision.
            </Feature>
            <Feature tag="F3" name="Risk & workflow">
              A category-weighted scorecard (identity 45% / footprint 35% /
              ownership 20%), hard-stops, review triggers, reason codes, a review
              queue with filters, analyst actions, and an immutable audit trail.
            </Feature>
            <Feature tag="ML" name="Machine-learning signals">
              IsolationForest anomaly detection over the case population and a
              supervised scaffold trained on analyst decisions — both feed the
              scorecard as signals, never as the verdict.
            </Feature>
          </Section>

          <Section id="glossary" title="Glossary">
            <Gloss term="KYB rating">
              How well the business matches government records (identity confidence
              × 100), graded A–F. <strong>PENDING</strong> when the registry
              hasn&apos;t confirmed the entity yet.
            </Gloss>
            <Gloss term="Risk rating">
              Fraud/compliance safety (100 − internal risk), graded A–F.
            </Gloss>
            <Gloss term="Match category">
              Entity-resolution strength: EXACT ≥ 0.97, SIMILAR ≥ 0.80, PARTIAL ≥
              0.50, else NONE.
            </Gloss>
            <Gloss term="Provisional review">
              The best outcome for a case resting on web evidence alone — human
              review, never an automatic approve, until the registry confirms.
            </Gloss>
            <Gloss term="Reason code">
              A short, auditable tag for every factor in a decision (e.g.
              COMPANY_INACTIVE, REGISTRY_UNAVAILABLE, WEAK_WEB_FOOTPRINT).
            </Gloss>
          </Section>

          <Section id="compliance" title="Compliance stance">
            <P>
              Every decision is <strong>deterministic, rule-based, and
              auditable</strong> with reason codes — the posture regulators expect
              (SR 11-7, FCRA/ECOA adverse action, EU AI Act). Machine learning adds
              signals; the LLM explains and judges soft web evidence. Neither makes
              the call. An outage or a coverage gap is never treated as evidence
              against the business — it routes to review.
            </P>
            <P>
              Ready to see it? <Link href="/verify" className="underline">Verify a business</Link>{" "}
              or explore the <Link href="/docs/api" className="underline">API</Link>.
            </P>
          </Section>

          <CodeBlock
            label="quickstart"
            code={`# backend
cd apps/api && uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs

# this site
cd web && npm run dev                           # http://localhost:3000`}
          />
        </article>
      </DocShell>
    </Suspense>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-24">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="text-sm leading-relaxed text-foreground/80">{children}</p>;
}

function Steps({ steps }: { steps: [string, string][] }) {
  return (
    <ol className="mt-2 space-y-3">
      {steps.map(([t, d], i) => (
        <li key={t} className="flex gap-3">
          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-bold text-paper dark:bg-paper dark:text-ink">
            {i + 1}
          </span>
          <span className="text-sm leading-relaxed">
            <strong>{t}.</strong>{" "}
            <span className="text-muted-foreground">{d}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

function Feature({ tag, name, children }: { tag: string; name: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border p-4">
      <div className="flex items-center gap-2">
        <span className="rounded-md bg-ink px-1.5 py-0.5 font-mono text-[10px] font-bold text-paper dark:bg-paper dark:text-ink">
          {tag}
        </span>
        <h3 className="text-sm font-semibold">{name}</h3>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{children}</p>
    </div>
  );
}

function Gloss({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div className="border-l-2 border-border pl-4">
      <div className="text-sm font-semibold">{term}</div>
      <p className="text-sm leading-relaxed text-muted-foreground">{children}</p>
    </div>
  );
}
