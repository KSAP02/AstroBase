// Typed calls to the backend. Every path starts with /api, which the Vite dev server proxies.

export interface RfqSummary {
  id: string;
  title: string;
  category: string;
}

export interface Rfq extends RfqSummary {
  quantity: string;
  material: string;
  delivery: string;
  technical: string[];
  mandatory: string[];
  required: string[];
  preferred: string[];
}

export type Verdict = "met" | "partial" | "not_met" | "not_evidenced" | "not_applicable";

export interface ScoredCriterion {
  id: string;
  tier: "mandatory" | "technical" | "required" | "preferred";
  text: string;
  verdict: Verdict;
  evidence: string;
  rationale: string;
  downgraded: boolean;
}

export interface Finding {
  criterion_id: string;
  text: string;
}

export interface Evaluation {
  id: number;
  created_at: string;
  rfq_id: string;
  vendor_name: string;
  score: number;
  raw_score: number;
  gate_passed: boolean;
  breakdown: Record<string, { points: number; max: number }>;
  criteria: ScoredCriterion[];
  reasons: Finding[];
  gaps: Finding[];
  model: string;
  prompt_version: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    // FastAPI errors look like {"detail": "..."} or, for validation errors, {"detail": [{msg: ...}]}
    let message = res.statusText;
    try {
      const body = await res.json();
      message = Array.isArray(body.detail)
        ? body.detail.map((d: { msg: string }) => d.msg).join("; ")
        : String(body.detail);
    } catch {
      // response wasn't JSON; keep the status text
    }
    throw new Error(`${res.status}: ${message}`);
  }
  return res.json() as Promise<T>;
}

export const getRfqs = () => request<RfqSummary[]>("/api/rfqs");

export const getRfq = (id: string) => request<Rfq>(`/api/rfqs/${encodeURIComponent(id)}`);

export const evaluate = (rfqId: string, vendorText: string) =>
  request<Evaluation>("/api/evaluations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rfq_id: rfqId, vendor_text: vendorText }),
  });

export const getEvaluations = () => request<Evaluation[]>("/api/evaluations?limit=20");
