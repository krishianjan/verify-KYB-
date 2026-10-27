"use client";

import { useState } from "react";
import Link from "next/link";
import { createCase, getReport, runEnrich, ApiError } from "@/lib/api";
import type { ReportOut } from "@/lib/types";
import { US_STATES } from "@/lib/states";
import { Button } from "@/components/ui/button";
import { Input, Label, Select, Textarea } from "@/components/ui/field";
import { Card, CardContent } from "@/components/ui/card";
import { Verifying } from "@/components/verifying";
import { ReportView } from "@/components/report/report-view";

type Phase = "form" | "loading" | "done" | "error";

export default function VerifyPage() {
  const [phase, setPhase] = useState<Phase>("form");
  const [report, setReport] = useState<ReportOut | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [error, setError] = useState<string>("");
  const [enriching, setEnriching] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const str = (k: string) => {
      const v = (f.get(k) as string)?.trim();
      return v ? v : null;
    };
    const legal_name = str("legal_name");
    if (!legal_name) return;

    setPhase("loading");
    setError("");
    try {
      const created = await createCase({
        legal_name,
        state: str("state"),
        company_number: str("company_number"),
        company_type: str("company_type"),
        website: str("website"),
        registered_address: str("registered_address"),
        incorporation_date: str("incorporation_date"),
      });
      setCaseId(created.business.id);
      setReport(await getReport(created.business.id));
      setPhase("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setPhase("error");
    }
  }

  async function onEnrich() {
    if (!caseId) return;
    setEnriching(true);
    try {
      await runEnrich(caseId);
      setReport(await getReport(caseId));
    } catch {
      /* surfaced as no-op; report stays */
    } finally {
      setEnriching(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">Verify a business</h1>
        <p className="mt-2 text-muted-foreground">
          One submission in, one explainable verdict out. Only the legal name is
          required — a US state makes the registry lookup faster and sharper.
        </p>
      </div>

      {phase === "form" || phase === "error" ? (
        <Card>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-5">
              <div>
                <Label htmlFor="legal_name">Legal business name *</Label>
                <Input id="legal_name" name="legal_name" required placeholder="Apple Inc" />
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                <div>
                  <Label htmlFor="state">US state (recommended)</Label>
                  <Select id="state" name="state" defaultValue="">
                    <option value="">— nationwide / web presence —</option>
                    {US_STATES.map((s) => (
                      <option key={s.code} value={s.code}>
                        {s.name}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <Label htmlFor="company_number">Company number (optional)</Label>
                  <Input id="company_number" name="company_number" placeholder="e.g. 201300810165" />
                </div>
                <div>
                  <Label htmlFor="company_type">Company type (optional)</Label>
                  <Input id="company_type" name="company_type" placeholder="LLC, Corp…" />
                </div>
                <div>
                  <Label htmlFor="website">Website (optional)</Label>
                  <Input id="website" name="website" placeholder="https://apple.com" />
                </div>
              </div>
              <div>
                <Label htmlFor="registered_address">Registered address (optional)</Label>
                <Textarea id="registered_address" name="registered_address" />
              </div>
              <div className="sm:w-1/2">
                <Label htmlFor="incorporation_date">Incorporation date (optional)</Label>
                <Input id="incorporation_date" name="incorporation_date" type="date" />
              </div>

              {phase === "error" && (
                <div className="rounded-xl border border-grey-300 bg-muted px-4 py-3 text-sm dark:border-grey-700">
                  {error}
                </div>
              )}

              <Button type="submit" size="lg" className="w-full sm:w-auto">
                Run verification
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {phase === "loading" && (
        <div className="py-8">
          <Verifying />
        </div>
      )}

      {phase === "done" && report && (
        <div className="space-y-5">
          <ReportView report={report} />
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" onClick={onEnrich} disabled={enriching}>
              {enriching ? "Gathering…" : "Run web intelligence"}
            </Button>
            {caseId && (
              <Link href={`/cases/${caseId}`} className="text-sm underline decoration-dotted">
                Open permalink
              </Link>
            )}
            <Button
              variant="ghost"
              onClick={() => {
                setPhase("form");
                setReport(null);
                setCaseId(null);
              }}
            >
              Verify another
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
