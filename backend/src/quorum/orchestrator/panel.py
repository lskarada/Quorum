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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncIterator

from quorum.llm.client import LLMClient
from quorum.orchestrator.agents import (
    ChallengerAgent,
    ChecklistAgent,
    HypothesisAgent,
    StewardshipAgent,
    TestChooserAgent,
)
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.safety import SafetyChecker
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    CaseInput,
    Differential,
    FinalVerdict,
    StreamEvent,
)

if TYPE_CHECKING:
    from quorum.audit.writer import AuditWriter
    from quorum.eval.eval_case import EvalCase


@dataclass
class SequentialResult:
    """Output of Panel.run_sequential — one row per case."""

    case_id: str
    committed_diagnosis: str
    final_posterior: dict[str, float]
    n_turns: int
    simulated_cost_usd: float = 0.0
    real_cost_usd: float = 0.0
    forced: bool = False  # True if max_turns or safety cost-override forced commit
    revealed_findings: list[str] = field(default_factory=list)

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
    # Sequential diagnosis (v2 — SDBench-style multi-turn with Gatekeeper)
    # ------------------------------------------------------------------

    async def run_sequential(
        self,
        case: "EvalCase",
        gatekeeper,
        audit_writer: "AuditWriter",
        *,
        max_turns: int = 30,
        commit_threshold: float = 0.70,
        safety_checker: SafetyChecker | None = None,
    ) -> SequentialResult:
        """Multi-turn sequential diagnosis with Gatekeeper + audit + safety.

        Per turn:
          1. Hypothesis refines its posterior given accumulated evidence.
          2. TestChooser proposes the next query (NextTest.name).
          3. Gatekeeper reveals (or refuses) the requested finding.
          4. Challenger + Stewardship + Checklist react to the new evidence.
          5. SafetyChecker evaluates commit conditions.
          6. If safety clean and commit signal raised → commit, return.

        Commit signals (any one is sufficient before safety check):
          - top posterior >= commit_threshold
          - Stewardship `accept_test` is False (vote stop)
          - Checklist `recommend_continue` is False AND `consistent` is True
            (panel says enough, no flagged inconsistencies)

        If the loop exhausts max_turns, a final commit is forced on the
        current top diagnosis (forced=True).
        """
        from quorum.eval.eval_case import Finding  # local import to avoid cycle

        # Require the full 5-agent panel; bail early if any slot is missing.
        for slot_name in ("hypothesis", "test_chooser", "challenger", "stewardship", "checklist"):
            if getattr(self, slot_name) is None:
                raise ValueError(
                    f"run_sequential requires all 5 agents; missing slot: {slot_name}"
                )

        safety = safety_checker or SafetyChecker()
        revealed: list[Finding] = []
        transcript: list[AgentMessage] = []
        total_real_cost = 0.0
        last_posterior: dict[str, float] = {}
        # Cap how much panel transcript is fed back into each agent each
        # turn. The full available_findings are always in case.presentation;
        # the transcript is just the panel's prior reasoning. Capping to the
        # most recent N messages keeps prompts cheap and avoids latent
        # validation failures from oversized context.
        TRANSCRIPT_TAIL = 5

        for turn in range(1, max_turns + 1):
            case_input = self._build_sequential_case_input(case, revealed)
            iteration = turn - 1
            tail = transcript[-TRANSCRIPT_TAIL:]

            # ----- Hypothesis -----
            try:
                hyp_msg = await self.hypothesis.deliberate(case_input, list(tail), iteration)
            except Exception as exc:  # noqa: BLE001 — per-turn resilience
                audit_writer.record_turn(
                    agent="hypothesis", message_role="out",
                    content=f"(error: {exc.__class__.__name__}: {exc})",
                    extra={"error": True, "iteration": iteration},
                )
                # Reuse last_posterior so the loop can continue.
                if last_posterior:
                    continue
                # No prior posterior to fall back on — bail.
                return self._finalize_forced(
                    case, audit_writer, last_posterior, turn,
                    gatekeeper.simulated_cost, total_real_cost, revealed,
                    reason=f"hypothesis failed: {exc}",
                )
            transcript.append(hyp_msg)
            total_real_cost += hyp_msg.cost_usd
            if isinstance(hyp_msg.structured_output, Differential):
                posterior = hyp_msg.structured_output.as_posterior_dict()
            else:
                posterior = {}
            last_posterior = posterior
            audit_writer.record_turn(
                agent="hypothesis",
                message_role="out",
                content=hyp_msg.content,
                tokens=hyp_msg.tokens_used,
                cost_usd=hyp_msg.cost_usd,
                posterior_at_turn=posterior,
            )

            # ----- TestChooser -----
            try:
                tc_msg = await self.test_chooser.deliberate(case_input, list(tail), iteration)
                transcript.append(tc_msg)
                total_real_cost += tc_msg.cost_usd
                query = (
                    tc_msg.structured_output.name
                    if tc_msg.structured_output is not None
                    and hasattr(tc_msg.structured_output, "name")
                    else ""
                )
            except Exception as exc:  # noqa: BLE001
                audit_writer.record_turn(
                    agent="test_chooser", message_role="out",
                    content=f"(error: {exc.__class__.__name__}: {exc})",
                    extra={"error": True},
                )
                query = ""  # let Gatekeeper return "not available"
                tc_msg = None
            audit_writer.record_turn(
                agent="test_chooser",
                message_role="out",
                content=tc_msg.content,
                tokens=tc_msg.tokens_used,
                cost_usd=tc_msg.cost_usd,
                extra={"query": query},
            )

            # ----- Gatekeeper -----
            audit_writer.record_turn(
                agent="gatekeeper",
                message_role="gatekeeper_query",
                content=query,
            )
            try:
                gk_response = await gatekeeper.query(query)
            except RuntimeError as exc:
                # Gatekeeper guard hit (max turns or max cost). Force-commit.
                audit_writer.record_turn(
                    agent="gatekeeper",
                    message_role="gatekeeper_response",
                    content=f"halted: {exc}",
                    extra={"halted": True},
                )
                return self._finalize_forced(
                    case, audit_writer, last_posterior, turn, gatekeeper.simulated_cost,
                    total_real_cost, revealed, reason=str(exc),
                )
            audit_writer.record_turn(
                agent="gatekeeper",
                message_role="gatekeeper_response",
                content=gk_response.content,
                cost_usd=gk_response.cost_usd,
                extra={
                    "matched": gk_response.matched,
                    "matched_label": gk_response.matched_label,
                },
            )
            if gk_response.matched:
                revealed.append(
                    Finding(
                        category="revealed",
                        label=gk_response.matched_label or "(unknown)",
                        content=gk_response.content,
                    )
                )

            # ----- Challenger -----
            try:
                chal_msg = await self.challenger.deliberate(case_input, list(tail), iteration)
                transcript.append(chal_msg)
                total_real_cost += chal_msg.cost_usd
                chal_dict = chal_msg.structured_output if isinstance(chal_msg.structured_output, dict) else {}
            except Exception as exc:  # noqa: BLE001
                audit_writer.record_turn(
                    agent="challenger", message_role="out",
                    content=f"(error: {exc.__class__.__name__}: {exc})",
                    extra={"error": True},
                )
                chal_dict = {"alternative_to_consider": "none", "against_top_candidate": [], "confidence_in_challenge": 0.0}
                chal_msg = None
            audit_writer.record_turn(
                agent="challenger",
                message_role="out",
                content=chal_msg.content,
                tokens=chal_msg.tokens_used,
                cost_usd=chal_msg.cost_usd,
                extra=dict(chal_dict),
            )

            # ----- Stewardship -----
            try:
                stew_msg = await self.stewardship.deliberate(case_input, list(tail), iteration)
                transcript.append(stew_msg)
                total_real_cost += stew_msg.cost_usd
                stew_dict = stew_msg.structured_output if isinstance(stew_msg.structured_output, dict) else {}
            except Exception as exc:  # noqa: BLE001
                audit_writer.record_turn(
                    agent="stewardship", message_role="out",
                    content=f"(error: {exc.__class__.__name__}: {exc})",
                    extra={"error": True},
                )
                stew_dict = {"accept_test": True, "cost_concern": None, "cheaper_alternative": None}
                stew_msg = None
            audit_writer.record_turn(
                agent="stewardship",
                message_role="out",
                content=stew_msg.content,
                tokens=stew_msg.tokens_used,
                cost_usd=stew_msg.cost_usd,
                extra={k: v for k, v in stew_dict.items() if k != "cheaper_alternative"},
            )

            # ----- Checklist -----
            try:
                chk_msg = await self.checklist.deliberate(case_input, list(tail), iteration)
                transcript.append(chk_msg)
                total_real_cost += chk_msg.cost_usd
                chk_dict = chk_msg.structured_output if isinstance(chk_msg.structured_output, dict) else {}
            except Exception as exc:  # noqa: BLE001
                audit_writer.record_turn(
                    agent="checklist", message_role="out",
                    content=f"(error: {exc.__class__.__name__}: {exc})",
                    extra={"error": True},
                )
                chk_dict = {"consistent": True, "flags": [], "recommend_continue": True}
                chk_msg = None
            audit_writer.record_turn(
                agent="checklist",
                message_role="out",
                content=chk_msg.content,
                tokens=chk_msg.tokens_used,
                cost_usd=chk_msg.cost_usd,
                extra=dict(chk_dict),
            )

            # ----- Commit decision -----
            if not posterior:
                continue
            top_dx = max(posterior, key=posterior.get)
            top_p = posterior[top_dx]

            stew_accept = stew_dict.get("accept_test", True)
            chk_continue = chk_dict.get("recommend_continue", True)
            chk_consistent = chk_dict.get("consistent", True)
            chk_flags = chk_dict.get("flags", [])
            chal_alt = chal_dict.get("alternative_to_consider", "none")

            commit_signal = (
                top_p >= commit_threshold
                or stew_accept is False
                or (chk_continue is False and chk_consistent is True)
            )

            if commit_signal:
                verdict = safety.check_commit(
                    committed_dx=top_dx,
                    hypothesis_shortlist=posterior,
                    challenger_top=chal_alt,
                    checklist_concerns=list(chk_flags),
                    n_findings_queried=len(revealed),
                    simulated_cost=gatekeeper.simulated_cost,
                )
                audit_writer.record_turn(
                    agent="safety_checker",
                    message_role="safety_check",
                    content=verdict.reason or "OK",
                    extra={"blocked": verdict.blocked, "forced": verdict.forced},
                )
                if not verdict.blocked:
                    audit_writer.set_final(
                        committed_diagnosis=top_dx,
                        final_posterior=posterior,
                        real_cost_usd=total_real_cost,
                        simulated_cost_usd=gatekeeper.simulated_cost,
                    )
                    return SequentialResult(
                        case_id=case.case_id,
                        committed_diagnosis=top_dx,
                        final_posterior=posterior,
                        n_turns=turn,
                        simulated_cost_usd=gatekeeper.simulated_cost,
                        real_cost_usd=total_real_cost,
                        forced=verdict.forced,
                        revealed_findings=[f.label for f in revealed],
                    )
            # otherwise: continue to next turn

        # Loop exhausted → force commit on current top
        return self._finalize_forced(
            case, audit_writer, last_posterior, max_turns, gatekeeper.simulated_cost,
            total_real_cost, revealed, reason="max turns reached",
        )

    def _build_sequential_case_input(self, case: "EvalCase", revealed: list) -> CaseInput:
        presentation = case.initial_presentation
        if revealed:
            lines = ["", "## Revealed findings"]
            for f in revealed:
                lines.append(f"- ({f.category}) {f.label}: {f.content}")
            presentation = presentation + "\n" + "\n".join(lines)
        return CaseInput(
            case_id=case.case_id,
            presentation=presentation,
            max_iterations=1,
        )

    def _finalize_forced(
        self,
        case: "EvalCase",
        audit_writer: "AuditWriter",
        posterior: dict[str, float],
        n_turns: int,
        simulated_cost: float,
        real_cost: float,
        revealed: list,
        *,
        reason: str,
    ) -> SequentialResult:
        top_dx = max(posterior, key=posterior.get) if posterior else "(no diagnosis)"
        audit_writer.record_turn(
            agent="safety_checker",
            message_role="safety_check",
            content=f"{reason}: forced commit on {top_dx!r}",
            extra={"blocked": False, "forced": True},
        )
        audit_writer.set_final(
            committed_diagnosis=top_dx,
            final_posterior=posterior,
            real_cost_usd=real_cost,
            simulated_cost_usd=simulated_cost,
        )
        return SequentialResult(
            case_id=case.case_id,
            committed_diagnosis=top_dx,
            final_posterior=posterior,
            n_turns=n_turns,
            simulated_cost_usd=simulated_cost,
            real_cost_usd=real_cost,
            forced=True,
            revealed_findings=[f.label for f in revealed],
        )

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
