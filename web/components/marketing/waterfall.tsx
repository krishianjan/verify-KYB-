"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

type Node = {
  tag: string;
  title: string;
  body: string;
  endpoint?: string;
};

const NODES: Node[] = [
  {
    tag: "Foundation",
    title: "Business Search",
    body: "Submit a legal name (plus a state, if you have one). We query Secretary-of-State registries across all 50 states + DC.",
    endpoint: "POST /kyb/cases",
  },
  {
    tag: "Feature 1",
    title: "Identity Verification",
    body: "Fuzzy-match name and address against the registry, prefer active entities, pull officers, and score a confidence with field-level mismatches.",
  },
  {
    tag: "Feature 2",
    title: "Digital Footprint",
    body: "Crawl the website, read domain intelligence (WHOIS/RDAP, DNS/MX, TLS), check reputation, and raise deterministic ‘ghost-business’ signals.",
    endpoint: "POST /kyb/cases/{id}/footprint",
  },
  {
    tag: "Feature 4",
    title: "Web Intelligence",
    body: "When the registry can’t confirm the entity, an agent scrapes the open web — location, team, funding, news — and an LLM judges the presence. It never decides.",
    endpoint: "POST /kyb/cases/{id}/enrich",
  },
  {
    tag: "Feature 3",
    title: "Risk & Review",
    body: "A weighted scorecard merges identity + footprint into a risk rating with reason codes, hard-stops, a review queue, and analyst actions — all audited.",
    endpoint: "GET /kyb/cases",
  },
  {
    tag: "Output",
    title: "Verification Report",
    body: "One structured verdict: two A–F grades (KYB + Risk), match categories, a decision object, and a source-of-truth map.",
    endpoint: "GET /kyb/cases/{id}/report",
  },
];

export function Waterfall() {
  const root = useRef<HTMLDivElement>(null);
  const line = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      // Progress line scrubs with the section.
      if (line.current) {
        gsap.fromTo(
          line.current,
          { scaleY: 0 },
          {
            scaleY: 1,
            ease: "none",
            scrollTrigger: {
              trigger: root.current,
              start: "top 60%",
              end: "bottom 70%",
              scrub: true,
            },
          },
        );
      }
      // Each node reveals + activates as it crosses the viewport center.
      gsap.utils.toArray<HTMLElement>("[data-node]").forEach((el) => {
        gsap.fromTo(
          el,
          { opacity: 0.25, y: 24 },
          {
            opacity: 1,
            y: 0,
            duration: 0.5,
            scrollTrigger: { trigger: el, start: "top 75%", toggleActions: "play none none reverse" },
          },
        );
      });
      ScrollTrigger.refresh();
    }, root);
    return () => ctx.revert();
  }, []);

  return (
    <section id="waterfall" ref={root} className="mx-auto max-w-5xl px-5 py-24">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          The waterfall
        </div>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
          One submission, each step building on the last
        </h2>
        <p className="mt-4 text-muted-foreground">
          Every product builds on the one before it — a verified case unlocks the
          deeper checks. This is exactly what verifyKYB runs today.
        </p>
      </div>

      <div className="relative pl-10 sm:pl-0">
        {/* Rail */}
        <div className="absolute left-4 top-0 h-full w-px bg-border sm:left-1/2 sm:-translate-x-1/2" />
        <div
          ref={line}
          className="absolute left-4 top-0 h-full w-px origin-top bg-ink dark:bg-paper sm:left-1/2 sm:-translate-x-1/2"
        />

        <ol className="space-y-10">
          {NODES.map((n, i) => (
            <li
              key={n.title}
              data-node
              className={`relative sm:grid sm:grid-cols-2 sm:gap-10 ${
                i % 2 ? "sm:[&>*:first-child]:col-start-2" : ""
              }`}
            >
              {/* Node dot */}
              <span className="absolute left-[-1.5rem] top-1.5 flex h-3 w-3 items-center justify-center sm:left-1/2 sm:-translate-x-1/2">
                <span className="h-3 w-3 rounded-full border-2 border-ink bg-background dark:border-paper" />
              </span>

              <div className={i % 2 ? "sm:text-left sm:pl-8" : "sm:text-right sm:pr-8"}>
                <div className="rounded-2xl border border-border bg-card p-5">
                  <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground"
                       style={{ justifyContent: i % 2 ? "flex-start" : "flex-end" }}>
                    <span className="rounded-full border border-border px-2 py-0.5 font-medium">
                      {n.tag}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold tracking-tight">{n.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {n.body}
                  </p>
                  {n.endpoint && (
                    <code className="mt-3 inline-block rounded-md bg-muted px-2 py-1 font-mono text-[11px] text-foreground/70">
                      {n.endpoint}
                    </code>
                  )}
                </div>
              </div>
              <div className="hidden sm:block" />
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
