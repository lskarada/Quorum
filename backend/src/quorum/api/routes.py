"""API routes. /api/diagnose (sync), /api/diagnose/stream (SSE), /api/panels."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from quorum.api.schemas import (
    DiagnoseRequest,
    DiagnoseResponse,
    PanelInfo,
)
from quorum.api.streaming import stream_event_to_sse
from quorum.llm.client import LLMClient
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import CaseInput

_PRESENTATION_MAX_LENGTH = 8000

router = APIRouter()


def _resolve_config(name: str | None) -> PanelConfig:
    configs = PanelConfig.list_available()
    if name is None:
        return configs[0]
    by_name = {c.name: c for c in configs}
    if name not in by_name:
        raise HTTPException(
            status_code=422,
            detail=f"unknown panel '{name}'; available: {sorted(by_name)}",
        )
    return by_name[name]


def get_panel(panel: str | None = Query(default=None, max_length=64)) -> Panel:
    """FastAPI dependency factory.

    Reads the optional `panel` query parameter and builds a Panel with the
    matching PanelConfig. Tests override via
    `app.dependency_overrides[get_panel] = lambda: <mocked panel>`.

    Note: the POST /diagnose route additionally accepts a `panel` field in
    the request body. The body field, when present, wins over the query
    parameter (see the diagnose endpoint).
    """
    cfg = _resolve_config(panel)
    return Panel(LLMClient(), cfg)


@router.get("/panels", response_model=list[PanelInfo])
async def list_panels() -> list[PanelInfo]:
    """List available named panel configurations."""
    return [
        PanelInfo(name=c.name, description=c.description)
        for c in PanelConfig.list_available()
    ]


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    request: DiagnoseRequest,
    panel: Panel = Depends(get_panel),
) -> DiagnoseResponse:
    """Synchronous diagnosis. Returns the final verdict.

    For long cases this can take 30-90 seconds. Use /diagnose/stream for live UI.

    If `request.panel` is set, it selects the PanelConfig used to build the
    Panel (overriding any `?panel=` query parameter).
    """
    if request.panel is not None:
        cfg = _resolve_config(request.panel)
        panel = Panel(LLMClient(), cfg)
    case = CaseInput(**request.model_dump(exclude={"panel"}))
    verdict = await panel.diagnose(case)
    return DiagnoseResponse(verdict=verdict)


@router.get("/diagnose/stream")
async def diagnose_stream(
    presentation: Annotated[str, Query(max_length=_PRESENTATION_MAX_LENGTH)],
    case_id: Annotated[str | None, Query(max_length=256)] = None,
    panel: Panel = Depends(get_panel),
) -> EventSourceResponse:
    """SSE-streamed diagnosis. Frontend consumes this for live debate display.

    Optional `?panel=<name>` query param selects a named PanelConfig.
    """
    case = CaseInput(presentation=presentation, case_id=case_id)

    async def event_generator():
        async for event in panel.diagnose_stream(case):
            yield stream_event_to_sse(event)

    return EventSourceResponse(event_generator())
