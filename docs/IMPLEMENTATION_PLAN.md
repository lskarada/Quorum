# Quorum — Vertical Slice Implementation Plan

> Hypothesis → Panel → SSE → Frontend transcript. 7 phases, gated on tests.
> Routes through `/router` lanes feature+bug+refactor+claude-md best practices.
> Karpathy guardrails enforced per edit.

## Scope of this slice

**Implement:** `HypothesisAgent.deliberate()`, `Panel.diagnose()` + `Panel.diagnose_stream()` (single-agent single-iteration path), `POST /diagnose` SSE endpoint, frontend `Diagnose.tsx` route consuming the stream end-to-end.

**Out of scope (remain stubbed):** `TestChooser`, `Challenger`, `Stewardship`, `Checklist` agents; multi-iteration consensus loop; real LLM provider integration tests; eval harness; MCP server impl.

## Locked contracts (assumptions surfaced)

If any of these are wrong, redirect now — every later phase compiles down to one of them.

### A1. Hypothesis output schema

```python
class DiagnosisCandidate(BaseModel):
    name: str                          # canonical disease name
    posterior: float                   # 0.0 .. 1.0
    supporting_findings: list[str]     # case findings that raise this prior
    against_findings: list[str]        # case findings that lower it
    citations: list[str] = []          # optional, freeform refs

class Differential(BaseModel):
    candidates: list[DiagnosisCandidate]  # length 3..7
    reasoning: str                        # 1-2 sentence summary
```

Validation rules:
- `3 <= len(candidates) <= 7` — outside range → schema violation event.
- `sum(posteriors)` within `0.95..1.05` — outside → normalize, emit `agent_message` with warning flag.
- Empty `supporting_findings` allowed; empty `name` rejected.

### A2. SSE event envelope

Every frame is the same shape:

```json
{
  "type": "agent_start | agent_message | agent_end | verdict | error",
  "agent": "hypothesis | null",
  "iteration": 0,
  "payload": { ... },
  "ts": 1700000000.123
}
```

Payload schema per type:
- `agent_start`: `{}`
- `agent_message`: `Differential` (above)
- `agent_end`: `{tokens_in, tokens_out, latency_ms}`
- `verdict`: `{top_candidate: DiagnosisCandidate, confidence: float, transcript_summary: str}`
- `error`: `{code, message, retriable: bool, http_status: int | null}`

SSE framing: `data: <json>\n\n`. No event IDs. Heartbeat every 15s as `event: ping\ndata: {}\n\n`.

### A3. Error envelope codes (closed set)

- `provider_429` retriable=true
- `provider_timeout` retriable=true
- `parse_failure` retriable=false (LLM returned non-JSON)
- `schema_violation` retriable=false (LLM returned wrong shape)
- `internal` retriable=false
- `client_disconnect` (not emitted to client — logged server-side only)

### A4. Frontend render rules per event

| Event | UI action |
|-------|-----------|
| `agent_start` | Show "Dr. Hypothesis is thinking…" with spinner, `aria-busy=true`, disable submit |
| `agent_message` | Append `AgentMessage` card with `DifferentialTable` rendered; ARIA live announces "New differential from Dr. Hypothesis" |
| `agent_end` | Freeze card, show latency badge |
| `verdict` | Highlight top candidate, replace spinner with checkmark, re-enable submit |
| `error` | Red banner with code + message; if `retriable`, show "Retry" button (single retry max) |
| connection drop | Show toast "Connection lost — retrying once"; if second drop, hard error |

### A5. Consensus / verdict definition (this slice)

Single-agent: verdict = top candidate from Hypothesis's first (only) iteration. Confidence = `top_candidate.posterior`. No multi-iteration loop. Multi-agent consensus deferred to a later phase.

## Phase gates

Each phase ends with a runnable command + expected output. No phase advances until its gate is green AND the gate output is pasted into the conversation [B2].

| Phase | Gate command | Expected |
|-------|--------------|----------|
| 0 | `cd backend && uv run pytest -q && cd ../frontend && pnpm vitest run` | both pass |
| 1 | `cd backend && uv run pytest tests/test_agents.py tests/test_panel.py -v` | RED with expected failure messages |
| 2 | `cd backend && uv run pytest tests/test_agents.py -v` | GREEN |
| 3 | `cd backend && uv run pytest tests/test_panel.py -v` | GREEN |
| 4 | `cd backend && uv run pytest tests/test_acceptance.py -v` + curl smoke | GREEN + valid SSE stream printed |
| 5 | `cd frontend && pnpm vitest run && pnpm build` + browser smoke | GREEN + screenshot golden + error path |
| 6 | Full suite + code-reviewer subagent report | clean |

## Discipline rules (apply throughout)

- **Diff size guard [R1]:** any phase's net diff > 150 lines triggers a split.
- **Commit cadence [R3]:** one commit per phase-substep where state changes. Never bundle tests + impl.
- **Evidence-before-assertion [B2]:** paste pytest/curl/browser output in chat before claiming green.
- **Subagent isolation [B3]:** test-drafting, debugging, and code review run in fresh subagent contexts.
- **No CLAUDE.md growth [C1]:** new conventions go to `.claude/rules/*.md` with `<important if=...>` scopes.
- **Karpathy:** surgical edits only; no speculative abstraction; no "while I'm here" cleanups inside an impl commit.
- **`/simplify` after every impl phase [R4];** `/refactor-clean` once before final review [R5].

## Skill orchestration map

| Phase | Superpower | Other |
|-------|-----------|-------|
| 0 | brainstorming, writing-plans | router C3 verification |
| 1 | test-driven-development, subagent-driven-development, dispatching-parallel-agents | — |
| 2 | verification-before-completion | /simplify |
| 3 | verification-before-completion | /simplify |
| 4 | systematic-debugging (on-demand) | /simplify, /sandbox if needed [B4] |
| 5 | test-driven-development, verification-before-completion | multi-frontend, /refactor-clean |
| 6 | requesting-code-review, verification-before-completion, finishing-a-development-branch | code-reviewer subagent |
