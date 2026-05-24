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


@pytest.mark.asyncio
async def test_complete_writes_to_spend_file_and_blocks_at_cap(monkeypatch, tmp_path):
    """Cumulative spend file is updated; cap raises before exceeding."""
    import quorum.llm.client as client_module
    spend_file = tmp_path / "spend.json"
    monkeypatch.setattr(client_module, "_SPEND_FILE", spend_file)
    monkeypatch.setenv("QUORUM_TOTAL_SPEND_LIMIT_USD", "0.005")  # tiny cap

    fake_resp = type("R", (), {
        "choices": [type("C", (), {"message": type("M", (), {"content": "ok"})()})()],
        "usage": type("U", (), {
            "prompt_tokens": 10, "completion_tokens": 5,
            "total_tokens": 15, "cost": 0.003,
        })(),
        "model": "anthropic/claude-haiku-4-5",
    })

    with patch("quorum.llm.client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=fake_resp)
        mock_cls.return_value = mock_client

        client = LLMClient()
        # First call: 0.003 -> under 0.005 cap, succeeds
        await client.complete(messages=[{"role": "user", "content": "a"}])
        import json as _json
        data = _json.loads(spend_file.read_text())
        assert data["total"] == pytest.approx(0.003)

        # Second call: would push to 0.006 -> over 0.005 cap, raises
        with pytest.raises(RuntimeError, match="spend cap"):
            await client.complete(messages=[{"role": "user", "content": "b"}])
