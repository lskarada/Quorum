"""Tests for cost-prior calibration (Phase 2).

PanelConfig grows an optional ``cost_prior_usd: float | None`` field that
reflects the calibrated mean cost per case for a panel. The eval-run CLI
uses it as a pre-flight projection: if ``n * cost_prior_usd > max_cost``
the run emits a warning and refuses to start unless ``--confirm-cost``
is passed.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest
from quorum.orchestrator.panel_config import PanelConfig
from typer.testing import CliRunner

from quorum.eval.cli import app

_YAML_WITH_PRIOR = """\
name: cp_test_with
description: cost-prior present
max_iterations: 3
consensus_threshold: 0.6
cost_prior_usd: 0.042
hypothesis: { model: "anthropic/claude-haiku-4-5" }
"""

_YAML_WITHOUT_PRIOR = """\
name: cp_test_without
description: cost-prior absent
max_iterations: 3
consensus_threshold: 0.6
hypothesis: { model: "anthropic/claude-haiku-4-5" }
"""


def _write(text: str) -> pathlib.Path:
    p = pathlib.Path(tempfile.mkdtemp()) / "panel.yaml"
    p.write_text(text)
    return p


def test_panel_config_loads_cost_prior_when_present():
    cfg = PanelConfig.from_yaml(_write(_YAML_WITH_PRIOR))
    assert cfg.cost_prior_usd == pytest.approx(0.042)


def test_panel_config_cost_prior_optional_defaults_none():
    cfg = PanelConfig.from_yaml(_write(_YAML_WITHOUT_PRIOR))
    assert cfg.cost_prior_usd is None


def test_eval_run_warns_when_budget_exceeded_by_prior(monkeypatch, tmp_path):
    """If n * cost_prior_usd exceeds QUORUM_MAX_COST_USD, ``quorum-eval run``
    must abort with a non-zero exit and an explanatory message that includes
    the projected cost and the cap. Passing ``--confirm-cost`` overrides."""
    # Build a single-panel configs dir so PanelConfig.list_available finds it.
    panels_dir = tmp_path / "config" / "panels"
    panels_dir.mkdir(parents=True)
    (panels_dir / "cp_test_with.yaml").write_text(_YAML_WITH_PRIOR)
    # Cases dir with one case (we never reach the panel — the abort happens
    # at pre-flight before any LLM call).
    cases_dir = tmp_path / "data" / "cases" / "medqa"
    cases_dir.mkdir(parents=True)
    (cases_dir / "all.json").write_text(
        '[{"id": "medqa_0001", "question": "Q?", "options": '
        '{"A":"a","B":"b","C":"c","D":"d"}, "answer_idx": "A", "answer": "a"}]'
    )

    # Force the CLI to discover our temp panel + a low cap.
    monkeypatch.setenv("QUORUM_PANELS_DIR", str(panels_dir))
    monkeypatch.setenv("QUORUM_MAX_COST_USD", "0.10")
    # n=100, cost_prior=0.042 → projected $4.20 > $0.10 cap → must warn+abort.

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--corpus", "medqa",
            "--panel", "cp_test_with",
            "--n", "100",
            "--cases-root", str(tmp_path / "data" / "cases"),
            "--results-root", str(tmp_path / "data" / "results"),
        ],
    )
    assert result.exit_code != 0, f"expected non-zero on cap exceeded, got stdout={result.stdout}"
    combined = (result.stdout or "") + (str(result.exception) if result.exception else "")
    assert "4.20" in combined or "projected" in combined.lower() or "cost_prior" in combined.lower(), (
        f"expected cost-prior warning, got: {combined}"
    )
