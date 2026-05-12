"""Scoring for eval results.

Compares each FinalVerdict against the corresponding case's ground truth and
emits per-case + aggregate metrics: top-1 accuracy, top-5 accuracy, MRR,
mean cost-per-case, mean latency.
"""
from __future__ import annotations

from pathlib import Path


def score_run(results_dir: Path, corpus_name: str) -> dict:
    """Score a completed run.

    Returns a dict with keys:
      top1, top5, mrr, mean_cost_usd, mean_latency_s, n_cases, per_case (list).
    """
    # TODO: load verdicts from results_dir/*.json, load ground truth from
    # data/cases/<corpus_name>/*.json, compute metrics.
    raise NotImplementedError
