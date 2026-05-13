"""Dr. Hypothesis — maintains the ranked differential diagnosis."""
from __future__ import annotations

import json
from typing import AsyncIterator

from quorum.orchestrator.agents.base import Agent
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    CaseInput,
    Differential,
)

_MIN_CANDIDATES = 3
_MAX_CANDIDATES = 7
_POSTERIOR_SUM_TOLERANCE = (0.95, 1.05)


class HypothesisAgent(Agent):
    """Proposes and refines a ranked differential.

    Output contract: structured_output is a `Differential` containing 3-7
    DiagnosisCandidate entries with posteriors summing to ~1.0 (auto-normalized
    when outside 0.95..1.05; raises on degenerate sum=0).
    """

    role = AgentRole.HYPOTHESIS

    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        if not case.presentation.strip():
            raise ValueError("presentation must be non-empty")

        messages = self._build_messages(case, transcript, iteration)
        response = await self.llm.complete(
            messages=messages,
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(response.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned malformed JSON: {e}") from e

        candidates = data.get("candidates", [])
        if not _MIN_CANDIDATES <= len(candidates) <= _MAX_CANDIDATES:
            raise ValueError(
                f"expected {_MIN_CANDIDATES}-{_MAX_CANDIDATES} candidates, "
                f"got {len(candidates)}"
            )

        differential = Differential.model_validate({**data, "iteration": iteration})
        differential = self._normalize_posteriors(differential)

        return AgentMessage(
            role=AgentRole.HYPOTHESIS,
            iteration=iteration,
            content=response.content,
            structured_output=differential,
            tokens_used=response.tokens_used,
            cost_usd=response.cost_usd,
        )

    def _build_messages(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> list[dict]:
        msgs: list[dict] = [
            {"role": "system", "content": self.prompt_template},
            {
                "role": "user",
                "content": (
                    f"Case presentation:\n{case.presentation}\n\n"
                    f"Iteration: {iteration}"
                ),
            },
        ]
        for prior in transcript:
            msgs.append({"role": "assistant", "content": prior.content})
        return msgs

    @staticmethod
    def _normalize_posteriors(diff: Differential) -> Differential:
        total = sum(c.posterior for c in diff.candidates)
        if total == 0:
            raise ValueError("posteriors sum to 0; degenerate differential")
        low, high = _POSTERIOR_SUM_TOLERANCE
        if low <= total <= high:
            return diff
        normalized = [
            c.model_copy(update={"posterior": c.posterior / total})
            for c in diff.candidates
        ]
        return diff.model_copy(update={"candidates": normalized})

    async def deliberate_stream(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # unreachable; keeps mypy happy about AsyncIterator return type
