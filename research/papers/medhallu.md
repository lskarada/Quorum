# MedHallu: A Comprehensive Benchmark for Detecting Medical Hallucinations in Large Language Models

**Authors:** Shrey Pandit, Jiawei Xu, Junyuan Hong, et al.
**Year:** 2025
**Venue:** arXiv preprint (cs.CL)
**Link:** https://arxiv.org/abs/2502.14302
**arXiv ID / DOI:** 2502.14302

## TL;DR
MedHallu is a 10,000-pair medical hallucination-detection benchmark derived from PubMedQA, with systematically constructed hallucinated answers stratified by difficulty. Even strong models (GPT-4o, Llama-3.1) struggle on the "hard" split, with the best F1 around 0.625; injecting medical domain knowledge and an explicit "uncertain" response option yields up to 38% relative improvement. The hardest hallucinations are the ones semantically closest to correct answers.

## Key claim
Best-in-class F1 on MedHallu's hard split is ≈0.625 — the headline metric showing frontier models are not yet competent at detecting plausible-sounding medical falsehoods.

## Relevance to Quorum
Risk-side benchmark. Quorum's accuracy claim against MAI-DxO is meaningless without a paired hallucination-rate claim — otherwise we cannot rule out that any deliberation gain is being purchased with more confident confabulation. MedHallu is the benchmark we should run Quorum's `FinalVerdict.differential` against to show the multi-agent deliberation does not amplify plausible-but-wrong content. The "hard split" framing also informs Challenger-agent design: that agent should be specifically rewarded for catching answers semantically close to but not identical to the supported claim.

## How we cite it
- README §"Evaluation" — paired with the headline NEJM accuracy number, as the explicit anti-confabulation metric.
- `docs/eval-methodology.md` — under "Risk-side metrics," as the second benchmark column alongside MedAbstain.
- `research/prior_art_map.md` — under "medical hallucination benchmarks."
