"""Calibration metric tests (Phase 4 Task 4.1)."""
from __future__ import annotations

import pytest
from quorum.calibration.metrics import compute_brier, compute_ece


def test_brier_perfect_prediction():
    assert compute_brier({"a": 1.0, "b": 0.0}, "a") == pytest.approx(0.0)


def test_brier_uniform_two_outcomes():
    # 0.5 each, truth = "a" → (1-0.5)^2 + (0-0.5)^2 = 0.5
    assert compute_brier({"a": 0.5, "b": 0.5}, "a") == pytest.approx(0.5)


def test_brier_wrong_prediction():
    # Truth = "a", posterior gives 0 → (0-1)^2 + (1-0)^2 = 2.0
    assert compute_brier({"a": 0.0, "b": 1.0}, "a") == pytest.approx(2.0)


def test_brier_handles_missing_truth_label():
    """Truth absent from posterior is treated as implicit 0 probability."""
    assert compute_brier({"a": 1.0, "b": 0.0}, "c") == pytest.approx(2.0)


def test_ece_perfect_calibration_uniform():
    posteriors = [{"a": 0.5, "b": 0.5}] * 10
    truths = ["a"] * 5 + ["b"] * 5
    # Top-1 confidence is 0.5; top-1 picks "a" (first key). Accuracy = 5/10 = 0.5.
    assert compute_ece(posteriors, truths, n_bins=2) < 0.01


def test_ece_total_miscalibration():
    posteriors = [{"a": 0.95, "b": 0.05}] * 10
    truths = ["b"] * 10
    ece = compute_ece(posteriors, truths, n_bins=5)
    assert ece > 0.8


def test_ece_empty_inputs_returns_zero():
    assert compute_ece([], [], n_bins=10) == 0.0


def test_ece_skips_empty_posteriors():
    posteriors = [{}, {"a": 0.9, "b": 0.1}]
    truths = ["a", "a"]
    # Only the second posterior contributes; confidence=0.9, acc=1.0 → ECE=|0.9-1.0|=0.1
    assert compute_ece(posteriors, truths, n_bins=2) == pytest.approx(0.1, abs=0.01)
