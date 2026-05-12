# Evaluation Methodology

> Design-intent doc. The eval corpus is **not** populated yet and the runner
> is a stub. Numbers below are TBD unless explicitly cited.

## Case sourcing

The primary benchmark is a reconstruction of the **NEJM Clinicopathological
Conference (CPC) set** in the spirit of MAI-DxO (arXiv 2506.22405), which
reported **85.5% top-1 diagnostic accuracy on 304 NEJM CPC cases**.

Cases are transcribed into the structured JSON shape declared in
`data/cases/nejm/_schema.json`: presentation vignette, optional prior
workup, ground-truth final diagnosis, and metadata (date, specialty,
discriminating features). MAI-DxO's exact case-extraction pipeline is
not redistributed; Quorum's corpus is independently re-curated.

A secondary control set is drawn from **MedQA** (`data/cases/medqa/`)
as a sanity-check on multiple-choice clinical reasoning that does not
require the iterative test-ordering loop.

## Corpus v1 plan

These are **targets**, not "as-built":

- ~50 NEJM CPC cases (subset of the 304 used by MAI-DxO; selection biased
  toward **post-cutoff** cases to reduce training-data contamination — see
  Limitations below).
- ~30 MedQA cases as a non-deliberative control.

Final counts will be reported in `data/results/<run_id>/manifest.json`
once the corpus is curated.

## Metrics

The eval scorer (`backend/src/quorum/eval/scorer.py`) is intended to
report, per run:

- **Top-1 accuracy** — does the panel's `FinalVerdict.top_diagnosis`
  match the ground-truth diagnosis (synonym-aware match)?
- **Top-5 accuracy** — is the ground truth in `FinalVerdict.alternatives[:5]`?
- **Mean Reciprocal Rank (MRR)** over the ranked differential.
- **Calibration** — Brier score and/or Expected Calibration Error (ECE).
  The specific calibration metric is **TBD**; both are commonly reported.
- **Cost per case** — total USD spent across all LLM calls, summed from
  provider usage in `LLMClient`.
- **Latency per case** — wall-clock from `Panel.diagnose()` entry to
  `FinalVerdict` emission.

## Comparison rubric

For each case in the corpus, the runner is intended to evaluate:

| System                                  | What it is                            | Expected result |
|-----------------------------------------|---------------------------------------|-----------------|
| Single-call Claude Opus 4.7             | One-shot prompt, no debate            | TBD             |
| Single-call GPT-5                       | One-shot prompt, no debate            | TBD             |
| Single-call Gemini 2.5 Pro              | One-shot prompt, no debate            | TBD             |
| **Quorum panel** (this project)         | 5-agent debate over N rounds          | TBD             |
| MAI-DxO (reported, arXiv 2506.22405)    | Microsoft's closed system, NEJM CPC   | **85.5%**       |
| Random baseline                         | Uniform pick from differential set    | ~5%             |

Only **85.5%** and **304 cases** are anchored numbers; everything else
is TBD until a run is executed.

## Limitations

- **Training-data contamination.** NEJM CPC cases are publicly indexed
  and have likely been seen by every frontier model in pre-training.
  Mitigation: prefer cases published after a chosen recency cutoff and
  record the cutoff in each run's manifest. Even with that filter,
  contamination cannot be ruled out.
- **Gatekeeper-model variance.** MAI-DxO uses a "gatekeeper" simulator
  to release test results on demand. Quorum's gatekeeper is a separate
  LLM prompt and will have variance across runs; reporting mean ± std
  over `n_seeds` repeats is the intended mitigation.
- **Prompt sensitivity.** Five-agent debate outcomes are sensitive to
  agent prompt wording. Per-agent prompts in
  `backend/src/quorum/orchestrator/prompts/*.md` will be versioned and
  the version tagged into the result manifest.
- **Small-N statistical power.** ~50 cases is small; confidence intervals
  on accuracy differences will be wide. The report module should emit
  bootstrap CIs alongside point estimates.

## File layout

```
data/cases/nejm/<case_id>.json     # one case per file, validated against _schema.json
data/cases/medqa/<case_id>.json    # control set
data/schemas/*.json                # generated Pydantic schemas
data/results/<run_id>/<case_id>.json  # per-case panel transcript + verdict
data/results/<run_id>/manifest.json   # run metadata, prompt versions, model IDs
data/results/<run_id>/report.md       # human-readable summary
```

## Code map

- `backend/src/quorum/eval/corpus.py` — load and validate cases from
  `data/cases/`.
- `backend/src/quorum/eval/runner.py` — drive `Panel.diagnose()` over a
  corpus; write per-case results.
- `backend/src/quorum/eval/scorer.py` — compute the metrics above.
- `backend/src/quorum/eval/report.py` — render the run report.

All four currently raise `NotImplementedError`.
