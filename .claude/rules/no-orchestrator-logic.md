# Rule: orchestrator scope by phase

<important if="touching backend/src/quorum/orchestrator/**">

This file is auto-loaded when any file under `backend/src/quorum/orchestrator/` is edited. The scaffolding-pass freeze has been lifted for the **vertical-slice phase** (see `docs/IMPLEMENTATION_PLAN.md`). New, narrower scope below.

## Currently authorized for implementation (vertical slice)

- `agents/hypothesis.py` — `deliberate()` may be implemented. `deliberate_stream()` deferred to a later phase.
- `panel.py` — `diagnose()` and `diagnose_stream()` may be implemented, but only the **single-agent single-iteration** path (calls Hypothesis once, returns a verdict).
- `schemas.py` — full content is canonical (schemas are the contract).
- `prompts/hypothesis.md` — production prompt content may be added.

## Still frozen (must remain stubs raising NotImplementedError)

- `agents/test_chooser.py`, `agents/challenger.py`, `agents/stewardship.py`, `agents/checklist.py` — bodies remain `raise NotImplementedError`.
- Multi-iteration consensus loop in `panel.py` — single-iter only.
- `prompts/{test_chooser,challenger,stewardship,checklist}.md` — skeletons only.

## Forbidden in all cases

- Hand-rolled "stand-in" stubs that pretend to be implementations. If not implementing, write `raise NotImplementedError`.
- New agent classes beyond the five in the brief.
- New dependencies outside the pins in `backend/pyproject.toml`.
- Filling in production prompt text for the four frozen agents.

## Why this scope

Single-agent vertical slice proves the full pipe (UI ↔ SSE ↔ FastAPI ↔ Panel ↔ Hypothesis ↔ LLM) before the orchestration logic for 5-agent debate is invested in. Prompt-engineering iteration for the four frozen agents happens in a dedicated pass with its own gate.

If you believe the contract should change again, surface to the main thread. Do not edit through it.

## Verification

```bash
# Stub tests for the four frozen agents must still pass:
cd backend && uv run pytest tests/ -q -k "stub and not hypothesis"

# Hypothesis-specific tests should NOT assert NotImplementedError once Phase 2 is complete:
cd backend && uv run pytest tests/test_agents.py -q
```

</important>
