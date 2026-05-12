// Quorum frontend types — mirror of backend Pydantic schemas in
// backend/src/quorum/orchestrator/schemas.py.
//
// Drift between this file and the Pydantic source is caught by
// src/lib/__tests__/types.parity.test.ts (Phase 7). When you change a
// schema, update both sides in the same commit.

export const AgentRoles = [
  "hypothesis",
  "test_chooser",
  "challenger",
  "stewardship",
  "checklist",
] as const;

export type AgentRole = (typeof AgentRoles)[number];

export interface Citation {
  source: string;
  title?: string;
  url?: string;
  excerpt?: string; // <=200 chars
}

export interface DiagnosisCandidate {
  name: string;
  icd10?: string;
  posterior: number; // 0..1
  rationale: string;
  supporting_findings: string[];
  against_findings: string[];
  citations: Citation[];
}

export interface Differential {
  candidates: DiagnosisCandidate[];
  iteration: number;
}

export interface NextTest {
  name: string;
  rationale: string;
  estimated_cost_usd?: number;
  information_gain_estimate?: number;
  discriminates_between: string[];
  citations: Citation[];
}

export interface AgentMessage {
  role: AgentRole;
  iteration: number;
  content: string;
  structured_output?: Differential | NextTest | Record<string, unknown>;
  citations: Citation[];
  timestamp: string; // ISO
  tokens_used: number;
  cost_usd: number;
}

export interface CaseInput {
  case_id?: string;
  presentation: string;
  available_tests: string[];
  budget_usd?: number;
  max_iterations: number;
}

export type TerminationReason =
  | "consensus"
  | "budget"
  | "max_iterations"
  | "error";

export interface FinalVerdict {
  case_id?: string;
  final_differential: Differential;
  recommended_next_test?: NextTest;
  confidence: number;
  iterations_used: number;
  total_tokens: number;
  total_cost_usd: number;
  transcript: AgentMessage[];
  termination_reason: TerminationReason;
}

// SSE event discriminated union — mirrors backend StreamEvent.
export type StreamEvent =
  | { event: "agent_start"; data: { role: AgentRole; iteration: number } }
  | { event: "agent_token"; data: { role: AgentRole; delta: string } }
  | { event: "agent_complete"; data: { message: AgentMessage } }
  | { event: "round_complete"; data: { iteration: number } }
  | { event: "verdict"; data: { verdict: FinalVerdict } }
  | { event: "error"; data: { message: string } };
