"""Tests for Panel.diagnose() and Panel.diagnose_stream().

Phase 5 multi-iter consensus loop. The existing single-agent fixture is
preserved against the `baseline_single_call` PanelConfig (hypothesis only,
max_iterations=1). The new multi-iter tests at the bottom of the file
exercise the full five-agent loop against `dev_cheap`.

Behavioral decisions pinned in this file:
- consensus threshold: top posterior > cfg.consensus_threshold → "consensus"
- single-iter path with posterior ≤ threshold → "max_iterations"
- error path: Panel.diagnose() must NOT bubble; returns FinalVerdict with
  termination_reason="error", is_error=True, and an empty Differential
- error path streaming: exactly one "error" event followed by one verdict
  event (so the SSE consumer never hangs waiting for a verdict that won't come)
- agent_start data: {"agent": <name>, "iteration": <int>}
- agent_complete payload key per agent:
    hypothesis → "differential"
    test_chooser → "next_test"
    challenger/stewardship/checklist → "structured_output"
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from quorum.llm.client import LLMClient, LLMResponse
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    CaseInput,
    DiagnosisCandidate,
    Differential,
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


def _baseline_config() -> PanelConfig:
    return next(
        c for c in PanelConfig.list_available() if c.name == "baseline_single_call"
    )


def _dev_cheap_config() -> PanelConfig:
    return next(c for c in PanelConfig.list_available() if c.name == "dev_cheap")


def _make_llm_stub() -> LLMClient:
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "x"
    return llm


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
    """Baseline single-call panel — only hypothesis is configured.

    The baseline_single_call config has max_iterations=1 and consensus_threshold=0.0
    so a single hypothesis call always terminates (posterior > 0.0 → consensus,
    or via the for-else max_iterations fallback for empty differentials).
    """
    llm = _make_llm_stub()
    panel = Panel(llm, _baseline_config())
    panel.hypothesis.deliberate = AsyncMock(return_value=make_canned_message())
    return panel


# ---------------------------------------------------------------------------
# diagnose() — non-streaming (baseline_single_call config)
# ---------------------------------------------------------------------------


async def test_diagnose_happy_path_returns_final_verdict(panel_with_mock_hypothesis):
    """Happy path: Panel.diagnose() returns a structurally correct FinalVerdict."""
    panel = panel_with_mock_hypothesis
    canned_hyp = make_canned_message()
    case = CaseInput(presentation="Patient presents with fever and rash.")

    verdict = await panel.diagnose(case)

    assert isinstance(verdict, FinalVerdict)
    assert verdict.final_differential == canned_hyp.structured_output
    assert verdict.confidence == canned_hyp.structured_output.candidates[0].posterior
    assert verdict.iterations_used == 1
    assert verdict.total_tokens == canned_hyp.tokens_used
    assert verdict.total_cost_usd == canned_hyp.cost_usd
    assert len(verdict.transcript) == 1
    assert verdict.transcript[0].role == AgentRole.HYPOTHESIS
    assert verdict.termination_reason in {"consensus", "max_iterations"}
    assert verdict.is_error is False
    assert verdict.schema_version == 1


async def test_diagnose_consensus_when_top_posterior_above_threshold(
    panel_with_mock_hypothesis,
):
    """top posterior=0.75 > baseline threshold (0.0) → 'consensus'."""
    panel = panel_with_mock_hypothesis
    panel.hypothesis.deliberate.return_value = make_canned_message(posterior_top=0.75)
    case = CaseInput(presentation="High-confidence presentation.")

    verdict = await panel.diagnose(case)

    assert verdict.termination_reason == "consensus"


async def test_diagnose_max_iterations_when_top_posterior_at_or_below_threshold():
    """top posterior 0.4, threshold 0.6, max_iter=1 → 'max_iterations'."""
    # Build a custom config with threshold above the posterior we're sending in.
    base = _baseline_config()
    cfg = base.model_copy(update={"consensus_threshold": 0.6, "max_iterations": 1})
    panel = Panel(_make_llm_stub(), cfg)
    panel.hypothesis.deliberate = AsyncMock(
        return_value=make_canned_message(posterior_top=0.40)
    )
    case = CaseInput(presentation="Ambiguous presentation.")

    verdict = await panel.diagnose(case)

    assert verdict.termination_reason == "max_iterations"


async def test_diagnose_hypothesis_error_returns_error_verdict(
    panel_with_mock_hypothesis,
):
    """Hypothesis raises → Panel returns FinalVerdict(termination_reason='error',
    is_error=True). Panel must NOT bubble.
    """
    panel = panel_with_mock_hypothesis
    panel.hypothesis.deliberate.side_effect = RuntimeError("upstream")
    case = CaseInput(presentation="Won't matter — agent will fail.")

    verdict = await panel.diagnose(case)

    assert isinstance(verdict, FinalVerdict)
    assert verdict.termination_reason == "error"
    assert verdict.is_error is True
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


async def test_diagnose_confidence_uses_max_posterior_not_first(
    panel_with_mock_hypothesis,
):
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
# diagnose_stream() — SSE generator (baseline_single_call config)
# ---------------------------------------------------------------------------


async def _collect_stream(panel: Panel, case: CaseInput) -> list[StreamEvent]:
    """Drain the async generator into a list."""
    events = []
    async for event in panel.diagnose_stream(case):
        events.append(event)
    return events


async def test_stream_event_order_on_happy_path(panel_with_mock_hypothesis):
    """Baseline happy path: agent_start(hyp), agent_complete(hyp),
    round_complete, verdict."""
    panel = panel_with_mock_hypothesis
    case = CaseInput(presentation="Streaming happy path.")

    events = await _collect_stream(panel, case)

    assert [e.event for e in events] == [
        "agent_start",
        "agent_complete",
        "round_complete",
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
    """Hypothesis raises → stream emits exactly one error event then one error
    verdict event, in that order. Verdict is terminal."""
    panel = panel_with_mock_hypothesis
    panel.hypothesis.deliberate.side_effect = RuntimeError("provider exploded")
    case = CaseInput(presentation="Will fail.")

    events = await _collect_stream(panel, case)

    error_events = [e for e in events if e.event == "error"]
    assert len(error_events) == 1

    code = error_events[0].data["code"]
    assert code in _A3_ERROR_CODES

    # error event must be immediately followed by exactly one verdict event
    error_idx = events.index(error_events[0])
    assert events[error_idx + 1].event == "verdict"
    assert error_idx + 1 == len(events) - 1
    # error verdict carries is_error=True
    err_verdict = FinalVerdict.model_validate(events[-1].data)
    assert err_verdict.is_error is True
    assert err_verdict.termination_reason == "error"


# ---------------------------------------------------------------------------
# Multi-iter consensus loop (dev_cheap config — all 5 agents)
# ---------------------------------------------------------------------------


def _hyp_json(top_posterior: float) -> str:
    """Differential JSON with the top candidate at the given posterior."""
    remaining = (1.0 - top_posterior) / 2
    return json.dumps({
        "candidates": [
            {"name": "Top", "posterior": top_posterior, "rationale": "r",
             "supporting_findings": [], "against_findings": [], "citations": []},
            {"name": "Second", "posterior": remaining, "rationale": "r",
             "supporting_findings": [], "against_findings": [], "citations": []},
            {"name": "Third", "posterior": remaining, "rationale": "r",
             "supporting_findings": [], "against_findings": [], "citations": []},
        ],
        "iteration": 0,
    })


_TC_JSON = json.dumps({
    "name": "Test X", "rationale": "discriminates",
    "estimated_cost_usd": 100.0, "information_gain_estimate": 0.5,
    "discriminates_between": ["Top", "Second"],
})
_CHAL_JSON = json.dumps({
    "against_top_candidate": ["finding"],
    "alternative_to_consider": "none",
    "confidence_in_challenge": 0.3,
})
_STEW_JSON = json.dumps({
    "accept_test": True, "cost_concern": None, "cheaper_alternative": None,
})
_CHK_CONTINUE = json.dumps({
    "consistent": True, "flags": [], "recommend_continue": True,
})
_CHK_STOP_CLEAN = json.dumps({
    "consistent": True, "flags": [], "recommend_continue": False,
})


def _mock_llm_for_n_iterations(responses_per_iter: list[list[str]]) -> LLMClient:
    """Build an LLMClient mock that serves responses in panel-call order.

    Each iteration of the panel issues 5 LLM calls (one per agent).
    asyncio.gather treats challenger+stewardship as 2 separate mock calls,
    so the per-iter list is exactly:
        [hypothesis, test_chooser, challenger, stewardship, checklist]
    """
    llm = _make_llm_stub()
    flat: list[LLMResponse] = []
    for batch in responses_per_iter:
        for content in batch:
            flat.append(
                LLMResponse(content=content, tokens_used=100, cost_usd=0.001, model="x")
            )
    llm.complete = AsyncMock(side_effect=flat)
    return llm


async def test_panel_multi_iter_consensus_terminates_first_round():
    """Top posterior > 0.6 in iteration 1 + checklist agrees → 'consensus'."""
    cfg = _dev_cheap_config()
    llm = _mock_llm_for_n_iterations([
        [_hyp_json(0.9), _TC_JSON, _CHAL_JSON, _STEW_JSON, _CHK_CONTINUE],
    ])
    panel = Panel(llm, cfg)
    verdict = await panel.diagnose(CaseInput(presentation="x"))
    assert verdict.termination_reason == "consensus"
    assert verdict.iterations_used == 1


async def test_panel_multi_iter_max_iterations_runs_three_rounds():
    """No consensus across 3 rounds → 'max_iterations'."""
    cfg = _dev_cheap_config()  # max_iterations=3
    llm = _mock_llm_for_n_iterations([
        [_hyp_json(0.3), _TC_JSON, _CHAL_JSON, _STEW_JSON, _CHK_CONTINUE],
        [_hyp_json(0.4), _TC_JSON, _CHAL_JSON, _STEW_JSON, _CHK_CONTINUE],
        [_hyp_json(0.5), _TC_JSON, _CHAL_JSON, _STEW_JSON, _CHK_CONTINUE],
    ])
    panel = Panel(llm, cfg)
    verdict = await panel.diagnose(CaseInput(presentation="x"))
    assert verdict.termination_reason == "max_iterations"
    assert verdict.iterations_used == 3


async def test_panel_multi_iter_checklist_stop_clean():
    """Checklist recommends stop with consistent=True → 'checklist_stop'."""
    cfg = _dev_cheap_config()
    llm = _mock_llm_for_n_iterations([
        [_hyp_json(0.3), _TC_JSON, _CHAL_JSON, _STEW_JSON, _CHK_STOP_CLEAN],
    ])
    panel = Panel(llm, cfg)
    verdict = await panel.diagnose(CaseInput(presentation="x"))
    assert verdict.termination_reason == "checklist_stop"
    assert verdict.iterations_used == 1


async def test_panel_emits_test_chooser_after_hypothesis(base_case):
    """Dev-cheap config: every iter emits hyp, tc, chal||stew, chk, round_complete.

    With consensus reached in iter 1, the expected event sequence is:
      agent_start(hyp), agent_complete(hyp),
      agent_start(tc),  agent_complete(tc),
      agent_start(chal), agent_start(stew),   # both spinning together
      agent_complete(chal), agent_complete(stew),
      agent_start(chk), agent_complete(chk),
      round_complete, verdict
    """
    cfg = _dev_cheap_config()
    llm = _mock_llm_for_n_iterations([
        [_hyp_json(0.9), _TC_JSON, _CHAL_JSON, _STEW_JSON, _CHK_CONTINUE],
    ])
    panel = Panel(llm, cfg)
    events = [ev async for ev in panel.diagnose_stream(base_case)]
    event_names = [(e.event, e.data.get("agent") if isinstance(e.data, dict) else None)
                   for e in events]
    assert event_names == [
        ("agent_start", "hypothesis"),
        ("agent_complete", "hypothesis"),
        ("agent_start", "test_chooser"),
        ("agent_complete", "test_chooser"),
        ("agent_start", "challenger"),
        ("agent_start", "stewardship"),
        ("agent_complete", "challenger"),
        ("agent_complete", "stewardship"),
        ("agent_start", "checklist"),
        ("agent_complete", "checklist"),
        ("round_complete", None),
        ("verdict", None),
    ]


async def test_panel_multi_iter_emits_round_complete_per_iteration():
    """Three iterations → three round_complete events."""
    cfg = _dev_cheap_config()
    llm = _mock_llm_for_n_iterations([
        [_hyp_json(0.3), _TC_JSON, _CHAL_JSON, _STEW_JSON, _CHK_CONTINUE],
        [_hyp_json(0.3), _TC_JSON, _CHAL_JSON, _STEW_JSON, _CHK_CONTINUE],
        [_hyp_json(0.3), _TC_JSON, _CHAL_JSON, _STEW_JSON, _CHK_CONTINUE],
    ])
    panel = Panel(llm, cfg)
    events = [ev async for ev in panel.diagnose_stream(CaseInput(presentation="x"))]
    round_events = [e for e in events if e.event == "round_complete"]
    assert [e.data["iteration"] for e in round_events] == [0, 1, 2]


@pytest.fixture
def base_case() -> CaseInput:
    return CaseInput(presentation="placeholder presentation for panel stream test")
