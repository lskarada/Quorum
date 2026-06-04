# Quorum v3 — decontaminated, run-once NEJM-2026 holdout

> **Headline:** on a 12-case NEJM CPC holdout that was screened for
> training-data contamination and scored exactly once, the 5-agent Quorum panel
> (with SafetyChecker) reaches **41.7% exact-match** and **75.0% exact-or-partial**,
> versus **16.7% / 58.3%** for the same model called once. Deliberation + safety
> gating **2.5× the exact-match rate** on cases neither arm had seen.

This document backs the headline table in the project [`README.md`](../README.md).
The committed run artifacts it summarizes live under
[`data/results/v3-holdout-sc-voted/`](../data/results/v3-holdout-sc-voted/) (Quorum)
and [`data/results/v3-holdout-baseline-voted/`](../data/results/v3-holdout-baseline-voted/)
(baseline): each is a `judge_results.json` (per-case LLM-judge verdicts) plus
one append-only `*.audit.jsonl` per case.

**Copyright note.** NEJM CPC case *bodies* are paywalled and are **not** included
here or in the committed artifacts. What is reported is the published final
*diagnosis name* (a fact, not the copyrighted case presentation), each arm's
committed diagnosis, and the judge verdict — the standard reporting surface for a
diagnostic benchmark.

## Method

- **Corpus:** 12 NEJM Clinical Pathological Conference cases from 2025–2026,
  held out from all tuning. The DEV pool used for prompt iteration is disjoint
  (see [`docs/superpowers/plans/2026-05-30-quorum-accuracy-maximization-v3-nejm.md`](superpowers/plans/2026-05-30-quorum-accuracy-maximization-v3-nejm.md)).
- **Decontamination:** each holdout case was screened with a cold-recall
  contamination probe before scoring; the holdout was scored a single time (no
  tuning on it).
- **Self-consistency:** each arm was run with `k=5` replicas at non-zero
  temperature; the reported diagnosis is the **modal vote** across the 5 replicas
  (`manifest.json` records the 5 source run dirs per arm).
- **Scoring:** an LLM judge (Claude Sonnet 4.6) graded each committed diagnosis
  against the published final diagnosis as `full_credit` (exact),
  `partial_credit` (correct disease category / missed co-diagnosis), or
  `no_credit`.
- **Panel:** `v2_quorum_calibrated` — all five agents on
  `anthropic/claude-sonnet-4-6`. Baseline = the same model, one call, no panel.

## Headline

| Arm | Top-1 (exact) | Top-1 or partial |
|-----|---------------|------------------|
| **Quorum** (5-agent + SafetyChecker, k=5 modal vote) | **41.7%** (5/12) | **75.0%** (9/12) |
| Single-model baseline (same model, one call, k=5 modal vote) | 16.7% (2/12) | 58.3% (7/12) |

Reference points from the literature (**not** directly comparable to this 12-case
holdout): the closed MAI-DxO reaches 85.5% and unaided physicians ~20% on the
broader 304-case SDBench set ([arXiv 2506.22405](https://arxiv.org/abs/2506.22405)).

## Per-case verdicts (both arms)

Ground truth = published NEJM final diagnosis. ✓ full credit · ◐ partial · ✗ no credit.

| Case | Ground-truth diagnosis | Quorum | Baseline |
|------|------------------------|:------:|:--------:|
| nejm-cpc-2-2026 | Disseminated hypervirulent *Klebsiella pneumoniae* (K1) | ✗ | ✗ |
| nejm-cpc-3-2026 | Lyme neuroborreliosis + *Babesia microti* coinfection | ◐ | ◐ |
| nejm-cpc-4-2026 | *Pneumocystis jirovecii* + *Cryptococcus neoformans* in AIDS | ◐ | ◐ |
| nejm-cpc-5-2026 | Reninoma (juxtaglomerular cell tumor) | ✗ | ✗ |
| nejm-cpc-6-2026 | Eosinophilic granulomatosis with polyangiitis (EGPA) | ✓ | ✓ |
| nejm-cpc-7-2026 | Periprosthetic joint infection, *M. bovis* BCG | ✓ | ◐ |
| nejm-cpc-8-2026 | Fungal (*Aspergillus flavus*) endocarditis + aortic-root abscess | ✓ | ✗ |
| nejm-cpc-9-2026 | Non-islet-cell tumor hypoglycemia (big IGF-II) | ✓ | ✗ |
| nejm-cpc-10-2026 | Esophageal-pericardial fistula after AF ablation | ◐ | ◐ |
| nejm-cpc-11-2026 | Narcolepsy type 1 (with cataplexy) | ✓ | ✓ |
| nejm-cpc-13-2026 | Waldenström macroglobulinemia + type II cryoglobulinemic vasculitis | ◐ | ◐ |
| nejm-cpc-14-2026 | SLE / inflammatory-myopathy overlap syndrome | ✗ | ✗ |

**Tally.** Quorum: 5 full (6, 7, 8, 9, 11) → 41.7%; +4 partial (3, 4, 10, 13) →
9/12 = 75.0%. Baseline: 2 full (6, 11) → 16.7%; +5 partial (3, 4, 7, 10, 13) →
7/12 = 58.3%.

**Where deliberation helped.** The three exact-match cases Quorum won and the
baseline missed (7 periprosthetic *M. bovis* BCG, 8 *Aspergillus* endocarditis,
9 NICTH/Doege-Potter) are all cases where the specific etiology only emerges from
multi-turn evidence pursuit — the panel queried the Gatekeeper for additional
findings (cultures, organism-specific markers) before committing, whereas the
single call settled on the correct disease *category* but the wrong specific
entity.

## Limitations

- **n = 12 is small.** A single case swing is ~8 points, so the 5-vs-2 exact-match
  gap rests on three cases. This is a directional holdout result, not a
  large-sample benchmark.
- **LLM-judge grading** introduces grader variance; verdicts and rationales are
  committed per case so they can be re-graded.
- **Reference points are not head-to-head.** MAI-DxO's 85.5% is on a different,
  larger set with a different harness; it is context, not a comparison.

## Reproducing this

The case *bodies* are license-restricted and not distributed, so this exact run
cannot be reproduced from a clean clone without supplying the holdout cases. The
committed artifacts let a reviewer **inspect and re-grade** every committed
diagnosis:

```bash
# Per-case judge verdicts (both arms)
cat data/results/v3-holdout-sc-voted/judge_results.json
cat data/results/v3-holdout-baseline-voted/judge_results.json

# Append-only audit trail for one Quorum case (final diagnosis, posteriors, cost)
cat data/results/v3-holdout-sc-voted/nejm-cpc-8-2026.audit.jsonl
```
