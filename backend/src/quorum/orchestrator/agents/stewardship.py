"""Dr. Stewardship — enforces cost-aware reasoning."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from quorum.orchestrator.agents.base import Agent
from quorum.orchestrator.schemas import AgentMessage, AgentRole, CaseInput, NextTest


class StewardshipAgent(Agent):
    """Cost-aware reviewer: flags tests that exceed reasonable cost-per-bit.

    Output contract: structured_output is a dict with keys `accept_test`
    (bool), `cost_concern` (str | None), and `cheaper_alternative` (NextTest
    dict | None).
    """

    role = AgentRole.STEWARDSHIP

    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        system = self.prompt_template
        user_parts: list[str] = [f"# Case\n{case.presentation}"]
        if case.budget_usd is not None:
            user_parts.append(f"# Budget\n${case.budget_usd:.2f} USD")
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
        )
        data: Any = json.loads(resp.content)

        # Validate dict shape per output contract.
        if not isinstance(data, dict):
            raise ValueError("stewardship output must be a JSON object")
        if "accept_test" not in data or not isinstance(data["accept_test"], bool):
            raise ValueError("accept_test must be a boolean")
        cost_concern = data.get("cost_concern")
        if cost_concern is not None and not isinstance(cost_concern, str):
            raise ValueError("cost_concern must be a string or null")
        cheaper = data.get("cheaper_alternative")
        if cheaper is not None:
            # Validate as a NextTest dict but keep structured_output as plain dict.
            validated = NextTest.model_validate(cheaper)
            data["cheaper_alternative"] = validated.model_dump()

        accept = data["accept_test"]
        if accept:
            content = "Test accepted"
        else:
            content = f"Test rejected: {data.get('cost_concern')}"

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
