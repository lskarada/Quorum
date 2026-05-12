"""Tests for individual specialist agents.

When agents are implemented, these should cover:
  - Each agent's structured_output validates against its expected sub-schema.
  - Each agent reads the latest relevant message from the transcript.
  - Streaming variants yield non-empty token deltas.

Currently agents raise NotImplementedError; see test_stubs.py.
"""
from __future__ import annotations

import pytest


def test_TODO_agent_structured_output_shapes():
    pytest.skip("TODO: implement once agents exist")
