"""Unified LLM client abstracting over Anthropic, OpenAI, and Google."""
from __future__ import annotations

from typing import AsyncIterator, Literal

from pydantic import BaseModel


ModelName = Literal[
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "gpt-5",
    "gpt-5-mini",
    "gemini-2.5-pro",
]


class LLMResponse(BaseModel):
    content: str
    tokens_used: int
    cost_usd: float
    model: str


class LLMClient:
    """Unified async client. Picks the right provider based on model name."""

    def __init__(self, default_model: ModelName = "claude-opus-4-7"):
        self.default_model = default_model
        # TODO: initialize provider clients lazily

    async def complete(
        self,
        messages: list[dict],
        model: ModelName | None = None,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Non-streaming completion."""
        # TODO: route to correct provider; aggregate usage + cost
        raise NotImplementedError

    async def stream(
        self,
        messages: list[dict],
        model: ModelName | None = None,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Streaming completion. Yields token deltas."""
        # TODO
        raise NotImplementedError
        yield  # keeps mypy happy
