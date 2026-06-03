# Demo Script — submission video (target < 3 min)

> CS153 requires the video to answer four questions: (Q1) why you built it /
> what bottleneck, (Q2) how it works technically, (Q3) use cases + societal
> value, (Q4) what you'd add next. This script hits all four and shows the
> live demo + the evidence. Keep it tight; 2:30–3:00 is the goal.

## 0:00–0:25 — Hook + Q1 (why / the bottleneck)

"Microsoft's MAI-DxO hit 85.5% on the NEJM CPC benchmark — but it's closed.
Clinicians can't see how it reasons, can't check its confidence, can't audit
what it did. Those are exactly the things that decide whether a clinical tool
gets trusted. Quorum is the open version: five specialist agents that debate a
case in the open, with calibrated confidence and a full audit trail."

## 0:25–1:15 — Q2 (how it works) + live single-panel demo

Paste a case at `/diagnose` (use a corpus vignette, e.g. the Kawasaki case).
Narrate as the cards stream:

- **Dr. Hypothesis** — ranked differential with *calibrated posteriors* (not
  just a top pick).
- **Dr. Test-Chooser** — the most discriminating next test.
- **Dr. Challenger** — attacks the leading hypothesis.
- **Dr. Stewardship** — cost-aware judgment.
- **Dr. Checklist** — contradiction scan; plus a SafetyChecker gate.

"They loop until they reach consensus, hit max iterations, or the checklist
says stop. Everything you're seeing streams over SSE from a FastAPI backend;
the same panel is callable as an MCP tool from Claude Desktop or Claude Code.
Stack: FastAPI + Vite/React + MCP stdio, routed through OpenRouter, runs on
Claude Sonnet 4.6."

## 1:15–1:45 — Compare mode at `/compare`

Same case, two panels side by side (the 5-agent panel vs a single-model
baseline). Both columns stream concurrently. "Same underlying model — the only
difference is the deliberation and safety layer on top."

## 1:45–2:25 — Q3 (evidence + societal value) at `/evidence`

Show the Evidence page benchmark figure (and `docs/results.md` /
`docs/results_v2.md` behind it):

- **Headline — decontaminated, run-once NEJM-2026 holdout, n=12, k=5 vote:**
  Quorum **41.7%** top-1 (5/12) and **75.0%** top-1-or-partial (9/12) vs a
  single-model baseline at **16.7%** (2/12) and **58.3%** (7/12) — **2.5× the
  exact-match rate** from the deliberation + safety layer alone.
- Be honest on camera: n is small (12 cases); these aren't directly comparable
  to MAI-DxO's 304-case 85.5% or unaided physicians' ~20% — those are
  reference points from the literature.
- Note the differentiators a grader cares about: **calibration** (Brier + ECE
  on the posteriors) and **auditability**, neither of which the closed system
  ships. Mention the design was informed by conversations with practicing
  clinicians (described by setting, not by name) and, briefly, the FDA
  non-device CDS framing on `/regulatory`.

## 2:25–2:50 — Q4 (what's next) + close

"Next: a larger decontaminated holdout with significance testing on the
headline, the premium mixed-vendor panel arm we deferred for budget, and
finishing the clinician-engagement write-up. It's MIT-licensed and open:
clone it, `uv sync`, `pnpm dev`, bring your own OpenRouter key."

Repo URL on screen. Done.

## Notes for recording

- Have the case text on the clipboard before you start so the paste is instant.
- Pre-warm the backend (one throwaway run) so the first on-camera deliberation
  streams without cold-start latency.
- All four required questions are tagged above (Q1–Q4) — make sure each is
  audibly answered.
