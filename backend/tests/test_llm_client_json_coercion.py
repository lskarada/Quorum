"""Regression tests for haiku-4-5 JSON-coercion failure modes.

Each test corresponds to a sample in
backend/tests/fixtures/haiku_json_failures.json — the canonical
JSON-emission patterns that defeat strict json.loads. These mirror the
failure shapes that drove dev_cheap's 33% v1 error_rate before the
v2-phase-1 fix; v1 instrumentation did not persist raw_response so the
fixtures are representative rather than verbatim (see fixture _source).

When these all pass, _normalize_json_content is robust enough that an
agent's subsequent json.loads succeeds on any of the listed patterns.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from quorum.llm.client import _normalize_json_content

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "haiku_json_failures.json"
)


def _load_sample(sample_id: str) -> dict:
    data = json.loads(_FIXTURE.read_text())
    for s in data["samples"]:
        if s["id"] == sample_id:
            return s
    raise KeyError(f"sample {sample_id!r} not in fixture")


def _assert_round_trips(sample_id: str) -> None:
    sample = _load_sample(sample_id)
    coerced = _normalize_json_content(sample["raw"])
    parsed = json.loads(coerced)
    assert parsed == sample["expected_value"], (
        f"{sample_id}: coerced={coerced!r}"
    )


def test_extracts_json_from_prose_preamble():
    _assert_round_trips("prose_preamble_then_json")


def test_strips_leading_xml_tag():
    _assert_round_trips("leading_xml_tag")


def test_extracts_json_after_thinking_block():
    _assert_round_trips("json_inside_thinking_tags")


def test_strips_mixed_case_lang_tag():
    _assert_round_trips("fence_with_lang_tag_mixed_case")


def test_handles_trailing_xml_after_object():
    _assert_round_trips("trailing_xml_tag_after_object")


def test_non_json_string_passes_through_unchanged():
    """Negative control: pure prose should not be mutated, so the agent's
    json.loads error path still fires and the failure is surfaced honestly.
    """
    out = _normalize_json_content("I'm sorry, I cannot answer this.")
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
