"""Integration tests for Panel.run_sequential (Phase 5 Task 5.3).

The plan's original Task 5.3 sketch was rewritten per the Task 5.0
contract audit. Key adjustments:
- Panel(llm=..., config=...) — kwarg is `llm`, NOT `llm_client`.
- Every agent's deliberate is async — use AsyncMock for stubs.
- Hypothesis returns AgentMessage with Differential structured_output;
  posterior is read via `.as_posterior_dict()`.
- TestChooser returns AgentMessage with NextTest; the query is
  `msg.structured_output.name`.
- Challenger/Stewardship/Checklist return AgentMessage with dict
  structured_output keyed per AGENT_CONTRACTS.md.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from quorum.audit.writer import AuditWriter
from quorum.eval.eval_case import EvalCase, Finding
from quorum.gatekeeper.gatekeeper import Gatekeeper
from quorum.llm.client import LLMClient
from quorum.orchestrator.panel import Panel, SequentialResult
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    DiagnosisCandidate,
    Differential,
    NextTest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm_stub() -> LLMClient:
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "x"
    return llm


def _dev_cheap_config() -> PanelConfig:
    return next(c for c in PanelConfig.list_available() if c.name == "dev_cheap")


def _hyp_msg(posteriors: dict[str, float], iteration: int = 0) -> AgentMessage:
    candidates = [
        DiagnosisCandidate(name=name, posterior=p, rationale=f"reason for {name}")
        for name, p in posteriors.items()
    ]
    diff = Differential(candidates=candidates, iteration=iteration)
    return AgentMessage(
        role=AgentRole.HYPOTHESIS,
        iteration=iteration,
        content="hypothesis",
        structured_output=diff,
        tokens_used=300,
        cost_usd=0.012,
    )


def _tc_msg(query: str, iteration: int = 0) -> AgentMessage:
    nt = NextTest(
        name=query,
        rationale=f"discriminates against alternatives ({query})",
        estimated_cost_usd=50.0,
    )
    return AgentMessage(
        role=AgentRole.TEST_CHOOSER,
        iteration=iteration,
        content=f"Recommend: {query}",
        structured_output=nt,
        tokens_used=80,
        cost_usd=0.003,
    )


def _challenger_msg(alternative: str = "none", confidence: float = 0.1) -> AgentMessage:
    return AgentMessage(
        role=AgentRole.CHALLENGER,
        iteration=0,
        content=f"Challenge: {alternative}",
        structured_output={
            "against_top_candidate": [],
            "alternative_to_consider": alternative,
            "confidence_in_challenge": confidence,
        },
        tokens_used=80,
        cost_usd=0.003,
    )


def _stewardship_msg(accept: bool = True) -> AgentMessage:
    return AgentMessage(
        role=AgentRole.STEWARDSHIP,
        iteration=0,
        content=f"Steward: accept={accept}",
        structured_output={
            "accept_test": accept,
            "cost_concern": None,
            "cheaper_alternative": None,
        },
        tokens_used=60,
        cost_usd=0.002,
    )


def _checklist_msg(consistent: bool = True, flags: list[str] | None = None, recommend_continue: bool = True) -> AgentMessage:
    return AgentMessage(
        role=AgentRole.CHECKLIST,
        iteration=0,
        content="checklist",
        structured_output={
            "consistent": consistent,
            "flags": flags or [],
            "recommend_continue": recommend_continue,
        },
        tokens_used=60,
        cost_usd=0.002,
    )


def _async_match_sequence(indices: list[int]):
    """Return an async stub that yields the given indices in order."""
    state = {"i": 0}

    async def _match(question, findings):
        idx = indices[min(state["i"], len(indices) - 1)]
        state["i"] += 1
        return idx

    return _match


@pytest.fixture
def toy_eval_case() -> EvalCase:
    return EvalCase(
        case_id="toy-seq",
        corpus="nejm",
        source="test",
        initial_presentation="50yo with fatigue and joint pain.",
        available_findings=[
            Finding(category="serology", label="ANA", content="ANA 1:640 homogeneous"),
            Finding(category="labs", label="anti-Smith", content="positive"),
            Finding(category="labs", label="complement_c3_c4", content="low C3, low C4"),
        ],
        ground_truth_diagnosis="systemic lupus erythematosus",
        acceptable_partial_credit=["SLE"],
    )


def _build_panel():
    panel = Panel(_make_llm_stub(), _dev_cheap_config())
    return panel


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_run_sequential_commits_when_threshold_exceeded(toy_eval_case, tmp_path, monkeypatch):
    """Hypothesis crosses 0.7 by turn 3; commit fires after SafetyChecker passes."""
    panel = _build_panel()
    # Posterior climbs over turns.
    hypothesis_outputs = [
        _hyp_msg({"SLE": 0.40, "MCTD": 0.30, "RA": 0.30}, iteration=0),
        _hyp_msg({"SLE": 0.55, "MCTD": 0.25, "RA": 0.20}, iteration=1),
        _hyp_msg({"SLE": 0.85, "MCTD": 0.10, "RA": 0.05}, iteration=2),
    ]
    panel.hypothesis.deliberate = AsyncMock(side_effect=hypothesis_outputs)
    panel.test_chooser.deliberate = AsyncMock(
        side_effect=[_tc_msg("ANA"), _tc_msg("anti-Smith"), _tc_msg("complement")]
    )
    panel.challenger.deliberate = AsyncMock(return_value=_challenger_msg(alternative="none"))
    panel.stewardship.deliberate = AsyncMock(return_value=_stewardship_msg(accept=True))
    panel.checklist.deliberate = AsyncMock(return_value=_checklist_msg(recommend_continue=True))

    gk = Gatekeeper(toy_eval_case)
    monkeypatch.setattr(gk, "_llm_match", _async_match_sequence([0, 1, 2]))
    writer = AuditWriter(root=tmp_path, run_id="t1", case_id=toy_eval_case.case_id, model="stub")

    result = await panel.run_sequential(toy_eval_case, gk, writer, max_turns=10, commit_threshold=0.7)

    assert isinstance(result, SequentialResult)
    assert result.committed_diagnosis == "SLE"
    assert result.final_posterior["SLE"] == pytest.approx(0.85)
    assert result.n_turns == 3
    assert result.forced is False
    assert gk.turn_index == 3
    # Audit captured per-turn events
    assert len(writer.audit.turns) > 5  # at least 5 agents x 3 turns + gk + safety
    assert writer.audit.final_committed_diagnosis == "SLE"


async def test_run_sequential_safety_blocks_premature_commit(toy_eval_case, tmp_path, monkeypatch):
    """High posterior + too few findings should NOT commit until safety clears."""
    panel = _build_panel()
    # Posterior crosses threshold immediately on turn 1, but only 1 finding queried.
    # SafetyChecker requires >=3 findings. The loop must continue until 3 findings.
    posteriors_per_turn = [
        _hyp_msg({"SLE": 0.85, "MCTD": 0.10, "RA": 0.05}, iteration=i) for i in range(5)
    ]
    panel.hypothesis.deliberate = AsyncMock(side_effect=posteriors_per_turn)
    panel.test_chooser.deliberate = AsyncMock(
        side_effect=[_tc_msg(f"q{i}") for i in range(5)]
    )
    panel.challenger.deliberate = AsyncMock(return_value=_challenger_msg())
    panel.stewardship.deliberate = AsyncMock(return_value=_stewardship_msg(accept=True))
    panel.checklist.deliberate = AsyncMock(return_value=_checklist_msg())

    gk = Gatekeeper(toy_eval_case)
    monkeypatch.setattr(gk, "_llm_match", _async_match_sequence([0, 1, 2, -1, -1]))
    writer = AuditWriter(root=tmp_path, run_id="t2", case_id=toy_eval_case.case_id, model="stub")

    result = await panel.run_sequential(toy_eval_case, gk, writer, max_turns=10, commit_threshold=0.7)

    # The first 2 turns can't commit (n_findings < 3); commit only at turn 3.
    assert result.n_turns >= 3
    # Audit should record at least 2 safety_check events with blocked=True before the clean commit.
    safety_checks = [t for t in writer.audit.turns if t.message_role == "safety_check"]
    assert len(safety_checks) >= 1
    blocked_checks = [t for t in safety_checks if t.extra.get("blocked")]
    assert len(blocked_checks) >= 1


async def test_run_sequential_records_audit_event_per_agent(toy_eval_case, tmp_path, monkeypatch):
    panel = _build_panel()
    panel.hypothesis.deliberate = AsyncMock(
        return_value=_hyp_msg({"SLE": 0.9, "MCTD": 0.05, "RA": 0.05})
    )
    panel.test_chooser.deliberate = AsyncMock(return_value=_tc_msg("ANA"))
    panel.challenger.deliberate = AsyncMock(return_value=_challenger_msg())
    panel.stewardship.deliberate = AsyncMock(return_value=_stewardship_msg(accept=True))
    panel.checklist.deliberate = AsyncMock(return_value=_checklist_msg())

    gk = Gatekeeper(toy_eval_case)
    monkeypatch.setattr(gk, "_llm_match", _async_match_sequence([0, 1, 2]))
    writer = AuditWriter(root=tmp_path, run_id="t3", case_id=toy_eval_case.case_id, model="stub")

    await panel.run_sequential(toy_eval_case, gk, writer, max_turns=10, commit_threshold=0.7)

    agents_seen = {t.agent for t in writer.audit.turns}
    assert {"hypothesis", "test_chooser", "challenger", "stewardship", "checklist", "gatekeeper", "safety_checker"} <= agents_seen


async def test_run_sequential_max_turns_forced_commit(toy_eval_case, tmp_path, monkeypatch):
    """If max_turns is reached without commit, force a commit on current top."""
    panel = _build_panel()
    # Posterior never crosses threshold.
    low_post = _hyp_msg({"SLE": 0.4, "MCTD": 0.3, "RA": 0.3})
    panel.hypothesis.deliberate = AsyncMock(return_value=low_post)
    panel.test_chooser.deliberate = AsyncMock(return_value=_tc_msg("ANA"))
    panel.challenger.deliberate = AsyncMock(return_value=_challenger_msg())
    panel.stewardship.deliberate = AsyncMock(return_value=_stewardship_msg(accept=True))
    panel.checklist.deliberate = AsyncMock(return_value=_checklist_msg())

    gk = Gatekeeper(toy_eval_case)
    monkeypatch.setattr(gk, "_llm_match", _async_match_sequence([0, 1, 2] + [-1] * 10))
    writer = AuditWriter(root=tmp_path, run_id="t4", case_id=toy_eval_case.case_id, model="stub")

    result = await panel.run_sequential(toy_eval_case, gk, writer, max_turns=3, commit_threshold=0.7)
    assert result.n_turns == 3
    assert result.committed_diagnosis == "SLE"  # top of low posterior
    assert result.forced is True


async def test_run_sequential_stops_when_stewardship_rejects_and_safety_clean(toy_eval_case, tmp_path, monkeypatch):
    """If Stewardship returns accept_test=False (stop) AND safety clean → commit."""
    panel = _build_panel()
    # Mid posterior (below threshold) but stewardship votes stop.
    panel.hypothesis.deliberate = AsyncMock(
        return_value=_hyp_msg({"SLE": 0.65, "MCTD": 0.20, "RA": 0.15})
    )
    panel.test_chooser.deliberate = AsyncMock(return_value=_tc_msg("ANA"))
    panel.challenger.deliberate = AsyncMock(return_value=_challenger_msg())
    # Accept first 2 tests so we get past the min-findings rule (3), then vote stop on turn 3.
    panel.stewardship.deliberate = AsyncMock(
        side_effect=[_stewardship_msg(accept=True)] * 2 + [_stewardship_msg(accept=False)]
    )
    panel.checklist.deliberate = AsyncMock(return_value=_checklist_msg())

    gk = Gatekeeper(toy_eval_case)
    monkeypatch.setattr(gk, "_llm_match", _async_match_sequence([0, 1, 2]))
    writer = AuditWriter(root=tmp_path, run_id="t5", case_id=toy_eval_case.case_id, model="stub")

    result = await panel.run_sequential(toy_eval_case, gk, writer, max_turns=10, commit_threshold=0.99)
    # Posterior never crosses 0.99 but stewardship vetoes after turn 3 → commit on turn 3.
    assert result.n_turns == 3
    assert result.committed_diagnosis == "SLE"
