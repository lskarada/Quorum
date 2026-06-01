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
from quorum.orchestrator.comparison_runner import ComparisonRunner
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


@router.post("/diagnose/stream")
async def diagnose_stream(
    request: DiagnoseRequest,
    panel: Panel = Depends(get_panel),
) -> EventSourceResponse:
    """SSE-streamed diagnosis. Frontend consumes this for live debate display.

    The case presentation is sent in the POST body (not the URL) so long
    cases don't overflow the server's request-line/header limit (HTTP 431).

    If `request.panel` is set, it selects the PanelConfig used to build the
    Panel (overriding any `?panel=` query parameter), matching POST /diagnose.
    """
    if request.panel is not None:
        cfg = _resolve_config(request.panel)
        panel = Panel(LLMClient(), cfg)
    case = CaseInput(presentation=request.presentation, case_id=request.case_id)

    async def event_generator():
        async for event in panel.diagnose_stream(case):
            yield stream_event_to_sse(event)

    return EventSourceResponse(event_generator())


def _resolve_compare_configs(panels_csv: str) -> list[PanelConfig]:
    """Parse a comma-separated `panels` query value into two PanelConfigs.

    Raises HTTPException(422) on wrong count, HTTPException(404) on unknown
    name. Returns the two configs in the requested order.
    """
    panel_names = [p.strip() for p in panels_csv.split(",") if p.strip()]
    if len(panel_names) != 2:
        raise HTTPException(
            status_code=422,
            detail="`panels` must list exactly two comma-separated panel names",
        )
    available = {c.name: c for c in PanelConfig.list_available()}
    configs: list[PanelConfig] = []
    for n in panel_names:
        if n not in available:
            raise HTTPException(
                status_code=404,
                detail=f"unknown panel '{n}'; available: {sorted(available)}",
            )
        configs.append(available[n])
    if configs[0].name == configs[1].name:
        raise HTTPException(
            status_code=422,
            detail="`panels` must list two distinct panel names",
        )
    return configs


@router.get("/compare/stream")
async def compare_stream(
    presentation: Annotated[str, Query(max_length=_PRESENTATION_MAX_LENGTH)],
    panels: Annotated[str, Query(max_length=256)],
    case_id: Annotated[str | None, Query(max_length=256)] = None,
) -> EventSourceResponse:
    """SSE-streamed two-panel comparison.

    Query params:
      - presentation: case presentation text (required).
      - panels: two comma-separated PanelConfig names (e.g.
        "mixed_vendor,single_model_premium").
      - case_id: optional case identifier echoed in the verdict.

    Every emitted event has `panel_id` injected into its data dict so the
    frontend can route events to the correct side-by-side column.
    """
    configs = _resolve_compare_configs(panels)
    runner = ComparisonRunner(configs, LLMClient())
    case = CaseInput(presentation=presentation, case_id=case_id)

    async def event_generator():
        async for event in runner.compare_stream(case):
            yield stream_event_to_sse(event)

    return EventSourceResponse(event_generator())
