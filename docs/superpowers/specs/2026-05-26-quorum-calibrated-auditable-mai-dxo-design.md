# Quorum Calibrated-Auditable MAI-DxO Pivot — Design Spec

**Date**: 2026-05-26
**Status**: Approved for implementation
**Owner**: Lance Skarada (CS153 Spring 2026 solo build)
**Prior context**: See `2026-05-23-quorum-completion-design.md` for the pre-pivot Approach-B design.

---

## 1. Strategic context (why this exists)

Quorum's current headline evaluation (MedQA n=30) shows the 5-agent panel *losing* to a single Claude Opus baseline (16.7% vs 26.7% top-1). The architecture has no place to shine on multiple-choice USMLE because debate, calibration, and stewardship don't matter when there's a deterministic right answer the model already knows.

The pivot: shift the headline eval to **a SDBench-flavored, cost-aware, sequential diagnostic encounter**, where 5-agent deliberation, calibrated uncertainty, and auditable reasoning are the structural advantages that justify the system's existence. This is the "narrow eval, exceptional pipeline" play applied to medicine.

### Positioning (one sentence)

> *Quorum is the open-source, MCP-exposed, calibrated, and audit-traceable reference implementation of cost-aware sequential diagnostic deliberation — the architectural shape Microsoft's MAI-DxO published in June 2025, but with honest probabilities, full reasoning trails, and a deterministic safety layer that no public competitor has owned.*

### What is *not* the goal

- Beating MAI-DxO + o3 on raw accuracy on SDBench (Microsoft's published 85.5% is the literature reference; we don't need to exceed it).
- Inventing a novel multi-agent architecture (we use the 5 agents already in place).
- Achieving SOTA on rare-disease benchmarks (DeepRare, RareAgents, Hygieia have done this).
- Generalizing across all medical AI tasks.

### What *is* the goal

1. **Reproduce a SDBench-flavored evaluation harness** on a publicly documented corpus.
2. **Build the Gatekeeper module** (turn-based information-reveal game).
3. **Add a Calibration layer** that scores panel posteriors with Brier score and ECE.
4. **Add an Audit Trail layer** that logs every agent message, query, and decision for downstream review.
5. **Run a clean three-arm headline evaluation**:
   - **Arm A** (Quorum-Calibrated, full system on Sonnet 4.6 with extended thinking)
   - **Arm B** (single Sonnet 4.6, no orchestration — the floor)
   - **Reference** (MAI-DxO + o3 = 85% accuracy / physicians = 20%, cited from Microsoft's paper)
6. **Report** accuracy, calibration (Brier/ECE), audit completeness, and cost per case as the headline metrics.
7. **Ship as MIT-licensed public GitHub repo** with reproducible methodology and full case-list disclosure.

---

## 2. Hard constraints

| Constraint | Value |
|---|---|
| Budget ceiling | $80 total Anthropic API spend; target $50-65; currently $5.21 of $30 v2 cap consumed |
| Time budget | 7-10 working days for build + 1-2 days for write-up |
| Model | Claude Sonnet 4.6 with extended thinking (all 5 agents) |
| No new runtime dependencies | Beyond pinned list in `backend/pyproject.toml` (must add PyYAML if absent; Anthropic SDK already there) |
| Corpus | n=35 case mix: 20 NEJM CPC (via Stanford library) + 10 MedCaseReasoning + 5 RareBench (already pulled) |
| TUNE/EVAL split | 5 TUNE / 30 EVAL, held out, run once |
| Repo state by submission | Public on GitHub, MIT-licensed, prompts checked in, eval case-list (citations) public |
| Architectural contract | 5 agents (Hypothesis / TestChooser / Challenger / Stewardship / Checklist) — no new agent classes |

---

## 3. Corpus (already built — see `data/cases/eval_corpus_v2/`)

**Total: 35 cases**
- 20 NEJM CPC cases (Sep 2025 – May 2026), `nejm_sample.json` — segmented into `initial_presentation`, `available_findings`, `hidden_discussant_differential`, `ground_truth_diagnosis`
- 10 MedCaseReasoning cases (Stanford zou-lab, MIT-licensed), `mcr_sample.json` — case_id, presentation, ground_truth_diagnosis, reasoning_trace
- 5 RareBench LIRICAL cases (Apache 2.0), `rarebench_sample.json` — HPO codes translated to phenotype names + OMIM/Orphanet codes resolved to disease names

**Topic distribution**: ID 7, cardio 5, heme-onc 6, rheum 4, endo 3, neuro-sleep 3, GI 2, peds 3, renal 4 (cases hit multiple specialties).

**TUNE/EVAL split**: deterministic seed (20260526). 5 TUNE cases for prompt iteration, 30 EVAL cases held out. Split will be recorded in `data/cases/eval_corpus_v2/splits.json` at build time. EVAL set run ONCE for the headline number; no peeking.

---

## 4. System architecture

```
┌────────────────────────────────────────────────────────────────┐
│                       Quorum-Calibrated                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐   │
│  │  Gatekeeper  │────│  Orchestrator   │────│  AuditTrail  │   │
│  │   (NEW)      │    │  (extended)     │    │   (NEW)      │   │
│  └──────────────┘    └────────┬────────┘    └──────────────┘   │
│                               │                                │
│        ┌──────────────────────┼───────────────────────┐        │
│        │                      │                       │        │
│   ┌────▼────┐  ┌──────────┐  ┌▼─────────┐ ┌─────────┐ ┌▼──────┐│
│   │Hypothesis│  │TestChooser│  │Challenger│ │Steward.│ │Checkl.││
│   └──────────┘  └──────────┘  └──────────┘ └────────┘ └───────┘│
│                                                                │
│  ┌────────────────────────────────────────────────────────────┐│
│  │            Calibration & Scoring (NEW)                     ││
│  │   Brier score / ECE on panel posterior over Dx shortlist   ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 4.1 New modules to build

**A. Gatekeeper** (`backend/src/quorum/gatekeeper/`):
- Holds the full case (`available_findings`, ground truth hidden).
- Receives agent queries ("what's the WBC?", "order CT chest with contrast").
- Matches queries against the `available_findings` array using fuzzy semantic match (LLM-as-matcher with Sonnet 4.6).
- Returns the matched finding or "not available" if no match.
- Maintains a simulated cost ledger: each query increments cost based on a published test-cost table (CMS allowable charges or similar).
- Hard limits: max 30 turns per case, max simulated cost $5,000 per case (cuts off agentic loops).

**B. AuditTrail** (`backend/src/quorum/audit/`):
- Pydantic schema: `TurnRecord` with fields `turn_index`, `timestamp`, `agent`, `message_role` (in/out), `content`, `tokens`, `cost_usd`, `posterior_at_turn` (Dict[Dx, prob]), `query_or_decision`.
- Writes JSONL to `data/results/<run_id>/<case_id>.audit.jsonl`.
- Schema versioned (v1) for downstream stability.

**C. Calibration** (`backend/src/quorum/calibration/`):
- Extracts panel posterior at each turn (the Hypothesis agent already emits per-Dx probabilities per existing schema).
- At commit time, computes Brier score against ground truth.
- Across the EVAL set, computes ECE (expected calibration error) using 10-bin reliability diagram.
- Reports Brier and ECE alongside accuracy in the final results JSON.

### 4.2 Existing modules to extend

**Panel orchestrator** (`backend/src/quorum/orchestrator/panel.py`):
- Add a new mode: `sequential_diagnosis` (alongside the existing `multi_iter_consensus` mode).
- In sequential mode, panel deliberation produces *queries* to the Gatekeeper for the first N-1 turns, then a final committed diagnosis on the last turn.
- Termination: top_posterior > threshold (0.7 default) OR turn ≥ max_turns OR Stewardship votes stop (cost-benefit threshold reached).

**Per-agent prompts** (`backend/src/quorum/orchestrator/prompts/*.md`):
- Tune for sequential workflow: Hypothesis maintains shortlist + posterior, TestChooser proposes 1-2 next queries with rationale, Challenger asks "what diagnoses haven't we considered yet given the latest finding?", Stewardship votes on whether next-best test is cost-justified, Checklist enforces safety rules (no committing without ≥3 findings; no committing on incoherent posterior).

**LLMClient** (`backend/src/quorum/llm/llm_client.py`):
- Verify: Sonnet 4.6 with extended thinking enabled; Anthropic prompt caching on; Batch API supported for eval mode (50% cost reduction). All likely already in place per CLAUDE.md but smoke-test.

### 4.3 Deterministic safety layer (the audit moat)

A small rule-engine that enforces invariants and fires before the panel commits:
1. Panel cannot commit without at least 3 queried findings.
2. Panel cannot commit if Checklist agent flagged ≥1 active safety concern.
3. Panel cannot commit a diagnosis not in the current Hypothesis shortlist.
4. Simulated cost > $5,000 forces a commit with current shortlist.
5. Disagreement between Hypothesis top-1 and Challenger top-1 > 30 pp triggers an extra deliberation turn.

These are *hard rules* checked by Python code, not by an LLM. That's what makes them deterministic and audit-able.

---

## 5. Evaluation methodology

### 5.1 Three-arm design

**Arm A — Quorum-Calibrated** (the main artifact):
- Sonnet 4.6 + extended thinking, all 5 agents, full Gatekeeper game, audit trail, calibrated posteriors, deterministic safety layer.
- Metrics: top-1 accuracy, top-3 accuracy, Brier score, ECE, audit-completeness rate, mean cost per case ($).

**Arm B — Single Sonnet 4.6** (the floor):
- One Sonnet 4.6 call per case, given the same `initial_presentation`, asked to produce a final diagnosis directly (no Gatekeeper, no panel).
- Quantifies the lift the orchestrator + Gatekeeper provides.

**Literature reference** (no run):
- MAI-DxO + o3 = 85.5% (Microsoft, n=304)
- Physicians = 20% (Microsoft)
- Single Sonnet 3.5 (Claude 3.5 Sonnet) = 33.4% on RareBench (DeepRare paper comparison) — gives a single-model expectation in similar disease space.

### 5.2 Scoring

**Diagnostic accuracy**: LLM-as-judge using Claude Opus 4.7 (or Sonnet 4.6 if budget-constrained). For each case, judge sees: `ground_truth_diagnosis`, `acceptable_partial_credit` list, and the system's committed diagnosis. Judge outputs `full_credit / partial_credit / no_credit` with a one-sentence rationale.

**Calibration**: Brier score per-case; ECE across the EVAL set (10-bin equal-frequency).

**Audit completeness** (custom metric): for each case, a structured checklist: (a) every agent's contribution logged; (b) every Gatekeeper query and response logged; (c) every safety-rule check logged with outcome; (d) final posterior at commit logged. Score = fraction of items satisfied.

**Cost**: simulated dollars (Gatekeeper test-cost ledger) AND real dollars (Anthropic API spend). Report both.

### 5.3 TUNE/EVAL discipline

1. Day 1: write `data/cases/eval_corpus_v2/splits.json` with the 5 TUNE / 30 EVAL split (deterministic seed 20260526). Commit to git. Never modify.
2. All prompt iteration uses only TUNE cases. Re-run freely.
3. EVAL is run **once**, near the end of the build, after all prompt freeze. The number reported is the number on EVAL.
4. If the EVAL run reveals a bug (not a prompt issue), the bug is fixed and EVAL is re-run — but this is disclosed in the writeup as "EVAL re-run after [bug X]".

---

## 6. Budget breakdown

Per-case estimate (Sonnet 4.6, extended thinking, prompt caching, multi-turn sequential):
- Without caching: ~$1.35/case
- With caching (~60% effective): ~$0.80/case
- With caching + Batch API (50% off): ~$0.40/case

| Phase | n_cases | Mode | Cost |
|---|---|---|---|
| Prompt tuning iterations | 5 TUNE × ~10 iters | Sonnet, caching | ~$20 |
| Headline EVAL run (Arm A) | 30 | Sonnet, caching + batch | ~$15 |
| Single-model baseline (Arm B) | 30 | Sonnet, single call | ~$5 |
| LLM-as-judge scoring | 30 × ~3 calls/judge | Opus 4.7 (or Sonnet) | ~$5 |
| Debugging buffer | — | — | ~$10 |
| **Subtotal in $50 plan** | | | **~$55** |
| Optional: Opus 4.7 mini-arm | 10 cases | Opus | +$15 |
| Optional: confirmation EVAL re-run | 30 | Sonnet | +$15 |

**Hard ceiling**: $80 total. Current spend $5.21, so $75 headroom.

---

## 7. Implementation phases

### Phase 0 — Repo hygiene (Day 0, 1-2 hours)

- Confirm Stanford NEJM library access (one CPC pulled — done with Case 14-2026 sample + 20 others provided by user).
- Confirm Anthropic billing state: bump cap to $80 if needed; prompt caching + Batch API enabled.
- Confirm GitHub repo can be public by demo time.
- Verify `data/cases/eval_corpus_v2/` corpus is complete (35 cases). ✅ Done.

### Phase 1 — Splits + smoke tests (Day 1, 4 hours)

1. Write `scripts/build_eval_splits.py` to emit `data/cases/eval_corpus_v2/splits.json` (5 TUNE / 30 EVAL with seed 20260526). Commit.
2. Write `scripts/load_eval_corpus.py` helper that loads all 35 cases into a single `EvalCase` Pydantic model, regardless of source corpus.
3. Smoke-test the existing `quorum-eval` CLI against one TUNE case using the existing panel mode.
4. Pin all panel YAML configs for the v2 benchmark; commit.

### Phase 2 — Gatekeeper module (Days 1-2, 8 hours)

1. Define `Gatekeeper` class in `backend/src/quorum/gatekeeper/gatekeeper.py`.
2. Implement `query(question: str) -> Optional[Finding]` using Sonnet 4.6 as a semantic matcher against the case's `available_findings` array. System prompt: "You are a clinical gatekeeper. Match the question to one of these findings or say 'not_available'."
3. Implement the cost ledger: hard-coded test-cost table from CMS allowable schedule for common tests (CBC = $11, CT chest = $200, etc.) in `gatekeeper/test_costs.yaml`. Out-of-table queries cost $0 by default.
4. Hard limits: 30 turns, $5,000 simulated cost.
5. Unit tests for Gatekeeper: known query → known finding match; out-of-scope query → not_available; cost accumulates correctly.

### Phase 3 — Audit Trail module (Day 2, 4 hours)

1. Define `TurnRecord` and `CaseAudit` Pydantic schemas in `backend/src/quorum/audit/schemas.py`.
2. Implement `AuditWriter` that streams JSONL to `data/results/<run_id>/<case_id>.audit.jsonl`.
3. Hook every agent invocation, Gatekeeper query, and safety-rule check.
4. Unit tests: spy-pattern test that verifies the audit catches all expected events.

### Phase 4 — Calibration module (Day 3, 4 hours)

1. Extend Hypothesis agent's output schema (`schemas.py`) to require `posterior_over_shortlist` as a `Dict[str, float]` that sums to 1.0.
2. Implement `compute_brier(posterior, ground_truth_label) -> float` and `compute_ece(posteriors_list, ground_truths_list, n_bins=10) -> float`.
3. Hook into AuditTrail so per-turn posteriors are captured.
4. Unit tests with hand-rolled posteriors and known Brier/ECE values.

### Phase 5 — Sequential Diagnosis orchestrator mode (Days 3-4, 8 hours)

1. Add `mode: sequential_diagnosis` to `PanelConfig` YAML.
2. Implement `panel.run_sequential(case, gatekeeper, audit_writer)` in `backend/src/quorum/orchestrator/panel.py`.
3. Termination logic: top_posterior > 0.7 OR turn ≥ 30 OR Stewardship votes stop OR cost > $5,000.
4. Deterministic safety layer: implement the 5 hard rules from §4.3 as a `SafetyChecker` class.
5. Integration tests on TUNE cases.

### Phase 6 — Per-agent prompt tuning (Days 4-5, 12 hours)

1. Iterate on each of the 5 agent prompts using the 5 TUNE cases. Each iteration:
   - Run Quorum-Calibrated on TUNE cases.
   - Inspect audit trails for failure modes (premature commits, weak Challenger probes, etc.).
   - Adjust prompts (one agent at a time, isolate effects).
   - Re-run.
2. Budget: ~10 iterations × 5 cases × $0.40 = ~$20.
3. Freeze prompts at end of Day 5. No further changes until after EVAL.

### Phase 7 — Headline EVAL run (Day 6, 3 hours real time + ~30 min compute)

1. Confirm prompts and code are frozen via git tag `v2-eval-frozen`.
2. Run Arm A (Quorum-Calibrated) on all 30 EVAL cases via Batch API.
3. Run Arm B (Single Sonnet 4.6) on the same 30 EVAL cases.
4. Run LLM-as-judge over both arms.
5. Compute metrics: top-1, top-3, Brier, ECE, audit-completeness, mean cost.
6. Write results to `docs/results_v2.md`.

### Phase 8 — Optional Opus arm (Day 6 evening, if budget allows)

1. Run Quorum-Calibrated with Opus 4.7 on 10 EVAL cases.
2. Compare to the Sonnet 4.6 results: is the architecture lifting accuracy on a stronger base model, or is it model-saturating?

### Phase 9 — Write-up + demo prep (Days 7-9)

1. Update `docs/results.md` with v2 headline numbers.
2. Write `docs/eval_methodology.md` v2 section: corpus, TUNE/EVAL discipline, three-arm design, judge methodology.
3. Update `README.md` with the new positioning and v2 headline.
4. Record demo video showing: case loads, panel deliberates, Gatekeeper queried, posterior evolves, commit, audit trail rendered.
5. Push to GitHub, set repo public, tag `v2.0`.

### Phase 10 — Stretch / fallback (Days 9-10)

- If everything went well: run a confirmation EVAL on Sonnet 4.6 to bound variance.
- If something failed: triage and fix; re-run only the affected arm.
- Optional: write a short blog post.

---

## 8. Acceptance criteria (the demo bar)

The project is considered shipped when ALL of these are true:

1. ✅ Corpus at `data/cases/eval_corpus_v2/` with 35 cases, README, splits.json.
2. ✅ Gatekeeper module passes its unit tests.
3. ✅ AuditTrail module passes its unit tests; sample audit JSONL is human-readable.
4. ✅ Calibration module computes Brier and ECE correctly against hand-rolled test fixtures.
5. ✅ Sequential Diagnosis mode runs end-to-end on at least one TUNE case from initial presentation through commit.
6. ✅ Deterministic safety layer demonstrably prevents at least one premature commit in TUNE.
7. ✅ Arm A (Quorum-Calibrated) achieves ≥ Arm B (single Sonnet 4.6) on top-1 accuracy. (If not, that's a real finding — write it up honestly; the architecture isn't helping on this corpus.)
8. ✅ Arm A reports a Brier score and ECE that the single-model arm cannot (because single-model arm doesn't expose posteriors).
9. ✅ Audit completeness rate ≥ 95% on Arm A.
10. ✅ Total real API spend ≤ $80.
11. ✅ GitHub repo public, MIT-licensed, with full documentation and demo video.
12. ✅ CS153 deliverable submitted.

**Stretch goals** (nice to have, not blocking):
- Top-1 accuracy within 15pp of MAI-DxO + o3 published number (85%, so target ≥70%).
- ECE ≤ 0.15 on EVAL set.
- One peer or instructor can clone the repo and reproduce Arm B (single-model baseline) in <30 minutes.

---

## 9. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Budget overrun (>$80) | Medium | Hard cap in code via `MAX_SPEND_USD` env var; abort batch if reached |
| EVAL accuracy below single-model baseline | Medium | If observed, write up as honest finding; check whether Gatekeeper match quality is poor; consider tightening the Hypothesis prompt |
| Gatekeeper false-matches findings to wrong queries | Medium | Use Sonnet 4.6 + few-shot examples in matcher prompt; log all matches in audit; spot-check during TUNE |
| Prompt overfitting to TUNE | Low | TUNE is only 5 cases; if prompts feel overfit, run on additional MCR cases (we have 200 in `data/cases/mcr/all.json` outside the EVAL set) |
| Anthropic API outage on EVAL day | Low | Use Batch API which is resilient to transient outages; retry logic with exponential backoff |
| Stanford NEJM access revoked | Low | We've already pulled the 20 NEJM cases into the corpus; no further pulls needed |

---

## 10. What the LLM-judge prompt looks like (concrete)

```
You are evaluating whether a diagnostic AI's final committed diagnosis matches
the ground truth from a published clinical case. You will be given:

- GROUND_TRUTH: the published final diagnosis from the NEJM Case Records.
- ACCEPTABLE_PARTIAL_CREDIT: a list of diagnoses that partially match.
- AI_COMMITTED: what the AI committed to.

Score one of three:
- "full_credit": AI committed to the GROUND_TRUTH, or a synonymous/equivalent
  rephrasing (e.g., "Henoch-Schönlein purpura" == "IgA vasculitis").
- "partial_credit": AI committed to one of ACCEPTABLE_PARTIAL_CREDIT entries,
  or to a diagnosis that captures the disease category but misses specifics.
- "no_credit": AI committed to something not in either list.

Provide a one-sentence rationale.

Respond as strict JSON: {"score": ..., "rationale": "..."}
```

---

## 11. Repo layout (for the LLM/human implementer)

```
backend/src/quorum/
├── gatekeeper/                  [NEW]
│   ├── __init__.py
│   ├── gatekeeper.py            # Gatekeeper class
│   ├── test_costs.yaml          # CMS-style cost table
│   └── tests/
├── audit/                       [NEW]
│   ├── __init__.py
│   ├── schemas.py               # TurnRecord, CaseAudit
│   ├── writer.py                # AuditWriter (streams JSONL)
│   └── tests/
├── calibration/                 [NEW]
│   ├── __init__.py
│   ├── metrics.py               # Brier, ECE
│   └── tests/
├── orchestrator/
│   ├── panel.py                 # EXTEND with sequential_diagnosis mode
│   ├── safety.py                # [NEW] deterministic safety rules
│   └── prompts/                 # TUNE these
├── eval/
│   ├── runner.py                # EXTEND for new mode
│   ├── judge.py                 # [NEW] LLM-as-judge
│   └── ...

backend/scripts/
├── build_eval_splits.py         [NEW]
├── load_eval_corpus.py          [NEW]
└── run_v2_benchmark.py          [NEW]

backend/config/panels/
├── v2_quorum_calibrated.yaml    [NEW] Arm A
├── v2_single_sonnet.yaml        [NEW] Arm B
└── (existing panels preserved for v1 sanity)

data/cases/eval_corpus_v2/
├── mcr_sample.json              ✅ done
├── rarebench_sample.json        ✅ done
├── nejm_sample.json             ✅ done (20 cases)
├── README.md                    ✅ done (will update for nejm count)
└── splits.json                  [Phase 1, day 1]

data/results/                    (gitignored except .gitkeep)
└── v2_<run_id>/
    ├── arm_a/
    │   ├── <case_id>.audit.jsonl
    │   └── ...
    ├── arm_b/
    └── summary.json

docs/
├── results.md                   ✅ exists; v2 section to be added
├── results_v2.md                [Phase 9]
├── eval_methodology.md          ✅ exists; v2 section to be added
└── superpowers/specs/
    └── 2026-05-26-quorum-calibrated-auditable-mai-dxo-design.md   (this file)
```

---

## 12. Out of scope (explicitly)

- Image / radiology reasoning (Microsoft excluded these from SDBench, so do we).
- Tool-use beyond Gatekeeper (no real EHR integration, no Orphanet/OMIM retrieval — that's a v3 feature).
- Patient-facing UI (the existing /compare frontend stays as-is for v1; new v2 results are reported via JSON + markdown).
- Genetic data ingestion (Hygieia and DeepRare have this; we don't).
- Real-time data export beyond saved JSONL audit logs.
- Multi-language support (English NEJM corpus only).

---

## 13. Open questions for the implementer

These are choices the implementer (human or `/goal` agent) may need to make during the build. Defaults are provided; if defaults change, document why.

1. **Initial reveal scope**: how much of `initial_presentation` does Turn 0 reveal? **Default**: entire `initial_presentation` field. Alternative: only first paragraph (harder, more SDBench-faithful).
2. **Max turns**: hard limit on panel turns per case. **Default**: 30.
3. **Max simulated cost**: hard cost limit per case. **Default**: $5,000.
4. **Commit threshold**: posterior threshold above which panel may commit. **Default**: 0.7.
5. **Judge model**: Opus 4.7 or Sonnet 4.6 for LLM-as-judge? **Default**: Opus 4.7 (better judgment quality); fallback to Sonnet 4.6 if budget pressured.
6. **Caching strategy**: explicit `cache_control` markers on which parts of the prompt? **Default**: cache `initial_presentation` and `available_findings` (the case payload) for the entire case duration; uncache only the conversation turn delta.
7. **Number of TUNE iterations**: how many prompt-tuning iterations on TUNE before freezing? **Default**: 10 max; freeze sooner if accuracy plateaus.
8. **Batch API**: use Batch API for EVAL run? **Default**: yes (50% cost reduction). Falls back to streaming API only if Batch is unavailable.

---

## 14. References

- Microsoft "Sequential Diagnosis with Language Models" (arxiv 2506.22405)
- DeepRare (Nature 2025): an agentic system for rare disease diagnosis
- RareAgents (arxiv 2412.12475)
- Hygieia (arxiv 2605.06226, May 7 2026)
- Open-MAI-Dx-Orchestrator (github.com/The-Swarm-Corporation): existing open-source MAI-DxO reimpl — Quorum positions adjacent to this (calibration + audit emphasis they lack)
- MedCoAct (arxiv 2510.10461) — confidence-aware multi-agent framework
- MACO v2.2 (r/softwarearchitecture, May 6 2026) — community deterministic-safety multi-agent
- CLAUDE.md (this repo's working contract)
- `docs/superpowers/specs/2026-05-23-quorum-completion-design.md` (prior Approach-B build)
