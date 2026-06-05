# Quorum

> **Calibrated, auditable diagnostic deliberation for clinical AI agents.**

Quorum is an open-source reproduction of cost-aware sequential diagnostic
deliberation — the architectural shape of Microsoft's MAI-DxO
([arXiv 2506.22405](https://arxiv.org/abs/2506.22405)) — plus two structural
additions Microsoft's closed system doesn't ship: **honest calibrated posteriors**
(Brier + ECE on per-diagnosis probabilities) and **append-only AuditTrails** of
every agent message, Gatekeeper query, and SafetyChecker verdict. MCP-native,
MIT-licensed, five Claude Sonnet 4.6 agents, with a live web UI that streams the
debate in real time.

This README is organized around the five things a reader (or grader) should be
able to check: the **problem**, what was **built**, the **evidence**, how to
**run and reproduce** it, and an honest account of **process and AI usage**.

---

## Problem & insight

Microsoft's MAI-DxO reached 85.5% on the 304-case NEJM CPC benchmark — a striking
result for sequential, multi-agent diagnosis — but it is **closed-source and
unavailable** to the community, and it ships no way to inspect *why* the panel
committed to a diagnosis. That second gap is the one clinicians care about: a
diagnostic suggestion is only usable if it can be *verified*.

Quorum is the open version, and it is opinionated about the missing piece. On top
of reproducing the deliberation architecture, it adds the three things a clinician
needs to trust (or reject) a suggestion: **show the reasoning** (a replayable
deliberation transcript), **quantify the uncertainty** (calibrated posteriors, not
a single unqualified pick), and **make every claim traceable** (an append-only
audit trail and primary-source citations). It is positioned deliberately as
**non-device, clinician-in-loop decision support** — see
[`research/fda_2026_cds_guidance.md`](research/fda_2026_cds_guidance.md) and the
`/regulatory` page in the demo.

---

## Execution — what was built

Five specialist agents deliberate on a case, all running on **Claude Sonnet 4.6**:

- **Dr. Hypothesis** — proposes a ranked differential with per-diagnosis posteriors
- **Dr. Test-Chooser** — selects the most informative next test
- **Dr. Challenger** — attacks the leading hypothesis
- **Dr. Stewardship** — enforces cost-aware reasoning
- **Dr. Checklist** — verifies internal consistency

In sequential mode the panel queries a **Gatekeeper** that holds the case findings
and reveals them turn-by-turn (SDBench-style), tracking simulated CMS-style test
cost. Every commit passes a deterministic 5-rule **SafetyChecker** (cost-overrun
forcing, minimum findings queried, no flagged contradictions, shortlist
membership, Hypothesis/Challenger agreement —
[`backend/src/quorum/orchestrator/safety.py`](backend/src/quorum/orchestrator/safety.py)).
The full transcript — every agent message, Gatekeeper query/response, and safety
verdict — is written to an append-only **AuditTrail JSONL** a reviewer can replay.
Output is a ranked differential with calibrated posteriors, a recommended next
test, primary-source citations, and the audit trail.

Every agent and the system as a whole are designed to **meticulously follow the
FDA's guidelines on clinical decision support (CDS) software**: Quorum surfaces its
reasoning, sources, and uncertainty so a clinician independently reviews the basis
of each recommendation rather than relying on it, keeping the system in the
non-device CDS lane by design. The full mapping to each FDA criterion is documented
in [`research/fda_2026_cds_guidance.md`](research/fda_2026_cds_guidance.md) and
summarized on the [`/regulatory`](frontend/src/routes/Regulatory.tsx) page of the
web demo.

This is a real, working artifact, not scaffolding: a multi-vendor LLM client,
YAML-configurable panels, a side-by-side comparison runner, SSE streaming to the
web UI, a self-consistency voting harness, an MCP stdio server, and an eval
pipeline with McNemar / Wilcoxon / bootstrap statistics. The backend ships **262
unit tests** that pass without any API key.

---

## Evaluation & evidence

**v3 — decontaminated, run-once NEJM-2026 holdout (n=12).** Each arm is the modal
vote over `k=5` replicas; an LLM judge grades every committed diagnosis against the
published final diagnosis. The holdout was screened for training-data contamination
and scored a single time (no tuning on it).

**Why only 12 cases?** The set is intentionally small because it is bounded by
recency, not by effort: these are the most recent NEJM cases published *after* the
training-data cutoff of every LLM in the panel. Restricting to post-cutoff cases is
what guarantees no arm could have memorized the answer — so the n=12 ceiling is the
price of a genuinely contamination-free holdout, not a sampling shortcut. As more
post-cutoff cases publish, the holdout can grow without compromising that guarantee.

| Arm | Top-1 (exact) | Top-1 or partial |
|-----|---------------|------------------|
| **Quorum** (5-agent + SafetyChecker) | **41.7%** (5/12) | **75.0%** (9/12) |
| Single-model baseline (same model, one call) | 16.7% (2/12) | 58.3% (7/12) |

Deliberation + safety gating **2.5× the exact-match rate** over the same model
called once, on cases neither arm had seen. The full per-case table, methodology,
and limitations are in [`docs/results_v3.md`](docs/results_v3.md); the underlying
per-case judge verdicts and audit trails are committed under
[`data/results/v3-holdout-sc-voted/`](data/results/v3-holdout-sc-voted/) and
[`data/results/v3-holdout-baseline-voted/`](data/results/v3-holdout-baseline-voted/),
so a reviewer can inspect or re-grade every commitment.

We are deliberately honest about scope: **n=12 is small** (a single case swing is
~8 points), so this is a directional holdout, not a large-sample benchmark.
Reference points from the literature — the closed MAI-DxO's 85.5% and unaided
physicians' ~20% on the broader 304-case SDBench set
([arXiv 2506.22405](https://arxiv.org/abs/2506.22405)) — are context, **not**
head-to-head comparisons.

Earlier evidence is preserved and committed: the v2 two-arm SDBench-flavored
result (Arm A Quorum-Calibrated vs Arm B Single Sonnet, with Brier + ECE
calibration and full audit trails) is in [`docs/results_v2.md`](docs/results_v2.md),
and the v1 MedQA ablation is in [`docs/results.md`](docs/results.md). The
calibration (Brier/ECE) and comparison statistics are implemented in
`backend/src/quorum/` and exercised by the test suite. A clinician-facing summary
of all of this is the **Evidence** page in the web demo (`/evidence`).

---

## Running it (communication & reproducibility)

```bash
# Install backend (uv) + frontend (pnpm)
make install

# Configure your API key (required for live deliberation + eval)
cp .env.example .env
# then edit .env and set OPENROUTER_API_KEY=...  (get one at https://openrouter.ai/keys)

# Run the API (:8000) + frontend (:3000)
make dev

# Run the eval harness on the MedQA dev corpus (3 cases, ~$0.05)
make eval

# Run as an MCP server, over stdio (for use by other agents)
make mcp
```

Notes for reproducibility:

- **Unit tests run without a key:** `cd backend && uv run pytest -q` (262 tests).
  Only `make dev` and `make eval` call the LLM and need `OPENROUTER_API_KEY`.
- **Eval needs local case data.** NEJM CPC and MedQA case *bodies* are
  license-restricted and are **not** distributed in this repo, so `make eval`
  expects you to supply case JSON under `data/cases/<corpus>/` — see
  [`data/cases/eval_corpus_v2/README.md`](data/cases/eval_corpus_v2/README.md) for
  the schema and corpus layout. The eval CLI (`quorum-eval run`) supports the
  `cupcase`, `medqa`, and `mcr` corpora.
- **The v3 headline run is not reproducible from a clean clone** (the holdout case
  bodies are paywalled), but every per-case judge verdict and audit trail that
  produced the numbers above **is** committed under `data/results/` so the result
  is inspectable and re-gradable.

---

## Clinical grounding

Quorum grew out of the author's research in the **Nigam Shah lab** at Stanford. A
survey sent to physicians, nurses, physician assistants, and nurse practitioners
across Stanford Health asked which uses of AI in care they considered riskiest.
**Differential diagnosis came back at the top** — and the reason was consistent: a
diagnostic suggestion that can't be *verified*. Models would name a condition with
no calibrated confidence and no trace of where the reasoning came from, leaving the
clinician unable to separate a sound suggestion from a confident-sounding wrong one.

That finding is the design brief for Quorum. Its three load-bearing choices — a
fully auditable deliberation transcript, calibrated (not just top-pick) posteriors,
and a clinician-in-loop, non-device posture — map directly onto what those
clinicians said was missing: show the reasoning, quantify the uncertainty, and make
every claim traceable to a source. The design was refined through follow-up
conversations with practicing clinicians across several care settings; participants
are described by setting and role only, not by name. The themes they raised line up
with the published literature on trust and adoption of clinical decision support.
See the **Evidence** page in the web demo (`/evidence`) and
[`research/`](research/) for the full picture and citations.

---

## AI usage & development process

This project was built with the assistance AI coding tools — primarily Claude
Code (Anthropic) — for implementation, refactoring, test authoring, research
synthesis, and documentation, under continuous human direction and careful review
by the author. Design decisions, scope, evaluation methodology, and all go/no-go
calls were made by the author; the AI executed and accelerated that work but every
part of the design was made by the author as well as sourcing all the literature.
The five diagnostic agents themselves run on Claude Sonnet 4.6 (with Haiku 4.5 used
for the Gatekeeper's fallback matcher and a Sonnet judge for scoring).

In keeping with the repo's anti-confabulation discipline: benchmark numbers in this
README and on the Evidence page are computed from committed run artifacts under
data/results/, research citations are drawn from research/, and any figure not
independently verified is flagged as such.

Development history is public: the project was built solo for Stanford CS153
(Spring 2026) over roughly three weeks (May–June 2026), across 107 commits and the
release tags `v2.0`, `v2.1-accuracy-final`, and `v3-nejm-final`. Sources and prior
art are credited in **Related work** below and in
[`research/prior_art_map.md`](research/prior_art_map.md); the closed MAI-DxO system
Quorum reproduces is cited throughout.

---

## Status

Pre-alpha. See [`docs/milestone.md`](docs/milestone.md) for the CS153 Week 7
deliverable and [`docs/results_v3.md`](docs/results_v3.md) for the current headline.

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

MIT. See [`LICENSE`](LICENSE).

## Related work

See [`research/prior_art_map.md`](research/prior_art_map.md) for the full picture.
Most directly relevant:
- **MAI-DxO** (Microsoft) — the closed orchestrator Quorum reproduces
- **MedAgentBench** (Stanford) — FHIR-grounded agent benchmark we could integrate
- **CareGuardAI** (Apr 2026) — the closest published multi-agent guardrails framework
- **MedAbstain** — abstention methods for medical LLMs under clinical uncertainty
