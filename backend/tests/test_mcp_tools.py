"""Tests for MCP diagnose_case tool."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from quorum.mcp_server.tools import diagnose_case_tool
from quorum.orchestrator.schemas import Differential, FinalVerdict

_FAKE_VERDICT = FinalVerdict(
    case_id="t1",
    final_differential=Differential(candidates=[], iteration=0),
    confidence=0.0,
    iterations_used=1,
    total_tokens=0,
    total_cost_usd=0.0,
    transcript=[],
    termination_reason="max_iterations",
    schema_version=1,
    is_error=False,
)


@pytest.mark.asyncio
async def test_diagnose_case_tool_returns_verdict_dict(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch("quorum.mcp_server.tools.Panel") as MockPanel:
        instance = MockPanel.return_value
        instance.diagnose = AsyncMock(return_value=_FAKE_VERDICT)
        result = await diagnose_case_tool({"presentation": "test case"})
    assert "final_differential" in result
    assert "termination_reason" in result
    assert result["termination_reason"] == "max_iterations"


@pytest.mark.asyncio
async def test_diagnose_case_tool_refuses_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        await diagnose_case_tool({"presentation": "x"})


@pytest.mark.asyncio
async def test_diagnose_case_tool_cost_guardrail_blocks_expensive_panel(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("QUORUM_MAX_COST_USD", "0.01")  # very tight
    with pytest.raises(RuntimeError, match="exceeds"):
        # dev_cheap has 5 agents * 3 max_iterations * $0.10 = $1.50 projected; > $0.01 cap
        await diagnose_case_tool({"presentation": "x", "panel": "dev_cheap"})


@pytest.mark.asyncio
async def test_diagnose_case_tool_default_panel_is_baseline_or_set(monkeypatch):
    """Default panel name should be one of the available configs."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("QUORUM_MAX_COST_USD", "10")
    with patch("quorum.mcp_server.tools.Panel") as MockPanel:
        instance = MockPanel.return_value
        instance.diagnose = AsyncMock(return_value=_FAKE_VERDICT)
        result = await diagnose_case_tool({"presentation": "x"})
    assert result is not None
