# Quorum Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the Quorum SPA to the approved "Clinical Chart Split" (Direction C) — case chart left, live ranked differential + streaming 5-agent deliberation right — so the `/diagnose` hero, `/compare` closing beat, and `/home` entry are beautiful, clinical-trust, light-only, and demo-video-ready.

**Architecture:** Pure presentation-layer change. The SSE protocol, `streamDiagnosis`/`streamCompare`, FastAPI, orchestrator, and all data contracts (`FinalVerdict`, `Differential`, `AgentMessage`, `StreamEvent`) are untouched. We (1) re-point the design tokens, (2) add a few stateless presentational primitives, (3) restyle existing components keeping their props + accessible names + test selectors, and (4) re-lay-out the three routes. A small amount of *derived display state* is added (compute "leading diagnosis" from the latest hypothesis differential while running; auto-scroll the feed).

**Tech Stack:** Vite + React 19 + TypeScript, Tailwind v3, shadcn/ui primitives, framer-motion (already installed, ^12.25), lucide-react (already installed). No new runtime dependencies.

---

## Hard invariants (every task must preserve these)

These strings/attributes/testids are asserted by `Diagnose.test.tsx` and `__tests__/Compare.test.tsx`. **Breaking any of them fails the suite — do not change them:**

- CaseInput: textarea placeholder must still match `/clinical vignette/i`; primary button label must still match `/Begin/i` (keep "Begin deliberation" / "Deliberating...").
- Diagnose empty state text must match `/Paste a case/i`.
- The deliberation region must keep `aria-label="Deliberation transcript"` and `aria-live="polite"`.
- The hypothesis message body string `Differential proposed. Top candidate: <name> (<n> total).` is generated in `Diagnose.tsx`/`Compare.tsx` — keep it (tests match `/Differential proposed/i`, `/Disease A/`, `/Pneumonia/`, `/Bronchitis/`).
- Error path: `role="alert"` element containing the error code + message; a button named exactly `Retry` that becomes `Retry used` (disabled) after one click.
- Compare: `getByLabelText(/Panel A/i)` and `/Panel B/i`; `data-testid="column-<panelId>"`; `data-testid="comparison-summary"`; `data-testid="panel-failed-<panelId>"` containing `/Panel failed/i`; disagreement headline matching `/disagree/i`.

**Other constraints:** No backend/SSE/data-contract edits. Agent role colors are locked (`hsl(217 91% 60%)` hypothesis, `hsl(160 84% 39%)` test_chooser, `hsl(0 84% 60%)` challenger, `hsl(43 96% 56%)` stewardship, `hsl(280 91% 60%)` checklist). Light theme only (keep `.dark` token block, just default to light). Honor `prefers-reduced-motion`.

## Verify commands (used throughout)

```bash
cd /Users/lskarada/Documents/Claude/Quorum/frontend
pnpm lint && pnpm tsc --noEmit && pnpm vitest run
```
Live checks use the Preview MCP (`mcp__Claude_Preview__*`) and/or the Claude-in-Chrome extension against the running dev server (Vite :3000, FastAPI :8000). Each route task ends with: load the page, screenshot, read console (zero errors), interact, screenshot again.

## File map

| File | Action | Responsibility |
|---|---|---|
| `frontend/index.html` | Modify | Add Inter + JetBrains Mono font links |
| `frontend/src/index.css` | Modify | Re-point `:root` tokens to clinical-trust light; keep `.dark`; add helper vars + reduced-motion |
| `frontend/tailwind.config.ts` | Modify | Add `fontFamily`, semantic colors, `boxShadow`; keep agent colors |
| `frontend/src/main.tsx` | Modify | Default theme → light |
| `frontend/src/components/ui/confidence-ring.tsx` | Create | Conic-gradient confidence ring |
| `frontend/src/components/agent-avatar.tsx` | Create | Role-colored initial avatar |
| `frontend/src/components/typing-indicator.tsx` | Create | Three blinking dots |
| `frontend/src/components/top-bar.tsx` | Create | Brand + panel chip + live status |
| `frontend/src/components/case-chart.tsx` | Create | Read-only case chart (presentation/demographics/tests/budget) |
| `frontend/src/components/verdict-header.tsx` | Create | Ring + leading dx + termination badge |
| `frontend/src/components/agent-message.tsx` | Modify | Bubble text + citation chips (drop nothing functional) |
| `frontend/src/components/agent-card.tsx` | Modify | Avatar + bubble + role color; plain role labels; no cost line |
| `frontend/src/components/differential-table.tsx` | Modify | Ranked rows, animated bars, mono values, `liveDifferential` prop, `data-verify-posterior-sum` |
| `frontend/src/components/confidence-meter.tsx` | Modify | Render via ConfidenceRing |
| `frontend/src/components/case-input.tsx` | Modify | Restyle; KEEP placeholder + button label |
| `frontend/src/components/next-test-card.tsx` | Modify | Restyle as chip/card |
| `frontend/src/components/citation-panel.tsx` | Modify | Restyle |
| `frontend/src/components/iteration-divider.tsx` | Modify | Restyle |
| `frontend/src/components/comparison-summary.tsx` | Modify | Restyle; KEEP all testids + headline logic |
| `frontend/src/routes/Diagnose.tsx` | Modify | 2-col + top bar + leading-while-running + auto-scroll + `data-verify-*` |
| `frontend/src/routes/Compare.tsx` | Modify | Dual-stage layout; KEEP testids/labels |
| `frontend/src/routes/Home.tsx` | Modify | Clinical-trust landing |
| `frontend/src/components/__tests__/invariants.test.tsx` | Create | data-verify invariant unit tests |

---

## Task 1: Design tokens + fonts + light default

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/index.css`
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Add font links to `index.html`** — inside `<head>`, before the module script:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

- [ ] **Step 2: Re-point tokens in `src/index.css`.** Keep the `@tailwind` directives and the `.dark` block as-is. Replace the `:root` block's values with the clinical-trust light palette and append helper vars. Final `:root` (HSL channel triplets for shadcn vars; hex for helper vars):

```css
  :root {
    --background: 213 33% 95%;        /* #eef2f7 app bg */
    --foreground: 222 47% 11%;        /* #0f172a ink */
    --card: 0 0% 100%;
    --card-foreground: 222 47% 11%;
    --primary: 212 75% 48%;           /* #1e6fd9 brand */
    --primary-foreground: 0 0% 100%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222 47% 11%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215 16% 47%;  /* #64748b */
    --accent: 210 40% 96.1%;
    --accent-foreground: 222 47% 11%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 0 0% 100%;
    --border: 214 32% 91%;            /* #e2e8f0 */
    --input: 214 32% 91%;
    --ring: 212 75% 48%;
    --radius: 0.75rem;
    /* helper tokens (hex; consumed via tailwind extend below) */
    --surface-2: #f8fafc;
    --ink-2: #334155;
    --faint: #94a3b8;
    --line-strong: #cbd5e1;
    --ok: #16a34a;
    --warn: #d97706;
  }
```

- [ ] **Step 3: Append a reduced-motion guard at the end of `src/index.css`:**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
}
```

- [ ] **Step 4: Extend `tailwind.config.ts`.** Inside `theme.extend`, add `fontFamily`, the semantic colors, and `boxShadow` (keep existing `colors` incl. agent colors and `borderRadius`):

```ts
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
```
And add to the `colors` object (alongside the agent colors):
```ts
        "surface-2": "var(--surface-2)",
        "ink-2": "var(--ink-2)",
        faint: "var(--faint)",
        "line-strong": "var(--line-strong)",
        ok: "var(--ok)",
        warn: "var(--warn)",
```
And add after `borderRadius`:
```ts
      boxShadow: {
        "card-1": "0 1px 2px rgba(15,23,42,.05)",
        "card-2": "0 1px 2px rgba(15,23,42,.04), 0 10px 30px rgba(15,23,42,.07)",
      },
      keyframes: {
        blink: { "0%,60%,100%": { opacity: "0.25" }, "30%": { opacity: "1" } },
        livepulse: {
          "0%": { boxShadow: "0 0 0 0 rgba(22,163,74,.45)" },
          "70%": { boxShadow: "0 0 0 7px rgba(22,163,74,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(22,163,74,0)" },
        },
      },
      animation: { blink: "blink 1.2s infinite", livepulse: "livepulse 1.6s infinite" },
```

- [ ] **Step 5: Default to light in `src/main.tsx`** — change `defaultTheme="dark"` to `defaultTheme="light"`.

- [ ] **Step 6: Verify.** Run `pnpm lint && pnpm tsc --noEmit && pnpm vitest run`. Expected: all green (token change doesn't touch markup/selectors). Then live: ensure Vite is up, load `http://localhost:3000/`, screenshot — the page should render on a light `#eef2f7`-ish background with Inter applied. Read console: zero errors.

- [ ] **Step 7: Commit.** `git add frontend/index.html frontend/src/index.css frontend/tailwind.config.ts frontend/src/main.tsx && git commit -m "feat(ui): clinical-trust light design tokens + Inter/JetBrains Mono"`

---

## Task 2: Stateless presentational primitives

**Files:**
- Create: `frontend/src/components/ui/confidence-ring.tsx`
- Create: `frontend/src/components/agent-avatar.tsx`
- Create: `frontend/src/components/typing-indicator.tsx`

- [ ] **Step 1: `confidence-ring.tsx`** — a conic-gradient ring driven by a 0..1 value, animated via framer-motion (falls back gracefully under reduced-motion):

```tsx
import { motion, useReducedMotion } from "framer-motion";

interface ConfidenceRingProps {
  value: number; // 0..1
  size?: number;
  label?: string;
}

const HYP = "hsl(217 91% 60%)";

export function ConfidenceRing({ value, size = 62, label }: ConfidenceRingProps) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const reduce = useReducedMotion();
  const inner = size - 16;
  return (
    <div
      role="img"
      aria-label={label ?? `Confidence ${pct} percent`}
      style={{
        width: size, height: size, borderRadius: "50%",
        background: `conic-gradient(${HYP} 0 ${pct}%, #e8eef6 ${pct}% 100%)`,
        display: "flex", alignItems: "center", justifyContent: "center", flex: "none",
      }}
    >
      <div style={{
        width: inner, height: inner, borderRadius: "50%", background: "#fff",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <motion.span
          className="font-mono font-extrabold text-agent-hypothesis"
          style={{ fontSize: size * 0.24 }}
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {pct}%
        </motion.span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: `agent-avatar.tsx`** — role initial in a rounded square, role color:

```tsx
import type { AgentRole } from "@/lib/types";

const INITIAL: Record<AgentRole, string> = {
  hypothesis: "H", test_chooser: "T", challenger: "C", stewardship: "S", checklist: "K",
};
const BG: Record<AgentRole, string> = {
  hypothesis: "bg-agent-hypothesis", test_chooser: "bg-agent-test-chooser",
  challenger: "bg-agent-challenger", stewardship: "bg-agent-stewardship", checklist: "bg-agent-checklist",
};
const FG: Record<AgentRole, string> = {
  hypothesis: "text-white", test_chooser: "text-white", challenger: "text-white",
  stewardship: "text-[#3a2c00]", checklist: "text-white",
};

export function AgentAvatar({ role }: { role: AgentRole }) {
  return (
    <span aria-hidden className={`flex h-[30px] w-[30px] flex-none items-center justify-center rounded-[9px] text-[11px] font-extrabold ${BG[role]} ${FG[role]}`}>
      {INITIAL[role]}
    </span>
  );
}
```

- [ ] **Step 3: `typing-indicator.tsx`:**

```tsx
export function TypingIndicator() {
  return (
    <span className="inline-flex items-center gap-[3px] align-middle" aria-label="thinking">
      <i className="h-[5px] w-[5px] rounded-full bg-faint animate-blink" />
      <i className="h-[5px] w-[5px] rounded-full bg-faint animate-blink [animation-delay:.2s]" />
      <i className="h-[5px] w-[5px] rounded-full bg-faint animate-blink [animation-delay:.4s]" />
    </span>
  );
}
```

- [ ] **Step 4: Verify.** `pnpm lint && pnpm tsc --noEmit && pnpm vitest run` — green (new files, no consumers yet).
- [ ] **Step 5: Commit.** `git add frontend/src/components/ui/confidence-ring.tsx frontend/src/components/agent-avatar.tsx frontend/src/components/typing-indicator.tsx && git commit -m "feat(ui): confidence ring, agent avatar, typing indicator primitives"`

---

## Task 3: Restyle agent message + agent card

**Files:**
- Modify: `frontend/src/components/agent-message.tsx`
- Modify: `frontend/src/components/agent-card.tsx`

- [ ] **Step 1: `agent-message.tsx`** — keep props/content; restyle text to `text-[13px] leading-relaxed text-ink-2`; keep citation chips (restyle to `rounded-full border border-line-strong`). The message text element stays a `<p>` rendering `message.content` verbatim (test depends on it).

- [ ] **Step 2: `agent-card.tsx`** — rewrite to avatar + role-colored bubble, plain role labels, **no token/cost line**:

```tsx
import { AgentMessage as MessageBubble } from "@/components/agent-message";
import { AgentAvatar } from "@/components/agent-avatar";
import { cn } from "@/lib/utils";
import type { AgentMessage, AgentRole } from "@/lib/types";

const ROLE_LABEL: Record<AgentRole, string> = {
  hypothesis: "Hypothesis", test_chooser: "Test Chooser", challenger: "Challenger",
  stewardship: "Stewardship", checklist: "Checklist",
};
const ROLE_LEFT: Record<AgentRole, string> = {
  hypothesis: "border-l-agent-hypothesis", test_chooser: "border-l-agent-test-chooser",
  challenger: "border-l-agent-challenger", stewardship: "border-l-agent-stewardship",
  checklist: "border-l-agent-checklist",
};
const ROLE_TEXT: Record<AgentRole, string> = {
  hypothesis: "text-agent-hypothesis", test_chooser: "text-agent-test-chooser",
  challenger: "text-agent-challenger", stewardship: "text-[#a8780a]", checklist: "text-agent-checklist",
};

export function AgentCard({ message }: { message: AgentMessage }) {
  return (
    <div className="flex gap-3" data-agent={message.role}>
      <AgentAvatar role={message.role} />
      <div className={cn("flex-1 rounded-xl border border-line bg-surface-2 border-l-[3px] px-3.5 py-2.5", ROLE_LEFT[message.role])}>
        <div className={cn("mb-1 text-[11px] font-extrabold uppercase tracking-wide", ROLE_TEXT[message.role])}>
          {ROLE_LABEL[message.role]}
        </div>
        <MessageBubble message={message} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify.** `pnpm vitest run` — `Diagnose.test` (`/Differential proposed/i`, `/Disease A/`) and `Compare.test` (`/Pneumonia/`, `/Bronchitis/`) still pass because `message.content` is rendered unchanged. Then `pnpm lint && pnpm tsc --noEmit`.
- [ ] **Step 4: Commit.** `git add frontend/src/components/agent-message.tsx frontend/src/components/agent-card.tsx && git commit -m "feat(ui): agent card as avatar + role-colored bubble, drop cost line"`

---

## Task 4: Restyle differential table + confidence meter (with live data)

**Files:**
- Modify: `frontend/src/components/differential-table.tsx`
- Modify: `frontend/src/components/confidence-meter.tsx`

- [ ] **Step 1: `differential-table.tsx`** — add optional `liveDifferential` prop (additive, backward compatible), render ranked rows with framer-motion-animated bars + mono posteriors, and a `data-verify-posterior-sum` attribute (rounded sum of shown posteriors) for the invariant probe:

```tsx
import { motion } from "framer-motion";
import type { Differential, FinalVerdict } from "@/lib/types";

interface DifferentialTableProps {
  verdict: FinalVerdict | null;
  liveDifferential?: Differential | null;
}

export function DifferentialTable({ verdict, liveDifferential }: DifferentialTableProps) {
  const diff = verdict?.final_differential ?? liveDifferential ?? null;
  const candidates = diff?.candidates.slice(0, 5) ?? [];
  const sum = candidates.reduce((a, c) => a + c.posterior, 0);

  if (candidates.length === 0) {
    return <p className="text-sm text-muted-foreground">Awaiting first differential…</p>;
  }
  return (
    <ul className="space-y-0" data-verify-posterior-sum={sum.toFixed(2)}>
      {candidates.map((c, idx) => (
        <li key={idx} className="flex items-center gap-3 border-b border-line py-2 last:border-b-0">
          <span className="w-4 text-xs font-extrabold text-faint">{idx + 1}</span>
          <span className="flex-1 text-[13.5px] font-semibold">
            {c.name}
            {c.rationale && <small className="block text-[11.5px] font-normal text-muted-foreground">{c.rationale}</small>}
          </span>
          <span className="h-2 w-[140px] overflow-hidden rounded bg-line">
            <motion.span
              className={idx === 0 ? "block h-full bg-agent-hypothesis" : "block h-full bg-faint"}
              initial={{ width: 0 }} animate={{ width: `${Math.round(c.posterior * 100)}%` }}
              transition={{ duration: 0.4, ease: "easeOut" }}
            />
          </span>
          <span className={`w-[42px] text-right font-mono text-[13px] font-semibold ${idx === 0 ? "text-agent-hypothesis" : "text-muted-foreground"}`}>
            {c.posterior.toFixed(2)}
          </span>
        </li>
      ))}
    </ul>
  );
}
```
Note: the card heading ("Differential") now lives in the parent (`verdict-header`/route), so this component renders just the list. No test asserts the old heading.

- [ ] **Step 2: `confidence-meter.tsx`** — render via `ConfidenceRing` plus the band copy; keep `{verdict}` prop and the null guard:

```tsx
import { ConfidenceRing } from "@/components/ui/confidence-ring";
import type { FinalVerdict } from "@/lib/types";

function bandFor(v: number) {
  if (v < 0.4) return "Recommend further workup";
  if (v < 0.8) return "Consider next test";
  return "Differential is well-supported";
}

export function ConfidenceMeter({ verdict }: { verdict: FinalVerdict | null }) {
  if (!verdict) return null;
  return (
    <div className="flex items-center gap-3">
      <ConfidenceRing value={verdict.confidence} size={52} />
      <p className="text-xs text-muted-foreground">{bandFor(verdict.confidence)}</p>
    </div>
  );
}
```

- [ ] **Step 3: Verify.** `pnpm vitest run`. `Diagnose.test` finds `/Disease A/` via the differential list (verdict path renders names) — still passes. `pnpm lint && pnpm tsc --noEmit`.
- [ ] **Step 4: Commit.** `git add frontend/src/components/differential-table.tsx frontend/src/components/confidence-meter.tsx && git commit -m "feat(ui): ranked differential with animated bars + live data; confidence ring"`

---

## Task 5: New composite components — top bar, case chart, verdict header; restyle small cards

**Files:**
- Create: `frontend/src/components/top-bar.tsx`
- Create: `frontend/src/components/case-chart.tsx`
- Create: `frontend/src/components/verdict-header.tsx`
- Modify: `frontend/src/components/case-input.tsx`
- Modify: `frontend/src/components/next-test-card.tsx`
- Modify: `frontend/src/components/citation-panel.tsx`
- Modify: `frontend/src/components/iteration-divider.tsx`

- [ ] **Step 1: `top-bar.tsx`** — brand mark + optional panel chip + live status (pulsing dot when `running`):

```tsx
interface TopBarProps { panelLabel?: string; status?: string; running?: boolean; }
export function TopBar({ panelLabel, status, running }: TopBarProps) {
  return (
    <div className="flex items-center gap-3.5 rounded-xl border border-line bg-card px-[18px] py-3 shadow-card-1">
      <div className="flex items-center gap-2 text-[17px] font-extrabold tracking-tight">
        <span className="h-[22px] w-[22px] rounded-md" style={{ background: "linear-gradient(135deg, hsl(217 91% 60%), hsl(280 91% 60%))" }} />
        Quorum
      </div>
      {panelLabel && (
        <span className="ml-1 flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-2.5 py-1 text-[12.5px] text-muted-foreground">
          Panel: <b className="font-semibold text-ink-2">{panelLabel}</b>
        </span>
      )}
      {status && (
        <span className="ml-auto flex items-center gap-2 text-[12.5px] font-semibold text-ink-2">
          {running && <span className="h-2 w-2 rounded-full bg-ok animate-livepulse" />}
          {status}
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 2: `case-chart.tsx`** — read-only chart shown once a run starts. Props are display-only data the route already has:

```tsx
import type { NextTest } from "@/lib/types";
interface CaseChartProps { presentation: string; testsOrdered?: NextTest[]; }
export function CaseChart({ presentation, testsOrdered = [] }: CaseChartProps) {
  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1.5 text-[10.5px] font-extrabold uppercase tracking-wide text-faint">Presentation</div>
        <div className="whitespace-pre-wrap rounded-lg border border-line bg-surface-2 p-3 text-[13px] leading-relaxed text-ink-2">{presentation}</div>
      </div>
      {testsOrdered.length > 0 && (
        <div>
          <div className="mb-1.5 text-[10.5px] font-extrabold uppercase tracking-wide text-faint">Tests ordered</div>
          <div className="flex flex-wrap gap-1.5">
            {testsOrdered.map((t, i) => (
              <span key={i} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-card px-2.5 py-1 text-xs font-semibold">
                <span className="h-2 w-2 rounded-full bg-agent-test-chooser" />{t.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: `verdict-header.tsx`** — ring + leading dx + termination badge. Accepts the live leading candidate (while running) or final verdict:

```tsx
import { ConfidenceRing } from "@/components/ui/confidence-ring";
import type { Differential, FinalVerdict } from "@/lib/types";

const TERM_LABEL: Record<string, string> = {
  consensus: "Consensus reached", max_iterations: "Max iterations", budget: "Budget reached",
  checklist_stop: "Checklist stop", error: "Panel error",
};

interface VerdictHeaderProps { verdict: FinalVerdict | null; liveDifferential?: Differential | null; }
export function VerdictHeader({ verdict, liveDifferential }: VerdictHeaderProps) {
  const diff = verdict?.final_differential ?? liveDifferential ?? null;
  const top = diff?.candidates[0] ?? null;
  const value = verdict ? verdict.confidence : (top?.posterior ?? 0);
  if (!top) return null;
  const term = verdict ? TERM_LABEL[verdict.termination_reason] ?? verdict.termination_reason : null;
  return (
    <div className="flex items-center gap-3.5" data-verify-leading={top.name}>
      <ConfidenceRing value={value} />
      <div>
        <div className="text-[10.5px] font-extrabold uppercase tracking-wide text-faint">Leading diagnosis</div>
        <div className="text-lg font-extrabold tracking-tight">{top.name}</div>
        <div className="text-[12.5px] text-muted-foreground">{diff?.candidates.length ?? 0} candidates</div>
      </div>
      {term && (
        <span className={`ml-auto rounded-full border px-3 py-1.5 text-[11.5px] font-bold ${verdict?.is_error ? "border-red-200 bg-red-50 text-red-700" : "border-green-200 bg-green-50 text-ok"}`}>
          ● {term}
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 4: `case-input.tsx`** — restyle to the system but **keep the heading, the placeholder `clinical vignette`, the button label `Begin deliberation`/`Deliberating...`, and the `onStart`/`disabled` contract**. Only class names change (e.g. larger primary button `bg-primary text-primary-foreground`, card chrome handled by parent).

- [ ] **Step 5: `next-test-card.tsx`** — restyle (system colors, mono cost). Keep `{verdict, nextTest}` and null-return. Add green left accent (test_chooser color).

- [ ] **Step 6: `citation-panel.tsx`** — restyle list (system colors). Keep `{verdict}`, dedupe, null-return.

- [ ] **Step 7: `iteration-divider.tsx`** — restyle to a centered uppercase label between thin rules using `text-faint`/`border-line`; keep `Iteration N` (one-indexed) and `role="separator"`.

- [ ] **Step 8: Verify.** `pnpm lint && pnpm tsc --noEmit && pnpm vitest run` — green (new components unused yet; case-input restyle preserves selectors).
- [ ] **Step 9: Commit.** `git add frontend/src/components && git commit -m "feat(ui): top bar, case chart, verdict header; restyle case/next-test/citation/divider"`

---

## Task 6: Re-lay-out `/diagnose` (the hero) + live verification

**Files:**
- Modify: `frontend/src/routes/Diagnose.tsx`

- [ ] **Step 1: Add derived state.** Keep all existing SSE/stream logic, `handleStart`, error/retry, Esc-abort, and `messageFromAgentComplete` (with its `Differential proposed…` content string). Add:
  - `submittedPresentation` state set on `handleStart` (for the case chart).
  - `liveDifferential`: derive from the most recent hypothesis `agent_complete` — track `const [liveDifferential, setLiveDifferential] = useState<Differential | null>(null)` and set it in the `agent_complete` branch when `evt.data.agent === "hypothesis"` (`setLiveDifferential(evt.data.differential)`).
  - `testsOrdered`: accumulate `NextTest` from `test_chooser` events into an array (dedupe by name) for the case chart chips.
  - `feedEndRef` (a `<div>` at the end of the feed); in a `useEffect` on the messages, call `feedEndRef.current?.scrollIntoView({ block: "end" })` while `running`.

- [ ] **Step 2: New layout.** Replace the 3-col `<main>` with: a `TopBar` (panelLabel `"v2 · 5-agent calibrated"`, status = `running ? \`Deliberating · round ${currentRound} of …\` : verdict ? "Complete" : "Idle"`, `running`), then a 2-col grid `lg:grid-cols-[380px_1fr]`:
  - **Left card:** before first run (`!running && !hasAnyMessages && !verdict`) render `<CaseInput .../>`; otherwise render `<CaseChart presentation={submittedPresentation} testsOrdered={testsOrdered} />`. Keep the error/retry block here (`role="alert"`, `Retry`/`Retry used`).
  - **Right column** (`space-y-4`):
    - Verdict card: `<VerdictHeader verdict={verdict} liveDifferential={liveDifferential} />` + `<DifferentialTable verdict={verdict} liveDifferential={liveDifferential} />`.
    - Deliberation card: header "Deliberation"; the section element keeps `aria-live="polite"`, `aria-busy={running}`, **`aria-label="Deliberation transcript"`**, and `data-verify-agent-count` = number of rendered messages in the last iteration; iteration dividers + `AgentCard`s; a `TypingIndicator` row while `running`; the empty state text **`Paste a case and hit Begin to start the deliberation.`**; `feedEndRef` div.
    - `<NextTestCard verdict={verdict} nextTest={nextTest} />` and `<CitationPanel verdict={verdict} />` below (unchanged props).
  - Wrap each card in `<div className="rounded-2xl border border-line bg-card p-[18px] shadow-card-2">` (or a restyled shadcn `Card`).

- [ ] **Step 3: Motion.** Wrap each `AgentCard` in `motion.div` with `initial={{opacity:0,y:6}} animate={{opacity:1,y:0}}` (guarded by `useReducedMotion`).

- [ ] **Step 4: Verify (tests).** `pnpm vitest run` — confirm `Diagnose.test.tsx` all pass: empty state `/Paste a case/i`; `/Begin/i` disabled when empty; region `aria-live="polite"` via label "Deliberation transcript"; `/Differential proposed/i` + `/Disease A/`; `role="alert"` + `provider_429` + `Retry`/`Retry used`; Begin disabled-while-running. Then `pnpm lint && pnpm tsc --noEmit`.

- [ ] **Step 5: Verify (LIVE — required).** With Vite (:3000) + FastAPI (:8000) running:
  1. Preview/Chrome: navigate to `http://localhost:3000/diagnose`. Screenshot. Console must be clean.
  2. Paste a short vignette into the textarea; click "Begin deliberation".
  3. Watch the stream: agent bubbles appear in role colors with avatars; the differential bars animate; the confidence ring fills; a typing indicator shows while running; on verdict, the termination badge appears and the case chart shows on the left.
  4. Screenshot the running state and the final state. Compare visually to `.superpowers/brainstorm/80606-1780288473/content/locked-C-hifi.html`. Read console again: zero errors/warnings (React key warnings count as failures — fix them).
  5. If the backend isn't reachable, trigger the error path and confirm the alert + Retry render correctly.

- [ ] **Step 6: Commit.** `git add frontend/src/routes/Diagnose.tsx && git commit -m "feat(ui): /diagnose clinical chart-split layout (Direction C hero)"`

---

## Task 7: Re-lay-out `/compare` + restyle comparison summary + live verification

**Files:**
- Modify: `frontend/src/routes/Compare.tsx`
- Modify: `frontend/src/components/comparison-summary.tsx`

- [ ] **Step 1: `comparison-summary.tsx`** — restyle to the system (rounded cards, mono numbers, system border colors) but **keep**: `data-testid="comparison-summary"`, the `Row` layout, `data-testid={`panel-failed-${panelId}`}` cell with text **`Panel failed`**, and the headline logic that yields `/disagree/i` on two distinct top candidates. Map border classes to the new palette (error→`border-red-400`, agree→`border-ok`, disagree→`border-warn`).

- [ ] **Step 2: `Compare.tsx`** — keep all stream logic, `routeEvent`, `PanelSelect` (labels **`Panel A`/`Panel B`**), and `PanelColumn` `data-testid="column-<id>"`. Re-skin: add a `TopBar` (status from `running`); put the two `PanelColumn`s into two equal "stage" cards side by side (`md:grid-cols-2`), each with a small header showing the panel name; render each panel's latest hypothesis differential via `DifferentialTable` above its `AgentCard` feed (reuse derived-leading logic per panel — optional; minimum is the restyled feed). Keep `ComparisonSummary` mount when `bothVerdictsIn`. Keep `CaseInput` (selectors preserved).

- [ ] **Step 3: Verify (tests).** `pnpm vitest run` — `Compare.test.tsx` passes: Panel A/B values, `column-alpha`/`column-beta` contain `Pneumonia`/`Bronchitis`, `comparison-summary` present, `/disagree/i`, `panel-failed-beta` → `Panel failed`. Then `pnpm lint && pnpm tsc --noEmit`.

- [ ] **Step 4: Verify (LIVE — required).** Navigate to `http://localhost:3000/compare`. Confirm panel selectors load from `/api/panels`. Pick two distinct panels, paste a vignette, Begin. Confirm both columns stream side by side, the summary renders, no console errors. Screenshot. **Note:** if `/compare/stream` 431s on a long case (known latent GET-query bug, see spec §9), use a short case for the demo and flag it; do not fix the backend route in this task.

- [ ] **Step 5: Commit.** `git add frontend/src/routes/Compare.tsx frontend/src/components/comparison-summary.tsx && git commit -m "feat(ui): /compare dual-stage layout + restyled comparison summary"`

---

## Task 8: Restyle `/home` + live verification

**Files:**
- Modify: `frontend/src/routes/Home.tsx`

- [ ] **Step 1:** Restyle the landing to the clinical-trust system: a `TopBar` (no status), a centered hero with the brand, a one-line value prop, the existing copy (refine to one tight sentence), and the two CTAs (`Try the demo` → `/diagnose` primary; `Compare panels` → `/compare` secondary). Use `bg-background`, `text-foreground`, brand button. Keep the `react-router-dom` `Link`s.

- [ ] **Step 2: Verify (tests).** `pnpm lint && pnpm tsc --noEmit && pnpm vitest run` — green.
- [ ] **Step 3: Verify (LIVE).** Navigate to `http://localhost:3000/`. Screenshot. Click "Try the demo" → lands on `/diagnose`. Console clean.
- [ ] **Step 4: Commit.** `git add frontend/src/routes/Home.tsx && git commit -m "feat(ui): clinical-trust landing page"`

---

## Task 9: data-verify invariant tests

**Files:**
- Create: `frontend/src/components/__tests__/invariants.test.tsx`

- [ ] **Step 1: Write the test** — render `VerdictHeader` + `DifferentialTable` with a fixture differential and assert the invariants:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerdictHeader } from "@/components/verdict-header";
import { DifferentialTable } from "@/components/differential-table";
import type { Differential } from "@/lib/types";

const diff: Differential = {
  candidates: [
    { name: "Giant-cell myocarditis", posterior: 0.78, rationale: "r" },
    { name: "Cardiac sarcoidosis", posterior: 0.16, rationale: "r" },
    { name: "Lymphoma", posterior: 0.06, rationale: "r" },
  ],
  iteration: 1,
};

describe("data-verify invariants", () => {
  it("leading diagnosis = rank-1 candidate", () => {
    const { container } = render(<VerdictHeader verdict={null} liveDifferential={diff} />);
    expect(container.querySelector("[data-verify-leading]")?.getAttribute("data-verify-leading"))
      .toBe("Giant-cell myocarditis");
  });
  it("shown posteriors sum to ~1.0", () => {
    const { container } = render(<DifferentialTable verdict={null} liveDifferential={diff} />);
    const sum = Number(container.querySelector("[data-verify-posterior-sum]")?.getAttribute("data-verify-posterior-sum"));
    expect(sum).toBeGreaterThan(0.99);
    expect(sum).toBeLessThan(1.01);
  });
  it("renders one row per candidate", () => {
    render(<DifferentialTable verdict={null} liveDifferential={diff} />);
    expect(screen.getByText("Giant-cell myocarditis")).toBeInTheDocument();
    expect(screen.getByText("Lymphoma")).toBeInTheDocument();
  });
});
```

- [x] **Step 2: Run** `pnpm vitest run src/components/__tests__/invariants.test.tsx` — expect 3 pass.
- [x] **Step 3: Commit.** `git add frontend/src/components/__tests__/invariants.test.tsx && git commit -m "test(ui): data-verify invariants for leading dx + posterior sum"`

---

## Task 10: Full-suite gate + live stress test across all routes

- [x] **Step 1: Full frontend gate.** `cd frontend && pnpm install && pnpm lint && pnpm tsc --noEmit && pnpm vitest run` — everything green. (lint 0 errors / 2 pre-existing warnings; tsc clean; vitest 25 passed across 7 files)
- [x] **Step 2: Backend sanity (no behavior changed, but confirm nothing broke).** `cd backend && uv run pytest -q` — green. (262 passed)
- [x] **Step 3: Production build smoke.** `cd frontend && pnpm build` — succeeds (tsc -b + vite build), no type errors. (dist 420.43 KB JS / 20.43 KB CSS)
- [x] **Step 4: Live stress test (required, Chrome extension preferred; Preview MCP fallback).** With both servers up:
  - `/` → `/diagnose` → ran a real `v2_quorum_calibrated` case end-to-end (5 agents in order, 82% ring, "Consensus reached", collapse-to-chart + "New case"); aborted mid-run with Esc → clean stop (status "Idle", aria-busy false, partial retained, no banner); error path `?panel=__nonexistent_panel__` → 422 → role="alert" banner, console clean.
  - `/compare` → ran two panels; both columns streamed (CRLF framing fix verified), no `parse_failure`, summary rendered, console clean.
  - Resized narrow (375px) → both `/diagnose` and `/compare` stack to a single 343px column, zero horizontal overflow; `/compare` splits to two equal columns at 768px.
  - For each route: console clean (the `net::ERR_ABORTED` entries are the expected signature of clean AbortController.abort(), not errors); screenshots captured; `/diagnose` visually matches the locked mockup.
- [x] **Step 5: Final commit (if any cleanup).** No remaining redesign changes to commit (Tasks 1–9 fully committed; only untracked `data/results/.holdout_*` campaign artifacts remain and are intentionally excluded). Proceeding to `superpowers:finishing-a-development-branch`.

---

## Self-review notes (author)

- **Spec coverage:** §3 tokens → Task 1; §4.1 hero → Tasks 2–6; §4.2 compare → Task 7; §4.3 home → Task 8; §5 component map → Tasks 3–8; §6 motion → Tasks 2,4,6; §7 self-verification → Tasks 6/7/9 + live steps; §8 constraints → invariants block + per-task selector callouts; §9 dark-mode parked → Task 1 step 5 (default light, `.dark` retained); 431 note → Task 7 step 4.
- **No new deps:** framer-motion + lucide-react already in `package.json`; fonts via `<link>`, not npm.
- **Type consistency:** `liveDifferential?: Differential | null` used identically in `DifferentialTable` and `VerdictHeader`; `AgentRole` maps reuse the locked names; `FinalVerdict.termination_reason` union matches `TERM_LABEL` keys.
- **Test-selector safety:** every restyle task restates the strings/testids it must preserve.
