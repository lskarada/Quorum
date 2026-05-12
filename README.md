# Quorum

> **Open-source diagnostic deliberation for clinical AI agents.**

Quorum is a multi-agent diagnostic orchestrator, callable as an MCP server, that produces calibrated differential diagnoses with cited reasoning. It's an open reproduction of the chain-of-debate pattern from Microsoft's MAI-DxO ([arXiv 2506.22405](https://arxiv.org/abs/2506.22405)), packaged so any clinical AI agent can call it as a tool.

**Why this exists.** Microsoft's MAI-DxO achieved 85.5% on the 304-case NEJM CPC benchmark — but it's closed-source and unavailable to the community. Quorum is the open version, MCP-native, with a live web UI that streams the agent debate in real time.

## How it works

Five specialist agents deliberate on a case:
- **Dr. Hypothesis** — proposes a ranked differential
- **Dr. Test-Chooser** — selects the most informative next test
- **Dr. Challenger** — attacks the leading hypothesis
- **Dr. Stewardship** — enforces cost-aware reasoning
- **Dr. Checklist** — verifies internal consistency

The orchestrator iterates until consensus (or a budget cap). Output is a ranked differential, recommended next test, calibrated confidence, and primary-source citations.

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
