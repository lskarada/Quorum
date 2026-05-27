# Quorum — Completion Design (Approach B + C-Roadmap)

**Status:** Draft, pending review
**Author:** Lance Skarada
**Date:** 2026-05-23
**Target window:** 3–4 weeks (mid-late June 2026)
**Approach:** B — Faithful MAI-DxO reproduction + first-class single-model vs mixed-vendor comparison
**Out-of-band:** Approach C extensions deferred to `docs/roadmap.md`

---

## 1. Context

Quorum is the open-source reproduction of Microsoft's MAI-DxO (Sequential Diagnosis with Language Models, arXiv:2506.22405). The repository today has a working vertical slice: one agent (Hypothesis), single-iteration panel, SSE streaming, React frontend transcript. Four agents remain stubbed; the multi-iteration consensus loop, the eval harness, and the MCP server are not implemented.

This design specifies the completion of Approach B: every component required to (a) run a five-agent multi-iteration debate, (b) run that debate under two different panel configurations (single-model and mixed-vendor) and compare them statistically, (c) expose the panel as both a web demo and an MCP tool, and (d) score the panel against public clinical case datasets.

Decisions locked during the brainstorming session (2026-05-23):

| Decision | Choice |
|----------|--------|
| Scope | CS153 demo-ready |
| Deadline | 3–4 weeks |
| Panel model strategy | Both single-model AND mixed-vendor as configurable modes |
| Testing depth | Three-layer: unit (mocked) + integration (live LLM, opt-in) + scored eval |
| Eval corpus | Public clinical case datasets (CUPCase, MedCaseReasoning, MedQA) — no NEJM curation |
| MCP server | Ships in this build |
| Frontend polish | Multi-agent live transcript + compare-mode A/B view |
| Demo deliverable | Video script + methodology + results writeup |
| Approach C | Deferred to roadmap, with explicit "uncertainty calculation requires more research" note |

## 2. Goals

1. All five agents implement `deliberate()` against the existing structured-output contract in `orchestrator/schemas.py`.
2. The orchestrator runs a multi-iteration consensus loop with three termination conditions: top posterior > threshold, max iterations reached, or checklist agent recommends stop.
3. Panel configuration is YAML-driven so model assignments can change without code edits.
4. A comparison runner executes two named panels in parallel against the same case and the frontend renders both debates side-by-side.
5. An eval CLI runs the panel against a public corpus and produces a scored markdown report.
6. The MCP server exposes the panel as a `diagnose_case` tool callable from any MCP client.
7. The full system can be exercised end-to-end with no manual case curation, no NEJM access, and no leaderboard submission flow.

## 3. Non-goals (explicit)

- NEJM CPC transcription or CPC-Bench leaderboard submission.
- Live-LLM CI tests (opt-in manual runs only).
- Cost dashboard or observability UI (log lines are sufficient).
- `agent_token` streaming-delta SSE variant.
- Approach C extensions (citation grounding, structured uncertainty, confidence-weighted consensus).
- Frontend feature work beyond the multi-agent transcript and compare-mode view.

## 4. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Vite + React 19)                        │
│  /diagnose              Single-panel mode (existing, polished)       │
│  /compare               Compare mode (new): two panels side-by-side  │
└────────────────────┬─────────────────────────────────────────────────┘
                     │ SSE
┌────────────────────▼─────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                                   │
│  POST /api/diagnose                  single panel, sync              │
│  GET  /api/diagnose/stream           single panel, SSE               │
│  GET  /api/compare/stream            two panels, SSE multiplexed     │
│  GET  /api/panels                    list available panel configs    │
└────────────────────┬─────────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────────┐
│                    ORCHESTRATOR                                      │
│  PanelConfig (YAML loader, per-agent model assignment)               │
│  Panel.diagnose() / diagnose_stream()  single-panel multi-iter loop  │
│  ComparisonRunner.compare_stream()     parallel two-panel execution  │
└────────────────────┬─────────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────────┐
│                    AGENTS (5)                                        │
│  HypothesisAgent / TestChooserAgent / ChallengerAgent /              │
│  StewardshipAgent / ChecklistAgent                                   │
│  Each takes its model from PanelConfig at construction               │
└────────────────────┬─────────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────────┐
│                    LLM CLIENT (collapsed)                            │
│  OpenRouterClient                  one OpenAI-compatible SDK client  │
│  Reads OPENROUTER_API_KEY + OPENROUTER_BASE_URL                      │
│  Cost extracted from OpenRouter usage response                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    EVAL HARNESS (typer CLI)                          │
│  quorum eval run --corpus cupcase --panel mixed_vendor --n 100       │
│  quorum eval compare --corpus cupcase --panels A,B --n 100           │
│  quorum eval score <results_dir>                                     │
│  quorum eval report <results_dir>                                    │
│  Loaders: load_cupcase / load_medcasereasoning / load_medqa          │
│  Scorer: top-1, top-K, MRR, mean cost, McNemar, paired t-test        │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    MCP SERVER (stdio)                                │
│  diagnose_case tool wraps Panel.diagnose() with default panel        │
└──────────────────────────────────────────────────────────────────────┘
```

## 5. Components

### 5.1 LLM client — `backend/src/quorum/llm/`

**Files touched:**
- `client.py` — full rewrite of stubbed `complete()` and `stream()`. Implements OpenRouter routing via the `openai` SDK pointed at `OPENROUTER_BASE_URL`. Reads key from env. Returns `LLMResponse` with cost extracted from OpenRouter's `usage.cost` field.
- `providers/anthropic_provider.py` — becomes thin wrapper or is removed in favor of model-prefix routing through OpenRouter. Decision deferred to Phase 1 (see plan).
- `providers/openai_provider.py` — same.
- `providers/google_provider.py` — same.
- `providers/workers_ai_provider.py` — **decision 2026-05-24: struck.** Cloudflare Workers AI as a 4th provider is removed from scope. The "open panel vs closed panel" comparison arm is replaced by "single-vendor vs mixed-vendor". The provider stub may be deleted in a future cleanup pass. Cloudflare AI Gateway (the routing layer, not the inference provider) remains supported via `CLOUDFLARE_AI_GATEWAY_URL` — Phase 5 verifies routing through it for the existing three providers.

**Model name convention:** vendor-prefixed strings as OpenRouter expects. The existing `ModelName` `Literal` in `client.py` is widened to `str` to accept any OpenRouter-supported model.

**Cost tracking:** OpenRouter returns USD cost directly. No per-model pricing table is maintained in the codebase.

**Behavior on missing key:** `LLMClient.__init__` raises `RuntimeError("OPENROUTER_API_KEY not set")` if the env var is absent and the test-mode flag is false. Tests use the `AsyncMock` fixture pattern already established in `test_agents.py`.

### 5.2 Panel configuration — `backend/config/panels/*.yaml` (new directory)

**Files created:**
- `backend/config/panels/single_model_premium.yaml`
- `backend/config/panels/mixed_vendor.yaml`

**Schema:**
```yaml
name: <str>
description: <str>
max_iterations: <int>          # default 3
consensus_threshold: <float>   # default 0.6
hypothesis:    { model: <openrouter model string> }
test_chooser:  { model: <openrouter model string> }
challenger:    { model: <openrouter model string> }
stewardship:   { model: <openrouter model string> }
checklist:     { model: <openrouter model string> }
```

**Loader:** new module `backend/src/quorum/orchestrator/panel_config.py` exposes `PanelConfig.from_yaml(path)` and `PanelConfig.list_available()`. Validates every config at load time with a Pydantic model.

**Dependency:** PyYAML. Add to `backend/pyproject.toml` runtime deps (currently absent — verify before importing).

### 5.3 Five agents — `backend/src/quorum/orchestrator/agents/*.py`

**HypothesisAgent (existing, minor extension):**
- Already implements `deliberate()`. Extension: when `transcript` parameter is non-empty, prepend the prior iteration's `AgentMessage` content to the LLM messages so Hypothesis can revise based on Challenger/Checklist feedback.

**TestChooserAgent (new implementation):**
- Input: current `Differential` (top candidates) + case context.
- Output: `AgentMessage` with `structured_output = NextTest`.
- Prompt: "Given these candidate diagnoses, which test best discriminates among them? Provide name, rationale, estimated cost, and which candidates it discriminates between."

**ChallengerAgent (new implementation):**
- Input: current `Differential` (top candidate + supporting findings) + case context.
- Output: `AgentMessage` with `structured_output = {against_top_candidate: list[str], alternative_to_consider: str | "none", confidence_in_challenge: float}`.
- Prompt: "The top candidate is X. List specific findings from the case that argue AGAINST it. If a stronger alternative exists, name it. Confidence 0–1."

**StewardshipAgent (new implementation):**
- Input: `NextTest` from TestChooser + `budget_usd` from `CaseInput`.
- Output: `AgentMessage` with `structured_output = {accept_test: bool, cost_concern: str | null, cheaper_alternative: NextTest | null}`.
- Prompt: "Given budget $B and proposed test (cost $C, rationale R), is this test cost-justified? If not, propose a cheaper alternative that would still discriminate."

**ChecklistAgent (new implementation):**
- Input: full `transcript` (all prior agent messages this round).
- Output: `AgentMessage` with `structured_output = {consistent: bool, flags: list[str], recommend_continue: bool}`.
- Prompt: "Scan the transcript for internal contradictions, unsupported claims, or premature closure. Should the panel continue deliberating?"

**Prompt files:** `prompts/{test_chooser,challenger,stewardship,checklist}.md` get production content replacing the current skeletons. All five prompts follow the same template: role, inputs, output JSON schema, behavioral guidelines, few-shot example.

### 5.4 Orchestrator — `backend/src/quorum/orchestrator/panel.py`

**Multi-iteration loop replaces the current single-iteration body of `diagnose()` and `diagnose_stream()`:**

```
for iteration in range(panel_config.max_iterations):
    hyp_msg = await hypothesis.deliberate(case, transcript, iteration)
    test_msg = await test_chooser.deliberate(case, transcript + [hyp_msg], iteration)
    chal_msg = await challenger.deliberate(case, transcript + [hyp_msg, test_msg], iteration)
    stew_msg = await stewardship.deliberate(case, transcript + [hyp_msg, test_msg, chal_msg], iteration)
    chk_msg = await checklist.deliberate(case, transcript + [hyp_msg, test_msg, chal_msg, stew_msg], iteration)

    transcript.extend([hyp_msg, test_msg, chal_msg, stew_msg, chk_msg])

    top_posterior = hyp_msg.structured_output.candidates[0].posterior
    if top_posterior > config.consensus_threshold:
        termination = "consensus"; break
    if not chk_msg.structured_output["recommend_continue"]:
        termination = "checklist_stop"; break
else:
    termination = "max_iterations"
```

`diagnose_stream()` yields events at each agent step:
- `agent_start` before each agent call
- `agent_complete` after each agent call (with the structured output)
- `round_complete` after each iteration (currently unused in SSE; ships now)
- `verdict` at the end

`FinalVerdict.termination_reason` accepts a new value: `"checklist_stop"`. Schema extension required (small change to the `Literal`).

### 5.5 ComparisonRunner — `backend/src/quorum/orchestrator/comparison_runner.py` (new)

**Purpose:** run two named panels on the same case in parallel, multiplex their event streams.

**Contract:**
```python
class ComparisonRunner:
    def __init__(self, panels: list[PanelConfig], llm: LLMClient): ...

    async def compare_stream(
        self, case: CaseInput
    ) -> AsyncIterator[ComparisonEvent]:
        """Yield events from both panels, each tagged with panel_id."""
```

`ComparisonEvent` extends `StreamEvent` with a `panel_id: str` field.

**Failure isolation:** one panel raising does NOT abort the other. The failing panel emits an `error` event; the other panel continues to its `verdict`.

### 5.6 API surface — `backend/src/quorum/api/routes.py`

**New endpoints:**
- `GET /api/panels` — returns list of available panel configs (name + description).
- `GET /api/compare/stream?presentation=…&panels=A,B` — SSE stream multiplexing two panels.

**Modified:**
- `POST /api/diagnose` — accepts optional `panel: str` field (defaults to `single_model_premium`).
- `GET /api/diagnose/stream` — accepts optional `panel` query param.

### 5.7 Frontend — `frontend/src/`

**Files modified:**
- `routes/Diagnose.tsx` — extended to render multi-iteration, multi-agent transcripts. Each iteration gets a horizontal-rule divider; each agent gets a colored card.

**Files created:**
- `routes/Compare.tsx` — two-column layout, each column streams one panel's debate. Verdict-comparison summary at the bottom.
- `components/iteration-divider.tsx`
- `components/comparison-summary.tsx`
- `lib/compare-sse.ts` — SSE consumer for the multiplexed compare stream; routes events by `panel_id`.
- `lib/types.ts` — extend StreamEvent union to include `round_complete` and `panel_id`.

**Existing components reused:** `AgentCard`, `DifferentialTable`, `NextTestCard`, `ConfidenceMeter`, `CitationPanel`.

### 5.8 Eval harness — `backend/src/quorum/eval/`

**Files (full rewrite, no longer stubs):**
- `corpus.py` — loaders for the three target corpora. Each returns `Iterator[CaseInput]`.
- `runner.py` — `run_eval(panel_config, corpus, n_cases, results_dir)`. Runs panel against each case sequentially, writes one JSON per case to `data/results/<run_id>/`.
- `comparison_runner.py` — `run_comparison(panel_a, panel_b, corpus, n_cases, results_dir)`. Parallel version.
- `scorer.py` — `score_run(results_dir, corpus_name) -> dict` with top-1, top-5, MRR, mean cost, mean latency. `compare_runs(run_a, run_b)` adds McNemar's test on top-1 and paired t-test on MRR.
- `report.py` — `build_report(scores, output_path)` writes markdown.
- `cli.py` — new typer app exposing the four commands.

**CLI entry:** `[project.scripts] quorum-eval = "quorum.eval.cli:app"` in `pyproject.toml`.

**Cost guardrail:** runner reads `QUORUM_MAX_COST_USD` env var (default $20). If projected cost (cases × ~$0.10/case) exceeds it, runner refuses to start without `--confirm-cost` flag.

### 5.9 MCP server — `backend/src/quorum/mcp_server/`

**Files (full rewrite):**
- `server.py` — stdio server using `mcp.server.Server` + `mcp.server.stdio.stdio_server` per the SDK v1.0.0+ decorator pattern.
- `tools.py` — `diagnose_case` tool handler: validate arguments → `CaseInput` → `Panel.diagnose()` → return `verdict.model_dump()`.

**Default panel:** `single_model_premium`. Caller-overridable via optional `panel: str` argument.

**Verification:** local smoke test via `python -m quorum.mcp_server.server` + manual JSON-RPC over stdin.

## 6. Data flow — compare mode

```
1. User submits case via frontend /compare or curl
2. Frontend: GET /api/compare/stream?presentation=…&panels=mixed_vendor,single_model_premium
3. Backend constructs ComparisonRunner with the two PanelConfigs
4. Backend spawns two Panel.diagnose_stream() coroutines via asyncio.gather (with return_exceptions=True)
5. Each coroutine writes events to a shared asyncio.Queue, tagged with panel_id
6. Backend drains the queue and writes SSE frames; format: event: <name>, data: {"panel_id": "...", ...}
7. Frontend routes events to columns by panel_id
8. When both verdicts arrive, frontend renders ComparisonSummary with side-by-side top candidates
```

## 7. Schemas — changes

**Existing (unchanged):** `DiagnosisCandidate`, `Differential`, `NextTest`, `AgentMessage`, `CaseInput`, `Citation`, `AgentRole`.

**Extended:**
- `FinalVerdict.termination_reason` — Literal adds `"checklist_stop"`.
- `StreamEvent` — `round_complete` is already in the enum; it ships now.

**New:**
- `PanelConfig` (Pydantic): name, description, max_iterations, consensus_threshold, hypothesis, test_chooser, challenger, stewardship, checklist (each a `{model: str}` dict).
- `ComparisonEvent` (Pydantic): extends `StreamEvent` with `panel_id: str`.
- `EvalRunMetadata` (Pydantic): run_id, panel_config_name, corpus_name, n_cases, started_at, finished_at, total_cost_usd.
- `CaseScore` (Pydantic): case_id, top1_correct, topk_correct, rank_of_truth, mrr_contribution, cost_usd, latency_s.

## 8. Error model

**Closed error code set (unchanged):** `provider_429`, `provider_timeout`, `parse_failure`, `schema_violation`, `internal`.

**OpenRouter HTTP error mapping:**
- 429 → `provider_429`, retriable
- 408, 504 → `provider_timeout`, retriable
- 500, 503 → `internal`, non-retriable
- 400, 422 → `schema_violation`, non-retriable

**Retry policy:** one retry per agent per round on retriable errors. Exponential backoff: 1s, 2s. After exhaustion: error event emitted, panel emits `_error_verdict()` (existing behavior).

**Compare-mode isolation:** one panel's error does NOT abort the other. Results writeup records the failure.

## 9. Testing strategy (three-layer)

### 9.1 Unit tests (mocked, fast, no API key)

| File | Coverage |
|------|----------|
| `tests/test_agents.py` | All 5 agents with mocked LLM (extends existing) |
| `tests/test_panel.py` | Multi-iter consensus loop + all termination paths (extends existing) |
| `tests/test_panel_config.py` (new) | YAML loader, validation errors |
| `tests/test_comparison.py` (new) | Parallel execution, panel_id tagging, failure isolation |
| `tests/test_eval_scorer.py` (new) | top-1/top-K/MRR computation, McNemar, paired t-test on synthetic data |
| `tests/test_eval_corpus.py` (new) | Loader for each corpus on cached fixture files |
| `tests/test_mcp_tools.py` (new) | `diagnose_case` handler with mocked Panel |
| `tests/test_api_compare.py` (new) | `/api/compare/stream` SSE format, panel_id tagging |

**Target:** all run in <5 seconds, no network, no API key. Triggered in CI on every PR.

### 9.2 Integration tests (live OpenRouter, opt-in)

| File | Coverage |
|------|----------|
| `tests/integration/test_live_single_panel.py` | One full `Panel.diagnose()` with `single_model_premium` on a synthetic case |
| `tests/integration/test_live_mixed_vendor.py` | Same with `mixed_vendor` |
| `tests/integration/test_live_compare.py` | One `ComparisonRunner.compare_stream()` end-to-end |
| `tests/integration/test_live_mcp.py` | MCP `diagnose_case` tool over stdio |

**Trigger:** `pytest tests/integration -m live --run-live`. Requires `OPENROUTER_API_KEY` in env. Costs ~$0.10 per run.

**Frontend integration:** Vitest + React Testing Library on `Compare.tsx` with a mocked SSE stream that emits a recorded debate from `tests/fixtures/recorded_compare_stream.ndjson`.

### 9.3 Scored eval

Runs against the full target corpora. Produces `data/results/<run_id>/` containing:
- `manifest.json` — run metadata
- `case_<id>.json` — per-case verdict + score
- `summary.json` — aggregate scores
- `report.md` — human-readable report

## 10. Eval methodology

**Primary corpus:** CUPCase (Clinically Uncommon Patient Cases, arXiv:2503.06204). Used to evaluate top-1 / top-5 / MRR.

**Secondary corpus:** MedCaseReasoning (arXiv:2505.11733). Used as a second open-source case-report benchmark for cross-validation.

**Tertiary corpus:** MedQA (USMLE-style, HuggingFace). Used only if CUPCase or MedCaseReasoning prove inaccessible. Format mismatch (multiple-choice) means MedQA serves as a saturation-check rather than a primary metric.

**Run size:** 100 cases per corpus per panel for the headline numbers. 30 cases for development iteration.

**Comparison protocol:**
1. Run `mixed_vendor` panel on N cases → results A.
2. Run `single_model_premium` panel on the SAME N cases → results B.
3. Scorer computes per-case top-1 correctness for both.
4. McNemar's test on top-1 correctness; paired t-test on MRR; bootstrap 95% CI on mean cost.
5. Report renders side-by-side table + significance markers.

**Headline framing:** "Quorum reproduces MAI-DxO's architecture and evaluates on public clinical-case benchmarks. Direct numerical comparison to MAI-DxO's 85.5% on NEJM CPCs requires paywalled-corpus access and is listed as future work. We report Quorum's performance vs single-call baselines on public corpora; mixed-vendor vs single-model comparison is the headline ablation."

### Eval Corpus Verification (Phase 0, 2026-05-23)

Probed HuggingFace API for accessibility of the three candidate corpora. Results:

| Corpus | HF dataset id | Gated? | Downloads | License/format |
|--------|---------------|--------|-----------|----------------|
| CUPCase | `ofir408/CUPCase` | No | 531 | MCQ + QA tags (loader will need to extract free-text case + diagnosis fields) |
| MedQA | `bigbio/med_qa` | No | 3,529 | Multilingual EN/ZH, USMLE-style |
| MedCaseReasoning | `zou-lab/MedCaseReasoning` | No | 827 | MIT, 10k-100k size, parquet format |

All three usable for Phase 8 eval. CUPCase remains the primary (case-report format closest to NEJM CPCs); MedCaseReasoning is the strongest secondary (MIT license + explicit reasoning labels); MedQA as the fallback / saturation check.

## 11. Deliverables

| Deliverable | Path | Owner |
|-------------|------|-------|
| Working web demo (single + compare modes) | `frontend/` | This plan |
| MCP server callable from any MCP client | `backend/src/quorum/mcp_server/` | This plan |
| Eval CLI: `quorum-eval run|compare|score|report` | `backend/src/quorum/eval/` | This plan |
| Per-case results JSON + aggregate scores | `data/results/<run_id>/` | Generated |
| `docs/eval_methodology.md` updated | `docs/eval_methodology.md` | This plan |
| `docs/results.md` with headline numbers | `docs/results.md` | This plan |
| `docs/roadmap.md` with Approach C | `docs/roadmap.md` | This plan |
| `docs/demo_script.md` updated for 3–5 min video | `docs/demo_script.md` | This plan; you record |

## 12. Risk register

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| OpenRouter rate-limits during eval | Medium | Concurrency cap of 3 in eval runner; exponential backoff on 429 |
| OpenRouter cost overrun | Low | `QUORUM_MAX_COST_USD` guardrail; default $20 cap per eval run |
| CUPCase or MedCaseReasoning not actually available on HuggingFace | Medium | Phase 4 verification gate before committing to a corpus; MedQA fallback |
| Multi-iter loop hangs on a pathological case | Low | Hard timeout per agent call (60s); hard cap of `max_iterations` |
| Comparison mode runs become flaky under network noise | Medium | Failure isolation; failed panels don't abort the other; reported in results |
| Production prompts under-perform on real cases | High | Prompt iteration is a planned phase with its own gate; eval reruns are cheap once the harness exists |
| Schema drift between backend Pydantic and frontend TypeScript | Medium | `dump_schemas.py` runs in CI; frontend Vitest checks parity via existing acceptance test |
| Approach B scope exceeds 3–4 week window | Medium | Phase plan front-loads the critical path (LLM client + agents + multi-iter loop); compare-mode + eval are additive and degrade gracefully |

## 13. Acceptance criteria

The build is "done" when ALL of the following are true:

1. `cd backend && uv run pytest -q` — green, all suites pass (existing + new).
2. `cd backend && uv run pytest tests/integration -m live --run-live` — green when run manually with `OPENROUTER_API_KEY` set.
3. `cd frontend && pnpm install && pnpm lint && pnpm tsc --noEmit && pnpm vitest run && pnpm build` — green.
4. `quorum-eval run --corpus cupcase --panel single_model_premium --n 10` produces a populated `data/results/<run_id>/` with one JSON per case and a summary.
5. `quorum-eval compare --corpus cupcase --panels mixed_vendor,single_model_premium --n 10` produces a side-by-side report with both panels' scores and statistical significance markers.
6. `quorum-eval report <results_dir>` writes a `report.md` that opens correctly in a markdown viewer and includes per-case + aggregate tables.
7. The web demo at `localhost:3000/compare` renders two streaming debates side-by-side without errors when fed a real case.
8. `python -m quorum.mcp_server.server` starts an MCP stdio server; a smoke client can call `diagnose_case` and receive a `FinalVerdict` JSON response.
9. `docs/eval_methodology.md`, `docs/results.md`, `docs/roadmap.md`, `docs/demo_script.md` all updated and committed.

## 14. Roadmap (Approach C, deferred)

Persisted in `docs/roadmap.md`. Three orthogonal research extensions:

1. **Citation grounding.** Schema-enforce that each agent backs assertions with PubMed E-utility citations. Reject agent responses without supporting citations.

2. **Structured uncertainty.** Each agent reports a calibrated confidence score with its output. *Open research question: how is this uncertainty actually calculated? Options to investigate include logit-based confidence, self-consistency over multiple samples, verbalized confidence with calibration training, and ensemble-based uncertainty quantification. **More research needed before implementation.***

3. **Confidence-weighted consensus.** Aggregator weights agent opinions by their reported uncertainty rather than treating all agents as equal voters. Depends on (2) being settled first.

## 15. Glossary

| Term | Definition |
|------|------------|
| **Panel** | A configured collection of five agents with model assignments + termination params |
| **PanelConfig** | YAML file declaring per-agent model assignments and consensus thresholds |
| **Iteration / round** | One full pass through all five agents |
| **Consensus** | Top candidate's posterior exceeds `consensus_threshold` |
| **Mixed-vendor** | A panel where each agent uses a different LLM vendor |
| **Single-model** | A panel where all agents share one model |
| **OpenRouter** | OpenAI-compatible API proxy that exposes 100+ models under one API key |
| **MAI-DxO** | Microsoft's closed-source Diagnostic Orchestrator (Sequential Diagnosis with Language Models, 2025) |
| **SDBench** | The 304-case NEJM CPC benchmark used by MAI-DxO; not used here (paywalled) |
| **CUPCase** | Public open-access corpus of clinically uncommon cases used as Quorum's primary eval corpus |
