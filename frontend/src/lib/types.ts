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
  | "checklist_stop"
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
  schema_version: number;
  is_error: boolean;
}

// Backend error envelope (A3 of docs/IMPLEMENTATION_PLAN.md).
export type ErrorCode =
  | "provider_429"
  | "provider_timeout"
  | "parse_failure"
  | "schema_violation"
  | "internal";

export interface ErrorPayload {
  code: ErrorCode;
  message: string;
  retriable: boolean;
  http_status: number | null;
}

// SSE event discriminated union — mirrors backend StreamEvent.
//
// Every event variant's `data` carries an optional `panel_id` so the
// /compare/stream endpoint (which multiplexes events from two panels
// against the same case) can be routed client-side to the correct column.
// Single-panel /diagnose/stream omits it.
export interface AgentCompleteHypothesisData {
  agent: "hypothesis";
  differential: Differential;
  tokens_used: number;
  cost_usd: number;
  latency_ms: number;
  panel_id?: string;
}

export interface AgentCompleteTestChooserData {
  agent: "test_chooser";
  next_test: NextTest;
  tokens_used: number;
  cost_usd: number;
  latency_ms: number;
  panel_id?: string;
}

// Challenger/Stewardship/Checklist emit structured payloads whose exact
// shape is still being iterated on the backend. We accept an opaque
// structured_output so the frontend can render a generic agent card while
// the schemas settle.
export interface AgentCompleteGenericData {
  agent: "challenger" | "stewardship" | "checklist";
  structured_output?: Record<string, unknown>;
  content?: string;
  tokens_used: number;
  cost_usd: number;
  latency_ms: number;
  panel_id?: string;
}

export type AgentCompleteData =
  | AgentCompleteHypothesisData
  | AgentCompleteTestChooserData
  | AgentCompleteGenericData;

export type StreamEvent =
  | {
      event: "agent_start";
      data: { agent: AgentRole; iteration: number; panel_id?: string };
    }
  | { event: "agent_complete"; data: AgentCompleteData }
  | {
      event: "round_complete";
      data: { iteration: number; panel_id?: string };
    }
  | { event: "verdict"; data: FinalVerdict & { panel_id?: string } }
  | { event: "error"; data: ErrorPayload & { panel_id?: string } };
