"use client";

import { useState } from "react";
import type { ReportOut, ScoreOut } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  decisionMeta,
  gradeTone,
  matchTone,
} from "@/components/report/helpers";
import { cn } from "@/lib/utils";

export function ReportView({ report }: { report: ReportOut }) {
  const dm = decisionMeta(report.decision.action);
  const verifiedLabel =
    report.verified === "pending"
      ? "Pending"
      : report.verified
        ? "Verified"
        : "Not verified";
  const verifiedTone =
    report.verified === "pending" ? "muted" : report.verified ? "solid" : "outline";

  return (
    <div className="space-y-5">
      {/* Verdict header */}
      <Card>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-xs uppercase tracking-wide text-muted-foreground">
                Verification report
              </div>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight">
                {report.business.name}
              </h2>
            </div>
            <Badge tone={verifiedTone} className="px-3 py-1 text-sm">
              {verifiedLabel}
            </Badge>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {report.scores.map((s) => (
              <ScoreCard key={s.type} score={s} />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-4">
            <span className="text-sm text-muted-foreground">Recommendation</span>
            <Badge tone={dm.tone} className="px-3 py-1 text-sm">
              {dm.label}
            </Badge>
          </div>
          {report.decision.reasoning && (
            <p className="text-sm leading-relaxed text-foreground/80">
              {report.decision.reasoning}
            </p>
          )}
          <CopyId id={report.id} />
        </CardContent>
      </Card>

      {report.warnings.length > 0 && (
        <div className="space-y-2">
          {report.warnings.map((w, i) => (
            <div
              key={i}
              className="flex gap-2 rounded-xl border border-grey-300 bg-muted px-4 py-3 text-sm dark:border-grey-700"
            >
              <span aria-hidden>⚠</span>
              <span className="text-foreground/80">{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Entity resolution */}
      <Section title="Entity resolution">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">Name match</span>
          <Badge tone={matchTone(report.business_name_match)}>
            {report.business_name_match}
          </Badge>
          {report.name_match_score != null && (
            <span className="font-mono text-xs text-muted-foreground">
              {report.name_match_score.toFixed(2)}
            </span>
          )}
          {report.business_address_match && (
            <>
              <span className="ml-3 text-muted-foreground">Address</span>
              <Badge tone={matchTone(report.business_address_match)}>
                {report.business_address_match}
              </Badge>
            </>
          )}
        </div>
      </Section>

      {/* Business block */}
      <Section title="Business">
        <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
          <Row k="Legal name" v={report.business.name} />
          <Row k="Structure" v={report.business.structure} />
          <Row k="Registry status" v={report.business.status} />
          <Row
            k="In business"
            v={
              report.business.months_in_business != null
                ? `${report.business.months_in_business} months`
                : null
            }
          />
          {report.business.registrations[0] && (
            <Row
              k="Registration"
              v={[
                report.business.registrations[0].state,
                report.business.registrations[0].status,
                report.business.registrations[0].filing_date,
              ]
                .filter(Boolean)
                .join(" · ")}
            />
          )}
        </dl>
        {report.business.officers.length > 0 && (
          <div className="mt-4">
            <div className="mb-1.5 text-xs font-medium text-muted-foreground">
              Officers
            </div>
            <ul className="space-y-1 text-sm">
              {report.business.officers.map((o, i) => (
                <li key={i}>
                  {o.name}
                  {o.role ? ` — ${o.role}` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      {report.digital_footprint && (
        <FootprintPanel fp={report.digital_footprint} />
      )}
      {report.enrichment && <EnrichmentPanel e={report.enrichment} />}

      {Object.keys(report.sources).length > 0 && (
        <Section title="Source of truth">
          <pre className="overflow-x-auto rounded-xl bg-muted p-4 font-mono text-xs text-foreground/80">
            {JSON.stringify(report.sources, null, 2)}
          </pre>
        </Section>
      )}
    </div>
  );
}

function ScoreCard({ score }: { score: ScoreOut }) {
  const label =
    score.type === "kyb"
      ? "KYB rating"
      : score.type === "risk"
        ? "Risk rating"
        : "Web presence";
  return (
    <div className="rounded-xl border border-border p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <Badge tone={gradeTone(score.rating)} className="px-2.5 py-1 text-base">
          {score.rating}
        </Badge>
        {score.score != null && (
          <span className="font-mono text-2xl font-semibold tabular-nums">
            {score.score}
          </span>
        )}
      </div>
    </div>
  );
}

function FootprintPanel({ fp }: { fp: NonNullable<ReportOut["digital_footprint"]> }) {
  return (
    <Section title="Digital footprint">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge tone="outline">{fp.verdict}</Badge>
        <span className="text-muted-foreground">
          legitimacy <span className="font-mono text-foreground">{fp.legitimacy_score}</span>/100
        </span>
        {fp.web_presence_score != null && (
          <span className="text-muted-foreground">
            · web presence{" "}
            <span className="font-mono text-foreground">{fp.web_presence_score}</span>/100
          </span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
        {fp.domain && <span>domain {fp.domain}</span>}
        {fp.domain_age_days != null && <span>age {fp.domain_age_days}d</span>}
        {fp.has_tls != null && <span>TLS {fp.has_tls ? "yes" : "no"}</span>}
      </div>
      {Object.keys(fp.social_links || {}).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          {Object.entries(fp.social_links).map(([k, v]) => (
            <a
              key={k}
              href={v}
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-border px-3 py-1 hover:bg-muted"
            >
              {k}
            </a>
          ))}
        </div>
      )}
      {fp.profile_summary && (
        <p className="mt-3 text-sm leading-relaxed text-foreground/80">
          {fp.profile_summary}
        </p>
      )}
      {fp.screenshot_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={fp.screenshot_url}
          alt="Website screenshot"
          className="mt-4 w-full rounded-xl border border-border"
        />
      )}
    </Section>
  );
}

function EnrichmentPanel({ e }: { e: NonNullable<ReportOut["enrichment"]> }) {
  const people = [...(e.founders || []), ...(e.executives || [])];
  return (
    <Section title="Web intelligence">
      {e.narrative && (
        <p className="text-sm leading-relaxed text-foreground/80">{e.narrative}</p>
      )}
      <dl className="mt-3 grid gap-x-8 gap-y-3 sm:grid-cols-2">
        <Row k="Industry" v={e.industry} />
        <Row k="Headquarters" v={e.hq} />
        <Row k="Team size" v={e.employee_range} />
        <Row k="Founded" v={e.founded_year} />
        <Row k="Locations" v={e.locations?.length ? e.locations.join(", ") : null} />
        <Row k="People" v={people.length ? people.join(", ") : null} />
      </dl>
      {e.funding?.length > 0 && (
        <div className="mt-4">
          <div className="mb-1.5 text-xs font-medium text-muted-foreground">Funding</div>
          <ul className="space-y-1 text-sm">
            {e.funding.map((f, i) => (
              <li key={i}>
                {[f.round, f.amount, f.date].filter(Boolean).join(" · ") || "reported"}
                {f.source && (
                  <a
                    href={f.source}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-2 underline decoration-dotted"
                  >
                    source
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {e.recent_news?.length > 0 && (
        <div className="mt-4">
          <div className="mb-1.5 text-xs font-medium text-muted-foreground">Recent news</div>
          <ul className="space-y-1 text-sm">
            {e.recent_news.map((n, i) => (
              <li key={i}>
                <a
                  href={n.url || "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="underline decoration-dotted"
                >
                  {n.title || n.url}
                </a>
                {n.date ? ` — ${n.date}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
      {e.presence_score != null && (
        <p className="mt-4 rounded-xl bg-muted px-4 py-3 text-xs text-muted-foreground">
          LLM web-presence judgment: <span className="font-mono text-foreground">{e.presence_score}</span>/100
          {e.judge_confidence ? ` (confidence: ${e.judge_confidence})` : ""} — a
          complementary signal. The decision stays deterministic.
          {e.judge_rationale ? ` ${e.judge_rationale}` : ""}
        </p>
      )}
    </Section>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardContent>
        <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function Row({ k, v }: { k: string; v: string | null | undefined }) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs text-muted-foreground">{k}</dt>
      <dd className={cn("text-sm", !v && "text-grey-400")}>{v || "not found"}</dd>
    </div>
  );
}

function CopyId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard?.writeText(id);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      className="inline-flex items-center gap-2 font-mono text-xs text-muted-foreground hover:text-foreground"
    >
      case {id.slice(0, 12)}… {copied ? "✓ copied" : "⧉ copy"}
    </button>
  );
}
