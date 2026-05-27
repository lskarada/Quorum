"""MCP tool implementations exposed by the Quorum stdio server."""
from __future__ import annotations

import os

from quorum.llm.client import LLMClient
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import CaseInput

DIAGNOSE_CASE_TOOL_NAME = "diagnose_case"

DIAGNOSE_CASE_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "presentation": {"type": "string", "description": "Clinical case vignette"},
        "case_id": {"type": "string"},
        "available_tests": {"type": "array", "items": {"type": "string"}},
        "budget_usd": {"type": "number"},
        "max_iterations": {"type": "integer", "default": 3},
        "panel": {"type": "string", "default": "dev_cheap"},
    },
    "required": ["presentation"],
}

_MAX_COST_PER_CALL_USD_ENV = "QUORUM_MAX_COST_USD"
_DEFAULT_MAX_COST_USD = 5.0
_EST_COST_PER_AGENT_CALL = 0.10  # conservative


def _max_cost_per_call() -> float:
    return float(os.environ.get(_MAX_COST_PER_CALL_USD_ENV, _DEFAULT_MAX_COST_USD))


async def diagnose_case_tool(arguments: dict) -> dict:
    """MCP tool handler for `diagnose_case`. Returns FinalVerdict as dict."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError(
            "diagnose_case requires OPENROUTER_API_KEY. Set it in the environment "
            "before launching the MCP server."
        )

    panel_name = arguments.get("panel", "dev_cheap")
    matches = [c for c in PanelConfig.list_available() if c.name == panel_name]
    if not matches:
        raise RuntimeError(f"Unknown panel: {panel_name}")
    cfg = matches[0]

    # Cost projection guardrail.
    est_agents = sum(
        1
        for slot in (
            cfg.hypothesis,
            cfg.test_chooser,
            cfg.challenger,
            cfg.stewardship,
            cfg.checklist,
        )
        if slot
    )
    est_cost = est_agents * cfg.max_iterations * _EST_COST_PER_AGENT_CALL
    cap = _max_cost_per_call()
    if est_cost > cap:
        raise RuntimeError(
            f"Projected cost ${est_cost:.2f} exceeds {_MAX_COST_PER_CALL_USD_ENV}=${cap:.2f}. "
            f"Lower max_iterations or use a cheaper panel."
        )

    panel_obj = Panel(LLMClient(), cfg)
    case = CaseInput(**{k: v for k, v in arguments.items() if k != "panel"})
    verdict = await panel_obj.diagnose(case)
    return verdict.model_dump(mode="json")
