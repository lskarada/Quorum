"""Ensemble baseline runner — N independent Hypothesis calls + majority vote.

H2 control for the v2 benchmark: without this, "5-agent debate beats single
call" is confounded with "5 samples beats 1 sample". The ensemble issues
n_votes independent calls to the SAME model with the SAME hypothesis prompt
(no panel, no Challenger / Stewardship / Checklist) and majority-votes the
top-1 diagnosis. The aggregated verdict is FinalVerdict-compatible so the
existing scorer / report pipeline handles it without ensemble-aware branches.
"""
from __future__ import annotations

import asyncio
import logging
import pathlib
import time
from collections import Counter

from pydantic import BaseModel

from quorum.llm.client import LLMClient
from quorum.orchestrator.agents.hypothesis import HypothesisAgent
from quorum.orchestrator.schemas import (
    AgentMessage,
    CaseInput,
    DiagnosisCandidate,
    Differential,
    FinalVerdict,
)

logger = logging.getLogger(__name__)

_HYPOTHESIS_PROMPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "orchestrator"
    / "prompts"
    / "hypothesis.md"
)


class EnsembleStats(BaseModel):
    """Per-case ensemble statistics. Persisted in manifest.per_case[case_id]."""

    n_votes_requested: int
    n_votes_successful: int
    n_votes_failed: int
    vote_distribution: dict[str, int]
    top_vote_count: int


def _load_hypothesis_prompt() -> str:
    return _HYPOTHESIS_PROMPT_PATH.read_text()


async def run_ensemble(
    case: CaseInput,
    model: str,
    n_votes: int,
    llm: LLMClient,
    prompt_template: str | None = None,
) -> tuple[FinalVerdict, EnsembleStats]:
    """Run `n_votes` independent Hypothesis calls; majority-vote the top-1.

    Returns (verdict, stats). Failures degrade the ensemble gracefully:
    if k of n_votes calls raise, the verdict is built from the remaining
    n_votes-k votes and stats.n_votes_failed records the drop. If all fail,
    verdict.is_error=True.
    """
    prompt = prompt_template or _load_hypothesis_prompt()
    agent = HypothesisAgent(llm=llm, model=model)
    # Bypass disk read — the ensemble may use a held-out or custom prompt.
    agent._prompt_template = prompt

    messages: list[AgentMessage] = []
    n_failed = 0
    total_cost = 0.0
    total_tokens = 0

    for vote_idx in range(n_votes):
        try:
            msg = await agent.deliberate(case, transcript=[], iteration=1)
            messages.append(msg)
            total_cost += msg.cost_usd
            total_tokens += msg.tokens_used
        except Exception as exc:
            n_failed += 1
            logger.warning(
                "ensemble vote %d/%d failed for case %s: %s",
                vote_idx + 1, n_votes, case.case_id, exc,
            )

    if not messages:
        verdict = FinalVerdict(
            case_id=case.case_id,
            final_differential=Differential(candidates=[], iteration=1),
            confidence=0.0,
            iterations_used=1,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            transcript=[],
            termination_reason="error",
            is_error=True,
        )
        stats = EnsembleStats(
            n_votes_requested=n_votes,
            n_votes_successful=0,
            n_votes_failed=n_failed,
            vote_distribution={},
            top_vote_count=0,
        )
        return verdict, stats

    # Tally votes on the top-1 candidate (normalized name) from each call.
    representatives: dict[str, DiagnosisCandidate] = {}
    counter: Counter[str] = Counter()
    for msg in messages:
        diff = msg.structured_output
        if not isinstance(diff, Differential) or not diff.candidates:
            continue
        top = diff.candidates[0]
        key = top.name.lower().strip()
        if key not in representatives:
            representatives[key] = top
        counter[key] += 1

    if not counter:
        # Every successful response had an empty differential — degenerate.
        verdict = FinalVerdict(
            case_id=case.case_id,
            final_differential=Differential(candidates=[], iteration=1),
            confidence=0.0,
            iterations_used=1,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            transcript=messages,
            termination_reason="error",
            is_error=True,
        )
        stats = EnsembleStats(
            n_votes_requested=n_votes,
            n_votes_successful=len(messages),
            n_votes_failed=n_failed,
            vote_distribution={},
            top_vote_count=0,
        )
        return verdict, stats

    n_successful_votes = sum(counter.values())
    ordered = counter.most_common()
    top_vote_count = ordered[0][1]
    aggregated_candidates = [
        representatives[key].model_copy(
            update={"posterior": count / n_successful_votes}
        )
        for key, count in ordered
    ]
    aggregated = Differential(candidates=aggregated_candidates, iteration=1)
    confidence = top_vote_count / n_votes

    verdict = FinalVerdict(
        case_id=case.case_id,
        final_differential=aggregated,
        confidence=confidence,
        iterations_used=1,
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
        transcript=messages,
        termination_reason="consensus",
        is_error=False,
    )
    stats = EnsembleStats(
        n_votes_requested=n_votes,
        n_votes_successful=len(messages),
        n_votes_failed=n_failed,
        vote_distribution=dict(counter),
        top_vote_count=top_vote_count,
    )
    return verdict, stats


async def run_ensemble_corpus(
    cases: list[CaseInput],
    model: str,
    n_votes: int,
    label: str,
    results_dir: pathlib.Path,
    llm: LLMClient | None = None,
) -> pathlib.Path:
    """Run the ensemble over a corpus, writing per-case verdicts + manifest.

    Same on-disk shape as `run_eval` so the existing scorer can read the
    results directory without ensemble-aware branches. The manifest adds
    ensemble-specific fields (model, n_votes, per_case_stats).
    Idempotent: re-running into the same dir skips completed cases.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    llm = llm or LLMClient()

    manifest_path = results_dir / "manifest.json"
    if manifest_path.exists():
        manifest = _read_json(manifest_path)
    else:
        manifest = {
            "schema_version": 1,
            "panel": label,
            "mechanism": "ensemble",
            "model": model,
            "n_votes": n_votes,
            "n_cases": len(cases),
            "started_at": time.time(),
            "per_case_stats": {},
        }
    _write_json(manifest_path, manifest)

    per_case_stats: dict[str, dict] = dict(manifest.get("per_case_stats", {}))

    for case in cases:
        cid = case.case_id or "unknown"
        out_path = results_dir / f"case_{cid}.json"
        if out_path.exists():
            continue
        verdict, stats = await run_ensemble(case, model, n_votes, llm)
        out_path.write_text(verdict.model_dump_json(indent=2))
        per_case_stats[cid] = stats.model_dump()
        manifest["per_case_stats"] = per_case_stats
        manifest["finished_at"] = time.time()
        _write_json(manifest_path, manifest)

    manifest["finished_at"] = time.time()
    _write_json(manifest_path, manifest)
    return results_dir


def _read_json(p: pathlib.Path) -> dict:
    import json
    return json.loads(p.read_text())


def _write_json(p: pathlib.Path, data: dict) -> None:
    import json
    p.write_text(json.dumps(data, indent=2))


__all__ = [
    "EnsembleStats",
    "run_ensemble",
    "run_ensemble_corpus",
]


# Convenience for the CLI smoke-call helper; keeps asyncio out of the typer entry.
def run_ensemble_sync(
    case: CaseInput, model: str, n_votes: int, llm: LLMClient
) -> tuple[FinalVerdict, EnsembleStats]:
    return asyncio.run(run_ensemble(case, model, n_votes, llm))
