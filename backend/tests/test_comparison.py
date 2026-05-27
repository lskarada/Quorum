"""Tests for ComparisonRunner — runs two panels in parallel, multiplexes events."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from quorum.llm.client import LLMClient, LLMResponse
from quorum.orchestrator.comparison_runner import ComparisonRunner
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import CaseInput, StreamEvent


def _dev_cheap() -> PanelConfig:
    return next(c for c in PanelConfig.list_available() if c.name == "dev_cheap")


def _baseline() -> PanelConfig:
    return next(
        c for c in PanelConfig.list_available() if c.name == "baseline_single_call"
    )


def _hyp_json(top_posterior: float = 0.9) -> str:
    remaining = (1.0 - top_posterior) / 2
    return json.dumps(
        {
            "candidates": [
                {
                    "name": "Top",
                    "posterior": top_posterior,
                    "rationale": "r",
                    "supporting_findings": [],
                    "against_findings": [],
                    "citations": [],
                },
                {
                    "name": "Second",
                    "posterior": remaining,
                    "rationale": "r",
                    "supporting_findings": [],
                    "against_findings": [],
                    "citations": [],
                },
                {
                    "name": "Third",
                    "posterior": remaining,
                    "rationale": "r",
                    "supporting_findings": [],
                    "against_findings": [],
                    "citations": [],
                },
            ],
            "iteration": 0,
        }
    )


_TC_JSON = json.dumps(
    {
        "name": "X",
        "rationale": "r",
        "estimated_cost_usd": 100.0,
        "information_gain_estimate": 0.5,
        "discriminates_between": [],
    }
)
_CHAL_JSON = json.dumps(
    {
        "against_top_candidate": [],
        "alternative_to_consider": "none",
        "confidence_in_challenge": 0.3,
    }
)
_STEW_JSON = json.dumps(
    {"accept_test": True, "cost_concern": None, "cheaper_alternative": None}
)
_CHK_JSON = json.dumps(
    {"consistent": True, "flags": [], "recommend_continue": True}
)


def _llm_for_combined_run() -> LLMClient:
    """LLM mock with enough canned responses for one dev_cheap iteration
    PLUS one baseline_single_call call.

    Order of consumption depends on async scheduling — to be robust we mix
    enough of each response type that whatever order .complete() is called
    in, every call resolves to a valid structured response for its agent.

    dev_cheap (1 iteration, consensus on first round w/ top_posterior=0.9):
      hyp, tc, chal, stew, chk  = 5 calls
    baseline_single_call (1 iteration, 1 agent):
      hyp                       = 1 call

    Total: 6 calls.

    Since the two panels run concurrently and we don't know the interleaving,
    we make .complete()'s side_effect content-aware by inspecting the messages
    arg and returning the right JSON for the requesting agent.
    """
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "x"

    async def _fake_complete(messages, model=None, response_format=None, max_tokens=4096):
        # Inspect prompt content to figure out which agent is calling.
        joined = " ".join(m.get("content", "") for m in messages).lower()
        if "test_chooser" in joined or "next diagnostic test" in joined or "next test" in joined:
            return LLMResponse(content=_TC_JSON, tokens_used=80, cost_usd=0.001, model="x")
        if "challenger" in joined or "challenge" in joined or "alternative_to_consider" in joined:
            return LLMResponse(content=_CHAL_JSON, tokens_used=80, cost_usd=0.001, model="x")
        if "stewardship" in joined or ("cost" in joined and "accept" in joined):
            return LLMResponse(content=_STEW_JSON, tokens_used=80, cost_usd=0.001, model="x")
        if "checklist" in joined or "consistent" in joined or "recommend_continue" in joined:
            return LLMResponse(content=_CHK_JSON, tokens_used=80, cost_usd=0.001, model="x")
        # default: hypothesis
        return LLMResponse(
            content=_hyp_json(0.9), tokens_used=100, cost_usd=0.001, model="x"
        )

    llm.complete = AsyncMock(side_effect=_fake_complete)
    return llm


@pytest.mark.asyncio
async def test_compare_emits_events_tagged_with_panel_id():
    """Every event from compare_stream carries panel_id in its data."""
    llm = _llm_for_combined_run()
    runner = ComparisonRunner([_dev_cheap(), _baseline()], llm)
    events: list[StreamEvent] = [
        ev async for ev in runner.compare_stream(CaseInput(presentation="x"))
    ]
    assert len(events) > 0
    for ev in events:
        assert "panel_id" in ev.data, f"event {ev.event} missing panel_id"
    panel_ids = {ev.data["panel_id"] for ev in events}
    assert panel_ids == {"dev_cheap", "baseline_single_call"}


@pytest.mark.asyncio
async def test_compare_both_verdicts_received():
    """Both panels emit exactly one verdict event each."""
    llm = _llm_for_combined_run()
    runner = ComparisonRunner([_dev_cheap(), _baseline()], llm)
    events = [
        ev async for ev in runner.compare_stream(CaseInput(presentation="x"))
    ]
    verdicts = [ev for ev in events if ev.event == "verdict"]
    assert len(verdicts) == 2
    by_panel = {ev.data["panel_id"]: ev for ev in verdicts}
    assert "dev_cheap" in by_panel
    assert "baseline_single_call" in by_panel


@pytest.mark.asyncio
async def test_compare_one_panel_failure_does_not_abort_other():
    """When panel A raises, panel B still runs to its verdict.

    Deterministic approach: monkey-patch each Panel instance's
    `diagnose_stream` async-generator method directly.
    """
    from quorum.orchestrator.schemas import Differential, FinalVerdict

    async def failing_stream(case):
        raise RuntimeError("dev_cheap broke")
        yield  # unreachable, but makes this an async-generator

    async def good_stream(case):
        verdict = FinalVerdict(
            case_id=None,
            final_differential=Differential(candidates=[], iteration=0),
            confidence=0.0,
            iterations_used=1,
            total_tokens=0,
            total_cost_usd=0.0,
            transcript=[],
            termination_reason="max_iterations",
            schema_version=1,
            is_error=False,
        )
        yield StreamEvent(
            event="verdict", data=verdict.model_dump(mode="json")
        )

    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "x"
    runner = ComparisonRunner([_dev_cheap(), _baseline()], llm)
    runner.panels[0].diagnose_stream = failing_stream
    runner.panels[1].diagnose_stream = good_stream

    events = [
        ev async for ev in runner.compare_stream(CaseInput(presentation="x"))
    ]
    by_panel = {
        pid: [ev for ev in events if ev.data.get("panel_id") == pid]
        for pid in ("dev_cheap", "baseline_single_call")
    }
    # dev_cheap emits one error event (no verdict, since the exception fired
    # before diagnose_stream ever yielded one).
    assert any(ev.event == "error" for ev in by_panel["dev_cheap"])
    # baseline runs to its verdict normally.
    assert any(ev.event == "verdict" for ev in by_panel["baseline_single_call"])


@pytest.mark.asyncio
async def test_compare_uniqueness_assert_on_panel_names():
    """ComparisonRunner refuses to construct with two configs of the same name."""
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "x"
    with pytest.raises(AssertionError, match="must differ"):
        ComparisonRunner([_dev_cheap(), _dev_cheap()], llm)
