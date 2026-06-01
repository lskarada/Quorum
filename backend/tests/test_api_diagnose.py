"""Acceptance tests for /api/diagnose, /api/diagnose/stream, /api/panels.

Phase 4 wired the FastAPI surface to the Panel orchestrator; Phase 5 added
the multi-iter consensus loop, the named PanelConfig dependency, the
optional `panel` parameter, and the GET /api/panels listing.

Tests use httpx.AsyncClient against an ASGI transport (no real network),
and inject a mocked Panel via FastAPI dependency_overrides.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from quorum.api.main import app
from quorum.api.routes import get_panel
from quorum.llm.client import LLMClient
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    DiagnosisCandidate,
    Differential,
    NextTest,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _baseline_config() -> PanelConfig:
    return next(
        c for c in PanelConfig.list_available() if c.name == "baseline_single_call"
    )


def _dev_cheap_config() -> PanelConfig:
    return next(c for c in PanelConfig.list_available() if c.name == "dev_cheap")


def _make_canned_message(posterior_top: float = 0.75) -> AgentMessage:
    diff = Differential(
        candidates=[
            DiagnosisCandidate(name="Disease A", posterior=posterior_top, rationale="r1"),
            DiagnosisCandidate(name="Disease B", posterior=0.20, rationale="r2"),
            DiagnosisCandidate(
                name="Disease C",
                posterior=round(1 - posterior_top - 0.20, 4),
                rationale="r3",
            ),
        ],
        iteration=0,
    )
    return AgentMessage(
        role=AgentRole.HYPOTHESIS,
        iteration=0,
        content="differential proposed",
        structured_output=diff,
        tokens_used=300,
        cost_usd=0.015,
    )


def _make_canned_test_chooser_message() -> AgentMessage:
    nt = NextTest(
        name="Test X",
        rationale="discriminates A from B",
        estimated_cost_usd=100.0,
        information_gain_estimate=0.5,
        discriminates_between=["Disease A", "Disease B"],
    )
    return AgentMessage(
        role=AgentRole.TEST_CHOOSER,
        iteration=0,
        content=f"Recommend: {nt.name} — {nt.rationale}",
        structured_output=nt,
        tokens_used=80,
        cost_usd=0.004,
    )


def _mock_panel(side_effect: Exception | None = None) -> Panel:
    """Build a baseline_single_call Panel and mock its hypothesis agent.

    The baseline config has only the hypothesis slot, so we don't need to
    mock the other four agents (they are None on this Panel instance).
    """
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "claude-opus-4-7"
    panel = Panel(llm, _baseline_config())
    if side_effect is not None:
        panel.hypothesis.deliberate = AsyncMock(side_effect=side_effect)
    else:
        panel.hypothesis.deliberate = AsyncMock(return_value=_make_canned_message())
    return panel


@pytest.fixture
def client_with_mock_panel():
    """Yields (AsyncClient, panel) and clears dependency overrides on teardown."""

    async def _factory(side_effect: Exception | None = None):
        panel = _mock_panel(side_effect)
        app.dependency_overrides[get_panel] = lambda: panel
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        return client, panel

    yield _factory
    app.dependency_overrides.clear()


def _parse_sse_events(text: str) -> list[dict]:
    """Parse an SSE response body into a list of {event, data} dicts."""
    events: list[dict] = []
    current_event: str | None = None
    current_data: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            current_data.append(line.split(":", 1)[1].strip())
        elif line == "":
            if current_event is not None:
                events.append(
                    {
                        "event": current_event,
                        "data": json.loads("\n".join(current_data)) if current_data else None,
                    }
                )
            current_event = None
            current_data = []
    return events


# ---------------------------------------------------------------------------
# POST /api/diagnose
# ---------------------------------------------------------------------------


async def test_post_diagnose_happy_path(client_with_mock_panel):
    client, _ = await client_with_mock_panel()
    async with client:
        response = await client.post(
            "/api/diagnose",
            json={"presentation": "45M with fever and cough."},
        )
    assert response.status_code == 200
    body = response.json()
    assert "verdict" in body
    assert body["verdict"]["termination_reason"] in {"consensus", "max_iterations"}
    assert body["verdict"]["confidence"] == pytest.approx(0.75)
    assert body["verdict"]["is_error"] is False
    assert body["verdict"]["schema_version"] == 1


async def test_post_diagnose_missing_presentation_returns_422(client_with_mock_panel):
    client, _ = await client_with_mock_panel()
    async with client:
        response = await client.post("/api/diagnose", json={})
    assert response.status_code == 422


async def test_post_diagnose_hypothesis_error_returns_200_with_error_verdict(
    client_with_mock_panel,
):
    """Panel.diagnose catches Hypothesis errors and returns an error-verdict;
    HTTP layer surfaces it as 200 with termination_reason='error' (no 500)."""
    client, _ = await client_with_mock_panel(side_effect=RuntimeError("provider boom"))
    async with client:
        response = await client.post(
            "/api/diagnose",
            json={"presentation": "Will fail."},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"]["termination_reason"] == "error"
    assert body["verdict"]["is_error"] is True
    assert body["verdict"]["final_differential"]["candidates"] == []


# ---------------------------------------------------------------------------
# POST /api/diagnose/stream
# ---------------------------------------------------------------------------


async def test_stream_diagnose_emits_events_in_order(client_with_mock_panel):
    """Baseline (hypothesis-only) emits: agent_start, agent_complete,
    round_complete, verdict."""
    client, _ = await client_with_mock_panel()
    async with client:
        response = await client.post(
            "/api/diagnose/stream",
            json={"presentation": "Patient with cough."},
        )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert [e["event"] for e in events] == [
        "agent_start",
        "agent_complete",
        "round_complete",
        "verdict",
    ]


async def test_stream_diagnose_agent_complete_payload(client_with_mock_panel):
    client, _ = await client_with_mock_panel()
    async with client:
        response = await client.post(
            "/api/diagnose/stream",
            json={"presentation": "Patient with cough."},
        )
    events = _parse_sse_events(response.text)
    complete = next(e for e in events if e["event"] == "agent_complete")
    assert complete["data"]["agent"] == "hypothesis"
    assert "differential" in complete["data"]
    assert len(complete["data"]["differential"]["candidates"]) == 3


async def test_stream_diagnose_missing_presentation_returns_422(client_with_mock_panel):
    client, _ = await client_with_mock_panel()
    async with client:
        response = await client.post("/api/diagnose/stream", json={})
    assert response.status_code == 422


async def test_stream_diagnose_emits_error_event_on_hypothesis_failure(
    client_with_mock_panel,
):
    client, _ = await client_with_mock_panel(
        side_effect=RuntimeError("provider 429 rate limit")
    )
    async with client:
        response = await client.post(
            "/api/diagnose/stream",
            json={"presentation": "Will fail."},
        )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    error_events = [e for e in events if e["event"] == "error"]
    assert len(error_events) == 1
    assert error_events[0]["data"]["code"] == "provider_429"
    assert error_events[0]["data"]["retriable"] is True
    # Error event is followed by exactly one terminal verdict event.
    error_idx = events.index(error_events[0])
    assert events[error_idx + 1]["event"] == "verdict"
    assert events[-1]["event"] == "verdict"
    assert events[-1]["data"]["is_error"] is True


# ---------------------------------------------------------------------------
# GET /api/panels
# ---------------------------------------------------------------------------


async def test_list_panels_returns_configs():
    """GET /api/panels returns name+description for each available config."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/panels")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    names = {p["name"] for p in body}
    assert {
        "baseline_single_call",
        "dev_cheap",
        "mixed_vendor",
        "single_model_premium",
    }.issubset(names)
    for entry in body:
        assert "name" in entry
        assert "description" in entry


# ---------------------------------------------------------------------------
# Panel-name selection via query / body
# ---------------------------------------------------------------------------


async def test_get_panel_dependency_selects_named_config(monkeypatch):
    """POST /api/diagnose/stream with `panel` in the body builds a Panel
    constructed from that named PanelConfig.

    Verified by intercepting the Panel constructor — the last-constructed
    Panel (the body override) must use the baseline PanelConfig.
    """
    from quorum.api import routes

    captured: dict = {}

    real_panel_cls = routes.Panel

    class _Spy(real_panel_cls):  # type: ignore[misc, valid-type]
        def __init__(self, llm, config=None):
            captured["config"] = config
            super().__init__(llm, config)
            # Mock the hypothesis agent so we don't hit the real LLM.
            self.hypothesis.deliberate = AsyncMock(
                return_value=_make_canned_message()
            )

    # Patch the LLMClient inside routes.get_panel so it doesn't try to talk
    # to the real network on construction (conftest already sets a placeholder
    # OPENROUTER_API_KEY so AsyncOpenAI builds fine; no live calls happen).
    monkeypatch.setattr(routes, "Panel", _Spy)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/diagnose/stream",
            json={"presentation": "x", "panel": "baseline_single_call"},
        )
    assert response.status_code == 200
    assert captured["config"].name == "baseline_single_call"


async def test_post_diagnose_with_panel_param_in_body(monkeypatch):
    """POST body with `panel`: routes constructs Panel using the named config."""
    from quorum.api import routes

    captured_configs: list = []

    real_panel_cls = routes.Panel

    class _Spy(real_panel_cls):  # type: ignore[misc, valid-type]
        def __init__(self, llm, config=None):
            captured_configs.append(config)
            super().__init__(llm, config)
            self.hypothesis.deliberate = AsyncMock(
                return_value=_make_canned_message()
            )

    monkeypatch.setattr(routes, "Panel", _Spy)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/diagnose",
            json={
                "presentation": "x",
                "panel": "baseline_single_call",
            },
        )
    assert response.status_code == 200
    # The body's panel override should result in at least one constructed
    # Panel using baseline_single_call.
    names = [c.name for c in captured_configs if c is not None]
    assert "baseline_single_call" in names


async def test_diagnose_stream_unknown_panel_returns_422(client_with_mock_panel):
    """Unknown panel name → 422 from the dependency resolver."""
    # Don't use the dependency override here — we want the real get_panel
    # to validate the name.
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/diagnose/stream",
            json={"presentation": "x", "panel": "no_such_panel"},
        )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# /health smoke
# ---------------------------------------------------------------------------


async def test_health_endpoint_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
