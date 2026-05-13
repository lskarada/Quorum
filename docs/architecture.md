# Architecture

> Design-intent doc. Orchestrator logic is **not** implemented yet — this describes
> the intended shape, not as-built behavior.

## System diagram

```
+------------------------------+         +--------------------------------+
|  Frontend (Vite + React)     |         |  MCP client                    |
|  http://localhost:3000       |         |  (Claude Code, etc., stdio)    |
|  - routes/                   |         |                                |
|  - components/DebateView     |         |                                |
|  - lib/sse.ts                |         |                                |
+--------------+---------------+         +---------------+----------------+
               |                                         |
       HTTP + SSE (/api/*)                       MCP stdio (no port)
               |                                         |
               v                                         v
+--------------+-------------------------+   +-----------+--------------------+
|  FastAPI app                           |   |  MCP server                    |
|  backend/src/quorum/api/main.py        |   |  backend/src/quorum/mcp_server |
|   - routes.py  (HTTP endpoints)        |   |   /server.py                   |
|   - streaming.py  (SSE plumbing)       |   |   /tools.py                    |
|   - schemas.py (request/response)      |   |   exposes tool: diagnose_case  |
+--------------+-------------------------+   +-----------+--------------------+
               |                                         |
               +-----------------+-----------------------+
                                 |
                                 v
              +------------------+------------------+
              |  Panel orchestrator                 |
              |  backend/src/quorum/orchestrator/   |
              |  panel.py                           |
              |   .diagnose(case) -> FinalVerdict   |
              |   .diagnose_stream(case) -> events  |
              +------------------+------------------+
                                 |
            +----------+---------+---------+----------+----------+
            v          v         v         v          v
       Hypothesis  TestChooser  Challenger  Stewardship  Checklist
       (5 agents in backend/src/quorum/orchestrator/agents/)
                                 |
                                 v
                  +--------------+--------------+
                  |  LLMClient (provider shim)  |
                  |  backend/src/quorum/llm/    |
                  |  Anthropic / OpenAI / Google|
                  |  / Workers AI               |
                  +--------------+--------------+
                                 |
                  (optional) CLOUDFLARE_AI_GATEWAY_URL
                                 |
                                 v
                  +--------------+--------------+
                  |  Cloudflare AI Gateway      |
                  |  cache + observability +    |
                  |  rate-limit + fallback      |
                  +--------------+--------------+
                                 |
            Anthropic API / OpenAI API / Gemini API / Workers AI
```

## Data flow (HTTP + SSE path)

1. User pastes case text into the frontend, hits **Begin deliberation**.
2. Frontend (`frontend/src/lib/sse.ts`) opens `GET /api/diagnose/stream`
   with the `CaseInput` payload.
3. FastAPI route in `backend/src/quorum/api/routes.py` validates the body
   against `CaseInput` (see `backend/src/quorum/api/schemas.py`) and
   calls `Panel.diagnose_stream(case)`.
4. `Panel.diagnose_stream()` yields `StreamEvent` objects round by round.
   Each agent's `deliberate_stream()` emits `AgentMessage` deltas which
   the panel forwards.
5. `backend/src/quorum/api/streaming.py` serializes events as SSE frames.
6. The frontend `DebateView` component consumes the stream and renders
   per-agent cards, the running differential, and the final verdict.

## Parallel MCP path

The same Panel is exposed via MCP. `backend/src/quorum/mcp_server/server.py`
runs over **stdio** (no TCP port) and registers the `diagnose_case` tool in
`backend/src/quorum/mcp_server/tools.py`. An MCP client (Claude Code, Claude
Desktop, etc.) can call `diagnose_case` with a `CaseInput`-shaped payload and
receive a `FinalVerdict`. This is the "callable as MCP" half of the project's
thesis.

## SSE stream contract

The `StreamEvent` union (defined in
`backend/src/quorum/orchestrator/schemas.py`) is the contract between
backend and frontend. Expected event variants:

- `agent_started` — which of the 5 agents is now speaking
- `agent_delta` — incremental `AgentMessage` content
- `differential_updated` — current `Differential` (ranked hypotheses)
- `test_proposed` — `NextTest` from TestChooser
- `round_complete` — round index + summary
- `verdict` — terminal `FinalVerdict`
- `error` — typed error envelope

Frame format on the wire: `event: <type>\ndata: <json>\n\n`.

## Key schemas

All Pydantic models live in
`backend/src/quorum/orchestrator/schemas.py`:

- `CaseInput` — vignette text, optional priors, `max_iterations`, `budget_usd`
- `AgentMessage` — agent name, role, content, citations
- `Differential` — ranked list of `(diagnosis, posterior, rationale)`
- `NextTest` — proposed test, cost, expected information gain
- `FinalVerdict` — top diagnosis + ranked alternatives + transcript ref
- `StreamEvent` — discriminated union of the variants above

`backend/scripts/dump_schemas.py` regenerates JSON schemas into
`data/schemas/` for frontend type parity.

## Port map

| Service     | Port | Notes                                              |
|-------------|------|----------------------------------------------------|
| FastAPI     | 8000 | `backend/scripts/serve_api.py`                     |
| Vite dev    | 3000 | **Pinned** in `vite.config.ts` (not Vite default)  |
| MCP stdio   | n/a  | stdio transport; no TCP socket                     |

Vite proxies `/api/*` → `http://localhost:8000/api/*`.

## LLM provider matrix

| Provider     | Models (Quorum-facing name)                              | Lane                  |
|--------------|----------------------------------------------------------|-----------------------|
| Anthropic    | `claude-opus-4-7`, `claude-sonnet-4-6`                   | closed-source primary |
| OpenAI       | `gpt-5`, `gpt-5-mini`                                    | closed-source baseline|
| Google       | `gemini-2.5-pro`                                         | closed-source baseline|
| Cloudflare Workers AI | `llama-3.3-70b-instruct`, `mistral-small-3.1-24b-instruct` | **open-source baseline** |

Cloudflare slugs are translated server-side in
`backend/src/quorum/llm/providers/workers_ai_provider.py`
(`CF_MODEL_SLUG` dict). The user-facing names above are what the orchestrator
sees; the provider rewrites them to `@cf/meta/...` form on the wire.

### Cloudflare AI Gateway (optional but recommended)

If `CLOUDFLARE_AI_GATEWAY_URL` is set, **all four** providers route through
the gateway. Benefits: response caching (huge for eval re-runs — same prompt
returns from cache, costs zero), per-provider observability, rate-limit
dashboards, and automatic fallback if a provider 5xx's. Quota: free with
Workers AI ($50K cap inside the $100K Cloudflare for Startups envelope).

## Pin choices worth calling out

- **Vite over Next.js.** Pure SPA, one demo route, no SSR. Vite boot
  ~10x faster on a 17-day loop. `create-react-app` deprecated Feb 2025.
- **Tailwind v3 over v4.** v4 is incompatible with current shadcn/ui.
- **`react-router-dom` over App Router.** Follows the Vite choice; no
  filesystem routing needed.
- **Five named agents, no more.** Hypothesis, TestChooser, Challenger,
  Stewardship, Checklist. Mirrors MAI-DxO (arXiv 2506.22405).
