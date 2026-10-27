"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

const links = [
  { href: "/verify", label: "Verify" },
  { href: "/queue", label: "Queue" },
  { href: "/docs", label: "Docs" },
  { href: "/docs/api", label: "API" },
];

export function SiteNav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-ink text-paper dark:bg-paper dark:text-ink text-[11px] font-bold">
            V
          </span>
          verifyKYB
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "rounded-full px-3 py-1.5 text-sm transition-colors hover:bg-muted",
                pathname.startsWith(l.href)
                  ? "text-foreground font-medium"
                  : "text-muted-foreground",
              )}
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link href="/verify" className="hidden sm:block">
            <Button size="sm">Try it</Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
