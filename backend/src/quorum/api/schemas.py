"""API-layer Pydantic schemas.

These wrap the orchestrator schemas (`quorum.orchestrator.schemas`) for the
HTTP surface. Keep them thin — the orchestrator schemas are the source of truth.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from quorum.orchestrator.schemas import FinalVerdict


class DiagnoseRequest(BaseModel):
    """POST /api/diagnose request body."""

    presentation: str = Field(max_length=8000)
    case_id: str | None = Field(default=None, max_length=256)
    available_tests: list[str] = Field(default_factory=list)
    budget_usd: float | None = None
    max_iterations: int = 5
    # Optional panel config name. If absent, the API picks the default
    # (PanelConfig.list_available()[0]). The /api/panels endpoint enumerates
    # valid names.
    panel: str | None = Field(default=None, max_length=64)


class DiagnoseResponse(BaseModel):
    """POST /api/diagnose response body."""

    verdict: FinalVerdict


class PanelInfo(BaseModel):
    """Summary entry for GET /api/panels."""

    name: str
    description: str
