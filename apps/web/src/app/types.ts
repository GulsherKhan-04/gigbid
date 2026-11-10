import type { Claim, Evidence } from "../components/EvidenceHover";

export type JobState = {
  job?: { title?: string; description?: string; budget?: { min?: number; max?: number; currency?: string }; required_skills?: string[] };
  job_spec?: { requirements: string[]; deliverables: string[]; hidden_needs: string[]; screening_questions: string[]; category: string; timeline: string };
  risk_report?: { score: number; client_quality: number; flags: string[]; injected_instructions: string[]; explanation: string };
  fit_report?: { score: number; reasons: string[]; matrix: { requirement: string; evidence_ids: string[]; strength: string; note: string }[] };
  decision?: { action: string; reason: string };
  price_quote?: { amount_usd: number; rate_type: string; connects_cost: number; worth_connects: boolean; rationale: string };
  proposal_draft?: { cover_letter: string; screening_answers: string[]; claims: Claim[]; unsupported_removed?: string[]; unsupported_before?: number; revision: number };
  critiques?: { passed: boolean; reasons: string[] }[];
  compliance_verdict?: { allowed: boolean; violations: string[] };
  evidence?: { evidence_id: string; title?: string; project?: string; type: string; source: string; text: string; outcome?: string }[];
  status?: string; errors?: string[];
  pending_approval: { kind: string; dry_run?: { dry_run?: boolean; preview?: { bid_amount_usd?: number; connects_cost?: number; rate_type?: string } }; evidence?: Evidence }[];
  trace?: { node: string; seconds?: number; usd?: number; model?: string; prompt_tokens?: number; completion_tokens?: number; summary?: string }[];
  usage?: Record<string, { usd?: number; seconds?: number; prompt_tokens?: number; completion_tokens?: number; model?: string }>;
};
export type Detail = { row: { job_id: string; title?: string; status?: string; action?: string; fit?: number }; state: JobState };
