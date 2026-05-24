"""Contract tests for stubs.

Every `# TODO:` body in the scaffolding pass MUST raise NotImplementedError.
A green test here for a stub that was silently filled in is the canary.

When a real implementation lands, MOVE that test to the appropriate
test_<module>.py file. Don't just delete it.
"""
from __future__ import annotations

import asyncio

import pytest

from quorum.llm.client import LLMClient
from quorum.orchestrator.agents import (
    ChallengerAgent,
    ChecklistAgent,
    StewardshipAgent,
)
from quorum.orchestrator.schemas import CaseInput

# HypothesisAgent's NotImplementedError contract moved to test_agents.py once
# its deliberate() was implemented in the vertical-slice phase.
# TestChooserAgent's NotImplementedError contract moved to test_agents.py once
# its deliberate() was implemented in Phase 3.


def _case() -> CaseInput:
    return CaseInput(presentation="placeholder", max_iterations=1)


@pytest.mark.parametrize(
    "AgentCls",
    [ChallengerAgent, ChecklistAgent, StewardshipAgent],
)
def test_agent_deliberate_raises_not_implemented(AgentCls):
    # Bypass __init__ so we don't need OPENROUTER_API_KEY for a stub-only test
    # (matches the LLMClient.__new__ pattern used in test_agents/test_panel).
    llm = LLMClient.__new__(LLMClient)
    llm.default_model = "anthropic/claude-opus-4"
    agent = AgentCls(llm)
    with pytest.raises(NotImplementedError):
        asyncio.run(agent.deliberate(_case(), [], 0))


# Panel.diagnose NotImplementedError contract moved to test_panel.py once
# the single-agent vertical slice was implemented.

# LLMClient.complete NotImplementedError contract moved to test_llm_client.py
# once the OpenRouter-routed implementation landed.


def test_mcp_diagnose_case_tool_raises_not_implemented():
    from quorum.mcp_server.tools import diagnose_case_tool

    with pytest.raises(NotImplementedError):
        asyncio.run(diagnose_case_tool({"presentation": "x"}))


def test_eval_corpus_loader_raises_not_implemented():
    from quorum.eval.corpus import load_corpus

    with pytest.raises(NotImplementedError):
        next(load_corpus("nejm"))


# stream_event_to_sse NotImplementedError contract moved to test_api_diagnose.py
# coverage (the helper is exercised by every streaming acceptance test).

# WorkersAI provider stub removed in Phase 1: all four single-provider stubs
# were collapsed into a single OpenRouter-routed LLMClient (see test_llm_client.py).
