"""Helper-method tests on Differential (Phase 5 Task 5.2).

The plan's Task 5.2 originally proposed adding a flat
`posterior_over_shortlist` field. Per the AGENT_CONTRACTS.md audit,
the existing `Differential` already carries per-candidate posteriors
that the agent auto-normalizes to sum ~1.0. So Task 5.2 collapses to
adding two small accessors that downstream code (SafetyChecker,
Brier/ECE) can call without inlining a list comprehension.
"""
from __future__ import annotations

import pytest

from quorum.orchestrator.schemas import DiagnosisCandidate, Differential


def _candidate(name: str, p: float) -> DiagnosisCandidate:
    return DiagnosisCandidate(name=name, posterior=p, rationale="test")


def test_as_posterior_dict_returns_name_keyed_dict():
    diff = Differential(
        candidates=[_candidate("SLE", 0.7), _candidate("MCTD", 0.2), _candidate("RA", 0.1)],
        iteration=0,
    )
    d = diff.as_posterior_dict()
    assert d == {"SLE": 0.7, "MCTD": 0.2, "RA": 0.1}


def test_as_posterior_dict_empty_when_no_candidates():
    diff = Differential(candidates=[], iteration=0)
    assert diff.as_posterior_dict() == {}


def test_top_diagnosis_returns_highest_posterior_pair():
    diff = Differential(
        candidates=[_candidate("SLE", 0.7), _candidate("MCTD", 0.2), _candidate("RA", 0.1)],
        iteration=0,
    )
    name, p = diff.top_diagnosis()
    assert name == "SLE"
    assert p == pytest.approx(0.7)


def test_top_diagnosis_none_when_empty():
    diff = Differential(candidates=[], iteration=0)
    assert diff.top_diagnosis() is None
