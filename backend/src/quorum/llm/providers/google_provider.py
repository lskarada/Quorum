"""Google provider — wraps `google-genai` SDK for Gemini 2.5 Pro."""
from __future__ import annotations

from typing import AsyncIterator

from quorum.llm.client import LLMResponse


class GoogleProvider:
    """Thin wrapper around the google-genai Python SDK."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        # TODO: instantiate the genai client lazily

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
