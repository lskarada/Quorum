"""Typer CLI for the eval harness.

Subcommands:
    run      — execute a panel over a corpus, write per-case results.
    score    — aggregate metrics from a results directory.
    compare  — paired comparison of two result directories.
    report   — render a markdown report from a results directory.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import time
from typing import Annotated

import typer
from dotenv import load_dotenv

# Load .env from repo root if present so OPENROUTER_API_KEY etc. are picked up.
# Mirrors backend/scripts/prompt_iteration_eval.py. Done before quorum imports
# in case any module-level init reads the env.
_REPO_ROOT_ENV = pathlib.Path(__file__).resolve().parents[4] / ".env"
if _REPO_ROOT_ENV.exists():
    load_dotenv(_REPO_ROOT_ENV)

from quorum.eval.corpus import load_cupcase, load_ground_truth, load_medqa  # noqa: E402
from quorum.eval.report import build_report  # noqa: E402
from quorum.eval.runner import run_eval  # noqa: E402
from quorum.eval.scorer import compare_runs, score_run  # noqa: E402
from quorum.orchestrator.panel_config import PanelConfig  # noqa: E402

app = typer.Typer(add_completion=False, help="Quorum eval harness CLI.")

_LOADERS = {"cupcase": load_cupcase, "medqa": load_medqa}
_DEFAULT_CASES_ROOT = pathlib.Path("data/cases")
_DEFAULT_RESULTS_ROOT = pathlib.Path("data/results")


def _cfg(name: str) -> PanelConfig:
    cfgs = PanelConfig.list_available()
    matches = [c for c in cfgs if c.name == name]
    if not matches:
        raise typer.BadParameter(
            f"Unknown panel: {name}. Available: {[c.name for c in cfgs]}"
        )
    return matches[0]


@app.command()
def run(
    corpus: Annotated[str, typer.Option(help="Corpus name (cupcase, medqa)")],
    panel: Annotated[str, typer.Option(help="Panel config name")] = "dev_cheap",
    n: Annotated[int, typer.Option(help="Number of cases")] = 10,
    cases_root: Annotated[
        pathlib.Path, typer.Option(help="Cases dir")
    ] = _DEFAULT_CASES_ROOT,
    results_root: Annotated[
        pathlib.Path, typer.Option(help="Results dir")
    ] = _DEFAULT_RESULTS_ROOT,
    confirm_cost: Annotated[bool, typer.Option("--confirm-cost")] = False,
) -> None:
    """Run a panel over a corpus and write per-case verdicts."""
    cfg = _cfg(panel)
    loader = _LOADERS.get(corpus)
    if loader is None:
        raise typer.BadParameter(
            f"Unknown corpus: {corpus}. Available: {sorted(_LOADERS)}"
        )
    cases_path = cases_root / corpus / "all.json"
    if not cases_path.exists():
        raise typer.BadParameter(f"Corpus file not found: {cases_path}")
    cases = loader(cases_path)
    out = results_root / f"{cfg.name}_{corpus}_{int(time.time())}"
    asyncio.run(run_eval(cases, cfg, n, out, confirm_cost=confirm_cost))
    typer.echo(str(out))


@app.command()
def score(
    results_dir: Annotated[pathlib.Path, typer.Argument()],
    corpus: Annotated[str, typer.Option(help="Corpus name for ground-truth lookup")],
    cases_root: Annotated[pathlib.Path, typer.Option()] = _DEFAULT_CASES_ROOT,
) -> None:
    """Aggregate metrics from a results directory."""
    gt = load_ground_truth(cases_root / corpus / "all.json")
    s = score_run(results_dir, gt)
    typer.echo(json.dumps(s, indent=2, default=str))


@app.command()
def compare(
    run_a: Annotated[pathlib.Path, typer.Argument()],
    run_b: Annotated[pathlib.Path, typer.Argument()],
    corpus: Annotated[str, typer.Option()],
    cases_root: Annotated[pathlib.Path, typer.Option()] = _DEFAULT_CASES_ROOT,
) -> None:
    """Paired comparison of two result directories."""
    gt = load_ground_truth(cases_root / corpus / "all.json")
    cmp = compare_runs(run_a, run_b, gt)
    typer.echo(json.dumps(cmp, indent=2, default=str))


@app.command()
def report(
    results_dir: Annotated[pathlib.Path, typer.Argument()],
    corpus: Annotated[str, typer.Option()],
    cases_root: Annotated[pathlib.Path, typer.Option()] = _DEFAULT_CASES_ROOT,
    output: Annotated[
        pathlib.Path | None,
        typer.Option(help="Output path (default results_dir/report.md)"),
    ] = None,
) -> None:
    """Render a markdown report from a results directory."""
    gt = load_ground_truth(cases_root / corpus / "all.json")
    s = score_run(results_dir, gt)
    out = output or (results_dir / "report.md")
    build_report(s, out)
    typer.echo(str(out))


if __name__ == "__main__":
    app()
