# Knowing When to Abstain: Medical LLMs Under Clinical Uncertainty (MedAbstain)

**Authors:** Sravanthi Machcha, Sushrita Yerra, Sahil Gupta, et al.
**Year:** 2026
**Venue:** EACL 2026 (Main Conference)
**Link:** https://arxiv.org/abs/2601.12471
**arXiv ID / DOI:** 2601.12471

## TL;DR
MedAbstain is a benchmark and evaluation protocol for measuring whether medical LLMs decline to answer when uncertain, covering proprietary and open-source models on medical multiple-choice QA. The headline finding: even state-of-the-art high-accuracy models routinely fail to abstain when they should, and giving them an explicit abstain option induces more calibrated uncertainty and safer behavior; in contrast, scaling model size or adding advanced prompting yields minimal abstention gains. The authors argue explicit abstention mechanisms are required for trustworthy deployment in high-stakes medical settings.

## Key claim
Explicit abstain-option prompting is the single intervention that meaningfully improves safe abstention; model size and prompting tricks alone do not — abstention is a calibration problem, not a capability problem.

## Relevance to Quorum
This is the calibration methodology Quorum should adopt. The `confidence` field on `FinalVerdict` (see `backend/src/quorum/orchestrator/schemas.py`) is currently a scalar reported by the Consensus agent; MedAbstain's framing suggests this should ultimately be conformal-calibrated against a held-out NEJM/MedQA split with an explicit "panel could not converge → abstain" branch in the deliberation contract. The MedAbstain protocol is also the right harness for evaluating Quorum's abstention behavior alongside accuracy, which is the part of the evaluation MAI-DxO underspecifies.

## How we cite it
- `docs/eval-methodology.md` — under "Calibration & abstention," as the evaluation harness for Quorum's confidence field.
- `research/prior_art_map.md` — under "calibration prior art."
- README §"Evaluation" — alongside MedHallu, as one of the two risk-side benchmarks we plan to report.
