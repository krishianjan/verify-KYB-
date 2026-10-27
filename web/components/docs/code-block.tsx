"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

export function CodeBlock({
  code,
  label,
  className,
}: {
  code: string;
  label?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);
  return (
    <div className={cn("overflow-hidden rounded-xl border border-border bg-muted", className)}>
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
        <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
          {label || "example"}
        </span>
        <button
          onClick={() => {
            navigator.clipboard?.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 1200);
          }}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          {copied ? "✓ copied" : "copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 font-mono text-xs leading-relaxed text-foreground/85">
        {code}
      </pre>
    </div>
  );
}
