"""Dr. Challenger — attacks the leading hypothesis."""
from __future__ import annotations

from typing import AsyncIterator

from quorum.orchestrator.agents.base import Agent
from quorum.orchestrator.schemas import AgentMessage, AgentRole, CaseInput


class ChallengerAgent(Agent):
    """Adversarial role: surfaces evidence against the top candidate.

    Output contract: structured_output is a dict with keys
    `against_top_candidate` (list of findings), `alternative_to_consider`
    (DiagnosisCandidate name), and `confidence_in_challenge` (0–1).
    """

    role = AgentRole.CHALLENGER

    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        # TODO: ask the LLM what's WRONG with the current top candidate;
        # parse into the dict shape described above.
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
