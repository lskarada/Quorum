"""Contamination probe for the v3 NEJM-2026 holdout (plan Task 0.5).

For each holdout case, present ONLY the first 1-2 sentences (no workup) and ask
the model for the diagnosis cold. If it names the specific ground-truth answer
without the workup, that case is flagged as a likely-memorization signal.

This does NOT modify the holdout (the goal-prompt holdout is exactly the 12
enumerated ids, run once). The flags are reported as a contamination caveat +
sensitivity analysis in the final write-up — never used to tune any
prompt/threshold/k. Output is intentionally aggregate (case_id + bool only); the
ground-truth diagnoses are never printed, to keep holdout specifics out of the
operator's context.

Usage:
    uv run python scripts/contamination_probe.py \
        --split-file splits_v3_nejm.json --split-key holdout \
        --out ../data/results/contamination_probe_holdout.json

Cost: ~2 Sonnet calls/case (cold guess + match judge), ~$0.25 for 12 cases.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re

from dotenv import load_dotenv

from quorum.eval.v2_runner import load_v2_cases
from quorum.llm.client import LLMClient

load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")

_MODEL = "anthropic/claude-sonnet-4-6"

_GUESS_SYSTEM = (
    "You are a diagnostician. You will be shown only the opening of a clinical "
    "case (no workup, no labs, no imaging). Name the single most likely specific "
    "diagnosis. Respond with ONLY the diagnosis name, no explanation."
)

_MATCH_SYSTEM = (
    "You judge whether two diagnosis strings refer to the same clinical entity. "
    "Account for synonyms, abbreviations, and specificity. Respond strict JSON: "
    '{"match": true|false}.'
)


def _first_sentences(text: str, n: int = 2) -> str:
    """Return the first n sentences of text (best-effort splitter)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n]).strip()


async def _probe_case(llm: LLMClient, opening: str, truth: str) -> tuple[str, bool]:
    """Return (cold_guess, is_match) for one case."""
    guess_resp = await llm.complete(
        messages=[
            {"role": "system", "content": _GUESS_SYSTEM},
            {"role": "user", "content": f"Case opening:\n{opening}"},
        ],
        model=_MODEL,
        max_tokens=64,
        temperature=0.0,
    )
    guess = (guess_resp.content or "").strip()

    match_resp = await llm.complete(
        messages=[
            {"role": "system", "content": _MATCH_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Diagnosis A (model's cold guess): {guess}\n"
                    f"Diagnosis B (ground truth): {truth}\n"
                    "Do A and B refer to the same clinical entity?"
                ),
            },
        ],
        model=_MODEL,
        response_format={"type": "json_object"},
        max_tokens=32,
        temperature=0.0,
    )
    try:
        is_match = bool(json.loads(match_resp.content).get("match", False))
    except (json.JSONDecodeError, AttributeError):
        is_match = False
    return guess, is_match


async def main() -> None:
    ap = argparse.ArgumentParser(description="Holdout contamination probe")
    ap.add_argument("--split-file", default="splits_v3_nejm.json")
    ap.add_argument("--split-key", default="holdout")
    ap.add_argument("--sentences", type=int, default=2)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cases = load_v2_cases(split_file=args.split_file, split_key=args.split_key)
    if not cases:
        raise SystemExit(
            f"No cases for split-file={args.split_file} split-key={args.split_key}"
        )

    llm = LLMClient()
    results = []
    total_cost = 0.0
    for case in sorted(cases, key=lambda c: c.case_id):
        opening = _first_sentences(case.initial_presentation, args.sentences)
        guess, is_match = await _probe_case(llm, opening, case.ground_truth_diagnosis)
        results.append({"case_id": case.case_id, "memorized": is_match})
        # Print only the flag, never the diagnoses, to keep holdout specifics out.
        print(f"  {case.case_id:20} memorized_cold={is_match}")

    n = len(results)
    n_mem = sum(r["memorized"] for r in results)
    summary = {
        "split_file": args.split_file,
        "split_key": args.split_key,
        "sentences_shown": args.sentences,
        "model": _MODEL,
        "n_cases": n,
        "n_recalled_cold": n_mem,
        "fraction_recalled_cold": round(n_mem / n, 3) if n else 0.0,
        "flagged_case_ids": [r["case_id"] for r in results if r["memorized"]],
        "per_case": results,
    }
    print(
        f"\nContamination probe: {n_mem}/{n} holdout cases recalled cold "
        f"({summary['fraction_recalled_cold']:.1%}) from {args.sentences} "
        f"opening sentence(s)."
    )

    if args.out:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2))
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
