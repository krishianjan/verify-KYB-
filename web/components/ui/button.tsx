import * as React from "react";
import { cn } from "@/lib/utils";

const variants = {
  solid:
    "bg-ink text-paper hover:bg-grey-700 dark:bg-paper dark:text-ink dark:hover:bg-grey-200",
  outline:
    "border border-grey-300 dark:border-grey-700 bg-transparent hover:bg-muted",
  ghost: "bg-transparent hover:bg-muted",
  subtle: "bg-muted text-foreground hover:bg-grey-200 dark:hover:bg-grey-900",
} as const;

const sizes = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
  icon: "h-10 w-10",
} as const;

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "solid", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";
