"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { API, api, type DemoBeat } from "@/lib/api";

type Quota = Awaited<ReturnType<typeof api.quota>>;

export default function DemoPage() {
  const [date, setDate] = useState("");
  const [quota, setQuota] = useState<Quota | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);
  const [beats, setBeats] = useState<DemoBeat[]>([]);
  const [runningBeat, setRunningBeat] = useState("");
  const router = useRouter();

  useEffect(() => {
    api.fixtures().then((f) => setBeats(f.beats)).catch(() => {});
  }, []);

  const runBeat = async (b: DemoBeat) => {
    setRunningBeat(b.key);
    setStatus(b.replay_weeks ? "Replaying and waiting for Hindsight to consolidate…" : "Checking, recalling and composing from past cases…");
    try {
      const r = await api.beat(b.key);
      if (r.case) router.push(`/cases/${r.case.request.id}?demo=1`);
      else setStatus(`Replayed: ${JSON.stringify(r.replay)}`);
      await refresh();
    } catch (e) {
      setStatus(`${b.title} failed: ${e}`);
    } finally {
      setRunningBeat("");
    }
  };

  const refresh = async () => {
    const t0 = performance.now();
    const [c, q] = await Promise.all([api.clock(), api.quota()]);
    setLatency(Math.round(performance.now() - t0));
    setDate(c.date);
    setQuota(q);
  };
  useEffect(() => {
    refresh().catch((e) => setStatus(String(e)));
  }, []);

  const run = (label: string, f: () => Promise<unknown>) => async () => {
    setBusy(true);
    setStatus(`${label}…`);
    try {
      const r = await f();
      setStatus(`${label}: ${JSON.stringify(r)}`);
      await refresh();
    } catch (e) {
      setStatus(`${label} failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <PageHeader eyebrow="Stage" title="Demo {controls}">
        Reset and seed the demo memory, then run the scripted beats in order. Each beat opens its case with the staged
        reveal.
      </PageHeader>
      <Card className="stage-in [animation-delay:250ms]">
        <CardHeader><CardTitle>Demo script (SPEC §18)</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          <p className="text-muted-foreground">Run in order after Reset and Seed. Each beat sets the demo date and opens the case in demo mode.</p>
          {beats.map((b, i) => (
            <div key={b.key} className="flex flex-wrap items-center gap-2 border-t pt-2">
              <span className="w-5 text-muted-foreground">{i + 1}.</span>
              <span className="flex-1">{b.title}</span>
              <span className="text-xs text-muted-foreground">{b.claim}</span>
              <Button size="sm" disabled={!!runningBeat || busy} onClick={() => runBeat(b)}>
                {runningBeat === b.key ? "Running…" : "Run"}
              </Button>
              {b.request && <Link className="text-xs text-primary hover:underline" href={`/cases/${b.request.request_id}?demo=1`}>open</Link>}
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Demo clock</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2 text-sm">
          <Input type="date" className="w-44" value={date} onChange={(e) => setDate(e.target.value)} />
          <Button size="sm" disabled={busy} onClick={run("Set clock", () => api.setClock(date))}>Set</Button>
          <span className="text-muted-foreground">New requests are dated to this day.</span>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Demo bank</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2 text-sm">
          <Button size="sm" variant="outline" disabled={busy} onClick={run("Reset", api.reset)}>Reset</Button>
          <Button size="sm" disabled={busy} onClick={run("Seed", api.seed)}>Seed (37 memories, ~3 min)</Button>
          <Button size="sm" variant="outline" disabled={busy} onClick={run("Replay 3 weeks", async () => { const r = await fetch(`${API}/demo/replay?weeks=3`, { method: "POST" }); return r.json(); })}>Replay 3 weeks</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>LLM quota left (free tiers)</CardTitle></CardHeader>
        <CardContent className="text-sm">
          {quota ? (
            <ul className="flex flex-col gap-1">
              {Object.entries(quota.models).map(([m, q]) => (
                <li key={m}>
                  <span className="font-mono text-xs">{m}</span>: {q.requests_left ?? "?"} requests
                  {q.tokens_left !== null && <>, {q.tokens_left.toLocaleString("en-IN")} tokens</>} left
                  <span className="text-muted-foreground"> ({q.window === "rolling_24h" ? "last 24 h" : `Pacific day ${quota.pacific_date}`})</span>
                </li>
              ))}
            </ul>
          ) : (
            "Loading…"
          )}
          {latency !== null && <p className="mt-2 text-xs text-muted-foreground">API round trip: {latency} ms</p>}
        </CardContent>
      </Card>
      {status && <p className="break-all text-xs text-muted-foreground">{status}</p>}
    </div>
  );
}
