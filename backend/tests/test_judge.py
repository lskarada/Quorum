"""Hermetic tests for the LLM-as-judge (Phase 7 Task 7.4)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

from quorum.audit.writer import AuditWriter
from quorum.eval.eval_case import EvalCase
from quorum.eval.judge import judge_case, judge_run_dir
from quorum.llm.client import LLMClient, LLMResponse


def _llm_stub() -> LLMClient:
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "x"
    return llm


def _eval_case(cid: str, gt: str, acceptable: list[str] | None = None) -> EvalCase:
    return EvalCase(
        case_id=cid,
        corpus="nejm",
        source="test",
        initial_presentation="x",
        ground_truth_diagnosis=gt,
        acceptable_partial_credit=acceptable or [],
    )


async def test_judge_returns_full_credit():
    llm = _llm_stub()
    llm.complete = AsyncMock(
        return_value=LLMResponse(
            content=json.dumps({"score": "full_credit", "rationale": "match"}),
            tokens_used=50,
            cost_usd=0.001,
            model="stub",
        )
    )
    score, rationale = await judge_case(
        ground_truth="SLE",
        acceptable_partial_credit=[],
        ai_committed="systemic lupus erythematosus",
        llm=llm,
    )
    assert score == "full_credit"
    assert rationale == "match"


async def test_judge_handles_parse_failure_as_no_credit():
    llm = _llm_stub()
    llm.complete = AsyncMock(
        return_value=LLMResponse(
            content="not json at all",
            tokens_used=10,
            cost_usd=0.0001,
            model="stub",
        )
    )
    score, rationale = await judge_case(
        ground_truth="SLE",
        acceptable_partial_credit=[],
        ai_committed="X",
        llm=llm,
    )
    assert score == "no_credit"
    assert "parse failure" in rationale


async def test_judge_rejects_unknown_score_value():
    llm = _llm_stub()
    llm.complete = AsyncMock(
        return_value=LLMResponse(
            content=json.dumps({"score": "maybe_credit"}),
            tokens_used=10,
            cost_usd=0.0001,
            model="stub",
        )
    )
    score, _ = await judge_case(
        ground_truth="SLE",
        acceptable_partial_credit=[],
        ai_committed="X",
        llm=llm,
    )
    assert score == "no_credit"


async def test_judge_run_dir_skips_existing_entries(tmp_path):
    """Idempotency: pre-existing judge_results.json entries are kept."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    # Pre-seed two cases
    for cid in ("c1", "c2"):
        w = AuditWriter(root=tmp_path, run_id="run", case_id=cid, model="stub")
        w.set_final(committed_diagnosis="SLE", real_cost_usd=0.0)
        w.close()
    # Pre-populate judge_results.json with c1
    (run_dir / "judge_results.json").write_text(
        json.dumps({"c1": {"score": "full_credit", "rationale": "pre-existing"}})
    )

    llm = _llm_stub()
    call_count = {"n": 0}
    async def fake_complete(**kwargs):
        call_count["n"] += 1
        return LLMResponse(
            content=json.dumps({"score": "partial_credit", "rationale": "x"}),
            tokens_used=10,
            cost_usd=0.0,
            model="stub",
        )
    llm.complete = fake_complete

    cases = {
        "c1": _eval_case("c1", "SLE"),
        "c2": _eval_case("c2", "SLE", acceptable=["lupus"]),
    }
    out = await judge_run_dir(run_dir, cases, llm)

    assert out["c1"]["score"] == "full_credit"  # untouched
    assert out["c1"]["rationale"] == "pre-existing"
    assert out["c2"]["score"] == "partial_credit"  # newly judged
    assert call_count["n"] == 1  # only c2 was judged
