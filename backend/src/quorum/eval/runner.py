"""Eval runner.

Iterates over a corpus, runs the Panel on each case, and writes results
to data/results/<run_id>/<case_id>.json.
"""
from __future__ import annotations

from pathlib import Path

from quorum.llm.client import LLMClient


async def run_eval(
    corpus_name: str,
    model: str = "claude-opus-4-7",
    limit: int | None = None,
    results_root: Path | None = None,
) -> Path:
    """Run the panel against each case in the corpus.

    Returns the path to the results directory for this run.
    """
    # TODO: create results dir; for each case in load_corpus(corpus_name),
    # instantiate Panel(LLMClient(model)), run diagnose(), serialize verdict to disk.
    raise NotImplementedError
