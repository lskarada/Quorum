"""API-layer Pydantic schemas.

These wrap the orchestrator schemas (`quorum.orchestrator.schemas`) for the
HTTP surface. Keep them thin — the orchestrator schemas are the source of truth.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from quorum.orchestrator.schemas import FinalVerdict


class DiagnoseRequest(BaseModel):
    """POST /api/diagnose request body."""

    presentation: str = Field(max_length=8000)
    case_id: Optional[str] = Field(default=None, max_length=256)
    available_tests: list[str] = Field(default_factory=list)
    budget_usd: Optional[float] = None
    max_iterations: int = 5


class DiagnoseResponse(BaseModel):
    """POST /api/diagnose response body."""

    verdict: FinalVerdict
