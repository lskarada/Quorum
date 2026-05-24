# Roadmap

Items listed here are **Approach C** extensions to Quorum, deferred to
future work beyond the 17-day Approach B build. Each entry records
motivation, design sketch, dependencies, and any open research
questions that gate implementation.

## 1. Citation grounding

**Motivation.** Today's agent outputs assert clinical claims (e.g.
"posterior 0.45 for cardiac amyloidosis given low-voltage QRS") without
mechanically enforced references. For a clinical-decision-support tool,
unverified assertions are the primary credibility risk — even when the
top-1 accuracy number is good, an unsupported chain of reasoning is hard
to defend in a regulatory or peer-reviewed setting.

**Design sketch.** Extend `AgentMessage.citations` to be a required,
non-empty list on assertion-bearing fields. The constraint is enforced
by Pydantic at schema-validation time and by a re-prompt loop in the
agent base class: if the LLM emits an assertion without a supporting
citation, the agent re-prompts with the missing-citation message and
retries up to `max_citation_retries`. The agent prompt is updated to
instruct the LLM to call PubMed E-utility (`esearch` + `esummary`)
before producing each assertion, returning PMIDs as the citation
identifier. The MCP server exposes a `pubmed_search` tool that the
agent can call during deliberation.

**Dependencies.** A PubMed E-utility wrapper (httpx, no new dep) and
a citation-id resolver (PMID → title/journal/year). No blocking
research questions.

## 2. Structured uncertainty

**Motivation.** The current `AgentMessage` carries a free-form
`confidence` string. To weight agents in consensus (item 3 below) and
to report calibrated uncertainty alongside the differential, each
agent needs a numeric, comparable confidence score with known
calibration properties.

**Design sketch.** Out of scope until the research question below is
resolved. Candidate approaches under consideration:

- **Logit-based.** Use the LLM's token log-probabilities at the
  diagnosis-emission position. Requires a provider that exposes
  logprobs in the response. Calibration is provider-dependent.
- **Self-consistency.** Sample the agent `k` times at temperature > 0
  and use the agreement rate as the confidence. Multiplies cost by `k`.
- **Verbalized confidence with calibration.** Have the LLM emit a
  numeric confidence and apply a calibration map (Platt scaling,
  isotonic regression) fit on a held-out set with known correctness
  labels.
- **Ensemble-based UQ.** Use disagreement across the panel's existing
  multi-vendor members as the uncertainty proxy. Cheapest because the
  ensemble already exists.

**Dependencies.** Held-out labeled set for calibration fitting
(separate from the eval corpus, to avoid leakage).

**Research questions (BLOCKING).**

- Which of the four approaches above is most reliable for clinical
  reasoning specifically? Existing UQ literature is largely
  factual-QA-flavored; clinical reasoning is multi-hop and the
  factual-QA calibration results may not transfer.
- Does a single confidence score capture the relevant uncertainty, or
  does each agent need a distribution over its proposed differential?

Until these are answered, do not ship a confidence number — a
poorly-calibrated number is worse than no number at all in this
domain.

## 3. Confidence-weighted consensus

**Motivation.** The current `Panel` treats agents as equal voters when
aggregating into `FinalVerdict`. If one agent is consistently
over-confident or consistently miscalibrated on a given case type,
equal weighting either degrades accuracy or wastes the signal from
the well-calibrated agents.

**Design sketch.** Replace the current equal-weight aggregation in
`Panel._build_final_verdict` with a confidence-weighted aggregation:
each agent's contribution to the posterior is scaled by its reported
confidence, normalized across agents. The Challenger and Checklist
agents may carry a fixed downweight since their role is adversarial
rather than diagnostic.

**Dependencies.** Item 2 (structured uncertainty) must ship first.
This item is purely the aggregation change; the heavy work is in (2).

## 4. Structured JSON logging and observability

**Motivation.** Explicitly deferred from Phase 5 of the build plan. The
current `Panel` and `LLMClient` emit human-readable logs to stderr,
which is fine for development but cannot be scraped reliably in a
production deployment for cost tracking, error rates, or panel-config
A/B comparison.

**Design sketch.** Three sub-items, each independently shippable:

- **Per-event JSON logs.** Each `panel_event`, `agent_message`,
  `llm_call`, and `final_verdict` is emitted as one JSON object per
  line to a configurable sink (stdout, file, or HTTP endpoint via a
  pluggable writer). Schema is fixed and versioned.
- **Generated TypeScript types from Pydantic schema.** Replace the
  hand-mirrored `frontend/src/lib/types.ts` with codegen from
  `data/schemas/*.json`. Removes a class of schema-drift bugs that
  the current `scripts/dump_schemas.py` + manual mirror catches only
  on a vitest run.
- **Per-panel-config cost-prior estimation.** A small calibration step
  that runs each panel config on a fixed smoke set, records mean
  cost-per-case, and writes it back to the panel YAML as a
  `cost_prior_usd` field. The CLI's `quorum-eval run` then warns when
  `--n × cost_prior_usd` exceeds `QUORUM_MAX_COST_USD` before the
  run starts, instead of only failing mid-run.

**Dependencies.** None blocking; each sub-item can ship independently.
