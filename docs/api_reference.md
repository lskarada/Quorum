# API Reference

> Design-intent doc. All routes and the MCP tool currently raise
> `NotImplementedError` until `Panel.diagnose()` and `Panel.diagnose_stream()`
> are wired. Shapes below are the **contract** the implementation will fulfill.

## HTTP API

Base URL (dev): `http://localhost:8000`. Frontend reaches these via the Vite
proxy at `http://localhost:3000/api/*`.

### `GET /health`

Liveness probe. Returns `200 OK` when the FastAPI process is up.

**Response**
```json
{ "status": "ok", "version": "0.1.0" }
```

### `POST /api/diagnose`

Synchronous, non-streaming diagnose call. Returns a single `FinalVerdict`.

**Request schema:** `CaseInput` (see `backend/src/quorum/api/schemas.py`,
re-exported from `backend/src/quorum/orchestrator/schemas.py`).

**Example body**
```json
{
  "case_text": "A 47-year-old man presents with...",
  "priors": null,
  "max_iterations": 3,
  "budget_usd": 1.00
}
```

**Response schema:** `FinalVerdict`.

**Example response**
```json
{
  "top_diagnosis": "TBD",
  "alternatives": [
    { "diagnosis": "TBD", "posterior": 0.0, "rationale": "TBD" }
  ],
  "transcript_ref": "run_<id>/case_<id>.json",
  "cost_usd": 0.0,
  "latency_ms": 0
}
```

### `GET /api/diagnose/stream`

Server-Sent Events stream of the panel deliberation. The request body uses
the same `CaseInput` shape (the route accepts it via POST + SSE upgrade in
some implementations; the canonical wiring lives in
`backend/src/quorum/api/streaming.py`).

**Event types** (frame: `event: <type>\ndata: <json>\n\n`):

- `event: agent_started`
  ```json
  { "agent": "Hypothesis", "round": 1 }
  ```
- `event: agent_delta`
  ```json
  { "agent": "Hypothesis", "delta": "partial text..." }
  ```
- `event: differential_updated`
  ```json
  { "round": 1, "differential": [ { "diagnosis": "TBD", "posterior": 0.0 } ] }
  ```
- `event: test_proposed`
  ```json
  { "round": 1, "test": "TBD", "cost_usd": 0.0, "expected_info_gain": 0.0 }
  ```
- `event: round_complete`
  ```json
  { "round": 1, "summary": "TBD" }
  ```
- `event: verdict` — terminal event; payload is `FinalVerdict`.
- `event: error`
  ```json
  { "code": "TBD", "message": "TBD" }
  ```

Clients should treat `verdict` and `error` as terminal.

## MCP tool

The same panel is exposed over MCP stdio. Server entry:
`backend/src/quorum/mcp_server/server.py`. Tool definitions:
`backend/src/quorum/mcp_server/tools.py`.

### Tool: `diagnose_case`

**Input schema:** `CaseInput` (same shape as `POST /api/diagnose`).

**Output schema:** `FinalVerdict`.

**Example MCP call** (conceptual):
```json
{
  "name": "diagnose_case",
  "arguments": {
    "case_text": "A 47-year-old man presents with...",
    "max_iterations": 3,
    "budget_usd": 1.00
  }
}
```

The MCP path does not stream incremental events in v1; it returns the final
verdict only. The live-debate UX is HTTP-SSE-specific.

## Status

All endpoints and the MCP tool currently raise `NotImplementedError`. Stub
tests under `backend/tests/` assert this until orchestrator logic lands.
See `docs/architecture.md` for how these surfaces connect to `Panel`.
