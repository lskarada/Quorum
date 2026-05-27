# Agent return contracts (snapshot 2026-05-27)

This file is the canonical reference for Phase 5 (`run_sequential`)
and downstream consumers. It supersedes any sketch in the v2 plan that
uses flat attribute names like `posterior_over_shortlist`, `accept_test`,
`top_alternative`, or `unresolved_concerns` — those names DO NOT exist.

Authority: `backend/src/quorum/orchestrator/schemas.py` and the five
agent classes under `backend/src/quorum/orchestrator/agents/`.

## Panel

```python
class Panel:
    def __init__(self, llm: LLMClient, config: PanelConfig | None = None): ...
    async def diagnose(self, case: CaseInput) -> FinalVerdict: ...
    async def diagnose_stream(self, case: CaseInput) -> AsyncIterator[StreamEvent]: ...
```

- The first positional kwarg is `llm`, NOT `llm_client`.
- All deliberation is async.
- There is NO `_call_agent` helper. Each agent is invoked directly:
  `msg = await self.hypothesis.deliberate(case, list(transcript), iteration)`.

## LLMClient

```python
class LLMClient:
    async def complete(
        self,
        messages: list[dict],     # OpenAI-style: [{"role": "system|user|assistant", "content": "..."}]
        model: str | None = None,  # OpenRouter vendor-prefixed; None → self.default_model
        response_format: dict | None = None,  # e.g. {"type": "json_object"}
        max_tokens: int = 4096,
    ) -> LLMResponse: ...
```

`LLMResponse(content: str, tokens_used: int, cost_usd: float, model: str)`.

Test stubs MUST be async. Use `unittest.mock.AsyncMock` and configure
`return_value=LLMResponse(content="...", tokens_used=0, cost_usd=0.0, model="stub")`.

## Agent base class

```python
class Agent(ABC):
    role: AgentRole
    def __init__(self, llm: LLMClient, model: str | None = None): ...
    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage: ...
```

All five concrete agents implement `deliberate` exactly this way. There
are no per-agent variants of the signature.

`AgentMessage` carries `role`, `iteration`, `content`, `structured_output`
(`Optional[Union[Differential, NextTest, dict]]`), `tokens_used`, `cost_usd`.

## HypothesisAgent

- `structured_output`: `Differential`
- `Differential.candidates: list[DiagnosisCandidate]`
- `DiagnosisCandidate.name: str` (the diagnosis label)
- `DiagnosisCandidate.posterior: float` in `[0.0, 1.0]`
- `Differential.iteration: int`

Posteriors are auto-normalized to sum ~1.0 by the agent itself (raises
on degenerate sum=0).

**To extract a posterior dict** for SafetyChecker / Brier / ECE:

```python
diff = msg.structured_output                              # Differential
posterior = {c.name: c.posterior for c in diff.candidates}
top_dx = max(posterior, key=posterior.get)
top_p = posterior[top_dx]
```

## TestChooserAgent

- `structured_output`: `NextTest`
- `NextTest.name: str` — THIS is the query to send to the Gatekeeper.
- `NextTest.rationale: str`
- `NextTest.estimated_cost_usd: float | None`
- `NextTest.information_gain_estimate: float | None`
- `NextTest.discriminates_between: list[str]`
- `NextTest.citations: list[Citation]`

**To get the query**: `query = msg.structured_output.name`.
There is no `.next_query` field — that name was a placeholder in the
plan sketch.

## ChallengerAgent

- `structured_output`: `dict` with these keys (validated in the agent):
  - `against_top_candidate: list[str]` — findings that argue against the leading dx
  - `alternative_to_consider: str` — single dx name, or "none"
  - `confidence_in_challenge: float` in `[0.0, 1.0]`

**To get the challenger's top alternative**:
`alt = msg.structured_output["alternative_to_consider"]`.

There is no flat `.top_alternative` attribute.

## StewardshipAgent

- `structured_output`: `dict` with these keys:
  - `accept_test: bool` — true if the test proposed by TestChooser is cost-justified
  - `cost_concern: str | None`
  - `cheaper_alternative: dict | None` — when present, a NextTest-shaped dict

**To get the stewardship vote**:
`vote_continue = msg.structured_output["accept_test"]` — `True` means
"continue/accept this next test", `False` means stop (or substitute).

There is no `.vote == "stop"` semantic. Map `accept_test=False` to "stop"
if you need a vote-like predicate.

## ChecklistAgent

- `structured_output`: `dict` with these keys:
  - `consistent: bool` — internal consistency of the panel so far
  - `flags: list[str]` — specific contradictions found (the v2 spec's
    "checklist_concerns" maps to this)
  - `recommend_continue: bool` — should the panel keep iterating?

**To get the safety concerns list**:
`concerns = msg.structured_output["flags"]`.

There is no `.unresolved_concerns` attribute.

## CaseInput

```python
class CaseInput(BaseModel):
    case_id: str | None = None
    presentation: str
    available_tests: list[str] = []
    budget_usd: float | None = None
    max_iterations: int = 5
```

`run_sequential` wraps a v2 `EvalCase` in a `CaseInput`:

```python
case_input = CaseInput(
    case_id=eval_case.case_id,
    presentation=eval_case.initial_presentation,  # plus optional revealed findings appended
    available_tests=[],
    budget_usd=None,
    max_iterations=cfg.max_iterations,
)
```

Revealed Gatekeeper findings are appended to the presentation between
turns (or surfaced via synthetic transcript messages — either pattern is
fine; the agents look at both the presentation and the transcript).

## PanelConfig sequential extension

The existing `PanelConfig` has no sequential block. For v2 we keep the
existing fields and read sequential-mode knobs (max_turns,
commit_threshold, gatekeeper_max_cost_usd, safety knobs) from a thin
wrapper or pass them as explicit kwargs to `Panel.run_sequential`. We
do NOT mutate the existing PanelConfig.mode enum because there isn't
one — `mode: sequential_diagnosis` from the plan sketch was aspirational.

## Summary of plan-sketch name corrections

| Plan sketch              | Actual                                                           |
|--------------------------|------------------------------------------------------------------|
| `Panel(llm_client=...)`  | `Panel(llm=...)`                                                 |
| `hypothesis_out.posterior_over_shortlist` | `{c.name: c.posterior for c in hyp_msg.structured_output.candidates}` |
| `next_query.next_query`  | `tc_msg.structured_output.name`                                  |
| `challenger_out.top_alternative` | `chal_msg.structured_output["alternative_to_consider"]`     |
| `stewardship_out.vote == "stop"` | `stew_msg.structured_output["accept_test"] is False`        |
| `checklist_out.unresolved_concerns` | `chk_msg.structured_output["flags"]`                     |
| `self._call_agent("hypothesis", ...)` | `await self.hypothesis.deliberate(case, list(transcript), iteration)` |
