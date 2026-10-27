"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { listCases, postAction, ApiError } from "@/lib/api";
import type { CaseListItem } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { decisionMeta } from "@/components/report/helpers";
import { cn } from "@/lib/utils";

const FILTERS = [
  { label: "All", value: "" },
  { label: "Review", value: "manual_review" },
  { label: "Approved", value: "auto_approved" },
  { label: "Rejected", value: "rejected" },
];

const ACTIONS = [
  { label: "Approve", value: "approve" },
  { label: "Reject", value: "reject" },
  { label: "Request docs", value: "request_docs" },
  { label: "Escalate", value: "escalate" },
] as const;

export default function QueuePage() {
  const [items, setItems] = useState<CaseListItem[]>([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    listCases({ status: status || undefined, limit: 100 })
      .then((r) => setItems(r.items))
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  async function act(id: string, action: (typeof ACTIONS)[number]["value"]) {
    setBusy(id);
    try {
      await postAction(id, action);
      load();
    } catch {
      /* ignore; reload shows current state */
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Review queue</h1>
          <p className="mt-2 text-muted-foreground">
            Cases routed for analyst review, with full decision context and actions.
          </p>
        </div>
        <Link href="/verify">
          <Button size="sm">New verification</Button>
        </Link>
      </div>

      <div className="mb-5 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatus(f.value)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-sm transition-colors",
              status === f.value
                ? "border-ink bg-ink text-paper dark:border-paper dark:bg-paper dark:text-ink"
                : "border-border hover:bg-muted",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <p className="text-muted-foreground">Loading queue…</p>}
      {error && !loading && (
        <Card>
          <CardContent>
            <p className="font-medium">{error}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Start the backend: <code className="font-mono">uvicorn app.main:app --reload</code>
            </p>
          </CardContent>
        </Card>
      )}

      {!loading && !error && items.length === 0 && (
        <Card>
          <CardContent className="text-muted-foreground">
            No cases yet. <Link href="/verify" className="underline">Verify one</Link> to populate the queue.
          </CardContent>
        </Card>
      )}

      {!loading && items.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Business</th>
                <th className="px-4 py-3 font-medium">Decision</th>
                <th className="px-4 py-3 font-medium">Confidence</th>
                <th className="px-4 py-3 font-medium">Risk</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => {
                const dm = decisionMeta(it.identity_decision || "");
                return (
                  <tr key={it.id} className="border-t border-border align-middle">
                    <td className="px-4 py-3">
                      <Link href={`/cases/${it.id}`} className="font-medium hover:underline">
                        {it.legal_name}
                      </Link>
                      <div className="text-xs text-muted-foreground">{it.jurisdiction}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={dm.tone}>{dm.label}</Badge>
                    </td>
                    <td className="px-4 py-3 font-mono tabular-nums text-muted-foreground">
                      {it.identity_confidence == null
                        ? "pending"
                        : `${Math.round(it.identity_confidence * 100)}%`}
                    </td>
                    <td className="px-4 py-3">
                      {it.risk_rating ? (
                        <span className="text-muted-foreground">
                          {it.risk_rating} · {it.overall_risk}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{it.status}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {ACTIONS.map((a) => (
                          <button
                            key={a.value}
                            disabled={busy === it.id}
                            onClick={() => act(it.id, a.value)}
                            className="rounded-full border border-border px-2.5 py-1 text-xs hover:bg-muted disabled:opacity-50"
                          >
                            {a.label}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
