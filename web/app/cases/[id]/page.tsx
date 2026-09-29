"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { ClassBadge, MaturityBadge, ReviewBadge, VerdictBadge } from "@/components/badges";
import { Highlighted } from "@/components/case/highlight";
import { StepPicker } from "@/components/case/step-picker";
import { WhyDrawer } from "@/components/case/why-drawer";
import { Reveal, SplitWords } from "@/components/motion";
import { Term } from "@/components/term";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input, Textarea } from "@/components/ui/input";
import { api, type CaseView, type DemoBeat } from "@/lib/api";
import { stepLabel, titleCase } from "@/lib/format";

const STAGES = 7; // request, failed checks, precedents, union, interaction changes, floor, final procedure
const STAGE_MS = 1500;

function Stage({ n, stage, title, children }: { n: number; stage: number; title: string; children: React.ReactNode }) {
  if (stage < n) return null;
  return (
    <Card className="stage-in relative overflow-hidden">
      <span className="pointer-events-none absolute -right-2 -top-6 select-none font-display text-[7rem] leading-none text-foreground/[0.05]">
        {String(n).padStart(2, "0")}
      </span>
      <CardHeader>
        <CardTitle className="flex items-baseline gap-3">
          <span className="font-mono text-xs text-signal">{String(n).padStart(2, "0")}</span>
          <span className="font-display text-2xl">{title}</span>
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function CaseInner() {
  const { id } = useParams<{ id: string }>();
  const demo = useSearchParams().get("demo") === "1";
  const [view, setView] = useState<CaseView | null>(null);
  const [error, setError] = useState("");
  const [stage, setStage] = useState(STAGES);
  const [ticked, setTicked] = useState<string[]>([]);
  const [mode, setMode] = useState<"" | "edit" | "reject" | "resolve">("");
  const [picked, setPicked] = useState<string[]>([]);
  const [rationale, setRationale] = useState("");
  const [outcome, setOutcome] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState("");
  const [fixture, setFixture] = useState<DemoBeat["decision"] | null>(null);

  useEffect(() => {
    if (!demo) return;
    api.fixtures().then((f) => {
      const beat = f.beats.find((b) => b.request?.request_id === id);
      if (beat?.decision) setFixture(beat.decision);
    }).catch(() => {});
  }, [id, demo]);

  const open = (m: "edit" | "reject" | "resolve") => {
    setMode(m);
    if (fixture && (fixture.action === m || (m === "reject" && fixture.action === "reject"))) {
      setPicked(fixture.final_steps);
      setRationale(fixture.rationale);
      setOutcome(fixture.outcome);
    } else if (m === "reject") {
      setPicked(["REJECT_REQUEST"]);
    }
  };

  useEffect(() => {
    api.getCase(id).then((v) => {
      setView(v);
      setPicked(v.procedure.steps.map((s) => s.code));
      if (demo) setStage(1);
    }).catch((e) => setError(String(e)));
  }, [id, demo]);

  useEffect(() => {
    if (stage >= STAGES) return;
    const t = setTimeout(() => setStage((s) => s + 1), STAGE_MS);
    return () => clearTimeout(t);
  }, [stage]);

  const decide = useCallback(
    async (action: string, steps: string[]) => {
      setBusy(true);
      try {
        const r = await api.decide(id, { action, final_steps: steps, rationale, outcome });
        setView(r.case);
        setDone(`Saved (${action}). Retained: ${r.retained.map((x) => x.kind).join(", ") || "nothing"}.`);
        setMode("");
      } catch (e) {
        setDone(`Not saved: ${e}`);
      } finally {
        setBusy(false);
      }
    },
    [id, rationale, outcome],
  );

  if (error) return <p className="text-sm text-destructive">Couldn&apos;t load {id}: {error}</p>;
  if (!view) return <p className="text-sm text-muted-foreground">Loading {id}…</p>;

  const r = view.request;
  const spans = [...r.signals.map((s) => s.span), ...view.violations.map((v) => v.source_span).filter(Boolean)];
  const union = view.procedure.union_steps.map((s) => s.code);
  const removed = view.procedure.removed_from_union;
  const final = view.procedure.steps;
  const floor = final.filter((s) => s.origin === "floor");
  const decided = view.decisions.length > 0;
  const allTicked = final.every((s) => ticked.includes(s.code));

  return (
    <div className="flex flex-col gap-5 pt-6 md:pt-10">
      <Link href="/" className="link-u w-fit text-sm text-muted-foreground">← Queue</Link>
      <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
        <h1 className="font-display text-5xl leading-none md:text-7xl">
          <SplitWords text={r.id} />
        </h1>
        <div className="flex flex-wrap items-center gap-2 pb-2">
          <ClassBadge cls={view.class} />
          <MaturityBadge maturity={view.maturity} />
          {view.novel_combination && <Badge variant="outline">novel combination</Badge>}
          <ReviewBadge mode={view.review_mode} />
        </div>
        <Button variant="outline" size="sm" className="mb-2 ml-auto" onClick={() => setStage(1)}>
          Replay reveal ↻
        </Button>
      </div>
      <Reveal delay={200}>
        <p className="border-l-2 border-signal pl-4 font-display text-2xl leading-snug md:text-3xl">{view.summary}</p>
      </Reveal>

      <Stage n={1} stage={stage} title="The request">
        <div className="grid gap-3 text-sm md:grid-cols-3">
          <div>
            <div className="text-muted-foreground">Vendor</div>
            <div>{r.vendor_name} {r.vendor_id && <span className="font-mono text-xs">({r.vendor_id})</span>}</div>
          </div>
          <div>
            <div className="text-muted-foreground">Amount</div>
            <div className="tabular-nums">{r.amount_text} <span className="text-xs text-muted-foreground">({r.band})</span></div>
          </div>
          <div>
            <div className="text-muted-foreground"><Term k="cost centre">Cost centre</Term> · category · urgency</div>
            <div>
              {r.cost_centre} · {r.category === "indirect_mro" ? <Term k="MRO">indirect MRO</Term> : titleCase(r.category)} ·{" "}
              {r.urgency === "line_down" ? <Term k="line-down">line down</Term> : r.urgency}
            </div>
          </div>
        </div>
        <div className="mt-3 flex flex-col gap-2 text-sm">
          <div><span className="text-muted-foreground">Justification: </span><Highlighted text={r.justification} spans={spans} /></div>
          <div><span className="text-muted-foreground">Email thread: </span><Highlighted text={r.email_thread} spans={spans} /></div>
          {r.attachment_text && (
            <div><span className="text-muted-foreground">Attachment: </span><Highlighted text={r.attachment_text} spans={spans} /></div>
          )}
          {r.signals.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {r.signals.map((s) => (
                <Badge key={s.name + s.span} variant="unknown">signal: {s.name.replace(/_/g, " ")} ({s.source.replace("_", " ")})</Badge>
              ))}
            </div>
          )}
        </div>
      </Stage>

      <Stage n={2} stage={stage} title={`Failed checks (${view.violations.length})`}>
        {view.violations.length === 0 && <p className="text-sm">Every check passed. Standard approval.</p>}
        <ul className="flex flex-col gap-2 text-sm">
          {view.violations.map((v) => (
            <li key={v.check} className="flex flex-col gap-0.5">
              <span className="font-medium">{titleCase(v.check)} <span className="font-normal text-muted-foreground">({v.cause.replace(/_/g, " ")})</span></span>
              <span className="text-muted-foreground">{v.detail}</span>
            </li>
          ))}
        </ul>
      </Stage>

      <Stage n={3} stage={stage} title="How each problem was resolved before">
        <div className="flex flex-col gap-3">
          {view.violations.map((v) => (
            <div key={v.check} className="rounded-md border p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{titleCase(v.check)}</span>
                <VerdictBadge verdict={v.coverage.status} />
                <MaturityBadge maturity={v.coverage.maturity} strength={v.coverage.strength} />
                <Link href={`/lessons?tag=${encodeURIComponent(v.tag)}`} className="ml-auto text-xs text-primary hover:underline">
                  Lesson panel →
                </Link>
              </div>
              {v.coverage.status === "no" ? (
                <p className="mt-1 text-amber-700 dark:text-amber-400">
                  No verified <Term k="precedent">precedent</Term>. This problem goes to a human, with what is known and what isn&apos;t.
                </p>
              ) : (
                <p className="mt-1 text-muted-foreground">
                  Cases {v.coverage.case_ids.join(", ")}. {v.coverage.reason}
                  {v.coverage.differences.length > 0 && <> Differences: {v.coverage.differences.join("; ")}.</>}
                </p>
              )}
            </div>
          ))}
          {view.interactions.length > 0 && (
            <div className="rounded-md border border-violet-300 p-3 text-sm">
              <div className="font-medium">Precedents where these problems happened together</div>
              {view.interactions.map((c) => (
                <div key={c.candidate_id} className="mt-1 flex flex-wrap items-center gap-2 text-muted-foreground">
                  <Badge variant="composed">{c.combo}</Badge> <VerdictBadge verdict={c.verdict} /> cases {c.case_ids.join(", ")}
                </div>
              ))}
            </div>
          )}
        </div>
      </Stage>

      <Stage n={4} stage={stage} title="The plain combination of single-check lessons">
        {union.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing to combine.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {union.map((c) => (
              <Badge key={c} variant="outline" className={removed.some((x) => x.code === c) ? "line-through opacity-60" : ""}>
                {stepLabel(c)}
              </Badge>
            ))}
          </div>
        )}
      </Stage>

      <Stage n={5} stage={stage} title="What changes when these problems occur together">
        {removed.length === 0 && final.every((s) => union.includes(s.code) || s.origin === "floor") ? (
          <p className="text-sm text-muted-foreground">No change from the plain combination.</p>
        ) : (
          <ul className="flex flex-col gap-1 text-sm">
            {removed.map((x) => (
              <li key={x.code}>
                <span className="line-through">{stepLabel(x.code)}</span>{" "}
                <span className="text-muted-foreground">— {x.reason} {x.cited_case_ids.length > 0 && `(${x.cited_case_ids.join(", ")})`}</span>
              </li>
            ))}
            {final.filter((s) => !union.includes(s.code) && s.origin !== "floor").map((s) => (
              <li key={s.code}>
                <span className="font-medium text-emerald-700 dark:text-emerald-400">+ {stepLabel(s.code)}</span>{" "}
                <span className="text-muted-foreground">— {s.reason} ({s.cited_case_ids.join(", ")})</span>
              </li>
            ))}
          </ul>
        )}
      </Stage>

      <Stage n={6} stage={stage} title="Safety floor">
        {floor.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            The <Term k="safety floor">safety floor</Term> holds without additions.
            {final.some((s) => s.code === "HOLD_PAYMENT") && " Payment stays held until the bank callback."}
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {floor.map((s) => (
              <Badge key={s.code} variant="floor">Added by safety floor: {stepLabel(s.code)}</Badge>
            ))}
          </div>
        )}
      </Stage>

      <Stage n={7} stage={stage} title="Recommended procedure">
        <ol className="flex flex-col gap-2">
          {final.map((s) => (
            <li key={s.code} className="flex flex-wrap items-center gap-2 rounded-xl border bg-background/50 px-4 py-3 text-sm transition-all duration-500 hover:translate-x-1 hover:border-foreground/30">
              {view.review_mode === "step_by_step" && !decided && (
                <Checkbox
                  checked={ticked.includes(s.code)}
                  onCheckedChange={() => setTicked((t) => (t.includes(s.code) ? t.filter((c) => c !== s.code) : [...t, s.code]))}
                />
              )}
              <span className="font-medium">{stepLabel(s.code)}</span>
              {s.origin === "floor" && <Badge variant="floor">Added by safety floor</Badge>}
              <span className="text-xs text-muted-foreground">{s.cited_case_ids.join(", ")}</span>
              <span className="ml-auto"><WhyDrawer step={s} view={view} /></span>
            </li>
          ))}
          {final.length === 0 && view.class !== "normal" && (
            <p className="text-sm text-muted-foreground">
              {view.procedure.flags.includes("empty_procedure")
                ? "A precedent matched, but it gave no steps to recommend, so this goes to a human. Resolve it below."
                : "No covered steps. Resolve this case below."}
            </p>
          )}
        </ol>
        {view.procedure.flags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {view.procedure.flags.map((f) => <Badge key={f} variant="outline">{f}</Badge>)}
          </div>
        )}

        {decided ? (
          <p className="mt-4 text-sm">
            Decided: {view.decisions[view.decisions.length - 1].action} by {view.decisions[view.decisions.length - 1].reviewer}.
          </p>
        ) : (
          <div className="mt-4 flex flex-wrap gap-2">
            {view.review_mode === "one_click" && (
              <Button disabled={busy} onClick={() => decide("approve", final.map((s) => s.code))}>Approve</Button>
            )}
            {view.review_mode === "step_by_step" && (
              <Button disabled={busy || !allTicked} onClick={() => decide("confirm", final.map((s) => s.code))}>
                Confirm {ticked.length} of {final.length} steps
              </Button>
            )}
            {view.review_mode === "escalate" && (
              <Button onClick={() => open("resolve")}>Resolve</Button>
            )}
            <Button variant="outline" onClick={() => open("edit")}>Edit</Button>
            <Button variant="outline" onClick={() => open("reject")}>Reject</Button>
          </div>
        )}
        {done && <p className="mt-2 text-sm">{done}</p>}
      </Stage>

      {mode && !decided && (
        <Card className="stage-in border-primary">
          <CardHeader>
            <CardTitle>
              {mode === "resolve" ? "Resolution form" : mode === "edit" ? "Edit the procedure" : "Reject the recommendation"}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            {mode === "resolve" && (
              <div className="grid gap-2 md:grid-cols-2">
                <div>
                  <div className="font-medium">Covered</div>
                  {view.violations.filter((v) => v.coverage.status !== "no").map((v) => <div key={v.check}>{titleCase(v.check)}: steps pre-filled below</div>)}
                  {view.violations.every((v) => v.coverage.status === "no") && <div className="text-muted-foreground">Nothing covered.</div>}
                </div>
                <div>
                  <div className="font-medium">Not covered: needs your decision</div>
                  {view.violations.filter((v) => v.coverage.status === "no").map((v) => <div key={v.check}>{titleCase(v.check)} ({v.cause.replace(/_/g, " ")})</div>)}
                </div>
              </div>
            )}
            <StepPicker value={picked} onChange={setPicked} />
            <label className="flex flex-col gap-1">
              <span>{mode === "resolve" ? "Why the standard process didn't fit, and the lesson" : "Why"}</span>
              <Textarea value={rationale} onChange={(e) => setRationale(e.target.value)} />
            </label>
            {mode === "resolve" && (
              <label className="flex flex-col gap-1">
                <span>Outcome</span>
                <Input value={outcome} onChange={(e) => setOutcome(e.target.value)} />
              </label>
            )}
            <div className="flex gap-2">
              <Button disabled={busy || picked.length === 0 || !rationale.trim()} onClick={() => decide(mode, picked)}>
                {mode === "resolve" ? "Save as edge experience" : mode === "edit" ? "Save edit" : "Reject"}
              </Button>
              <Button variant="ghost" onClick={() => setMode("")}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function CasePage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading…</p>}>
      <CaseInner />
    </Suspense>
  );
}
