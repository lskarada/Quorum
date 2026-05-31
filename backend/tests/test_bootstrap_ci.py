"""Regression tests for bootstrap_ci utility."""
from scripts.bootstrap_ci import bootstrap_ci


def test_bootstrap_ci_bounds():
    scores = [1] * 8 + [0] * 2  # 0.8 on n=10
    lo, hi = bootstrap_ci(scores, iters=2000, seed=0)
    assert 0.0 <= lo < 0.8 < hi <= 1.0
