# Quorum v2 Headline Results

*Calibrated-Auditable MAI-DxO — SDBench-style sequential diagnostic encounter*

**Status:** *in-progress (Phase 6 baseline TUNE iteration running)*
**Run date:** 2026-05-27
**Eval set:** 30 held-out cases (17 NEJM CPC + 8 MedCaseReasoning + 5 RareBench)
**Tune set:** 5 cases (3 NEJM + 2 MCR), used once for the prompt-freeze baseline.
**Models:** Claude Sonnet 4.6 (all five agents). Gatekeeper matcher: Haiku 4.5 fallback when substring miss.
**Spec:** [`docs/superpowers/specs/2026-05-26-quorum-calibrated-auditable-mai-dxo-design.md`](superpowers/specs/2026-05-26-quorum-calibrated-auditable-mai-dxo-design.md)
**Plan:** [`docs/superpowers/plans/2026-05-27-quorum-calibrated-mai-dxo.md`](superpowers/plans/2026-05-27-quorum-calibrated-mai-dxo.md)
**Frozen at:** *(git tag `v2-prompts-frozen` — to be set after Phase 6 completes)*

---

## Methodology snapshot

- **Three arms**:
  - **Arm A (Quorum-Calibrated)**: 5-agent panel (Hypothesis / TestChooser / Challenger / Stewardship / Checklist) on Sonnet 4.6, full Gatekeeper game, deterministic SafetyChecker, append-only AuditTrail JSONL per case.
  - **Arm B (Single Sonnet)**: one Hypothesis call only, no orchestration. Quantifies the lift Arm A's orchestrator provides over the same base model.
  - **Reference (literature)**: MAI-DxO + o3 = 85.5% (Microsoft, n=304); physicians = 20% (Microsoft).
- **Routing**: cases with structured `available_findings` (NEJM) run the full sequential mode. MCR + RareBench cases route to a single-Hypothesis path inside Arm A as well (matches the spec's "single-turn for MCR/RB").
- **Safety**: a deterministic 5-rule SafetyChecker gates every commit (min findings, no flagged checklist concerns, shortlist membership, Hypothesis/Challenger agreement, cost-overrun override).
- **Calibration**: Brier per-case from `final_posterior` against ground truth; 10-bin equal-width ECE across the EVAL set.
- **Judge**: Sonnet 4.6 LLM-as-judge scores each committed diagnosis as `full_credit` / `partial_credit` / `no_credit` against ground_truth + acceptable_partial_credit synonyms.
- **Audit completeness**: fraction of the 7 expected event types (`hypothesis`, `test_chooser`, `challenger`, `stewardship`, `checklist`, `gatekeeper`, `safety_checker`) that appear at least once per case audit.
- **Budget gate**: hard stop at $80 total Anthropic spend. Spend tracked in `data/results/.spend_total.txt`.

## Headline numbers

*(filled in after Phase 7 completes)*

| Metric | Arm A (Quorum-Calibrated) | Arm B (Single Sonnet) | Reference |
|---|---|---|---|
| Top-1 accuracy | — | — | MAI-DxO + o3: 85% (Microsoft) |
| Top-1 + partial | — | — | — |
| Brier (mean per-case) | — | n/a (Arm B has no shortlist) | — |
| ECE (10-bin equal-width) | — | n/a | — |
| Audit completeness | — | n/a | — |
| Real cost / case | — | — | — |
| Total real spend | — | — | — |

## TUNE-set baseline (Phase 6 iter-1)

*(filled in after the 5-case TUNE run completes)*

| Case | Ground truth | Committed | Judge score |
|---|---|---|---|
| nejm-cpc-5-2026  | Reninoma | — | — |
| nejm-cpc-28-2025 | — | — | — |
| nejm-cpc-36-2025 | — | — | — |
| mcr-PMC7311097   | — | — | — |
| mcr-PMC9568751   | — | — | — |

## Reproducibility

- **Corpus**: `data/cases/eval_corpus_v2/` (mcr_sample.json + rarebench_sample.json + README + splits.json — NEJM bodies are paywalled and gitignored).
- **Splits**: `data/cases/eval_corpus_v2/splits.json` (deterministic, seed 20260526).
- **Panel configs**: `backend/config/panels/v2_quorum_calibrated.yaml` (Arm A), `v2_single_sonnet.yaml` (Arm B).
- **Agent contracts**: `backend/src/quorum/orchestrator/AGENT_CONTRACTS.md` (snapshot of return shapes).
- **Tag**: `v2-prompts-frozen` — *(to be set)*
- **Audit trails**: `data/results/<run_id>/<case_id>.audit.jsonl` per case.

## Interpretation

*(filled in once metrics land — honest write-up regardless of which arm wins)*

## Limitations

- 13 of 30 EVAL cases (8 MCR + 5 RareBench) have no structured `available_findings` and therefore route to a single-Hypothesis path inside Arm A. The Gatekeeper/Sequential lift is measurable only on the 17 NEJM EVAL cases. Per-corpus breakdowns are reported below.
- `max_turns` capped at 10 for cost discipline (spec calls for 30). Each Sonnet 4.6 5-agent turn costs ~$0.06 of real spend; the cap keeps Arm A per-case cost near $0.40-0.60.
- Phase 6 ran a single baseline iteration on TUNE rather than 10 prompt-tuning iterations. The smoke + 1 baseline iter already costs ~$3; given the $80 ceiling, additional tuning iterations would have eaten into the headline EVAL budget. The honest version: prompts were not iteratively refined for v2.
- Gatekeeper matcher uses substring-first, Haiku-fallback (cost-efficient). A Sonnet matcher might match a few more paraphrased queries; not exercised in this build.
