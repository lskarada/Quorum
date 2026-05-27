# Rule: orchestrator scope by phase

<important if="touching backend/src/quorum/orchestrator/**">

This file is auto-loaded when any file under `backend/src/quorum/orchestrator/` is edited. The vertical-slice freeze has been lifted for the **Approach-B build phase** (see `docs/superpowers/specs/2026-05-23-quorum-completion-design.md`). New, broader scope below.

## Currently authorized for implementation

- `agents/hypothesis.py` — `deliberate()` is done; may be extended to consume prior-iteration transcript history. `deliberate_stream()` remains optional (only implement if a streaming-token UI requires it).
- `agents/test_chooser.py`, `agents/challenger.py`, `agents/stewardship.py`, `agents/checklist.py` — implement `deliberate()` against the structured-output contract in `schemas.py`. `deliberate_stream()` optional.
- `panel.py` — full multi-iteration consensus loop. Termination on `top_posterior > consensus_threshold`, `iteration >= max_iterations`, OR `checklist.recommend_continue == False`.
- `comparison_runner.py` (new) — runs two named panels in parallel against the same case; multiplexes SSE events tagged with `panel_id`.
- `panel_config.py` (new) — loads YAML configs from `backend/config/panels/*.yaml`; each agent's model is config-driven.
- `schemas.py` — canonical; only extend with new fields if compare-mode or panel-config require them.
- `prompts/hypothesis.md` — production content may be iterated.
- `prompts/{test_chooser,challenger,stewardship,checklist}.md` — production content (no longer skeletons).

## Forbidden in all cases

- Hand-rolled "stand-in" stubs that pretend to be implementations. If not implementing, write `raise NotImplementedError`.
- New agent classes beyond the five in the brief. The five-agent structure is the architectural contract.
- New runtime dependencies outside the pins in `backend/pyproject.toml`. PyYAML must be added explicitly if it is not already present — verify before importing.
- Hardcoding model assignments inside agent classes. Models come from `PanelConfig` only.
- Filling `data/cases/**/*.json` with synthetic LLM-generated cases without an explicit `synthetic: true` field in the JSON.

## Why this scope

The vertical slice proved the full pipe (UI ↔ SSE ↔ FastAPI ↔ Panel ↔ Hypothesis ↔ LLM). Approach B builds the remaining four agents, the multi-iter consensus loop, the comparison runner that enables the single-model-vs-mixed-vendor A/B story, and the eval harness that scores against public clinical case datasets. See the design doc for the full plan and per-phase gates.

If you believe this contract should change, surface to the main thread. Do not edit through it.

## Verification

```bash
# All agents: tests must pass without NotImplementedError asserts
cd backend && uv run pytest tests/test_agents.py -v

# Multi-iter panel: tests cover consensus termination paths
cd backend && uv run pytest tests/test_panel.py -v

# Compare runner: side-by-side execution + isolation under failure
cd backend && uv run pytest tests/test_comparison.py -v

# Schemas still round-trip
cd backend && uv run python scripts/dump_schemas.py
```

</important>
