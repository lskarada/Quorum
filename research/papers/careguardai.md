# CareGuardAI: Context-Aware Multi-Agent Guardrails for Clinical Safety & Hallucination Mitigation in Patient-Facing LLMs

**Authors:** Elham Nasarian, Abhilash Neog, Kwok-Leung Tsui, Niyousha HosseiniChimeh
**Year:** 2026
**Venue:** arXiv preprint (cs.CY)
**Link:** https://arxiv.org/abs/2604.26959
**arXiv ID / DOI:** 2604.26959

## TL;DR
CareGuardAI is a multi-agent guardrail system for patient-facing clinical LLMs, addressing safety risks and hallucination jointly through a risk-aware framework that scores medical appropriateness and factual accuracy before releasing a response. The pipeline uses controller agents plus dual risk evaluators and only emits output when both safety metrics clear clinical thresholds. The authors report consistent gains over GPT-4o-mini baselines on multiple medical benchmarks.

## Key claim
A context-aware multi-agent guardrail pipeline with explicit dual risk evaluators (safety + factuality) and threshold-gated release outperforms strong baselines including GPT-4o-mini on patient-facing clinical benchmarks.

## Relevance to Quorum
This is the closest published prior art to Quorum, and the citation must be careful. CareGuardAI is patient-facing safety with a guardrail-shaped multi-agent system: orthogonal but adjacent to Quorum, which is provider-facing diagnostic deliberation where the 5 agents argue toward a differential rather than gate a response. The "controller + dual risk evaluator" topology is a useful contrast for explaining why Quorum's panel is heterogeneous (Hypothesizer / Test-Chooser / Challenger / Stewardship / Consensus) rather than a homogeneous safety-gate ensemble. We should also borrow CareGuardAI's threshold-gated release pattern as a design reference for the Consensus agent's abstain branch.

## How we cite it
- `research/prior_art_map.md` — top-of-section in "multi-agent clinical systems," with explicit deliniation: CareGuardAI = patient-facing safety, MAI-DxO/Quorum = provider-facing diagnostic deliberation.
- README §"Related work" — single-line citation distinguishing Quorum's deliberation-for-diagnosis stance from CareGuardAI's gate-for-safety stance.
- `docs/architecture.md` — as the comparison topology when motivating the heterogeneous-agent design choice.
