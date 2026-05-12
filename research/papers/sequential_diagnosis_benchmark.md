# Sequential Diagnosis Benchmark (SDBench)

**Authors:** Harsha Nori, Mayank Daswani, Christopher Kelly, et al. (15 total authors)
**Year:** 2025
**Venue:** arXiv (Microsoft) — same paper as MAI-DxO
**Link:** https://arxiv.org/abs/2506.22405
**arXiv ID / DOI:** arXiv:2506.22405

## TL;DR
The **Sequential Diagnosis Benchmark (SDBench)** is the evaluation artifact introduced alongside MAI-DxO in the same paper. It converts 304 NEJM clinicopathological conference (CPC) cases into stepwise diagnostic encounters in which a solver — physician or AI system — must iteratively request case details and propose diagnoses based on revealed findings, rather than seeing the full vignette up front. A gatekeeper-style mediator controls what information is disclosed in response to each query.

## Key claim
SDBench operationalizes diagnosis as a **sequential, information-acquisition task over 304 NEJM CPC cases**, replacing static one-shot vignette QA with an interactive protocol that exposes both accuracy and test-selection cost.

## Relevance to Quorum
SDBench is the **target benchmark** for Quorum's evaluation harness. Quorum's `data/cases/nejm/` schema and the planned eval-runner in `backend/src/quorum/eval/` are designed against this protocol: stepwise reveal, query-driven information gain, accuracy and cost both scored. Treating SDBench as a sibling artifact to MAI-DxO is important: even if a team cannot match MAI-DxO's orchestrator, they can still report meaningful numbers against the benchmark, which is the comparison Quorum will lean on for its CS153 deliverable.

## How we cite it
Cited in `docs/eval_methodology.md` as the canonical evaluation protocol Quorum targets, in `data/cases/nejm/README.md` as the schema source for case JSON, and in the README §8 (acceptance criteria) as the benchmark against which Quorum's headline accuracy/cost numbers should be reported. Cross-referenced with `mai_dxo.md` in `research/prior_art_map.md`.
