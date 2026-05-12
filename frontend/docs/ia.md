# Information Architecture — `/diagnose`

Locked before component scaffolding so the visual-design pass later doesn't have
to rewire layout. Component skeleton implements this; styling is open.

## Routes

```
/           → Home (hero + "Try the demo" CTA → /diagnose)
/diagnose   → The live demo
```

No 404, no auth, no settings page. v1 surface only.

## `/diagnose` — 3-column layout

```
┌───────────────┬──────────────────────────────┬────────────────────┐
│  CaseInput    │      DebateView (live)       │  Right rail        │
│               │                              │  ┌──────────────┐  │
│  - Textarea   │  ┌────────────────────────┐  │  │ Differential │  │
│  - Sample     │  │ AgentCard: Hypothesis  │  │  │ Table        │  │
│    dropdown   │  │  └─ AgentMessage       │  │  └──────────────┘  │
│  - Begin btn  │  │      with citations    │  │  ┌──────────────┐  │
│  - Status     │  │  └─ (typing indicator) │  │  │ NextTestCard │  │
│    (running/  │  ├────────────────────────┤  │  └──────────────┘  │
│    idle)      │  │ AgentCard: TestChooser │  │  ┌──────────────┐  │
│               │  │  └─ AgentMessage       │  │  │ Confidence   │  │
│               │  ├────────────────────────┤  │  │   Meter      │  │
│               │  │ AgentCard: Challenger  │  │  └──────────────┘  │
│               │  │  └─ AgentMessage       │  │  ┌──────────────┐  │
│               │  ├────────────────────────┤  │  │ Citation     │  │
│               │  │ AgentCard: Stewardship │  │  │   Panel      │  │
│               │  ├────────────────────────┤  │  │ (deduped)    │  │
│               │  │ AgentCard: Checklist   │  │  └──────────────┘  │
│               │  └────────────────────────┘  │                    │
│               │                              │                    │
└───────────────┴──────────────────────────────┴────────────────────┘
   320px              flex-1                       360px
```

Mobile (`< lg`): stack vertically — input → debate → right rail.

## Role color schema

Five agents, five colors. Locked in `tailwind.config.ts` so any future styling
choice references the same tokens.

| Agent | Token | HSL |
|---|---|---|
| Hypothesis | `agent-hypothesis` | `hsl(217, 91%, 60%)` — blue |
| Test-Chooser | `agent-test-chooser` | `hsl(160, 84%, 39%)` — emerald |
| Challenger | `agent-challenger` | `hsl(0, 84%, 60%)` — red |
| Stewardship | `agent-stewardship` | `hsl(43, 96%, 56%)` — amber |
| Checklist | `agent-checklist` | `hsl(280, 91%, 60%)` — violet |

Each `AgentCard` uses its role color for a 4px left-border, the role icon, and
the agent-name pill. Body text stays neutral.

## DebateView streaming semantics

`DebateView` consumes `AgentMessage[]` plus a "currently streaming" flag.

Per-card lifecycle, driven by SSE events from `lib/sse.ts`:

| Event | Card state |
|---|---|
| `agent_start` | Card appears, typing indicator visible, body empty. Framer-motion fade-in + slide-up. |
| `agent_token` | Body accumulates incoming token deltas. Citation chips not yet shown. |
| `agent_complete` | Typing indicator disappears, structured_output renders (Differential top-3 inline, NextTest with cost). Citation chips appear. |
| `round_complete` | Soft divider line inserted between iterations. Iteration counter increments in the header. |
| `verdict` | DebateView dims; right rail's verdict-shaped components light up. |
| `error` | Inline alert at the bottom of the card; debate halts. |

## Citation-chip affordance

Citations are small inline chips with the source (e.g. `NEJM 2024;390:1234`).

- Hover: tooltip with `title` + `excerpt`.
- Click: opens the `CitationPanel` in the right rail, scrolled to that citation.
- Same citation appearing in multiple messages renders once in the deduped panel.

## Confidence meter

A horizontal bar 0–1 with three labeled bands:
- `0.0–0.4` — low (red); right-rail copy: "Recommend further workup"
- `0.4–0.8` — moderate (amber); copy: "Consider next test"
- `0.8–1.0` — high (green); copy: "Differential is well-supported"

Bands are advisory copy only; the actual posterior comes from `FinalVerdict.confidence`.

## Negative space / what we are NOT building this pass

- Multi-case history.
- User accounts.
- "Continue debate" button (panel runs to natural termination or budget cap).
- Export-to-PDF.
- Persistence beyond the active SSE connection.
- Mobile-first UX. Desktop demo first; mobile is "doesn't break" not "delightful".

## Open visual choices (deferred to your styling pass)

- Typography pairing (Inter is the safe default but feel free to swap).
- Background / surface palette (light vs dark — current default is dark).
- Card elevation / shadows.
- Animation tuning beyond fade+slide.
- Hero copy on `/`.
