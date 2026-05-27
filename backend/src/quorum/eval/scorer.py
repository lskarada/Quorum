"""Scoring for eval results.

Per-case score (top-1, top-5, rank, MRR contribution, cost, latency) plus
run-level aggregates and paired-run comparison (McNemar on top-1, Wilcoxon
signed-rank on MRR).
"""
from __future__ import annotations

import pathlib

from pydantic import BaseModel

from quorum.orchestrator.schemas import FinalVerdict


class CaseScore(BaseModel):
    case_id: str
    top1_correct: bool
    topk_correct: bool
    rank_of_truth: int | None
    mrr_contribution: float
    cost_usd: float
    latency_s: float


def _matches(candidate: str, truth: str) -> bool:
    return truth in candidate or candidate in truth


def score_case(verdict: FinalVerdict, ground_truth: str, k: int = 5) -> CaseScore:
    candidates = [c.name.lower().strip() for c in verdict.final_differential.candidates]
    truth = ground_truth.lower().strip()
    rank: int | None = next(
        (i + 1 for i, c in enumerate(candidates) if _matches(c, truth)),
        None,
    )
    return CaseScore(
        case_id=verdict.case_id or "unknown",
        top1_correct=(rank == 1),
        topk_correct=(rank is not None and rank <= k),
        rank_of_truth=rank,
        mrr_contribution=(1.0 / rank if rank else 0.0),
        cost_usd=verdict.total_cost_usd,
        latency_s=0.0,
    )


def score_run(results_dir: pathlib.Path, ground_truth: dict[str, str]) -> dict:
    """Aggregate top-1, top-5, MRR, mean cost across all per-case results."""
    scores: list[CaseScore] = []
    for f in sorted(results_dir.glob("case_*.json")):
        verdict = FinalVerdict.model_validate_json(f.read_text())
        cid = verdict.case_id or f.stem.removeprefix("case_")
        gt = ground_truth.get(cid)
        if gt is None:
            continue
        scores.append(score_case(verdict, gt))
    if not scores:
        return {"n_cases": 0}
    return {
        "n_cases": len(scores),
        "top1": sum(s.top1_correct for s in scores) / len(scores),
        "topk": sum(s.topk_correct for s in scores) / len(scores),
        "mrr": sum(s.mrr_contribution for s in scores) / len(scores),
        "mean_cost_usd": sum(s.cost_usd for s in scores) / len(scores),
        "per_case": [s.model_dump() for s in scores],
    }


def compare_runs(
    run_a_dir: pathlib.Path,
    run_b_dir: pathlib.Path,
    ground_truth: dict[str, str],
) -> dict:
    """Paired comparison: McNemar on top-1, Wilcoxon signed-rank on MRR."""
    from scipy.stats import wilcoxon
    from statsmodels.stats.contingency_tables import mcnemar

    scores_a = {
        s["case_id"]: CaseScore.model_validate(s)
        for s in score_run(run_a_dir, ground_truth).get("per_case", [])
    }
    scores_b = {
        s["case_id"]: CaseScore.model_validate(s)
        for s in score_run(run_b_dir, ground_truth).get("per_case", [])
    }
    paired_ids = sorted(set(scores_a) & set(scores_b))
    paired = [(scores_a[c], scores_b[c]) for c in paired_ids]
    if not paired:
        return {"n_cases_paired": 0}

    # McNemar contingency table on top-1:
    #   [[both_correct, a_correct_b_wrong], [b_correct_a_wrong, both_wrong]]
    b_correct_a_wrong = sum(1 for a, b in paired if not a.top1_correct and b.top1_correct)
    a_correct_b_wrong = sum(1 for a, b in paired if a.top1_correct and not b.top1_correct)
    contingency = [[0, a_correct_b_wrong], [b_correct_a_wrong, 0]]
    mcnemar_result = mcnemar(contingency, exact=False, correction=True)

    mrr_a = [a.mrr_contribution for a, b in paired]
    mrr_b = [b.mrr_contribution for a, b in paired]
    if all(x == y for x, y in zip(mrr_a, mrr_b, strict=True)):
        wilcoxon_result = {
            "statistic": 0.0,
            "pvalue": 1.0,
            "note": "all pairs equal; test not meaningful",
        }
    else:
        w = wilcoxon(mrr_a, mrr_b)
        wilcoxon_result = {"statistic": float(w.statistic), "pvalue": float(w.pvalue)}

    return {
        "n_cases_paired": len(paired),
        "mcnemar": {
            "statistic": float(mcnemar_result.statistic),
            "pvalue": float(mcnemar_result.pvalue),
        },
        "wilcoxon_mrr": wilcoxon_result,
        "top1_a": sum(1 for a, _ in paired if a.top1_correct) / len(paired),
        "top1_b": sum(1 for _, b in paired if b.top1_correct) / len(paired),
        "mean_cost_a": sum(a.cost_usd for a, _ in paired) / len(paired),
        "mean_cost_b": sum(b.cost_usd for _, b in paired) / len(paired),
    }
