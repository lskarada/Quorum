# Quorum v3 — NEJM-CPC Accuracy-Maximization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This plan feeds an autonomous `/goal` session.

**Goal:** Push the Quorum Sonnet panel's **NEJM-CPC** top-1 accuracy as close as possible to MAI-DxO's published Claude-Sonnet result (**0.819** full+partial on NEJM-CPC), on a **decontaminated, frozen holdout**, within a **$100 incremental budget** ($200 hard cap), dropping MCR + RareBench from the headline benchmark.

**Architecture:** Keep the 5-agent Sonnet panel (Hypothesis / TestChooser / Challenger / Stewardship / Checklist). Add accuracy via three evidence-ranked layers: (1) **test-time compute** — self-consistency over k panel runs + retrieved few-shot CoT; (2) **scaffolding quality** — stronger Bayesian Hypothesis, disconfirming-test Challenger, info-value TestChooser, chain-length control; (3) **diversity/reasoning** — extended thinking + persona divergence, only if budget remains. All tuning happens on a grown NEJM DEV set; the holdout is run **once**.

**Tech Stack:** Python 3.11, `uv`, pytest, anthropic via OpenRouter, Sonnet 4.6 only. No new runtime deps. No new agent classes.

**Hard constraints (inherited from `.claude/rules/v2-benchmark.md`, still binding):**
- Sonnet 4.6 only for the 5 agents (Opus 4.7 only as an optional stretch mini-arm, and the MAI-DxO data shows Opus 4.1 *underperformed* Sonnet 4.5 when orchestrated — 78.0 vs 81.9 — so deprioritize it).
- No new runtime dependencies. No new agent classes.
- Spend hard stop **$200** (`backend/scripts/spend_gate.sh`, raised from $142 by user approval 2026-05-30). Log every run with `bash backend/scripts/log_spend.sh AMOUNT "label"`.
- **Copyright:** NEJM CPC text (`nejm_sample.json`, `dev_nejm_sample.json`, and any new NEJM files) is paywalled + gitignored. Never commit/redistribute it.
- **Never tune on the holdout.** The frozen NEJM holdout is touched exactly once, at the very end.

---

## A. Verified starting point (measured this session — do not re-derive)

From the existing EVAL runs, re-scored with the new per-corpus metrics (`compute_v2_metrics.py`):

| Subset | n | Panel top-1 (full) | Panel top-1-or-partial | Single-Sonnet top-1-or-partial |
|---|---|---|---|---|
| **NEJM-CPC** | 17 | 0.529 | **0.824** | 0.588 |
| MCR | 8 | 0.500 | 0.500 | 0.375 |
| RareBench | 5 | 0.000 | 0.200 | 0.200 |
| All 30 | 30 | 0.433 | 0.633 | 0.467 |

**Critical reading.** `top_1_or_partial` is the metric comparable to MAI-DxO's ≥4/5 "leads-to-correct-treatment" rubric (per research agent, their rubric is looser than strict string top-1). On the NEJM subset the panel is **already at 0.824 ≈ MAI-DxO's 0.819** — but n=17 (95% CI ≈ [0.59, 0.93]) and the cases may be training-contaminated, so this number is **not yet trustworthy**. The real work is therefore:
1. **Make the number mean something** — a larger, decontaminated NEJM holdout (Phase 0). Without this, "accuracy at all costs" optimizes noise.
2. **Lift exact-match (full_credit)** from 0.529 — there is genuine headroom here even though full+partial is already high.
3. **Beat a *fair* baseline** (single Sonnet + CoT + self-consistency), not just the greedy single call.

## B. Strategy — levers ranked by evidence strength × budget fit

| # | Lever | Evidence | Expected effect | Cost |
|---|---|---|---|---|
| 1 | **Self-consistency** (k panel runs, modal vote) | Medprompt: biggest medical lever; also averages temp-0 noise; produced Quorum's own best calibration (ECE 0.52→0.40) | +3–8 pp + variance reduction | high (k×) |
| 2 | **Retrieved few-shot + explicit CoT** in Hypothesis | Medprompt: CoT +3.4, kNN few-shot +1.1, random few-shot +2.2 on MedQA | +2–5 pp | low |
| 3 | **Stronger Hypothesis (Bayesian) + Challenger (disconfirming tests)** | MAI-DxO qualitative analysis credits its wins here; anti-anchoring | +2–6 pp | ~free |
| 4 | **Info-value TestChooser + chain-length cap** | MAI-DxO "theory of information value"; overthinking hurts hard cases (<5k chars → higher accuracy) | +1–4 pp | ~free |
| 5 | **Extended thinking (capped) + persona diversity** | reasoning modes dominate medical QA; heterogeneous panels 91% vs 82% | +1–4 pp, risk of overthinking | medium |
| — | Mixed-vendor ensemble | **Rejected** — MAI-DxO's "ensemble" is same-model multi-run; multi-vendor unsupported; violates single-vendor constraint | n/a | n/a |

Order of execution = order of expected ROI per dollar: instrument first (Phase 0), then 2+3 (cheap, do during iteration), then 1 (expensive, reserve for confirmation/final), then 4–5 if budget remains.

## C. Budget ($100 incremental; $200 hard cap, ~$100.34 already spent)

**Corrected after adversarial review (panel-level SC is k× a full run, so it is affordable ONLY on the 12-case holdout, never on DEV):**

| Phase | Activity | Est. cost |
|---|---|---|
| 0 | Corpus growth (DEV + holdout) + contamination probe + formatting | $5 |
| 0/1 | DEV baseline run (~30 NEJM, single, temp 0) | $15 |
| 1–2 | Iteration: ~20 five-case smoke screens ($0.30 ea) + 2 confirmation DEV runs (~30 NEJM, $15 ea) | $36 |
| 4 | Fair baseline (single Sonnet + CoT + SC) on DEV + holdout | $6 |
| 4 | **Holdout run, panel-level SC k=5, ~12 cases** (0.50 × 12 × 5 = $30) | $30 |
| — | Buffer | $8 |
| | **Total** | **~$100** |

Per-case cost basis (from ledger): Arm-A ≈ $0.30–0.50/case; smoke screen ≈ $0.30. **Self-consistency multiplies a full panel run by k**, so at ~$0.50/case it is affordable only on the 12-case holdout ($30 at k=5), NOT on a 30-case DEV set ($75 at k=5). SC is therefore applied **once, at the holdout** (justified by literature + Quorum's own ECE 0.52→0.40 result), and we do not attempt to measure its accuracy delta on DEV. Log spend after **every** run.

## D. Anti-contamination & copyright protocol (READ BEFORE PHASE 0)

This is the integrity backbone. "Accuracy at all costs" without it produces a meaningless number.

1. **Decontaminated holdout = newest cases only.** Use **NEJM-CPC 2026** cases (12 available: `nejm-cpc-{2,3,4,5,6,7,8,9,10,11,13,14}-2026`) as the frozen holdout — they postdate plausible Sonnet-4.6 training cutoffs. We do **not** know Sonnet 4.6's exact cutoff; document this as an assumption and prefer the most recent cases regardless. NEJM-2025 + DEV-file cases become the tuning pool.
2. **Holdout is run once.** No prompt, threshold, k, or exemplar may be chosen by looking at holdout outputs. All selection happens on DEV.
3. **Exemplar/retrieval banks exclude the holdout.** Any few-shot exemplar or retrieved snippet bank is built only from DEV/training cases or external open sources — never from a holdout case's text or diagnosis. Add an assertion that holdout `case_id`s are absent from the exemplar bank.
4. **Copyright.** New NEJM cases go in gitignored files only (`dev_nejm_sample.json`, `nejm_2026_holdout.json`). Verify `git status` shows them untracked before any commit.
5. **Report contamination caveat** in the final writeup: NEJM CPCs are public; even 2026 cases may leak via web indexing. State it explicitly.

---

## Phase 0 — Instrument & corpus (mostly free; do entirely before spending on runs)

### Task 0.1: NEJM-only corpus filter + decontaminated split file

**Files:**
- Create: `data/cases/eval_corpus_v2/splits_v3_nejm.json`
- Modify: `backend/src/quorum/eval/v2_runner.py` (`load_v2_cases`, add `corpus`/`split_file` filtering)
- Test: `backend/tests/test_v3_nejm_split.py`

- [ ] **Step 1: Write the split file** (DEV = NEJM-2025 + tune-NEJM + DEV-file NEJM; HOLDOUT = NEJM-2026). Holdout list:

```json
{
  "dev": ["nejm-cpc-26-2025","nejm-cpc-27-2025","nejm-cpc-28-2025","nejm-cpc-30-2025",
          "nejm-cpc-32-2025","nejm-cpc-34-2025","nejm-cpc-35-2025","nejm-cpc-36-2025"],
  "holdout": ["nejm-cpc-2-2026","nejm-cpc-3-2026","nejm-cpc-4-2026","nejm-cpc-5-2026",
              "nejm-cpc-6-2026","nejm-cpc-7-2026","nejm-cpc-8-2026","nejm-cpc-9-2026",
              "nejm-cpc-10-2026","nejm-cpc-11-2026","nejm-cpc-13-2026","nejm-cpc-14-2026"],
  "_note": "v3 NEJM-only. DEV may be extended with dev_nejm_sample.json ids. HOLDOUT run once."
}
```

- [ ] **Step 2: Write failing test** in `backend/tests/test_v3_nejm_split.py`:

```python
from quorum.eval.v2_runner import load_v2_cases

def test_nejm_holdout_is_all_nejm_2026():
    cases = load_v2_cases(split_file="splits_v3_nejm.json", split_key="holdout")
    assert len(cases) >= 10
    assert all(c.corpus == "nejm" for c in cases)
    assert all(c.case_id.endswith("2026") for c in cases)

def test_dev_and_holdout_disjoint():
    dev = {c.case_id for c in load_v2_cases(split_file="splits_v3_nejm.json", split_key="dev")}
    hold = {c.case_id for c in load_v2_cases(split_file="splits_v3_nejm.json", split_key="holdout")}
    assert dev.isdisjoint(hold)
```

- [ ] **Step 3: Run it, verify it fails** — `cd backend && uv run pytest tests/test_v3_nejm_split.py -v` → FAIL (`load_v2_cases` has no `split_file` kwarg).

- [ ] **Step 4: Implement** — add to `load_v2_cases` in `v2_runner.py`:

```python
def load_v2_cases(
    split: Split | None = None,
    case_id: str | None = None,
    split_file: str | None = None,
    split_key: str | None = None,
) -> list[EvalCase]:
    pool = load_corpus() + load_dev_corpus()
    if case_id:
        return [c for c in pool if c.case_id == case_id]
    if split_file is not None:
        import json
        from quorum.eval.eval_case import CORPUS_DIR
        ids = set(json.loads((CORPUS_DIR / split_file).read_text())[split_key])
        return [c for c in pool if c.case_id in ids]
    if split == "dev":
        return load_dev_corpus()
    return load_corpus(split=split)
```

- [ ] **Step 5: Run test, verify pass.** Commit: `git add backend/src/quorum/eval/v2_runner.py backend/tests/test_v3_nejm_split.py data/cases/eval_corpus_v2/splits_v3_nejm.json && git commit -m "feat(eval): v3 NEJM-only decontaminated split (2026 holdout)"`

### Task 0.2: Grow the NEJM DEV pool (the rate-limiter for trustworthy tuning)

**Files:** Modify (gitignored): `data/cases/eval_corpus_v2/dev_nejm_sample.json`

**PROGRESS (2026-05-31):** 14 NEJM-2025 CPC cases (`nejm-cpc-{1..14}-2025`) added from the user's paywalled access → **NEJM DEV pool now 25** (was 11; ids `nejm-cpc-{1..25}-2025`). Target ≥30 → **~5 short**. All 2025, so correctly DEV (the 2026 holdout is untouched). Structured by 7 parallel subagents into the exact `_load_nejm` schema; validated (schema, types, no-answer-leakage into `initial_presentation`, confirmatory finding present). DEV now loads as **40 cases (25 NEJM + 15 MCR)**. Copyright + disjointness verified; a regression test guards both (see below). Case 13 carries a `_discrepancy_note` (source "Final Diagnosis" wording vs discussant phrasing) for human adjudication.

- [x] **Step 1:** Added 14 NEJM-2025 cases schema-matching `_load_nejm` (`case_id`, `initial_presentation`, `available_findings[]{category,label,content}`, `ground_truth_diagnosis`, `acceptable_partial_credit[]`, + rich `hidden_discussant_differential`/`ground_truth_components`/`citation`/`doi` ignored by the loader). **Remaining: ~5 more (2023–2024 preferred) to clear ≥30.**
- [x] **Step 2: Copyright safe** — `git check-ignore data/cases/eval_corpus_v2/dev_nejm_sample.json` confirms IGNORED; `git status` shows it untracked. Raw scratch lives in gitignored `_dev_nejm_raw/`.
- [x] **Step 3: Load verified** — `cd backend && uv run python -c "from quorum.eval.eval_case import load_dev_corpus; d=load_dev_corpus(); print(len(d), len([c for c in d if c.corpus=='nejm']))"` → `40 25`. (When Task 0.1 builds `splits_v3_nejm.json`, extend its `dev` list with `nejm-cpc-{1..25}-2025`.)
- [x] **Step 3b: Regression test added** — `backend/tests/test_splits.py::{test_dev_disjoint_from_splits,test_dev_no_duplicate_ids,test_dev_cases_well_formed}` assert DEV ∩ (TUNE∪EVAL)=∅, no dup ids, every NEJM DEV case carries `available_findings`. CI-safe (NEJM file may be absent on clean clone). `uv run pytest tests/test_splits.py -q` → 5 passed.
- [x] **Step 4:** No commit of data (gitignored); test + plan are committable. Log: `bash backend/scripts/log_spend.sh 0.00 "phase-0 corpus grow (+14 NEJM DEV, $0)"`.

### Task 0.3: Per-corpus metrics — DONE (2026-05-30)

`compute_v2_metrics.py` now emits `nejm_top_1`, `nejm_top_1_or_partial`, and `by_corpus`. Verified on `eval-baseline-arm-a`: `nejm_top_1_or_partial = 0.824`. No action.

### Task 0.4: Bootstrap CI helper for honest reporting

**Files:** Create `backend/scripts/bootstrap_ci.py`; Test `backend/tests/test_bootstrap_ci.py`

- [ ] **Step 1: Failing test:**

```python
from scripts.bootstrap_ci import bootstrap_ci
def test_bootstrap_ci_bounds():
    scores = [1]*8 + [0]*2  # 0.8 on n=10
    lo, hi = bootstrap_ci(scores, iters=2000, seed=0)
    assert 0.0 <= lo < 0.8 < hi <= 1.0
```

- [ ] **Step 2:** Run → FAIL. **Step 3: Implement:**

```python
import random
def bootstrap_ci(scores: list[int], iters: int = 2000, seed: int = 0, alpha: float = 0.05):
    rng = random.Random(seed); n = len(scores); means = []
    for _ in range(iters):
        means.append(sum(scores[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return means[int(alpha/2*iters)], means[int((1-alpha/2)*iters)]
```

- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(eval): bootstrap CI for small-n accuracy reporting`.

**GATE 0:** `cd backend && uv run pytest -q` green; ≥30 NEJM DEV cases load; holdout defined and untouched. Do not spend on model runs until GATE 0 passes.

---

## Phase 1 — Test-time compute (the two biggest levers)

### Task 1.1: Temperature plumbing for self-consistency

**Files:** Modify `backend/src/quorum/llm/client.py`; Test `backend/tests/test_llm_temperature.py`

- [ ] **Step 1:** Read `llm/client.py`; confirm whether `complete(...)` forwards `temperature`. If it already does, mark this task done and skip. If not:
- [ ] **Step 2: Failing test** — assert `complete(messages=..., temperature=0.6)` forwards `temperature` to the underlying call (use an AsyncMock on the transport).
- [ ] **Step 3:** Add `temperature: float | None = None` to `complete()` and forward it into the request payload only when not `None` (preserve current default behavior).
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(llm): optional temperature passthrough for self-consistency`.

### Task 1.2: Self-consistency aggregator (run k times → modal vote)

This needs **no runner refactor**: run `run_arm_a` k times into sibling dirs at temp>0, then aggregate. (For diversity, SC runs use temp≈0.6; deterministic baselines stay temp 0.)

**Files:** Create `backend/scripts/aggregate_self_consistency.py`; Test `backend/tests/test_sc_aggregate.py`

- [ ] **Step 1: Failing test** (build 3 fake run dirs with header lines carrying `final_committed_diagnosis`, assert modal vote + confidence):

```python
import json
from pathlib import Path
from scripts.aggregate_self_consistency import aggregate

def _mk(dir_, case, dx):
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_/f"{case}.audit.jsonl").write_text(json.dumps(
        {"case_id": case, "final_committed_diagnosis": dx,
         "final_posterior": {dx: 1.0}, "real_cost_usd": 0.1, "simulated_cost_usd": 0.0}) + "\n")

def test_modal_vote(tmp_path):
    for i, dx in enumerate(["Lupus","Lupus","Sarcoid"]):
        _mk(tmp_path/f"run{i}", "c1", dx)
    out = aggregate([tmp_path/f"run{i}" for i in range(3)], tmp_path/"voted")
    hdr = json.loads((out/"c1.audit.jsonl").read_text().splitlines()[0])
    assert hdr["final_committed_diagnosis"] == "Lupus"
    assert abs(hdr["final_posterior"]["Lupus"] - 2/3) < 1e-9
```

- [ ] **Step 2:** Run → FAIL. **Step 3: Implement:**

```python
"""Aggregate k self-consistency run dirs into one voted run dir.
For each case, take the modal final_committed_diagnosis across the k runs;
confidence = vote fraction. The voted dir is judged like any normal run.
Usage: aggregate_self_consistency.py voted_dir run0 run1 run2 ...
"""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path

def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())

def aggregate(run_dirs: list[Path], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    case_ids = {p.stem.replace(".audit","") for d in run_dirs for p in d.glob("*.audit.jsonl")}
    for case in sorted(case_ids):
        votes, display, cost = Counter(), {}, 0.0
        for d in run_dirs:
            f = d / f"{case}.audit.jsonl"
            if not f.exists():
                continue
            hdr = json.loads(f.read_text().splitlines()[0])
            dx = hdr.get("final_committed_diagnosis") or "(none)"
            votes[_norm(dx)] += 1; display.setdefault(_norm(dx), dx)
            cost += float(hdr.get("real_cost_usd", 0) or 0)
        if not votes:
            continue
        k = sum(votes.values())
        winner, nwin = votes.most_common(1)[0]
        posterior = {display[key]: c / k for key, c in votes.items()}
        (out_dir / f"{case}.audit.jsonl").write_text(json.dumps({
            "case_id": case,
            "final_committed_diagnosis": display[winner],
            "final_posterior": posterior,
            "real_cost_usd": cost,
            "simulated_cost_usd": 0.0,
            "sc_k": k, "sc_confidence": nwin / k,
        }) + "\n")
    return out_dir

if __name__ == "__main__":
    aggregate([Path(p) for p in sys.argv[2:]], Path(sys.argv[1]))
```

- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(eval): self-consistency vote aggregator`.

> **REQUIRED (adversarial-review fix): synonym clustering before voting.** The `_norm` (lowercase+whitespace) key above will scatter clinically-identical answers — "SLE" / "lupus" / "systemic lupus erythematosus" become 3 buckets, so the modal winner can be a 2/5 minority even when 4/5 agree. Before `Counter`, add **one Sonnet call** that groups the k committed strings into equivalence classes and returns a canonical label per class (reuse `quorum.eval.judge`'s LLM); vote on classes, not raw strings. Add a test where `["SLE","lupus","systemic lupus erythematosus","Sarcoidosis","SLE"]` → winner "systemic lupus erythematosus" with confidence 4/5. Without this fix, SC will *underperform* a single run.

### Task 1.3: Retrieved few-shot + explicit CoT in Hypothesis prompt

**Files:** Modify `backend/src/quorum/orchestrator/prompts/hypothesis.md`; optionally a DEV-only exemplar bank (gitignored if NEJM-derived).

- [ ] **Step 1:** Add an explicit chain-of-thought scaffold to `hypothesis.md` before the JSON output instruction, e.g.: *"Reason step by step BEFORE giving the differential: (1) list the discriminating features of the presentation; (2) for each candidate, state the supporting and refuting evidence; (3) assign a calibrated posterior. Keep reasoning under ~800 words — overlong chains correlate with anchoring errors on hard cases. Then output the JSON differential."*
- [ ] **Step 2:** Add 2–3 worked exemplars (presentation → reasoning → correct differential) drawn ONLY from DEV/training cases. Assert (Task D.3) that no holdout `case_id` text appears.
- [ ] **Step 3: Smoke screen** — `cd backend && uv run python scripts/prompt_iteration_eval.py` (5-case) → all outputs schema-valid. **Step 4:** Commit prompt change (verify no NEJM holdout text committed).

### Task 1.4: DEV measurement of Phase-1 stack

- [ ] **Step 1:** Single DEV run (temp 0), current config, NEJM DEV: establish the DEV baseline. `QUORUM_MAX_COST_USD=15 uv run python -m quorum.eval.v2_runner --arm arm_a --panel v2_quorum_calibrated --confirm-cost` against the v3 DEV split (wire `--split-file/--split-key` into the CLI argparse, mirroring Task 0.1). Judge + compute metrics. Log spend.
- [ ] **Step 2:** Self-consistency k=5 on the same DEV set (temp 0.6 × 5 runs) → aggregate → judge → compute `nejm_top_1` + `nejm_top_1_or_partial` + bootstrap CI.
- [ ] **GATE 1:** SC k=5 NEJM-DEV `top_1_or_partial` exceeds the single-run DEV baseline by more than the bootstrap CI half-width. If not, keep k for variance reduction but do not claim an accuracy win; proceed to Phase 2.

---

## Phase 2 — Scaffolding quality (cheap, evidence-backed)

### Task 2.1: Stronger Bayesian Hypothesis + disconfirming Challenger

**Files:** Modify `prompts/hypothesis.md`, `prompts/challenger.md`.

- [ ] **Step 1 (Hypothesis):** Require explicit prior → likelihood → posterior per candidate, an explicit "must-not-miss" (consequence) row, and a confidence that reflects evidence, not fluency.
- [ ] **Step 2 (Challenger):** Require it to name the single test/finding that would most cheaply *discriminate the top-2 hypotheses* and to state "what evidence would change the leading diagnosis." This is the lever MAI-DxO credits most.
- [ ] **Step 3:** Smoke screen (5-case) schema-valid. Single DEV run + metrics + bootstrap CI vs Phase-1 DEV. **GATE 2a:** keep only if DEV `top_1_or_partial` does not regress beyond noise. Commit.

### Task 2.2: Info-value TestChooser + chain-length control

**Files:** Modify `prompts/test_chooser.md`; `run_arm_a` call site (`max_turns`, `commit_threshold`).

- [ ] **Step 1:** TestChooser prompt: select the test maximizing expected information gain across the current top hypotheses (not just "the next obvious test").
- [ ] **Step 2:** Sweep `commit_threshold ∈ {0.60, 0.70, 0.80}` and `max_turns ∈ {12, 20, 30}` on a 5-case smoke, then one DEV run at the best smoke setting. (Evidence: shorter chains help hard cases.)
- [ ] **GATE 2b:** adopt the (threshold, max_turns) with best DEV `top_1_or_partial` within budget. Commit.

---

## Phase 3 — Diversity & reasoning (only if >$30 budget remains)

### Task 3.1: Extended thinking on Hypothesis (capped)

- [ ] Enable Sonnet extended-thinking for the Hypothesis agent with a **capped thinking budget**; measure one DEV run. **GATE 3a:** keep only if DEV `top_1` improves beyond noise AND cost stays in budget (reasoning tokens are pricey). Revert if overthinking degrades hard cases.

### Task 3.2: Persona diversity + anti-conformity

- [ ] Differentiate agent personas (e.g., Hypothesis = broad differential generator; Challenger = skeptical contrarian with explicit anti-conformity instruction "do not defer to the majority; argue the strongest alternative"). One DEV run. **GATE 3b:** keep only on non-noise DEV improvement.

> Retrieval-augmented external knowledge (MDAgents +11.8%) is **deferred**: vector retrieval needs a new dep (violates constraints) and a curated leakage-safe corpus. Only pursue with explicit user approval + a dependency exception.

---

## Phase 4 — Fair baseline & the single frozen holdout run

### Task 4.1: Fair baseline arm (single Sonnet + CoT + self-consistency)

**Files:** Create `backend/config/panels/v3_single_sonnet_sc.yaml` (single agent, CoT prompt); reuse Arm-B path + SC aggregator.

- [ ] Run single-Sonnet+CoT k=5 SC on NEJM DEV. This is the **honest** baseline (the greedy single call is too weak — literature: same-model debate barely beats single+SC). Record DEV `top_1_or_partial`.

### Task 4.2: THE holdout run (once)

- [ ] **Step 1:** Freeze the winning panel config (prompts, threshold, max_turns, k) from Phases 1–3. No further changes after this point.
- [ ] **Step 2:** Run the frozen panel, **k=5 self-consistency**, on the **12-case NEJM-2026 holdout**. Aggregate → judge (`judge_v2_run.py`) → `compute_v2_metrics.py`.
- [ ] **Step 3:** Run the fair baseline (4.1) on the same holdout, k matched.
- [ ] **Step 4:** Report `nejm_top_1`, `nejm_top_1_or_partial`, bootstrap 95% CI, ECE/Brier (secondary), cost — panel vs fair baseline vs MAI-DxO 0.819. Log spend.

---

## Success criteria

- **Primary:** decontaminated NEJM-2026 holdout `top_1_or_partial` ≥ **0.75** (stretch ≥ 0.819), reported with bootstrap 95% CI and the contamination caveat.
- **Secondary:** NEJM `full_credit` (exact top-1) improves beyond run-to-run noise vs the 0.529 baseline (multi-seed/SC-confirmed).
- **Guardrail:** panel ≥ fair baseline (single Sonnet + CoT + SC) on the holdout. If the panel does **not** beat it, report that honestly — it means the panel's value is calibration/auditability, not raw accuracy.
- **No regression:** ECE not materially worse than the 0.45 baseline.
- **Integrity:** holdout run exactly once; no holdout text in any committed file or exemplar bank.

## Risk register

| Risk | Mitigation |
|---|---|
| Tuning toward a tiny holdout = overfitting | Holdout run once; all selection on DEV; bootstrap CIs reported |
| Training contamination inflates the number | 2026-only holdout; documented caveat; report DEV(older) vs holdout(newer) gap |
| n=12 holdout too small to detect effects | Report CIs honestly; frame as "consistent with," not "matches"; grow holdout if more 2026 cases become available |
| SC blows the budget | SC only at confirmation + final; iterate with single runs + smoke screens |
| "Accuracy at all costs" abandons the calibration niche | Keep ECE/Brier as secondary readout; fair-baseline guardrail reveals whether the panel earns its accuracy keep |
| Retrieval leakage | Deferred; if pursued, assert holdout ids absent from bank |

## Self-review (per writing-plans skill)

- **Spec coverage:** levers 1–5 each map to a task (1→1.2/1.4, 2→1.3, 3→2.1, 4→2.2, 5→3.1/3.2); instrument + decontamination → Phase 0; fair baseline → 4.1; final → 4.2. ✓
- **Placeholders:** none — code shown for all code tasks; experiments have concrete commands + gates. ✓
- **Type consistency:** `aggregate(run_dirs, out_dir)`, `bootstrap_ci(scores, iters, seed)`, `load_v2_cases(..., split_file, split_key)` used consistently. ✓ (Open item: `prompt_iteration_eval.py` and the runner CLI need `--split-file/--split-key` flags — folded into Tasks 1.4/0.1.)

## Execution handoff

Recommended: run as an autonomous `/goal` session pointed at this file, OR subagent-driven-development task-by-task with review at each GATE. GATE 0 (instrument + decontamination) must pass before any model spend.

---

## Adversarial Review & Revisions (pre-mortem, self-conducted 2026-05-30)

A red-team of the plan above against the stated goal ("approach MAI-DxO accuracy on NEJM-CPC, accuracy at all costs, no data leakage"). Items marked **REVISION** override the relevant task; two errors were already fixed inline (budget table, Task 1.2 voting).

**1. The premise may already be satisfied — spend accordingly.** The panel is already at NEJM `top_1_or_partial` = 0.824 ≈ MAI-DxO's 0.819. The highest-value outcome is a *trustworthy* 0.82, not a higher one. **REVISION (overrides Phase 1–3 budget):** reallocate away from many DEV iteration runs (each unmeasurable at n≈30) toward (a) growing the decontaminated holdout and (b) one clean SC holdout run. Treat prompt tweaks as adopt-on-smoke-validity-and-theory, not measured wins.

**2. Decontamination will likely LOWER the number — that is the point.** The 0.824 is on 2025/older cases that Sonnet may have memorized. A clean 2026 holdout could land at 0.60–0.75. MAI-DxO's 0.819 is itself partly contaminated (they report a decontamination drop). **REVISION (overrides Success criteria):** expectation-set explicitly — the honest decontaminated target is "approach MAI-DxO *on comparably-decontaminated data*," and a result of 0.65–0.75 with a tight CI is a **better** outcome than 0.85 on contaminated cases. Do not treat a drop from 0.824 as failure.

**3. n=12 holdout cannot resolve the effects we care about.** 9/12 = 0.75 ± ~0.24. **REVISION (overrides Phase 0):** add **Task 0.2b — grow the holdout** to ≥25 decontaminated NEJM cases (2024–2026, kept disjoint from DEV/exemplars) BEFORE the final run. This is the single highest-leverage budget item; bench size beats every model tweak for shrinking the CI.

**4. Date-based decontamination is an assumption, not a check.** **REVISION (overrides Phase 0):** add **Task 0.5 — contamination probe.** For each holdout candidate, give the model only the first 1–2 sentences (no workup) and ask for the diagnosis cold; if it nails the rare/specific answer without the workup, flag as likely-memorized and exclude from the holdout. Cheap (~$0.02/case), and it makes the "decontaminated" claim defensible.

**5. Self-consistency design was both unaffordable and unsafe as written.** Panel-level SC at temp 0.6 (a) costs k× a full run (budget-breaking on DEV — fixed in the budget table) and (b) raising temperature across a multi-turn agent + Gatekeeper pipeline can degrade per-run reasoning (Medprompt's SC was single-call QA, not an agent loop). **REVISION (overrides Task 1.4 / removes GATE 1):** (i) SC is applied **only at the holdout**, panel-level k=5; (ii) before committing to temp 0.6, run a one-shot temp sweep {0.0, 0.4, 0.7} on 5 DEV cases and pick the lowest temp that still yields vote diversity; (iii) the holdout report compares single-run vs SC directly (that *is* the SC measurement). The cheaper, safer alternative — resample only the final Hypothesis synthesis at temp>0 while keeping deliberation at temp 0 — is preferred if the bounded runner refactor is acceptable; it cuts SC cost ~10×.

**6. Voting on raw diagnosis strings is a correctness bug.** Fixed inline in Task 1.2 (REQUIRED synonym clustering). Without it SC underperforms a single run. Flagged here because it is the most likely silent failure.

**7. NEJM-narrowing looks like cherry-picking unless transparent.** Dropping MCR/RareBench toward the subset that scores best is a real reviewer/grader objection. **REVISION (overrides §A framing):** do **not delete** MCR/RB data; keep them as a secondary "generalization" column in every report. State the justification prominently: MAI-DxO benchmarks on NEJM-CPC, so NEJM-only is the apples-to-apples comparison, with MCR/RB retained for out-of-distribution transparency.

**8. The fair baseline may beat the panel — accept the risk before spending.** Literature (same-model debate ≈ single+SC at equal compute) means single-Sonnet+CoT+SC could match the panel. For an "accuracy at all costs" goal this could read as "the multi-agent panel buys little accuracy." **Decision:** keep the fair baseline — discovering this honestly is worth more than a fragile headline, and the panel's calibration/auditability remain genuine differentiators. The user should expect this possible outcome.

**9. Phase 3 is aspirational.** Given the corrected budget, Phases 0–2 + 4 consume ~$92; Phase 3 (extended thinking, personas) will almost certainly not run. **REVISION:** mark Phase 3 "execute only if Phases 0–2+4 underspend by >$15." Extended thinking also risks the documented overthinking-hurts-hard-cases effect, so it is correctly low priority.

**10. DEV gates are themselves underpowered.** GATE 2a/2b "improve DEV `top_1_or_partial`" at n≈30 inherits the exact disease that killed the overnight campaign (±9pt CI). **REVISION (overrides GATE 2a/2b):** DEV gates become **"smoke-screen schema-valid AND no >1-bootstrap-CI-half-width regression."** Prompt changes are adopted on mechanism/theory (Bayesian framing, disconfirming tests, info-value) plus non-regression — not on sub-CI DEV deltas. Only the holdout + SC comparison is treated as a measured result.

**Net effect of the review:** the plan shifts from "tune prompts hard and chase a higher number" to "**build a trustworthy decontaminated holdout, apply the one high-evidence test-time lever (SC) correctly and affordably, adopt cheap scaffolding improvements on theory, and report honestly with CIs against a fair baseline.**" This is the optimal expected-value use of $100 given the goal and the measured starting point.

> An independent second-pass review by a separate `architect`/`code-reviewer` subagent is available on request; this review was self-conducted with full session context.
