from unittest.mock import AsyncMock, patch

import pytest
from quorum.llm.client import LLMClient, LLMResponse


@pytest.mark.asyncio
async def test_complete_returns_llm_response_with_cost():
    """LLMClient.complete must return an LLMResponse populated from OpenRouter usage."""
    fake_openai_response = type("R", (), {
        "choices": [type("C", (), {"message": type("M", (), {"content": "ok"})()})()],
        "usage": type("U", (), {
            "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
            "cost": 0.001,
        })(),
        "model": "anthropic/claude-haiku-4-5",
    })

    with patch("quorum.llm.client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=fake_openai_response)
        mock_cls.return_value = mock_client

        client = LLMClient()
        resp = await client.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="anthropic/claude-haiku-4-5",
        )

    assert isinstance(resp, LLMResponse)
    assert resp.content == "ok"
    assert resp.tokens_used == 15
    assert resp.cost_usd == 0.001
    assert resp.model == "anthropic/claude-haiku-4-5"


@pytest.mark.asyncio
async def test_missing_key_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        LLMClient()
