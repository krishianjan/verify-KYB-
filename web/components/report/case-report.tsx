"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getReport, ApiError } from "@/lib/api";
import type { ReportOut } from "@/lib/types";
import { ReportView } from "@/components/report/report-view";
import { Button } from "@/components/ui/button";

export function CaseReport({ id }: { id: string }) {
  const [report, setReport] = useState<ReportOut | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getReport(id)
      .then((r) => alive && setReport(r))
      .catch(
        (e) => alive && setError(e instanceof ApiError ? e.message : "Failed to load"),
      )
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [id]);

  if (loading) return <p className="text-muted-foreground">Loading case…</p>;
  if (error)
    return (
      <div className="rounded-xl border border-border bg-muted p-6">
        <p className="font-medium">{error}</p>
        <Link href="/verify" className="mt-3 inline-block">
          <Button variant="outline" size="sm">
            Verify a business
          </Button>
        </Link>
      </div>
    );
  return report ? <ReportView report={report} /> : null;
}
