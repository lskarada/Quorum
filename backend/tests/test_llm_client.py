from unittest.mock import AsyncMock, patch

import pytest
from quorum.llm.client import (
    LLMClient,
    LLMResponse,
    _normalize_json_content,
    _strip_json_fence,
)


def test_normalize_json_content_takes_first_object():
    """LLM often emits JSON object followed by commentary; take only the object."""
    s = '{"x": 1}\nHere is some commentary.'
    out = _normalize_json_content(s)
    assert out == '{"x": 1}'


def test_normalize_json_content_handles_fenced_then_trailing():
    s = '```json\n{"x": 1}\n```\nAnd some prose.'
    out = _normalize_json_content(s)
    assert out == '{"x": 1}'


def test_normalize_json_content_passes_through_clean():
    s = '{"x": 1}'
    assert _normalize_json_content(s) == '{"x": 1}'


def test_normalize_json_content_passes_through_non_json():
    s = "not json at all"
    assert _normalize_json_content(s) == "not json at all"


def test_strip_json_fence_unwrapped_passthrough():
    assert _strip_json_fence('{"x": 1}') == '{"x": 1}'


def test_strip_json_fence_handles_json_fence():
    fenced = '```json\n{"x": 1}\n```'
    assert _strip_json_fence(fenced) == '{"x": 1}'


def test_strip_json_fence_handles_bare_fence():
    fenced = '```\n{"x": 1}\n```'
    assert _strip_json_fence(fenced) == '{"x": 1}'


def test_strip_json_fence_handles_uppercase_lang_tag():
    fenced = '```JSON\n{"x": 1}\n```'
    assert _strip_json_fence(fenced) == '{"x": 1}'


def test_strip_json_fence_idempotent_with_whitespace():
    fenced = '  ```json\n{"x": 1}\n```  '
    assert _strip_json_fence(fenced) == '{"x": 1}'


@pytest.mark.asyncio
async def test_complete_strips_fence_when_json_object_requested():
    fenced = '```json\n{"x": 1}\n```'
    fake_resp = type("R", (), {
        "choices": [type("C", (), {"message": type("M", (), {"content": fenced})()})()],
        "usage": type("U", (), {"prompt_tokens": 1, "completion_tokens": 1,
                                  "total_tokens": 2, "cost": 0.0})(),
        "model": "anthropic/claude-haiku-4-5",
    })
    with patch("quorum.llm.client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=fake_resp)
        mock_cls.return_value = mock_client
        client = LLMClient()
        resp = await client.complete(
            messages=[{"role": "user", "content": "x"}],
            response_format={"type": "json_object"},
        )
    assert resp.content == '{"x": 1}'


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
