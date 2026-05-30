"""Augment the v2 DEV tuning set with deterministic, EVAL/TUNE-disjoint MCR cases.

The DEV set tunes the P3 optimization loop WITHOUT ever touching EVAL. NEJM DEV
cases live in dev_nejm_sample.json (gitignored, paywalled). This script adds public,
MIT-licensed MedCaseReasoning (MCR) cases as dev_mcr_sample.json (committable).

Seed is fixed at 20260530 (campaign date); re-running must produce identical output.
Every MCR id already used in splits.json (tune+eval) and every NEJM DEV id is excluded,
so DEV ∩ (TUNE ∪ EVAL) = ∅ is preserved by construction.

Run:  python3 backend/scripts/build_dev_augment.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 20260530
N = 15
ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS_DIR = ROOT / "data" / "cases" / "eval_corpus_v2"
POOL_FILE = ROOT / "data" / "cases" / "mcr" / "all.json"


def main() -> None:
    pool = {it["case_id"]: it for it in json.loads(POOL_FILE.read_text())}
    sample = json.loads((CORPUS_DIR / "mcr_sample.json").read_text())
    splits = json.loads((CORPUS_DIR / "splits.json").read_text())
    nejm_dev = json.loads((CORPUS_DIR / "dev_nejm_sample.json").read_text())

    # Verify the pool->committed-sample field mapping on the 10 known cases before
    # trusting it to mint new ones. (final_diagnosis->ground_truth_diagnosis, reasoning->reasoning_trace.)
    for s in sample:
        p = pool[s["case_id"].removeprefix("mcr-")]
        assert s["presentation"].strip() == p["presentation"].strip()
        assert s["ground_truth_diagnosis"].strip() == p["final_diagnosis"].strip()
        assert s["reasoning_trace"].strip() == p["reasoning"].strip()

    used = set(splits["tune"]) | set(splits["eval"]) | {c["case_id"] for c in nejm_dev}
    used_pmc = {u.removeprefix("mcr-") for u in used if u.startswith("mcr-")}

    candidates = sorted(pid for pid in pool if pid not in used_pmc)
    picks = sorted(random.Random(SEED).sample(candidates, N))

    dev_mcr = [
        {
            "case_id": f"mcr-{pid}",
            "source": "MedCaseReasoning (PMC)",
            "corpus": "mcr",
            "presentation": pool[pid]["presentation"],
            "ground_truth_diagnosis": pool[pid]["final_diagnosis"],
            "reasoning_trace": pool[pid]["reasoning"],
        }
        for pid in picks
    ]

    dev_ids = {c["case_id"] for c in dev_mcr}
    assert len(dev_ids) == N, f"expected {N} unique ids, got {len(dev_ids)}"
    overlap = dev_ids & used
    assert not overlap, f"DEV/EVAL/TUNE overlap: {overlap}"

    out = CORPUS_DIR / "dev_mcr_sample.json"
    out.write_text(json.dumps(dev_mcr, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {out.name}: {len(dev_mcr)} MCR cases (seed={SEED}), disjoint from {len(used)} used ids")
    for c in dev_mcr:
        print("  ", c["case_id"], "->", c["ground_truth_diagnosis"][:70])


if __name__ == "__main__":
    main()
