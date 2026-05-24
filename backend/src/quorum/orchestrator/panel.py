"""The deliberation orchestrator.

Phase-5 multi-iteration consensus loop. Per-iteration call order:
    hypothesis → test_chooser → (challenger || stewardship) → checklist

Agents whose slot is absent in PanelConfig are skipped — e.g. the
`baseline_single_call` config runs only the hypothesis slot.

Termination (evaluated at the END of every iteration):
    consensus:       top posterior > consensus_threshold AND NOT checklist-blocks
    checklist_stop:  checklist recommends stop AND consistent=True
    max_iterations:  loop hit cfg.max_iterations without consensus
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
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    CaseInput,
    Differential,
    FinalVerdict,
    StreamEvent,
)

logger = logging.getLogger(__name__)


class Panel:
    """The (up to) five-agent deliberation orchestrator.

    Usage:
        panel = Panel(llm, PanelConfig.list_available()[0])
        verdict = await panel.diagnose(case)
        # or stream:
        async for event in panel.diagnose_stream(case):
            ...
    """

    def __init__(self, llm: LLMClient, config: PanelConfig | None = None):
        self.llm = llm
        if config is None:
            config = PanelConfig.list_available()[0]
        self.config = config

        # Required slot.
        self.hypothesis = HypothesisAgent(llm, model=config.hypothesis.model)

        # Optional slots — None when the YAML omits them (e.g. baseline_single_call).
        self.test_chooser = (
            TestChooserAgent(llm, model=config.test_chooser.model)
            if config.test_chooser is not None
            else None
        )
        self.challenger = (
            ChallengerAgent(llm, model=config.challenger.model)
            if config.challenger is not None
            else None
        )
        self.stewardship = (
            StewardshipAgent(llm, model=config.stewardship.model)
            if config.stewardship is not None
            else None
        )
        self.checklist = (
            ChecklistAgent(llm, model=config.checklist.model)
            if config.checklist is not None
            else None
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def diagnose(self, case: CaseInput) -> FinalVerdict:
        """Run the deliberation loop and return the FinalVerdict.

        Internally drains diagnose_stream; the verdict event carries the
        already-built FinalVerdict, so this is just a convenience wrapper.
        """
        final: dict | None = None
        async for ev in self.diagnose_stream(case):
            if ev.event == "verdict":
                final = ev.data
        if final is None:
            return self._error_verdict(case)
        return FinalVerdict.model_validate(final)

    async def diagnose_stream(
        self, case: CaseInput
    ) -> AsyncIterator[StreamEvent]:
        """Stream SSE events across the multi-iteration deliberation."""
        transcript: list[AgentMessage] = []
        termination: str = "max_iterations"
        iterations_used = 0

        for iteration in range(self.config.max_iterations):
            iterations_used = iteration + 1

            # ----- hypothesis (required, sequential) -----
            yield StreamEvent(
                event="agent_start",
                data={"agent": "hypothesis", "iteration": iteration},
            )
            started = time.perf_counter()
            try:
                hyp_msg = await self.hypothesis.deliberate(
                    case, list(transcript), iteration
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("hypothesis.deliberate failed mid-stream")
                async for ev in self._emit_error_then_verdict(
                    exc, case, transcript, iterations_used
                ):
                    yield ev
                return
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            transcript.append(hyp_msg)
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

            # ----- test_chooser (optional, sequential) -----
            tc_msg: AgentMessage | None = None
            if self.test_chooser is not None:
                yield StreamEvent(
                    event="agent_start",
                    data={"agent": "test_chooser", "iteration": iteration},
                )
                started_tc = time.perf_counter()
                try:
                    tc_msg = await self.test_chooser.deliberate(
                        case, list(transcript), iteration
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception("test_chooser.deliberate failed mid-stream")
                    async for ev in self._emit_error_then_verdict(
                        exc, case, transcript, iterations_used
                    ):
                        yield ev
                    return
                transcript.append(tc_msg)
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

            # ----- challenger || stewardship (optional, gathered) -----
            # CRITICAL: emit BOTH agent_start events synchronously so the UI
            # shows both spinning, then asyncio.gather. After gather, emit
            # agent_complete events in original (challenger, stewardship) order.
            chal_msg: AgentMessage | None = None
            stew_msg: AgentMessage | None = None
            both_parallel = self.challenger is not None and self.stewardship is not None
            if both_parallel:
                yield StreamEvent(
                    event="agent_start",
                    data={"agent": "challenger", "iteration": iteration},
                )
                yield StreamEvent(
                    event="agent_start",
                    data={"agent": "stewardship", "iteration": iteration},
                )
                started_par = time.perf_counter()
                results = await asyncio.gather(
                    self.challenger.deliberate(case, list(transcript), iteration),
                    self.stewardship.deliberate(case, list(transcript), iteration),
                    return_exceptions=True,
                )
                par_ms = int((time.perf_counter() - started_par) * 1000)
                chal_res, stew_res = results
                if isinstance(chal_res, BaseException):
                    if isinstance(chal_res, asyncio.CancelledError):
                        raise chal_res
                    logger.exception(
                        "challenger.deliberate failed mid-stream",
                        exc_info=chal_res,
                    )
                    async for ev in self._emit_error_then_verdict(
                        chal_res, case, transcript, iterations_used
                    ):
                        yield ev
                    return
                if isinstance(stew_res, BaseException):
                    if isinstance(stew_res, asyncio.CancelledError):
                        raise stew_res
                    logger.exception(
                        "stewardship.deliberate failed mid-stream",
                        exc_info=stew_res,
                    )
                    async for ev in self._emit_error_then_verdict(
                        stew_res, case, transcript, iterations_used
                    ):
                        yield ev
                    return
                chal_msg = chal_res
                stew_msg = stew_res
                transcript.append(chal_msg)
                transcript.append(stew_msg)
                yield StreamEvent(
                    event="agent_complete",
                    data={
                        "agent": "challenger",
                        "structured_output": chal_msg.structured_output,
                        "tokens_used": chal_msg.tokens_used,
                        "cost_usd": chal_msg.cost_usd,
                        "latency_ms": par_ms,
                    },
                )
                yield StreamEvent(
                    event="agent_complete",
                    data={
                        "agent": "stewardship",
                        "structured_output": stew_msg.structured_output,
                        "tokens_used": stew_msg.tokens_used,
                        "cost_usd": stew_msg.cost_usd,
                        "latency_ms": par_ms,
                    },
                )
            else:
                # Run whichever one is configured (if any) sequentially.
                for name, agent in (
                    ("challenger", self.challenger),
                    ("stewardship", self.stewardship),
                ):
                    if agent is None:
                        continue
                    yield StreamEvent(
                        event="agent_start",
                        data={"agent": name, "iteration": iteration},
                    )
                    started_one = time.perf_counter()
                    try:
                        msg = await agent.deliberate(case, list(transcript), iteration)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        logger.exception("%s.deliberate failed mid-stream", name)
                        async for ev in self._emit_error_then_verdict(
                            exc, case, transcript, iterations_used
                        ):
                            yield ev
                        return
                    transcript.append(msg)
                    if name == "challenger":
                        chal_msg = msg
                    else:
                        stew_msg = msg
                    yield StreamEvent(
                        event="agent_complete",
                        data={
                            "agent": name,
                            "structured_output": msg.structured_output,
                            "tokens_used": msg.tokens_used,
                            "cost_usd": msg.cost_usd,
                            "latency_ms": int(
                                (time.perf_counter() - started_one) * 1000
                            ),
                        },
                    )

            # ----- checklist (optional, sequential — runs LAST per round) -----
            chk_msg: AgentMessage | None = None
            if self.checklist is not None:
                yield StreamEvent(
                    event="agent_start",
                    data={"agent": "checklist", "iteration": iteration},
                )
                started_chk = time.perf_counter()
                try:
                    chk_msg = await self.checklist.deliberate(
                        case, list(transcript), iteration
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception("checklist.deliberate failed mid-stream")
                    async for ev in self._emit_error_then_verdict(
                        exc, case, transcript, iterations_used
                    ):
                        yield ev
                    return
                transcript.append(chk_msg)
                yield StreamEvent(
                    event="agent_complete",
                    data={
                        "agent": "checklist",
                        "structured_output": chk_msg.structured_output,
                        "tokens_used": chk_msg.tokens_used,
                        "cost_usd": chk_msg.cost_usd,
                        "latency_ms": int(
                            (time.perf_counter() - started_chk) * 1000
                        ),
                    },
                )

            # ----- end-of-round signal -----
            yield StreamEvent(
                event="round_complete",
                data={"iteration": iteration},
            )

            # ----- termination evaluation (AFTER checklist) -----
            top_posterior = self._top_posterior(hyp_msg)
            chk_blocks = False
            chk_stops_clean = False
            if chk_msg is not None and isinstance(chk_msg.structured_output, dict):
                so = chk_msg.structured_output
                recommend_continue = so.get("recommend_continue", True)
                consistent = so.get("consistent", True)
                if recommend_continue is False and consistent is False:
                    chk_blocks = True
                if recommend_continue is False and consistent is True:
                    chk_stops_clean = True

            if top_posterior > self.config.consensus_threshold and not chk_blocks:
                termination = "consensus"
                break
            if chk_stops_clean:
                termination = "checklist_stop"
                break
            # else: keep iterating; fall through to next round
        else:
            # for-loop ran to completion without break
            termination = "max_iterations"

        verdict = self._build_verdict(case, transcript, termination, iterations_used)
        yield StreamEvent(event="verdict", data=verdict.model_dump(mode="json"))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _emit_error_then_verdict(
        self,
        exc: BaseException,
        case: CaseInput,
        transcript: list[AgentMessage],
        iterations_used: int,
    ) -> AsyncIterator[StreamEvent]:
        """Emit one error event followed by an error verdict, then close."""
        yield StreamEvent(
            event="error",
            data={
                "code": self._classify_error(exc),
                "message": str(exc),
                "retriable": self._is_retriable(exc),
                "http_status": None,
            },
        )
        err = self._error_verdict(case)
        yield StreamEvent(event="verdict", data=err.model_dump(mode="json"))

    @staticmethod
    def _top_posterior(hyp_msg: AgentMessage) -> float:
        diff = hyp_msg.structured_output
        if not isinstance(diff, Differential) or not diff.candidates:
            return 0.0
        return max(c.posterior for c in diff.candidates)

    def _build_verdict(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        termination: str,
        iterations_used: int,
    ) -> FinalVerdict:
        if not transcript:
            raise ValueError("cannot build verdict from empty transcript")
        # Use the LAST hypothesis message (latest iteration).
        hyp_msgs = [m for m in transcript if m.role == AgentRole.HYPOTHESIS]
        if not hyp_msgs:
            raise ValueError("no hypothesis message in transcript")
        last_hyp = hyp_msgs[-1]
        diff = last_hyp.structured_output
        if not isinstance(diff, Differential):
            raise TypeError(
                "Hypothesis must produce a Differential as structured_output; "
                f"got {type(diff).__name__}"
            )
        confidence = self._top_posterior(last_hyp)
        return FinalVerdict(
            case_id=case.case_id,
            final_differential=diff,
            confidence=confidence,
            iterations_used=iterations_used,
            total_tokens=sum(m.tokens_used for m in transcript),
            total_cost_usd=sum(m.cost_usd for m in transcript),
            transcript=list(transcript),
            termination_reason=termination,  # type: ignore[arg-type]
            schema_version=1,
            is_error=False,
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
            schema_version=1,
            is_error=True,
        )

    @staticmethod
    def _classify_error(exc: BaseException) -> str:
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
    def _is_retriable(exc: BaseException) -> bool:
        msg = str(exc).lower()
        return "429" in msg or "rate limit" in msg or "timeout" in msg
