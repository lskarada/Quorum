# Quorum

> **Calibrated, auditable diagnostic deliberation for clinical AI agents.**

Quorum is the open-source reproduction of cost-aware sequential diagnostic deliberation — the architectural shape of Microsoft's MAI-DxO ([arXiv 2506.22405](https://arxiv.org/abs/2506.22405)) — with two structural additions Microsoft's closed system doesn't ship: **honest calibrated posteriors** (Brier + ECE on Hypothesis's per-diagnosis probabilities) and **append-only AuditTrails** of every agent message, Gatekeeper query, and SafetyChecker verdict. MCP-native, MIT-licensed, runs on Claude Sonnet 4.6.

**Why this exists.** Microsoft's MAI-DxO achieved 85.5% on the 304-case NEJM CPC benchmark — but it's closed-source and unavailable to the community. Quorum is the open version: MCP-native, with a live web UI that streams the agent debate in real time, plus the Gatekeeper + Calibration + Audit layers needed for reviewers to actually inspect what the panel did.

## Headline results (v2)

See [`docs/results_v2.md`](docs/results_v2.md) for the SDBench-flavored three-arm headline (Arm A Quorum-Calibrated vs Arm B Single Sonnet vs literature reference MAI-DxO + o3) on a 30-case held-out NEJM + MedCaseReasoning + RareBench corpus.

## How it works

Five specialist agents deliberate on a case:
- **Dr. Hypothesis** — proposes a ranked differential with per-diagnosis posteriors
- **Dr. Test-Chooser** — selects the most informative next test
- **Dr. Challenger** — attacks the leading hypothesis
- **Dr. Stewardship** — enforces cost-aware reasoning
- **Dr. Checklist** — verifies internal consistency

In v2 (sequential mode), the panel queries a **Gatekeeper** module that holds the case findings and reveals them turn-by-turn (SDBench-style), tracking simulated CMS-style test cost. Every commit passes through a deterministic 5-rule **SafetyChecker** (min findings queried, no flagged contradictions, shortlist membership, Hypothesis/Challenger agreement, cost-overrun forcing). The full transcript — every agent message, Gatekeeper query/response, safety verdict — is written to an append-only **AuditTrail JSONL** that a reviewer can replay.

Output is a ranked differential with calibrated posteriors (Brier + ECE-scored on the held-out EVAL set), recommended next test, primary-source citations, and the audit trail.

## Quick start

```bash
# Install
make install

# Run the API + frontend
make dev

# Run evaluation on NEJM CPC corpus
make eval

# Run as MCP server (for use by other agents)
make mcp
```

## Status

Pre-alpha. Built for Stanford CS153 (Spring 2026). 17-day solo build. See `docs/milestone.md`.

## Citation

```bibtex
@software{quorum2026,
  title = {Quorum: Open-source diagnostic deliberation for clinical AI agents},
  year = {2026},
  url = {https://github.com/YOUR_USERNAME/quorum}
}
```

## License

MIT. See `LICENSE`.

## Related work

See `research/prior_art_map.md` for the full picture. Most directly relevant:
- MAI-DxO (Microsoft) — the closed orchestrator Quorum reproduces
- MedAgentBench (Stanford) — FHIR-grounded agent benchmark we could integrate
- CareGuardAI (Apr 2026) — the closest published multi-agent guardrails framework
- MedAbstain (Jan 2026) — conformal abstention for medical LLMs
