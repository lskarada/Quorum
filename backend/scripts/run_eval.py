"""Run the evaluation harness against a case corpus.

Usage:
    uv run python scripts/run_eval.py --corpus nejm [--limit 10] [--model claude-opus-4-7]
"""
from __future__ import annotations

import typer

app = typer.Typer(add_completion=False)


@app.command()
def main(
    corpus: str = typer.Option("nejm", help="Case corpus: nejm | medqa"),
    limit: int | None = typer.Option(None, help="Cap number of cases"),
    model: str = typer.Option("claude-opus-4-7", help="Default model for the panel"),
) -> None:
    """Run eval on a case corpus and write results to data/results/."""
    # TODO: load cases via quorum.eval.corpus, run quorum.eval.runner,
    # score via quorum.eval.scorer, emit report via quorum.eval.report.
    raise NotImplementedError


if __name__ == "__main__":
    app()
