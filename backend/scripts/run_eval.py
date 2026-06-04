"""Thin wrapper around the real eval CLI.

Prefer the installed console script: `uv run quorum-eval run --corpus medqa ...`.
This wrapper exists so `python scripts/run_eval.py ...` resolves to the same
Typer app (sub-commands: run / score / report).
"""
from __future__ import annotations

from quorum.eval.cli import app

if __name__ == "__main__":
    app()
