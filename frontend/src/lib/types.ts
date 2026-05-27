// Pydantic-derived types are codegen'd into ./types.generated.ts from
// data/schemas/quorum.schema.json (run `pnpm gen:types` after editing
// backend/src/quorum/orchestrator/schemas.py). Frontend-only types — runtime
// const arrays, the strict SSE discriminated union, and the error envelope —
// live here.

export type {
  AgentRole,
  Citation,
  DiagnosisCandidate,
  Differential,
  NextTest,
  AgentMessage,
  CaseInput,
  FinalVerdict,
} from "./types.generated";

// Re-export StreamEvent from the generated file under an alias because the
// frontend layers a strict discriminated union on top (below). The generated
// version is the loose backend contract; the strict one below is what UI
// code should consume.
export type { StreamEvent as StreamEventLoose } from "./types.generated";

// Runtime tuple used by routes that need to iterate / validate agent names.
export const AgentRoles = [
  "hypothesis",
  "test_chooser",
  "challenger",
  "stewardship",
  "checklist",
] as const;

export type TerminationReason =
  | "consensus"
  | "budget"
  | "max_iterations"
  | "checklist_stop"
  | "error";

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

import type {
  AgentRole as _AgentRole,
  Differential as _Differential,
  NextTest as _NextTest,
  FinalVerdict as _FinalVerdict,
} from "./types.generated";

// SSE event discriminated union — mirrors backend StreamEvent.
//
// Every event variant's `data` carries an optional `panel_id` so the
// /compare/stream endpoint (which multiplexes events from two panels
// against the same case) can be routed client-side to the correct column.
// Single-panel /diagnose/stream omits it.
export interface AgentCompleteHypothesisData {
  agent: "hypothesis";
  differential: _Differential;
  tokens_used: number;
  cost_usd: number;
  latency_ms: number;
  panel_id?: string;
}

export interface AgentCompleteTestChooserData {
  agent: "test_chooser";
  next_test: _NextTest;
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
      data: { agent: _AgentRole; iteration: number; panel_id?: string };
    }
  | { event: "agent_complete"; data: AgentCompleteData }
  | {
      event: "round_complete";
      data: { iteration: number; panel_id?: string };
    }
  | { event: "verdict"; data: _FinalVerdict & { panel_id?: string } }
  | { event: "error"; data: ErrorPayload & { panel_id?: string } };
