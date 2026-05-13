"""API routes. /api/diagnose (sync) and /api/diagnose/stream (SSE)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from quorum.api.schemas import DiagnoseRequest, DiagnoseResponse
from quorum.api.streaming import stream_event_to_sse
from quorum.llm.client import LLMClient
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.schemas import CaseInput

router = APIRouter()


def get_panel() -> Panel:
    """FastAPI dependency factory. Tests override via app.dependency_overrides."""
    return Panel(LLMClient())


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    request: DiagnoseRequest,
    panel: Panel = Depends(get_panel),
) -> DiagnoseResponse:
    """Synchronous diagnosis. Returns the final verdict.

    For long cases this can take 30-90 seconds. Use /diagnose/stream for live UI.
    """
    case = CaseInput(**request.model_dump())
    verdict = await panel.diagnose(case)
    return DiagnoseResponse(verdict=verdict)


@router.get("/diagnose/stream")
async def diagnose_stream(
    presentation: str,
    case_id: str | None = None,
    panel: Panel = Depends(get_panel),
) -> EventSourceResponse:
    """SSE-streamed diagnosis. Frontend consumes this for live debate display."""
    case = CaseInput(presentation=presentation, case_id=case_id)

    async def event_generator():
        async for event in panel.diagnose_stream(case):
            yield stream_event_to_sse(event)

    return EventSourceResponse(event_generator())
