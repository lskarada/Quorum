"""Base class for deliberation agents.

All five specialist agents (Hypothesis, Test-Chooser, Challenger, Stewardship,
Checklist) inherit from this. Each agent reads the running transcript and
emits an AgentMessage with structured output appropriate to its role.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path

from quorum.llm.client import LLMClient
from quorum.orchestrator.schemas import AgentMessage, AgentRole, CaseInput

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class Agent(ABC):
    """Abstract specialist agent."""

    role: AgentRole

    def __init__(
        self,
        llm: LLMClient,
        model: str | None = None,
        temperature: float | None = None,
    ):
        self.llm = llm
        self.model = model  # None → llm.default_model is used by self.llm.complete
        self.temperature = temperature  # None → API default; configs set 0.0
        self._prompt_template: str | None = None

    @property
    def prompt_template(self) -> str:
        """Lazy-load the prompt template from disk on first access."""
        if self._prompt_template is None:
            path = PROMPTS_DIR / f"{self.role.value}.md"
            self._prompt_template = path.read_text(encoding="utf-8")
        return self._prompt_template

    @abstractmethod
    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        """Produce this agent's contribution to the current round.

        Args:
            case: The original case input.
            transcript: All messages from prior rounds, in order.
            iteration: Current iteration index (0-based).

        Returns:
            An AgentMessage with role==self.role and structured_output
            appropriate to this agent type.
        """
        ...

    @abstractmethod
    async def deliberate_stream(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AsyncIterator[str]:
        """Streaming version. Yields token deltas as the agent thinks."""
        ...
