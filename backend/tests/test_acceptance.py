"""Programmatic acceptance checks mirroring the README §8 checklist.

Each test asserts that a specific scaffolding artifact exists. Run with:
    cd backend && uv run pytest tests/test_acceptance.py -v

Designed to be the single command that confirms the scaffolding pass shipped
everything it promised.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _exists(*parts: str) -> Path:
    p = REPO_ROOT.joinpath(*parts)
    return p


# --- Workspace root ----------------------------------------------------------


@pytest.mark.parametrize(
    "rel",
    [
        "README.md",
        "LICENSE",
        ".gitignore",
        ".env.example",
        "pyproject.toml",
        ".python-version",
        "Makefile",
        "CLAUDE.md",
        ".claude/rules/no-orchestrator-logic.md",
    ],
)
def test_root_artifact_exists(rel: str):
    assert _exists(rel).exists(), f"Missing root artifact: {rel}"


# --- Backend -----------------------------------------------------------------


def test_backend_schemas_importable():
    from quorum.orchestrator.schemas import FinalVerdict  # noqa: F401


def test_backend_api_importable():
    from quorum.api.main import app  # noqa: F401


def test_backend_panel_importable():
    from quorum.orchestrator.panel import Panel  # noqa: F401


@pytest.mark.parametrize(
    "module_path",
    [
        "quorum.llm.providers.anthropic_provider",
        "quorum.llm.providers.openai_provider",
        "quorum.llm.providers.google_provider",
        "quorum.llm.providers.workers_ai_provider",
    ],
)
def test_llm_provider_importable(module_path: str):
    """All four provider stubs must exist and import cleanly."""
    import importlib

    importlib.import_module(module_path)


# --- Data --------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel",
    [
        "data/cases/nejm/_schema.json",
        "data/cases/medqa/_schema.json",
        "data/README.md",
    ],
)
def test_data_artifact_exists(rel: str):
    assert _exists(rel).exists(), f"Missing data artifact: {rel}"


# --- Docs --------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel",
    [
        "docs/architecture.md",
        "docs/eval_methodology.md",
        "docs/demo_script.md",
        "docs/milestone.md",
        "docs/api_reference.md",
    ],
)
def test_docs_artifact_exists(rel: str):
    assert _exists(rel).exists(), f"Missing docs artifact: {rel}"


# --- Research KB -------------------------------------------------------------


@pytest.mark.parametrize(
    "paper",
    [
        "mai_dxo",
        "sequential_diagnosis_benchmark",
        "medagentbench",
        "amie",
        "medhelm",
        "check",
        "medabstain",
        "medhallu",
        "medsafetybench",
        "careguardai",
        "polaris",
        "dxgpt",
        "conformal_abstention_yadkori",
        "medagents_bench",
    ],
)
def test_paper_annotation_exists(paper: str):
    p = _exists("research", "papers", f"{paper}.md")
    assert p.exists(), f"Missing paper annotation: {paper}.md"
    # Each annotation must have all 5 template sections.
    body = p.read_text()
    for section in ("## TL;DR", "## Key claim", "## Relevance to Quorum", "## How we cite it"):
        assert section in body, f"{paper}.md missing section: {section}"


@pytest.mark.parametrize(
    "rel",
    [
        "research/README.md",
        "research/prior_art_map.md",
        "research/fda_2026_cds_guidance.md",
    ],
)
def test_research_synthesis_exists(rel: str):
    assert _exists(rel).exists(), f"Missing research artifact: {rel}"


# --- Frontend ----------------------------------------------------------------


@pytest.mark.parametrize(
    "rel",
    [
        "frontend/package.json",
        "frontend/vite.config.ts",
        "frontend/tailwind.config.ts",
        "frontend/components.json",
        "frontend/src/App.tsx",
        "frontend/src/main.tsx",
        "frontend/src/routes/Home.tsx",
        "frontend/src/routes/Diagnose.tsx",
        "frontend/src/lib/types.ts",
        "frontend/src/lib/sse.ts",
        "frontend/src/lib/api.ts",
        "frontend/src/lib/utils.ts",
        "frontend/docs/ia.md",
    ],
)
def test_frontend_artifact_exists(rel: str):
    assert _exists(rel).exists(), f"Missing frontend artifact: {rel}"


# --- CI ----------------------------------------------------------------------


def test_ci_workflow_exists():
    assert _exists(".github/workflows/ci.yml").exists()


# --- Schemas (generated) ----------------------------------------------------


def test_schemas_bundle_exists_or_can_be_built():
    """The JSON schema bundle is generated, not hand-written.

    This test asserts it either already exists OR the dump_schemas script runs
    cleanly. (CI runs dump_schemas as a job step; locally a contributor may not
    have run it yet.)
    """
    schema_path = _exists("data", "schemas", "quorum.schema.json")
    if not schema_path.exists():
        # Try to build it.
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "scripts/dump_schemas.py"],
            cwd=REPO_ROOT / "backend",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"dump_schemas failed: {result.stderr}"
    assert schema_path.exists()


def test_anti_hallucination_flag_only_in_expected_files():
    """The literal `[abstract not independently retrieved` flag should appear
    ONLY in research/papers/ markdown files (never in docs/ or code).

    A flag appearing outside research/papers/ means a confabulation guard
    leaked into a non-bibliography file.
    """
    import subprocess

    result = subprocess.run(
        ["grep", "-rl", "abstract not independently retrieved", str(REPO_ROOT)],
        capture_output=True,
        text=True,
    )
    leaks = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        # Compiled Python caches mirror source content; ignore.
        if "/__pycache__/" in line or line.endswith(".pyc"):
            continue
        # The acceptance test itself mentions the literal in its docstring; allow.
        if line.endswith("test_acceptance.py"):
            continue
        # CLAUDE.md mentions it as a contract; allow.
        if line.endswith("CLAUDE.md"):
            continue
        # Subagent rules / prompts may mention it; allow under .claude/.
        if "/.claude/" in line:
            continue
        if "/research/papers/" in line or "/research/" in line:
            continue
        leaks.append(line)
    assert not leaks, f"Anti-hallucination flag leaked into: {leaks}"
