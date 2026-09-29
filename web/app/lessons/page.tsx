"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { PageHeader, Reveal } from "@/components/motion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type LessonsView } from "@/lib/api";

const TAGS = [
  "step:vendor", "step:budget", "step:approver", "step:duplicate", "step:bank", "step:quotes",
  "combo:approver+budget", "combo:bank+budget", "signal:related_party",
];

// Word-level diff between an observation's previous and current text (SPEC §15.1 lesson panel).
function Diff({ before, after }: { before: string; after: string }) {
  const a = before.split(/\s+/);
  const b = after.split(/\s+/);
  const inA = new Set(a);
  const inB = new Set(b);
  return (
    <div className="grid gap-2 text-xs md:grid-cols-2">
      <p className="leading-relaxed">
        <span className="font-medium">Before: </span>
        {a.map((w, i) => (
          <span key={i} className={inB.has(w) ? "" : "bg-rose-200 line-through dark:bg-rose-900/50"}>{w} </span>
        ))}
      </p>
      <p className="leading-relaxed">
        <span className="font-medium">After: </span>
        {b.map((w, i) => (
          <span key={i} className={inA.has(w) ? "" : "bg-emerald-200 dark:bg-emerald-900/50"}>{w} </span>
        ))}
      </p>
    </div>
  );
}

function LessonsInner() {
  const tag = useSearchParams().get("tag") ?? "step:vendor";
  const router = useRouter();
  const [data, setData] = useState<LessonsView | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    setError("");
    api.lessons(tag).then(setData).catch((e) => setError(String(e)));
  }, [tag]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader eyebrow="Memory" title="What it has {learned}">
        Per failed check and per combination: the current consolidated lesson, the cases behind it, and how it changed
        as people decided.
      </PageHeader>
      <Reveal delay={350} className="flex flex-wrap gap-2">
        {TAGS.map((t) => (
          <button
            key={t}
            onClick={() => router.push(`/lessons?tag=${encodeURIComponent(t)}`)}
            className="transition-transform duration-300 hover:-translate-y-0.5"
          >
            <Badge variant={t === tag ? "default" : "outline"} className="px-3 py-1 text-sm">{t}</Badge>
          </button>
        ))}
      </Reveal>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!data && !error && <p className="text-sm text-muted-foreground">Loading {tag}…</p>}
      {data && (
        <>
          <Card className="stage-in">
            <CardHeader><CardTitle>Current lesson (Hindsight observation)</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-4 text-sm">
              {data.observations.length === 0 && (
                <p className="text-muted-foreground">No consolidated lesson under {tag} yet.</p>
              )}
              {data.observations.map((o) => (
                <div key={o.id} className="flex flex-col gap-2">
                  <p className="font-display text-2xl leading-snug">{o.text}</p>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    Consolidated from {o.case_ids.length} {o.case_ids.length === 1 ? "case" : "cases"}:
                    {o.case_ids.map((c) => <span key={c} className="font-mono">{c}</span>)}
                  </div>
                  {o.history.length > 0 && (
                    <div className="flex flex-col gap-2 rounded-md border p-2">
                      <div className="text-xs font-medium">How this lesson changed ({o.history.length} revisions)</div>
                      <Diff before={o.history[o.history.length - 1].previous_text} after={o.text} />
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="stage-in [animation-delay:150ms]">
            <CardHeader><CardTitle>Cases in the ledger under {tag}</CardTitle></CardHeader>
            <CardContent className="divide-y text-sm">
              {data.cases.length === 0 && <p className="text-muted-foreground">None.</p>}
              {data.cases.map((c) => (
                <div key={c.case_id} className="flex flex-wrap items-center gap-2 py-1.5">
                  <Link href={c.case_id.startsWith("PR-DEMO") ? `/cases/${c.case_id}` : "#"} className="w-36 font-mono text-xs">{c.case_id}</Link>
                  <Badge variant="outline">{c.kind}</Badge>
                  {c.status !== "active" && <Badge variant="unknown">{c.status}</Badge>}
                  {c.overridden_by && (
                    <Badge variant="unknown" title={c.overridden_by}>overridden in context</Badge>
                  )}
                  <span className="text-xs text-muted-foreground">{c.resolved_at}</span>
                  <span className="text-xs">{c.steps.join(", ")}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

export default function LessonsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading…</p>}>
      <LessonsInner />
    </Suspense>
  );
}
