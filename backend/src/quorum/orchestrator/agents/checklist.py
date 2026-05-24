"""Dr. Checklist — verifies internal consistency of the panel's reasoning."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

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
        system = self.prompt_template
        user_parts: list[str] = [f"# Case\n{case.presentation}"]
        if transcript:
            user_parts.append("# Panel transcript so far")
            for m in transcript:
                user_parts.append(f"## {m.role.value}\n{m.content}")
        user_parts.append(f"# Current iteration\n{iteration}")
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]
        resp = await self.llm.complete(
            messages=messages,
            model=self.model,
            response_format={"type": "json_object"},
            max_tokens=2048,
        )
        data: Any = json.loads(resp.content)

        # Validate dict shape per output contract.
        if not isinstance(data, dict):
            raise ValueError("checklist output must be a JSON object")
        if "consistent" not in data or not isinstance(data["consistent"], bool):
            raise ValueError("consistent must be a boolean")
        flags = data.get("flags")
        if not isinstance(flags, list) or not all(isinstance(x, str) for x in flags):
            raise ValueError("flags must be a list of strings")
        if "recommend_continue" not in data or not isinstance(data["recommend_continue"], bool):
            raise ValueError("recommend_continue must be a boolean")

        if data["consistent"]:
            content = "OK"
        else:
            content = f"Flagged: {len(flags)} issues"

        return AgentMessage(
            role=self.role,
            iteration=iteration,
            content=content,
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
