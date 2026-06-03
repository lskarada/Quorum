# Quorum

> **Calibrated, auditable diagnostic deliberation for clinical AI agents.**

Quorum is the open-source reproduction of cost-aware sequential diagnostic deliberation — the architectural shape of Microsoft's MAI-DxO ([arXiv 2506.22405](https://arxiv.org/abs/2506.22405)) — with two structural additions Microsoft's closed system doesn't ship: **honest calibrated posteriors** (Brier + ECE on Hypothesis's per-diagnosis probabilities) and **append-only AuditTrails** of every agent message, Gatekeeper query, and SafetyChecker verdict. MCP-native, MIT-licensed, runs on Claude Sonnet 4.6.

**Why this exists.** Microsoft's MAI-DxO achieved 85.5% on the 304-case NEJM CPC benchmark — but it's closed-source and unavailable to the community. Quorum is the open version: MCP-native, with a live web UI that streams the agent debate in real time, plus the Gatekeeper + Calibration + Audit layers needed for reviewers to actually inspect what the panel did.

## Headline results

**v3 — decontaminated, run-once NEJM-2026 holdout (n=12).** Each arm is the
modal vote over k=5 replicas; an LLM judge grades every committed diagnosis
against the published final diagnosis. The holdout was screened for
training-data contamination and scored a single time (no tuning on it).

| Arm | Top-1 (exact) | Top-1 or partial |
|-----|--------------|------------------|
| **Quorum** (5-agent + SafetyChecker) | **41.7%** (5/12) | **75.0%** (9/12) |
| Single-model baseline (same model, one call) | 16.7% (2/12) | 58.3% (7/12) |

Deliberation + safety gating **2.5× the exact-match rate** over the same model
called once, on cases neither arm had seen. Reference points from the
literature (not directly comparable to this 12-case holdout): the closed
MAI-DxO reaches 85.5% and unaided physicians ~20% on the broader 304-case
SDBench set ([arXiv 2506.22405](https://arxiv.org/abs/2506.22405)).

The earlier v2 three-arm SDBench-flavored headline (Arm A Quorum-Calibrated vs
Arm B Single Sonnet, with Brier + ECE calibration) lives in
[`docs/results_v2.md`](docs/results_v2.md); the v1 MedQA ablation is in
[`docs/results.md`](docs/results.md). A clinician-facing summary of all of this
— plus how the design was shaped by conversations with practicing clinicians —
is the **Evidence** page in the web demo (`/evidence`).

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

# Configure your API key (required for live deliberation + eval)
cp .env.example .env
# then edit .env and set OPENROUTER_API_KEY=...  (get one at https://openrouter.ai/keys)

# Run the API + frontend
make dev

# Run evaluation on NEJM CPC corpus
make eval

# Run as MCP server (for use by other agents)
make mcp
```

Unit tests run without a key (`cd backend && uv run pytest -q`); only live
deliberation (`make dev`) and `make eval` call the LLM and need
`OPENROUTER_API_KEY` set in `.env`.

## Status

Pre-alpha. Built for Stanford CS153 (Spring 2026). 17-day solo build. See `docs/milestone.md`.

## Clinical grounding

Quorum grew out of the author's research in the **Nigam Shah lab** at Stanford.
A survey we sent to hundreds of physicians, nurses, physician assistants, and
nurse practitioners across Stanford Health asked which uses of AI in care they
considered riskiest. **Differential diagnosis came back at the top** — and the
reason was consistent: a diagnostic suggestion that can't be *verified*. The
models would name a condition with no calibrated confidence and no trace of
where the reasoning came from, leaving the clinician unable to separate a sound
suggestion from a confident-sounding wrong one.

That finding is the design brief for Quorum. Its three load-bearing choices — a
fully auditable deliberation transcript, calibrated (not just top-pick)
posteriors, and a clinician-in-loop, non-device posture — map directly onto what
those clinicians said was missing: show the reasoning, quantify the uncertainty,
and make every claim traceable to a source. Beyond the survey, the design was
refined through follow-up conversations with practicing clinicians across
several care settings; participants are described by setting and role only, not
by name. The themes they raised line up with the published literature on trust
and adoption of clinical decision support. See the **Evidence** page in the web
demo (`/evidence`) and [`research/`](research/) for the full picture and
citations.

## AI usage & development process

This project was built with heavy use of AI coding tools — primarily **Claude
Code** (Anthropic) — for implementation, refactoring, test authoring, research
synthesis, and documentation, under continuous human direction and review by the
author. Design decisions, scope, evaluation methodology, and all
go/no-go calls were made by the author; the AI executed and accelerated that
work. The five diagnostic agents themselves run on **Claude Sonnet 4.6** (with
Haiku 4.5 used for the Gatekeeper's fallback matcher and a Sonnet judge for
scoring).

In keeping with the repo's anti-confabulation discipline: benchmark numbers in
this README and on the Evidence page are computed from committed run artifacts
under [`data/results/`](data/results/), research citations are drawn from
[`research/`](research/), and any figure not independently verified is flagged
as such. Development history is public in the git commit log and release tags
(`v2.0`, `v2.1-accuracy-final`, `v3-nejm-final`).

## Citation

```bibtex
@software{quorum2026,
  title = {Quorum: Open-source diagnostic deliberation for clinical AI agents},
  author = {Skarada, Lance},
  year = {2026},
  url = {https://github.com/lskarada/Quorum}
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
