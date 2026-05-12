# Towards Conversational Diagnostic AI (AMIE)

**Authors:** Tao Tu, Anil Palepu, Mike Schaekermann, et al. (23 additional authors)
**Year:** 2024
**Venue:** arXiv (Google Research / Google DeepMind)
**Link:** https://arxiv.org/abs/2401.05654
**arXiv ID / DOI:** arXiv:2401.05654

## TL;DR
**AMIE (Articulate Medical Intelligence Explorer)** is an LLM-based diagnostic conversational agent trained with self-play simulation and automated feedback across diverse diseases and specialties. It was evaluated in a randomized, double-blind crossover OSCE-style study of text-based consultations with validated patient actors across 149 case scenarios from Canada, the UK, and India, compared against 20 primary care physicians. AMIE matched or exceeded the PCPs on 28 of 32 specialist-rated axes and 24 of 26 patient-actor-rated axes.

## Key claim
A purpose-built diagnostic dialogue LLM **outperforms primary care physicians** on the majority of evaluation axes in OSCE-style text consultations, demonstrating that diagnostic competence is achievable in a single-agent conversational frame given sufficient training and evaluation rigor.

## Relevance to Quorum
AMIE is **adjacent prior art**, not a direct comparator. It occupies the patient-facing single-agent conversational lane, whereas Quorum occupies the clinician-facing multi-agent deliberation lane (same lane as MAI-DxO). Citing AMIE matters for two reasons: (1) it establishes that LLM-as-clinician is a credible research direction with rigorous OSCE-style evaluation precedent, and (2) it lets Quorum cleanly differentiate its contribution — multi-agent chain-of-debate over a static case, not single-agent live conversation with a patient.

## How we cite it
Cited in `research/prior_art_map.md` to mark the boundary between the conversational-diagnostic lane (AMIE, Google) and the orchestrated-deliberation lane (MAI-DxO, Quorum), and in `docs/architecture.md`'s related-work section to acknowledge OSCE-style evaluation as a methodological influence on how we frame qualitative readouts.
