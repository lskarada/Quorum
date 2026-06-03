# Prior Art Map

## Where Quorum sits

Quorum is a multi-agent diagnostic orchestrator, callable as an MCP server,
with a live web UI. It is closest to MAI-DxO architecturally and to MedAgentBench
methodologically, with safety/calibration borrowing from CHECK and MedAbstain.

## What's adjacent and what's different

### MAI-DxO (Microsoft, 2025)
- **Same:** Multi-agent diagnostic orchestrator with chain-of-debate.
- **Different:** Closed-source. We are the open reproduction with MCP packaging.

### CareGuardAI (Apr 2026)
- **Same:** Multi-agent safety in clinical context.
- **Different:** Patient-facing response gating; we are provider-facing diagnostic reasoning.

### MedAgentBench (Stanford, 2025)
- **Same:** FHIR-grounded clinical agent evaluation.
- **Different:** Tasks are operational ("find the A1c"); we evaluate diagnostic accuracy.
  We can use MedAgentBench's FHIR environment as a v2 substrate.

### Polaris (Hippocratic, 2024)
- **Same:** Multi-agent constellation.
- **Different:** Patient-facing voice with proprietary 1T+ parameter model;
  we are an MCP service callable by any frontier LLM.

### AMIE (Google, 2024)
- **Same:** Diagnostic reasoning agent.
- **Different:** Conversational with patients; we orchestrate panels with structured output.

### MedHELM (Stanford, 2025)
- **Same:** Stanford ecosystem evaluation.
- **Different:** Q&A leaderboard infrastructure; we run a derived diagnostic eval.

## Methodological building blocks we cite

- **Calibration & abstention:** MedAbstain, Yadkori conformal abstention.
- **Hallucination measurement:** CHECK, MedHallu.
- **Safety baseline:** MedSafetyBench.

## What Quorum claims that nothing in this list claims

1. Open-source diagnostic orchestrator at MAI-DxO's chain-of-debate scope.
2. MCP-native — any agent can invoke diagnostic deliberation as a tool call.
3. Live web UI streaming the debate (research artifact for transparency studies).
4. Calibrated posteriors — Hypothesis emits per-diagnosis probabilities scored
   for honesty with Brier + ECE on a held-out set, not just a top-pick label.
   The closed MAI-DxO reports accuracy, not calibration.
5. Append-only audit trails — every agent message, Gatekeeper query, and
   SafetyChecker verdict is logged for after-the-fact inspection, which the
   non-device CDS posture (see `fda_2026_cds_guidance.md`) depends on.
