# /goal prompt — finish Quorum to demo-ready

> Paste the contents of the **`/goal` prompt** section below into a fresh
> Claude Code session in this repo. Everything else in this doc is
> reference context for humans reviewing the plan.

---

## /goal prompt

```
/goal Finish the Quorum project so it is demo-ready and optimally tuned per
docs/milestone.md and docs/demo_script.md. Implement the punch list below
autonomously, but STOP at the named human-gate checkpoints. Treat this
prompt as the contract.

== HARD STOP CONDITIONS (abort if any trip) ==

1. Cumulative LLM spend for this session exceeds $5.00 USD across all
   phases EXCEPT phase 7 (headline eval) which has its own gated cap.
   The repo already enforces QUORUM_TOTAL_SPEND_LIMIT_USD via
   ~/.quorum/spend.json — set QUORUM_MAX_COST_USD=5 in env for non-eval
   work.
2. Any verification command listed in a phase returns non-zero. Do NOT
   patch the test to make it pass. Diagnose and fix the underlying
   cause, or surface to the user.
3. Working tree drifts in ways not described by the current phase
   (untracked .py or .ts files appearing outside the phase's listed
   paths). Prior sessions have had subagents silently revert work —
   run `git status` between phases and confirm.
4. Any NotImplementedError stub re-appears in tests or source.
5. Any phase requires editing data/cases/**/*.json with synthetic
   content lacking a `"synthetic": true` field. Per CLAUDE.md rule.

== ANTI-HALLUCINATION PROTOCOL (CLAUDE.md §"Anti-hallucination") ==

- After every Write: `ls -la <path>` + `wc -l <path>` and report.
- No new dependencies beyond backend/pyproject.toml and frontend
  package.json pins. If you think you need one, STOP and ask.
- No file-structure changes outside the agreed tree.
- No confabulated citations or paper details. If WebFetch fails on a
  reference, annotate `[abstract not independently retrieved]`.
- Verify before recommending: every memory or doc claim that names a
  file/function/flag must be re-checked with grep/Read before acting.

== TDD GATE ==

For phases 2, 3, 5, 6 below: write the failing test FIRST, run it to
confirm red, THEN implement. For phase 1 (data housekeeping) and
phase 7 (eval runs), TDD does not apply — these are operations, not
code. Phase 8/9 (docs) — no tests.

== KARPATHY GUARDRAILS ==

- Surgical changes only. Don't refactor adjacent code.
- Surface assumptions before encoding them.
- Every phase ends with a runnable verification command + expected
  output. Report both.
- Premature abstraction is worse than mild repetition.

== PHASE 0 — PRE-FLIGHT ==

Tasks:
- `git status` — confirm only the two untracked dirs (data/cases/cupcase,
  data/cases/mcr) are unexpected. Anything else: STOP and ask.
- `cd backend && uv run pytest -q` — confirm green baseline (expect
  ~103 passing, 1 skipped per memory 3708).
- `cd frontend && pnpm vitest run` — confirm green.
- Confirm env: OPENROUTER_API_KEY present, CLOUDFLARE_AI_GATEWAY_URL
  presence noted (not required yet).
- Read docs/superpowers/plans/2026-05-24-quorum-finish.md (THIS file)
  in full.

Verify: both test suites green; report exit codes + pass counts.

== PHASE 1 — CORPUS HOUSEKEEPING (HUMAN GATE) ==

State: data/cases/cupcase/all.json and data/cases/mcr/all.json are
untracked. data/cases/nejm/ has only _schema.json — NEJM corpus is
empty despite docs/milestone.md naming it as headline.

AskUserQuestion three things BEFORE touching anything:

  Q1: For cupcase + mcr corpora — commit, gitignore, or move to
      external download step? Risks: license unclear without review.
  Q2: NEJM corpus is empty. Three options: (a) populate via
      scripts/download_corpus.py if NEJM source is supported, (b) keep
      empty + remove NEJM mentions from milestone/demo docs, (c) defer.
  Q3: If we populate NEJM, do you have a confirmed
      training-data-cutoff date for the eval models so we can filter
      to post-cutoff CPCs only (anti-contamination per CLAUDE.md)?

Implement per the user's answers. If commit: stage explicitly with
file paths (no `git add .`). If gitignore: update .gitignore + write
docs/eval_methodology.md section on download step.

Verify: `git status` shows clean tree (or only intentional staging);
`ls data/cases/<each>/` matches what was decided.

== PHASE 2 — COST-PRIOR CALIBRATION (TDD) ==

Goal: roadmap §4 sub-item. Each panel YAML in backend/config/panels/
gets a `cost_prior_usd` field reflecting mean cost per case on a
smoke set, so `quorum-eval run --n N` can warn pre-flight when
N × cost_prior_usd > QUORUM_MAX_COST_USD.

TDD step:
- Write backend/tests/test_cost_prior.py:
  - test_panel_config_loads_cost_prior_when_present
  - test_panel_config_cost_prior_optional_defaults_none
  - test_eval_run_warns_when_budget_exceeded_by_prior
- Run; confirm red.

Implement step:
- Add optional `cost_prior_usd: float | None = None` to PanelConfig
  (backend/src/quorum/orchestrator/panel_config.py).
- Add pre-flight warning to backend/src/quorum/eval/cli.py (`run`
  subcommand): if cost_prior set and n * cost_prior > max_cost,
  emit warning + require --force.
- DO NOT yet write the calibrated values to YAML. That happens in
  phase 7 prep (since we need premium-model runs to calibrate).
- For now: write a small `quorum-eval calibrate` subcommand that
  takes --panel + --n (default 3) and updates the YAML in place.

Verify:
- `cd backend && uv run pytest tests/test_cost_prior.py -v` — all pass.
- `cd backend && uv run quorum-eval calibrate --panel dev_cheap --n 3`
  — exits 0, dev_cheap.yaml now has cost_prior_usd field, costs <$0.05.
- `cd backend && uv run quorum-eval run --corpus medqa --panel dev_cheap --n 100`
  WITHOUT --force should now WARN (since 100 × $0.01ish > $5 default).

== PHASE 3 — FRONTEND SCHEMA CODEGEN (TDD) ==

Goal: roadmap §4 sub-item. Replace hand-mirrored frontend/src/lib/types.ts
with codegen from data/schemas/*.json.

DECISION POINT before starting: AskUserQuestion whether to use
`json-schema-to-typescript` (adds devDep, ~200kB) vs hand-rolled
generator script. Recommend json-schema-to-typescript for time.

TDD step:
- Write frontend/src/lib/__tests__/types-codegen.test.ts:
  - test_generated_types_match_pydantic_schema_round_trip
  - test_generated_types_file_is_not_hand_edited (check for a
    "DO NOT EDIT" banner in the generated file)
- Run vitest; confirm red.

Implement:
- Add backend/scripts/dump_schemas.py invocation to a frontend npm
  script: `pnpm gen:types`.
- Generate frontend/src/lib/types.generated.ts with banner.
- Update frontend/src/lib/types.ts to re-export from generated, or
  replace inline.

Verify:
- `cd backend && uv run python scripts/dump_schemas.py` then
  `cd frontend && pnpm gen:types && pnpm tsc --noEmit && pnpm vitest run`
  — all green.
- `git diff frontend/src/lib/types.ts` — show the diff to the user.

== PHASE 4 — CLOUDFLARE WORKERS AI PROVIDER (HUMAN GATE) ==

CLAUDE.md describes a 4th provider (Cloudflare Workers AI) for the
"open panel vs closed panel" eval arm. No code references it.

AskUserQuestion:
  Q: Implement Cloudflare Workers AI as a 4th provider now, or strike
     it from CLAUDE.md and CLAUDE-vision until later?
  Context: Implementation = HTTP-only via httpx (no new dep), but
  adds eval scope. Striking = remove from docs and the eval
  comparison arm narrows to "single-vendor vs mixed-vendor".

If IMPLEMENT (TDD):
- Write backend/tests/test_llm_client_cloudflare.py:
  - test_cloudflare_provider_dispatches_to_workers_ai_endpoint
  - test_cloudflare_provider_respects_ai_gateway_url
  - test_cloudflare_response_json_normalization
  Use httpx_mock or respx.
- Run; confirm red.
- Extend backend/src/quorum/llm/client.py with a Cloudflare branch.
- Add a backend/config/panels/open_vs_closed.yaml referencing it.

If STRIKE:
- Remove the Cloudflare section from CLAUDE.md.
- Note the decision in docs/superpowers/specs/2026-05-23-quorum-completion-design.md.

Verify: pytest green (if implement) OR `grep -ri cloudflare CLAUDE.md`
returns nothing (if strike).

== PHASE 5 — AI GATEWAY ENV WIRING VERIFICATION (TDD) ==

Goal: confirm that CLOUDFLARE_AI_GATEWAY_URL, when set, routes ALL
four (or three, depending on phase 4) providers through it. The
docs claim this; verify with code.

TDD step:
- Write backend/tests/test_llm_client_gateway.py:
  - test_anthropic_calls_route_through_gateway_when_set
  - test_openai_calls_route_through_gateway_when_set
  - test_google_calls_route_through_gateway_when_set
  - test_gateway_url_absent_falls_back_to_native_endpoints
- Run; confirm red on any provider not yet wired.

Implement: fix LLMClient init/dispatch for each provider that isn't
already gateway-aware.

Verify: pytest green; show diff of llm/client.py.

== PHASE 6 — PROMPT ITERATION (TDD-ADJACENT, MANUAL EVAL) ==

Goal: tune each of the 5 agent prompts using
backend/scripts/prompt_iteration_eval.py against a held-out subset.

IMPORTANT — this is the highest-leverage step for accuracy.

Process (per agent, sequentially):
- Select 5–10 cases from the MedQA corpus as a HELD-OUT prompt-tuning
  set. Mark these in a new file backend/tests/fixtures/prompt_tuning_holdout.json
  so the headline eval (phase 7) can exclude them. CRITICAL: do not
  let the held-out tuning set leak into the eval n.
- For each agent (Hypothesis → TestChooser → Challenger →
  Stewardship → Checklist):
  - Baseline: run current prompt on holdout, record accuracy +
    cost in data/results/prompt_tuning/<agent>_baseline_<ts>/.
  - Propose 1–2 prompt variants (small, surgical — don't rewrite
    the prompt wholesale). Document the hypothesis behind each
    variant in a comment header in the prompt file.
  - Run each variant on holdout. Record.
  - Pick the winner by (accuracy_delta - 0.5 * cost_delta_pct).
    Tie-break by lower cost.
  - Commit the winner with a message that includes the holdout
    accuracy delta.

HARD CAP: $1.50 total spend across phase 6. Abort if approaching.

Verify per agent: `cd backend && uv run python scripts/prompt_iteration_eval.py
--agent <name> --cases <holdout>` shows the winning variant's
accuracy >= baseline.

== PHASE 7 — HEADLINE EVAL (HUMAN GATE) ==

This is the EXPENSIVE step. STOP before running and confirm with user.

Pre-flight:
- Run `quorum-eval run --corpus medqa --panel dev_cheap --n 3
  --dry-run` (you may need to add --dry-run; if not present, skip).
- Compute expected cost: n=100, three panels (single_model_premium,
  mixed_vendor, baseline_single_call), 2 corpora (medqa + nejm if
  populated in phase 1). Use phase 2 cost priors.
- AskUserQuestion the user to confirm the expected total $ and
  approve. Default proposal: n=100 medqa for the three premium
  configs only ≈ $X (compute X from priors).

If approved:
- export QUORUM_MAX_COST_USD=<approved cap>
- Run each combo:
  `quorum-eval run --corpus <c> --panel <p> --n 100`
  `quorum-eval score <results_dir> --corpus <c>`
  `quorum-eval report <results_dir> --corpus <c>`
- HOLDOUT EXCLUSION: pass the prompt-tuning holdout case IDs via
  --exclude flag (add if missing — surgical, single-line change to
  corpus loader).
- Stream `tail -f ~/.quorum/spend.json` between runs; if approaching
  cap, STOP.

Verify per run: results_dir/manifest.json exists, scorer printed
McNemar p-value + Wilcoxon for cost, report.md rendered.

== PHASE 8 — RESULTS WRITE-UP ==

Tasks:
- Create docs/results.md with the eval numbers table. Pull metrics
  from scorer output. NO confabulation — every number is sourced
  from a results_dir.
- Add an "Eval methodology" link back to docs/eval_methodology.md.
- Update docs/demo_script.md lines 2:30–3:30 to reference real
  numbers in docs/results.md (delete the "placeholder" hedge).

Verify: `grep -i placeholder docs/demo_script.md` returns nothing.

== PHASE 9 — STATUS TABLE + CLAUDE.md REFRESH ==

Tasks:
- Update CLAUDE.md status table: "Headline eval with premium panels"
  → Complete (with date). Demo video stays "Not started".
- Add a "Latest results" subsection to CLAUDE.md pointing at
  docs/results.md.
- Bump the "## Status" section accuracy if anything is now stale.

Verify: `grep -c "Pending" CLAUDE.md` shows reduction; `git diff
CLAUDE.md` reviewed.

== EXPLICITLY OUT OF SCOPE FOR THIS GOAL ==

- Recording the demo video (item 4 of the original punch list).
  Requires human in front of a screen.
- `git push origin main` of the 32 commits. Requires human approval
  per session-guidance ("Actions visible to others"). Surface a
  final summary and ask.
- Approach C roadmap items (citation grounding, structured
  uncertainty, confidence-weighted consensus, structured JSON
  logging). These are documented as future work.

== FINAL STEP ==

At the end of all phases, produce a one-screen summary:
- Per-phase status: green / yellow (with reason) / red (with reason).
- Total session spend.
- Files changed (grouped by phase).
- Outstanding items requiring human action (push, video, any
  AskUserQuestion the user deferred).
- One-line recommendation for what to do next.

Then STOP. Do not push, do not record video, do not start a new goal.
```

---

## Why the prompt is structured this way

- **Hard stops first.** Prior sessions have had subagents silently revert work (memory 3723, 3728). The `git status` between phases + the spend cap protect against runaway.
- **TDD on code phases only.** Phases 1, 7, 8, 9 are operations or docs — TDD doesn't apply and forcing it wastes tokens.
- **Human gates on the three irreversible decisions.** Corpus licensing, Cloudflare scope, and headline-eval $ — none of these should be made by a model.
- **Prompt iteration (phase 6) is the highest-leverage accuracy step.** It's also the easiest to do badly: the prompt warns to use a held-out set so the headline eval doesn't leak.
- **Holdout exclusion is explicit.** Without it, phase 7 numbers would be optimistic on the cases used to tune the prompts in phase 6.
- **Out-of-scope list is named.** Demo video and `git push` are not a model's job; calling that out prevents an over-eager session from doing them anyway.

## How to use this

```bash
cat docs/superpowers/plans/2026-05-24-quorum-finish.md | pbcopy
# paste the /goal prompt block into a fresh session
```

Or invoke directly:
```
/goal <paste the /goal prompt section>
```
