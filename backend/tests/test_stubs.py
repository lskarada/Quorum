"""Contract tests for stubs.

Every `# TODO:` body in the scaffolding pass MUST raise NotImplementedError.
A green test here for a stub that was silently filled in is the canary.

When a real implementation lands, MOVE that test to the appropriate
test_<module>.py file. Don't just delete it.
"""
from __future__ import annotations

import asyncio

import pytest

# HypothesisAgent's NotImplementedError contract moved to test_agents.py once
# its deliberate() was implemented in the vertical-slice phase.
# TestChooserAgent's NotImplementedError contract moved to test_agents.py once
# its deliberate() was implemented in Phase 3.
# All four optional-agent stubs implemented; see test_agents.py for per-agent contracts.


# Panel.diagnose NotImplementedError contract moved to test_panel.py once
# the single-agent vertical slice was implemented.

# LLMClient.complete NotImplementedError contract moved to test_llm_client.py
# once the OpenRouter-routed implementation landed.


def test_mcp_diagnose_case_tool_raises_not_implemented():
    from quorum.mcp_server.tools import diagnose_case_tool

    with pytest.raises(NotImplementedError):
        asyncio.run(diagnose_case_tool({"presentation": "x"}))


# eval.corpus.load_corpus was deleted in Phase 8: replaced by load_medqa /
# load_cupcase / load_ground_truth. Contract tests moved to test_eval_corpus.py.


# stream_event_to_sse NotImplementedError contract moved to test_api_diagnose.py
# coverage (the helper is exercised by every streaming acceptance test).

# WorkersAI provider stub removed in Phase 1: all four single-provider stubs
# were collapsed into a single OpenRouter-routed LLMClient (see test_llm_client.py).
