"""Quick per-case summary of a v2 benchmark run.

Pulls case_id, ground_truth, committed_diagnosis, top-1 posterior,
real cost, and turn count out of every .audit.jsonl in the run dir.
Stand-alone — no API calls. Intended for fast eyeballing after a TUNE
or EVAL run finishes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from quorum.eval.eval_case import load_corpus


def main(run_dir: Path) -> None:
    cases_by_id = {c.case_id: c for c in load_corpus()}

    print(f"{'case_id':<22}{'truth':<28}{'committed':<28}{'topP':>6}{'cost':>8}{'turns':>6}")
    print("-" * 100)

    total_cost = 0.0
    for path in sorted(run_dir.glob("*.audit.jsonl")):
        lines = path.read_text().strip().splitlines()
        if not lines:
            continue
        header = json.loads(lines[0])
        cid = header["case_id"]
        committed = header.get("final_committed_diagnosis") or "(none)"
        post = header.get("final_posterior", {})
        top_p = max(post.values()) if post else 0.0
        cost = header.get("real_cost_usd") or 0.0
        total_cost += cost
        turns = len([
            json.loads(l) for l in lines[1:]
            if json.loads(l).get("agent") == "hypothesis"
        ])
        case = cases_by_id.get(cid)
        gt = (case.ground_truth_diagnosis if case else "?")[:25]
        print(
            f"{cid:<22}{gt:<28}{committed[:25]:<28}"
            f"{top_p:>6.2f}${cost:>7.4f}{turns:>6}"
        )

    print("-" * 100)
    print(f"Total real cost: ${total_cost:.4f}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: summarize_v2_run.py <run_dir>", file=sys.stderr)
        sys.exit(2)
    main(Path(sys.argv[1]))
