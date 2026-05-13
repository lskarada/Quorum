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
    # Cloudflare Workers AI (open-source). Slugs translated to "@cf/..."
    # inside WorkersAIProvider.CF_MODEL_SLUG.
    "llama-3.3-70b-instruct",
    "mistral-small-3.1-24b-instruct",
]


class LLMResponse(BaseModel):
    content: str
    tokens_used: int
    cost_usd: float
    model: str


class LLMClient:
    """Unified async client. Picks the right provider based on model name.

    Provider routing (by model-name prefix):
        claude-*    → AnthropicProvider
        gpt-*       → OpenAIProvider
        gemini-*    → GoogleProvider
        llama-*, mistral-*  → WorkersAIProvider (Cloudflare Workers AI)

    When `CLOUDFLARE_AI_GATEWAY_URL` is set, ALL four providers can be
    routed through it for caching/observability/fallback. Each provider's
    base URL becomes `{gateway}/{provider-name}` instead of the SDK default.
    See docs/architecture.md for the gateway data-flow diagram.
    """

    def __init__(self, default_model: ModelName = "claude-opus-4-7"):
        self.default_model = default_model
        # TODO: initialize provider clients lazily; honor CLOUDFLARE_AI_GATEWAY_URL
        # by passing it into every provider's `gateway_url` kwarg when present.

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
