"""Acceptance tests for /api/diagnose and /api/diagnose/stream.

Phase 4 — wires the FastAPI surface to the Panel orchestrator. Tests use
httpx.AsyncClient against an ASGI transport (no real network), and inject a
mocked Panel via FastAPI dependency_overrides.
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
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    DiagnosisCandidate,
    Differential,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _mock_panel(side_effect: Exception | None = None) -> Panel:
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "claude-opus-4-7"
    panel = Panel(llm)
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
    assert body["verdict"]["final_differential"]["candidates"] == []


# ---------------------------------------------------------------------------
# GET /api/diagnose/stream
# ---------------------------------------------------------------------------


async def test_stream_diagnose_emits_three_events_in_order(client_with_mock_panel):
    client, _ = await client_with_mock_panel()
    async with client:
        response = await client.get(
            "/api/diagnose/stream",
            params={"presentation": "Patient with cough."},
        )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert [e["event"] for e in events] == ["agent_start", "agent_complete", "verdict"]


async def test_stream_diagnose_agent_complete_payload(client_with_mock_panel):
    client, _ = await client_with_mock_panel()
    async with client:
        response = await client.get(
            "/api/diagnose/stream",
            params={"presentation": "Patient with cough."},
        )
    events = _parse_sse_events(response.text)
    complete = next(e for e in events if e["event"] == "agent_complete")
    assert complete["data"]["agent"] == "hypothesis"
    assert "differential" in complete["data"]
    assert len(complete["data"]["differential"]["candidates"]) == 3


async def test_stream_diagnose_missing_presentation_returns_422(client_with_mock_panel):
    client, _ = await client_with_mock_panel()
    async with client:
        response = await client.get("/api/diagnose/stream")
    assert response.status_code == 422


async def test_stream_diagnose_emits_error_event_on_hypothesis_failure(
    client_with_mock_panel,
):
    client, _ = await client_with_mock_panel(side_effect=RuntimeError("provider 429 rate limit"))
    async with client:
        response = await client.get(
            "/api/diagnose/stream",
            params={"presentation": "Will fail."},
        )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    error_events = [e for e in events if e["event"] == "error"]
    assert len(error_events) == 1
    assert error_events[0]["data"]["code"] == "provider_429"
    assert error_events[0]["data"]["retriable"] is True
    # Error event must be terminal (no events after it).
    assert events[-1]["event"] == "error"


# ---------------------------------------------------------------------------
# /health smoke
# ---------------------------------------------------------------------------


async def test_health_endpoint_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
