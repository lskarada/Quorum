# MedHELM: Holistic Evaluation of Large Language Models for Medical Tasks

**Authors:** Suhana Bedi, Hejie Cui, Miguel Fuentes, et al. (80 additional co-authors)
**Year:** 2025
**Venue:** arXiv (Stanford CRFM)
**Link:** https://arxiv.org/abs/2505.23802
**arXiv ID / DOI:** arXiv:2505.23802

## TL;DR
**MedHELM** is an extensible, Stanford CRFM-led evaluation framework for medical LLMs that goes well beyond licensing-exam QA. It defines a clinician-validated taxonomy spanning **5 categories, 22 subcategories, and 121 tasks**, developed with 29 clinicians, and ships **35 benchmarks (17 existing + 18 newly formulated)** covering the full taxonomy. The paper compares nine frontier LLMs using an LLM-jury method that achieves ICC = 0.47 with clinician ratings, and finds e.g. that Claude 3.5 Sonnet matches advanced reasoning models at ~40% lower estimated compute cost.

## Key claim
A **clinician-validated, 121-task / 35-benchmark taxonomy** demonstrates that medical LLM capability is uneven across categories — strong on note generation and patient education, weaker on clinical decision support and administrative workflow — and that LLM-jury evaluation can stand in for clinician scoring with moderate agreement.

## Relevance to Quorum
MedHELM is the **methodological scaffolding** Quorum should align with for its eval rigor story. It is Stanford-flavored (CRFM), aligns with the same institutional context as CS153, and provides a defensible vocabulary for talking about Quorum's eval beyond a single accuracy number — task taxonomies, LLM-jury scoring, cost-vs-performance tradeoffs. Quorum's `docs/eval_methodology.md` can borrow the LLM-jury framing for qualitative deliberation-quality scoring, and the taxonomy categorization for positioning what Quorum measures (CDS lane) vs. what it explicitly does not (note generation, patient comms).

## How we cite it
Cited in `docs/eval_methodology.md` as the methodological reference for taxonomy-based evaluation and LLM-jury scoring, in `research/prior_art_map.md` as the Stanford-CRFM evaluation infrastructure lane, and in the CS153 milestone writeup to anchor Quorum's eval philosophy in established Stanford rigor rather than ad-hoc accuracy reporting.
