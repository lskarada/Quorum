"""Tests for the deliberation orchestrator (Panel).

When Panel.diagnose() is implemented, these should cover:
  - The five agents are invoked in the expected order each round.
  - Consensus termination short-circuits the loop.
  - Budget exhaustion short-circuits the loop.
  - The final verdict's transcript is well-ordered.

Currently the orchestrator raises NotImplementedError, so the only test here
is a placeholder asserting that fact (see test_stubs.py for the full set).
"""
from __future__ import annotations

import pytest


def test_TODO_panel_diagnose_loop():
    """Placeholder. See test_stubs.py for the NotImplementedError contract."""
    pytest.skip("TODO: implement once Panel.diagnose() exists")
