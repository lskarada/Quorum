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
    TestChooserAgent,
)
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.schemas import CaseInput

# HypothesisAgent's NotImplementedError contract moved to test_agents.py once
# its deliberate() was implemented in the vertical-slice phase.


def _case() -> CaseInput:
    return CaseInput(presentation="placeholder", max_iterations=1)


@pytest.mark.parametrize(
    "AgentCls",
    [TestChooserAgent, ChallengerAgent, StewardshipAgent, ChecklistAgent],
)
def test_agent_deliberate_raises_not_implemented(AgentCls):
    agent = AgentCls(LLMClient())
    with pytest.raises(NotImplementedError):
        asyncio.run(agent.deliberate(_case(), [], 0))


def test_panel_diagnose_raises_not_implemented():
    panel = Panel(LLMClient())
    with pytest.raises(NotImplementedError):
        asyncio.run(panel.diagnose(_case()))


def test_llm_client_complete_raises_not_implemented():
    client = LLMClient()
    with pytest.raises(NotImplementedError):
        asyncio.run(client.complete(messages=[{"role": "user", "content": "x"}]))


def test_mcp_diagnose_case_tool_raises_not_implemented():
    from quorum.mcp_server.tools import diagnose_case_tool

    with pytest.raises(NotImplementedError):
        asyncio.run(diagnose_case_tool({"presentation": "x"}))


def test_eval_corpus_loader_raises_not_implemented():
    from quorum.eval.corpus import load_corpus

    with pytest.raises(NotImplementedError):
        next(load_corpus("nejm"))


def test_api_streaming_helper_raises_not_implemented():
    from quorum.api.streaming import stream_event_to_sse
    from quorum.orchestrator.schemas import StreamEvent

    with pytest.raises(NotImplementedError):
        stream_event_to_sse(StreamEvent(event="agent_start", data={}))


def test_workers_ai_provider_complete_raises_not_implemented():
    from quorum.llm.providers.workers_ai_provider import WorkersAIProvider

    provider = WorkersAIProvider()
    with pytest.raises(NotImplementedError):
        asyncio.run(
            provider.complete(
                messages=[{"role": "user", "content": "x"}],
                model="llama-3.3-70b-instruct",
            )
        )
