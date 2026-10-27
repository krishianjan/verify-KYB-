"use client";

import { useEffect, useState } from "react";

const STEPS = [
  "Resolving entity in official registries",
  "Fetching officers & corporate record",
  "Analyzing digital footprint",
  "Gathering web intelligence",
  "Scoring risk & assembling verdict",
];

/** Animated "verifying…" state. The lookup hits live registries (10–60s). */
export function Verifying() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const id = setInterval(
      () => setActive((a) => Math.min(a + 1, STEPS.length - 1)),
      2600,
    );
    return () => clearInterval(id);
  }, []);

  return (
    <div className="mx-auto max-w-md">
      <div className="relative overflow-hidden rounded-2xl border border-border bg-card p-8">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-ink/60 animate-scan dark:bg-paper/60" />
        <div className="mb-6 flex items-center gap-3">
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full rounded-full bg-ink animate-pulse-ring dark:bg-paper" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-ink dark:bg-paper" />
          </span>
          <span className="text-sm font-medium">Verifying…</span>
        </div>
        <ul className="space-y-3">
          {STEPS.map((s, i) => (
            <li
              key={s}
              className="flex items-center gap-3 text-sm transition-opacity"
              style={{ opacity: i <= active ? 1 : 0.35 }}
            >
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full border text-[10px]"
                style={{
                  background: i < active ? "var(--ink)" : "transparent",
                  color: i < active ? "var(--paper)" : "var(--muted-foreground)",
                  borderColor: i <= active ? "var(--ink)" : "var(--border)",
                }}
              >
                {i < active ? "✓" : i + 1}
              </span>
              {s}
            </li>
          ))}
        </ul>
        <p className="mt-6 text-xs text-muted-foreground">
          Live registry lookups can take 10–60 seconds.
        </p>
      </div>
    </div>
  );
}
