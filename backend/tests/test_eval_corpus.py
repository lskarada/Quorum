"""Tests for quorum.eval.corpus loaders."""
from __future__ import annotations

import pathlib

from quorum.eval.corpus import load_cupcase, load_ground_truth, load_mcr, load_medqa
from quorum.orchestrator.schemas import CaseInput

_FIXTURES = pathlib.Path(__file__).parent / "fixtures"
_MEDQA = _FIXTURES / "medqa_sample.json"
_CUPCASE = _FIXTURES / "cupcase_sample.json"
_MCR = _FIXTURES / "mcr_sample.json"


def test_load_medqa_yields_caseinputs():
    cases = list(load_medqa(_MEDQA))
    assert len(cases) >= 5
    for c in cases:
        assert isinstance(c, CaseInput)
        assert c.presentation.strip()
        assert "Options:" in c.presentation
        assert c.case_id


def test_load_cupcase_yields_caseinputs():
    cases = list(load_cupcase(_CUPCASE))
    assert len(cases) >= 5
    for c in cases:
        assert isinstance(c, CaseInput)
        assert c.presentation.strip()
        assert c.case_id


def test_load_ground_truth_returns_dict_medqa():
    gt = load_ground_truth(_MEDQA)
    assert isinstance(gt, dict)
    assert len(gt) >= 5
    for k, v in gt.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
        assert v.strip()


def test_load_ground_truth_returns_dict_cupcase():
    gt = load_ground_truth(_CUPCASE)
    assert isinstance(gt, dict)
    assert len(gt) >= 5
    for k, v in gt.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
        assert v.strip()


def test_load_ground_truth_medqa_returns_option_text():
    # Spot-check: case 001 (spontaneous pneumothorax) — answer_idx "C"
    gt = load_ground_truth(_MEDQA)
    assert "Spontaneous pneumothorax" in gt["medqa_synth_001"]


def test_load_ground_truth_cupcase_returns_final_diagnosis():
    gt = load_ground_truth(_CUPCASE)
    assert gt["cup_synth_001"] == "Non-small cell lung cancer"


def test_load_mcr_yields_caseinputs():
    cases = list(load_mcr(_MCR))
    assert len(cases) >= 5
    for c in cases:
        assert isinstance(c, CaseInput)
        assert c.presentation.strip()
        assert c.case_id


def test_load_ground_truth_mcr_returns_final_diagnosis():
    gt = load_ground_truth(_MCR)
    assert gt["mcr_synth_001"] == "Dermatomyositis"
