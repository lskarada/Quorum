"""Case corpus loader.

Reads JSON files from data/cases/{nejm,medqa}/ conforming to the corresponding
_schema.json and yields normalized CaseInput-shaped dicts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from quorum.orchestrator.schemas import CaseInput


def load_corpus(name: str, root: Path | None = None) -> Iterator[CaseInput]:
    """Iterate cases from data/cases/<name>/*.json.

    Args:
        name: corpus name, e.g. "nejm" or "medqa".
        root: optional repo root override (defaults to git toplevel).
    """
    # TODO: resolve root → root/data/cases/<name>/*.json, skip _schema.json,
    # validate each against the schema, yield CaseInput.
    raise NotImplementedError
