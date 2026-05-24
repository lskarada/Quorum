"""Tests for quorum.eval.report.build_report."""
from __future__ import annotations

import pathlib

from quorum.eval.report import build_report


def _sample_scores() -> dict:
    return {
        "n_cases": 3,
        "top1": 2 / 3,
        "topk": 1.0,
        "mrr": 0.78,
        "mean_cost_usd": 0.0123,
        "per_case": [
            {
                "case_id": "c1",
                "top1_correct": True,
                "topk_correct": True,
                "rank_of_truth": 1,
                "mrr_contribution": 1.0,
                "cost_usd": 0.01,
                "latency_s": 0.0,
            },
            {
                "case_id": "c2",
                "top1_correct": False,
                "topk_correct": True,
                "rank_of_truth": 3,
                "mrr_contribution": 1 / 3,
                "cost_usd": 0.015,
                "latency_s": 0.0,
            },
            {
                "case_id": "c3",
                "top1_correct": True,
                "topk_correct": True,
                "rank_of_truth": 1,
                "mrr_contribution": 1.0,
                "cost_usd": 0.012,
                "latency_s": 0.0,
            },
        ],
    }


def test_build_report_writes_markdown(tmp_path: pathlib.Path):
    out = tmp_path / "report.md"
    build_report(_sample_scores(), out)
    text = out.read_text()
    assert out.exists()
    assert "# Quorum eval results" in text
    assert "Headline" in text
    assert "top-1 accuracy" in text
    assert "Per-case" in text
    assert "c1" in text and "c2" in text and "c3" in text


def test_build_report_handles_empty_scores(tmp_path: pathlib.Path):
    out = tmp_path / "empty.md"
    build_report({"n_cases": 0}, out)
    text = out.read_text()
    assert "No cases scored" in text


def test_build_report_includes_comparison_section(tmp_path: pathlib.Path):
    out = tmp_path / "compare.md"
    comparison = {
        "n_cases_paired": 3,
        "mcnemar": {"statistic": 0.5, "pvalue": 0.4795},
        "wilcoxon_mrr": {"statistic": 1.0, "pvalue": 0.3173},
        "top1_a": 2 / 3,
        "top1_b": 1 / 3,
        "mean_cost_a": 0.012,
        "mean_cost_b": 0.018,
    }
    build_report(_sample_scores(), out, comparison=comparison)
    text = out.read_text()
    assert "Comparison (paired)" in text
    assert "Panel A" in text and "Panel B" in text
    assert "McNemar" in text
    assert "Wilcoxon" in text
