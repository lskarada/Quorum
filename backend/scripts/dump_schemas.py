"""Dump Pydantic JSON schemas for cross-language parity checks.

Writes data/schemas/quorum.schema.json with a `$defs`-style bundle of every
orchestrator schema. The frontend parity test consumes this to verify
TypeScript types in `src/lib/types.ts` cover the same surface area.

Run:
    uv run python scripts/dump_schemas.py
"""
from __future__ import annotations

import json
from pathlib import Path

from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    CaseInput,
    Citation,
    DiagnosisCandidate,
    Differential,
    FinalVerdict,
    NextTest,
    StreamEvent,
)

SCHEMAS = {
    "AgentRole": AgentRole,
    "Citation": Citation,
    "DiagnosisCandidate": DiagnosisCandidate,
    "Differential": Differential,
    "NextTest": NextTest,
    "AgentMessage": AgentMessage,
    "CaseInput": CaseInput,
    "FinalVerdict": FinalVerdict,
    "StreamEvent": StreamEvent,
}


def _schema(model) -> dict:
    # AgentRole is a str-enum, not a BaseModel; handle separately.
    if model is AgentRole:
        return {
            "type": "string",
            "enum": [m.value for m in AgentRole],
            "title": "AgentRole",
        }
    return model.model_json_schema()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out_path = repo_root / "data" / "schemas" / "quorum.schema.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    bundle = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Quorum schemas",
        "version": "0.1.0",
        "$defs": {name: _schema(model) for name, model in SCHEMAS.items()},
    }
    out_path.write_text(json.dumps(bundle, indent=2) + "\n")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
