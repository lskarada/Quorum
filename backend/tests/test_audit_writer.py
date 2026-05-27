"""AuditWriter tests (Phase 3 Task 3.2)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from quorum.audit.writer import AuditWriter


def test_writer_creates_dir_and_writes_file():
    with tempfile.TemporaryDirectory() as td:
        run_id = "test-run-123"
        writer = AuditWriter(
            root=Path(td), run_id=run_id, case_id="toy-1", model="sonnet-4.6"
        )
        writer.record_turn(
            agent="hypothesis", message_role="out", content="hello",
            tokens=10, cost_usd=0.001,
        )
        writer.set_final(
            committed_diagnosis="SLE",
            final_posterior={"SLE": 0.9, "MCTD": 0.1},
            real_cost_usd=0.5,
            simulated_cost_usd=120.0,
        )
        writer.close()

        path = Path(td) / run_id / "toy-1.audit.jsonl"
        assert path.exists()
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2

        header = json.loads(lines[0])
        assert header["case_id"] == "toy-1"
        assert header["final_committed_diagnosis"] == "SLE"
        assert header["final_posterior"] == {"SLE": 0.9, "MCTD": 0.1}
        assert header["real_cost_usd"] == 0.5
        assert header["simulated_cost_usd"] == 120.0
        assert header["turns"] == []  # header strips turn array

        turn = json.loads(lines[1])
        assert turn["agent"] == "hypothesis"
        assert turn["message_role"] == "out"
        assert turn["tokens"] == 10


def test_writer_records_multiple_event_types(tmp_path):
    writer = AuditWriter(root=tmp_path, run_id="r", case_id="c", model="m")
    writer.record_turn(agent="hypothesis", message_role="out", content="dx")
    writer.record_turn(agent="gatekeeper", message_role="gatekeeper_response", content="finding")
    writer.record_turn(agent="safety_checker", message_role="safety_check", content="OK")
    writer.set_final(committed_diagnosis="x")
    writer.close()

    lines = (tmp_path / "r" / "c.audit.jsonl").read_text().strip().splitlines()
    assert len(lines) == 4  # header + 3 turns
    roles = [json.loads(line).get("message_role") for line in lines[1:]]
    assert roles == ["out", "gatekeeper_response", "safety_check"]


def test_writer_turn_indices_are_sequential(tmp_path):
    writer = AuditWriter(root=tmp_path, run_id="r", case_id="c", model="m")
    writer.record_turn(agent="a", message_role="out", content="1")
    writer.record_turn(agent="b", message_role="out", content="2")
    writer.record_turn(agent="c", message_role="out", content="3")
    writer.close()
    lines = (tmp_path / "r" / "c.audit.jsonl").read_text().strip().splitlines()
    assert [json.loads(line)["turn_index"] for line in lines[1:]] == [1, 2, 3]
