"""Markdown report generator for eval runs.

Renders the headline metrics (top-1, top-5, MRR, mean cost), an optional
paired-comparison section (panel A vs B with McNemar + Wilcoxon p-values),
and a per-case table.
"""
from __future__ import annotations

import pathlib


def build_report(
    scores: dict,
    output_path: pathlib.Path,
    comparison: dict | None = None,
) -> pathlib.Path:
    """Write a markdown report from `scores` (output of scorer.score_run).

    If `comparison` (output of scorer.compare_runs) is provided and contains
    paired cases, an additional A-vs-B section is rendered.
    """
    lines: list[str] = ["# Quorum eval results\n"]
    if scores.get("n_cases", 0) == 0:
        lines.append("No cases scored.\n")
        output_path.write_text("\n".join(lines))
        return output_path

    lines.append(f"## Headline (n={scores['n_cases']})\n")
    lines.append("| Metric | Value |\n|--------|-------|\n")
    lines.append(f"| top-1 accuracy | {scores['top1']:.1%} |\n")
    lines.append(f"| top-5 accuracy | {scores['topk']:.1%} |\n")
    lines.append(f"| MRR | {scores['mrr']:.3f} |\n")
    lines.append(f"| Mean cost / case | ${scores['mean_cost_usd']:.4f} |\n")

    if comparison and comparison.get("n_cases_paired", 0) > 0:
        lines.append("\n## Comparison (paired)\n")
        lines.append("| Metric | Panel A | Panel B |\n|--------|---------|---------|\n")
        lines.append(
            f"| top-1  | {comparison['top1_a']:.1%} | {comparison['top1_b']:.1%} |\n"
        )
        lines.append(
            f"| Mean cost | ${comparison['mean_cost_a']:.4f} "
            f"| ${comparison['mean_cost_b']:.4f} |\n"
        )
        lines.append(f"\nMcNemar p={comparison['mcnemar']['pvalue']:.4f}\n")
        lines.append(f"Wilcoxon (MRR) p={comparison['wilcoxon_mrr']['pvalue']:.4f}\n")

    if scores.get("per_case"):
        lines.append("\n## Per-case\n")
        lines.append(
            "| case_id | top-1 | top-5 | rank | MRR | cost |\n"
            "|---------|-------|-------|------|-----|------|\n"
        )
        for c in scores["per_case"]:
            lines.append(
                f"| {c['case_id']} "
                f"| {'YES' if c['top1_correct'] else 'no'} "
                f"| {'YES' if c['topk_correct'] else 'no'} "
                f"| {c['rank_of_truth'] if c['rank_of_truth'] is not None else '-'} "
                f"| {c['mrr_contribution']:.3f} "
                f"| ${c['cost_usd']:.4f} |\n"
            )

    output_path.write_text("".join(lines))
    return output_path
