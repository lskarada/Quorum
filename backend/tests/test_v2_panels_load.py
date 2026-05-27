"""v2 panel YAML smoke tests (Phase 5 Task 5.4)."""
from __future__ import annotations

from quorum.orchestrator.panel_config import PanelConfig


def _panel(name: str) -> PanelConfig:
    return next(c for c in PanelConfig.list_available() if c.name == name)


def test_v2_quorum_calibrated_loads_with_all_five_agents():
    c = _panel("v2_quorum_calibrated")
    assert c.hypothesis is not None
    assert c.test_chooser is not None
    assert c.challenger is not None
    assert c.stewardship is not None
    assert c.checklist is not None
    # All five share Sonnet 4.6 in the calibrated baseline (system-level lift only)
    assert c.hypothesis.model == "anthropic/claude-sonnet-4-6"
    assert c.test_chooser.model == "anthropic/claude-sonnet-4-6"
    assert c.challenger.model == "anthropic/claude-sonnet-4-6"
    assert c.stewardship.model == "anthropic/claude-sonnet-4-6"
    assert c.checklist.model == "anthropic/claude-sonnet-4-6"
    # Sequential-mode knobs
    assert c.max_iterations == 30
    assert c.consensus_threshold == 0.70


def test_v2_single_sonnet_is_hypothesis_only_baseline():
    c = _panel("v2_single_sonnet")
    assert c.hypothesis is not None
    assert c.test_chooser is None
    assert c.challenger is None
    assert c.stewardship is None
    assert c.checklist is None
    assert c.hypothesis.model == "anthropic/claude-sonnet-4-6"
    assert c.max_iterations == 1
