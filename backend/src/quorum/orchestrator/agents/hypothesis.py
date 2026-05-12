"""Dr. Hypothesis — maintains the ranked differential diagnosis."""
from __future__ import annotations

from typing import AsyncIterator

from quorum.orchestrator.agents.base import Agent
from quorum.orchestrator.schemas import AgentMessage, AgentRole, CaseInput


class HypothesisAgent(Agent):
    """Proposes and refines a ranked differential.

    Output contract: structured_output is a Differential containing 3–7
    DiagnosisCandidate entries with posteriors summing to ~1.0, each with
    supporting/against findings and at least one citation when possible.
    """

    role = AgentRole.HYPOTHESIS

    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        # TODO: build LLM messages from prompt_template + case + transcript;
        # call self.llm.complete() with JSON response_format; parse into
        # Differential; wrap in AgentMessage; return.
        raise NotImplementedError

    async def deliberate_stream(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AsyncIterator[str]:
        # TODO: same as deliberate() but use self.llm.stream() and yield deltas.
        raise NotImplementedError
        yield  # unreachable; keeps mypy happy about AsyncIterator return type
