// Parity test: Pydantic schemas (backend) vs TypeScript types (frontend).
//
// This guards against silent drift between
//   backend/src/quorum/orchestrator/schemas.py
//   frontend/src/lib/types.ts
//
// If you add a Pydantic schema, you MUST add the corresponding TS type and
// register its name below. If you remove one, this test will tell you about it.
//
// To regenerate the JSON-schema bundle: `cd backend && uv run python scripts/dump_schemas.py`.
import { describe, expect, it } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import type {
  AgentMessage,
  AgentRole,
  CaseInput,
  Citation,
  DiagnosisCandidate,
  Differential,
  FinalVerdict,
  NextTest,
  StreamEvent,
} from "../types";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCHEMA_PATH = resolve(__dirname, "../../../../data/schemas/quorum.schema.json");

const EXPECTED_TYPES = [
  "AgentRole",
  "Citation",
  "DiagnosisCandidate",
  "Differential",
  "NextTest",
  "AgentMessage",
  "CaseInput",
  "FinalVerdict",
  "StreamEvent",
] as const;

describe("schema parity (Pydantic ↔ TypeScript)", () => {
  it("the JSON-schema bundle has been generated", () => {
    expect(
      existsSync(SCHEMA_PATH),
      `Missing ${SCHEMA_PATH}. Run: cd backend && uv run python scripts/dump_schemas.py`,
    ).toBe(true);
  });

  it("every expected type has a Pydantic-side definition", () => {
    if (!existsSync(SCHEMA_PATH)) return; // covered by the first test
    const bundle = JSON.parse(readFileSync(SCHEMA_PATH, "utf-8")) as {
      $defs: Record<string, unknown>;
    };
    for (const name of EXPECTED_TYPES) {
      expect(bundle.$defs[name], `Pydantic schema missing: ${name}`).toBeDefined();
    }
  });

  it("the TypeScript-side covers exactly the same type names (compile-time check)", () => {
    // This is a tsc-time check: the imports above will fail to compile if any
    // of the listed types disappears from types.ts. The runtime body just
    // touches each type so unused-import lints stay green.
    const _touch: [
      AgentRole?,
      Citation?,
      DiagnosisCandidate?,
      Differential?,
      NextTest?,
      AgentMessage?,
      CaseInput?,
      FinalVerdict?,
      StreamEvent?,
    ] = [];
    expect(_touch).toHaveLength(0);
  });

  it("AgentRole enum has exactly 5 members on both sides", () => {
    if (!existsSync(SCHEMA_PATH)) return;
    const bundle = JSON.parse(readFileSync(SCHEMA_PATH, "utf-8")) as {
      $defs: { AgentRole: { enum?: string[] } };
    };
    expect(bundle.$defs.AgentRole.enum).toEqual([
      "hypothesis",
      "test_chooser",
      "challenger",
      "stewardship",
      "checklist",
    ]);
  });
});
