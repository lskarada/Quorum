"""Phase 3 panel-load tests for the four new tier-matched ablation cells.

Confirms each YAML loads via PanelConfig.from_yaml, the model fields point
at the right vendor strings, and the 5-agent panels populate all five
agent slots while the 1-call panels populate only `hypothesis`.
"""
from __future__ import annotations

import pathlib

import pytest
from quorum.orchestrator.panel_config import PanelConfig

_PANELS_DIR = (
    pathlib.Path(__file__).resolve().parents[1] / "config" / "panels"
)

_HAIKU = "anthropic/claude-haiku-4-5"
_SONNET = "anthropic/claude-sonnet-4-6"


def _load(name: str) -> PanelConfig:
    p = _PANELS_DIR / f"{name}.yaml"
    assert p.exists(), f"missing panel YAML: {p}"
    return PanelConfig.from_yaml(p)


@pytest.mark.parametrize(
    "name,model",
    [("single_haiku", _HAIKU), ("single_sonnet", _SONNET)],
)
def test_single_call_panel(name: str, model: str) -> None:
    cfg = _load(name)
    assert cfg.name == name
    assert cfg.max_iterations == 1
    assert cfg.hypothesis.model == model
    assert cfg.test_chooser is None
    assert cfg.challenger is None
    assert cfg.stewardship is None
    assert cfg.checklist is None


@pytest.mark.parametrize(
    "name,model",
    [("uniform_cheap", _HAIKU), ("uniform_mid", _SONNET)],
)
def test_uniform_5_agent_panel(name: str, model: str) -> None:
    cfg = _load(name)
    assert cfg.name == name
    assert cfg.max_iterations == 3
    for slot_name in ("hypothesis", "test_chooser", "challenger", "stewardship", "checklist"):
        slot = getattr(cfg, slot_name)
        assert slot is not None, f"{name}.{slot_name} missing"
        assert slot.model == model, (
            f"{name}.{slot_name} model={slot.model} expected={model}"
        )


def test_all_four_panels_register_with_list_available(monkeypatch):
    """list_available() must surface the four new panels alongside the existing four."""
    monkeypatch.setenv("QUORUM_PANELS_DIR", str(_PANELS_DIR))
    names = {cfg.name for cfg in PanelConfig.list_available()}
    for required in {"single_haiku", "single_sonnet", "uniform_cheap", "uniform_mid"}:
        assert required in names, f"{required} missing from list_available"
