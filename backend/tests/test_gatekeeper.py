"""Gatekeeper unit tests (Phase 2 Task 2.2).

All tests are async because the production LLM matcher is async. We
monkey-patch `_llm_match` to make tests hermetic (no API calls).
"""
from __future__ import annotations

import pytest
from quorum.eval.eval_case import EvalCase, Finding
from quorum.gatekeeper.gatekeeper import Gatekeeper, GatekeeperResponse


@pytest.fixture
def toy_case() -> EvalCase:
    return EvalCase(
        case_id="toy-1",
        corpus="nejm",
        source="test",
        initial_presentation="patient with chest pain",
        available_findings=[
            Finding(category="labs", label="Troponin", content="Troponin 0.15 ng/mL (elevated)"),
            Finding(
                category="imaging",
                label="Chest x-ray",
                content="No cardiomegaly, clear lungs",
            ),
        ],
        ground_truth_diagnosis="acute myocardial infarction",
        acceptable_partial_credit=[],
    )


def _stub_match_factory(idx: int):
    async def _stub(question, findings):
        return idx
    return _stub


async def test_gatekeeper_matches_known_finding(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case)
    monkeypatch.setattr(gk, "_llm_match", _stub_match_factory(0))
    resp = await gk.query("What is the troponin level?")
    assert isinstance(resp, GatekeeperResponse)
    assert resp.matched is True
    assert "Troponin" in resp.content
    # CMS-table lookup found troponin (lab)
    assert resp.cost_usd > 0


async def test_gatekeeper_returns_not_available_for_unrelated(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case)
    monkeypatch.setattr(gk, "_llm_match", _stub_match_factory(-1))
    resp = await gk.query("What is the patient's astrological sign?")
    assert resp.matched is False
    assert "not available" in resp.content.lower()
    assert resp.cost_usd == 0.0


async def test_gatekeeper_accumulates_cost(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case)
    monkeypatch.setattr(gk, "_llm_match", _stub_match_factory(0))
    assert gk.simulated_cost == 0
    await gk.query("Troponin?")
    assert gk.simulated_cost > 0


async def test_gatekeeper_turn_limit(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case, max_turns=2)
    monkeypatch.setattr(gk, "_llm_match", _stub_match_factory(0))
    await gk.query("q1")
    await gk.query("q2")
    with pytest.raises(RuntimeError, match="max turns"):
        await gk.query("q3")


async def test_gatekeeper_cost_limit(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case, max_cost_usd=10)
    # First finding is Troponin = $22 in CMS table; exceeds $10
    monkeypatch.setattr(gk, "_llm_match", _stub_match_factory(0))
    await gk.query("Troponin?")
    with pytest.raises(RuntimeError, match="max cost"):
        await gk.query("Troponin again?")


async def test_gatekeeper_substring_fallback(toy_case):
    """When no LLM client is provided, fall back to substring match on label."""
    gk = Gatekeeper(toy_case)  # llm_client=None
    resp = await gk.query("Tell me the troponin")
    assert resp.matched is True
    assert "Troponin" in resp.content


async def test_gatekeeper_records_matched_label(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case)
    monkeypatch.setattr(gk, "_llm_match", _stub_match_factory(0))
    resp = await gk.query("Troponin?")
    assert resp.matched_label == "Troponin"
    assert resp.turn_index == 1
