# MedSafetyBench: Evaluating and Improving the Medical Safety of Large Language Models

**Authors:** Tessa Han, Aounon Kumar, Chirag Agarwal, Himabindu Lakkaraju
**Year:** 2024
**Venue:** NeurIPS 2024 Datasets and Benchmarks Track (arXiv:2403.03744)
**Link:** https://arxiv.org/abs/2403.03744
**arXiv ID / DOI:** 2403.03744

## TL;DR
MedSafetyBench is the first medical-safety benchmark grounded in the AMA's Principles of Medical Ethics, paired with a fine-tuning protocol that improves model safety without degrading medical-task performance. Per the brief, the dataset contains 900 harmful and 900 safe medical requests. The headline finding is that publicly available medical LLMs do not meet standards of medical safety as encoded in the benchmark, and that targeted fine-tuning on MedSafetyBench improves safety while preserving capability.

## Key claim
Existing publicly available medical LLMs fail the AMA-grounded medical-safety bar, and fine-tuning on MedSafetyBench raises safety scores without hurting medical performance — establishing a deployable safety/utility tradeoff curve.

## Relevance to Quorum
Safety baseline for any clinical deployment claim. Quorum is provider-facing diagnostic deliberation, so harmful-request behavior is less central than for a patient-facing chatbot — but if Quorum's MCP surface is ever exposed to non-physician users, MedSafetyBench is the bar it must clear before any real clinical use. The benchmark is also useful as a sanity check that prompt-engineered deliberation does not regress the underlying provider models' refusal behavior on the 900 harmful requests.

## How we cite it
- README §"Safety & limitations" — as the safety bar Quorum has not yet been evaluated against, with an explicit "not yet measured" note in the pre-alpha disclosure.
- `docs/eval-methodology.md` — under "Future work / out of scope for v0.1," documenting what we would need to measure before any clinical pilot.
- `research/prior_art_map.md` — under "medical-safety benchmarks."
