# /goal prompt — Quorum benchmark v2 (system-vs-model attribution + improvement signal)

/goal Benchmark Quorum cleanly so we can attribute any accuracy delta
to "the 5-agent debate system" vs "the underlying model" — not both
mixed together — AND surface which parts of the pipeline are highest-
leverage to improve next. Spend cap for this whole session: $30 USD,
hard. Treat this prompt as the contract.

== STRATEGIC CONTEXT (read first; don't skip) ==

This is v2 of a three-session optimization sequence. Knowing where v2
sits prevents scope creep:

  v2 (THIS SESSION): cheap + mid tier ablation, ensemble control at
       cheap, full diagnostics → produces a ranked "what to fix" list.
       Frontier coverage is limited to Anthropic single_model_premium
       and mixed_vendor (already calibrated). No new vendors, no
       frontier ensemble.

  v3 (NEXT /GOAL, after implementing v2's top 1–3 fixes): re-run
       cheap+mid to confirm improvements survived, AND add
       DeepSeek V4-Pro triplet (single / ensemble / 5-agent) as a
       "near-frontier-cheap" tier (~$0.435/M input, $0.87/M output
       per OpenRouter — ~35× cheaper than Anthropic Opus). Estimated
       v3 budget: $5–10. Phase 7 of THIS session pre-stages the v3
       prompt.

  v4 (CONDITIONAL — only if v3 shows debate-uplift persists at
       near-frontier): Anthropic Opus triplet, probably without
       ensemble (too expensive). Estimated $15–25. Skip entirely if
       v3 shows debate-uplift collapses at higher capability.

Why this ordering: v2 diagnostics generalize across tiers, so fixing
them once benefits v3 and v4. Mixing optimization-finding with
tier-expansion in one session destroys attribution. DeepSeek V4-Pro
is cheap enough to add now but adding it would dilute v2's focus and
capture suboptimal pipeline state — better to add it once the
diagnostics-driven fixes from v2 are in place.

== HYPOTHESES BEING TESTED ==

State these up front so results are interpretable, not retrofitted:

H1 (tier ablation): 5-agent debate uplift over a single call shrinks
   monotonically from cheap → mid → frontier tier.
H2 (ensemble control): At cheap tier, 5-agent debate beats a naive
   5x-sample-and-vote ensemble of the same model. If it doesn't, the
   "debate" mechanism is just sampling-with-extra-cost.
H3 (JSON-fix isolation): Phase 1's parser fix accounts for a
   measurable share of dev_cheap's v2 vs v1 accuracy delta —
   independently from any debate effect.
H4 (cross-vendor): At frontier tier, mixed-vendor beats single-vendor
   premium (consistent with v1 directional finding, n permitting).
H5 (convergence): >50% of 5-agent runs reach consensus by iteration 1,
   meaning max_iterations=3 is over-provisioned and a cost lever.

Each phase below ends with "Expected learning:" — name it before
running, so a null result is interpretable and not retrofitted.

== HARD STOPS ==

1. Cumulative LLM spend exceeds $30.00 USD. Set
   `export QUORUM_MAX_COST_USD=30` before any LLM-touching phase.
   Check `cat ~/.quorum/spend.json` between every phase + every panel
   run in phase 5.
2. Any verification command returns non-zero. Diagnose, don't patch
   the test. If a test must change, surface to user with reasoning.
3. Working tree drifts outside the phase's listed paths.
4. Any NotImplementedError stub re-appears.
5. New runtime deps outside backend/pyproject.toml or frontend
   package.json. STOP and ask.
6. Phase 5 (the expensive run) begins WITHOUT explicit user approval
   via AskUserQuestion, with computed cost projection + remaining cap.
7. Phase 4 cost projection for phase 5 exceeds $22. STOP and
   AskUserQuestion which panels to defer — the mid_ensemble panel
   (item B in phase 3) is the first to cut.
8. ANY proposal to add DeepSeek / new vendor / frontier ensemble in
   this session. Those are explicitly v3/v4 scope. STOP and tell the
   user the proposal belongs in the v3 prompt.

== ANTI-HALLUCINATION + KARPATHY GUARDRAILS ==

Both already in CLAUDE.md — re-read once at session start. Key items
specific to this session:

- After every Write: `ls -la <path>` + `wc -l <path>` and report.
- Every $ figure must come from cost_prior_usd in a YAML, a real
  ~/.quorum/spend.json delta, or a manifest.json — never estimated.
- Surgical changes only. Don't refactor adjacent code.
- Every phase ends with a runnable verification command + expected
  output. Report both.

== STATISTICAL-POWER CAVEAT (read before phase 6) ==

n=30 paired McNemar needs ~7–10 discordant pairs for p<0.05. If
discordant_pairs<7, report effect size + 95% CI but DO NOT claim
"no effect" — pre-commit to: "p>0.05 with discordant_pairs<7 is
consistent with both H0 and H1; result is underpowered." No
post-hoc pair selection to chase significance.

== TDD GATE ==

Phases 1, 1.5, 3 are code → TDD required (red → green → refactor).
Phases 0, 2, 4, 5, 6, 7, 8 are operations or docs → TDD does not apply.

== PHASE 0 — PRE-FLIGHT ==

Expected learning: confirm we start from a known-green state and
record the v1 baseline that phase 1's fix will be measured against.

Tasks:
- `git status` — note the ~7 uncommitted/untracked files from the
  prior /goal session. Default: create branch
  `benchmark/v2-system-vs-model` and stage uncommitted work as a
  single "previous session WIP" commit on it.
- `cd backend && uv run pytest -q` — confirm green baseline.
- `cd frontend && pnpm vitest run` — confirm green.
- Confirm env: OPENROUTER_API_KEY present. CLOUDFLARE_AI_GATEWAY_URL
  presence noted (cached re-runs are effectively free — flag if
  missing; strongly recommended before phase 4+).
- `cat ~/.quorum/spend.json` — record starting spend ($X.XX).
- Read docs/results.md and docs/eval_methodology.md in full.
- **Freeze v1 baseline**: from the most recent dev_cheap v1 results
  directory under data/results/, extract and save to
  `data/results/v1_baseline_frozen.json`: {top1, mrr, mean_cost,
  error_rate, n_json_parse_errors}. This is phase 1's attribution
  reference.

Verify: both test suites green; starting spend reported; v1 baseline
frozen file exists with all 5 fields populated.

== PHASE 1 — FIX haiku-4-5 JSON-PARSE BUG (TDD) ==

Expected learning: quantify how much of dev_cheap's v1 error rate
was parsing vs model substance. If parser fix flips dev_cheap's
ranking, the v1 conclusion was a measurement artifact.

TDD step:
- Find 3–5 raw responses in data/results/dev_cheap_medqa_*/case_*.json
  where verdict has is_error=true with a JSON-related error. Save raw
  strings to backend/tests/fixtures/haiku_json_failures.json.
  (If no captured failures exist, AskUserQuestion whether to spend
  $0.50 generating fresh failures via 3–5 haiku-4-5 calls.)
- Write backend/tests/test_llm_client_json_coercion.py with one test
  per captured failure mode (test_strips_markdown_fence,
  test_extracts_json_from_prose_preamble,
  test_handles_trailing_text_after_json, etc.). Confirm red.

Implement step:
- Extend the JSON-coercion path in backend/src/quorum/llm/client.py.
  Surgical edits only. Likely: `re.search(r'\{.*\}', ..., re.DOTALL)`
  fallback, more aggressive fence stripping, trailing-text tolerance.
- Re-run new tests; confirm green.
- Run full backend suite; confirm no regressions.

Verify:
- `cd backend && uv run pytest tests/test_llm_client_json_coercion.py -v` — pass.
- `cd backend && uv run pytest -q` — full suite green.
- Spend: <$0.50.

== PHASE 1.5 — ENSEMBLE BASELINE RUNNER (TDD) ==

Expected learning: enables H2. Without this, "5-agent debate beats
single call" is confounded with "5 samples beats 1 sample." This
phase builds the missing control.

Design: a new eval CLI subcommand `quorum-eval ensemble` that, for
each case, makes N independent Hypothesis-prompt calls to a single
specified model, majority-votes the top diagnosis, and writes a
manifest in the same format as `quorum-eval run`. No orchestrator,
no Challenger/Stewardship/Checklist — pure sampling control.

TDD step:
- Write backend/tests/test_ensemble_runner.py covering:
  - 5 mocked LLMClient calls return distinct diagnoses; majority vote
    picks the modal one.
  - All 5 calls return same diagnosis → that diagnosis wins, with
    confidence flag.
  - 1 call raises → ensemble degrades to 4-of-4; flagged in manifest.
  - Manifest schema matches quorum-eval run output (top-N, MRR, cost,
    is_error fields).
- Confirm red.

Implement step:
- Add `backend/src/quorum/eval/ensemble.py` (~150 LOC):
  - Function `run_ensemble(case, model, n_votes, llm_client) -> Verdict`
  - Reads the same hypothesis.md prompt as the orchestrator.
  - Direct LLMClient calls in a loop, no panel.
- Add `ensemble` subcommand to `backend/src/quorum/eval/cli.py`:
  `quorum-eval ensemble --corpus medqa --model anthropic/claude-haiku-4-5 --n-votes 5 --n 30 --label uniform_cheap_ensemble`
- Add `--calibrate-only` flag (same shape as `quorum-eval calibrate`
  but for the ensemble subcommand) so phase 4 can prime cost_prior
  for the ensemble cells.
- Re-run tests; confirm green.
- Smoke-run `--n 1` against a single MedQA case; confirm manifest
  written and shape matches `quorum-eval run` output.

Verify:
- `cd backend && uv run pytest tests/test_ensemble_runner.py -v` — pass.
- `cd backend && uv run pytest -q` — full suite green.
- `cd backend && uv run quorum-eval ensemble --help` shows the command.
- Spend: <$0.20 (mostly mocked; one smoke call).

== PHASE 2 — RECALIBRATE EXISTING PANELS POST-FIX ==

Expected learning: cost_prior drift from the JSON fix tells us how
much the parser was driving retries.

Tasks:
- `cd backend && uv run quorum-eval calibrate --panel dev_cheap --n 3`
- `cd backend && uv run quorum-eval calibrate --panel baseline_single_call --n 3`
- If cost_prior moved >30%, flag to user with the delta.

Verify:
- `git diff backend/config/panels/dev_cheap.yaml backend/config/panels/baseline_single_call.yaml`
  shows only cost_prior_usd changes.
- Spend after phase 2 cumulative: ~$1.

== PHASE 3 — ADD FOUR NEW PANEL CONFIGS (TDD) ==

Expected learning: enable tier-matched ablation cells.

Create (5-agent and 1-call panels — ensembles are run via the CLI
subcommand from phase 1.5, NOT as panel YAMLs):

  1. `backend/config/panels/single_haiku.yaml` — 1-call,
     anthropic/claude-haiku-4-5, max_iterations=1.
  2. `backend/config/panels/single_sonnet.yaml` — 1-call,
     anthropic/claude-sonnet-4-6, max_iterations=1.
  3. `backend/config/panels/uniform_cheap.yaml` — 5-agent,
     anthropic/claude-haiku-4-5 in every slot, max_iterations=3.
  4. `backend/config/panels/uniform_mid.yaml` — 5-agent,
     anthropic/claude-sonnet-4-6 in every slot, max_iterations=3.

DO NOT touch existing single_model_premium.yaml or mixed_vendor.yaml.
DO NOT add a DeepSeek panel (v3 scope per HARD STOP #8).

TDD step:
- backend/tests/test_new_panels_load.py — one test per panel asserts
  YAML loads via PanelConfig.from_file(), has expected model fields,
  round-trips. Confirm red.

Implement:
- Write each YAML following existing dev_cheap.yaml / baseline_single_call.yaml
  shapes. temperature: 0.0 throughout.
- Re-run tests; confirm green.

Verify:
- `cd backend && uv run pytest tests/test_new_panels_load.py -v` — green.
- `ls backend/config/panels/` shows 8 YAMLs total.
- Spend: $0.

== PHASE 4 — CALIBRATE ALL PANELS + ENSEMBLE LABELS ==

Expected learning: real cost_prior for every cell that will run in
phase 5, so the gate projection is grounded.

Calibrate panels (sequentially; `cat ~/.quorum/spend.json` between
each):
- `uv run --project backend quorum-eval calibrate --panel single_haiku --n 3`
- `uv run --project backend quorum-eval calibrate --panel single_sonnet --n 3`
- `uv run --project backend quorum-eval calibrate --panel uniform_cheap --n 3`
- `uv run --project backend quorum-eval calibrate --panel uniform_mid --n 3`
- `uv run --project backend quorum-eval calibrate --panel single_model_premium --n 3`
- `uv run --project backend quorum-eval calibrate --panel mixed_vendor --n 3`

Calibrate ensemble labels (n=3; writes cost_prior to a sidecar JSON
since ensembles aren't panel YAMLs):
- `uv run --project backend quorum-eval ensemble --corpus medqa --model anthropic/claude-haiku-4-5 --n-votes 5 --n 3 --label uniform_cheap_ensemble --calibrate-only`
- `uv run --project backend quorum-eval ensemble --corpus medqa --model anthropic/claude-sonnet-4-6 --n-votes 5 --n 3 --label uniform_mid_ensemble --calibrate-only`

Phase 5 cost projection at n=30:
  cheap-tier:    single_haiku + uniform_cheap + uniform_cheap_ensemble + dev_cheap
  mid-tier:      single_sonnet + uniform_mid + uniform_mid_ensemble
  frontier-tier: baseline_single_call + single_model_premium + mixed_vendor

Sum the 10 cells × 30 cases. Expected total: $18–28.

Hard stops:
- If running total during phase 4 crosses $5, STOP and AskUserQuestion.
- If projected phase 5 total exceeds $22, drop uniform_mid_ensemble
  first (saves ~$3–5), then re-project.

Verify:
- All 6 panel YAMLs have cost_prior_usd set.
- Both ensemble sidecar JSONs exist with cost_prior populated.
- Total projected phase 5 cost reported with itemization per cell.
- Spend after phase 4 cumulative: ~$5–7 expected.

== PHASE 5 — RUN THE BENCHMARK (HUMAN GATE) ==

This is the expensive phase. STOP and AskUserQuestion with:
- Itemized $ projection for each of the 10 cells at n=30.
- Cumulative-to-date spend + remaining cap.
- Recommended set: all 10. Fallback: drop uniform_mid_ensemble if
  projection > $22.
- Explicit confirmation to proceed.

Only after approval, run each cell. Panel order (cheapest first;
ensembles run before their corresponding debate panel):

  1. single_haiku
  2. uniform_cheap_ensemble    (CLI: quorum-eval ensemble ...)
  3. uniform_cheap
  4. dev_cheap                  (re-run, supersedes v1)
  5. single_sonnet
  6. uniform_mid_ensemble       (CLI: quorum-eval ensemble ...) — IF NOT DEFERRED
  7. uniform_mid
  8. baseline_single_call
  9. single_model_premium
 10. mixed_vendor

Standard panel command:
  QUORUM_MAX_COST_USD=30 uv run --project backend quorum-eval run \
    --corpus medqa --panel <name> --n 30 --confirm-cost \
    --exclude backend/tests/fixtures/prompt_tuning_holdout.json \
    --cases-root data/cases --results-root data/results

Ensemble command:
  QUORUM_MAX_COST_USD=30 uv run --project backend quorum-eval ensemble \
    --corpus medqa --model <model> --n-votes 5 --n 30 \
    --label <label> --confirm-cost \
    --exclude backend/tests/fixtures/prompt_tuning_holdout.json \
    --results-root data/results

INCREMENTAL CHECKPOINT (mandatory between each run):
- `cat ~/.quorum/spend.json` → report cumulative.
- Append one line to `data/results/v2_progress.jsonl`:
  {cell, ts, results_dir, top1, mrr, mean_cost, error_rate, cumulative_spend}
  This makes a budget-truncated run still yield ranked, attributable
  data.
- If cumulative spend approaches $25, STOP and AskUserQuestion which
  remaining cells (if any) are essential.

Verify per run:
- `data/results/<cell>_medqa_<ts>/manifest.json` exists.
- Mean cost per case within 50% of cost_prior_usd (large deviations
  flagged).
- progress.jsonl line appended.

== PHASE 6 — SCORE + DIAGNOSTICS + PAIRWISE COMPARE ==

Expected learning: not just "did debate help" but "where in the
pipeline does cost / error / time go, and what's the highest-leverage
next change." These diagnostics are the input to v3's plan.

6a. Score + report every cell:
- `uv run --project backend quorum-eval score <dir> --corpus medqa --cases-root data/cases`
- `uv run --project backend quorum-eval report <dir> --corpus medqa --cases-root data/cases`

6b. Error-mode taxonomy (write a one-off script
`backend/scripts/classify_error_modes.py` if not already present;
it's a post-hoc analyzer, not production code — keep it small):
- For every is_error=true verdict across all 10 result dirs, classify
  the raw_response field into:
  {json_parse_error, refusal, timeout, hallucinated_diagnosis_not_in_ddx,
   empty_response, other}.
- Aggregate per cell. Write to
  `data/results/v2_error_modes.json` with shape
  {cell: {json_parse: N, refusal: N, ...}}.

6c. Per-iteration / per-stage cost analysis (for 5-agent cells only):
- For each manifest, extract per-iteration data if present
  (iterations_taken, per-iteration top diagnoses).
- Compute: % of cases that converged at iter 1 vs iter 2 vs iter 3.
- Compute: per-stage cost share (hypothesis / test_chooser /
  challenger / stewardship / checklist) averaged across cases, if
  manifest tracks per-call cost. If the manifest doesn't expose this,
  flag as a future instrumentation improvement and skip — do NOT
  invent numbers.
- Write to `data/results/v2_pipeline_diagnostics.json`.

6d. JSON-fix attribution (H3):
- Compare v2 dev_cheap (from this run) vs frozen v1 baseline (from
  phase 0).
- Decompose Δ accuracy: (drop in json_parse error_rate × top-1 of
  parsed cases) + residual.
- Write to `data/results/v2_json_fix_attribution.json`.

6e. Pairwise comparisons (McNemar on top-1, Wilcoxon on MRR):
  Tier-ablation pairs (H1):
  - single_haiku vs uniform_cheap                  → cheap debate uplift
  - single_sonnet vs uniform_mid                   → mid debate uplift
  - baseline_single_call vs single_model_premium   → frontier debate uplift

  Ensemble-control pairs (H2):
  - single_haiku vs uniform_cheap_ensemble         → cheap sampling effect
  - uniform_cheap_ensemble vs uniform_cheap        → cheap debate-over-ensemble
  - (mid_ensemble pairs ONLY IF not deferred)

  Cross-vendor (H4):
  - single_model_premium vs mixed_vendor

  Vendor-mix at cheap (clarifies dev_cheap composition):
  - dev_cheap vs uniform_cheap                     → cross-vendor effect at cheap

For every pair: report Δ top-1, 95% CI, McNemar p, Wilcoxon p,
discordant_pairs count. Flag any pair with discordant_pairs<7 as
underpowered per the statistical-power caveat.

6f. Convergence stats (H5):
- From 6c output, report % of 5-agent runs converging at iter 1.
- If >50%, flag max_iterations as a cost lever for v3.

Save the unified table to `data/results/v2_benchmark_summary.json`
with: per-cell metrics, error-mode breakdown, pipeline diagnostics,
JSON-fix attribution, every pair's stats, convergence stats.

Verify: every cell + every pair has a row; no NaN values; p-values
are floats in [0,1]; underpowered pairs explicitly flagged.

== PHASE 7 — WRITE-UP (docs/results.md v2) + PRE-STAGE v3 ==

Expected learning: end-state document that v3's /goal prompt can act
on directly.

Replace docs/results.md with:

1. Original headline section flagged "v1 (deprecated)".
2. "v2 — tier-matched ablation" section with the 10-cell table
   (cell, top-1, MRR, mean cost, error rate, model tier, mechanism).
3. "System uplift by tier" sub-table (3 rows: cheap/mid/frontier;
   each with 1-call top-1, ensemble top-1, 5-agent top-1, Δ debate
   over ensemble, Δ debate over single, McNemar p).
4. "Error-mode breakdown" sub-table from 6b — one row per cell, one
   column per error category.
5. "Pipeline diagnostics" section from 6c — convergence % by
   iteration, per-stage cost share where available.
6. "JSON-fix attribution" callout from 6d — explicit decomposition
   of v2 dev_cheap vs v1.
7. "Cross-vendor finding" from 6e.
8. **"What to improve next" section** — direct mapping from
   diagnostics to candidate changes, e.g.:
   - If error_modes shows >5% json_parse remaining → harden parser.
   - If convergence-at-iter-1 is >50% → cap max_iterations at 1, save
     ~60% cost.
   - If per-stage cost shows one agent dominating spend → audit its
     prompt for redundancy.
   - If ensemble matches debate within margin of error at cheap tier
     → debate mechanism may not be earning its keep there.
   Each recommendation must cite the diagnostic file that justifies
   it. Rank items by (expected accuracy uplift OR cost reduction) /
   implementation effort.

9. **"Recommended for v3" section** (NEW — pre-stages the next /goal):
   List, in priority order:
   - The top 1–3 "What to improve next" items from §8 that v3 should
     implement before adding any new tier.
   - Conditional addition: "If cheap-tier debate uplift ≥ 5pts AND
     statistically significant, v3 should add the DeepSeek V4-Pro
     near-frontier-cheap tier — single / ensemble / 5-agent triplet
     via OpenRouter (model id: deepseek/deepseek-v4-pro). Pricing:
     ~$0.435/M input, $0.87/M output (cache miss); $0.003625/M cache
     hit. Estimated v3 budget for that triplet: ~$1–2 at n=30. Total
     v3 budget cap: $10."
   - Conditional skip: "If cheap-tier debate uplift is <2pts or
     underpowered, v3 should NOT add new tiers — instead, rerun
     cheap+mid at larger n (60–100) after fixes, to reach statistical
     power before scaling up the model tier."
   - Note: Anthropic Opus ensemble remains out of scope for v3 — defer
     to v4-or-never based on v3 outcomes.

10. "Limitations" section — at minimum: n=30 statistical power;
    single corpus (MedQA only); no near-frontier-cheap (DeepSeek)
    tier; no frontier ensemble.
11. Every $ figure cites a manifest.json path.

Update docs/eval_methodology.md to document:
- The tier-matched ablation design.
- The ensemble baseline as a debate control.
- The error-mode taxonomy categories.
- The v2 → v3 → v4 optimization sequence rationale (so future
  contributors understand why each tier is scoped to its own session).

Verify:
- `grep -i 'placeholder\|TODO\|TBD' docs/results.md` returns nothing.
- "What to improve next" has ≥3 recommendations, each citing a
  diagnostic file.
- "Recommended for v3" section exists with the DeepSeek conditional
  and the explicit v3 cap of $10.

== PHASE 8 — CLAUDE.md REFRESH + FINAL SUMMARY ==

Tasks:
- Update CLAUDE.md status table: add "Headline eval v2 (tier-matched
  ablation + ensemble control)" → Complete (2026-MM-DD).
- Update "Latest results" subsection: one sentence on top-line
  finding + one sentence on top-priority next improvement (cite the
  v2 What-to-Improve-Next item).
- Add a one-line note to CLAUDE.md status table: "Headline eval v3
  (near-frontier-cheap tier + post-fix confirmation) → Planned, see
  docs/results.md §Recommended for v3."
- `git status` + `git diff --stat` summary.

== EXPLICITLY OUT OF SCOPE (this session only) ==

- DeepSeek V4-Pro tier (any cells) — v3 scope.
- Anthropic Opus frontier ensemble — v4 scope at earliest, possibly
  never (depends on v3 signal).
- `git push origin main` — requires human approval.
- Demo video recording.
- Approach C items (citation grounding, structured uncertainty).
- Re-running v1 panels at larger n.
- Newer Anthropic models (opus-4-7) — leave for v3 or later.
- Multi-corpus runs (NEJM, MCR) — single corpus this round.
- Implementing recommendations from §8 "What to improve next" — that's
  literally v3's job. Phase 7 §9 stages it.

If you find yourself proposing any of these mid-session, that's a
signal to stop and re-read the STRATEGIC CONTEXT block at the top.

== FINAL STEP ==

One-screen summary at the end:
- Per-phase status: green / yellow / red with reason.
- Total session spend ($X.XX of $30 cap).
- Files changed (grouped by phase).
- Hypothesis verdicts: H1 H2 H3 H4 H5 each → supported / not
  supported / underpowered, with effect size.
- Top three "What to improve next" items in priority order, each
  with cited diagnostic.
- v3 trigger decision: DeepSeek tier (yes / no / conditional-on-X),
  based on the conditional in Phase 7 §9.
- Branch name + commit count.
- Recommended literal one-line prompt for the next /goal session
  (e.g., "Run Quorum benchmark v3: implement fixes [A, B, C] from
  v2 §8, re-confirm cheap+mid tier results, and add DeepSeek V4-Pro
  triplet. Spend cap $10. See docs/superpowers/plans/ for full
  prompt.").

Then STOP. Do not push, do not start a new goal, do not begin v3.
