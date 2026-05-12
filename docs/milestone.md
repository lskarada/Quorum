# Quorum — CS153 Milestone (Week 7)

## Project pitch
Quorum is an open-source multi-agent diagnostic orchestrator, callable as an MCP
server, that reproduces Microsoft's closed-source MAI-DxO chain-of-debate (arXiv
2506.22405; 85.5% on 304 NEJM CPC cases) with a live web UI streaming the
agent debate in real time.

## What's shipped at milestone
- Scaffolding: backend (uv workspace, FastAPI, MCP server stub, eval harness stub) + frontend (Vite + React + Tailwind + shadcn-style components) + research KB
- 5 agent stubs with prompt skeletons (Hypothesis, TestChooser, Challenger, Stewardship, Checklist)
- TBD NEJM-style cases curated with ground truth
- Hello-world end-to-end: one case → one agent's output → frontend display (TBD)
- Comparison plan documented (`docs/eval_methodology.md`)

## Decisions and pivots
- Pivoted from Countersign (compliance rails) to Quorum (diagnostic orchestrator) — diagnostic deliberation is the more research-worthy lane and has a credible open-source gap
- Eval corpus: NEJM CPC (~50) + MedQA control (~30)
- Vite over Next.js: pure SPA, no SSR needed, faster iteration on a 17-day timeline
- Tailwind v3 pinned for shadcn compatibility

## Risks and mitigations
- Training-data contamination → mitigate with case-recency filter (post-cutoff CPCs only)
- Cost per case → bounded by `case.max_iterations` and `case.budget_usd`
- MAI-DxO already exists → differentiate on open-source + MCP-callable + live UI + transparency (the debate transcript IS the artifact)

## Plan to ship final (Week 9)
- Days 4–10: full agent prompt engineering, end-to-end happy path
- Days 11–16: eval run, video shoot, README polish
