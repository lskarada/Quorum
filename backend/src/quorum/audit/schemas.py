"""AuditTrail Pydantic schemas (v1, append-only).

A CaseAudit is one JSONL file per case with a header line followed by
one line per turn. The header captures run-level metadata; each turn
record captures everything the agent, gatekeeper, or safety check did.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "audit.v1"

MessageRole = Literal[
    "in",
    "out",
    "gatekeeper_query",
    "gatekeeper_response",
    "safety_check",
]


class TurnRecord(BaseModel):
    schema_version: Literal["audit.v1"] = SCHEMA_VERSION
    turn_index: int
    timestamp: datetime
    agent: str
    message_role: MessageRole
    content: str
    tokens: int = 0
    cost_usd: float = 0.0
    posterior_at_turn: dict[str, float] = Field(default_factory=dict)
    extra: dict = Field(default_factory=dict)


class CaseAudit(BaseModel):
    schema_version: Literal["audit.v1"] = SCHEMA_VERSION
    case_id: str
    run_id: str
    model: str
    panel_config_name: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    turns: list[TurnRecord] = Field(default_factory=list)
    final_committed_diagnosis: Optional[str] = None
    final_posterior: dict[str, float] = Field(default_factory=dict)
    simulated_cost_usd: float = 0.0
    real_cost_usd: float = 0.0
    judge_score: Optional[Literal["full_credit", "partial_credit", "no_credit"]] = None
    judge_rationale: Optional[str] = None

    def to_jsonl(self) -> str:
        header = self.model_copy(update={"turns": []}).model_dump_json()
        lines = [header]
        for turn in self.turns:
            lines.append(turn.model_dump_json())
        return "\n".join(lines) + "\n"
