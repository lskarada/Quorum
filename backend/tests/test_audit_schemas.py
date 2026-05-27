"""AuditTrail schema tests (Phase 3 Task 3.1)."""
from __future__ import annotations

from datetime import UTC, datetime

from quorum.audit.schemas import CaseAudit, TurnRecord


def test_turnrecord_roundtrip():
    t = TurnRecord(
        turn_index=3,
        timestamp=datetime.now(UTC),
        agent="hypothesis",
        message_role="out",
        content="Posterior: {SLE: 0.6, AML: 0.2}",
        tokens=350,
        cost_usd=0.012,
        posterior_at_turn={"SLE": 0.6, "AML": 0.2, "MCTD": 0.2},
    )
    t2 = TurnRecord.model_validate(t.model_dump())
    assert t == t2


def test_case_audit_aggregates_turns():
    audit = CaseAudit(case_id="toy-1", run_id="abc", model="sonnet-4.6")
    audit.turns.append(
        TurnRecord(
            turn_index=1,
            timestamp=datetime.now(UTC),
            agent="hypothesis",
            message_role="out",
            content="x",
            tokens=1,
            cost_usd=0.0,
            posterior_at_turn={},
        )
    )
    assert len(audit.turns) == 1


def test_case_audit_jsonl_format_with_no_turns():
    audit = CaseAudit(case_id="toy-1", run_id="abc", model="sonnet-4.6")
    lines = audit.to_jsonl().splitlines()
    assert len(lines) == 1  # header only
    import json
    header = json.loads(lines[0])
    assert header["case_id"] == "toy-1"
    assert header["schema_version"] == "audit.v1"


def test_case_audit_jsonl_format_with_turns():
    audit = CaseAudit(case_id="toy-1", run_id="abc", model="sonnet-4.6")
    audit.turns.append(
        TurnRecord(
            turn_index=1,
            timestamp=datetime.now(UTC),
            agent="hypothesis",
            message_role="out",
            content="hi",
            tokens=5,
            cost_usd=0.0,
            posterior_at_turn={},
        )
    )
    lines = audit.to_jsonl().splitlines()
    assert len(lines) == 2  # header + 1 turn
