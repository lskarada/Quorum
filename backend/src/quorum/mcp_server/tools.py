"""MCP tool definitions exposed by the Quorum server.

Currently one tool: `diagnose_case`. Input matches CaseInput; output matches
FinalVerdict. Both are JSON-serializable via the orchestrator schemas.
"""
from __future__ import annotations


DIAGNOSE_CASE_TOOL_NAME = "diagnose_case"

DIAGNOSE_CASE_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "presentation": {"type": "string", "description": "Clinical case vignette"},
        "case_id": {"type": "string"},
        "available_tests": {"type": "array", "items": {"type": "string"}},
        "budget_usd": {"type": "number"},
        "max_iterations": {"type": "integer", "default": 5},
    },
    "required": ["presentation"],
}


async def diagnose_case_tool(arguments: dict) -> dict:
    """MCP tool handler for `diagnose_case`.

    Args:
        arguments: dict matching DIAGNOSE_CASE_INPUT_SCHEMA.

    Returns:
        FinalVerdict as a dict (JSON-serializable).
    """
    # TODO: instantiate Panel, validate arguments into CaseInput, run diagnose,
    # return verdict.model_dump().
    raise NotImplementedError
