import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-12 md:flex-row md:items-start md:justify-between">
        <div className="max-w-xs">
          <div className="flex items-center gap-2 font-semibold">
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-ink text-paper dark:bg-paper dark:text-ink text-[11px] font-bold">
              V
            </span>
            verifyKYB
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Open-source Know-Your-Business verification. One submission in, one
            explainable verdict out.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-10 text-sm sm:grid-cols-3">
          <FooterCol title="Product" links={[["Verify a business", "/verify"], ["Review queue", "/queue"]]} />
          <FooterCol title="Developers" links={[["Documentation", "/docs"], ["API reference", "/docs/api"]]} />
          <FooterCol title="How it works" links={[["The waterfall", "/#waterfall"], ["Features", "/#features"]]} />
        </div>
      </div>
      <div className="border-t border-border">
        <div className="mx-auto max-w-6xl px-5 py-5 text-xs text-muted-foreground">
          Decisions are deterministic, rule-based, and auditable. AI explains — it
          never decides.
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, links }: { title: string; links: [string, string][] }) {
  return (
    <div>
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </div>
      <ul className="space-y-2">
        {links.map(([label, href]) => (
          <li key={href}>
            <Link href={href} className="text-foreground/80 hover:text-foreground">
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
