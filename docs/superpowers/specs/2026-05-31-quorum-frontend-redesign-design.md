# Quorum Frontend Redesign — Design Spec

**Date:** 2026-05-31
**Status:** Approved (design), pending implementation plan
**Scope:** Visual / UX redesign of the existing React SPA. **Reskin + demo UX only — no backend, LLM, or orchestrator changes.**
**Locked mockup:** `.superpowers/brainstorm/80606-1780288473/content/locked-C-hifi.html` (Direction C, high fidelity)

---

## 1. Goal

Make the Quorum web app **beautiful, usable, and demo-video-ready**. When recording the demo, the screen should clearly show *how the five agents deliberate toward a diagnosis* and *how the system works as a whole* — without the viewer needing narration to follow it.

The redesign is a **reskin and layout pass**. It does **not** touch:
- The FastAPI backend, orchestrator, agents, prompts, or eval harness.
- The SSE event protocol or the `streamDiagnosis` / `streamComparison` data flow.
- The data contracts of presentational components (props stay the same; only markup/styling/motion change).

Frontend *functionality* changes are limited to presentation-layer concerns the methodology calls for: layout restructure, motion, empty/loading/error states, auto-scroll, and a small amount of derived display state (e.g. computing a "leading diagnosis" from the latest hypothesis differential while running, rather than only after the final verdict).

## 2. Decisions (locked in brainstorming)

| Decision | Choice |
|---|---|
| Scope | Reskin + demo UX (not a rebuild) |
| Aesthetic | **Clinical trust** — calm, credible, decision-support-tool feel |
| Theme | **Light only** (drop the dark-mode toggle from the demo path; see §9) |
| Demo hero | The live single-panel debate at **`/diagnose`** |
| Closing beat | The **`/compare`** two-panel view (single-vendor vs. mixed/calibrated) |
| Layout direction | **C — Clinical Chart Split**: case chart on the left, live ranked differential + streaming deliberation on the right |
| Per-message token/cost | **Removed** (cut as clutter during review) |

## 3. Design system (tokens)

These are the locked tokens from the hi-fi mockup. They land in `tailwind.config.ts` (extend) and `src/index.css` (CSS custom properties on `:root`). Existing shadcn HSL token names are preserved; we re-point their *values* to the clinical-trust palette rather than renaming them.

**Color — surfaces & ink (light)**
- `--bg: #eef2f7` (app background) · `--surface: #ffffff` · `--surface-2: #f8fafc`
- `--ink: #0f172a` · `--ink-2: #334155` · `--muted: #64748b` · `--faint: #94a3b8`
- `--line: #e2e8f0` · `--line-strong: #cbd5e1`
- `--brand: #1e6fd9` (primary action) · `--ok: #16a34a` · `--warn: #d97706`

**Color — the five agent roles (LOCKED — do not change; matches `tailwind.config.ts` and `docs/ia.md`)**
- Hypothesis `hsl(217 91% 60%)` (blue)
- Test Chooser `hsl(160 84% 39%)` (green)
- Challenger `hsl(0 84% 60%)` (red)
- Stewardship `hsl(43 96% 56%)` (amber; use `#a8780a` for amber *text* to keep contrast)
- Checklist `hsl(280 91% 60%)` (purple)

**Type**
- UI/body: `Inter` (already the app default) → `-apple-system, system-ui` fallback.
- Numeric/metrics (posteriors, budget, confidence): `JetBrains Mono` / `ui-monospace`. Mono is used *only* for numbers, not prose.

**Radius:** `--r-sm: 8px` · `--r: 12px` · `--r-lg: 16px` (cards). Maps to shadcn `--radius`.
**Shadow:** `--sh-1` (subtle, resting) and `--sh-2` (card lift). Defined in the mockup `<style>`.
**Spacing:** 4px base grid; card padding 18px; inter-card gap 18px.

## 4. Screen specs

### 4.1 `/diagnose` — the hero (primary)

Two-column layout: **`[ 380px case chart ] [ 1fr right column ]`** (stacks to one column under ~980px).

**Top bar** (full width, above the columns): brand mark + "Quorum", panel selector chip (`Panel: v2 · 5-agent calibrated ▾`), and a right-aligned live status with a pulsing green dot (`Deliberating · round N of M` while running; `Idle` / `Complete` otherwise).

**Left — Case chart card:**
- Before run: this is the **case input** (textarea + "Begin deliberation" primary button). `CaseInput`'s `onStart`/`disabled` contract is unchanged.
- During/after run: collapses to a read-only chart — Presentation (boxed), Demographics (pills), Tests ordered (green Test-Chooser chips, fed by `nextTest` / verdict), Budget meter. (Deriving the chart summary from the submitted presentation is new *display* logic, not new data.)

**Right column, top — Verdict + live differential card:**
- Confidence **ring** (conic-gradient) showing the leading candidate's posterior; leading diagnosis name; "N candidates" subline; termination badge (`● Consensus reached` / `Max iterations` / `Stopped`) driven by `verdict.termination_reason`.
- Ranked differential list: rank, name + one-line rationale, animated posterior bar, mono posterior value. Rank 1 uses the Hypothesis blue; alternates are muted. While running, this is fed by the latest `agent_complete` hypothesis differential; on `verdict` it locks to `verdict.final_differential`.
- Restyles `DifferentialTable` + `ConfidenceMeter` (props unchanged: `{verdict}`).

**Right column, bottom — Deliberation card:**
- Header "Deliberation · 5 agents · streaming".
- Iteration dividers (`IterationDivider`, `{iteration}`) separate rounds.
- Each agent message: 30px rounded avatar with role initial in the role color, a bubble with a role-colored left border, the agent name in role color, and the message text. Restyles `AgentCard` (`{message}`) — **no token/cost line**.
- Typing indicator (three blinking dots) on the in-flight agent while `running`.
- Auto-scrolls to newest message while running (one of the `DebateView` TODOs).

**States:** empty ("Paste a case and hit Begin…"), running (typing indicator + live pulse), error (existing retriable error card, restyled), aborted (Esc still cancels via existing `AbortController`).

### 4.2 `/compare` — closing beat (secondary)

Reuse the §4.1 right-column "stage" as a single reusable unit, rendered **twice side by side**, one per panel, each labeled (e.g. *Single-vendor Sonnet* vs *Calibrated 5-agent*). A shared case chart sits above or to the side. Consumes the existing `compare-sse` stream and `comparison-summary` component (restyled). This is the "two panels, same case, watch them diverge" payoff shot.

### 4.3 `/home` — entry

A calm landing screen in the same system: one-line value prop, a primary "Try a case" CTA into `/diagnose`, and a secondary link to `/compare`. Minimal — it is not a demo focus.

## 5. Component map (restyle, preserve contract)

| Component | Action |
|---|---|
| `routes/Diagnose.tsx` | Re-layout to 2-col + top bar; add derived "leading diagnosis while running" + auto-scroll. Keep all SSE/state logic. |
| `routes/Compare.tsx` | Re-layout to dual-stage; keep stream logic. |
| `routes/Home.tsx` | Restyle to clinical-trust landing. |
| `components/agent-card.tsx` / `agent-message.tsx` | New bubble + avatar + role-color styling; remove token/cost display. Props unchanged. |
| `components/differential-table.tsx` | New ranked-row styling + animated bars. Props unchanged. |
| `components/confidence-meter.tsx` | Render as the conic ring. Props unchanged. |
| `components/case-input.tsx` | Restyle; same `onStart`/`disabled`. |
| `components/next-test-card.tsx`, `citation-panel.tsx`, `iteration-divider.tsx`, `comparison-summary.tsx`, `debate-view.tsx` | Restyle to the system; complete `debate-view` TODOs (divider, sticky header, auto-scroll, empty state). |
| `components/ui/*` (shadcn) | Keep; re-point CSS tokens. No new shadcn components unless a primitive is genuinely missing. |
| `theme-provider.tsx` | Force light for the demo path (§9). |

## 6. Motion (framer-motion, already a dependency)

Restrained, purposeful — never gratuitous (clinical trust):
- Agent message: fade + 6px rise on enter (stagger as they stream in).
- Posterior bars: width tween (~400ms ease-out) when a differential updates.
- Confidence ring: animate the conic sweep to the new posterior.
- Live status dot: CSS pulse. Typing dots: CSS blink.
- Respect `prefers-reduced-motion` (disable transforms/tweens).

## 7. Self-verification & QA (the methodology)

Apply the design-before-build → self-verify → vision-loop methodology the user supplied:
- **`data-verify-*` invariants** on key dynamic nodes (e.g. `data-verify-posterior-sum`, `data-verify-leading`, `data-verify-agent-count`) so a probe can assert the UI reflects the data (posteriors sum ≈ 1.0; leading = rank 1; exactly the agents that spoke are rendered).
- **Co-located component spec** per restyled component (schema / fixture / known-state / invariant / probe) where it adds value.
- **Preview + Chrome MCP self-check:** drive `/diagnose` with a fixture case, screenshot, and run a **vision QA loop** against the locked mockup until they match. Use the Chrome extension for live interaction checks.
- **Gate every change** on: `pnpm lint && pnpm tsc --noEmit && pnpm vitest run` (existing tests must stay green; restyles must not break the `Diagnose`/`Compare` tests' selectors — update test queries only where markup legitimately changes).

## 8. Constraints (hard)

- **No new runtime dependencies.** Tailwind **v3** (pinned), shadcn/ui, framer-motion, lucide-react, react-router-dom only.
- **Agent role colors are locked** (§3) — they are the system's semantic vocabulary.
- **No backend / SSE / data-contract changes.** If a screen needs data the stream doesn't provide, surface it — do not invent backend fields.
- Keep Vite on port 3000; `/api/*` proxy unchanged.
- Backend `pytest` and frontend test suites remain green.

## 9. Non-goals / deferred

- **Dark mode:** the app currently ships a light/dark toggle. For the demo we lock light. We will *keep the dark token block* in `index.css` but remove the toggle from the demo nav so the recording is consistent. (Re-enabling later is a token-value exercise, not a rebuild.)
- Mobile-first polish beyond "doesn't break when narrow" (demo is desktop screen-capture).
- New routes, auth, persistence, or settings.
- The latent **431 bug in `/compare/stream` + `compare-sse.ts`** (GET-with-query). Out of scope for the *visual* redesign but flagged — fix before demoing `/compare`.

## 10. Verification summary

```bash
cd frontend && pnpm install && pnpm lint && pnpm tsc --noEmit && pnpm vitest run
# Visual: drive /diagnose with a fixture, screenshot, vision-compare to locked-C-hifi.html
```
Done when: `/diagnose`, `/compare`, `/home` match the locked mockup's look; all agent roles render in their locked colors; differential/confidence animate on update; tests green; lint+typecheck clean.
