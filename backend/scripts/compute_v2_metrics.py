"""Aggregate v2 headline metrics from audit files + judge results.

Reads a run directory written by quorum.eval.v2_runner and emits:
- top-1 accuracy (full_credit fraction)
- top-1-or-partial fraction
- mean Brier across cases (skips cases with empty posterior)
- ECE across cases
- audit completeness rate
- real & simulated cost totals + means

Usage:
    python3 backend/scripts/compute_v2_metrics.py data/results/<run_id>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from quorum.calibration.metrics import compute_brier, compute_ece
from quorum.eval.eval_case import load_corpus, load_dev_corpus

REQUIRED_AUDIT_AGENTS = {
    "hypothesis", "test_chooser", "challenger", "stewardship",
    "checklist", "gatekeeper", "safety_checker",
}


def main(run_dir: Path) -> dict:
    # Union with DEV so DEV run dirs resolve ground-truth for Brier/ECE; ids are
    # disjoint from TUNE/EVAL, so eval/tune metrics are unaffected.
    cases_by_id = {c.case_id: c for c in (load_corpus() + load_dev_corpus())}
    audits = []
    audit_completeness_scores = []

    for audit_path in sorted(run_dir.glob("*.audit.jsonl")):
        lines = audit_path.read_text().strip().splitlines()
        if not lines:
            continue
        header = json.loads(lines[0])
        turns = [json.loads(line) for line in lines[1:]]
        audits.append({**header, "turns": turns})
        # Audit completeness: was every required agent type seen at least once?
        agents_seen = {t.get("agent") for t in turns}
        audit_completeness_scores.append(
            sum(1 for a in REQUIRED_AUDIT_AGENTS if a in agents_seen)
            / len(REQUIRED_AUDIT_AGENTS)
        )

    judge_path = run_dir / "judge_results.json"
    judge = json.loads(judge_path.read_text()) if judge_path.exists() else {}

    n = len(audits)
    if n == 0:
        return {"error": "no audit files found in run dir"}

    n_full = sum(
        1 for a in audits if judge.get(a["case_id"], {}).get("score") == "full_credit"
    )
    n_partial = sum(
        1 for a in audits if judge.get(a["case_id"], {}).get("score") == "partial_credit"
    )

    # Calibration: use final_posterior + ground truth
    posteriors: list[dict[str, float]] = []
    truths: list[str] = []
    briers: list[float] = []
    for a in audits:
        post = a.get("final_posterior") or {}
        case = cases_by_id.get(a["case_id"])
        if not post or case is None:
            continue
        posteriors.append(post)
        truths.append(case.ground_truth_diagnosis)
        # Use the AI-committed label if present in posterior; otherwise the
        # ground-truth label (with implicit 0 prob → adds 1.0 Brier).
        briers.append(compute_brier(post, case.ground_truth_diagnosis))

    mean_brier = sum(briers) / len(briers) if briers else None
    ece = compute_ece(posteriors, truths, n_bins=10) if posteriors else None

    return {
        "run_dir": str(run_dir),
        "n_cases": n,
        "n_full_credit": n_full,
        "n_partial_credit": n_partial,
        "top_1_accuracy": n_full / n,
        "top_1_or_partial": (n_full + n_partial) / n,
        "mean_brier": mean_brier,
        "ece": ece,
        "audit_completeness_rate": (
            sum(audit_completeness_scores) / n if audit_completeness_scores else None
        ),
        "mean_real_cost_usd": sum(a.get("real_cost_usd", 0) for a in audits) / n,
        "total_real_cost_usd": sum(a.get("real_cost_usd", 0) for a in audits),
        "mean_simulated_cost_usd": sum(a.get("simulated_cost_usd", 0) for a in audits) / n,
        "total_simulated_cost_usd": sum(a.get("simulated_cost_usd", 0) for a in audits),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: compute_v2_metrics.py <run_dir>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(main(Path(sys.argv[1])), indent=2))
