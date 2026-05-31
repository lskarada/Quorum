"""Tests for the v3 NEJM-only decontaminated split (splits_v3_nejm.json).

The NEJM data files (dev_nejm_sample.json, nejm_sample.json) are paywalled
and gitignored — absent on a clean clone. Tests that require those files are
skipped if they are not present, mirroring the guard pattern in test_splits.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest

CORPUS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "cases" / "eval_corpus_v2"
)
_NEJM_DEV = CORPUS_DIR / "dev_nejm_sample.json"
_NEJM_EVAL = CORPUS_DIR / "nejm_sample.json"
_NEJM_DATA_PRESENT = _NEJM_DEV.exists() and _NEJM_EVAL.exists()

pytestmark = pytest.mark.skipif(
    not _NEJM_DATA_PRESENT,
    reason="NEJM data files absent (gitignored); skipping on clean clone",
)


def test_nejm_holdout_is_all_nejm_2026():
    from quorum.eval.v2_runner import load_v2_cases

    cases = load_v2_cases(split_file="splits_v3_nejm.json", split_key="holdout")
    assert len(cases) >= 10
    assert all(c.corpus == "nejm" for c in cases)
    assert all(c.case_id.endswith("2026") for c in cases)


def test_dev_and_holdout_disjoint():
    from quorum.eval.v2_runner import load_v2_cases

    dev = {c.case_id for c in load_v2_cases(split_file="splits_v3_nejm.json", split_key="dev")}
    hold = {c.case_id for c in load_v2_cases(split_file="splits_v3_nejm.json", split_key="holdout")}
    assert dev.isdisjoint(hold)


def test_dev_has_at_least_30_nejm():
    from quorum.eval.v2_runner import load_v2_cases

    dev = load_v2_cases(split_file="splits_v3_nejm.json", split_key="dev")
    nejm = [c for c in dev if c.corpus == "nejm"]
    assert len(nejm) >= 30
