# Sequential Diagnosis with Language Models (MAI-DxO)

**Authors:** Harsha Nori, Mayank Daswani, Christopher Kelly, et al. (15 total authors)
**Year:** 2025
**Venue:** arXiv (Microsoft)
**Link:** https://arxiv.org/abs/2506.22405
**arXiv ID / DOI:** arXiv:2506.22405

## TL;DR
Microsoft introduces the **MAI Diagnostic Orchestrator (MAI-DxO)**, a model-agnostic multi-agent system that simulates a panel of physicians, proposes differential diagnoses, and strategically selects cost-effective tests. Evaluated on a new Sequential Diagnosis Benchmark of 304 NEJM clinicopathological conference (CPC) cases transformed into stepwise diagnostic encounters, MAI-DxO reaches 80% diagnostic accuracy in its default configuration and 85.5% when configured for maximum performance — roughly four times the ~20% average of generalist physicians on the same cases.

## Key claim
MAI-DxO achieves **85.5% diagnostic accuracy on 304 NEJM CPC cases** while also cutting diagnostic costs by ~20% vs. physicians and ~70% vs. off-the-shelf o3, via orchestrated multi-agent deliberation and test selection.

## Relevance to Quorum
This is **the** paper Quorum reproduces. Quorum is the open-source MCP-and-web analogue of MAI-DxO: same five-persona panel framing, same chain-of-debate metaphor, same target benchmark (NEJM CPC sequential diagnosis). MAI-DxO is closed-source and tied to Microsoft's stack; Quorum is the open lane. Every architectural choice in `backend/src/quorum/orchestrator/` — panel composition, deliberation loop, gatekeeper-style information reveal — traces back to this paper, and our eval harness is explicitly designed to be runnable against the same 304-case substrate.

## How we cite it
Cited as the **primary prior art** in `README.md` (project framing — "open reproduction of Microsoft's MAI-DxO"), in `research/prior_art_map.md` as the anchor of the orchestrator lane, in `docs/eval_methodology.md` as the source of the 85.5% / 80% accuracy targets Quorum reports against, and in the CS153 demo script as the headline comparator.
