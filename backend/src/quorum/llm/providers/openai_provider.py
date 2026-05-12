"""OpenAI provider — wraps `openai` SDK."""
from __future__ import annotations

from typing import AsyncIterator

from quorum.llm.client import LLMResponse


class OpenAIProvider:
    """Thin wrapper around the official openai Python SDK for GPT-5 family."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        # TODO: instantiate AsyncOpenAI client lazily

    async def complete(
        self,
        messages: list[dict],
        model: str,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        # TODO
        raise NotImplementedError

    async def stream(
        self,
        messages: list[dict],
        model: str,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        # TODO
        raise NotImplementedError
        yield
