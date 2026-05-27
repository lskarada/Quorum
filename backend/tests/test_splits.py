"""TUNE/EVAL split tests for the v2 benchmark corpus."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

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
