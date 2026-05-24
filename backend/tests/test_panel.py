"""Failing tests for Panel.diagnose() and Panel.diagnose_stream().

These are Phase 1 RED tests. Every test here should fail with
NotImplementedError until the implementation lands in Phase 3.

Behavioral decisions pinned during writing:
- consensus threshold: top posterior > 0.6 → termination_reason="consensus"
- single-iter path with posterior ≤ 0.6 → termination_reason="max_iterations"
  (honest name: 1 iteration = max_iterations for the vertical slice)
- error path: Panel.diagnose() must NOT bubble; returns FinalVerdict with
  termination_reason="error" and a sentinel Differential (empty candidates)
- error path streaming: exactly one "error" event then generator closes;
  data["code"] must be from the A3 closed set
- agent_start data: {"agent": "hypothesis", "iteration": 0}
- agent_complete data keys: "agent", "differential", "tokens_used",
  "cost_usd", "latency_ms"
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from quorum.llm.client import LLMClient
from quorum.orchestrator.agents.hypothesis import HypothesisAgent
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    CaseInput,
    Differential,
    DiagnosisCandidate,
    FinalVerdict,
    NextTest,
    StreamEvent,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_A3_ERROR_CODES = frozenset(
    {"provider_429", "provider_timeout", "parse_failure", "schema_violation", "internal"}
)


def make_canned_message(posterior_top: float = 0.75) -> AgentMessage:
    diff = Differential(
        candidates=[
            DiagnosisCandidate(name="Disease A", posterior=posterior_top, rationale="r1"),
            DiagnosisCandidate(name="Disease B", posterior=0.20, rationale="r2"),
            DiagnosisCandidate(
                name="Disease C",
                posterior=round(1 - posterior_top - 0.20, 4),
                rationale="r3",
            ),
        ],
        iteration=0,
    )
    return AgentMessage(
        role=AgentRole.HYPOTHESIS,
        iteration=0,
        content="differential proposed",
        structured_output=diff,
        tokens_used=300,
        cost_usd=0.015,
    )


def make_canned_test_chooser_message() -> AgentMessage:
    nt = NextTest(
        name="Test X",
        rationale="discriminates A from B",
        estimated_cost_usd=100.0,
        information_gain_estimate=0.5,
        discriminates_between=["Disease A", "Disease B"],
    )
    return AgentMessage(
        role=AgentRole.TEST_CHOOSER,
        iteration=0,
        content=f"Recommend: {nt.name} — {nt.rationale}",
        structured_output=nt,
        tokens_used=80,
        cost_usd=0.004,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def panel_with_mock_hypothesis(monkeypatch):
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "claude-opus-4-7"
    panel = Panel(llm)
    panel.hypothesis.deliberate = AsyncMock(return_value=make_canned_message())
    panel.test_chooser.deliberate = AsyncMock(
        return_value=make_canned_test_chooser_message()
    )
    return panel


# ---------------------------------------------------------------------------
# diagnose() — non-streaming
# ---------------------------------------------------------------------------


async def test_diagnose_happy_path_returns_final_verdict(panel_with_mock_hypothesis):
    """Happy path: Panel.diagnose() returns a structurally correct FinalVerdict."""
    panel = panel_with_mock_hypothesis
    canned_hyp = make_canned_message()
    canned_tc = make_canned_test_chooser_message()
    case = CaseInput(presentation="Patient presents with fever and rash.")

    verdict = await panel.diagnose(case)

    assert isinstance(verdict, FinalVerdict)
    assert verdict.final_differential == canned_hyp.structured_output
    assert verdict.confidence == canned_hyp.structured_output.candidates[0].posterior
    assert verdict.iterations_used == 1
    assert verdict.total_tokens == canned_hyp.tokens_used + canned_tc.tokens_used
    assert verdict.total_cost_usd == canned_hyp.cost_usd + canned_tc.cost_usd
    assert len(verdict.transcript) == 2
    assert verdict.transcript[0].role == AgentRole.HYPOTHESIS
    assert verdict.transcript[1].role == AgentRole.TEST_CHOOSER
    assert verdict.termination_reason in {"consensus", "max_iterations"}


async def test_diagnose_consensus_when_top_posterior_above_threshold(panel_with_mock_hypothesis):
    """top posterior=0.75 → termination_reason='consensus'."""
    panel = panel_with_mock_hypothesis
    panel.hypothesis.deliberate.return_value = make_canned_message(posterior_top=0.75)
    case = CaseInput(presentation="High-confidence presentation.")

    verdict = await panel.diagnose(case)

    assert verdict.termination_reason == "consensus"


async def test_diagnose_max_iterations_when_top_posterior_at_or_below_threshold(
    panel_with_mock_hypothesis,
):
    """top posterior=0.4 → termination_reason='max_iterations' (no consensus reached)."""
    panel = panel_with_mock_hypothesis
    panel.hypothesis.deliberate.return_value = make_canned_message(posterior_top=0.40)
    case = CaseInput(presentation="Ambiguous presentation.")

    verdict = await panel.diagnose(case)

    assert verdict.termination_reason == "max_iterations"


async def test_diagnose_hypothesis_error_returns_error_verdict(panel_with_mock_hypothesis):
    """Hypothesis raises RuntimeError → Panel returns FinalVerdict(termination_reason='error').

    Panel must NOT bubble the exception. The final_differential should be an
    empty sentinel (no candidates) so callers can inspect the reason without
    special-casing None.
    """
    panel = panel_with_mock_hypothesis
    panel.hypothesis.deliberate.side_effect = RuntimeError("upstream")
    case = CaseInput(presentation="Won't matter — agent will fail.")

    verdict = await panel.diagnose(case)

    assert isinstance(verdict, FinalVerdict)
    assert verdict.termination_reason == "error"
    assert verdict.final_differential.candidates == []


async def test_diagnose_case_id_propagated(panel_with_mock_hypothesis):
    """case_id from CaseInput propagates through to the returned FinalVerdict."""
    panel = panel_with_mock_hypothesis
    case = CaseInput(case_id="case-123", presentation="Some presentation.")

    verdict = await panel.diagnose(case)

    assert verdict.case_id == "case-123"


async def test_diagnose_case_id_none_propagates_as_none(panel_with_mock_hypothesis):
    """No case_id supplied -> FinalVerdict.case_id is None (not coerced to empty)."""
    panel = panel_with_mock_hypothesis
    case = CaseInput(presentation="No case_id here.")

    verdict = await panel.diagnose(case)

    assert verdict.case_id is None


async def test_diagnose_confidence_uses_max_posterior_not_first(panel_with_mock_hypothesis):
    """If the LLM returns candidates in non-descending posterior order, confidence
    is still the max posterior (not candidates[0])."""
    panel = panel_with_mock_hypothesis
    unsorted = AgentMessage(
        role=AgentRole.HYPOTHESIS,
        iteration=0,
        content="unsorted",
        structured_output=Differential(
            candidates=[
                DiagnosisCandidate(name="Low", posterior=0.10, rationale="r"),
                DiagnosisCandidate(name="High", posterior=0.70, rationale="r"),
                DiagnosisCandidate(name="Mid", posterior=0.20, rationale="r"),
            ],
            iteration=0,
        ),
        tokens_used=10,
        cost_usd=0.001,
    )
    panel.hypothesis.deliberate.return_value = unsorted
    case = CaseInput(presentation="Out-of-order candidates.")

    verdict = await panel.diagnose(case)

    assert verdict.confidence == pytest.approx(0.70)
    assert verdict.termination_reason == "consensus"


# ---------------------------------------------------------------------------
# diagnose_stream() — SSE generator
# ---------------------------------------------------------------------------


async def _collect_stream(panel: Panel, case: CaseInput) -> list[StreamEvent]:
    """Drain the async generator into a list."""
    events = []
    async for event in panel.diagnose_stream(case):
        events.append(event)
    return events


async def test_stream_event_order_on_happy_path(panel_with_mock_hypothesis):
    """Happy path: hypothesis start/complete, test_chooser start/complete, verdict."""
    panel = panel_with_mock_hypothesis
    case = CaseInput(presentation="Streaming happy path.")

    events = await _collect_stream(panel, case)

    assert len(events) == 5
    assert [e.event for e in events] == [
        "agent_start",
        "agent_complete",
        "agent_start",
        "agent_complete",
        "verdict",
    ]


async def test_stream_agent_start_data(panel_with_mock_hypothesis):
    """First event is agent_start with agent='hypothesis' and iteration=0."""
    panel = panel_with_mock_hypothesis
    case = CaseInput(presentation="Checking agent_start payload.")

    events = await _collect_stream(panel, case)

    first = events[0]
    assert first.event == "agent_start"
    assert first.data["agent"] == "hypothesis"
    assert first.data["iteration"] == 0


async def test_stream_agent_complete_carries_differential(panel_with_mock_hypothesis):
    """Second event is agent_complete whose data.differential is a valid Differential."""
    panel = panel_with_mock_hypothesis
    case = CaseInput(presentation="Checking agent_complete payload.")

    events = await _collect_stream(panel, case)

    second = events[1]
    assert second.event == "agent_complete"
    assert second.data["agent"] == "hypothesis"
    # Must be parseable back into a Differential — proves the full schema round-trip.
    diff = Differential.model_validate(second.data["differential"])
    assert len(diff.candidates) > 0


async def test_stream_verdict_event_carries_final_verdict(panel_with_mock_hypothesis):
    """Last event is verdict whose data parses into a FinalVerdict."""
    panel = panel_with_mock_hypothesis
    case = CaseInput(presentation="Checking verdict payload.")

    events = await _collect_stream(panel, case)

    last = events[-1]
    assert last.event == "verdict"
    verdict = FinalVerdict.model_validate(last.data)
    assert isinstance(verdict, FinalVerdict)


async def test_stream_emits_error_event_on_hypothesis_failure(panel_with_mock_hypothesis):
    """Hypothesis raises → stream emits exactly one error event then closes cleanly."""
    panel = panel_with_mock_hypothesis
    panel.hypothesis.deliberate.side_effect = RuntimeError("provider exploded")
    case = CaseInput(presentation="Will fail.")

    events = await _collect_stream(panel, case)

    error_events = [e for e in events if e.event == "error"]
    assert len(error_events) == 1

    # code must be from the A3 closed set
    code = error_events[0].data["code"]
    assert code in _A3_ERROR_CODES

    # No events after the error event
    error_idx = events.index(error_events[0])
    assert error_idx == len(events) - 1


async def test_panel_stream_emits_test_chooser_after_hypothesis(base_case):
    """After hypothesis, panel runs TestChooser and yields its events before verdict."""
    # Mock LLMClient so both agents get canned responses
    import json

    from quorum.llm.client import LLMResponse

    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "x"
    # Hypothesis: a 3-candidate differential; TestChooser: a NextTest
    hyp_json = json.dumps({
        "candidates": [
            {"name": "Diagnosis A", "posterior": 0.5, "rationale": "r",
             "supporting_findings": [], "against_findings": [], "citations": []},
            {"name": "Diagnosis B", "posterior": 0.3, "rationale": "r",
             "supporting_findings": [], "against_findings": [], "citations": []},
            {"name": "Diagnosis C", "posterior": 0.2, "rationale": "r",
             "supporting_findings": [], "against_findings": [], "citations": []},
        ],
        "iteration": 0,
    })
    tc_json = json.dumps({
        "name": "Test X", "rationale": "discriminates",
        "estimated_cost_usd": 100.0, "information_gain_estimate": 0.5,
        "discriminates_between": ["Diagnosis A", "Diagnosis B"],
    })
    llm.complete = AsyncMock(side_effect=[
        LLMResponse(content=hyp_json, tokens_used=100, cost_usd=0.001, model="x"),
        LLMResponse(content=tc_json, tokens_used=80, cost_usd=0.0008, model="x"),
    ])
    panel = Panel(llm)
    events = [ev async for ev in panel.diagnose_stream(base_case)]
    event_names = [(e.event, e.data.get("agent")) for e in events]
    assert event_names == [
        ("agent_start", "hypothesis"),
        ("agent_complete", "hypothesis"),
        ("agent_start", "test_chooser"),
        ("agent_complete", "test_chooser"),
        ("verdict", None),
    ]


@pytest.fixture
def base_case() -> CaseInput:
    return CaseInput(presentation="placeholder presentation for panel stream test")
