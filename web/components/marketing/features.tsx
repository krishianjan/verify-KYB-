"use client";

import { motion } from "framer-motion";

const FEATURES = [
  {
    k: "F1",
    title: "Registry & identity",
    body: "Secretary-of-State lookups across all 50 states + DC, fuzzy name/address matching, officers, and an explainable confidence score.",
  },
  {
    k: "F2",
    title: "Digital footprint",
    body: "Tiered crawling, WHOIS/RDAP domain age, DNS/MX, TLS, reputation, and deterministic ghost-business signals with a legitimacy score.",
  },
  {
    k: "F3",
    title: "Web intelligence",
    body: "An agent scrapes the open web for location, team, funding and news; an LLM structures the evidence and judges presence — as a signal, not a verdict.",
  },
  {
    k: "F4",
    title: "Risk & workflow",
    body: "A bank-style weighted scorecard with hard-stops and reason codes, a review queue, analyst actions, and an immutable audit trail.",
  },
  {
    k: "ML",
    title: "ML signals",
    body: "IsolationForest anomaly detection and a supervised scaffold trained on analyst decisions — complementary signals that feed the scorecard.",
  },
  {
    k: "OUT",
    title: "One report",
    body: "A Baselayer-shaped verdict: two A–F grades, match categories, a decision object with reasoning, and a source-of-truth map.",
  },
];

export function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl px-5 py-24">
      <div className="mb-14 max-w-2xl">
        <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          What we built
        </div>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
          Everything behind the verdict
        </h2>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.45, delay: (i % 3) * 0.06 }}
            className="group rounded-2xl border border-border bg-card p-6 transition-colors hover:border-grey-400 dark:hover:border-grey-500"
          >
            <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-ink font-mono text-xs font-bold text-paper dark:bg-paper dark:text-ink">
              {f.k}
            </div>
            <h3 className="font-semibold tracking-tight">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
