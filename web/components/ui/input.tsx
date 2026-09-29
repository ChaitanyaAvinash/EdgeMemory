import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-xl border border-input bg-card/60 px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none transition-colors focus-visible:border-signal focus-visible:ring-2 focus-visible:ring-signal/20 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[72px] w-full rounded-xl border border-input bg-card/60 px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none transition-colors focus-visible:border-signal focus-visible:ring-2 focus-visible:ring-signal/20 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
