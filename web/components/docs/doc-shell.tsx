"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV = [
  {
    group: "Guides",
    links: [
      { href: "/docs", label: "Overview" },
      { href: "/docs#waterfall", label: "The waterfall" },
      { href: "/docs#features", label: "Features" },
      { href: "/docs#glossary", label: "Glossary" },
      { href: "/docs#compliance", label: "Compliance" },
    ],
  },
  {
    group: "Reference",
    links: [{ href: "/docs/api", label: "API discovery" }],
  },
];

export function DocShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="mx-auto flex max-w-6xl gap-10 px-5 py-12">
      <aside className="hidden w-52 shrink-0 md:block">
        <nav className="sticky top-24 space-y-6">
          {NAV.map((g) => (
            <div key={g.group}>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {g.group}
              </div>
              <ul className="space-y-1">
                {g.links.map((l) => (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      className={cn(
                        "block rounded-md px-2 py-1 text-sm transition-colors hover:bg-muted",
                        pathname === l.href.split("#")[0] &&
                          l.href.endsWith(pathname)
                          ? "font-medium text-foreground"
                          : "text-muted-foreground",
                      )}
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
