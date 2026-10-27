"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";

const PRESETS: { label: string; method: string; path: string; body?: string }[] = [
  { label: "Health", method: "GET", path: "/health" },
  {
    label: "Create case",
    method: "POST",
    path: "/kyb/cases",
    body: JSON.stringify({ legal_name: "Apple Inc", state: "CA" }, null, 2),
  },
  { label: "List queue", method: "GET", path: "/kyb/cases?limit=10" },
  { label: "Get report", method: "GET", path: "/kyb/cases/{id}/report" },
  { label: "Run enrich", method: "POST", path: "/kyb/cases/{id}/enrich" },
];

export function TryIt() {
  const [method, setMethod] = useState("GET");
  const [path, setPath] = useState("/health");
  const [body, setBody] = useState("");
  const [resp, setResp] = useState<string>("");
  const [status, setStatus] = useState<number | null>(null);
  const [running, setRunning] = useState(false);

  function preset(p: (typeof PRESETS)[number]) {
    setMethod(p.method);
    setPath(p.path);
    setBody(p.body || "");
    setResp("");
    setStatus(null);
  }

  async function run() {
    setRunning(true);
    setResp("");
    setStatus(null);
    try {
      const init: RequestInit = { method, headers: { "Content-Type": "application/json" } };
      if (method !== "GET" && body.trim()) init.body = body;
      const r = await fetch(`${API_BASE}${path}`, init);
      setStatus(r.status);
      const text = await r.text();
      try {
        setResp(JSON.stringify(JSON.parse(text), null, 2));
      } catch {
        setResp(text);
      }
    } catch {
      setResp(`Could not reach ${API_BASE}. Is the backend running?`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <div className="mb-3 flex flex-wrap gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => preset(p)}
            className="rounded-full border border-border px-3 py-1 text-xs hover:bg-muted"
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value)}
          className="h-10 rounded-xl border border-grey-300 bg-background px-3 text-sm dark:border-grey-700"
        >
          <option>GET</option>
          <option>POST</option>
        </select>
        <Input
          value={path}
          onChange={(e) => setPath(e.target.value)}
          className="h-10 flex-1 font-mono text-xs"
        />
        <Button onClick={run} disabled={running} className="h-10">
          {running ? "Running…" : "Send"}
        </Button>
      </div>
      <p className="mt-2 font-mono text-[11px] text-muted-foreground">
        {method} {API_BASE}
        {path}
      </p>
      {method === "POST" && (
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Request body (JSON)"
          className="mt-3 min-h-24 w-full rounded-xl border border-grey-300 bg-background p-3 font-mono text-xs dark:border-grey-700"
        />
      )}
      {(resp || status != null) && (
        <div className="mt-3">
          {status != null && (
            <div className="mb-1 font-mono text-xs text-muted-foreground">
              HTTP {status}
            </div>
          )}
          <pre className="max-h-96 overflow-auto rounded-xl bg-muted p-4 font-mono text-xs leading-relaxed">
            {resp}
          </pre>
        </div>
      )}
      <p className="mt-2 text-xs text-muted-foreground">
        Replace <code className="font-mono">{"{id}"}</code> with a real case id from
        a create-case response.
      </p>
    </div>
  );
}
