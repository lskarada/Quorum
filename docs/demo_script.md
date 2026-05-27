# Demo Script — 3–5 minute video

## 0:00–0:30 — Hook

"MAI-DxO hit 85.5% on NEJM. Microsoft kept it closed. Quorum is the
open version, and here's a thing they didn't show: panel composition
matters."

## 0:30–1:30 — Live single-panel demo (dev_cheap)

Paste a case at `/diagnose`. Five agent cards light up across
iterations:

- **Hypothesis** — Top-3 differential with posteriors.
- **TestChooser** — discriminating next test.
- **Challenger** — attack on the top hypothesis.
- **Stewardship** — cost-aware judgment.
- **Checklist** — contradiction scan.

Round 2 begins; the differential shifts. Verdict in 2–3 iterations.

## 1:30–2:30 — Compare-mode demo at `/compare`

Same case, two panels (`dev_cheap` vs `baseline_single_call`). Both
columns stream concurrently. Side-by-side verdict summary at the
bottom highlights agreement and disagreement.

## 2:30–3:30 — Eval numbers

Show `docs/results.md` table. The headline ablation is
**5-agent debate (`dev_cheap`)** vs **single-call baseline
(`baseline_single_call`, all Opus)** on MedQA at n=30, scored with
paired McNemar on top-1 and Wilcoxon on MRR. Premium-tier panels
(`single_model_premium`, `mixed_vendor`) are documented but were not
run in this release for budget reasons — see results.md Limitations.

## 3:30–4:30 — Architecture + MCP + open repo

One slide: FastAPI + Vite/React frontend + MCP stdio + OpenRouter
routing + YAML panel configs. "Built solo in 17 days. MIT-licensed.
Callable as MCP from Claude Desktop or Claude Code."

## 4:30–5:00 — Close

Repo URL + "Try it: clone, `uv sync`, `pnpm dev`. Bring your own
OpenRouter key."
