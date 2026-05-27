"""Tests for the ensemble baseline runner (H2 control)."""
from __future__ import annotations

import json
import pathlib
from typing import Any
from unittest.mock import AsyncMock

import pytest
from quorum.eval.ensemble import EnsembleStats, run_ensemble
from quorum.llm.client import LLMResponse
from quorum.orchestrator.schemas import (
    CaseInput,
    Differential,
    FinalVerdict,
)

_CASE = CaseInput(case_id="ens_test", presentation="Stub presentation.")


def _diff_json(top: str, others: list[str] | None = None) -> str:
    """Build a Hypothesis-shaped JSON payload with `top` as candidate 0."""
    others = others or ["Alt One", "Alt Two"]
    candidates = [
        {
            "name": top,
            "icd10": "Z99.0",
            "posterior": 0.6,
            "rationale": "primary",
            "supporting_findings": [],
            "against_findings": [],
            "citations": [],
        }
    ] + [
        {
            "name": n,
            "icd10": None,
            "posterior": 0.2,
            "rationale": "alt",
            "supporting_findings": [],
            "against_findings": [],
            "citations": [],
        }
        for n in others
    ]
    return json.dumps({"candidates": candidates})


def _mock_llm_with_returns(returns: list[Any]) -> Any:
    """returns is a list whose items are either str (content) or Exception."""
    side_effects: list[Any] = []
    for r in returns:
        if isinstance(r, Exception):
            side_effects.append(r)
        else:
            side_effects.append(
                LLMResponse(
                    content=r,
                    tokens_used=42,
                    cost_usd=0.001,
                    model="anthropic/claude-haiku-4-5",
                )
            )
    llm = AsyncMock()
    llm.complete = AsyncMock(side_effect=side_effects)
    return llm


@pytest.mark.asyncio
async def test_majority_vote_picks_modal_diagnosis():
    """5 votes: ['A','A','B','A','C'] → 'A' wins with 3/5."""
    llm = _mock_llm_with_returns([
        _diff_json("A"),
        _diff_json("A"),
        _diff_json("B"),
        _diff_json("A"),
        _diff_json("C"),
    ])
    verdict, stats = await run_ensemble(
        _CASE, model="anthropic/claude-haiku-4-5", n_votes=5, llm=llm
    )
    assert verdict.final_differential.candidates[0].name == "A"
    # 3/5 votes → confidence 0.6, posterior 0.6
    assert verdict.confidence == pytest.approx(0.6)
    assert verdict.final_differential.candidates[0].posterior == pytest.approx(0.6)
    assert stats.n_votes_requested == 5
    assert stats.n_votes_successful == 5
    assert stats.n_votes_failed == 0
    assert stats.vote_distribution["a"] == 3
    assert verdict.is_error is False
    assert verdict.termination_reason == "consensus"


@pytest.mark.asyncio
async def test_unanimous_vote_returns_single_diagnosis_with_full_confidence():
    """All 5 same diagnosis → confidence 1.0, single aggregated candidate."""
    llm = _mock_llm_with_returns([_diff_json("UTI")] * 5)
    verdict, stats = await run_ensemble(
        _CASE, model="anthropic/claude-haiku-4-5", n_votes=5, llm=llm
    )
    assert verdict.confidence == pytest.approx(1.0)
    assert len(verdict.final_differential.candidates) == 1
    assert verdict.final_differential.candidates[0].name == "UTI"
    assert verdict.final_differential.candidates[0].posterior == pytest.approx(1.0)
    assert stats.vote_distribution == {"uti": 5}


@pytest.mark.asyncio
async def test_one_call_raises_degrades_to_majority_of_remaining():
    """1 of 5 calls fails → ensemble continues with 4; manifest stats note 1 failure."""
    llm = _mock_llm_with_returns([
        _diff_json("X"),
        _diff_json("X"),
        RuntimeError("openrouter 503"),
        _diff_json("Y"),
        _diff_json("X"),
    ])
    verdict, stats = await run_ensemble(
        _CASE, model="anthropic/claude-haiku-4-5", n_votes=5, llm=llm
    )
    assert verdict.final_differential.candidates[0].name == "X"
    # 3 of 4 successful votes for X → posterior 0.75
    assert verdict.final_differential.candidates[0].posterior == pytest.approx(0.75)
    # Confidence is votes/n_votes_REQUESTED (penalises failed calls)
    assert verdict.confidence == pytest.approx(3 / 5)
    assert stats.n_votes_requested == 5
    assert stats.n_votes_successful == 4
    assert stats.n_votes_failed == 1
    assert verdict.is_error is False


@pytest.mark.asyncio
async def test_all_calls_fail_returns_is_error_verdict():
    """5/5 calls raise → verdict is_error=True, empty differential."""
    llm = _mock_llm_with_returns([RuntimeError("fail")] * 5)
    verdict, stats = await run_ensemble(
        _CASE, model="anthropic/claude-haiku-4-5", n_votes=5, llm=llm
    )
    assert verdict.is_error is True
    assert verdict.termination_reason == "error"
    assert verdict.final_differential.candidates == []
    assert stats.n_votes_successful == 0
    assert stats.n_votes_failed == 5


@pytest.mark.asyncio
async def test_verdict_round_trips_through_score_run(tmp_path: pathlib.Path):
    """Ensemble verdict files must be FinalVerdict-compatible so scorer
    works without ensemble-aware branches."""
    llm = _mock_llm_with_returns([_diff_json("Diabetes")] * 5)
    verdict, _ = await run_ensemble(
        _CASE, model="anthropic/claude-haiku-4-5", n_votes=5, llm=llm
    )
    p = tmp_path / "case_ens_test.json"
    p.write_text(verdict.model_dump_json())
    reloaded = FinalVerdict.model_validate_json(p.read_text())
    assert isinstance(reloaded.final_differential, Differential)
    assert reloaded.final_differential.candidates[0].name == "Diabetes"
    assert reloaded.case_id == "ens_test"


@pytest.mark.asyncio
async def test_total_cost_sums_across_calls():
    llm = _mock_llm_with_returns([_diff_json("A")] * 5)
    verdict, _stats = await run_ensemble(
        _CASE, model="anthropic/claude-haiku-4-5", n_votes=5, llm=llm
    )
    assert verdict.total_cost_usd == pytest.approx(0.005)  # 5 x $0.001
    assert verdict.total_tokens == 5 * 42
    assert verdict.iterations_used == 1


def test_ensemble_stats_is_serialisable():
    """Stats must round-trip JSON so the manifest can persist them."""
    stats = EnsembleStats(
        n_votes_requested=5,
        n_votes_successful=4,
        n_votes_failed=1,
        vote_distribution={"a": 3, "b": 1},
        top_vote_count=3,
    )
    s = stats.model_dump_json()
    assert "n_votes_requested" in s
    back = EnsembleStats.model_validate_json(s)
    assert back == stats
