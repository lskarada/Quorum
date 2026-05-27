"""Tests for CLOUDFLARE_AI_GATEWAY_URL wiring (Phase 5).

All three providers (Anthropic / OpenAI / Google) reach the model via
OpenRouter (see CLAUDE.md decision 2026-05-24 — Workers AI as 4th provider
was struck). When ``CLOUDFLARE_AI_GATEWAY_URL`` is set, the LLMClient must
route the OpenRouter calls through the gateway URL so that all three
vendors benefit from caching + observability uniformly. When the env var
is absent, the client must fall back to the native OpenRouter endpoint.
"""
from __future__ import annotations

from quorum.llm.client import LLMClient

_GATEWAY = "https://gateway.ai.cloudflare.com/v1/test-account/test-gateway"


def _make_client(monkeypatch, gateway: str | None) -> LLMClient:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    if gateway is None:
        monkeypatch.delenv("CLOUDFLARE_AI_GATEWAY_URL", raising=False)
    else:
        monkeypatch.setenv("CLOUDFLARE_AI_GATEWAY_URL", gateway)
    return LLMClient()


def _base_url(c: LLMClient) -> str:
    # AsyncOpenAI exposes base_url as a httpx.URL or str; coerce.
    return str(c._client.base_url).rstrip("/")


def test_anthropic_calls_route_through_gateway_when_set(monkeypatch):
    c = _make_client(monkeypatch, _GATEWAY)
    # The LLMClient is OpenRouter-routed for every vendor, so gateway routing
    # is a property of the client base_url itself, not the per-model call.
    assert _GATEWAY in _base_url(c)
    assert "/openrouter" in _base_url(c)


def test_openai_calls_route_through_gateway_when_set(monkeypatch):
    c = _make_client(monkeypatch, _GATEWAY)
    assert _GATEWAY in _base_url(c)
    assert "/openrouter" in _base_url(c)


def test_google_calls_route_through_gateway_when_set(monkeypatch):
    c = _make_client(monkeypatch, _GATEWAY)
    assert _GATEWAY in _base_url(c)
    assert "/openrouter" in _base_url(c)


def test_gateway_url_absent_falls_back_to_native_endpoints(monkeypatch):
    c = _make_client(monkeypatch, None)
    assert _GATEWAY not in _base_url(c)
    assert "openrouter.ai" in _base_url(c)
