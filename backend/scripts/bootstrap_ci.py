"""Bootstrap confidence interval for small-n accuracy reporting."""
import random


def bootstrap_ci(
    scores: list[int],
    iters: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Return (lower, upper) bootstrap CI for the mean of binary scores.

    Args:
        scores: List of 0/1 correctness scores.
        iters: Number of bootstrap resamples.
        seed: RNG seed for reproducibility.
        alpha: Significance level (default 0.05 → 95% CI).

    Returns:
        (lo, hi) confidence interval bounds.
    """
    rng = random.Random(seed)
    n = len(scores)
    means = []
    for _ in range(iters):
        means.append(sum(scores[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return means[int(alpha / 2 * iters)], means[int((1 - alpha / 2) * iters)]
