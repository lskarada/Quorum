# MedAgentBench: A Realistic Virtual EHR Environment to Benchmark Medical LLM Agents

**Authors:** Yixing Jiang, Kameron C. Black, Gloria Geng, et al.
**Year:** 2025
**Venue:** arXiv (Stanford ML Group)
**Link:** https://arxiv.org/abs/2501.14654
**arXiv ID / DOI:** arXiv:2501.14654

## TL;DR
**MedAgentBench** is an evaluation suite for medical LLM agents grounded in a FHIR-compliant interactive EHR environment. It contains **300 clinically-derived tasks across 10 categories**, with patient profiles for 100 individuals comprising 700,000+ data elements. On the leaderboard reported in the paper, Claude 3.5 Sonnet v2 tops out at a **69.67% success rate**, with substantial variation across task categories indicating an unsaturated benchmark.

## Key claim
A FHIR-grounded, 300-task agentic benchmark that **frontier models do not saturate** (top score ~69.67%), establishing operational-EHR tasks as a distinct, harder lane than vignette QA.

## Relevance to Quorum
MedAgentBench is the **alternative substrate for Quorum v2**. Where SDBench tests deliberative diagnosis on synthetic CPC vignettes, MedAgentBench tests operational tasks against a real FHIR API — chart review, order placement, data retrieval. A natural Quorum extension is to expose the panel deliberation over an MCP tool surface that wraps MedAgentBench's FHIR environment, letting the same orchestrator handle both diagnostic and operational lanes. Stanford-aligned (same institution as CS153), which makes citation politically clean.

## How we cite it
Cited in `research/prior_art_map.md` as the **operational/EHR-agent lane** (vs. Quorum's deliberation lane), in `docs/architecture.md` as motivation for the MCP tool-surface design (so a future adapter can plug into FHIR), and in `README.md` future-work section as the v2 evaluation target.
