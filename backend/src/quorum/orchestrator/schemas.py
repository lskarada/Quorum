"""Pydantic schemas for orchestrator messages and state.

These are the canonical data shapes that flow between agents, the API,
and the frontend. Treat as a stable contract.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    HYPOTHESIS = "hypothesis"
    TEST_CHOOSER = "test_chooser"
    CHALLENGER = "challenger"
    STEWARDSHIP = "stewardship"
    CHECKLIST = "checklist"


class Citation(BaseModel):
    """A primary-source citation backing an agent's claim."""

    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    excerpt: Optional[str] = Field(default=None, max_length=200)


class DiagnosisCandidate(BaseModel):
    """A single entry in the differential."""

    name: str
    icd10: Optional[str] = None
    posterior: float = Field(ge=0.0, le=1.0)
    rationale: str
    supporting_findings: list[str] = Field(default_factory=list)
    against_findings: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class Differential(BaseModel):
    """A ranked differential diagnosis."""

    candidates: list[DiagnosisCandidate]
    iteration: int = 0

    def as_posterior_dict(self) -> dict[str, float]:
        """Project the candidates into a {dx_name: posterior} dict.

        Used by Phase 5 run_sequential, SafetyChecker, and the Brier/ECE
        calibration metrics. HypothesisAgent auto-normalizes posteriors
        to sum ~1.0 at deliberation time, so callers can treat the dict
        as a proper probability distribution.
        """
        return {c.name: c.posterior for c in self.candidates}

    def top_diagnosis(self) -> tuple[str, float] | None:
        if not self.candidates:
            return None
        top = max(self.candidates, key=lambda c: c.posterior)
        return top.name, top.posterior


class NextTest(BaseModel):
    """A recommended next diagnostic test."""

    name: str
    rationale: str
    estimated_cost_usd: Optional[float] = None
    information_gain_estimate: Optional[float] = None
    discriminates_between: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class AgentMessage(BaseModel):
    """One utterance from one agent in a deliberation round."""

    role: AgentRole
    iteration: int
    content: str
    structured_output: Optional[Union[Differential, NextTest, dict]] = None
    citations: list[Citation] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tokens_used: int = 0
    cost_usd: float = 0.0


class CaseInput(BaseModel):
    """Input to the orchestrator."""

    case_id: Optional[str] = None
    presentation: str
    available_tests: list[str] = Field(default_factory=list)
    budget_usd: Optional[float] = None
    max_iterations: int = 5


class FinalVerdict(BaseModel):
    """Output of the orchestrator after deliberation concludes."""

    case_id: Optional[str] = None
    final_differential: Differential
    recommended_next_test: Optional[NextTest] = None
    confidence: float = Field(ge=0.0, le=1.0)
    iterations_used: int
    total_tokens: int
    total_cost_usd: float
    transcript: list[AgentMessage]
    termination_reason: Literal[
        "consensus", "budget", "max_iterations", "checklist_stop", "error"
    ]
    schema_version: int = 1
    is_error: bool = False


class StreamEvent(BaseModel):
    """SSE event emitted during streaming deliberation."""

    event: Literal[
        "agent_start",
        "agent_token",
        "agent_complete",
        "round_complete",
        "verdict",
        "error",
    ]
    data: dict
