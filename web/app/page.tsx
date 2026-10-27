import Link from "next/link";
import { Hero } from "@/components/marketing/hero";
import { Waterfall } from "@/components/marketing/waterfall";
import { Features } from "@/components/marketing/features";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <>
      <Hero />
      <Waterfall />
      <Features />

      {/* Compliance stance */}
      <section className="mx-auto max-w-4xl px-5 py-10">
        <div className="rounded-2xl border border-border bg-muted/50 p-8 text-center">
          <h2 className="text-xl font-semibold tracking-tight">
            Built for compliance from the first line
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Every decision is deterministic, rule-based, and traceable to reason
            codes  the posture regulators expect (SR 11-7 model risk, FCRA/ECOA
            adverse action, EU AI Act). Machine learning and LLMs add signals and
            explanations; they never make the call.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-5 py-24">
        <div className="relative overflow-hidden rounded-3xl border border-border bg-ink px-8 py-16 text-center text-paper dark:bg-paper dark:text-ink">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Verify your first business in a minute
          </h2>
          <p className="mx-auto mt-4 max-w-md text-sm text-paper/70 dark:text-ink/70">
            No signup for the demo. Submit a name, watch the waterfall run, read the
            verdict.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Link href="/verify">
              <Button
                size="lg"
                variant="outline"
                className="border-paper/30 text-paper hover:bg-paper/10 dark:border-ink/30 dark:text-ink dark:hover:bg-ink/10"
              >
                Try the live demo
              </Button>
            </Link>
            <Link href="/docs/api">
              <Button
                size="lg"
                className="bg-paper text-ink hover:bg-grey-200 dark:bg-ink dark:text-paper"
              >
                Explore the API
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
