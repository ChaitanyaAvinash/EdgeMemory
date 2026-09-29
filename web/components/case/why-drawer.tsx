"use client";

import { VerdictBadge } from "@/components/badges";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import type { CaseView, Step } from "@/lib/api";
import { stepLabel } from "@/lib/format";

// "Why this step?" (SPEC §15.1): cited cases, recalled memory text, verdicts, source counts and flags.
export function WhyDrawer({ step, view }: { step: Step; view: CaseView }) {
  const cands = [...view.violations.flatMap((v) => v.candidates), ...view.interactions].filter((c) =>
    c.case_ids.some((id) => step.cited_case_ids.includes(id)),
  );
  const cases = new Map(cands.flatMap((c) => c.cases).map((c) => [c.case_id, c]));
  const flags = view.procedure.flags.filter((f) => f.includes(step.code));
  return (
    <Sheet>
      <SheetTrigger className="text-xs text-primary underline-offset-2 hover:underline">Why this step?</SheetTrigger>
      <SheetContent>
        <SheetTitle>{stepLabel(step.code)}</SheetTitle>
        <SheetDescription>
          <span className="font-mono text-xs">{step.code}</span> · {step.class.replace("_", " ")}
        </SheetDescription>
        {step.origin === "floor" ? (
          <p className="rounded-md border border-rose-300 bg-rose-50 p-3 text-sm dark:bg-rose-950/40">
            Added by safety floor. This step is required by a rule no learned lesson can go below. It is not
            learned from memory.
          </p>
        ) : (
          <p className="text-sm">{step.reason}</p>
        )}
        {step.origin === "union" && (
          <p className="text-xs text-muted-foreground">
            From the plain combination of single-check lessons (kept or restored by code).
          </p>
        )}
        {flags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {flags.map((f) => (
              <Badge key={f} variant="unknown">
                {f}
              </Badge>
            ))}
          </div>
        )}
        <section className="flex flex-col gap-2">
          <h4 className="text-sm font-semibold">Cited cases (ledger)</h4>
          {step.cited_case_ids.length === 0 && <p className="text-sm text-muted-foreground">None.</p>}
          {step.cited_case_ids.map((id) => {
            const c = cases.get(id);
            return (
              <div key={id} className="rounded-md border p-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs">{id}</span>
                  {c && (
                    <>
                      <span>{c.amount_text}</span>
                      <span className="text-muted-foreground">{c.category.replace("_", " ")}</span>
                      <span className="text-muted-foreground">resolved {c.resolved_at}</span>
                      {c.status !== "active" && <Badge variant="unknown">{c.status}</Badge>}
                    </>
                  )}
                </div>
                {c && <div className="mt-1 text-xs text-muted-foreground">Final steps: {c.steps.join(", ")}</div>}
              </div>
            );
          })}
        </section>
        <section className="flex flex-col gap-2">
          <h4 className="text-sm font-semibold">What memory recalled, and the verifier&apos;s verdict</h4>
          {cands.length === 0 && <p className="text-sm text-muted-foreground">No recalled memory cites this step.</p>}
          {cands.map((c) => (
            <div key={c.candidate_id} className="flex flex-col gap-1 rounded-md border p-2 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{c.memory_type === "observation" ? "consolidated lesson" : "fact"}</Badge>
                {c.memory_type === "observation" && (
                  <span className="text-xs text-muted-foreground">from {c.case_ids.length} cases</span>
                )}
                {c.combo && <Badge variant="composed">interaction: {c.combo}</Badge>}
                <VerdictBadge verdict={c.verdict} />
              </div>
              <p className="text-xs leading-relaxed">{c.memory_text}</p>
              {c.reason && <p className="text-xs text-muted-foreground">Verifier: {c.reason}</p>}
              {c.differences.length > 0 && (
                <ul className="list-disc pl-5 text-xs text-muted-foreground">
                  {c.differences.map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              )}
              {c.guard && <p className="text-xs text-amber-700">Code guard lowered this verdict: {c.guard}</p>}
            </div>
          ))}
        </section>
      </SheetContent>
    </Sheet>
  );
}
