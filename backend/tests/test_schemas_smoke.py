"""Smoke tests for orchestrator schemas.

These exist to verify schemas.py is a stable contract. They are the ONLY
backend tests that exercise real (non-stub) code in the scaffolding pass.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError
from quorum.orchestrator.schemas import (
    AgentMessage,
    AgentRole,
    Citation,
    DiagnosisCandidate,
    Differential,
    FinalVerdict,
)


def test_agent_role_has_exactly_five_members():
    assert len(list(AgentRole)) == 5
    assert {r.value for r in AgentRole} == {
        "hypothesis",
        "test_chooser",
        "challenger",
        "stewardship",
        "checklist",
    }


def test_diagnosis_candidate_rejects_posterior_above_one():
    with pytest.raises(ValidationError):
        DiagnosisCandidate(name="x", posterior=1.5, rationale="r")


def test_diagnosis_candidate_rejects_posterior_below_zero():
    with pytest.raises(ValidationError):
        DiagnosisCandidate(name="x", posterior=-0.1, rationale="r")


def test_final_verdict_validates_minimal_dict():
    payload = {
        "final_differential": {
            "candidates": [
                {"name": "sarcoidosis", "posterior": 0.4, "rationale": "..."}
            ],
            "iteration": 1,
        },
        "confidence": 0.7,
        "iterations_used": 2,
        "total_tokens": 1000,
        "total_cost_usd": 0.05,
        "transcript": [],
        "termination_reason": "consensus",
    }
    verdict = FinalVerdict.model_validate(payload)
    assert verdict.confidence == 0.7
    assert verdict.termination_reason == "consensus"
    assert len(verdict.final_differential.candidates) == 1


def test_citation_json_round_trip_preserves_excerpt():
    c = Citation(
        source="NEJM 2024;390:1234",
        title="A case of fever",
        url="https://nejm.org/x",
        excerpt="The patient presented with...",
    )
    raw = c.model_dump_json()
    restored = Citation.model_validate_json(raw)
    assert restored.excerpt == c.excerpt
    assert restored.source == c.source


def test_citation_excerpt_max_length_enforced():
    with pytest.raises(ValidationError):
        Citation(source="x", excerpt="a" * 201)


def test_agent_message_default_timestamp_is_set():
    m = AgentMessage(role=AgentRole.HYPOTHESIS, iteration=0, content="...")
    assert m.timestamp is not None
    assert m.tokens_used == 0


def test_differential_json_schema_includes_candidates():
    schema = Differential.model_json_schema()
    assert "candidates" in schema["properties"]
