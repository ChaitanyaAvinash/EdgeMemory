"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader, Reveal } from "@/components/motion";
import { Term } from "@/components/term";
import { api, type BenchmarkData, type Metrics } from "@/lib/api";

type Result = Awaited<ReturnType<typeof api.evalResults>>["results"][number];

// Every number on this page comes from eval/report.py, eval/replay.py and api/metrics.py (CLAUDE.md rule 3);
// the page only picks fields and lays them out.
const ARMS: { key: string; name: string; what: string }[] = [
  { key: "A", name: "A", what: "no memory" },
  { key: "B", name: "B", what: "plain RAG" },
  { key: "C", name: "C · EdgeMemory", what: "Hindsight" },
  { key: "D", name: "D", what: "same pipeline, vector store" },
  { key: "E", name: "E", what: "C without interaction learning" },
];

function field(m: Metrics | undefined, path: string[]): string {
  let v: unknown = m;
  for (const p of path) v = v && typeof v === "object" ? (v as Record<string, unknown>)[p] : undefined;
  if (v === undefined || v === null) return "—";
  if (typeof v === "string" && / of 0$/.test(v)) return "—";
  if (typeof v === "number") return v.toLocaleString("en-IN");
  return String(v);
}

const ROWS: { label: React.ReactNode; better: "lower" | "higher"; path: string[] }[] = [
  { label: <><Term k="false confidence">False confidence</Term> on unknown cases</>, better: "lower", path: ["M1_false_confidence", "text"] },
  { label: <>Required <Term k="safety floor">safety steps</Term> missing</>, better: "lower", path: ["M2_floor_violations", "text"] },
  { label: "Case type identified correctly", better: "higher", path: ["M3_classification", "correct", "text"] },
  { label: "Procedure accuracy (F1, 0 to 1)", better: "higher", path: ["M4_procedure_f1", "macro"] },
  { label: <><Term k="interaction">Interaction</Term> procedures exactly right</>, better: "higher", path: ["M5_interaction", "exact_match", "text"] },
  { label: "New combinations flagged", better: "higher", path: ["M5_interaction", "novel_flagged", "text"] },
  { label: "Outdated pre-July lesson used", better: "lower", path: ["M6_outdated_lesson_use", "text"] },
  { label: <>Correct after a reviewer <Term k="override">override</Term></>, better: "higher", path: ["M7_post_override_correctness", "text"] },
  { label: "Sent to a human unnecessarily", better: "lower", path: ["M10_unnecessary_escalations", "text"] },
  { label: "Reviewer effort per 10 cases", better: "lower", path: ["M8_review_effort", "per_10_cases"] },
  { label: "Estimated minutes per 10 exception cases", better: "lower", path: ["M9_minutes", "per_10_exception_cases"] },
  { label: "LLM tokens per case", better: "lower", path: ["M11_cost_latency", "tokens_per_case"] },
];

function ArmTable({ arms }: { arms: Record<string, Metrics> }) {
  const shown = ARMS.filter((a) => arms[a.key]);
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs text-muted-foreground">
        <tr>
          <th className="py-1 pr-2">Measure</th>
          {shown.map((a) => (
            <th key={a.key} className={`px-2 ${a.key === "C" ? "text-signal" : ""}`}>
              {a.name}
              <div className="font-normal">{a.what}</div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {ROWS.map((r, i) => (
          <tr key={i} className="border-t">
            <td className="py-1 pr-2">
              {r.label} <span className="text-xs text-muted-foreground">({r.better} is better)</span>
            </td>
            {shown.map((a) => (
              <td key={a.key} className={`px-2 tabular-nums ${a.key === "C" ? "bg-signal-soft/50 font-medium" : ""}`}>
                {field(arms[a.key], r.path)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function LearningCurves({ replays }: { replays: BenchmarkData["replays"] }) {
  const h = replays.hindsight;
  const v = replays.vector;
  if (!h || !v) return null;
  const oneClick = h.curves.one_click_share.map((p, k) => ({
    i: p.i,
    Hindsight: p.share,
    "Vector store": v.curves.one_click_share[k]?.share,
  }));
  const effort = h.curves.review_effort.map((p, k) => ({
    i: p.i,
    Hindsight: p.per_case,
    "Vector store": v.curves.review_effort[k]?.per_case,
  }));
  const chart = (data: Record<string, number | undefined>[], y: string) => (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 16, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="i" label={{ value: "exception case, in date order", position: "insideBottom", offset: -8 }} />
        <YAxis allowDecimals={y !== "count"} />
        <Tooltip />
        <Legend verticalAlign="top" />
        <Line type="monotone" dataKey="Hindsight" stroke="var(--signal)" strokeWidth={2.5} dot={false} />
        <Line type="monotone" dataKey="Vector store" stroke="#9ca3af" strokeWidth={2} dot={false} strokeDasharray="5 4" />
      </LineChart>
    </ResponsiveContainer>
  );
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Term k="learning curve">Learning curve</Term>: the test cases replayed in date order
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          Both start from an empty memory. After each case, the reviewer&apos;s decision is remembered. Same pipeline,
          same model; only the memory differs.
        </p>
        <table className="text-sm">
          <thead className="text-left text-xs text-muted-foreground">
            <tr><th className="py-1 pr-4">Over {h.summary.exception_cases} exception cases</th><th className="pr-4">Hindsight</th><th>Vector store</th></tr>
          </thead>
          <tbody>
            <tr className="border-t"><td className="py-1 pr-4"><Term k="one-click review">One-click reviews</Term></td><td className="pr-4 font-medium">{h.summary.one_click}</td><td>{v.summary.one_click}</td></tr>
            <tr className="border-t"><td className="py-1 pr-4"><Term k="false confidence">False confidence</Term></td><td className="pr-4 font-medium">{h.summary.false_confidence}</td><td>{v.summary.false_confidence}</td></tr>
            <tr className="border-t"><td className="py-1 pr-4">Sent to a human</td><td className="pr-4 font-medium">{h.summary.escalations}</td><td>{v.summary.escalations}</td></tr>
            <tr className="border-t"><td className="py-1 pr-4">Mean reviewer effort per case (lower is better)</td><td className="pr-4 font-medium">{h.summary.mean_effort}</td><td>{v.summary.mean_effort}</td></tr>
          </tbody>
        </table>
        <div>
          <h3 className="text-sm font-medium">One-click reviews in the last 10 exception cases</h3>
          {chart(oneClick, "count")}
        </div>
        <div>
          <h3 className="text-sm font-medium">Average reviewer effort per case so far (lower is better)</h3>
          {chart(effort, "effort")}
        </div>
        <p className="text-xs text-muted-foreground">
          One case in each replay was sent to a human because the verifier prompt exceeded the free tier&apos;s
          single-request limit, not because of a judgement. Details in docs/benchmark.md.
        </p>
      </CardContent>
    </Card>
  );
}

export default function BenchmarkPage() {
  const [bench, setBench] = useState<BenchmarkData | null>(null);
  const [results, setResults] = useState<Result[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.benchmark().then(setBench).catch((e) => setError(String(e)));
    api.evalResults().then((r) => setResults(r.results)).catch((e) => setError(String(e)));
  }, []);

  const gates = (results ?? []).filter((r) => r.kind === "gate1" && r.summary);
  const runs = (results ?? []).filter((r) => r.kind === "run");
  const test = bench?.reports.test;
  const dev = bench?.reports.dev;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader eyebrow="Evidence" title="Does it {hold up?}">
        Counts, not percentages. Synthetic data, one domain, small sample. The answer key was written blind and frozen
        before scoring; each arm ran once on the test cases. Per-case results are below and in docs/benchmark.md.
      </PageHeader>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {test && (
        <Card className="stage-in [animation-delay:300ms]">
          <CardHeader><CardTitle className="font-display text-3xl">Test cases <span className="font-sans text-sm text-muted-foreground">24, each arm run once</span></CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <ArmTable arms={test.arms} />
            <p className="mt-2 text-xs text-muted-foreground">
              Where EdgeMemory is behind: plain RAG (B) handles cases after a reviewer override better, and D sends
              fewer cases to a human. B and A also give confident answers on unknown cases and miss required safety
              steps; C, D and E never do. Source: {test.file}.
            </p>
          </CardContent>
        </Card>
      )}
      {bench && <Reveal><LearningCurves replays={bench.replays} /></Reveal>}
      {dev && (
        <Card className="stage-in">
          <CardHeader><CardTitle className="font-display text-3xl">Dev cases <span className="font-sans text-sm text-muted-foreground">20, used for tuning</span></CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <ArmTable arms={dev.arms} />
            <p className="mt-2 text-xs text-muted-foreground">
              Prompts and rules were tuned on these cases, so they overstate how the system does on new ones. The dev
              split has no interaction, override or policy-change cases (shown as —). Source: {dev.file}.
            </p>
          </CardContent>
        </Card>
      )}
      {gates.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Gate G1 runs (15 hand-written borderline cases)</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr><th className="py-1">Run</th><th>False confidence</th><th>Classes correct</th><th>Citations resolved</th><th>Tokens</th></tr>
              </thead>
              <tbody>
                {gates.map((g) => (
                  <tr key={g.file} className="border-t">
                    <td className="py-1 font-mono text-xs">{g.file.replace(".json", "")}</td>
                    <td>{g.summary!.false_confidence} of {g.summary!.cases}</td>
                    <td>{g.summary!.classes_correct} of {g.summary!.cases}</td>
                    <td>{g.summary!.citations_resolved} of {g.summary!.citations_total}</td>
                    <td className="tabular-nums">{g.summary!.tokens?.toLocaleString("en-IN")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
      {runs.map((r) => (
        <details key={r.file} className="rounded-lg border">
          <summary className="cursor-pointer px-4 py-2 font-mono text-sm">{r.file} · per-case results</summary>
          <div className="overflow-x-auto px-4 pb-4">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr><th className="py-1">Arm</th><th>Case</th><th>Class</th><th>Review</th><th>Steps</th></tr>
              </thead>
              <tbody>
                {(r.rows ?? []).map((row, i) => (
                  <tr key={i} className="border-t align-top">
                    <td className="py-1">{String(row.arm)}</td>
                    <td className="font-mono text-xs">{String(row.case_id)}</td>
                    <td>{String(row.predicted_class)}</td>
                    <td>{String(row.review_mode || "—")}</td>
                    <td className="text-xs">{((row.predicted_steps as string[] | undefined) ?? []).join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ))}
    </div>
  );
}
