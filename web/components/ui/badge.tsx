import * as React from "react";
import { cn } from "@/lib/utils";

const tones = {
  solid: "bg-ink text-paper dark:bg-paper dark:text-ink border-transparent",
  mid: "bg-grey-200 text-grey-900 dark:bg-grey-700 dark:text-grey-100 border-transparent",
  outline: "bg-transparent text-foreground border-grey-300 dark:border-grey-700",
  muted: "bg-muted text-muted-foreground border-transparent",
} as const;

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: keyof typeof tones;
}

export function Badge({ className, tone = "outline", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
