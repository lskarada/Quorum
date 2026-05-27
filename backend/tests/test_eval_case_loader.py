"""Tests for the unified EvalCase loader (Phase 1 Task 1.3)."""
from __future__ import annotations

from quorum.eval.eval_case import EvalCase, Finding, load_corpus


def test_load_corpus_returns_35_cases():
    cases = load_corpus()
    assert len(cases) == 35
    assert all(isinstance(c, EvalCase) for c in cases)


def test_eval_case_has_required_fields():
    cases = load_corpus()
    for c in cases:
        assert c.case_id
        assert c.initial_presentation
        assert c.ground_truth_diagnosis
        assert isinstance(c.available_findings, list)
        assert c.corpus in ("nejm", "mcr", "rarebench")


def test_load_split_works():
    tune = load_corpus(split="tune")
    evaluation = load_corpus(split="eval")
    assert len(tune) == 5
    assert len(evaluation) == 30
    assert set(c.case_id for c in tune).isdisjoint(set(c.case_id for c in evaluation))


def test_nejm_findings_preserved():
    """NEJM cases carry structured `available_findings`."""
    cases = [c for c in load_corpus() if c.corpus == "nejm"]
    assert len(cases) == 20
    nejm_with_findings = [c for c in cases if c.available_findings]
    assert len(nejm_with_findings) == 20, "every NEJM case should have ≥1 finding"
    f = nejm_with_findings[0].available_findings[0]
    assert isinstance(f, Finding)
    assert f.category and f.label and f.content


def test_mcr_and_rarebench_have_no_findings():
    """MCR + RareBench run single-turn for v2."""
    for c in load_corpus():
        if c.corpus in ("mcr", "rarebench"):
            assert c.available_findings == []


def test_rarebench_partial_credit_includes_all_disease_names():
    rb = [c for c in load_corpus() if c.corpus == "rarebench"]
    assert rb
    for c in rb:
        # all_ground_truth_names → acceptable_partial_credit
        assert isinstance(c.acceptable_partial_credit, list)
