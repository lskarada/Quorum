"""Download HF datasets and normalize into data/cases/<name>/all.json.

Runtime-only script; relies on `datasets` (install via `uv pip install
--python .venv/bin/python3 datasets`). Output shape matches what
backend/src/quorum/eval/corpus.py loaders expect.

HF mirrors used (verified accessible 2026-05-24):
- medqa   → GBaker/MedQA-USMLE-4-options (parquet, no script loader)
- cupcase → ofir408/CUPCase              (test split only)
- mcr     → zou-lab/MedCaseReasoning     (train split)

Usage:
    cd backend && uv run python scripts/download_corpus.py            # all 3
    cd backend && uv run python scripts/download_corpus.py medqa      # one
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

from datasets import load_dataset

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CASES_DIR = REPO_ROOT / "data" / "cases"


def _write(name: str, rows: list[dict]) -> pathlib.Path:
    out = CASES_DIR / name / "all.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2))
    print(f"  wrote {len(rows)} rows -> {out}")
    return out


def medqa(limit: int = 500) -> None:
    """USMLE-format MCQ. Loader expects question + options dict + answer_idx."""
    print(f"medqa: loading GBaker/MedQA-USMLE-4-options[:{limit}] ...")
    ds = load_dataset("GBaker/MedQA-USMLE-4-options", split=f"train[:{limit}]")
    rows = []
    for i, ex in enumerate(ds):
        # `options` is stored as a stringified dict.
        opts_raw = ex["options"]
        opts = ast.literal_eval(opts_raw) if isinstance(opts_raw, str) else dict(opts_raw)
        rows.append({
            "id": f"medqa_{i:04d}",
            "question": ex["question"],
            "options": opts,
            "answer_idx": ex["answer_idx"],
            "answer": ex.get("answer", ""),
        })
    _write("medqa", rows)


def cupcase(limit: int = 200) -> None:
    """CUPCase (clinical case reports). Loader expects case_id, presentation,
    final_diagnosis. Real columns (verified 2026-05-24): clean_case_presentation,
    correct_diagnosis, distractor1/2/3. Test split only; no native case_id."""
    print(f"cupcase: loading ofir408/CUPCase[:{limit}] ...")
    ds = load_dataset("ofir408/CUPCase", split=f"test[:{limit}]")
    rows = []
    for i, ex in enumerate(ds):
        rows.append({
            "case_id": f"cupcase_{i:04d}",
            "presentation": ex["clean_case_presentation"],
            "final_diagnosis": ex["correct_diagnosis"],
        })
    _write("cupcase", rows)


def mcr(limit: int = 200) -> None:
    """MedCaseReasoning. Same shape as CUPCase plus diagnostic_reasoning field.
    Real columns: case_prompt, final_diagnosis, diagnostic_reasoning."""
    print(f"mcr: loading zou-lab/MedCaseReasoning[:{limit}] ...")
    ds = load_dataset("zou-lab/MedCaseReasoning", split=f"train[:{limit}]")
    rows = []
    for i, ex in enumerate(ds):
        case_id = ex.get("pmcid") or ex.get("case_id") or f"mcr_{i:04d}"
        rows.append({
            "case_id": case_id,
            "presentation": ex.get("case_prompt") or ex.get("case_text") or "",
            "final_diagnosis": ex.get("final_diagnosis") or ex.get("diagnosis") or "",
            "reasoning": ex.get("diagnostic_reasoning") or "",
        })
    _write("mcr", rows)


if __name__ == "__main__":
    which = sys.argv[1:] or ["medqa", "cupcase", "mcr"]
    for name in which:
        {"medqa": medqa, "cupcase": cupcase, "mcr": mcr}[name]()
