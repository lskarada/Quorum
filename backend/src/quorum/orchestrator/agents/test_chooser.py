"""Dr. Test-Chooser — selects the most informative next diagnostic test."""
from __future__ import annotations

from typing import AsyncIterator

from quorum.orchestrator.agents.base import Agent
from quorum.orchestrator.schemas import AgentMessage, AgentRole, CaseInput


class TestChooserAgent(Agent):
    """Picks the next test that maximally discriminates between top candidates.

    Output contract: structured_output is a NextTest with rationale,
    estimated_cost_usd (if available), and discriminates_between listing
    the DiagnosisCandidate names the test separates.
    """

    role = AgentRole.TEST_CHOOSER
    __test__ = False  # pytest discovery: not a test class despite "Test" prefix

    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        # TODO: read the latest Differential from transcript; ask the LLM for
        # the cheapest test that maximizes expected information gain across
        # the top-2 or top-3 candidates; parse into NextTest.
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
