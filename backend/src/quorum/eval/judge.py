"""LLM-as-judge for diagnostic scoring (Phase 7 Task 7.4).

Scores a committed diagnosis against the case's ground truth and an
optional list of acceptable_partial_credit synonyms. The judge returns
one of three labels: full_credit, partial_credit, or no_credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from quorum.audit.schemas import CaseAudit, TurnRecord
from quorum.eval.eval_case import EvalCase
from quorum.llm.client import LLMClient

JudgeScore = Literal["full_credit", "partial_credit", "no_credit"]

JUDGE_SYSTEM = (
    "You are evaluating whether a diagnostic AI's final committed diagnosis "
    "matches the ground truth from a published clinical case."
)

JUDGE_USER_TEMPLATE = """GROUND_TRUTH: {ground_truth}
ACCEPTABLE_PARTIAL_CREDIT: {acceptable}
AI_COMMITTED: {ai_committed}

Score one of three:
- "full_credit": AI committed to the GROUND_TRUTH, or a synonymous/equivalent rephrasing.
- "partial_credit": AI committed to one of ACCEPTABLE_PARTIAL_CREDIT entries, or a diagnosis capturing disease category but missing specifics.
- "no_credit": AI committed to something not in either list.

Provide a one-sentence rationale.

Respond as strict JSON: {{"score": ..., "rationale": "..."}}"""


async def judge_case(
    *,
    ground_truth: str,
    acceptable_partial_credit: list[str],
    ai_committed: str,
    llm: LLMClient,
    model: str = "anthropic/claude-sonnet-4-6",
) -> tuple[JudgeScore, str]:
    user = JUDGE_USER_TEMPLATE.format(
        ground_truth=ground_truth,
        acceptable=json.dumps(acceptable_partial_credit),
        ai_committed=ai_committed,
    )
    resp = await llm.complete(
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user},
        ],
        model=model,
        response_format={"type": "json_object"},
        max_tokens=200,
    )
    try:
        obj = json.loads(resp.content)
        score = obj["score"]
        rationale = obj.get("rationale", "")
        if score not in ("full_credit", "partial_credit", "no_credit"):
            return "no_credit", f"judge returned unknown score {score!r}"
        return score, rationale
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return "no_credit", f"judge parse failure: {exc!s} | raw={resp.content[:120]!r}"


async def judge_run_dir(
    run_dir: Path,
    cases_by_id: dict[str, EvalCase],
    llm: LLMClient,
    *,
    model: str = "anthropic/claude-sonnet-4-6",
) -> dict[str, dict]:
    """Judge every <case>.audit.jsonl in run_dir; write judge_results.json.

    Returns the in-memory dict keyed by case_id. Idempotent: existing
    entries in judge_results.json are preserved.
    """
    results_path = run_dir / "judge_results.json"
    results: dict[str, dict] = (
        json.loads(results_path.read_text()) if results_path.exists() else {}
    )

    for audit_path in sorted(run_dir.glob("*.audit.jsonl")):
        case_id = audit_path.stem.replace(".audit", "")
        if case_id in results:
            continue
        case = cases_by_id.get(case_id)
        if case is None:
            results[case_id] = {"score": "no_credit", "rationale": "case not found in corpus"}
            continue
        header = json.loads(audit_path.read_text().splitlines()[0])
        committed = header.get("final_committed_diagnosis") or "(none)"
        score, rationale = await judge_case(
            ground_truth=case.ground_truth_diagnosis,
            acceptable_partial_credit=case.acceptable_partial_credit,
            ai_committed=committed,
            llm=llm,
            model=model,
        )
        results[case_id] = {
            "score": score,
            "rationale": rationale,
            "ground_truth": case.ground_truth_diagnosis,
            "ai_committed": committed,
        }
        results_path.write_text(json.dumps(results, indent=2))
    return results
