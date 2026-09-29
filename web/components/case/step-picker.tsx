"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { STEP_LIBRARY } from "@/lib/api";
import { stepLabel } from "@/lib/format";

// Pick steps from the step library, grouped by class (resolution form and edits).
export function StepPicker({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const toggle = (code: string) =>
    onChange(value.includes(code) ? value.filter((c) => c !== code) : [...value, code]);
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {Object.entries(STEP_LIBRARY).map(([cls, codes]) => (
        <fieldset key={cls} className="rounded-md border p-2">
          <legend className="px-1 text-xs font-medium text-muted-foreground">{cls}</legend>
          {codes.map((code) => (
            <label key={code} className="flex items-center gap-2 py-0.5 text-sm">
              <Checkbox checked={value.includes(code)} onCheckedChange={() => toggle(code)} />
              <span title={code}>{stepLabel(code)}</span>
            </label>
          ))}
        </fieldset>
      ))}
    </div>
  );
}
