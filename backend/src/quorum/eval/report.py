"""Markdown report generator for eval runs.

Produces a comparison table with headline numbers + comparison to MAI-DxO's
reported 85.5% (from arXiv 2506.22405).
"""
from __future__ import annotations

from pathlib import Path


def build_report(scores: dict, output: Path) -> None:
    """Write a markdown report from a scorer result dict.

    Output sections:
      - Headline numbers (top-1, top-5, MRR, cost, latency)
      - Per-case breakdown
      - Comparison row against MAI-DxO 85.5% (arXiv 2506.22405)
      - Per-specialty breakdown if metadata is available
    """
    # TODO: render markdown from `scores`, write to `output`.
    raise NotImplementedError
