"""Tests for the eval harness.

When the harness is implemented, these should cover:
  - load_corpus yields validated CaseInput.
  - score_run computes top-1 / top-5 / MRR correctly.
  - build_report produces a renderable markdown file.

Currently the harness raises NotImplementedError; see test_stubs.py.
"""
from __future__ import annotations

import pytest


def test_TODO_eval_corpus_loader():
    pytest.skip("TODO: implement once eval.corpus is built")
