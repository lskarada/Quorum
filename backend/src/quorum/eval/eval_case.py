"""Unified EvalCase for the v2 benchmark.

Wraps the three sample formats (NEJM, MCR, RareBench) into a single
Pydantic shape the orchestrator and Gatekeeper can consume identically.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

CORPUS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "data"
    / "cases"
    / "eval_corpus_v2"
)


class Finding(BaseModel):
    category: str
    label: str
    content: str


class EvalCase(BaseModel):
    case_id: str
    corpus: Literal["nejm", "mcr", "rarebench"]
    source: str
    initial_presentation: str
    available_findings: list[Finding] = Field(default_factory=list)
    ground_truth_diagnosis: str
    acceptable_partial_credit: list[str] = Field(default_factory=list)
    difficulty: str | None = "hard"
    specialty_tags: list[str] = Field(default_factory=list)


def _load_nejm(raw: dict) -> EvalCase:
    findings = [Finding(**f) for f in raw.get("available_findings", [])]
    return EvalCase(
        case_id=raw["case_id"],
        corpus="nejm",
        source=raw.get("source", "NEJM CPC"),
        initial_presentation=raw["initial_presentation"],
        available_findings=findings,
        ground_truth_diagnosis=raw["ground_truth_diagnosis"],
        acceptable_partial_credit=raw.get("acceptable_partial_credit", []),
        difficulty=raw.get("difficulty", "hard"),
        specialty_tags=raw.get("specialty_tags", []),
    )


def _load_mcr(raw: dict) -> EvalCase:
    return EvalCase(
        case_id=raw["case_id"],
        corpus="mcr",
        source=raw.get("source", "MedCaseReasoning"),
        initial_presentation=raw["presentation"],
        available_findings=[],
        ground_truth_diagnosis=raw["ground_truth_diagnosis"],
        acceptable_partial_credit=[],
        specialty_tags=[],
    )


def _load_rarebench(raw: dict) -> EvalCase:
    return EvalCase(
        case_id=raw["case_id"],
        corpus="rarebench",
        source=raw.get("source", "RareBench LIRICAL"),
        initial_presentation=raw["presentation"],
        available_findings=[],
        ground_truth_diagnosis=raw["ground_truth_diagnosis"],
        acceptable_partial_credit=raw.get("all_ground_truth_names", []),
        specialty_tags=["rare_disease"],
    )


def load_corpus(split: Literal["tune", "eval"] | None = None) -> list[EvalCase]:
    """Load all 35 v2 cases (or a TUNE/EVAL partition) as EvalCase models."""
    nejm = [_load_nejm(c) for c in json.loads((CORPUS_DIR / "nejm_sample.json").read_text())]
    mcr = [_load_mcr(c) for c in json.loads((CORPUS_DIR / "mcr_sample.json").read_text())]
    rb_path = CORPUS_DIR / "rarebench_sample.json"
    rb = [_load_rarebench(c) for c in json.loads(rb_path.read_text())]
    all_cases = nejm + mcr + rb

    if split is None:
        return all_cases

    splits = json.loads((CORPUS_DIR / "splits.json").read_text())
    ids = set(splits[split])
    return [c for c in all_cases if c.case_id in ids]
