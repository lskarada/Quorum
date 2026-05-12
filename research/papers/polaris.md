# Polaris: A Safety-focused LLM Constellation Architecture for Healthcare

**Authors:** Subhabrata Mukherjee, Paul Gamble, Markel Sanz Ausin, Neel Kant, Kriti Aggarwal, Neha Manjunath, Debajyoti Datta, Zhengliang Liu, Jiayuan Ding, Sophia Busacca, Cezanne Bianco, Swapnil Sharma, Rae Lasko, Michelle Voisard, Sanchay Harneja, Darya Filippova, Gerry Meixiong, Kevin Cha, Amir Youssefi, Meyhaa Buvanesh, Howard Weingram, Sebastian Bierman-Lytle, Harpreet Singh Mangat, Kim Parikh, Saad Godil, Alex Miller (Hippocratic AI)
**Year:** 2024
**Venue:** arXiv preprint (cs.AI, cs.CL)
**Link:** https://arxiv.org/abs/2403.13313
**arXiv ID / DOI:** arXiv:2403.13313

## TL;DR
Hippocratic AI's Polaris is a ~1T-parameter constellation of cooperative multi-billion-parameter LLMs designed for real-time patient-facing voice conversations in healthcare. A stateful primary agent drives the conversation while specialist support agents handle medication, labs, checklist, safety, and EHR-grounding subtasks. In evaluation with 1,100+ nurses and 130 physicians it performs on par with human nurses on medical safety, clinical readiness, conversational quality, and bedside manner.

## Key claim
A specialized multi-agent constellation of cooperating LLMs can match human nurses on safety and conversational quality in patient-facing healthcare voice interactions.

## Relevance to Quorum
Polaris sits in an explicitly different lane from Quorum: patient-facing voice with a proprietary trillion-parameter model, optimized for conversational rapport and operational nurse-style tasks. Quorum is provider-facing diagnostic deliberation behind an MCP boundary, callable by any frontier LLM, optimized for differential-diagnosis accuracy and audit transparency rather than empathy. Citing Polaris establishes that multi-agent constellations are an active design idiom in medical AI, while making clear Quorum's lane (debate-style diagnostic reasoning, open-source, model-agnostic) is non-overlapping.

## How we cite it
In `research/prior_art_map.md` (already drafted) and in any Related Work section of the project write-up; specifically the "we are aware of multi-agent medical AI like Polaris but operate in a different lane" framing.
