"""TUNE/EVAL split tests for the v2 benchmark corpus."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from quorum.eval.eval_case import load_dev_corpus

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPLITS_PATH = REPO_ROOT / "data" / "cases" / "eval_corpus_v2" / "splits.json"
BUILDER = REPO_ROOT / "backend" / "scripts" / "build_eval_splits.py"


def test_splits_file_structure():
    assert SPLITS_PATH.exists(), "splits.json must exist (run build_eval_splits.py)"
    splits = json.loads(SPLITS_PATH.read_text())
    assert "tune" in splits and "eval" in splits
    assert len(splits["tune"]) == 5
    assert len(splits["eval"]) == 30
    # No overlap
    assert set(splits["tune"]).isdisjoint(set(splits["eval"]))
    # All 35 unique IDs
    all_ids = set(splits["tune"]) | set(splits["eval"])
    assert len(all_ids) == 35


def test_split_deterministic():
    """Re-running the build script must produce byte-identical splits."""
    snapshot = SPLITS_PATH.read_text()
    subprocess.run(["python3", str(BUILDER)], check=True, cwd=str(REPO_ROOT))
    re_run = SPLITS_PATH.read_text()
    assert snapshot == re_run, "splits.json must be deterministic"


# --- DEV-set integrity (held SEPARATE from splits.json) -------------------
# The NEJM dev file is paywalled + gitignored, so it may be absent on a clean
# clone/CI; these tests assert what is invariant either way. The MCR dev file
# is committed, so its 15 cases are always present.

def test_dev_disjoint_from_splits():
    """No DEV case may leak into TUNE/EVAL — the anti-leakage guarantee."""
    dev_ids = {c.case_id for c in load_dev_corpus()}
    splits = json.loads(SPLITS_PATH.read_text())
    heldout = set(splits["tune"]) | set(splits["eval"])
    assert dev_ids.isdisjoint(heldout), (
        f"DEV cases overlap TUNE/EVAL: {sorted(dev_ids & heldout)}"
    )


def test_dev_no_duplicate_ids():
    dev_ids = [c.case_id for c in load_dev_corpus()]
    dupes = sorted({i for i in dev_ids if dev_ids.count(i) > 1})
    assert not dupes, f"duplicate DEV case_ids: {dupes}"


def test_dev_cases_well_formed():
    """Every loaded DEV case has a presentation + gold dx; NEJM cases carry
    available_findings (the sequential-disclosure Gatekeeper path)."""
    dev = load_dev_corpus()
    mcr = [c for c in dev if c.corpus == "mcr"]
    nejm = [c for c in dev if c.corpus == "nejm"]
    assert len(mcr) == 15, f"expected 15 committed MCR dev cases, got {len(mcr)}"
    for c in dev:
        assert c.initial_presentation.strip(), f"{c.case_id} empty presentation"
        assert c.ground_truth_diagnosis.strip(), f"{c.case_id} empty diagnosis"
    for c in nejm:  # empty on a paywalled-free clone; checked only when present
        assert c.available_findings, f"{c.case_id} missing available_findings"
