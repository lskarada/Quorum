# Quorum — Headline eval results

> Eval methodology and corpus rationale live in
> [`docs/eval_methodology.md`](./eval_methodology.md). This page reports
> the numbers from the headline run.

## Headline comparison

**Setup**: MedQA, n=30 cases per panel (cases 7–36 — the first 7 case IDs
are reserved as a prompt-tuning holdout in
`backend/tests/fixtures/prompt_tuning_holdout.json` and excluded via the
`--exclude` flag). One panel pair runs, scored with paired McNemar on
top-1 accuracy.

| Panel                  | Top-1 accuracy | Mean cost / case | Error rate | Schema notes |
|------------------------|---------------:|-----------------:|-----------:|--------------|
| `dev_cheap`            | 5/30 = 16.7%   | $0.0069          | 10/30 = 33.3% | 5-agent, 3-iter loop, mid-tier models (haiku-4-5 / gemini-2.5-flash / gpt-4o-mini / llama-3.3-70b) |
| `baseline_single_call` | 8/30 = 26.7%   | $0.0766          | 3/30 = 10.0%  | 1 Hypothesis call only, claude-opus-4 |

**Paired McNemar** (top-1, continuity-corrected): statistic = 1.333,
**p = 0.248** (not significant at α=0.05; n=30 is power-limited).
**Wilcoxon signed-rank** (MRR): statistic = 0.0, **p = 0.083** (marginal).

The observed direction at this n is that `baseline_single_call` (single
claude-opus-4 call) edges out the 5-agent `dev_cheap` panel on top-1 by
10 percentage points, but the McNemar test does not reject the null of
no difference at α=0.05. The error-rate gap (33% vs 10%) is the
dominant driver of the observed top-1 gap: `dev_cheap`'s
haiku-4-5-routed hypothesis agent intermittently returns malformed JSON
that defeats parsing, and those cases get scored as wrong. Tighter
JSON-coercion logic in `LLMClient` (or replacing haiku-4-5 in the
hypothesis slot) is the highest-leverage follow-up.

## Methodological caveat on MedQA scoring

MedQA cases are USMLE-format multiple-choice questions. The `answer`
field is the correct *option text*, which is heterogeneous: sometimes a
diagnosis (which the Hypothesis agent's top candidate can be
substring-matched against), sometimes a *treatment* ("Nitrofurantoin"),
a *prevention measure* ("Placing the infant in a supine position on a
firm surface"), or a *next diagnostic test* ("24-hour urine protein").

The scorer's substring match (`backend/src/quorum/eval/scorer.py`
`_matches`) silently underestimates the panel's *diagnostic* accuracy
on cases where the correct option is not a diagnosis. The understatement
applies equally to both panels in a paired comparison, so the *relative*
ranking and the McNemar test remain valid even when the absolute
top-1 numbers are pessimistic. A future eval on a diagnosis-pure corpus
(CUPCase, MedCaseReasoning) would tighten the absolute numbers.

## What this comparison shows

The headline ablation is **5-agent debate (dev_cheap) vs single-call
baseline (claude-opus-4 alone)**. Both panels see the same MedQA cases
and are scored identically. The paired McNemar test on top-1 detects
whether one panel systematically wins or loses on cases where the two
disagree.

This is the demo number Quorum reports, not a head-to-head against
MAI-DxO's 85.5% on NEJM. MAI-DxO's corpus is paywalled and not
redistributable; the comparison framing is documented in
`docs/eval_methodology.md` § "Reporting framing".

## Run artifacts

Per-case verdict JSONs + manifests live under `data/results/` (gitignored
— regenerate with the `quorum-eval run` commands below). For
reproducibility, the runs that produced this table are:

- `data/results/dev_cheap_medqa_1779678619/` — n=30 dev_cheap MedQA
- `data/results/baseline_single_call_medqa_1779679153/` — n=30 baseline MedQA

## Reproducing locally

```bash
# Get a fresh OpenRouter key + load it into .env, then:
cd backend && uv run quorum-eval calibrate --panel dev_cheap --n 2
cd backend && uv run quorum-eval calibrate --panel baseline_single_call --n 2

QUORUM_MAX_COST_USD=4 uv run --project backend quorum-eval run \
  --corpus medqa --panel dev_cheap --n 30 --confirm-cost \
  --exclude backend/tests/fixtures/prompt_tuning_holdout.json \
  --cases-root data/cases --results-root data/results

QUORUM_MAX_COST_USD=4 uv run --project backend quorum-eval run \
  --corpus medqa --panel baseline_single_call --n 30 --confirm-cost \
  --exclude backend/tests/fixtures/prompt_tuning_holdout.json \
  --cases-root data/cases --results-root data/results

# Score + compare
uv run --project backend quorum-eval score data/results/<dev_cheap_dir> --corpus medqa --cases-root data/cases
uv run --project backend quorum-eval score data/results/<baseline_dir>  --corpus medqa --cases-root data/cases
uv run --project backend quorum-eval compare data/results/<dev_cheap_dir> data/results/<baseline_dir> --corpus medqa --cases-root data/cases
```

## Limitations

See `docs/eval_methodology.md` § "Limitations" for the full list. The
two most load-bearing for this table:

1. **Statistical power.** At n=30 (smaller than the originally-planned
   n=100 because of session budget), McNemar detects roughly 25-point
   top-1 deltas at α=0.05. Smaller true deltas may be reported as "not
   significant" without implying equivalence.
2. **Premium-model panels deferred.** `single_model_premium` (all-Opus)
   and `mixed_vendor` (Opus + GPT-4o + Gemini-2.5-pro) are documented
   panel configs but were not run as part of the headline ablation
   because their projected cost (~$150 each at n=100) exceeded the
   session cap. Reproducing those panels requires raising
   `QUORUM_MAX_COST_USD` and budgeting accordingly.
