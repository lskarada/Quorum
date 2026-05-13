"""The deliberation orchestrator.

Vertical-slice impl: single-agent (Hypothesis) single-iteration loop. The
five-agent debate loop (TestChooser/Challenger/Stewardship/Checklist) is
deferred to a later phase.
"""
from __future__ import annotations

import json
import time
from typing import AsyncIterator

from quorum.llm.client import LLMClient
from quorum.orchestrator.agents import (
    ChallengerAgent,
    ChecklistAgent,
    HypothesisAgent,
    StewardshipAgent,
    TestChooserAgent,
)
from quorum.orchestrator.schemas import (
    AgentMessage,
    CaseInput,
    Differential,
    FinalVerdict,
    StreamEvent,
)

_CONSENSUS_THRESHOLD = 0.6  # strict: > 0.6 → consensus


class Panel:
    """The five-agent deliberation orchestrator.

    Usage:
        panel = Panel(llm)
        verdict = await panel.diagnose(case)
        # or stream:
        async for event in panel.diagnose_stream(case):
            ...
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.hypothesis = HypothesisAgent(llm)
        self.test_chooser = TestChooserAgent(llm)
        self.challenger = ChallengerAgent(llm)
        self.stewardship = StewardshipAgent(llm)
        self.checklist = ChecklistAgent(llm)

    async def diagnose(self, case: CaseInput) -> FinalVerdict:
        try:
            message = await self.hypothesis.deliberate(case, [], 0)
        except Exception:
            return self._error_verdict(case)
        return self._build_verdict(case, message)

    async def diagnose_stream(
        self, case: CaseInput
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(
            event="agent_start",
            data={"agent": "hypothesis", "iteration": 0},
        )

        started = time.perf_counter()
        try:
            message = await self.hypothesis.deliberate(case, [], 0)
        except Exception as exc:
            yield StreamEvent(
                event="error",
                data={
                    "code": self._classify_error(exc),
                    "message": str(exc),
                    "retriable": self._is_retriable(exc),
                    "http_status": None,
                },
            )
            return
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        yield StreamEvent(
            event="agent_complete",
            data={
                "agent": "hypothesis",
                "differential": message.structured_output.model_dump(mode="json"),
                "tokens_used": message.tokens_used,
                "cost_usd": message.cost_usd,
                "latency_ms": elapsed_ms,
            },
        )

        verdict = self._build_verdict(case, message)
        yield StreamEvent(event="verdict", data=verdict.model_dump(mode="json"))

    def _build_verdict(self, case: CaseInput, message: AgentMessage) -> FinalVerdict:
        diff = message.structured_output
        assert isinstance(diff, Differential), "Hypothesis must produce a Differential"
        top_posterior = diff.candidates[0].posterior if diff.candidates else 0.0
        termination_reason = (
            "consensus" if top_posterior > _CONSENSUS_THRESHOLD else "max_iterations"
        )
        return FinalVerdict(
            case_id=case.case_id,
            final_differential=diff,
            confidence=top_posterior,
            iterations_used=1,
            total_tokens=message.tokens_used,
            total_cost_usd=message.cost_usd,
            transcript=[message],
            termination_reason=termination_reason,
        )

    def _error_verdict(self, case: CaseInput) -> FinalVerdict:
        return FinalVerdict(
            case_id=case.case_id,
            final_differential=Differential(candidates=[], iteration=0),
            confidence=0.0,
            iterations_used=1,
            total_tokens=0,
            total_cost_usd=0.0,
            transcript=[],
            termination_reason="error",
        )

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        msg = str(exc).lower()
        if "429" in msg or "rate limit" in msg:
            return "provider_429"
        if "timeout" in msg:
            return "provider_timeout"
        if isinstance(exc, json.JSONDecodeError) or "json" in msg:
            return "parse_failure"
        if "validation" in msg or "schema" in msg:
            return "schema_violation"
        return "internal"

    @staticmethod
    def _is_retriable(exc: Exception) -> bool:
        msg = str(exc).lower()
        return "429" in msg or "rate limit" in msg or "timeout" in msg
