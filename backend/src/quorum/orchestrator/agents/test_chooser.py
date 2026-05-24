"""TestChooserAgent — recommends the next diagnostic test."""
from __future__ import annotations

import json
from typing import AsyncIterator

from quorum.orchestrator.agents.base import Agent
from quorum.orchestrator.schemas import AgentMessage, AgentRole, CaseInput, NextTest


class TestChooserAgent(Agent):
    """Selects the next test that maximally discriminates between top candidates."""

    role = AgentRole.TEST_CHOOSER
    __test__ = False  # pytest discovery: not a test class despite "Test" prefix

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
            response_format={"type": "json_object"},
            max_tokens=2048,
        )
        data = json.loads(resp.content)
        next_test = NextTest.model_validate(data)
        return AgentMessage(
            role=self.role,
            iteration=iteration,
            content=f"Recommend: {next_test.name} — {next_test.rationale}",
            structured_output=next_test,
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
