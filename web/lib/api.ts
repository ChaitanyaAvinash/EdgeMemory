// Typed client for the EdgeMemory API, hand-mirrored against the FastAPI schema (api/views.py, api/main.py).
export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Verdict = "yes" | "partial" | "no" | "";
export type CaseClass = "normal" | "known" | "generalized" | "composed" | "unknown";
export type ReviewMode = "one_click" | "step_by_step" | "escalate" | "";

export interface CitedCase {
  case_id: string;
  amount: number;
  amount_text: string;
  band: string;
  category: string;
  resolved_at: string;
  status: string;
  steps: string[];
  kind: string;
}

export interface Candidate {
  candidate_id: string;
  memory_type: string;
  memory_text: string;
  case_ids: string[];
  verdict: Verdict;
  differences: string[];
  reason: string;
  guard: string;
  combo: string;
  cases: CitedCase[];
}

export interface ViolationView {
  check: string;
  tag: string;
  cause: string;
  detail: string;
  source: string;
  source_span: string;
  coverage: {
    status: Verdict;
    case_ids: string[];
    strength: number;
    maturity: "" | "tentative" | "established";
    differences: string[];
    reason: string;
  };
  candidates: Candidate[];
}

export interface Step {
  code: string;
  reason: string;
  cited_case_ids: string[];
  origin: "memory" | "union" | "floor" | "default";
  class: string;
}

export interface CaseView {
  request: {
    id: string;
    submitted_at: string;
    vendor_id: string | null;
    vendor_name: string;
    amount: number | null;
    amount_text: string;
    band: string;
    cost_centre: string;
    category: string;
    urgency: string;
    requester_id: string;
    quotes_count: number;
    justification: string;
    email_thread: string;
    attachment_text: string;
    signals: { name: string; source: string; span: string }[];
    dropped_signals: { name: string; source: string; span: string; why: string }[];
    status: string;
  };
  class: CaseClass;
  novel_combination: boolean;
  maturity: string;
  review_mode: ReviewMode;
  summary: string;
  violations: ViolationView[];
  interactions: Candidate[];
  procedure: {
    steps: Step[];
    union_steps: { code: string; cited_case_ids: string[] }[];
    removed_from_union: { code: string; reason: string; cited_case_ids: string[] }[];
    conflicts: { pair: string[]; kept: string; dropped: string; reason: string }[];
    flags: string[];
    floor_added: string[];
  };
  decisions: { reviewer: string; action: string; final_steps: string[]; rationale: string; decided_at: string }[];
}

export interface QueueItem {
  id: string;
  vendor_name: string;
  amount_text: string;
  submitted_at: string;
  maturity: string;
  review_mode: ReviewMode;
  novel_combination: boolean;
  status: string;
}

export interface LessonsView {
  tag: string;
  observations: { id: string; text: string; case_ids: string[]; history: { previous_text: string; changed_at: string }[] }[];
  cases: { case_id: string; kind: string; steps: string[]; status: string; resolved_at: string; overridden_by: string }[];
  snapshots: { text: string; source_case_ids: string[]; fetched_at: string }[];
}

export interface DemoBeat {
  key: string;
  title: string;
  claim: string;
  clock?: string;
  replay_weeks?: number;
  request?: { request_id: string } & Record<string, unknown>;
  decision?: { action: string; final_steps: string[]; rationale: string; outcome: string };
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  queue: () => call<Record<CaseClass, QueueItem[]>>("/queue"),
  getCase: (id: string) => call<CaseView>(`/requests/${encodeURIComponent(id)}`),
  submit: (body: Record<string, unknown>) => call<CaseView>("/requests", { method: "POST", body: JSON.stringify(body) }),
  decide: (id: string, body: { action: string; final_steps: string[]; rationale: string; reviewer?: string; outcome?: string }) =>
    call<{ retained: { kind: string; document_id: string; tags: string[] }[]; case: CaseView }>(
      `/requests/${encodeURIComponent(id)}/decision`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  lessons: (tag: string) => call<LessonsView>(`/lessons?tag=${encodeURIComponent(tag)}`),
  benchmark: () => call<BenchmarkData>("/eval/benchmark"),
  evalResults: () => call<{ results: { file: string; kind: string; summary: Record<string, number> | null; arm: string | null; rows: Record<string, unknown>[] }[] }>("/eval/results"),
  quota: () => call<{ pacific_date: string; models: Record<string, { requests_left: number | null; tokens_left: number | null; window: string }> }>("/quota"),
  clock: () => call<{ date: string }>("/demo/clock"),
  setClock: (date: string) => call<{ date: string }>("/demo/clock", { method: "POST", body: JSON.stringify({ date }) }),
  seed: () => call<Record<string, unknown>>("/admin/seed", { method: "POST" }),
  fixtures: () => call<{ beats: DemoBeat[] }>("/demo/fixtures"),
  beat: (key: string) =>
    call<{ beat: string; case?: CaseView; replay?: Record<string, unknown> }>(`/demo/beat/${key}`, { method: "POST" }),
  reset: () => call<Record<string, unknown>>("/admin/reset", { method: "POST" }),
};

// The step library (config/step_library.yaml), for the resolution form and edits.
export const STEP_LIBRARY: Record<string, string[]> = {
  "Risk control": ["VERIFY_BANK_CALLBACK", "HOLD_PAYMENT", "ESCALATE_AUDIT", "DECLARE_CONFLICT_OF_INTEREST"],
  Compliance: ["HOLD_PO", "REQUEST_RENEWED_CERT", "VERIFY_GST_STATUS", "SOLE_SOURCE_FORM", "COLLECT_QUOTES",
    "CONDITIONAL_PO_WITH_QC", "INCOMING_QC_INSPECTION", "ATTACH_LINE_DOWN_EVIDENCE"],
  "Approval routing": ["STANDARD_APPROVAL", "ROUTE_DELEGATE", "ROUTE_NEXT_LEVEL_APPROVER", "ADD_CONTROLLER_SIGNOFF",
    "CATEGORY_HEAD_SIGNOFF", "ADD_CFO_SIGNOFF"],
  Convenience: ["ALLOW_BUDGET_OVERRUN", "EXPEDITE_PO", "LINK_MASTER_PO", "ALLOW_SPLIT_DELIVERY", "KEEP_VENDOR_ACTIVE"],
  Outcome: ["REQUEST_MORE_INFO", "REJECT_REQUEST"],
};

// /eval/benchmark: the latest scored reports (eval/report.py) and test learning curves (eval/replay.py).
export type Metrics = Record<string, Record<string, unknown>>;
export interface CurvePoint { i: number; date: string; share?: number; of?: number; per_case?: number; false_confidence?: number }
export interface Replay {
  file: string;
  curves: { one_click_share: CurvePoint[]; review_effort: CurvePoint[]; false_confidence: CurvePoint[] };
  summary: { exception_cases: number; one_click: string; escalations: string; false_confidence: string; classes_correct: string; mean_effort: number | null };
}
export interface BenchmarkData {
  reports: Partial<Record<"dev" | "test", { file: string; arms: Record<string, Metrics> }>>;
  replays: Partial<Record<"hindsight" | "vector", Replay>>;
}
