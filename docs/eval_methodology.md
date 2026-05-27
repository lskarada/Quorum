# Evaluation Methodology

This document describes Quorum's eval harness as built. The harness loads
public clinical-case corpora, runs them through a configured panel, scores
the verdicts against ground truth, and reports paired statistical tests
across panel configurations.

## Corpus

### Primary: MedQA

The primary benchmark is **MedQA** (USMLE-format multiple-choice questions
on clinical reasoning). MedQA is public and available via the BigBio
mirror; Quorum loads cases from `data/cases/medqa/`. MedQA cases used for
autonomous `/goal` runs are the public train/dev split — no paywalled
material is redistributed.

MedQA is the corpus used for the `/goal` autonomous smoke runs (n=3 by
default) and is the default `--corpus` flag for `quorum-eval`.

### Secondary corpora (loaders shipped)

The following corpora have download loaders in
`backend/scripts/download_corpus.py` and matching eval-harness loaders in
`backend/src/quorum/eval/corpus.py`. The case JSON is **not committed**
(license uncertainty + corpus size); reproduce locally via the download
step below.

- **CUPCase** — open case-report corpus (`ofir408/CUPCase` on
  HuggingFace, test split). 200 cases. More discursive, presentation-style
  format than MedQA's MCQ structure.
- **MedCaseReasoning** — `zou-lab/MedCaseReasoning` on HuggingFace, train
  split, 200 cases. Includes explicit per-case reasoning labels enabling
  reasoning-trace scoring on top of final-answer scoring.

### Reproducibility — downloading corpora

Corpus JSON files at `data/cases/<name>/all.json` are gitignored to
avoid redistributing third-party medical case data without a license
audit. Reproduce locally:

```bash
cd backend && uv run python scripts/download_corpus.py            # all three
cd backend && uv run python scripts/download_corpus.py cupcase    # one corpus
```

The script reads from upstream HuggingFace mirrors (verified accessible
2026-05-24) and normalizes each row into the schema expected by the
loader. Re-run any time you need a fresh local copy.

### Not included: NEJM CPCs

The NEJM Clinicopathological Conference (CPC) corpus used by MAI-DxO
(arXiv 2506.22405) is **not** part of this evaluation. NEJM CPCs are
paywalled and Microsoft did not redistribute their extracted corpus.
Direct head-to-head comparison to MAI-DxO's reported 85.5% top-1 figure
is therefore listed as future work and is not claimed here.

## Metrics

Per-case metrics, computed by `backend/src/quorum/eval/scorer.py`:

- **Top-1 accuracy** — does `FinalVerdict.top_diagnosis` match the
  ground-truth diagnosis (synonym-aware match)?
- **Top-5 accuracy** — is the ground truth in
  `FinalVerdict.alternatives[:5]`?
- **Mean Reciprocal Rank (MRR)** — over the ranked differential.
- **Mean cost per case** — USD spent across all LLM calls in the run,
  summed from per-call usage in `LLMClient`.

Latency is recorded in per-case result files but not summarized in the
default report.

## Comparison protocol

The headline ablation is **mixed-vendor panel vs single-model premium
panel**, scored on the same corpus with paired statistical tests.

- **Top-1 accuracy** — paired **McNemar's test** with continuity
  correction. Each case yields a (panel_A_correct, panel_B_correct) pair;
  McNemar tests whether the discordant pairs are symmetric.
- **MRR** — **Wilcoxon signed-rank** test on per-case MRR differences.
  Wilcoxon replaces the paired t-test that an earlier draft specified
  because MRR is bimodal (heavily concentrated at 1.0 and at 0.0) and
  violates the normality assumption of t-test. The architect note on
  this is documented in the design doc.

The scorer reports the test statistic, p-value, and the discordant-pair
count alongside the headline accuracy numbers.

## Run sizes

| Use case               | n   | Notes |
|------------------------|-----|-------|
| `/goal` smoke run      | 3–10 | dev_cheap panel, ~$0.05–$0.20 |
| Headline comparison    | 100 | mixed_vendor vs single_model_premium, ~$5–10/panel |
| Power-adequate future  | 300 | not run in this release; see Limitations |

The default `--n` for the CLI is 100 for headline runs and 3 for autonomous
smoke runs. Run size is recorded in `data/results/<run_id>/manifest.json`.

## Limitations

### Statistical power

At n=100 cases with an empirically observed discordant-pair rate around
30%, McNemar's test (and Wilcoxon on MRR) can detect accuracy deltas of
approximately 15 percentage points at α=0.05. Smaller true deltas will
be reported as "not statistically significant" — this is a power
limitation and **does not imply equivalence between panels**. A future
run at n=300 is planned to address this; the design doc tracks this as
known future work.

### Inter-run variance

All eval runs use `temperature=0` in `PanelConfig`. No 3× replication
across seeds is performed. Run-to-run variance from non-determinism in
provider routing (OpenRouter), tokenization, and any small temperature
floor at the provider level is therefore not characterized. This is a
known limitation; replicate-with-seeds is feasible but not on the
release path.

### Training-data contamination

MedQA, CUPCase, and MedCaseReasoning are public corpora and have likely
appeared in pre-training data for every frontier model the panels route
to. Per-case dates and a recency cutoff are not enforced by the loader.
Contamination cannot be ruled out and confounds the absolute-accuracy
numbers.

### Prompt sensitivity

Five-agent debate outcomes depend on prompt wording. Per-agent prompt
files in `backend/src/quorum/orchestrator/prompts/*.md` are versioned in
git; the commit SHA is recorded in each run manifest, but no automated
prompt-variant ablation is included.

### Prompt tuning protocol + held-out set

A 7-case held-out set is reserved in
`backend/tests/fixtures/prompt_tuning_holdout.json` (case IDs
`medqa_0050..medqa_0056`). These cases MUST be excluded from any headline
run via the `--exclude` flag on `quorum-eval run`, to prevent the
headline numbers from being optimistic against the cases used to tune
the prompts. A single hypothesis-prompt iteration cycle was attempted
on this holdout (2026-05-24): a fully rewritten production variant
neither improved over the skeleton baseline on the comparable
non-error subset nor reduced the intermittent LLM-JSON-parse error
rate, so the skeleton prompt was retained. Per-agent prompt iteration
for the remaining four agents is documented as future work.

## Reporting framing

Quorum reproduces MAI-DxO's architecture and evaluates on public
clinical-case benchmarks. Direct numerical comparison to MAI-DxO's 85.5%
on NEJM CPCs requires paywalled-corpus access and is listed as future
work. We report Quorum's performance vs single-call baselines on public
corpora; **mixed-vendor vs single-model comparison is the headline
ablation**.

## Cost guardrails

Two independent caps prevent runaway spend:

- **`QUORUM_MAX_COST_USD`** — per-eval-run cap. The runner aborts the
  current run when cumulative cost exceeds this value. Default: $20.
  Configurable via env var or `--max-cost` on the CLI.
- **`QUORUM_TOTAL_SPEND_LIMIT_USD`** — cumulative across all LLM use,
  not just one run. Persists across processes via
  `~/.quorum/spend.json`. Default: $15. The `LLMClient` refuses calls
  that would exceed this cap.

Both caps fail closed: an exceeded cap raises before the next LLM call,
the run terminates with a partial manifest, and the scorer treats the
unfinished cases as missing.

## File layout

```
data/cases/medqa/<case_id>.json       # MedQA case, validated against schema
data/schemas/*.json                   # generated Pydantic schemas
data/results/<run_id>/<case_id>.json  # per-case panel transcript + verdict
data/results/<run_id>/manifest.json   # run metadata, panel config, prompt SHA, cost
data/results/<run_id>/report.md       # human-readable summary (from `report` CLI)
```

## Code map

- `backend/src/quorum/eval/corpus.py` — load and validate cases.
- `backend/src/quorum/eval/runner.py` — drive `Panel.diagnose()` over a
  corpus; write per-case results; honor `QUORUM_MAX_COST_USD`.
- `backend/src/quorum/eval/scorer.py` — top-1, top-5, MRR, mean cost;
  paired McNemar and Wilcoxon for two-panel comparisons.
- `backend/src/quorum/eval/report.py` — render `report.md`.
- `backend/src/quorum/eval/cli.py` — `quorum-eval {run,score,report}`.

## Invocation

```bash
# Smoke run (autonomous /goal scale)
cd backend && uv run quorum-eval run --corpus medqa --panel dev_cheap --n 3

# Score against ground truth
cd backend && uv run quorum-eval score data/results/<run_id> --corpus medqa

# Render report.md
cd backend && uv run quorum-eval report data/results/<run_id> --corpus medqa
```
