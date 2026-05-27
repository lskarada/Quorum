"""Build deterministic TUNE/EVAL split for the v2 benchmark corpus.

Seed is fixed at 20260526 (the spec date). Re-running this script must
produce byte-identical output.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 20260526
CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cases" / "eval_corpus_v2"
SAMPLE_FILES = ["nejm_sample.json", "mcr_sample.json", "rarebench_sample.json"]
TUNE_N = 5
EVAL_N = 30


def main() -> None:
    all_ids: list[str] = []
    for f in SAMPLE_FILES:
        cases = json.loads((CORPUS_DIR / f).read_text())
        all_ids.extend(c["case_id"] for c in cases)

    assert len(all_ids) == TUNE_N + EVAL_N, f"Expected 35 cases, got {len(all_ids)}"

    rng = random.Random(SEED)
    all_ids_sorted = sorted(all_ids)
    shuffled = all_ids_sorted[:]
    rng.shuffle(shuffled)

    splits = {
        "tune": sorted(shuffled[:TUNE_N]),
        "eval": sorted(shuffled[TUNE_N:]),
        "_provenance": {
            "seed": SEED,
            "source_files": SAMPLE_FILES,
            "tune_n": TUNE_N,
            "eval_n": EVAL_N,
        },
    }
    (CORPUS_DIR / "splits.json").write_text(json.dumps(splits, indent=2) + "\n")
    print(f"Wrote splits: {TUNE_N} TUNE + {EVAL_N} EVAL")


if __name__ == "__main__":
    main()
