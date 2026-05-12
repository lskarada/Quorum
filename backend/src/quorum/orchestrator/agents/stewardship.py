"""Dr. Stewardship — enforces cost-aware reasoning."""
from __future__ import annotations

from typing import AsyncIterator

from quorum.orchestrator.agents.base import Agent
from quorum.orchestrator.schemas import AgentMessage, AgentRole, CaseInput


class StewardshipAgent(Agent):
    """Cost-aware reviewer: flags tests that exceed reasonable cost-per-bit.

    Output contract: structured_output is a dict with keys `accept_test`
    (bool), `cost_concern` (str | None), and `cheaper_alternative` (NextTest |
    None).
    """

    role = AgentRole.STEWARDSHIP

    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        # TODO: read latest NextTest from transcript; compare to case.budget_usd
        # if set; surface cost concerns and propose alternatives.
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
