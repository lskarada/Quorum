"""Tests for backend/src/quorum/orchestrator/panel_config.py"""
import pathlib
import tempfile

import pytest
from pydantic import ValidationError
from quorum.orchestrator.panel_config import PanelConfig

_VALID_YAML = """\
name: test_panel
description: For unit tests
max_iterations: 3
consensus_threshold: 0.6
hypothesis:   { model: "anthropic/claude-opus-4" }
test_chooser: { model: "openai/gpt-4o" }
challenger:   { model: "google/gemini-2.5-pro" }
stewardship:  { model: "anthropic/claude-haiku-4-5" }
checklist:    { model: "meta-llama/llama-3.3-70b-instruct" }
"""


def _write_tmp_yaml(text: str) -> pathlib.Path:
    p = pathlib.Path(tempfile.mkdtemp()) / "panel.yaml"
    p.write_text(text)
    return p


def test_loads_valid_config():
    cfg = PanelConfig.from_yaml(_write_tmp_yaml(_VALID_YAML))
    assert cfg.name == "test_panel"
    assert cfg.max_iterations == 3
    assert cfg.consensus_threshold == 0.6
    assert cfg.hypothesis.model == "anthropic/claude-opus-4"
    assert cfg.checklist.model == "meta-llama/llama-3.3-70b-instruct"


def test_missing_required_agent_raises():
    # DEVIATION from plan: original test commented out `checklist`, but the
    # implementation (per Task 2.2 comment + Task 2.3 baseline_single_call)
    # makes only `hypothesis` required. Test the actually-required slot instead.
    bad = _VALID_YAML.replace('hypothesis:   { model: "anthropic/claude-opus-4" }', "")
    with pytest.raises(ValidationError, match="hypothesis"):
        PanelConfig.from_yaml(_write_tmp_yaml(bad))


def test_invalid_threshold_raises():
    bad = _VALID_YAML.replace("consensus_threshold: 0.6", "consensus_threshold: 1.5")
    with pytest.raises(ValidationError):
        PanelConfig.from_yaml(_write_tmp_yaml(bad))


def test_reference_configs_load():
    cfgs = PanelConfig.list_available()
    names = {c.name for c in cfgs}
    assert "single_model_premium" in names
    assert "mixed_vendor" in names
    assert "baseline_single_call" in names
    assert "dev_cheap" in names


def test_baseline_has_only_hypothesis():
    baseline = next(c for c in PanelConfig.list_available() if c.name == "baseline_single_call")
    assert baseline.hypothesis is not None
    assert baseline.test_chooser is None
    assert baseline.challenger is None
    assert baseline.stewardship is None
    assert baseline.checklist is None
