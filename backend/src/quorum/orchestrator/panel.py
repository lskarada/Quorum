"""The deliberation orchestrator.

The Panel runs all five agents through N iterations, with a loop:
    for iteration in range(max_iter):
        hypothesis = await Hypothesis.deliberate(...)
        test = await TestChooser.deliberate(...)
        challenge = await Challenger.deliberate(...)
        steward = await Stewardship.deliberate(...)
        check = await Checklist.deliberate(...)
        if consensus_reached(transcript): break
        if budget_exhausted(transcript, budget): break
    return synthesize_verdict(transcript)
"""
from __future__ import annotations

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
    FinalVerdict,
    StreamEvent,
)


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
        """Run synchronous deliberation. Returns final verdict."""
        # TODO: implement the deliberation loop
        # 1. For iteration in range(case.max_iterations):
        # 2.   Each agent produces its message in sequence
        # 3.   After Checklist, evaluate consensus_reached()
        # 4.   Check budget
        # 5.   If terminate: break
        # 6. Synthesize FinalVerdict from final transcript
        raise NotImplementedError

    async def diagnose_stream(
        self, case: CaseInput
    ) -> AsyncIterator[StreamEvent]:
        """Streaming deliberation. Yields SSE events for the frontend."""
        # TODO: same loop as diagnose(), but emit StreamEvents at:
        #   - agent_start (when each agent begins)
        #   - agent_token (per token delta during streaming)
        #   - agent_complete (when an agent's message is finalized)
        #   - round_complete (end of each iteration)
        #   - verdict (final)
        raise NotImplementedError
        yield  # unreachable; keeps mypy happy about AsyncIterator return type

    def _consensus_reached(self, transcript: list[AgentMessage]) -> bool:
        """Has the panel converged? True if the top differential candidate is
        stable across the last 2 iterations AND Checklist flags no consistency
        issues."""
        # TODO
        raise NotImplementedError

    def _synthesize_verdict(
        self, case: CaseInput, transcript: list[AgentMessage], reason: str
    ) -> FinalVerdict:
        """Build the FinalVerdict from the transcript."""
        # TODO
        raise NotImplementedError
