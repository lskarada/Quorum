"""Hermetic tests for v2_runner (Phase 6/7 prep)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from quorum.eval.eval_case import EvalCase, Finding
from quorum.eval.v2_runner import run_arm_a, run_arm_b
from quorum.llm.client import LLMClient, LLMResponse
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    DiagnosisCandidate,
    Differential,
    NextTest,
)


def _llm_stub() -> LLMClient:
    """Build a stub LLMClient with .complete mocked to return a numeric index.

    Used as the Gatekeeper matcher backend in tests. Agents are mocked at
    the .deliberate() level so they never call .complete.
    """
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "x"
    llm.complete = AsyncMock(
        return_value=LLMResponse(
            content="0", tokens_used=5, cost_usd=0.0, model="stub",
        )
    )
    return llm


def _panel(name: str) -> PanelConfig:
    return next(c for c in PanelConfig.list_available() if c.name == name)


def _toy_eval_case(cid: str = "toy-runner") -> EvalCase:
    return EvalCase(
        case_id=cid,
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


def _hyp_msg(top_p: float = 0.85) -> AgentMessage:
    diff = Differential(
        candidates=[
            DiagnosisCandidate(name="SLE", posterior=top_p, rationale="x"),
            DiagnosisCandidate(name="MCTD", posterior=(1 - top_p) * 0.6, rationale="x"),
            DiagnosisCandidate(name="RA", posterior=(1 - top_p) * 0.4, rationale="x"),
        ],
        iteration=0,
    )
    return AgentMessage(
        role=AgentRole.HYPOTHESIS,
        iteration=0,
        content="hyp",
        structured_output=diff,
        tokens_used=300,
        cost_usd=0.012,
    )


def _tc_msg(name: str = "ANA") -> AgentMessage:
    return AgentMessage(
        role=AgentRole.TEST_CHOOSER,
        iteration=0,
        content="tc",
        structured_output=NextTest(name=name, rationale="r"),
        tokens_used=80,
        cost_usd=0.003,
    )


def _challenger_msg() -> AgentMessage:
    return AgentMessage(
        role=AgentRole.CHALLENGER, iteration=0, content="chal",
        structured_output={
            "against_top_candidate": [],
            "alternative_to_consider": "none",
            "confidence_in_challenge": 0.1,
        },
        tokens_used=60, cost_usd=0.003,
    )


def _stewardship_msg() -> AgentMessage:
    return AgentMessage(
        role=AgentRole.STEWARDSHIP, iteration=0, content="stew",
        structured_output={
            "accept_test": True,
            "cost_concern": None,
            "cheaper_alternative": None,
        },
        tokens_used=60, cost_usd=0.002,
    )


def _checklist_msg() -> AgentMessage:
    return AgentMessage(
        role=AgentRole.CHECKLIST, iteration=0, content="chk",
        structured_output={"consistent": True, "flags": [], "recommend_continue": True},
        tokens_used=60, cost_usd=0.002,
    )


async def test_run_arm_a_writes_audit_jsonl(tmp_path, monkeypatch):
    """run_arm_a happy path: writes audit JSONL + manifest, includes posterior."""
    llm = _llm_stub()
    cfg = _panel("v2_quorum_calibrated")

    # We can't easily inject panel stubs through run_arm_a, so we use a thin
    # wrapper that patches the panel's agents post-construction.
    from quorum.orchestrator.panel import Panel as RealPanel

    real_init = RealPanel.__init__

    def patched_init(self, llm_, config=None):
        real_init(self, llm_, config)
        self.hypothesis.deliberate = AsyncMock(return_value=_hyp_msg(0.85))
        self.test_chooser.deliberate = AsyncMock(return_value=_tc_msg())
        self.challenger.deliberate = AsyncMock(return_value=_challenger_msg())
        self.stewardship.deliberate = AsyncMock(return_value=_stewardship_msg())
        self.checklist.deliberate = AsyncMock(return_value=_checklist_msg())

    monkeypatch.setattr(RealPanel, "__init__", patched_init)

    case = _toy_eval_case("toy-arm-a")
    out_dir = await run_arm_a(
        [case], cfg, tmp_path, llm=llm, run_id="t-a",
        max_turns=5, commit_threshold=0.7, confirm_cost=True,
    )
    assert (out_dir / "manifest.json").exists()
    audit_path = out_dir / f"{case.case_id}.audit.jsonl"
    assert audit_path.exists()
    lines = audit_path.read_text().strip().splitlines()
    header = json.loads(lines[0])
    assert header["final_committed_diagnosis"] == "SLE"
    assert header["final_posterior"]["SLE"] == pytest.approx(0.85)


async def test_run_arm_a_is_idempotent(tmp_path, monkeypatch):
    """Re-running run_arm_a with same run_id skips finished cases."""
    llm = _llm_stub()
    cfg = _panel("v2_quorum_calibrated")

    from quorum.orchestrator.panel import Panel as RealPanel

    call_counter = {"n": 0}
    real_init = RealPanel.__init__

    def patched_init(self, llm_, config=None):
        real_init(self, llm_, config)
        async def _hyp(*a, **kw):
            call_counter["n"] += 1
            return _hyp_msg(0.9)
        self.hypothesis.deliberate = _hyp
        self.test_chooser.deliberate = AsyncMock(return_value=_tc_msg())
        self.challenger.deliberate = AsyncMock(return_value=_challenger_msg())
        self.stewardship.deliberate = AsyncMock(return_value=_stewardship_msg())
        self.checklist.deliberate = AsyncMock(return_value=_checklist_msg())

    monkeypatch.setattr(RealPanel, "__init__", patched_init)

    case = _toy_eval_case("toy-idem")
    await run_arm_a([case], cfg, tmp_path, llm=llm, run_id="t-idem",
                    max_turns=5, commit_threshold=0.7, confirm_cost=True)
    first = call_counter["n"]
    await run_arm_a([case], cfg, tmp_path, llm=llm, run_id="t-idem",
                    max_turns=5, commit_threshold=0.7, confirm_cost=True)
    assert call_counter["n"] == first  # second run did NOT call hypothesis


async def test_cost_cap_blocks_unconfirmed_run(tmp_path, monkeypatch):
    """If projected > QUORUM_MAX_COST_USD and confirm_cost=False, raise."""
    monkeypatch.setenv("QUORUM_MAX_COST_USD", "0.10")
    cfg = _panel("v2_quorum_calibrated")
    case = _toy_eval_case("toy-cap")
    with pytest.raises(RuntimeError, match="Projected cost"):
        await run_arm_a([case], cfg, tmp_path, llm=_llm_stub(), confirm_cost=False)


async def test_run_arm_b_uses_diagnose(tmp_path, monkeypatch):
    """Arm B runs Panel.diagnose, captures the verdict's top diagnosis."""
    llm = _llm_stub()
    cfg = _panel("v2_single_sonnet")

    from quorum.orchestrator.panel import Panel as RealPanel
    from quorum.orchestrator.schemas import FinalVerdict

    real_init = RealPanel.__init__

    def patched_init(self, llm_, config=None):
        real_init(self, llm_, config)
        # Fake the diagnose() call directly
        canned_diff = _hyp_msg(0.78).structured_output
        async def _diag(case_input):
            return FinalVerdict(
                case_id=case_input.case_id,
                final_differential=canned_diff,
                confidence=0.78,
                iterations_used=1,
                total_tokens=300,
                total_cost_usd=0.012,
                transcript=[],
                termination_reason="consensus",
                schema_version=1,
                is_error=False,
            )
        self.diagnose = _diag

    monkeypatch.setattr(RealPanel, "__init__", patched_init)

    case = _toy_eval_case("toy-arm-b")
    out_dir = await run_arm_b([case], cfg, tmp_path, llm=llm,
                              run_id="t-b", confirm_cost=True)
    audit_path = out_dir / f"{case.case_id}.audit.jsonl"
    header = json.loads(audit_path.read_text().splitlines()[0])
    assert header["final_committed_diagnosis"] == "SLE"
    assert header["final_posterior"]["SLE"] == pytest.approx(0.78)
