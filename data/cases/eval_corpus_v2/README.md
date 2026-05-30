# Eval Corpus v2 — Calibrated Sequential Diagnosis

This directory contains the **public-reproducible portion** of the v2 benchmark corpus for the
Calibrated-Auditable-Quorum (CAQ) eval pivot. Together with 20 NEJM Clinicopathological
Conference cases (pulled separately via Stanford library access), these files form the
n=35 corpus used for prompt tuning and headline evaluation.

## Files

### `mcr_sample.json` — 10 cases
- **Source**: [zou-lab/MedCaseReasoning](https://huggingface.co/datasets/zou-lab/MedCaseReasoning) (Stanford, MIT License)
- **Underlying source**: PubMed Central case reports (clinician-validated)
- **Sampling**: `random.sample(test_split, 10)` with seed=20260526 for determinism
- **Schema**: `case_id`, `source`, `corpus`, `presentation`, `ground_truth_diagnosis`, `reasoning_trace`

### `rarebench_sample.json` — 5 cases
- **Source**: [chenxz/RareBench](https://huggingface.co/datasets/chenxz/RareBench) (Apache 2.0)
- **Underlying source**: LIRICAL configuration (370 cases, 252 diseases, multi-country)
- **Sampling**: `random.sample(LIRICAL_test, 5)` with seed=20260526 for determinism
- **Translation**: HPO phenotype codes mapped to natural-language phenotype names using
  `phenotype_mapping.json`; OMIM/Orphanet disease codes mapped to disease names using
  `disease_mapping.json`. The original HPO codes are preserved alongside translated names.
- **Schema**: `case_id`, `source`, `corpus`, `presentation`, `ground_truth_diagnosis`,
  `ground_truth_code`, `all_ground_truth_codes`, `all_ground_truth_names`, `hpo_codes`, `hpo_names`

## Reproducibility

To regenerate exactly these case lists:
1. MCR: load `data/cases/mcr/all.json` (200 cases), `random.seed(20260526)`, `random.sample(cases, 10)`.
2. RareBench: download `data.zip` and `mapping/{phenotype,disease}_mapping.json` from
   the HuggingFace dataset page. Load `LIRICAL.jsonl` (370 cases), `random.seed(20260526)`,
   `random.sample(cases, 5)`.

The pull script that produced these files is in the spec doc; the seed (`20260526`) is fixed.

## NEJM Holdout

The remaining 20 cases of the n=35 corpus are NEJM CPC cases pulled via Stanford library
institutional access. They are stored under `data/cases/eval_corpus_v2/nejm_sample.json`
(see separate provenance file there). NEJM cases are NOT included in this directory because
their distribution requires institutional licensing — but the case-list (citations only)
will be published so anyone with NEJM access can reproduce.

## TUNE / EVAL split

The 35-case corpus is split into:
- **TUNE** (5 cases): for prompt iteration. Re-run freely.
- **EVAL** (30 cases): held out. Run ONCE for the headline number.

The specific split is recorded in `data/cases/eval_corpus_v2/splits.json` (see spec doc).

## DEV set (tuning corpus, held out from EVAL)

The v2.1 Accuracy-Maximization Campaign added a **26-case DEV set** so the optimization loop
has real statistical traction without ever touching the 30-case EVAL. The DEV set lives in two
files, **separate from `nejm_sample.json` / `mcr_sample.json` by design** so that a re-split of
`splits.json` can never pull a DEV case into TUNE/EVAL. Every DEV id is disjoint from
TUNE ∪ EVAL by construction.

### `dev_nejm_sample.json` — 11 NEJM CPC cases (2025 #15–25)
- **Gitignored + paywalled** — NEJM text requires institutional licensing; never committed,
  redistributed, or published. Only the citation-level manifest is shared (see the campaign
  brief `docs/overnight/2026-05-30-brief.md`).
- Rich schema: `initial_presentation`, `available_findings[]` (drives progressive Gatekeeper
  reveal), `hidden_discussant_differential`, `ground_truth_*`.

### `dev_mcr_sample.json` — 15 MedCaseReasoning/PMC cases
- **Committed** (MIT-licensed, public PMC case reports) — allowlisted in `.gitignore`.
- Schema: `case_id`, `source`, `corpus`, `presentation`, `ground_truth_diagnosis`, `reasoning_trace`.
- **Reproducibility**: minted by `backend/scripts/build_dev_augment.py` with a fixed seed
  (`20260530`). The sampler excludes every PMC id already in `splits.json` (tune+eval) **and**
  every NEJM DEV id, then `random.Random(20260530).sample(candidates, 15)` over the sorted
  remaining pool. Re-running the script reproduces the exact 15 ids byte-for-byte:
  ```bash
  python3 backend/scripts/build_dev_augment.py
  ```
