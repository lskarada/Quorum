# Rule: v2 benchmark scope (Calibrated-Auditable MAI-DxO)

<important if="touching backend/src/quorum/gatekeeper/** OR backend/src/quorum/audit/** OR backend/src/quorum/calibration/** OR backend/src/quorum/orchestrator/safety.py OR backend/config/panels/v2_*.yaml OR data/cases/eval_corpus_v2/**">

The Quorum v2 build is bounded by two authoritative documents; if they conflict, the spec wins:

- **SPEC**: `docs/superpowers/specs/2026-05-26-quorum-calibrated-auditable-mai-dxo-design.md`
- **PLAN**: `docs/superpowers/plans/2026-05-27-quorum-calibrated-mai-dxo.md`

## Non-negotiable for v2

1. **No new agent classes.** The 5 agents (Hypothesis / TestChooser / Challenger / Stewardship / Checklist) are the architectural contract.
2. **No new runtime dependencies** beyond `backend/pyproject.toml`. Required deps (`anthropic`, `pydantic`, `pyyaml`, `httpx`) are already pinned.
3. **Sonnet 4.6 only** for all 5 agents in v2 panels. Opus 4.7 is allowed ONLY in the optional Phase 8 mini-arm and only if remaining spend budget >= $20.
4. **Spend hard stop: $300.** Raised $80 (gate $75) → $142 → $200 → $250 → **$300** by explicit user approval. The $200 step (2026-05-30) funded the v3 NEJM-CPC campaign; the →$250 step (2026-05-31) funded the once-only holdout self-consistency run at k=5 × max_turns=30 after the measured cost basis came in at ~$1.41/case (not the ~$0.50/case the plan budgeted); the →$300 step (2026-05-31) gives margin to complete the k=5 holdout + fair baseline comfortably under the rail. Spend gate enforces the $300 hard stop / $290 warn via `backend/scripts/spend_gate.sh` AND the client tracker rail `QUORUM_TOTAL_SPEND_LIMIT_USD=300` in `.env`; do NOT raise further without explicit user approval. Log spend after every API run with `bash backend/scripts/log_spend.sh AMOUNT "label"`.
5. **TUNE/EVAL discipline**: 5 TUNE cases, 30 EVAL cases. EVAL runs once. Never tune on EVAL. Never modify `data/cases/eval_corpus_v2/splits.json` after Phase 1.
6. **Copyright**: `data/cases/eval_corpus_v2/nejm_sample.json` contains NEJM-paywalled text and is gitignored. Do NOT commit it, redistribute it, or publish it.
7. **Agent return contracts** (verified 2026-05-27): existing agents return `AgentMessage` with `structured_output: Optional[Union[Differential, NextTest, dict]]`. The Hypothesis posterior lives at `msg.structured_output.candidates[i].posterior` (each `DiagnosisCandidate` has `name: str` and `posterior: float`). TestChooser query is `msg.structured_output.name`. Challenger/Stewardship/Checklist `structured_output` is a free-form dict — inspect each agent's prompt to find the expected keys. Do NOT assume flat attribute names like `accept_test`, `top_alternative`, `unresolved_concerns` — they do not exist as direct attributes.
8. **Panel constructor**: `Panel(llm: LLMClient, config: PanelConfig | None = None)`. The first positional kwarg is `llm`, NOT `llm_client`. All `await self.llm.complete(messages=...)` calls are async — test stubs must be async too (use `unittest.mock.AsyncMock`).

## Verification gates

After each phase:
```bash
cd backend && uv run pytest -q
bash backend/scripts/log_spend.sh 0.00 "phase-N gate check"
cat data/results/.spend_total.txt
```

## When this rule should NOT apply

This rule scopes the **v2 build**. v1 panels (`dev_cheap`, `baseline_single_call`, `single_haiku`, `single_sonnet`, `uniform_cheap`, `uniform_mid`) are frozen and outside this scope. Do not modify them.

</important>
