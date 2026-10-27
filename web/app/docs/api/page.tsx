import { Suspense } from "react";
import { DocShell } from "@/components/docs/doc-shell";
import { CodeBlock } from "@/components/docs/code-block";
import { TryIt } from "@/components/docs/try-it";
import { Badge } from "@/components/ui/badge";

export const metadata = { title: "API reference — verifyKYB" };

const ENDPOINTS: {
  method: "GET" | "POST";
  path: string;
  desc: string;
  sample?: string;
}[] = [
  { method: "GET", path: "/health", desc: "Service status + active registry provider." },
  {
    method: "POST",
    path: "/kyb/cases",
    desc: "Create a case and run identity + risk. Auto-runs web intelligence when the registry can’t confirm the entity. Returns a CaseOut.",
    sample: `{
  "legal_name": "Apple Inc",
  "state": "CA",
  "company_number": null,
  "website": null
}`,
  },
  { method: "GET", path: "/kyb/cases/{id}", desc: "Full raw case (CaseOut)." },
  {
    method: "GET",
    path: "/kyb/cases/{id}/report",
    desc: "Customer-facing verdict (ReportOut): two A–F grades, match categories, decision, enrichment, warnings, sources.",
  },
  {
    method: "POST",
    path: "/kyb/cases/{id}/footprint",
    desc: "Run the digital-footprint pipeline (crawl + domain intel + web intelligence) and recompute risk.",
  },
  { method: "GET", path: "/kyb/cases/{id}/footprint", desc: "Latest footprint (FootprintOut)." },
  {
    method: "POST",
    path: "/kyb/cases/{id}/enrich",
    desc: "On-demand web-intelligence enrichment: scrape, parse, judge presence, recompute risk.",
  },
  { method: "GET", path: "/kyb/cases", desc: "Review queue. Filters: status, rating, decision, limit." },
  {
    method: "POST",
    path: "/kyb/cases/{id}/actions",
    desc: "Analyst action.",
    sample: `{ "action": "approve", "notes": "ok", "actor": "alice" }`,
  },
  { method: "POST", path: "/kyb/cases/{id}/risk", desc: "Recompute the combined risk score." },
  { method: "POST", path: "/kyb/cases/{id}/explain", desc: "On-demand AI narrative of the risk decision." },
  { method: "GET", path: "/kyb/cases/{id}/memory", desc: "Vector case memory (recall)." },
];

export default function ApiPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-6xl px-5 py-12" />}>
      <DocShell>
        <article className="max-w-2xl space-y-8">
          <header>
            <h1 className="text-3xl font-semibold tracking-tight">API discovery</h1>
            <p className="mt-3 text-muted-foreground">
              A REST API. Base URL is <code className="font-mono">NEXT_PUBLIC_API_BASE_URL</code>{" "}
              (defaults to <code className="font-mono">http://127.0.0.1:8000</code>). Full
              OpenAPI docs live at <code className="font-mono">/docs</code> on the backend.
            </p>
          </header>

          <section>
            <h2 className="mb-3 text-xl font-semibold tracking-tight">Try it live</h2>
            <TryIt />
          </section>

          <section>
            <h2 className="mb-4 text-xl font-semibold tracking-tight">Endpoints</h2>
            <div className="space-y-3">
              {ENDPOINTS.map((e) => (
                <div key={e.method + e.path} className="rounded-xl border border-border p-4">
                  <div className="flex items-center gap-2">
                    <Badge tone={e.method === "POST" ? "solid" : "mid"}>{e.method}</Badge>
                    <code className="font-mono text-sm">{e.path}</code>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{e.desc}</p>
                  {e.sample && <CodeBlock className="mt-3" label="request" code={e.sample} />}
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-semibold tracking-tight">Enums</h2>
            <CodeBlock
              label="values"
              code={`decision        auto_approve | manual_review | reject
report action   auto_approve | manual_review | provisional_review | reject
severity        info | low | medium | high
match category  EXACT | SIMILAR | PARTIAL | NONE
verified        true | false | "pending"
kyb rating      A | B | C | D | F | PENDING`}
            />
          </section>
        </article>
      </DocShell>
    </Suspense>
  );
}
