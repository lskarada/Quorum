"""Live-LLM smoke for all 5 agents against a small bench of cases.

Runs each agent once against each case using the dev_cheap panel (mid-tier
models routed through OpenRouter). Reports schema-validity rate per agent
and prints qualitative output for human review.

Cost: ~$0.05-$0.15 per full run with dev_cheap models.

Usage:
    cd backend && uv run python scripts/prompt_iteration_eval.py
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys
from typing import Any

# Load .env so OPENROUTER_API_KEY is available.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")

from quorum.llm.client import LLMClient  # noqa: E402
from quorum.orchestrator.agents.challenger import ChallengerAgent  # noqa: E402
from quorum.orchestrator.agents.checklist import ChecklistAgent  # noqa: E402
from quorum.orchestrator.agents.hypothesis import HypothesisAgent  # noqa: E402
from quorum.orchestrator.agents.stewardship import StewardshipAgent  # noqa: E402
from quorum.orchestrator.agents.test_chooser import TestChooserAgent  # noqa: E402
from quorum.orchestrator.panel_config import PanelConfig  # noqa: E402
from quorum.orchestrator.schemas import AgentMessage, CaseInput  # noqa: E402

CASES = [
    CaseInput(
        case_id="bench_01",
        presentation=(
            "62yo M, 2 days of progressive R-sided weakness and aphasia. "
            "BP 168/95. No fever. PMHx HTN, T2DM."
        ),
        budget_usd=500.0,
    ),
    CaseInput(
        case_id="bench_02",
        presentation=(
            "28yo F, 1 week of polyuria + 15-lb weight loss + nocturnal "
            "enuresis. Fingerstick glucose 412."
        ),
        budget_usd=300.0,
    ),
    CaseInput(
        case_id="bench_03",
        presentation=(
            "45yo M day 3 post-PCI for STEMI, now febrile, chest pain worse "
            "leaning forward, pericardial rub."
        ),
        budget_usd=1000.0,
    ),
    CaseInput(
        case_id="bench_04",
        presentation=(
            "71yo F, 3 mo of progressive dyspnea + bilateral lower-leg edema "
            "+ JVD. No CP."
        ),
        budget_usd=2000.0,
    ),
    CaseInput(
        case_id="bench_05",
        presentation=(
            "34yo M IVDU, 5 days of fever + back pain + paresthesias in feet. "
            "T 38.7."
        ),
        budget_usd=1500.0,
    ),
]


def _dev_cheap_config() -> PanelConfig:
    cfgs = PanelConfig.list_available()
    return next(c for c in cfgs if c.name == "dev_cheap")


async def _run_one_case(
    case: CaseInput, cfg: PanelConfig, llm: LLMClient
) -> dict[str, Any]:
    """Run all 5 agents on one case sequentially. Return per-agent result."""
    transcript: list[AgentMessage] = []
    results: dict[str, Any] = {"case_id": case.case_id, "agents": {}}

    agent_specs = [
        ("hypothesis", HypothesisAgent(llm), cfg.hypothesis),
        ("test_chooser", TestChooserAgent(llm), cfg.test_chooser),
        ("challenger", ChallengerAgent(llm), cfg.challenger),
        ("stewardship", StewardshipAgent(llm), cfg.stewardship),
        ("checklist", ChecklistAgent(llm), cfg.checklist),
    ]

    for name, agent, slot in agent_specs:
        if slot is None:
            results["agents"][name] = {"status": "skipped"}
            continue
        try:
            msg = await agent.deliberate(case, list(transcript), 0)
            transcript.append(msg)
            so = msg.structured_output
            so_dump = so.model_dump(mode="json") if hasattr(so, "model_dump") else so
            results["agents"][name] = {
                "status": "ok",
                "tokens": msg.tokens_used,
                "cost_usd": msg.cost_usd,
                "content": msg.content,
                "structured_output": so_dump,
            }
        except Exception as exc:
            results["agents"][name] = {
                "status": "fail",
                "error": f"{type(exc).__name__}: {exc}",
            }
    return results


async def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not set", file=sys.stderr)
        return 2

    cfg = _dev_cheap_config()
    print(f"Using panel config: {cfg.name}")
    print(f"  hypothesis:   {cfg.hypothesis.model}")
    print(f"  test_chooser: {cfg.test_chooser.model if cfg.test_chooser else '—'}")
    print(f"  challenger:   {cfg.challenger.model if cfg.challenger else '—'}")
    print(f"  stewardship:  {cfg.stewardship.model if cfg.stewardship else '—'}")
    print(f"  checklist:    {cfg.checklist.model if cfg.checklist else '—'}")

    llm = LLMClient(default_model=cfg.hypothesis.model)

    out_dir = pathlib.Path(__file__).resolve().parents[2] / "data" / "prompt_iteration"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    total_cost = 0.0
    for case in CASES:
        print(f"\n=== {case.case_id} ===")
        result = await _run_one_case(case, cfg, llm)
        all_results.append(result)
        for name, agent_result in result["agents"].items():
            status = agent_result["status"]
            if status == "ok":
                cost = agent_result["cost_usd"]
                total_cost += cost
                print(
                    f"  {name:12s} ok   tokens={agent_result['tokens']:5d}  "
                    f"cost=${cost:.5f}  → {agent_result['content'][:80]}"
                )
            elif status == "skipped":
                print(f"  {name:12s} skip")
            else:
                print(f"  {name:12s} FAIL {agent_result['error']}")

    (out_dir / "smoke_results.json").write_text(json.dumps(all_results, indent=2))

    # Per-agent schema-validity summary
    print("\n=== schema-validity summary ===")
    _agent_names = ["hypothesis", "test_chooser", "challenger", "stewardship", "checklist"]
    per_agent_pass = {n: 0 for n in _agent_names}
    per_agent_total = {n: 0 for n in _agent_names}
    for r in all_results:
        for name, agent_result in r["agents"].items():
            per_agent_total[name] += 1
            if agent_result["status"] == "ok":
                per_agent_pass[name] += 1
    for name in per_agent_pass:
        print(f"  {name:12s} {per_agent_pass[name]}/{per_agent_total[name]} schema-valid")

    print(f"\nTotal LLM cost this run: ${total_cost:.4f}")
    print(f"Results written: {out_dir / 'smoke_results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
