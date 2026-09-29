"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { GLOSSARY } from "@/lib/glossary";

// A procurement term with its plain-language explanation on hover or focus.
export function Term({ k, children }: { k: string; children?: React.ReactNode }) {
  const text = GLOSSARY[k];
  if (!text) return <>{children ?? k}</>;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0} className="cursor-help underline decoration-dotted underline-offset-2">
          {children ?? k}
        </span>
      </TooltipTrigger>
      <TooltipContent>{text}</TooltipContent>
    </Tooltip>
  );
}
