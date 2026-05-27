"""Pytest session setup.

Sets a placeholder OPENROUTER_API_KEY so that any test which constructs
LLMClient() (without monkeypatching the env) gets a client whose
AsyncOpenAI HTTP layer is expected to be mocked by the test itself.

Also auto-redirects the cumulative-spend tracker file to a tmp path
so pytest runs cannot pollute the real ~/.quorum/spend.json. Without
this, tests that exercise LLMClient.complete() leak mock-cost data
into the user's real spend tracker and can spuriously trip the cap.
"""
from __future__ import annotations

import os

import pytest


def pytest_configure(config):
    os.environ.setdefault("OPENROUTER_API_KEY", "test-key-placeholder")


@pytest.fixture(autouse=True)
def _isolate_spend_file(tmp_path, monkeypatch):
    """Redirect _SPEND_FILE to a tmp path for every test.

    Prevents test runs from writing to ~/.quorum/spend.json. Tests that
    need to inspect the file should use the same tmp_path fixture.
    """
    import quorum.llm.client as client_module
    monkeypatch.setattr(client_module, "_SPEND_FILE", tmp_path / "spend.json")
