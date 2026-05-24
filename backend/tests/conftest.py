"""Pytest session setup.

Sets a placeholder OPENROUTER_API_KEY so that any test which constructs
LLMClient() (without monkeypatching the env) gets a client whose
AsyncOpenAI HTTP layer is expected to be mocked by the test itself.

Tests that intentionally exercise the missing-key path call
`monkeypatch.delenv("OPENROUTER_API_KEY")` to override this.
"""
from __future__ import annotations

import os


def pytest_configure(config):
    os.environ.setdefault("OPENROUTER_API_KEY", "test-key-placeholder")
