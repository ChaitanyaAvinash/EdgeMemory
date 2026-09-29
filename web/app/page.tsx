"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ClassBadge, MaturityBadge, ReviewBadge } from "@/components/badges";
import { CountUp, FadeOnScroll, Marquee, Parallax, Reveal, SplitWords } from "@/components/motion";
import { Badge } from "@/components/ui/badge";
import { api, type BenchmarkData, type CaseClass, type QueueItem } from "@/lib/api";

const ORDER: CaseClass[] = ["unknown", "composed", "generalized", "known", "normal"];
const HELP: Record<CaseClass, string> = {
  unknown: "At least one failed check has no verified precedent. A human resolves it, and EdgeMemory learns.",
  composed: "Several checks failed; each has a precedent. Interaction precedents may change the plain combination.",
  generalized: "One failed check with a precedent that applies with listed differences.",
  known: "One failed check with a precedent that applies directly.",
  normal: "Every check passed.",
};
const TITLE: Record<CaseClass, string> = {
  unknown: "Needs a human",
  composed: "Composed",
  generalized: "Generalized",
  known: "Known",
  normal: "Normal",
};

const HOW = [
  ["Detect", "Six rule checks find what broke: budget, vendor, approver, duplicate, bank, quotes."],
  ["Recall", "For each failed check, memory finds how your people resolved it before, and a verifier checks each precedent really applies."],
  ["Compose", "Lessons combine into one procedure. When checks fail together, learned interactions change the plain sum. A safety floor can't be removed."],
  ["Decide & remember", "A human approves, edits or resolves. Hindsight remembers the decision, so the next one is easier."],
];

// "x of n" from the API, split so x can count up (the numbers themselves come from eval/report.py).
function OfStat({ text }: { text?: string }) {
  const m = text?.match(/^(\d+) of (\d+)$/);
  if (!m) return <span>{text ?? "—"}</span>;
  return (
    <span>
      <CountUp value={Number(m[1])} />
      <span className="text-muted-foreground"> of {m[2]}</span>
    </span>
  );
}

function Hero({ bench }: { bench: BenchmarkData | null }) {
  const c = bench?.reports.test?.arms.C as Record<string, Record<string, string>> | undefined;
  const h = bench?.replays.hindsight?.summary;
  const v = bench?.replays.vector?.summary;
  const stats = [
    { label: "false confidence on unknown cases", value: c?.M1_false_confidence?.text },
    { label: "required safety steps missed", value: c?.M2_floor_violations?.text },
    { label: "one-click reviews as memory learns", value: h?.one_click, note: v ? `vector memory: ${v.one_click}` : "" },
  ];
  return (
    <section className="relative mx-[calc(50%-50vw)] flex min-h-[88vh] flex-col justify-center overflow-hidden">
      {/* Parallax layers: light, grid, and an outlined word moving at different speeds. */}
      <Parallax speed={0.35} className="pointer-events-none absolute inset-0 -z-10">
        <div className="drift absolute -right-[10%] -top-[15%] h-[70vh] w-[70vh] rounded-full bg-signal/25 blur-[120px]" />
        <div className="drift absolute -bottom-[20%] -left-[10%] h-[50vh] w-[50vh] rounded-full bg-foreground/10 blur-[120px] [animation-delay:-8s]" />
      </Parallax>
      <Parallax speed={0.15} className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] bg-[size:72px_72px] opacity-40 [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" />
      </Parallax>
      <Parallax speed={-0.12} className="pointer-events-none absolute -right-8 bottom-[8%] -z-10 hidden md:block">
        <span className="font-display text-[16rem] italic leading-none text-transparent [-webkit-text-stroke:1px_var(--border)]">
          memory
        </span>
      </Parallax>

      <div className="mx-auto w-full max-w-6xl px-4 md:px-6">
      <FadeOnScroll className="flex flex-col gap-8">
        <Reveal>
          <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-signal" /> Procurement exception copilot
          </span>
        </Reveal>
        <h1 className="font-display text-[12vw] leading-[0.9] md:text-[5.75rem] xl:text-[6.5rem]">
          <SplitWords text="Where the happy path {breaks,}" start={150} />
          <br />
          <SplitWords text="and how your people {fixed it.}" start={550} />
        </h1>
        <Reveal delay={900} className="max-w-xl text-lg text-muted-foreground">
          Normal automation encodes the happy path. EdgeMemory learns where it breaks: it finds how each failed check
          was resolved before, composes a procedure, says plainly when nothing applies, and learns from every human
          decision.
        </Reveal>
        <Reveal delay={1050} className="flex flex-wrap gap-3">
          <a
            href="#queue"
            className="group inline-flex h-12 items-center gap-2 rounded-full bg-foreground px-7 text-background transition-all duration-300 hover:bg-signal hover:text-white"
          >
            Open the queue <span className="transition-transform duration-300 group-hover:translate-y-0.5">↓</span>
          </a>
          <Link
            href="/demo"
            className="group inline-flex h-12 items-center gap-2 rounded-full border border-foreground/30 px-7 transition-all duration-300 hover:border-foreground hover:bg-foreground hover:text-background"
          >
            Run the demo <span className="transition-transform duration-300 group-hover:translate-x-1">→</span>
          </Link>
        </Reveal>
      </FadeOnScroll>

      {c && (
        <div className="mt-16 grid gap-6 border-t pt-8 md:grid-cols-3">
          {stats.map((s, i) => (
            <Reveal key={s.label} delay={1200 + i * 120} className="flex flex-col gap-1">
              <span className="font-display text-5xl md:text-6xl">
                <OfStat text={s.value} />
              </span>
              <span className="text-sm text-muted-foreground">
                {s.label}
                {s.note && <span className="block text-xs">{s.note}</span>}
              </span>
            </Reveal>
          ))}
          <Reveal delay={1600} className="text-xs text-muted-foreground md:col-span-3">
            Blind-labelled test cases, each arm run once. Synthetic data, small sample.{" "}
            <Link href="/benchmark" className="link-u text-foreground">See the benchmark →</Link>
          </Reveal>
        </div>
      )}
      </div>
    </section>
  );
}

export default function QueuePage() {
  const [queue, setQueue] = useState<Record<CaseClass, QueueItem[]> | null>(null);
  const [bench, setBench] = useState<BenchmarkData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.queue().then(setQueue).catch((e) => setError(String(e)));
    api.benchmark().then(setBench).catch(() => {});
  }, []);

  const open = queue ? ORDER.filter((k) => (queue[k] ?? []).length > 0) : [];

  return (
    <div className="flex flex-col">
      <Hero bench={bench} />

      <Marquee
        className="mx-[calc(50%-50vw)] border-y py-5 font-display text-3xl italic md:text-5xl"
        items={["Budget", "Vendor", "Approver", "Duplicate", "Bank", "Quotes", "Related party"]}
      />

      <section className="grid gap-px overflow-hidden py-20 md:grid-cols-4">
        {HOW.map(([title, body], i) => (
          <Reveal key={title} delay={i * 120} className="group flex flex-col gap-3 border-t pt-6 md:pr-8">
            <span className="font-mono text-xs text-muted-foreground">0{i + 1}</span>
            <h3 className="font-display text-3xl transition-colors duration-500 group-hover:text-signal">{title}</h3>
            <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
          </Reveal>
        ))}
      </section>

      <section id="queue" className="scroll-mt-24 flex flex-col gap-10">
        <Reveal className="flex flex-wrap items-end justify-between gap-4">
          <h2 className="font-display text-5xl md:text-6xl">
            The <span className="italic text-signal">queue</span>
          </h2>
          <p className="max-w-md text-sm text-muted-foreground">
            Open purchase-request exceptions, grouped by what EdgeMemory knows about them.
          </p>
        </Reveal>
        {error && <p className="text-sm text-destructive">Couldn&apos;t load the queue: {error}</p>}
        {!queue && !error && <p className="text-sm text-muted-foreground">Loading…</p>}
        {open.map((cls, gi) => (
          <Reveal key={cls} delay={gi * 80} className="flex flex-col">
            <div className="flex flex-wrap items-baseline gap-4 border-b pb-3">
              <h3 className="font-display text-3xl">{TITLE[cls]}</h3>
              <span className="font-mono text-xs text-muted-foreground">
                {queue![cls].length} {queue![cls].length === 1 ? "case" : "cases"}
              </span>
              <span className="text-sm text-muted-foreground md:ml-auto md:max-w-md md:text-right">{HELP[cls]}</span>
            </div>
            {queue![cls].map((c) => (
              <Link
                key={c.id}
                href={`/cases/${c.id}`}
                className="group relative flex flex-wrap items-center gap-3 overflow-hidden border-b py-4 text-sm"
              >
                <span className="absolute inset-0 -z-10 origin-left scale-x-0 bg-accent transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:scale-x-100" />
                <span className="w-36 font-mono text-xs text-muted-foreground transition-transform duration-500 group-hover:translate-x-2">
                  {c.id}
                </span>
                <span className="flex-1 text-base transition-transform duration-500 group-hover:translate-x-2">{c.vendor_name}</span>
                <span className="w-28 text-right tabular-nums">{c.amount_text}</span>
                <ClassBadge cls={cls} />
                <MaturityBadge maturity={c.maturity} />
                {c.novel_combination && <Badge variant="outline">novel combination</Badge>}
                <ReviewBadge mode={c.review_mode} />
                <span className="ml-2 -translate-x-2 opacity-0 transition-all duration-500 group-hover:translate-x-0 group-hover:opacity-100">
                  →
                </span>
              </Link>
            ))}
          </Reveal>
        ))}
        {queue && open.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No open cases. <Link className="link-u text-foreground" href="/new">Submit a request</Link> or run the{" "}
            <Link className="link-u text-foreground" href="/demo">demo</Link>.
          </p>
        )}
      </section>
    </div>
  );
}
