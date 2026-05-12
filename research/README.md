# Quorum Research Knowledge Base

Annotated bibliography for the Quorum project (Stanford CS153, Spring 2026). Each entry under `papers/` is a one-page summary; the two synthesis docs (`prior_art_map.md`, `fda_2026_cds_guidance.md`) explain how the pieces relate to what Quorum is building.

## Papers by category

### Diagnostic orchestrators
- **`papers/mai_dxo.md`** — Microsoft's MAI-DxO; the closed-source multi-agent diagnostic orchestrator Quorum reproduces.
- **`papers/sequential_diagnosis_benchmark.md`** — Sequential-diagnosis evaluation methodology used by MAI-DxO.
- **`papers/amie.md`** — Google's conversational diagnostic agent for patient interviews.
- **`papers/polaris.md`** — Hippocratic AI's ~1T-parameter constellation for patient-facing voice.
- **`papers/dxgpt.md`** — Microsoft's rare-disease diagnostic companion to MAI-DxO.

### Medical agent benchmarks
- **`papers/medagentbench.md`** — Stanford's FHIR-grounded clinical agent task benchmark.
- **`papers/medhelm.md`** — Stanford's HELM-style medical evaluation harness.
- **`papers/medagents_bench.md`** — Hard-subset benchmark for thinking models and agent frameworks on medical reasoning.

### Hallucination and safety
- **`papers/check.md`** — Hallucination detection framework for clinical LLM outputs.
- **`papers/medhallu.md`** — Medical-domain hallucination benchmark.
- **`papers/medsafetybench.md`** — Safety baseline for medical LLMs.
- **`papers/careguardai.md`** — Multi-agent safety gating for patient-facing clinical AI (Apr 2026).

### Calibration and abstention
- **`papers/medabstain.md`** — Abstention methods for medical question answering.
- **`papers/conformal_abstention_yadkori.md`** — Yadkori et al. (DeepMind) foundational conformal abstention paper.

## Synthesis

- **`prior_art_map.md`** — where Quorum sits relative to MAI-DxO, MedAgentBench, AMIE, Polaris, and CareGuardAI, plus the methodological building blocks (CHECK, MedAbstain, conformal abstention).
- **`fda_2026_cds_guidance.md`** — non-binding analysis of the FDA Jan 2026 Clinical Decision Support guidance and where Quorum sits inside the non-device CDS lane.
