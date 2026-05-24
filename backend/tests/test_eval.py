"""Tests for the eval runner.

Cover: per-case JSON output, manifest, n_cases cap, cost guardrail,
idempotency.
"""
from __future__ import annotations

import json
import pathlib
from unittest.mock import AsyncMock, patch

import pytest
from quorum.eval.runner import run_eval
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import (
    CaseInput,
    DiagnosisCandidate,
    Differential,
    FinalVerdict,
)


def _dev_cheap_config() -> PanelConfig:
    return next(c for c in PanelConfig.list_available() if c.name == "dev_cheap")


def _baseline_config() -> PanelConfig:
    return next(
        c for c in PanelConfig.list_available() if c.name == "baseline_single_call"
    )


def _make_verdict(case_id: str) -> FinalVerdict:
    return FinalVerdict(
        case_id=case_id,
        final_differential=Differential(
            candidates=[
                DiagnosisCandidate(name="canned", posterior=0.9, rationale="r"),
            ],
            iteration=0,
        ),
        confidence=0.9,
        iterations_used=1,
        total_tokens=100,
        total_cost_usd=0.01,
        transcript=[],
        termination_reason="consensus",
        schema_version=1,
        is_error=False,
    )


def _cases(n: int) -> list[CaseInput]:
    return [
        CaseInput(case_id=f"c{i:03d}", presentation=f"presentation {i}")
        for i in range(n)
    ]


async def test_runner_writes_one_json_per_case(tmp_path: pathlib.Path):
    cases = _cases(3)
    results_dir = tmp_path / "run1"

    with patch("quorum.eval.runner.Panel") as mock_panel:
        instance = mock_panel.return_value
        instance.diagnose = AsyncMock(side_effect=lambda c: _make_verdict(c.case_id))
        await run_eval(iter(cases), _baseline_config(), n_cases=3, results_dir=results_dir)

    per_case = sorted(results_dir.glob("case_*.json"))
    assert len(per_case) == 3
    assert (results_dir / "manifest.json").exists()
    manifest = json.loads((results_dir / "manifest.json").read_text())
    assert manifest["panel"] == "baseline_single_call"
    assert "started_at" in manifest
    assert "finished_at" in manifest


async def test_runner_respects_n_cases(tmp_path: pathlib.Path):
    cases = _cases(20)
    results_dir = tmp_path / "capped"

    with patch("quorum.eval.runner.Panel") as mock_panel:
        instance = mock_panel.return_value
        instance.diagnose = AsyncMock(side_effect=lambda c: _make_verdict(c.case_id))
        await run_eval(iter(cases), _baseline_config(), n_cases=5, results_dir=results_dir)

    per_case = sorted(results_dir.glob("case_*.json"))
    assert len(per_case) == 5


async def test_runner_cost_guardrail(tmp_path: pathlib.Path, monkeypatch):
    cases = _cases(10)
    results_dir = tmp_path / "blocked"
    monkeypatch.setenv("QUORUM_MAX_COST_USD", "0.01")

    with pytest.raises(RuntimeError, match="exceeds QUORUM_MAX_COST_USD"):
        with patch("quorum.eval.runner.Panel"):
            await run_eval(
                iter(cases),
                _baseline_config(),
                n_cases=10,
                results_dir=results_dir,
                confirm_cost=False,
            )


async def test_runner_idempotency_skips_existing(tmp_path: pathlib.Path):
    cases = _cases(3)
    results_dir = tmp_path / "resume"
    results_dir.mkdir()
    # Pre-populate one case's JSON as if a previous run completed it.
    pre_existing = _make_verdict("c000")
    (results_dir / "case_c000.json").write_text(pre_existing.model_dump_json(indent=2))

    with patch("quorum.eval.runner.Panel") as mock_panel:
        instance = mock_panel.return_value
        instance.diagnose = AsyncMock(side_effect=lambda c: _make_verdict(c.case_id))
        await run_eval(iter(cases), _baseline_config(), n_cases=3, results_dir=results_dir)
        # Should only be called for the two remaining cases.
        called_cids = [call.args[0].case_id for call in instance.diagnose.call_args_list]
        assert sorted(called_cids) == ["c001", "c002"]

    per_case = sorted(results_dir.glob("case_*.json"))
    assert len(per_case) == 3
