// Request text with the extracted signals' source spans highlighted (SPEC §15.1 stage 1).
export function Highlighted({ text, spans }: { text: string; spans: string[] }) {
  if (!text) return <span className="text-muted-foreground">(none)</span>;
  const marks: [number, number][] = [];
  const lower = text.toLowerCase();
  for (const s of spans) {
    const i = s ? lower.indexOf(s.toLowerCase()) : -1;
    if (i >= 0) marks.push([i, i + s.length]);
  }
  marks.sort((a, b) => a[0] - b[0]);
  const out: React.ReactNode[] = [];
  let at = 0;
  marks.forEach(([a, b], k) => {
    if (a < at) return;
    out.push(text.slice(at, a));
    out.push(
      <mark key={k} className="rounded bg-amber-200 px-0.5 text-amber-950 dark:bg-amber-700/60 dark:text-amber-50">
        {text.slice(a, b)}
      </mark>,
    );
    at = b;
  });
  out.push(text.slice(at));
  return <span className="whitespace-pre-wrap">{out}</span>;
}
