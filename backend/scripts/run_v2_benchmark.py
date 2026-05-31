"""Top-level entry point for the v2 (Calibrated-Auditable MAI-DxO) benchmark.

Thin wrapper around quorum.eval.v2_runner. Named explicitly so the
spend-gate PreToolUse hook recognizes invocations and applies the
$142 hard stop / $135 warn check against data/results/.spend_total.txt.

Examples
--------

Smoke (1 TUNE case, short max_turns to control cost):
    uv run python backend/scripts/run_v2_benchmark.py \
        --arm arm_a --panel v2_quorum_calibrated --split tune -n 1 \
        --max-turns 8 --confirm-cost

Full headline EVAL Arm A:
    uv run python backend/scripts/run_v2_benchmark.py \
        --arm arm_a --panel v2_quorum_calibrated --split eval \
        --run-id v2-arm-a-final --confirm-cost

Full headline EVAL Arm B (single Sonnet):
    uv run python backend/scripts/run_v2_benchmark.py \
        --arm arm_b --panel v2_single_sonnet --split eval \
        --run-id v2-arm-b-final --confirm-cost
"""
from __future__ import annotations

import argparse
import asyncio
import pathlib

from dotenv import load_dotenv

from quorum.eval.v2_runner import run

load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")


def main() -> None:
    ap = argparse.ArgumentParser(description="v2 benchmark runner")
    ap.add_argument("--arm", choices=("arm_a", "arm_b"), required=True)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--split", choices=("tune", "eval", "dev"), default=None)
    ap.add_argument("--case-id", default=None)
    ap.add_argument("-n", type=int, default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--commit-threshold", type=float, default=0.70)
    ap.add_argument("--confirm-cost", action="store_true")
    ap.add_argument("--split-file", default=None)
    ap.add_argument("--split-key", default=None)
    ap.add_argument("--temperature", type=float, default=None)
    args = ap.parse_args()

    out = asyncio.run(
        run(
            args.arm,
            panel_name=args.panel,
            split=args.split,
            case_id=args.case_id,
            n=args.n,
            run_id=args.run_id,
            max_turns=args.max_turns,
            commit_threshold=args.commit_threshold,
            confirm_cost=args.confirm_cost,
            split_file=args.split_file,
            split_key=args.split_key,
            temperature=args.temperature,
        )
    )
    print(f"Wrote results to {out}")


if __name__ == "__main__":
    main()
