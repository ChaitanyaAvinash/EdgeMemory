import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium tracking-tight whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground",
        known: "border-transparent bg-emerald-100/80 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200",
        generalized: "border-transparent bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-200",
        composed: "border-transparent bg-violet-100 text-violet-900 dark:bg-violet-900/40 dark:text-violet-200",
        unknown: "border-transparent bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200",
        normal: "border-transparent bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200",
        floor: "border-transparent bg-signal-soft text-signal",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
