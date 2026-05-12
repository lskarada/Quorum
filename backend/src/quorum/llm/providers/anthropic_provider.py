"""Anthropic provider — wraps `anthropic` SDK."""
from __future__ import annotations

from typing import AsyncIterator

from quorum.llm.client import LLMResponse


class AnthropicProvider:
    """Thin wrapper around the official anthropic Python SDK.

    Handles message format translation, token counting, and cost computation
    for Claude Opus 4.7 and Claude Sonnet 4.6.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        # TODO: instantiate AsyncAnthropic client lazily

    async def complete(
        self,
        messages: list[dict],
        model: str,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        # TODO: call self._client.messages.create(...) and wrap.
        raise NotImplementedError

    async def stream(
        self,
        messages: list[dict],
        model: str,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        # TODO: call self._client.messages.stream(...) and yield content deltas.
        raise NotImplementedError
        yield
