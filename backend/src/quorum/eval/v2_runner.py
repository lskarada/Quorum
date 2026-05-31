"""Runner for the v2 (Calibrated-Auditable MAI-DxO) benchmark.

Drives Panel.run_sequential (Arm A) or Panel.diagnose (Arm B) against
the v2 EvalCase corpus, persists per-case AuditTrail JSONL, and emits
a run-level manifest.

Cost guardrail: enforces QUORUM_MAX_COST_USD before any API call.
Honors a precomputed `_ESTIMATED_COST_PER_CASE` per arm; pass
`confirm_cost=True` to bypass.

Idempotent on re-run: cases whose audit.jsonl already exists are skipped.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Literal

from quorum.audit.writer import AuditWriter
from quorum.eval.eval_case import EvalCase, load_corpus, load_dev_corpus
from quorum.gatekeeper.gatekeeper import Gatekeeper
from quorum.llm.client import LLMClient
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import CaseInput

Arm = Literal["arm_a", "arm_b"]
Split = Literal["tune", "eval", "dev"]

# Per-case projection used only by the env-gated cap.
_ARM_A_COST_PER_CASE = 0.50  # Sonnet 4.6 sequential, 5 agents, many turns
_ARM_B_COST_PER_CASE = 0.15  # Single Sonnet 4.6 call


def _projected_cap_or_raise(n: int, arm: Arm, confirm_cost: bool) -> None:
    cap = float(os.environ.get("QUORUM_MAX_COST_USD", "20"))
    per = _ARM_A_COST_PER_CASE if arm == "arm_a" else _ARM_B_COST_PER_CASE
    projected = n * per
    if projected > cap and not confirm_cost:
        raise RuntimeError(
            f"Projected cost ${projected:.2f} for arm={arm} n={n} exceeds "
            f"QUORUM_MAX_COST_USD=${cap:.2f}. Pass confirm_cost=True to override."
        )


async def run_arm_a(
    cases: list[EvalCase],
    panel_config: PanelConfig,
    results_dir: Path,
    *,
    llm: LLMClient | None = None,
    run_id: str | None = None,
    max_turns: int = 30,
    commit_threshold: float = 0.70,
    confirm_cost: bool = False,
) -> Path:
    """Run Quorum-Calibrated sequential mode on `cases`."""
    _projected_cap_or_raise(len(cases), "arm_a", confirm_cost)
    results_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_id or f"v2-arm-a-{int(time.time())}"
    out_dir = results_dir / run_id

    llm = llm or LLMClient()
    panel = Panel(llm, panel_config)

    manifest = _start_manifest(out_dir, panel_config, "arm_a", len(cases))

    for case in cases:
        out_path = out_dir / f"{case.case_id}.audit.jsonl"
        if out_path.exists():
            continue
        writer = AuditWriter(
            root=results_dir,
            run_id=run_id,
            case_id=case.case_id,
            model=panel_config.hypothesis.model,
            panel_config_name=panel_config.name,
        )
        try:
            if not case.available_findings:
                # MCR / RareBench cases have no structured findings. The spec
                # routes these single-turn: skip Gatekeeper and the multi-agent
                # debate loop, just take Hypothesis's first differential as
                # the commit.
                await _run_single_hypothesis(panel, case, writer)
            else:
                gk = Gatekeeper(case, llm_client=llm)
                await panel.run_sequential(
                    case, gk, writer,
                    max_turns=max_turns,
                    commit_threshold=commit_threshold,
                )
        except Exception as exc:
            import traceback
            writer.record_turn(
                agent="runner",
                message_role="safety_check",
                content=f"ERROR: {exc.__class__.__name__}: {exc}",
                extra={"traceback": traceback.format_exc()[-1500:]},
            )
            writer.audit.final_committed_diagnosis = f"(error: {exc.__class__.__name__})"
        writer.close()

    manifest["finished_at"] = time.time()
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return out_dir


async def run_arm_b(
    cases: list[EvalCase],
    panel_config: PanelConfig,
    results_dir: Path,
    *,
    llm: LLMClient | None = None,
    run_id: str | None = None,
    confirm_cost: bool = False,
) -> Path:
    """Run the single-Sonnet baseline (Panel.diagnose, single call) on `cases`."""
    _projected_cap_or_raise(len(cases), "arm_b", confirm_cost)
    results_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_id or f"v2-arm-b-{int(time.time())}"
    out_dir = results_dir / run_id

    llm = llm or LLMClient()
    panel = Panel(llm, panel_config)

    manifest = _start_manifest(out_dir, panel_config, "arm_b", len(cases))

    for case in cases:
        out_path = out_dir / f"{case.case_id}.audit.jsonl"
        if out_path.exists():
            continue
        writer = AuditWriter(
            root=results_dir,
            run_id=run_id,
            case_id=case.case_id,
            model=panel_config.hypothesis.model,
            panel_config_name=panel_config.name,
        )
        case_input = CaseInput(
            case_id=case.case_id,
            presentation=case.initial_presentation,
            max_iterations=panel_config.max_iterations,
        )
        try:
            verdict = await panel.diagnose(case_input)
            top = (
                verdict.final_differential.top_diagnosis()
                if verdict.final_differential.candidates
                else None
            )
            top_name, _top_p = (top[0], top[1]) if top else ("(no diagnosis)", 0.0)
            posterior = verdict.final_differential.as_posterior_dict()
            writer.record_turn(
                agent="hypothesis",
                message_role="out",
                content=verdict.final_differential.model_dump_json(),
                tokens=verdict.total_tokens,
                cost_usd=verdict.total_cost_usd,
                posterior_at_turn=posterior,
            )
            writer.set_final(
                committed_diagnosis=top_name,
                final_posterior=posterior,
                real_cost_usd=verdict.total_cost_usd,
                simulated_cost_usd=0.0,
            )
        except Exception as exc:
            writer.audit.final_committed_diagnosis = f"(error: {exc.__class__.__name__})"
        writer.close()

    manifest["finished_at"] = time.time()
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return out_dir


async def _run_single_hypothesis(panel, case, writer) -> None:
    """Single Hypothesis call path for cases without structured findings.

    Used inside Arm A when an EvalCase has no available_findings (MCR /
    RareBench). The case still goes through Hypothesis once; the resulting
    Differential is recorded as the committed posterior.
    """
    case_input = CaseInput(
        case_id=case.case_id,
        presentation=case.initial_presentation,
        max_iterations=1,
    )
    hyp_msg = await panel.hypothesis.deliberate(case_input, [], 0)
    posterior = (
        hyp_msg.structured_output.as_posterior_dict()
        if hyp_msg.structured_output is not None
        and hasattr(hyp_msg.structured_output, "as_posterior_dict")
        else {}
    )
    writer.record_turn(
        agent="hypothesis",
        message_role="out",
        content=hyp_msg.content,
        tokens=hyp_msg.tokens_used,
        cost_usd=hyp_msg.cost_usd,
        posterior_at_turn=posterior,
    )
    top = max(posterior, key=posterior.get) if posterior else "(no diagnosis)"
    writer.record_turn(
        agent="runner",
        message_role="safety_check",
        content=f"single-turn (no available_findings) commit on {top!r}",
        extra={"forced": True, "single_turn": True},
    )
    writer.set_final(
        committed_diagnosis=top,
        final_posterior=posterior,
        real_cost_usd=hyp_msg.cost_usd,
        simulated_cost_usd=0.0,
    )


def _start_manifest(out_dir: Path, panel_config: PanelConfig, arm: Arm, n: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    manifest = {
        "schema_version": "v2.run.v1",
        "arm": arm,
        "panel": panel_config.name,
        "n_cases": n,
        "started_at": time.time(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest


def load_v2_cases(
    split: Split | None = None,
    case_id: str | None = None,
    split_file: str | None = None,
    split_key: str | None = None,
) -> list[EvalCase]:
    """Return EvalCases filtered by split or single case_id.

    split="dev" loads the held-out 26-case DEV tuning set from its own files
    (never splits.json). DEV ids are disjoint from TUNE/EVAL by construction.

    split_file + split_key: load from a named split JSON under CORPUS_DIR,
    e.g. split_file="splits_v3_nejm.json", split_key="holdout".
    The pool searched is load_corpus() + load_dev_corpus().
    """
    if case_id:
        pool = load_corpus() + load_dev_corpus()
        return [c for c in pool if c.case_id == case_id]
    if split_file is not None:
        import json
        from quorum.eval.eval_case import CORPUS_DIR
        ids = set(json.loads((CORPUS_DIR / split_file).read_text())[split_key])
        pool = load_corpus() + load_dev_corpus()
        return [c for c in pool if c.case_id in ids]
    if split == "dev":
        return load_dev_corpus()
    return load_corpus(split=split)


async def run(
    arm: Arm,
    *,
    panel_name: str,
    split: Split | None = None,
    case_id: str | None = None,
    n: int | None = None,
    results_dir: Path | None = None,
    run_id: str | None = None,
    max_turns: int = 30,
    commit_threshold: float = 0.70,
    confirm_cost: bool = False,
) -> Path:
    """High-level entry used by scripts."""
    panel_config = next(
        c for c in PanelConfig.list_available() if c.name == panel_name
    )
    cases = load_v2_cases(split=split, case_id=case_id)
    if n is not None:
        cases = cases[:n]
    if not cases:
        raise ValueError(f"No cases matched split={split!r} case_id={case_id!r}")

    repo_root = Path(__file__).resolve().parents[4]
    results_dir = results_dir or (repo_root / "data" / "results")

    if arm == "arm_a":
        return await run_arm_a(
            cases, panel_config, results_dir,
            run_id=run_id, max_turns=max_turns,
            commit_threshold=commit_threshold,
            confirm_cost=confirm_cost,
        )
    return await run_arm_b(
        cases, panel_config, results_dir,
        run_id=run_id, confirm_cost=confirm_cost,
    )


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(description="v2 benchmark runner")
    ap.add_argument("--arm", choices=("arm_a", "arm_b"), required=True)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--split", choices=("tune", "eval"), default=None)
    ap.add_argument("--case-id", default=None)
    ap.add_argument("-n", type=int, default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--commit-threshold", type=float, default=0.70)
    ap.add_argument("--confirm-cost", action="store_true")
    ap.add_argument("--split-file", default=None)
    ap.add_argument("--split-key", default=None)
    args = ap.parse_args()

    if args.split_file is not None:
        cases = load_v2_cases(split_file=args.split_file, split_key=args.split_key)
        if args.n is not None:
            cases = cases[: args.n]
        if not cases:
            raise ValueError(f"No cases matched --split-file={args.split_file!r} --split-key={args.split_key!r}")
        panel_config = next(
            c for c in __import__("quorum.orchestrator.panel_config", fromlist=["PanelConfig"]).PanelConfig.list_available()
            if c.name == args.panel
        )
        out = asyncio.run(
            (run_arm_a if args.arm == "arm_a" else run_arm_b)(
                cases, panel_config, None,
                run_id=args.run_id,
                **({
                    "max_turns": args.max_turns,
                    "commit_threshold": args.commit_threshold,
                    "confirm_cost": args.confirm_cost,
                } if args.arm == "arm_a" else {"confirm_cost": args.confirm_cost}),
            )
        )
    else:
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
            )
        )
    print(f"Wrote results to {out}")
