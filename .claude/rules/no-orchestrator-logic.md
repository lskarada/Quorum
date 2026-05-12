# Rule: no orchestrator implementation in scaffolding pass

<important if="touching backend/src/quorum/orchestrator/**">

This file is auto-loaded when any file under `backend/src/quorum/orchestrator/` is edited. It overrides the default tendency to "be helpful" by filling in working implementations.

## What is allowed

- Module/class/function **docstrings** describing the contract.
- **Pydantic schemas** in `schemas.py` (full content — schemas ARE the contract).
- **Type-annotated function signatures** with no body, or a body of `raise NotImplementedError` / `...` / `# TODO: ...`.
- **Imports** required for the signatures to type-check.
- Prompt template files in `prompts/*.md` — **skeleton only** with a header, role description, input list, output JSON shape, and a TODO marker for behavioral guidelines.

## What is forbidden

- Any actual LLM call inside an agent's `deliberate()` or `deliberate_stream()`.
- Any actual deliberation loop in `Panel.diagnose()` or `Panel.diagnose_stream()`.
- Any heuristic or rules-based "stand-in" implementation. If you can't help yourself, write `raise NotImplementedError`, not a hand-rolled stub that "kind of" works.
- Any production prompt text. Bullet skeletons in `prompts/*.md` are fine. Multi-paragraph prompt content is not.
- Any new agent class beyond the five named in the brief.

## Why

The scope is locked because (a) the orchestrator design is the core thesis of the project and requires careful prompt-engineering iteration that should NOT happen in a scaffolding pass, and (b) silent half-implementations break the "all stub tests assert `raises NotImplementedError`" contract used to catch unintended drift.

If you believe the contract should change, surface the request to the main thread. Do not edit through it.

## Verification

Stub tests under `backend/tests/test_*_stub.py` assert that each agent's `deliberate()` raises `NotImplementedError`. If those tests go green without raising, something was implemented that shouldn't have been.

```bash
cd backend && uv run pytest tests/ -q -k "stub"
```

</important>
