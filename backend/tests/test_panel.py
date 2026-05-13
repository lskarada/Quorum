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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def panel_with_mock_hypothesis(monkeypatch):
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "claude-opus-4-7"
    panel = Panel(llm)
    panel.hypothesis.deliberate = AsyncMock(return_value=make_canned_message())
    return panel


# ---------------------------------------------------------------------------
# diagnose() — non-streaming
# ---------------------------------------------------------------------------


async def test_diagnose_happy_path_returns_final_verdict(panel_with_mock_hypothesis):
    """Happy path: Panel.diagnose() returns a structurally correct FinalVerdict."""
    panel = panel_with_mock_hypothesis
    canned = make_canned_message()
    case = CaseInput(presentation="Patient presents with fever and rash.")

    verdict = await panel.diagnose(case)

    assert isinstance(verdict, FinalVerdict)
    assert verdict.final_differential == canned.structured_output
    assert verdict.confidence == canned.structured_output.candidates[0].posterior
    assert verdict.iterations_used == 1
    assert verdict.total_tokens == canned.tokens_used
    assert verdict.total_cost_usd == canned.cost_usd
    assert len(verdict.transcript) == 1
    assert verdict.transcript[0].role == AgentRole.HYPOTHESIS
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
    """Happy path: event sequence must be agent_start → agent_complete → verdict."""
    panel = panel_with_mock_hypothesis
    case = CaseInput(presentation="Streaming happy path.")

    events = await _collect_stream(panel, case)

    assert len(events) == 3
    assert [e.event for e in events] == ["agent_start", "agent_complete", "verdict"]


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
