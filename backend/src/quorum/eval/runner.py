"""Eval runner.

Iterates a corpus through Panel.diagnose() and writes one verdict JSON per
case plus a manifest.json into a results directory. Idempotent: a re-run
into the same dir skips cases whose result file already exists.

Cost guardrail: projected cost = n_cases * _ESTIMATED_COST_PER_CASE. If the
projection exceeds the QUORUM_MAX_COST_USD cap (default $20) the runner
refuses to start unless confirm_cost=True.
"""
from __future__ import annotations

import json
import os
import pathlib
import time
from collections.abc import Iterable

from quorum.llm.client import LLMClient
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import CaseInput

_ESTIMATED_COST_PER_CASE = 0.10  # conservative — used only for the env-gated cap.


async def run_eval(
    corpus: Iterable[CaseInput],
    panel_config: PanelConfig,
    n_cases: int,
    results_dir: pathlib.Path,
    confirm_cost: bool = False,
) -> pathlib.Path:
    """Run `panel_config` over the first `n_cases` of `corpus`.

    Args:
        corpus: iterable of CaseInput (loader output).
        panel_config: PanelConfig to instantiate the Panel with.
        n_cases: cap on how many cases to consume from the corpus.
        results_dir: target directory; created if missing. One JSON per case
            is written here plus a manifest.json.
        confirm_cost: must be True to bypass the projected-cost cap.

    Returns: results_dir (now containing per-case JSONs + manifest.json).
    """
    cases = list(corpus)[:n_cases]
    projected = len(cases) * _ESTIMATED_COST_PER_CASE
    cap = float(os.environ.get("QUORUM_MAX_COST_USD", "20"))
    if projected > cap and not confirm_cost:
        raise RuntimeError(
            f"Projected cost ${projected:.2f} exceeds QUORUM_MAX_COST_USD="
            f"${cap:.2f}. Pass confirm_cost=True to override."
        )

    results_dir.mkdir(parents=True, exist_ok=True)
    llm = LLMClient()
    panel = Panel(llm, panel_config)

    manifest_path = results_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {
            "schema_version": 1,
            "panel": panel_config.name,
            "n_cases": len(cases),
            "started_at": time.time(),
        }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    for case in cases:
        cid = case.case_id or "unknown"
        out_path = results_dir / f"case_{cid}.json"
        if out_path.exists():
            # idempotency — skip already-completed cases on re-run.
            continue
        verdict = await panel.diagnose(case)
        out_path.write_text(verdict.model_dump_json(indent=2))

    manifest["finished_at"] = time.time()
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return results_dir
