// Codegen guard (Phase 3).
//
// `frontend/src/lib/types.generated.ts` is produced by `pnpm gen:types`
// from `data/schemas/quorum.schema.json`. These tests catch:
//   - Manual edits to the generated file (the banner must remain).
//   - Drift between the Pydantic schema and the generated TS, by
//     re-checking that every $defs entry has a matching interface or
//     type alias in the generated file.
//
// Run `pnpm gen:types` before `vitest` if the schema changed.
import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const GENERATED_PATH = resolve(__dirname, "../types.generated.ts");
const SCHEMA_PATH = resolve(__dirname, "../../../../data/schemas/quorum.schema.json");

describe("types codegen", () => {
  it("generated types file exists and carries a DO NOT EDIT banner", () => {
    expect(existsSync(GENERATED_PATH)).toBe(true);
    const text = readFileSync(GENERATED_PATH, "utf-8");
    expect(text).toMatch(/DO NOT EDIT/i);
    expect(text).toMatch(/json-schema-to-typescript|generated/i);
  });

  it("generated types cover every $defs entry in the Pydantic schema", () => {
    expect(existsSync(GENERATED_PATH)).toBe(true);
    const text = readFileSync(GENERATED_PATH, "utf-8");
    const schema = JSON.parse(readFileSync(SCHEMA_PATH, "utf-8")) as {
      $defs?: Record<string, unknown>;
    };
    const defs = Object.keys(schema.$defs ?? {});
    const missing = defs.filter(
      (name) =>
        !new RegExp(`\\b(?:interface|type|enum)\\s+${name}\\b`).test(text),
    );
    expect(missing).toEqual([]);
  });
});
