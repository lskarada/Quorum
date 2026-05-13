"""Cloudflare Workers AI provider.

HTTP-only — no Python SDK required, just the existing `httpx` dependency.
Hosts open-source models (Llama, Mistral) for the "open panel" comparison
arm of Quorum's eval.

Routing:
    Default base URL:
        https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run

    With AI Gateway (if `CLOUDFLARE_AI_GATEWAY_URL` is set):
        {CLOUDFLARE_AI_GATEWAY_URL}/workers-ai

    The Gateway URL adds caching, observability, rate-limit dashboards, and
    automatic fallback. It costs nothing extra and is strongly recommended
    for eval runs.

Auth:
    Authorization: Bearer {CLOUDFLARE_API_TOKEN}

Model slug translation (user-facing name → Cloudflare catalog slug):
    "llama-3.3-70b-instruct"           → "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    "mistral-small-3.1-24b-instruct"   → "@cf/mistralai/mistral-small-3.1-24b-instruct"

Cost cap reminder: $50K Workers AI cap inside the $100K Cloudflare for Startups
total. At Quorum's expected eval volume (304 cases × 5 agents × ~5 iterations
≈ 7,600 calls) this is comfortably under the cap.
"""
from __future__ import annotations

from typing import AsyncIterator

from quorum.llm.client import LLMResponse


# Map Quorum's user-facing ModelName values to Cloudflare's catalog slugs.
# Kept here so it's a single source of truth and easy to extend.
CF_MODEL_SLUG: dict[str, str] = {
    "llama-3.3-70b-instruct": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "mistral-small-3.1-24b-instruct": "@cf/mistralai/mistral-small-3.1-24b-instruct",
}


class WorkersAIProvider:
    """Thin async wrapper over Cloudflare Workers AI's `/ai/run/{slug}` HTTP API."""

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        gateway_url: str | None = None,
    ):
        self.account_id = account_id
        self.api_token = api_token
        self.gateway_url = gateway_url
        # TODO: instantiate an httpx.AsyncClient lazily; resolve base URL from
        # gateway_url if present, else fall back to the canonical /accounts/{id}/ai/run.

    async def complete(
        self,
        messages: list[dict],
        model: str,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        # TODO: translate `model` via CF_MODEL_SLUG; POST {messages,max_tokens}
        # to {base_url}/{slug}; parse the response into LLMResponse with
        # cost_usd computed from the model's per-token pricing.
        raise NotImplementedError

    async def stream(
        self,
        messages: list[dict],
        model: str,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        # TODO: same as complete() but set `stream: true` in the payload and
        # consume Server-Sent Events back; yield content deltas.
        raise NotImplementedError
        yield  # unreachable; keeps mypy happy about AsyncIterator return type
