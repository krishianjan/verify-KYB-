"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div className="bg-dotgrid mask-fade-b absolute inset-0 opacity-70" />
      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-5 py-24 lg:grid-cols-2 lg:py-32">
        <div>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-background/60 px-3 py-1 text-xs text-muted-foreground backdrop-blur"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-ink dark:bg-paper" />
            Open-source KYB · deterministic & auditable
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05 }}
            className="mt-6 text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl"
          >
            Know the business
            <br />
            before you onboard it.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.12 }}
            className="mt-6 max-w-md text-lg text-muted-foreground"
          >
            Registry identity, digital footprint, and live web intelligence —
            merged into one explainable verdict. One submission in, two letter
            grades out.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.18 }}
            className="mt-8 flex flex-wrap gap-3"
          >
            <Link href="/verify">
              <Button size="lg">Verify a business</Button>
            </Link>
            <Link href="/docs">
              <Button size="lg" variant="outline">
                Read the docs
              </Button>
            </Link>
          </motion.div>
          <p className="mt-6 text-xs text-muted-foreground">
            Decisions are rule-based and auditable. AI explains — it never decides.
          </p>
        </div>

        <HeroCard />
      </div>
    </section>
  );
}

function HeroCard() {
  const rows = [
    ["KYB rating", "A", "92"],
    ["Risk rating", "A", "94"],
    ["Name match", "EXACT", ""],
    ["Registry", "Active", ""],
  ];
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.7, delay: 0.15 }}
      className="relative mx-auto w-full max-w-sm"
    >
      <div className="relative overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px animate-scan bg-ink/50 dark:bg-paper/50" />
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              Verification report
            </div>
            <div className="mt-1 font-semibold">Apple Inc</div>
          </div>
          <span className="rounded-full bg-ink px-3 py-1 text-xs text-paper dark:bg-paper dark:text-ink">
            Verified
          </span>
        </div>
        <div className="mt-5 space-y-3">
          {rows.map(([k, v, n]) => (
            <div key={k} className="flex items-center justify-between border-t border-border pt-3 text-sm">
              <span className="text-muted-foreground">{k}</span>
              <span className="flex items-center gap-2 font-medium">
                <span className="rounded-full border border-border px-2 py-0.5 text-xs">{v}</span>
                {n && <span className="font-mono tabular-nums">{n}</span>}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-5 rounded-xl bg-muted px-3 py-2 text-xs text-muted-foreground">
          Decision: <span className="font-medium text-foreground">auto-approve</span> ·
          6 signals · fully audited
        </div>
      </div>
    </motion.div>
  );
}
