# Quorum — Claude Code working context

> **Open-source diagnostic deliberation for clinical AI agents.** MCP server + web demo. Stanford CS153 (Spring 2026), 17-day solo build. Pre-alpha.

## Hard scope discipline

This repository is currently in **scaffolding + stubs + research-KB-only** mode. Every implementation file under `backend/src/quorum/` consists of docstrings, function signatures, and `# TODO:` bodies. Tests for stub files assert `raises NotImplementedError`.

**Do not, in this pass:**
- Implement orchestrator deliberation logic (`panel.py`, the 5 agent classes).
- Write production prompt content (the 5 files in `backend/src/quorum/orchestrator/prompts/`). Skeletons only.
- Fill in LLM provider clients with real API calls. Schematic only.
- Build out UI interaction behavior beyond stub renders.
- Generate eval cases. Schemas + empty dir + README only.
- Add dependencies beyond the pinned lists below.

The orchestrator-specific rule is captured in `.claude/rules/no-orchestrator-logic.md` (glob-scoped).

## Stack pins

**Python (backend)**
- `>=3.11,<3.13` (the upper cap exists because of prior burns on Python 3.13 in adjacent projects; biopython etc.).
- Package manager: `uv` workspace; root `pyproject.toml` declares `members = ["backend"]`.
- Key runtime deps (see `backend/pyproject.toml` for the canonical list): `anthropic`, `openai`, `google-genai`, `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `mcp>=1.0.0`, `sse-starlette`, `httpx`, `typer`.
- Dev deps: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`.

**Cloudflare (4th LLM provider + observability)**
- **Workers AI** is the 4th provider, sitting alongside Anthropic/OpenAI/Google. Hosts open-source models (Llama, Mistral) for the "open panel vs closed panel" comparison arm of the eval. HTTP-only — uses the existing `httpx` dependency; no new Python package.
- **AI Gateway** (optional) routes all 4 providers through a single Cloudflare-managed URL for caching, observability, and rate-limit dashboards. Set `CLOUDFLARE_AI_GATEWAY_URL` to enable. Strongly recommended for eval runs because cached responses make re-runs essentially free.
- **Compute envelope**: $50K Workers AI cap inside the $100K Cloudflare for Startups total; available for 1 year. At expected eval volume (304 cases × 5 agents × ~5 iterations ≈ 7,600 calls) this is comfortably under the cap.

**Node (frontend)**
- Node 20+, package manager `pnpm`.
- Framework: **Vite + React 19 + TypeScript** (not Next.js — see "Why not Next.js" below). React 19 came in with the Vite default scaffold; the brief didn't pin a React major, so we kept it.
- Tailwind **v3** (pinned; v4 incompatible with current shadcn).
- shadcn/ui via `pnpm dlx shadcn@latest`.
- Router: `react-router-dom`.
- Animation: `framer-motion`. Icons: `lucide-react`.
- Test: Vitest + `@testing-library/react`.

## Why not Next.js

The brief originally specified Next.js 14 App Router. We swapped to Vite because:
- The frontend is a pure SPA with one demo route; App Router buys us nothing.
- The Next.js Route Handler proxy (`app/api/diagnose/route.ts`) is unnecessary — FastAPI is reachable directly via Vite's dev proxy.
- Vite dev server boots ~10× faster; matters over a 17-day iteration loop.
- `create-react-app` was officially deprecated by the React team in Feb 2025; Vite is the modern "plain React SPA" scaffold.

## Port map

| Service | Port | Notes |
|---------|------|-------|
| FastAPI | 8000 | `backend/scripts/serve_api.py` |
| Vite dev | 3000 | **Pinned via `vite.config.ts`** (not the Vite default 5173). Honor brief's `.env.example`. Diverges from sibling `countersign-mcp` (5173) — different project. |
| MCP stdio | n/a | MCP runs over stdio, not TCP |

Vite proxies `/api/*` → `http://localhost:8000/api/*` so frontend code uses relative paths.

## Verify commands

After any meaningful change, run the relevant gate:

```bash
# Backend
cd backend && uv sync --extra dev && uv run pytest -q

# Frontend
cd frontend && pnpm install && pnpm lint && pnpm tsc --noEmit && pnpm vitest run

# Schema parity (after backend/frontend changes)
cd backend && uv run python scripts/dump_schemas.py
# then frontend Vitest should still pass

# Full acceptance (mirrors README §8)
cd backend && uv run pytest tests/test_acceptance.py -q

# Run eval (~$0.05 for 3 cases with dev_cheap, $5-10 for 100 cases with premium)
cd backend && uv run quorum-eval run --corpus medqa --panel dev_cheap --n 3
cd backend && uv run quorum-eval score <results_dir> --corpus medqa
cd backend && uv run quorum-eval report <results_dir> --corpus medqa

# MCP server (stdio)
cd backend && uv run python -m quorum.mcp_server.server
```

## Repository topology

Standalone git repo. Parent directory (`~/Documents/claude/`) is itself a git repo for unrelated subprojects; `Quorum/` is git-ignored from the parent.

## Directory contract

```
backend/src/quorum/    # Python package, importable as `quorum`
backend/tests/         # pytest; mirrors src layout
data/cases/{nejm,medqa}/  # JSON cases per `_schema.json` — empty for now
data/schemas/          # Generated Pydantic JSON schemas (do not hand-edit)
data/results/          # Eval output (gitignored except .gitkeep)
frontend/src/          # Vite source root
frontend/src/routes/   # Page-level components
frontend/src/components/ # Reusable components (shadcn ui/ subdir under here)
frontend/src/lib/      # API client, types, SSE helper, utils
docs/                  # Architecture, eval methodology, demo script, milestone, API ref
research/papers/       # 14 annotated bibliography entries
research/              # prior_art_map.md, fda_2026_cds_guidance.md, README.md
.github/workflows/     # CI
```

## Anti-hallucination protocol

When working in this repo, especially as a subagent:

1. **Verify file existence** after every Write. `ls -la` + `wc -l` and report.
2. **No confabulated citations.** If WebFetch fails on an arXiv abstract, annotate from the brief's TL;DR and include the literal flag `[abstract not independently retrieved — drafted from brief's TL;DR]`. Do not invent paper details. (This matches user feedback: `feedback_no_confabulated_citations`.)
3. **No new dependencies** outside the pinned lists.
4. **No file-structure changes** outside the agreed tree without surfacing to main thread.
5. **Stub tests use NotImplementedError-asserts.** A green test on a TODO body means someone silently filled in an implementation — catch it.

## Karpathy guardrails (apply to every code edit)

- **Surgical changes.** Don't refactor adjacent code. Don't "improve" wording in the brief.
- **Surface assumptions.** Any decision not literally specified by the brief is reported back to the main thread.
- **Verifiable success criteria.** Every task ends with a runnable command and an expected output.
- **No overcomplication.** If three near-identical agent stubs feel repetitive, that's fine for now — premature abstraction is worse than mild repetition at scaffolding scale.

## Related work + research

- `research/README.md` — paper index
- `research/prior_art_map.md` — where Quorum sits relative to MAI-DxO, MedAgentBench, AMIE, etc.
- `research/fda_2026_cds_guidance.md` — non-device CDS lane analysis for Quorum

## Status

| Phase | Status |
|-------|--------|
| Scaffolding | Complete |
| Vertical slice (Hypothesis + Panel + SSE + frontend transcript) | Complete |
| Five agents (Hypothesis/TestChooser/Challenger/Stewardship/Checklist) | Complete |
| Multi-agent consensus loop (3 termination paths, parallel Challenger\|\|Stewardship) | Complete |
| YAML panel configs (dev_cheap, single_model_premium, mixed_vendor, baseline_single_call) | Complete |
| Compare runner + /api/compare/stream | Complete |
| Polished frontend (multi-iter transcript + /compare route) | Complete |
| Eval harness (corpus loaders, runner, scorer with McNemar+Wilcoxon, CLI) | Complete |
| MCP stdio server (diagnose_case tool) | Complete |
| Headline eval with premium panels | Pending (out of /goal autonomous scope) |
| Demo video | Not started |

See `docs/milestone.md` for the CS153 Week 7 deliverable.

## License

MIT.
