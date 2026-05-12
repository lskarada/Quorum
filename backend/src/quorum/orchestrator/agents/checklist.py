"""Dr. Checklist — verifies internal consistency of the panel's reasoning."""
from __future__ import annotations

from typing import AsyncIterator

from quorum.orchestrator.agents.base import Agent
from quorum.orchestrator.schemas import AgentMessage, AgentRole, CaseInput


class ChecklistAgent(Agent):
    """Consistency auditor: flags contradictions within the panel.

    Output contract: structured_output is a dict with keys `consistent`
    (bool), `flags` (list[str] — specific contradictions found), and
    `recommend_continue` (bool — should the panel keep iterating).
    """

    role = AgentRole.CHECKLIST

    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        # TODO: scan the full transcript for contradictions between agents
        # (e.g., Test-Chooser picks test that Stewardship rejects); produce
        # the flag list.
        raise NotImplementedError

    async def deliberate_stream(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AsyncIterator[str]:
        # TODO: streaming variant.
        raise NotImplementedError
        yield
