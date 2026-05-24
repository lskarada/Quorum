"""Acceptance tests for GET /api/compare/stream.

The endpoint resolves two PanelConfigs by name, constructs a
ComparisonRunner, and streams multiplexed events tagged with panel_id.

Like test_api_diagnose, these tests use httpx.AsyncClient against an ASGI
transport (no real network). Live LLM calls are blocked by monkey-patching
each Panel's diagnose_stream on the constructed runner.
"""
from __future__ import annotations

import json

from httpx import ASGITransport, AsyncClient
from quorum.api.main import app
from quorum.orchestrator.schemas import (
    Differential,
    FinalVerdict,
    StreamEvent,
)


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
                        "data": (
                            json.loads("\n".join(current_data))
                            if current_data
                            else None
                        ),
                    }
                )
            current_event = None
            current_data = []
    return events


def _canned_verdict() -> FinalVerdict:
    return FinalVerdict(
        case_id=None,
        final_differential=Differential(candidates=[], iteration=0),
        confidence=0.0,
        iterations_used=1,
        total_tokens=0,
        total_cost_usd=0.0,
        transcript=[],
        termination_reason="max_iterations",
        schema_version=1,
        is_error=False,
    )


def _patch_compare_runner_with_canned_panels(monkeypatch) -> None:
    """Replace ComparisonRunner used inside routes with a subclass that
    rewrites each Panel.diagnose_stream to emit a single canned verdict.

    This blocks any real LLM call from the compare endpoint while still
    exercising the full route → runner → SSE plumbing.
    """
    from quorum.api import routes
    from quorum.orchestrator.comparison_runner import ComparisonRunner

    class _CannedRunner(ComparisonRunner):
        def __init__(self, configs, llm):
            super().__init__(configs, llm)
            for panel in self.panels:
                async def _good_stream(case, _p=panel):
                    yield StreamEvent(
                        event="verdict",
                        data=_canned_verdict().model_dump(mode="json"),
                    )

                panel.diagnose_stream = _good_stream

    monkeypatch.setattr(routes, "ComparisonRunner", _CannedRunner)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_compare_stream_happy_path_emits_both_verdicts(monkeypatch):
    """GET /api/compare/stream multiplexes two panels; each emits a verdict
    tagged with its panel_id."""
    _patch_compare_runner_with_canned_panels(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/compare/stream",
            params={
                "presentation": "x",
                "panels": "dev_cheap,baseline_single_call",
            },
        )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    # Every event must carry panel_id.
    for ev in events:
        assert "panel_id" in ev["data"], f"event {ev['event']} missing panel_id"
    # Exactly two verdicts — one per panel.
    verdicts = [ev for ev in events if ev["event"] == "verdict"]
    assert len(verdicts) == 2
    panel_ids = {v["data"]["panel_id"] for v in verdicts}
    assert panel_ids == {"dev_cheap", "baseline_single_call"}


# ---------------------------------------------------------------------------
# Validation: wrong number of panels
# ---------------------------------------------------------------------------


async def test_compare_stream_one_panel_returns_422(monkeypatch):
    """`panels=onlyone` (one entry) → 422."""
    _patch_compare_runner_with_canned_panels(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/compare/stream",
            params={"presentation": "x", "panels": "dev_cheap"},
        )
    assert response.status_code == 422


async def test_compare_stream_three_panels_returns_422(monkeypatch):
    """`panels=a,b,c` (three entries) → 422."""
    _patch_compare_runner_with_canned_panels(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/compare/stream",
            params={
                "presentation": "x",
                "panels": "dev_cheap,baseline_single_call,mixed_vendor",
            },
        )
    assert response.status_code == 422


async def test_compare_stream_duplicate_panel_names_returns_422(monkeypatch):
    """`panels=dev_cheap,dev_cheap` (duplicate) → 422 (architect MAJOR)."""
    _patch_compare_runner_with_canned_panels(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/compare/stream",
            params={"presentation": "x", "panels": "dev_cheap,dev_cheap"},
        )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Validation: unknown panel name
# ---------------------------------------------------------------------------


async def test_compare_stream_unknown_panel_returns_404(monkeypatch):
    """`panels=does_not_exist,dev_cheap` → 404 from the resolver."""
    _patch_compare_runner_with_canned_panels(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/compare/stream",
            params={
                "presentation": "x",
                "panels": "does_not_exist,dev_cheap",
            },
        )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Validation: missing presentation
# ---------------------------------------------------------------------------


async def test_compare_stream_missing_presentation_returns_422(monkeypatch):
    _patch_compare_runner_with_canned_panels(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/compare/stream",
            params={"panels": "dev_cheap,baseline_single_call"},
        )
    assert response.status_code == 422
