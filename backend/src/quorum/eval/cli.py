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
import os
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

from quorum.eval.corpus import load_cupcase, load_ground_truth, load_mcr, load_medqa  # noqa: E402
from quorum.eval.report import build_report  # noqa: E402
from quorum.eval.runner import run_eval  # noqa: E402
from quorum.eval.scorer import compare_runs, score_run  # noqa: E402
from quorum.orchestrator.panel_config import PanelConfig  # noqa: E402

app = typer.Typer(add_completion=False, help="Quorum eval harness CLI.")

_LOADERS = {"cupcase": load_cupcase, "medqa": load_medqa, "mcr": load_mcr}
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
    exclude: Annotated[
        pathlib.Path | None,
        typer.Option(
            help=(
                "Path to a JSON fixture with a `case_ids` array; matching "
                "case IDs are skipped. Used by Phase 7 to exclude prompt-"
                "tuning holdouts."
            ),
        ),
    ] = None,
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
    cases_iter = loader(cases_path)
    if exclude is not None:
        if not exclude.exists():
            raise typer.BadParameter(f"Exclude fixture not found: {exclude}")
        fixture = json.loads(exclude.read_text())
        excluded_ids = set(fixture.get("case_ids") or [])
        cases = [c for c in cases_iter if c.case_id not in excluded_ids]
        typer.echo(
            f"Excluded {len(excluded_ids)} case IDs from {exclude.name}; "
            f"{len(cases)} cases remain before --n cap."
        )
    else:
        cases = list(cases_iter)

    # Cost-prior pre-flight (Phase 2). If panel has a calibrated cost_prior_usd,
    # project n * prior against QUORUM_MAX_COST_USD and abort unless confirmed.
    if cfg.cost_prior_usd is not None:
        cap = float(os.environ.get("QUORUM_MAX_COST_USD", "20"))
        projected = n * cfg.cost_prior_usd
        if projected > cap and not confirm_cost:
            typer.echo(
                f"WARNING: panel '{cfg.name}' cost_prior_usd="
                f"${cfg.cost_prior_usd:.4f} × n={n} → projected ${projected:.2f} "
                f"exceeds QUORUM_MAX_COST_USD=${cap:.2f}. "
                f"Pass --confirm-cost to override."
            )
            raise typer.Exit(code=2)

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
def calibrate(
    panel: Annotated[str, typer.Option(help="Panel config name to calibrate")],
    corpus: Annotated[str, typer.Option(help="Corpus name (cupcase, medqa, mcr)")] = "medqa",
    n: Annotated[int, typer.Option(help="Number of smoke cases to average over")] = 3,
    cases_root: Annotated[
        pathlib.Path, typer.Option(help="Cases dir")
    ] = _DEFAULT_CASES_ROOT,
    results_root: Annotated[
        pathlib.Path, typer.Option(help="Results dir")
    ] = _DEFAULT_RESULTS_ROOT,
) -> None:
    """Run a small smoke set, compute mean cost/case, write cost_prior_usd
    into the panel YAML in-place.

    Idempotent: re-running overwrites the prior value with the new average.
    The calibration burns real LLM dollars at the smoke-set scale — keep n
    small (default 3).
    """
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
    out = results_root / f"calibrate_{cfg.name}_{corpus}_{int(time.time())}"
    asyncio.run(run_eval(cases, cfg, n, out, confirm_cost=True))

    # Sum cost from per-case verdict files (FinalVerdict.total_cost_usd).
    # Skip cases where is_error=True so transient LLM failures don't bias
    # the mean to zero. If every case errors, surface that explicitly.
    total = 0.0
    counted = 0
    errors = 0
    for vf in sorted(out.glob("case_*.json")):
        data = json.loads(vf.read_text())
        if data.get("is_error"):
            errors += 1
            continue
        c = data.get("total_cost_usd")
        if isinstance(c, (int, float)):
            total += float(c)
            counted += 1
    if counted == 0:
        raise typer.BadParameter(
            f"No successful cases under {out} ({errors} errored); cannot calibrate."
        )
    mean_cost = total / counted

    # Locate + rewrite the YAML in place, preserving comments by re-loading
    # the raw dict, updating, and dumping. (PyYAML default does NOT preserve
    # comments — acceptable for a generated calibrated value.)
    panels_root = pathlib.Path(
        os.environ.get("QUORUM_PANELS_DIR")
        or pathlib.Path(__file__).resolve().parents[3] / "config" / "panels"
    )
    yaml_path = panels_root / f"{cfg.name}.yaml"
    if not yaml_path.exists():
        raise typer.BadParameter(f"Panel YAML not found at {yaml_path}")
    import yaml as _yaml

    raw = _yaml.safe_load(yaml_path.read_text())
    raw["cost_prior_usd"] = round(mean_cost, 6)
    yaml_path.write_text(_yaml.safe_dump(raw, sort_keys=False))
    typer.echo(
        f"Calibrated {cfg.name}: cost_prior_usd={mean_cost:.6f} "
        f"(n_success={counted}, n_error={errors}, total=${total:.4f}) → {yaml_path}"
    )


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
