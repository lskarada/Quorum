"""Run LLM-as-judge over a v2 benchmark run directory.

Reads every <case>.audit.jsonl in the run dir, scores the committed
diagnosis against ground_truth + acceptable_partial_credit, and writes
judge_results.json (idempotent — already-judged cases are kept).

Example
-------
    bash backend/scripts/log_spend.sh 0.00 "phase-7 judge run start"
    set -a && source .env && set +a
    uv run python backend/scripts/judge_v2_run.py \
        data/results/v2-arm-a-final --judge-model anthropic/claude-sonnet-4-6
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from quorum.eval.eval_case import load_corpus
from quorum.eval.judge import judge_run_dir
from quorum.llm.client import LLMClient


def main() -> None:
    ap = argparse.ArgumentParser(description="LLM-as-judge for v2 audit dirs")
    ap.add_argument("run_dir", type=Path, help="data/results/<run_id>")
    ap.add_argument("--judge-model", default="anthropic/claude-sonnet-4-6")
    args = ap.parse_args()

    if not args.run_dir.exists():
        raise SystemExit(f"run dir not found: {args.run_dir}")

    cases_by_id = {c.case_id: c for c in load_corpus()}
    llm = LLMClient()
    results = asyncio.run(
        judge_run_dir(args.run_dir, cases_by_id, llm, model=args.judge_model)
    )
    print(f"Wrote {args.run_dir / 'judge_results.json'} with {len(results)} entries.")


if __name__ == "__main__":
    main()
