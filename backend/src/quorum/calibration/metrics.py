"""Calibration metrics: Brier score and Expected Calibration Error.

- Brier: multi-class form summed over candidate diagnoses. If the
  ground truth is absent from the posterior, treat it as if a class
  with probability 0 was present (adds (0-1)^2 = 1 to the score).
- ECE: equal-width binning on top-1 confidence (Naeini et al. 2015).
  Items with confidence c land in bin floor(c * n_bins). Bin n_bins
  rolls into the top bin (n_bins - 1).
"""
from __future__ import annotations


def compute_brier(posterior: dict[str, float], ground_truth: str) -> float:
    score = 0.0
    seen_truth = False
    for label, p in posterior.items():
        y = 1.0 if label == ground_truth else 0.0
        if label == ground_truth:
            seen_truth = True
        score += (p - y) ** 2
    if not seen_truth:
        score += 1.0  # (0 - 1)^2 for the missing-truth class
    return score


def compute_ece(
    posteriors: list[dict[str, float]],
    truths: list[str],
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error using equal-frequency bins on top-1 confidence."""
    assert len(posteriors) == len(truths), "posteriors and truths must align"
    if not posteriors:
        return 0.0

    confidences: list[float] = []
    correct: list[float] = []
    for post, truth in zip(posteriors, truths, strict=True):
        if not post:
            continue
        top_label = max(post, key=post.get)
        confidences.append(post[top_label])
        correct.append(1.0 if top_label == truth else 0.0)

    if not confidences:
        return 0.0

    total = len(confidences)
    bins: list[list[tuple[float, float]]] = [[] for _ in range(n_bins)]
    for conf, acc in zip(confidences, correct, strict=True):
        idx = min(int(conf * n_bins), n_bins - 1)
        bins[idx].append((conf, acc))

    ece = 0.0
    for chunk in bins:
        if not chunk:
            continue
        avg_conf = sum(c for c, _ in chunk) / len(chunk)
        avg_acc = sum(a for _, a in chunk) / len(chunk)
        ece += (len(chunk) / total) * abs(avg_conf - avg_acc)
    return ece
