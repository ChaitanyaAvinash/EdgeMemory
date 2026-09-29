import { Badge } from "@/components/ui/badge";
import type { CaseClass, ReviewMode } from "@/lib/api";

const CLASS_LABEL: Record<string, string> = {
  normal: "Normal",
  known: "Known",
  generalized: "Generalized",
  composed: "Composed",
  unknown: "Unknown",
};

export function ClassBadge({ cls }: { cls: CaseClass | string }) {
  return <Badge variant={(cls as CaseClass) || "outline"}>{CLASS_LABEL[cls] ?? cls}</Badge>;
}

export function MaturityBadge({ maturity, strength }: { maturity: string; strength?: number }) {
  if (!maturity) return null;
  const text = strength !== undefined ? `${maturity} (${strength} ${strength === 1 ? "case" : "cases"})` : maturity;
  return <Badge variant={maturity === "established" ? "known" : "outline"}>{text}</Badge>;
}

export function VerdictBadge({ verdict }: { verdict: string }) {
  const v = verdict || "no";
  const variant = v === "yes" ? "known" : v === "partial" ? "generalized" : "unknown";
  const label = v === "yes" ? "precedent applies" : v === "partial" ? "applies with differences" : "no precedent";
  return <Badge variant={variant}>{label}</Badge>;
}

export function ReviewBadge({ mode }: { mode: ReviewMode | string }) {
  const label: Record<string, string> = {
    one_click: "One-click review",
    step_by_step: "Step-by-step review",
    escalate: "Escalate to a human",
  };
  if (!mode) return null;
  return <Badge variant={mode === "escalate" ? "unknown" : "outline"}>{label[mode] ?? mode}</Badge>;
}
