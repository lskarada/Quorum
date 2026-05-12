# Mitigating LLM Hallucinations via Conformal Abstention

**Authors:** Yasin Abbasi Yadkori, Ilja Kuzborskij, David Stutz, András György, Adam Fisch, Arnaud Doucet, Iuliya Beloshapka, Wei-Hung Weng, Yao-Yuan Yang, Csaba Szepesvári, Ali Taylan Cemgil, Nenad Tomasev (Google DeepMind)
**Year:** 2024
**Venue:** arXiv preprint (cs.LG)
**Link:** https://arxiv.org/abs/2405.01563
**arXiv ID / DOI:** arXiv:2405.01563

## TL;DR
The authors apply conformal prediction to LLM abstention: the model samples multiple responses, scores their pairwise self-consistency, and abstains when the calibration set indicates the answer is unlikely to be reliable. The framework provides a distribution-free, theoretically grounded bound on the hallucination rate at a chosen confidence level. On closed-book QA the method bounds hallucinations while abstaining less often than baselines built on raw probability scores or logit-derived uncertainty.

## Key claim
A self-consistency similarity score, calibrated with conformal prediction, gives an LLM a principled abstention rule with a provable hallucination-rate bound and lower abstention than naive likelihood baselines.

## Relevance to Quorum
Quorum's `FinalVerdict.confidence` field and the abstention pathway in the consensus stage need a defensible calibration story rather than a soft-maxed self-reported number. This paper is the methodological reference for the "sample-then-conformalize" approach: at v1, Quorum's confidence is heuristic, but a v2 path is to (a) sample multiple panel runs per case, (b) compute self-consistency over the differential top-1 (and ranked list), (c) calibrate an abstention threshold against held-out NEJM CPC / MedQA cases using conformal prediction so the system can refuse high-stakes ambiguous cases with a guaranteed error rate. It also doubles as the citation backing the safety claim that Quorum's abstentions are not vibes.

## How we cite it
In `docs/eval_methodology.md` (calibration section) and in any safety/abstention discussion in the project write-up. Pair it with MedAbstain for the medical-domain instantiation.
