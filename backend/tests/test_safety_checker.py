"""Tests for the deterministic safety layer (Phase 5 Task 5.1)."""
from __future__ import annotations

import pytest

from quorum.orchestrator.safety import SafetyChecker, SafetyVerdict


def test_block_commit_without_enough_findings():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85, "MCTD": 0.10, "RA": 0.05},
        challenger_top="SLE",
        checklist_concerns=[],
        n_findings_queried=2,
        simulated_cost=200,
    )
    assert v.blocked
    assert not v.forced
    assert "3 queried findings" in v.reason or "queried findings" in v.reason


def test_block_commit_when_checklist_flagged():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85, "MCTD": 0.10, "RA": 0.05},
        challenger_top="SLE",
        checklist_concerns=["consider lymphoma given lymphadenopathy"],
        n_findings_queried=10,
        simulated_cost=500,
    )
    assert v.blocked


def test_block_commit_dx_not_in_shortlist():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="thyrotoxicosis",
        hypothesis_shortlist={"SLE": 0.85, "MCTD": 0.10, "RA": 0.05},
        challenger_top="SLE",
        checklist_concerns=[],
        n_findings_queried=10,
        simulated_cost=500,
    )
    assert v.blocked
    assert "shortlist" in v.reason.lower()


def test_force_commit_on_cost_overrun():
    sc = SafetyChecker(force_commit_cost_usd=5000)
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85, "MCTD": 0.10, "RA": 0.05},
        challenger_top="SLE",
        checklist_concerns=[],
        n_findings_queried=10,
        simulated_cost=6000,
    )
    assert not v.blocked
    assert v.forced
    assert "cost" in v.reason.lower()


def test_disagreement_triggers_extra_turn():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85, "AML": 0.05, "MCTD": 0.05, "lymphoma": 0.05},
        challenger_top="lymphoma",
        checklist_concerns=[],
        n_findings_queried=10,
        simulated_cost=500,
    )
    assert v.blocked
    assert "disagreement" in v.reason.lower()


def test_clean_commit_passes():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85, "MCTD": 0.10, "RA": 0.05},
        challenger_top="SLE",
        checklist_concerns=[],
        n_findings_queried=10,
        simulated_cost=500,
    )
    assert not v.blocked
    assert not v.forced


def test_challenger_top_none_is_treated_as_no_disagreement():
    """If Challenger says 'none' (no alternative), don't block on disagreement."""
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85, "MCTD": 0.10, "RA": 0.05},
        challenger_top="none",
        checklist_concerns=[],
        n_findings_queried=10,
        simulated_cost=500,
    )
    assert not v.blocked


def test_cost_overrun_overrides_other_blocks():
    """Even if checklist flagged concerns, cost overrun forces commit."""
    sc = SafetyChecker(force_commit_cost_usd=5000)
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85, "MCTD": 0.10, "RA": 0.05},
        challenger_top="lymphoma",
        checklist_concerns=["multiple unresolved alternatives"],
        n_findings_queried=1,
        simulated_cost=6000,
    )
    assert not v.blocked
    assert v.forced
