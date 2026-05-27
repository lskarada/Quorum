"""Tests for quorum.eval.scorer."""
from __future__ import annotations

import pathlib

from quorum.eval.scorer import compare_runs, score_case, score_run
from quorum.orchestrator.schemas import (
    DiagnosisCandidate,
    Differential,
    FinalVerdict,
)


def _verdict(case_id: str, candidates: list[str], cost: float = 0.01) -> FinalVerdict:
    return FinalVerdict(
        case_id=case_id,
        final_differential=Differential(
            candidates=[
                DiagnosisCandidate(
                    name=n,
                    posterior=round(1.0 / (i + 2), 4),
                    rationale="r",
                )
                for i, n in enumerate(candidates)
            ],
            iteration=0,
        ),
        confidence=0.5,
        iterations_used=1,
        total_tokens=100,
        total_cost_usd=cost,
        transcript=[],
        termination_reason="consensus",
        schema_version=1,
        is_error=False,
    )


def test_top1_correct_when_top_candidate_matches():
    v = _verdict("c1", ["Acute appendicitis", "Gastroenteritis", "UTI"])
    s = score_case(v, "Acute appendicitis")
    assert s.top1_correct is True
    assert s.topk_correct is True
    assert s.rank_of_truth == 1
    assert s.mrr_contribution == 1.0


def test_top5_correct_when_truth_in_top5():
    v = _verdict(
        "c1",
        ["Pneumonia", "Bronchitis", "Pleural effusion", "Pulmonary embolism", "Acute appendicitis"],
    )
    s = score_case(v, "Acute appendicitis", k=5)
    assert s.top1_correct is False
    assert s.topk_correct is True
    assert s.rank_of_truth == 5
    assert abs(s.mrr_contribution - 0.2) < 1e-9


def test_not_found_returns_no_rank():
    v = _verdict("c1", ["Migraine", "Tension headache", "Cluster headache"])
    s = score_case(v, "Subarachnoid hemorrhage")
    assert s.top1_correct is False
    assert s.topk_correct is False
    assert s.rank_of_truth is None
    assert s.mrr_contribution == 0.0


def test_score_run_aggregates(tmp_path: pathlib.Path):
    # Three cases: 2 correct top-1, 1 wrong.
    for cid, cands in (
        ("c1", ["Pneumonia", "Bronchitis"]),
        ("c2", ["Stroke", "Migraine"]),
        ("c3", ["Migraine", "Stroke"]),
    ):
        (tmp_path / f"case_{cid}.json").write_text(
            _verdict(cid, cands, cost=0.02).model_dump_json()
        )
    gt = {"c1": "Pneumonia", "c2": "Stroke", "c3": "Stroke"}
    s = score_run(tmp_path, gt)
    assert s["n_cases"] == 3
    assert abs(s["top1"] - 2 / 3) < 1e-9
    assert abs(s["topk"] - 1.0) < 1e-9
    assert abs(s["mean_cost_usd"] - 0.02) < 1e-9


def test_score_run_skips_missing_ground_truth(tmp_path: pathlib.Path):
    (tmp_path / "case_c1.json").write_text(_verdict("c1", ["X"]).model_dump_json())
    (tmp_path / "case_c2.json").write_text(_verdict("c2", ["Y"]).model_dump_json())
    gt = {"c1": "X"}  # c2 absent
    s = score_run(tmp_path, gt)
    assert s["n_cases"] == 1


def test_compare_runs_runs_mcnemar_and_wilcoxon(tmp_path: pathlib.Path):
    a_dir = tmp_path / "a"
    b_dir = tmp_path / "b"
    a_dir.mkdir()
    b_dir.mkdir()
    # 3 paired cases. A: 2 correct; B: 1 correct.
    (a_dir / "case_c1.json").write_text(_verdict("c1", ["Pneumonia"]).model_dump_json())
    (a_dir / "case_c2.json").write_text(_verdict("c2", ["Stroke"]).model_dump_json())
    (a_dir / "case_c3.json").write_text(_verdict("c3", ["Migraine"]).model_dump_json())
    (b_dir / "case_c1.json").write_text(_verdict("c1", ["Pneumonia"]).model_dump_json())
    (b_dir / "case_c2.json").write_text(_verdict("c2", ["Migraine"]).model_dump_json())
    (b_dir / "case_c3.json").write_text(_verdict("c3", ["Migraine"]).model_dump_json())
    gt = {"c1": "Pneumonia", "c2": "Stroke", "c3": "Stroke"}

    cmp = compare_runs(a_dir, b_dir, gt)
    assert cmp["n_cases_paired"] == 3
    assert "mcnemar" in cmp and "pvalue" in cmp["mcnemar"]
    assert "wilcoxon_mrr" in cmp and "pvalue" in cmp["wilcoxon_mrr"]
    assert abs(cmp["top1_a"] - 2 / 3) < 1e-9
    assert abs(cmp["top1_b"] - 1 / 3) < 1e-9
