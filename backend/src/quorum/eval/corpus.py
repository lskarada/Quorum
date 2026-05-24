"""Case corpus loaders.

Loads JSON corpora into iterators of CaseInput and provides a ground-truth
lookup table per corpus. Two corpus shapes are supported:

  medqa:   list of {id, question, options: {<letter>: text}, answer_idx}
           presentation := question + "\n\nOptions:\n" + formatted options
           ground truth := options[answer_idx]

  cupcase: list of {case_id, presentation, final_diagnosis}
           presentation := presentation
           ground truth := final_diagnosis
"""
from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator

from quorum.orchestrator.schemas import CaseInput


def _format_options(options: dict[str, str]) -> str:
    return "\n".join(f"{k}. {v}" for k, v in options.items())


def load_medqa(path: pathlib.Path) -> Iterator[CaseInput]:
    """Yield CaseInputs from a MedQA-style JSON file.

    Each entry contributes a single CaseInput whose `presentation` is the
    stem concatenated with the formatted options block.
    """
    data = json.loads(pathlib.Path(path).read_text())
    for i, entry in enumerate(data):
        case_id = entry.get("id") or entry.get("case_id") or f"medqa_{i:04d}"
        question = entry["question"]
        options = entry.get("options", {})
        presentation = f"{question}\n\nOptions:\n{_format_options(options)}"
        yield CaseInput(case_id=case_id, presentation=presentation)


def load_cupcase(path: pathlib.Path) -> Iterator[CaseInput]:
    """Yield CaseInputs from a case-report-style JSON file."""
    data = json.loads(pathlib.Path(path).read_text())
    for i, entry in enumerate(data):
        case_id = entry.get("case_id") or entry.get("id") or f"cup_{i:04d}"
        yield CaseInput(case_id=case_id, presentation=entry["presentation"])


def load_mcr(path: pathlib.Path) -> Iterator[CaseInput]:
    """Yield CaseInputs from a MedCaseReasoning-style JSON file.

    Same shape as cupcase: {case_id, presentation, final_diagnosis}.
    MCR additionally carries a `reasoning` field that we don't pass to the
    panel (ground truth only).
    """
    data = json.loads(pathlib.Path(path).read_text())
    for i, entry in enumerate(data):
        case_id = entry.get("case_id") or entry.get("id") or f"mcr_{i:04d}"
        yield CaseInput(case_id=case_id, presentation=entry["presentation"])


def load_ground_truth(path: pathlib.Path) -> dict[str, str]:
    """Return {case_id: ground_truth_diagnosis}.

    Auto-detects the corpus shape:
      - entry has `final_diagnosis` → cupcase-style
      - entry has `options` + `answer_idx` → medqa-style (ground truth is
        the option text at answer_idx)
    """
    data = json.loads(pathlib.Path(path).read_text())
    out: dict[str, str] = {}
    for i, entry in enumerate(data):
        case_id = (
            entry.get("case_id")
            or entry.get("id")
            or f"case_{i:04d}"
        )
        if "final_diagnosis" in entry:
            out[case_id] = entry["final_diagnosis"]
        elif "answer_idx" in entry and "options" in entry:
            idx = entry["answer_idx"]
            options = entry["options"]
            if isinstance(options, dict):
                out[case_id] = options.get(idx, "")
            elif isinstance(options, list):
                # numeric index
                try:
                    out[case_id] = options[int(idx)]
                except (ValueError, IndexError):
                    out[case_id] = ""
            else:
                out[case_id] = ""
        elif "ground_truth_diagnosis" in entry:
            # NEJM-style fallback (per data/cases/nejm/_schema.json)
            out[case_id] = entry["ground_truth_diagnosis"]
        else:
            out[case_id] = ""
    return out
