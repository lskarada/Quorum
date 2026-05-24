"""Unified LLM client routed through OpenRouter (OpenAI-SDK-compatible)."""
from __future__ import annotations

import os
import json
import pathlib
import sys
from collections.abc import AsyncIterator
from datetime import datetime

from openai import AsyncOpenAI
from pydantic import BaseModel


_SPEND_FILE = pathlib.Path.home() / ".quorum" / "spend.json"


def _track_spend(cost_usd: float) -> None:
    """Persist cumulative spend; raise if over cap, warn at 67% of cap.

    Reads QUORUM_TOTAL_SPEND_LIMIT_USD env var (default very high).
    Writes to _SPEND_FILE (~/.quorum/spend.json by default).
    Survives across processes — multiple agent calls, eval runs, MCP calls
    all share one cumulative total.
    """
    cap = float(os.environ.get("QUORUM_TOTAL_SPEND_LIMIT_USD", "999"))
    _SPEND_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _SPEND_FILE.exists():
        data = json.loads(_SPEND_FILE.read_text())
    else:
        data = {"total": 0.0, "since": datetime.utcnow().isoformat()}
    data["total"] = float(data.get("total", 0.0)) + float(cost_usd)
    _SPEND_FILE.write_text(json.dumps(data, indent=2))
    if data["total"] >= cap:
        raise RuntimeError(
            f"Hit cumulative spend cap ${cap:.2f} (now ${data['total']:.4f}). "
            f"Reset: rm {_SPEND_FILE}"
        )
    soft = 0.67 * cap
    if data["total"] >= soft:
        print(
            f"⚠ Spend alert: ${data['total']:.2f} of ${cap:.2f} "
            f"({100 * data['total'] / cap:.0f}%)",
            file=sys.stderr,
        )


class LLMResponse(BaseModel):
    content: str
    tokens_used: int
    cost_usd: float
    model: str


class LLMClient:
    """OpenRouter-routed LLM client.

    Model names are OpenRouter vendor-prefixed strings:
        anthropic/claude-opus-4
        openai/gpt-4o
        google/gemini-2.5-pro
        meta-llama/llama-3.3-70b-instruct
        mistralai/mistral-small-3.1-24b-instruct
    """

    def __init__(self, default_model: str = "anthropic/claude-opus-4"):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set. See .env.example."
            )
        base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        extra_headers = {}
        if site := os.environ.get("OPENROUTER_SITE_URL"):
            extra_headers["HTTP-Referer"] = site
        if app := os.environ.get("OPENROUTER_APP_NAME"):
            extra_headers["X-Title"] = app

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=extra_headers or None,
        )
        self.default_model = default_model

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        r = await self._client.chat.completions.create(**kwargs)
        usage = r.usage
        cost = getattr(usage, "cost", 0.0) or 0.0
        _track_spend(cost)
        return LLMResponse(
            content=r.choices[0].message.content or "",
            tokens_used=getattr(usage, "total_tokens", 0) or 0,
            cost_usd=float(cost),
            model=r.model,
        )

    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        kwargs: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        async for chunk in await self._client.chat.completions.create(**kwargs):
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
