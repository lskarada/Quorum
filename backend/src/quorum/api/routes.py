"""API routes. /api/diagnose (sync) and /api/diagnose/stream (SSE)."""
from __future__ import annotations

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from quorum.api.schemas import DiagnoseRequest, DiagnoseResponse

router = APIRouter()


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    """Synchronous diagnosis. Returns the final verdict.

    For long cases this can take 30-90 seconds. Use /diagnose/stream for live UI.
    """
    # TODO: instantiate Panel, run diagnose(), return verdict wrapped in DiagnoseResponse
    raise NotImplementedError


@router.get("/diagnose/stream")
async def diagnose_stream(
    case_id: str | None = None,
    presentation: str = "",
) -> EventSourceResponse:
    """SSE-streamed diagnosis. Frontend consumes this for live debate display."""
    # TODO: instantiate Panel, run diagnose_stream(), yield SSE events
    raise NotImplementedError
