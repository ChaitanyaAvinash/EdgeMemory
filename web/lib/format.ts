// Indian number formatting: 480000 -> "₹4,80,000" (SPEC §15.2). Numbers themselves always come from the API.
export function inr(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function stepLabel(code: string): string {
  return code.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}
