"""The deliberation orchestrator.

Vertical-slice impl: single-agent (Hypothesis) single-iteration loop. The
five-agent debate loop (TestChooser/Challenger/Stewardship/Checklist) is
deferred to a later phase.
"""
from __future__ import annotations

import asyncio
import json
import logging
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

logger = logging.getLogger(__name__)

_CONSENSUS_THRESHOLD = 0.6


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
        messages: list[AgentMessage] = []
        try:
            hyp_msg = await self.hypothesis.deliberate(case, [], 0)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("hypothesis.deliberate failed for case %s", case.case_id)
            return self._error_verdict(case)
        messages.append(hyp_msg)

        try:
            tc_msg = await self.test_chooser.deliberate(case, list(messages), 0)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("test_chooser.deliberate failed for case %s", case.case_id)
            return self._error_verdict(case)
        messages.append(tc_msg)

        return self._build_verdict(case, messages)

    async def diagnose_stream(
        self, case: CaseInput
    ) -> AsyncIterator[StreamEvent]:
        messages: list[AgentMessage] = []

        yield StreamEvent(
            event="agent_start",
            data={"agent": "hypothesis", "iteration": 0},
        )

        started = time.perf_counter()
        try:
            hyp_msg = await self.hypothesis.deliberate(case, [], 0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("hypothesis.deliberate failed mid-stream")
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
        messages.append(hyp_msg)

        yield StreamEvent(
            event="agent_complete",
            data={
                "agent": "hypothesis",
                "differential": hyp_msg.structured_output.model_dump(mode="json"),
                "tokens_used": hyp_msg.tokens_used,
                "cost_usd": hyp_msg.cost_usd,
                "latency_ms": elapsed_ms,
            },
        )

        yield StreamEvent(
            event="agent_start",
            data={"agent": "test_chooser", "iteration": 0},
        )

        started_tc = time.perf_counter()
        try:
            tc_msg = await self.test_chooser.deliberate(case, list(messages), 0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("test_chooser.deliberate failed mid-stream")
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
        messages.append(tc_msg)

        yield StreamEvent(
            event="agent_complete",
            data={
                "agent": "test_chooser",
                "next_test": tc_msg.structured_output.model_dump(mode="json"),
                "tokens_used": tc_msg.tokens_used,
                "cost_usd": tc_msg.cost_usd,
                "latency_ms": int((time.perf_counter() - started_tc) * 1000),
            },
        )

        verdict = self._build_verdict(case, messages)
        yield StreamEvent(event="verdict", data=verdict.model_dump(mode="json"))

    def _build_verdict(
        self, case: CaseInput, messages: list[AgentMessage]
    ) -> FinalVerdict:
        if not messages:
            raise ValueError("cannot build verdict from empty transcript")
        hyp_msg = messages[0]
        diff = hyp_msg.structured_output
        if not isinstance(diff, Differential):
            raise TypeError(
                "Hypothesis must produce a Differential as structured_output; "
                f"got {type(diff).__name__}"
            )
        top_posterior = (
            max(c.posterior for c in diff.candidates) if diff.candidates else 0.0
        )
        termination_reason = (
            "consensus" if top_posterior > _CONSENSUS_THRESHOLD else "max_iterations"
        )
        return FinalVerdict(
            case_id=case.case_id,
            final_differential=diff,
            confidence=top_posterior,
            iterations_used=1,
            total_tokens=sum(m.tokens_used for m in messages),
            total_cost_usd=sum(m.cost_usd for m in messages),
            transcript=list(messages),
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
