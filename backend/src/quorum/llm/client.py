"""Unified LLM client routed through OpenRouter (OpenAI-SDK-compatible)."""
from __future__ import annotations

import json
import os
import pathlib
import re
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


# Triple-backtick fence with an optional language tag (json/JSON/Json/etc).
# Case-insensitive so ```Json, ```JSON, ```json all strip cleanly.
_FENCE_OPEN_RE = re.compile(r"^```[A-Za-z0-9_+\-]*\s*\n?", flags=re.IGNORECASE)
_FENCE_CLOSE_RE = re.compile(r"\n?```\s*$")


def _strip_json_fence(content: str) -> str:
    """Strip ```json ... ``` markdown fences some models wrap JSON in.

    Anthropic models routed through OpenRouter often wrap structured output
    in triple-backtick fences even when response_format={"type":"json_object"}
    is set, because Anthropic's API doesn't natively support OpenAI-style JSON
    mode. The fence may carry any case of the json language tag (```Json,
    ```JSON, ```json, ```) or no tag at all. Stripping defensively here lets
    every agent's json.loads succeed.
    """
    s = content.strip()
    if not s.startswith("```"):
        return content
    s = _FENCE_OPEN_RE.sub("", s, count=1)
    s = _FENCE_CLOSE_RE.sub("", s)
    return s.strip()


def _normalize_json_content(content: str) -> str:
    """Normalize LLM JSON output: strip markdown fence + take first JSON value.

    Coercion order:
      1. Strip surrounding ``` fences (any case of lang tag, or none).
      2. If content starts with a JSON value, raw_decode it and discard
         trailing prose ("Extra data" tolerance).
      3. Otherwise scan for the first '{' / '[' and try raw_decode from
         there — handles prose preambles ("Here is the JSON: {...}"),
         XML-style wrappers (<json>{...}</json>), and reasoning blocks
         (<thinking>...</thinking>\n{...}).

    If no valid JSON value is found, returns the (fence-stripped) content
    unchanged so the agent's downstream error path can surface a malformed-
    output failure honestly. This is the intended fallback for refusals
    and empty responses — coercion is silent-best-effort, never silent-fix.
    """
    s = _strip_json_fence(content)
    s = s.lstrip()
    if not s:
        return s
    decoder = json.JSONDecoder()
    # Fast path: content already starts with a JSON value.
    if s[0] in "{[":
        try:
            value, _end = decoder.raw_decode(s)
            return json.dumps(value)
        except json.JSONDecodeError:
            pass
    # Fallback: scan for the first plausible JSON start and try every
    # candidate position. Each '{' or '[' is a candidate; raw_decode will
    # bail on the bad ones and succeed on the first balanced object.
    for match in re.finditer(r"[{\[]", s):
        try:
            value, _end = decoder.raw_decode(s[match.start():])
            return json.dumps(value)
        except json.JSONDecodeError:
            continue
    return s


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
        # CLOUDFLARE_AI_GATEWAY_URL, when set, wraps OpenRouter so all three
        # vendor calls (Anthropic / OpenAI / Google) share caching +
        # observability. Cloudflare's URL pattern for OpenRouter is
        #   {gateway}/openrouter/v1
        # An explicit OPENROUTER_BASE_URL still wins (escape hatch). When
        # neither is set the client falls back to native OpenRouter.
        explicit = os.environ.get("OPENROUTER_BASE_URL")
        if explicit:
            base_url = explicit
        elif gateway := os.environ.get("CLOUDFLARE_AI_GATEWAY_URL"):
            base_url = f"{gateway.rstrip('/')}/openrouter/v1"
        else:
            base_url = "https://openrouter.ai/api/v1"

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
        raw_content = r.choices[0].message.content or ""
        if response_format and response_format.get("type") == "json_object":
            raw_content = _normalize_json_content(raw_content)
        return LLMResponse(
            content=raw_content,
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
