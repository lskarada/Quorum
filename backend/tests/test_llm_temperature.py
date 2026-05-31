"""Regression tests locking temperature passthrough in LLMClient.complete()."""
from unittest.mock import AsyncMock, call, patch

import pytest

from quorum.llm.client import LLMClient


def _fake_resp(content: str = "ok"):
    """Build a minimal response object matching the shape client.py reads."""
    return type("R", (), {
        "choices": [type("C", (), {
            "message": type("M", (), {"content": content})()
        })()],
        "usage": type("U", (), {
            "prompt_tokens": 1, "completion_tokens": 1,
            "total_tokens": 2, "cost": 0.0,
        })(),
        "model": "anthropic/claude-haiku-4-5",
    })


@pytest.mark.asyncio
async def test_temperature_forwarded_when_set():
    """temperature kwarg must reach the underlying API call when provided."""
    with patch("quorum.llm.client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_fake_resp())
        mock_cls.return_value = mock_client

        client = LLMClient()
        await client.complete(
            messages=[{"role": "user", "content": "x"}],
            temperature=0.6,
        )

    create_call = mock_client.chat.completions.create.call_args
    assert create_call is not None
    _, call_kwargs = create_call
    assert call_kwargs.get("temperature") == 0.6, (
        f"Expected temperature=0.6 in kwargs, got {call_kwargs}"
    )


@pytest.mark.asyncio
async def test_temperature_absent_when_none():
    """temperature key must NOT appear in the API call when not provided."""
    with patch("quorum.llm.client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_fake_resp())
        mock_cls.return_value = mock_client

        client = LLMClient()
        await client.complete(
            messages=[{"role": "user", "content": "x"}],
        )

    create_call = mock_client.chat.completions.create.call_args
    assert create_call is not None
    _, call_kwargs = create_call
    assert "temperature" not in call_kwargs, (
        f"temperature should not appear in kwargs when not set, got {call_kwargs}"
    )
