# Demo Script — 3-minute video

## 0:00–0:20 — Hook
Anj's "Safety, Policy, Governance / Models & Agents" slide. Cut to Quorum landing page.
Voiceover: "Microsoft's MAI-DxO hit 85.5% on NEJM cases. It's closed. Quorum is the open
version, callable as MCP, with the debate streamed live."

## 0:20–1:40 — Live demo
Paste an NEJM-style case into the demo. Hit "Begin deliberation."
- Five agent cards light up in sequence.
- Hypothesis proposes a ranked differential (Top-3 displayed with posteriors).
- Test-Chooser picks the cheapest discriminating test.
- Challenger attacks the top hypothesis.
- Stewardship enforces cost-aware reasoning.
- Checklist green-lights consistency.
- Round 2 begins; differential shifts.
- After 2-3 rounds, verdict displayed with citations.

## 1:40–2:20 — Architecture
One clean diagram. FastAPI + MCP server + Vite/React frontend. Five-agent panel. SSE stream.
"Built by one undergrad in 17 days."

## 2:20–3:00 — Numbers + vision
Comparison table:
- Off-the-shelf Claude Opus 4.7: TBD
- Off-the-shelf GPT-5: TBD
- Off-the-shelf Llama-3.3-70b (Cloudflare Workers AI): TBD
- Quorum panel — closed members (Opus/GPT-5/Gemini): TBD
- Quorum panel — open members (Llama/Mistral via Workers AI): TBD
- MAI-DxO reported: 85.5%
- Random baseline: ~5%

"Any clinical AI agent ships into a market that needs diagnostic depth. MAI-DxO
proved this works. Quorum is the open version anyone can call — and the
open-models-as-a-panel result is the part that doesn't exist anywhere yet."
