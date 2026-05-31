"""Dr. Challenger — attacks the leading hypothesis."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from quorum.orchestrator.agents.base import Agent
from quorum.orchestrator.schemas import AgentMessage, AgentRole, CaseInput


class ChallengerAgent(Agent):
    """Adversarial role: surfaces evidence against the top candidate.

    Output contract: structured_output is a dict with keys
    `against_top_candidate` (list of findings), `alternative_to_consider`
    (DiagnosisCandidate name or "none"), and `confidence_in_challenge` (0-1).
    """

    role = AgentRole.CHALLENGER

    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        system = self.prompt_template
        user_parts: list[str] = [f"# Case\n{case.presentation}"]
        if transcript:
            user_parts.append("# Panel transcript so far")
            for m in transcript:
                user_parts.append(f"## {m.role.value}\n{m.content}")
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]
        resp = await self.llm.complete(
            messages=messages,
            model=self.model,
            response_format={"type": "json_object"},
            max_tokens=2048,
            temperature=self.temperature,
        )
        data: Any = json.loads(resp.content)

        # Validate dict shape per output contract.
        if not isinstance(data, dict):
            raise ValueError("challenger output must be a JSON object")
        against = data.get("against_top_candidate")
        if not isinstance(against, list) or not all(isinstance(x, str) for x in against):
            raise ValueError("against_top_candidate must be a list of strings")
        alternative = data.get("alternative_to_consider")
        if not isinstance(alternative, str):
            raise ValueError("alternative_to_consider must be a string")
        confidence = data.get("confidence_in_challenge")
        if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
            raise ValueError("confidence_in_challenge must be a number in [0.0, 1.0]")
        data["confidence_in_challenge"] = float(confidence)

        return AgentMessage(
            role=self.role,
            iteration=iteration,
            content=(
                f"Challenge: {data['alternative_to_consider']} "
                f"(confidence={data['confidence_in_challenge']:.2f})"
            ),
            structured_output=data,
            tokens_used=resp.tokens_used,
            cost_usd=resp.cost_usd,
        )

    async def deliberate_stream(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # unreachable; keeps mypy happy
