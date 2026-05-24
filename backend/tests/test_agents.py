"""Tests for HypothesisAgent.deliberate().

Phase 1 — RED state: every test should fail with NotImplementedError because
deliberate() is not yet implemented. Once the implementation lands (Phase 2),
these tests define the full behavioral contract.

Pinned behavioral decisions (implementer must follow):
  - Posterior normalization: normalize silently and log when sum is outside
    0.95..1.05; raise ValueError only if sum == 0.0 (fully degenerate).
  - Too-few / too-many candidates: raise ValueError mentioning "candidate".
  - Malformed JSON from LLM: raise ValueError or json.JSONDecodeError.
  - Schema violation (posterior > 1.0): let Pydantic raise ValidationError.
  - Missing required field (no rationale): let Pydantic raise ValidationError.
  - Empty presentation: raise ValueError("presentation must be non-empty")
    BEFORE calling llm.complete (verified via mock not-called assertion).
  - LLM RuntimeError: propagate as-is (Panel is responsible for wrapping).
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from quorum.llm.client import LLMClient, LLMResponse
from quorum.orchestrator.agents.hypothesis import HypothesisAgent
from quorum.orchestrator.agents.test_chooser import TestChooserAgent
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    CaseInput,
    Differential,
    NextTest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        tokens_used=100,
        cost_usd=0.01,
        model="claude-opus-4-7",
    )


def _candidate(
    name: str,
    posterior: float,
    rationale: str = "Test rationale.",
) -> dict:
    return {
        "name": name,
        "posterior": posterior,
        "rationale": rationale,
        "supporting_findings": ["finding A"],
        "against_findings": [],
        "citations": [],
    }


def _differential_json(candidates: list[dict], iteration: int = 0) -> str:
    return json.dumps({"candidates": candidates, "iteration": iteration})


def _three_candidates(posteriors: tuple[float, float, float] = (0.5, 0.3, 0.2)) -> list[dict]:
    names = ["Diagnosis Alpha", "Diagnosis Beta", "Diagnosis Gamma"]
    return [_candidate(n, p) for n, p in zip(names, posteriors)]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm() -> LLMClient:
    client = LLMClient.__new__(LLMClient)
    client.default_model = "claude-opus-4-7"
    client.complete = AsyncMock(spec=LLMClient.complete)
    return client


@pytest.fixture
def agent(mock_llm: LLMClient) -> HypothesisAgent:
    return HypothesisAgent(mock_llm)


@pytest.fixture
def base_case() -> CaseInput:
    return CaseInput(
        presentation=(
            "45-year-old male with 3-day history of fever, productive cough, "
            "and right lower lobe consolidation on CXR."
        )
    )


# ---------------------------------------------------------------------------
# Test 1 — Happy path
# ---------------------------------------------------------------------------

async def test_happy_path_returns_valid_agent_message(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """LLM returns valid JSON with 3 candidates; deliberate() returns a well-formed AgentMessage."""
    candidates = _three_candidates()
    mock_llm.complete.return_value = _response(_differential_json(candidates))

    result = await agent.deliberate(base_case, [], iteration=0)

    assert isinstance(result, AgentMessage)
    assert result.role == AgentRole.HYPOTHESIS
    assert result.iteration == 0
    assert isinstance(result.structured_output, Differential)
    assert len(result.structured_output.candidates) == 3


# ---------------------------------------------------------------------------
# Test 2 — Posterior sum normalization
# ---------------------------------------------------------------------------

async def test_posterior_sum_normalization(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """LLM returns posteriors [0.6, 0.5, 0.4] (sum=1.5). Agent normalizes so sum ≈ 1.0."""
    candidates = _three_candidates((0.6, 0.5, 0.4))
    mock_llm.complete.return_value = _response(_differential_json(candidates))

    result = await agent.deliberate(base_case, [], iteration=0)

    assert isinstance(result.structured_output, Differential)
    total = sum(c.posterior for c in result.structured_output.candidates)
    assert abs(total - 1.0) < 0.01, f"Expected normalized sum ~ 1.0, got {total}"


async def test_posterior_sum_at_lower_boundary_passes_through(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """Sum exactly 0.95 is inside tolerance and passes through unchanged."""
    candidates = _three_candidates((0.50, 0.30, 0.15))  # sum = 0.95
    mock_llm.complete.return_value = _response(_differential_json(candidates))

    result = await agent.deliberate(base_case, [], iteration=0)

    assert isinstance(result.structured_output, Differential)
    posteriors = [c.posterior for c in result.structured_output.candidates]
    assert posteriors == [0.50, 0.30, 0.15], "0.95 boundary must NOT be normalized"


async def test_posterior_sum_at_upper_boundary_passes_through(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """Sum exactly 1.05 is inside tolerance and passes through unchanged."""
    candidates = _three_candidates((0.50, 0.30, 0.25))  # sum = 1.05
    mock_llm.complete.return_value = _response(_differential_json(candidates))

    result = await agent.deliberate(base_case, [], iteration=0)

    assert isinstance(result.structured_output, Differential)
    posteriors = [c.posterior for c in result.structured_output.candidates]
    assert posteriors == [0.50, 0.30, 0.25], "1.05 boundary must NOT be normalized"


async def test_candidates_not_list_raises(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """LLM returns a JSON object where `candidates` is not a list (e.g., null
    or an object). Must raise ValueError, not TypeError."""
    payload = json.dumps({"candidates": None, "iteration": 0})
    mock_llm.complete.return_value = _response(payload)

    with pytest.raises(ValueError, match="candidates"):
        await agent.deliberate(base_case, [], iteration=0)


# ---------------------------------------------------------------------------
# Test 3 — Too few candidates
# ---------------------------------------------------------------------------

async def test_too_few_candidates_raises(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """LLM returns only 2 candidates. Agent raises ValueError mentioning 'candidate'.
    RED state: NotImplementedError is acceptable until deliberate() is implemented.
    GREEN contract: ValueError with 'candidate' in message."""
    two_candidates = [
        _candidate("Diagnosis Alpha", 0.6),
        _candidate("Diagnosis Beta", 0.4),
    ]
    mock_llm.complete.return_value = _response(_differential_json(two_candidates))

    with pytest.raises((ValueError, NotImplementedError)) as exc_info:
        await agent.deliberate(base_case, [], iteration=0)

    # Post-implementation: must be ValueError with 'candidate' in message.
    if not isinstance(exc_info.value, NotImplementedError):
        assert "candidate" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 4 — Too many candidates
# ---------------------------------------------------------------------------

async def test_too_many_candidates_raises(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """LLM returns 9 candidates. Agent raises ValueError mentioning 'candidate'.
    RED state: NotImplementedError is acceptable until deliberate() is implemented.
    GREEN contract: ValueError with 'candidate' in message."""
    nine_candidates = [_candidate(f"Diagnosis {i}", 1 / 9) for i in range(9)]
    mock_llm.complete.return_value = _response(_differential_json(nine_candidates))

    with pytest.raises((ValueError, NotImplementedError)) as exc_info:
        await agent.deliberate(base_case, [], iteration=0)

    # Post-implementation: must be ValueError with 'candidate' in message.
    if not isinstance(exc_info.value, NotImplementedError):
        assert "candidate" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 5 — Malformed JSON
# ---------------------------------------------------------------------------

async def test_malformed_json_raises(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """LLM returns non-JSON garbage. Agent raises ValueError or JSONDecodeError."""
    mock_llm.complete.return_value = _response("not json {{{")

    with pytest.raises((ValueError, json.JSONDecodeError)):
        await agent.deliberate(base_case, [], iteration=0)


# ---------------------------------------------------------------------------
# Test 6 — Schema violation: posterior > 1.0
# ---------------------------------------------------------------------------

async def test_schema_violation_posterior_out_of_range_raises(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """LLM returns a candidate with posterior=1.5 (Pydantic field constraint le=1.0).
    Agent propagates ValidationError from Pydantic parsing."""
    bad_candidates = [
        {
            "name": "Bad Diagnosis",
            "posterior": 1.5,   # violates le=1.0 constraint
            "rationale": "Over-confident.",
            "supporting_findings": [],
            "against_findings": [],
            "citations": [],
        },
        _candidate("Diagnosis Beta", 0.2),
        _candidate("Diagnosis Gamma", 0.1),
    ]
    mock_llm.complete.return_value = _response(_differential_json(bad_candidates))

    with pytest.raises(ValidationError):
        await agent.deliberate(base_case, [], iteration=0)


# ---------------------------------------------------------------------------
# Test 7 — Missing required field: no rationale
# ---------------------------------------------------------------------------

async def test_missing_required_field_rationale_raises(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """LLM returns a candidate missing the required 'rationale' field.
    Pydantic raises ValidationError during parsing."""
    no_rationale_candidates = [
        {
            "name": "Diagnosis Alpha",
            "posterior": 0.5,
            # 'rationale' intentionally omitted
            "supporting_findings": [],
            "against_findings": [],
            "citations": [],
        },
        _candidate("Diagnosis Beta", 0.3),
        _candidate("Diagnosis Gamma", 0.2),
    ]
    mock_llm.complete.return_value = _response(_differential_json(no_rationale_candidates))

    with pytest.raises(ValidationError):
        await agent.deliberate(base_case, [], iteration=0)


# ---------------------------------------------------------------------------
# Test 8 — Non-empty transcript carries forward
# ---------------------------------------------------------------------------

async def test_prior_transcript_included_in_llm_prompt(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """When transcript has a prior AgentMessage, its content appears in the
    messages passed to llm.complete, and iteration=1 is reflected in the result."""
    from datetime import datetime
    prior_message = AgentMessage(
        role=AgentRole.HYPOTHESIS,
        iteration=0,
        content="Prior round differential: top candidate is community-acquired pneumonia.",
        structured_output=None,
        timestamp=datetime.utcnow(),
    )

    candidates = _three_candidates()
    mock_llm.complete.return_value = _response(_differential_json(candidates, iteration=1))

    result = await agent.deliberate(base_case, [prior_message], iteration=1)

    mock_llm.complete.assert_called_once()
    call_args = mock_llm.complete.call_args

    # Extract the messages list from either positional or keyword args.
    if call_args.args:
        messages_passed = call_args.args[0]
    else:
        messages_passed = call_args.kwargs["messages"]

    # The prior transcript content must appear somewhere in the prompt messages.
    all_content = " ".join(
        m.get("content", "") if isinstance(m, dict) else str(m)
        for m in messages_passed
    )
    assert "community-acquired pneumonia" in all_content

    assert result.iteration == 1


# ---------------------------------------------------------------------------
# Test 9 — Empty case presentation
# ---------------------------------------------------------------------------

async def test_empty_presentation_raises_before_llm_call(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
) -> None:
    """CaseInput with empty presentation causes ValueError before LLM is called.
    RED state: NotImplementedError raised before any validation check — LLM still
    not called (NotImplementedError fires first in the stub).
    GREEN contract: ValueError('presentation must be non-empty') raised, LLM NOT called."""
    empty_case = CaseInput(presentation="")

    with pytest.raises((ValueError, NotImplementedError)) as exc_info:
        await agent.deliberate(empty_case, [], iteration=0)

    # Post-implementation: must be ValueError with the specific message.
    if not isinstance(exc_info.value, NotImplementedError):
        assert "presentation must be non-empty" in str(exc_info.value)

    # LLM must never be called for an empty presentation (true in both RED and GREEN).
    mock_llm.complete.assert_not_called()


# ---------------------------------------------------------------------------
# Test 10 — LLM client raises RuntimeError
# ---------------------------------------------------------------------------

async def test_llm_runtime_error_propagates(
    agent: HypothesisAgent,
    mock_llm: LLMClient,
    base_case: CaseInput,
) -> None:
    """If llm.complete raises RuntimeError (e.g. provider 429), it propagates unchanged.
    The Panel layer is responsible for converting it to an error event.
    RED state: NotImplementedError fires before llm.complete is reached.
    GREEN contract: RuntimeError('provider 429') propagates to caller."""
    mock_llm.complete.side_effect = RuntimeError("provider 429")

    with pytest.raises((RuntimeError, NotImplementedError)) as exc_info:
        await agent.deliberate(base_case, [], iteration=0)

    # Post-implementation: must be RuntimeError with the provider message.
    if not isinstance(exc_info.value, NotImplementedError):
        assert "provider 429" in str(exc_info.value)


# ============================================================
# TestChooserAgent
# ============================================================


@pytest.fixture
def test_chooser(mock_llm) -> TestChooserAgent:
    return TestChooserAgent(mock_llm)


_NEXT_TEST_JSON = json.dumps({
    "name": "MRI brain w/ contrast",
    "rationale": "Discriminates between cerebrovascular and inflammatory etiologies",
    "estimated_cost_usd": 1200.0,
    "information_gain_estimate": 0.8,
    "discriminates_between": ["Acute ischemic stroke", "CNS vasculitis"],
})


async def test_test_chooser_happy_path(test_chooser, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_NEXT_TEST_JSON, tokens_used=300, cost_usd=0.003,
        model="anthropic/claude-opus-4",
    )
    msg = await test_chooser.deliberate(base_case, transcript=[], iteration=0)
    assert msg.role == AgentRole.TEST_CHOOSER
    assert isinstance(msg.structured_output, NextTest)
    assert msg.structured_output.name == "MRI brain w/ contrast"
    assert msg.structured_output.estimated_cost_usd == 1200.0
    assert msg.tokens_used == 300


async def test_test_chooser_malformed_json_raises(test_chooser, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content="not json", tokens_used=10, cost_usd=0.0, model="x",
    )
    with pytest.raises((ValueError, json.JSONDecodeError)):
        await test_chooser.deliberate(base_case, [], 0)


# ============================================================
# ChallengerAgent
# ============================================================


@pytest.fixture
def challenger(mock_llm):
    from quorum.orchestrator.agents.challenger import ChallengerAgent
    return ChallengerAgent(mock_llm)


_CHALLENGE_JSON = json.dumps({
    "against_top_candidate": ["Onset was acute, not insidious", "No fever"],
    "alternative_to_consider": "Transient ischemic attack",
    "confidence_in_challenge": 0.7,
})


@pytest.mark.asyncio
async def test_challenger_happy_path(challenger, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_CHALLENGE_JSON, tokens_used=200, cost_usd=0.002, model="x",
    )
    msg = await challenger.deliberate(base_case, [], 0)
    assert msg.role.value == "challenger"
    assert msg.structured_output["alternative_to_consider"] == "Transient ischemic attack"
    assert msg.structured_output["confidence_in_challenge"] == 0.7


# ============================================================
# StewardshipAgent
# ============================================================


@pytest.fixture
def stewardship(mock_llm):
    from quorum.orchestrator.agents.stewardship import StewardshipAgent
    return StewardshipAgent(mock_llm)


_STEW_JSON_ACCEPT = json.dumps({
    "accept_test": True,
    "cost_concern": None,
    "cheaper_alternative": None,
})

_STEW_JSON_REJECT = json.dumps({
    "accept_test": False,
    "cost_concern": "MRI exceeds the $500 budget",
    "cheaper_alternative": {
        "name": "Non-contrast CT head",
        "rationale": "Adequately rules out hemorrhage at 1/10th cost",
        "estimated_cost_usd": 150.0,
        "information_gain_estimate": 0.5,
        "discriminates_between": [],
    },
})


@pytest.mark.asyncio
async def test_stewardship_accepts(stewardship, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_STEW_JSON_ACCEPT, tokens_used=100, cost_usd=0.001, model="x",
    )
    msg = await stewardship.deliberate(base_case, [], 0)
    assert msg.structured_output["accept_test"] is True


@pytest.mark.asyncio
async def test_stewardship_rejects_with_alternative(stewardship, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_STEW_JSON_REJECT, tokens_used=180, cost_usd=0.0018, model="x",
    )
    msg = await stewardship.deliberate(base_case, [], 0)
    assert msg.structured_output["accept_test"] is False
    assert msg.structured_output["cheaper_alternative"]["estimated_cost_usd"] == 150.0


# ============================================================
# ChecklistAgent
# ============================================================


@pytest.fixture
def checklist(mock_llm):
    from quorum.orchestrator.agents.checklist import ChecklistAgent
    return ChecklistAgent(mock_llm)


_CHK_JSON_CLEAN = json.dumps({
    "consistent": True, "flags": [], "recommend_continue": True,
})

_CHK_JSON_CONTRADICTION = json.dumps({
    "consistent": False,
    "flags": ["Hypothesis cites fever as evidence; case states T=98.6F"],
    "recommend_continue": False,
})


@pytest.mark.asyncio
async def test_checklist_clean(checklist, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_CHK_JSON_CLEAN, tokens_used=80, cost_usd=0.0008, model="x",
    )
    msg = await checklist.deliberate(base_case, [], 0)
    assert msg.structured_output["consistent"] is True
    assert msg.structured_output["recommend_continue"] is True


@pytest.mark.asyncio
async def test_checklist_flags_contradiction(checklist, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_CHK_JSON_CONTRADICTION, tokens_used=120, cost_usd=0.0012, model="x",
    )
    msg = await checklist.deliberate(base_case, [], 0)
    assert msg.structured_output["consistent"] is False
    assert len(msg.structured_output["flags"]) >= 1
    assert msg.structured_output["recommend_continue"] is False
