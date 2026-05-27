"""AuditWriter: streams CaseAudit JSONL to disk."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schemas import CaseAudit, TurnRecord


class AuditWriter:
    def __init__(
        self,
        root: Path,
        run_id: str,
        case_id: str,
        model: str,
        panel_config_name: Optional[str] = None,
    ):
        self.root = root
        self.run_id = run_id
        self.case_id = case_id
        self.dir = root / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{case_id}.audit.jsonl"
        self.audit = CaseAudit(
            case_id=case_id,
            run_id=run_id,
            model=model,
            panel_config_name=panel_config_name,
        )

    def record_turn(self, **kwargs) -> None:
        if "turn_index" not in kwargs:
            kwargs["turn_index"] = len(self.audit.turns) + 1
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.now(timezone.utc)
        self.audit.turns.append(TurnRecord(**kwargs))

    def set_final(
        self,
        committed_diagnosis: Optional[str] = None,
        final_posterior: Optional[dict[str, float]] = None,
        real_cost_usd: float = 0.0,
        simulated_cost_usd: float = 0.0,
    ) -> None:
        self.audit.final_committed_diagnosis = committed_diagnosis
        self.audit.final_posterior = final_posterior or {}
        self.audit.real_cost_usd = real_cost_usd
        self.audit.simulated_cost_usd = simulated_cost_usd
        self.audit.completed_at = datetime.now(timezone.utc)

    def set_judge(self, score: str, rationale: str) -> None:
        self.audit.judge_score = score  # type: ignore[assignment]
        self.audit.judge_rationale = rationale

    def close(self) -> None:
        self.path.write_text(self.audit.to_jsonl())
