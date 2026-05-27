# v2 benchmark paused at Phase 4 gate, 2026-05-26

## Current state

All 10 cells **calibrated**. 0 cells **run**. Stopped at the Phase 5
human gate before any benchmark LLM spend.

Branch: `benchmark/v2-system-vs-model` (frozen at commit `86a4aee`).

## Calibrated cost-prior table (n=30 projection)

| Cell | Tier | cost_prior | n=30 raw | n=30 padded ×1.20 |
|---|---|---:|---:|---:|
| single_haiku | cheap | $0.00704 | $0.21 | $0.25 |
| dev_cheap | cheap | $0.00892 | $0.27 | $0.32 |
| uniform_cheap | cheap | $0.01529 | $0.46 | $0.55 |
| uniform_cheap_ensemble | cheap | $0.02906 | $0.87 | $1.05 |
| single_sonnet | mid | $0.02877 | $0.86 | $1.04 |
| uniform_mid | mid | $0.06319 | $1.90 | $2.27 |
| uniform_mid_ensemble | mid | $0.14614 | $4.38 | $5.26 |
| mixed_vendor | frontier | $0.09066 | $2.72 | $3.26 |
| baseline_single_call | frontier | $0.09114 | $2.73 | $3.28 |
| single_model_premium | frontier | $0.19524 | $5.86 | $7.03 |
| **All 10** | | | **$20.26** | **$24.32** |
| **9 (drop mid_ensemble)** | | | **$15.88** | **$19.06** |

Per-cell priors live in:
- Panel YAMLs: `backend/config/panels/<cell>.yaml` → `cost_prior_usd`
- Ensemble sidecars: `data/results/ensemble_cost_priors/<label>.json`

## Spend at pause

- Cumulative (lifetime): **$7.80** USD (`~/.quorum/spend.json`)
- Session-relative: $2.59 (started at $5.21)
- Remaining of $30 cap: **$22.20** — rolls forward intact

## Reason for pause

Strategic pivot decided in a separate Claude session. Project direction
moving from the MedQA tier-matched ablation (v2) to a SDBench/MAI-DxO-
style sequential diagnosis benchmark with calibration + audit trail
(v3 direction), on the NEJM CPC + MedCaseReasoning corpus.

Running v2's full 9-cell grid would burn ~$19–24 of the budget needed
for v3. The cleaner move is to freeze v2 calibrated-but-unrun and
redeploy the budget to v3.

## Resume instructions (if v3 direction is reverted)

```bash
git checkout benchmark/v2-system-vs-model
cd backend

# Then for each cell (cheapest first; see plan §5 for order):
QUORUM_MAX_COST_USD=30 uv run quorum-eval run \
  --corpus medqa --panel <cell> --n 30 --confirm-cost \
  --exclude tests/fixtures/prompt_tuning_holdout.json \
  --cases-root ../data/cases --results-root ../data/results

# Ensemble cells:
QUORUM_MAX_COST_USD=30 uv run quorum-eval ensemble \
  --corpus medqa --model <model> --n-votes 5 --n 30 \
  --label <label> --confirm-cost \
  --exclude tests/fixtures/prompt_tuning_holdout.json \
  --cases-root ../data/cases --results-root ../data/results
```

Cell ↔ model map for ensemble runs:
- `uniform_cheap_ensemble` → `anthropic/claude-haiku-4-5`
- `uniform_mid_ensemble`   → `anthropic/claude-sonnet-4-6`

Full Phase 5 plan, cell ordering, per-run checkpoint contract, and
Phases 6–7 diagnostics live in
`docs/superpowers/plans/2026-05-26-quorum-benchmark-v2.md`.

## What's reusable for v3 regardless of direction

Everything below survives the pivot — no code thrown away.

- **`backend/src/quorum/eval/ensemble.py`** — N-vote ensemble runner
  with majority-vote, fail-soft degradation, FinalVerdict-compatible
  output. 7 unit tests in `tests/test_ensemble_runner.py`. Useful for
  any benchmark that wants a sampling baseline.
- **4 new panel YAMLs** (`single_haiku`, `single_sonnet`,
  `uniform_cheap`, `uniform_mid`) — provides cheap/mid-tier 1-call and
  uniform-5-agent ablation cells; reusable for any future ablation.
- **LLM JSON coercion fixes** (`backend/src/quorum/llm/client.py`) —
  handles prose preambles, leading/trailing XML tags, mixed-case
  language tags. 6 regression tests in
  `tests/test_llm_client_json_coercion.py`. Cuts cheap-tier error
  rate measurably regardless of corpus.
- **Calibration plumbing** (`quorum-eval calibrate` + ensemble
  `--calibrate-only`) — works for any panel/ensemble. Sidecar
  cost-prior format at `data/results/ensemble_cost_priors/<label>.json`
  lets non-YAML cells (ensembles, future SDBench tier runners) carry
  priors without bloating the panel directory.
- **Frozen v1 baseline** at `data/results/v1_baseline_frozen.json` —
  reference for any future re-analysis of the dev_cheap MedQA run.

## Outstanding §8 items noted at the gate

Real defects worth fixing before any benchmark that depends on cost
attribution. Carry into v3 spec:

1. **`mixed_vendor` retry policy** — first calibration cohort of 3
   cases all failed (3/3 `is_error=True`), burned ~$0.35, then re-ran
   and 2/3 succeeded. Calibrator should retry transient empty-response
   failures before declaring "no successful cases" and bailing.
   Path: `backend/src/quorum/eval/cli.py` `calibrate` command + ditto
   for ensemble's `--calibrate-only` branch.

2. **`_error_verdict` cost-tracking bug** — `panel._error_verdict`
   returns `total_cost_usd=0.0` and empty transcript regardless of
   how much LLM spend the failed iteration incurred. Real spend
   (~/.quorum/spend.json) goes up; per-case verdict file says $0;
   scorer/calibrator under-counts cost. Affects every panel that
   errors mid-iteration. Path:
   `backend/src/quorum/orchestrator/panel.py:426` `_error_verdict`.

3. **opus-4 empty-response handling** — `single_model_premium`
   calibration hit 1/3 empty responses (`"Expecting value: line 1
   column 1 (char 0)"`). Parser fix can't recover from genuinely-empty
   content. Options: detect empty content explicitly and retry once,
   or attribute as an `empty_response` error mode in the v2 taxonomy.

4. **`AgentSlot.temperature` is declared but never consumed** —
   `panel_config.AgentSlot.temperature` is in every YAML
   (`temperature: 0.0`) but no agent passes it to `LLMClient.complete`.
   Every call uses the API's default temperature. Either remove the
   field or wire it through. Affects determinism / ensemble diversity.

## Phase-by-phase status at pause

| Phase | Status | Notes |
|---|---|---|
| 0 — pre-flight | ✅ complete | Branch created, v1 baseline frozen, tests green |
| 1 — JSON-fix TDD | ✅ complete | 6 new tests, full suite 176 → 183 → 188 green |
| 1.5 — ensemble runner TDD | ✅ complete | 7 new tests, smoke-call verified |
| 2 — recalibrate dev_cheap + baseline | ✅ complete | dev_cheap −14%, baseline +13% (under 30% flag) |
| 3 — 4 new panel YAMLs | ✅ complete | 5 new tests, 8 panels total |
| 4 — calibrate all + project cost | ✅ complete | All 10 cells primed |
| 5 — run benchmark | ⏸ paused | HARD STOP #6 gate, awaiting v3 direction |
| 6 — score + diagnostics | not started | |
| 7 — write-up (results.md §8/§9) | not started | |
| 8 — CLAUDE.md refresh + summary | not started | |

## Branch end-state

```
86a4aee chore(eval): calibrate 4 new panels + 2 ensemble labels for v2 phase-5 gate
b881b12 feat(panels): add four tier-matched ablation panels for v2 benchmark
37436ef chore(eval): recalibrate dev_cheap + baseline_single_call post JSON-fix
6b09077 feat(eval): ensemble baseline runner + quorum-eval ensemble subcommand
e0729eb fix(llm): JSON coercion handles prose preambles + XML wrappers + mixed-case fences
b27034f chore(v2): previous-session WIP + v1 baseline freeze
```

7 commits, unpushed, frozen.
