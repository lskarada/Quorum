import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TopBar } from "@/components/top-bar";

/* ------------------------------------------------------------------ *
 * Clinician-engagement content.
 *
 * PRIVACY NOTE: participants are de-identified — attributed by setting
 * and role only, never by name or identifiable organization. Settings
 * and themes are paraphrased to protect anonymity.
 * ------------------------------------------------------------------ */
const ENGAGEMENT_DRAFT = false;

/** Institution *types* only — no individual names or identifiable orgs. */
const SETTINGS: string[] = [
  "Community / outpatient clinic systems",
  "An academic medical center",
  "Independent primary-care practice",
];

/** What we heard, paired with how Quorum's design responds. Edit freely. */
const ENGAGEMENT_THEMES: { heard: string; response: string }[] = [
  {
    heard:
      "“I won't act on a black-box suggestion — I need to see the reasoning, not just the answer.”",
    response:
      "Quorum streams the full five-agent deliberation and writes an append-only audit trail a reviewer can replay turn-by-turn.",
  },
  {
    heard:
      "“A confident wrong answer is more dangerous than an uncertain one. Tell me how sure the model is.”",
    response:
      "Quorum reports calibrated per-diagnosis posteriors (Brier + ECE), instead of a single unqualified top pick.",
  },
  {
    heard:
      "“Don't drown me in output mid-shift. Give me the headline, let me drill in if I want.”",
    response:
      "The differential leads with a ranked headline; the transcript and citations are there to expand, not forced on the reader.",
  },
  {
    heard:
      "“This has to support my judgment, not replace it — and it can't order tests on its own.”",
    response:
      "Quorum is positioned as non-device, clinician-in-loop decision support: it recommends a next test and a differential; the clinician decides.",
  },
];

type Ref = { n: number; cite: string; url: string };

const REFS: Ref[] = [
  {
    n: 1,
    cite:
      "Nori et al. “Sequential Diagnosis with Language Models” (MAI-DxO). arXiv:2506.22405, Microsoft Research, 2025.",
    url: "https://arxiv.org/abs/2506.22405",
  },
  {
    n: 2,
    cite:
      "“Trust in AI-Based Clinical Decision Support Systems Among Healthcare Workers: A Systematic Review.” JMIR, 2025.",
    url: "https://www.jmir.org/2025/1/e69678",
  },
  {
    n: 3,
    cite:
      "“Across generations, sizes, and types, LLMs poorly report self-confidence in clinical reasoning.” npj Gut & Liver, 2026.",
    url: "https://www.nature.com/articles/s44355-026-00053-3",
  },
  {
    n: 4,
    cite:
      "Tu et al. “Towards Conversational Diagnostic AI” (AMIE). Nature / arXiv:2401.05654, 2025.",
    url: "https://arxiv.org/abs/2401.05654",
  },
  {
    n: 5,
    cite:
      "FDA. “Clinical Decision Support Software” — Final Guidance, Mar 11, 2026.",
    url: "https://www.fda.gov/media/191560/download",
  },
];

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-[12px] font-bold uppercase tracking-[0.14em] text-faint">
      {children}
    </p>
  );
}

function RefSup({ ids }: { ids: number[] }) {
  return (
    <sup className="ml-0.5 text-[11px] font-semibold text-primary">
      [{ids.join(",")}]
    </sup>
  );
}

/* ------------------------------------------------------------------ *
 * Benchmark comparison — designed against Tufte's display rules:
 *  • zero baseline, length ∝ value (lie factor ≈ 1)
 *  • both panels share one 0–100% scale, so the 2.5× gap is true to the eye
 *  • direct value labels (no legend); one accent (Quorum = ok green),
 *    muted slate for the baseline, faint frame for the 0–100 range
 *  • n, k, units and grading source disclosed in the figure caption
 *  • honest precision: one decimal, matching the underlying fractions
 * Numbers verified from data/results/v3-holdout-{sc,baseline}-voted.
 * ------------------------------------------------------------------ */
type BenchArm = {
  name: string;
  sub: string;
  pct: number;
  frac: string;
  accent: boolean;
};

const BENCH: {
  scaleNote: string;
  metrics: { label: string; delta: string; arms: BenchArm[] }[];
} = {
  scaleNote:
    "n = 12 NEJM-2026 holdout cases · each arm is the modal vote over k = 5 replicas · graded full / partial / none by an LLM judge against the published final diagnosis · values are percent of cases.",
  metrics: [
    {
      label: "Top-1 — exact match",
      delta: "2.5× baseline",
      arms: [
        {
          name: "Quorum",
          sub: "5-agent + SafetyChecker",
          pct: 41.7,
          frac: "5 / 12",
          accent: true,
        },
        {
          name: "Single-model baseline",
          sub: "same model, one call",
          pct: 16.7,
          frac: "2 / 12",
          accent: false,
        },
      ],
    },
    {
      label: "Top-1 or partial credit",
      delta: "+16.7 pts",
      arms: [
        {
          name: "Quorum",
          sub: "5-agent + SafetyChecker",
          pct: 75.0,
          frac: "9 / 12",
          accent: true,
        },
        {
          name: "Single-model baseline",
          sub: "same model, one call",
          pct: 58.3,
          frac: "7 / 12",
          accent: false,
        },
      ],
    },
  ],
};

function BenchmarkChart() {
  return (
    <figure className="m-0 flex flex-col gap-6">
      <div className="grid gap-x-10 gap-y-7 sm:grid-cols-2">
        {BENCH.metrics.map((m) => (
          <div key={m.label} className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between gap-2 border-b border-line pb-1.5">
              <span className="text-[12px] font-bold uppercase tracking-[0.12em] text-ink-2">
                {m.label}
              </span>
              <span className="font-mono text-[11px] font-semibold text-faint">
                {m.delta}
              </span>
            </div>

            <div className="flex flex-col gap-3.5">
              {m.arms.map((a) => (
                <div key={a.name} className="flex flex-col gap-1.5">
                  <div className="flex items-baseline justify-between gap-3">
                    <span
                      className={
                        a.accent
                          ? "text-[12.5px] font-semibold text-ink-2"
                          : "text-[12.5px] text-muted-foreground"
                      }
                    >
                      {a.name}
                      <span className="ml-1.5 text-[10.5px] font-normal text-faint">
                        {a.sub}
                      </span>
                    </span>
                    <span className="shrink-0 tabular-nums">
                      <span
                        className={
                          a.accent
                            ? "font-mono text-[13px] font-bold text-ok"
                            : "font-mono text-[13px] font-bold text-ink-2"
                        }
                      >
                        {a.pct.toFixed(1)}%
                      </span>
                      <span className="ml-1.5 font-mono text-[10.5px] text-faint">
                        {a.frac}
                      </span>
                    </span>
                  </div>
                  <div
                    className="h-2.5 w-full rounded-[3px] bg-foreground/[0.06]"
                    role="img"
                    aria-label={`${a.name}: ${a.pct.toFixed(1)} percent (${a.frac})`}
                  >
                    <div
                      className={
                        a.accent
                          ? "h-full rounded-[3px] bg-ok"
                          : "h-full rounded-[3px] bg-faint"
                      }
                      style={{ width: `${a.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-between font-mono text-[10px] text-faint">
              <span>0%</span>
              <span>100%</span>
            </div>
          </div>
        ))}
      </div>
      <figcaption className="border-t border-line pt-3 text-[11.5px] leading-relaxed text-faint">
        {BENCH.scaleNote}
      </figcaption>
    </figure>
  );
}

export default function Evidence() {
  return (
    <main className="mx-auto flex min-h-screen max-w-[1080px] flex-col gap-5 bg-background p-4 text-foreground">
      <TopBar status="Evidence & clinical grounding" />

      {/* Hero ------------------------------------------------------- */}
      <section className="flex flex-col gap-3 px-1 pt-2">
        <SectionLabel>Evidence</SectionLabel>
        <h1 className="text-4xl font-extrabold tracking-tight">
          Does deliberation actually help — and do clinicians trust it?
        </h1>
        <p className="max-w-3xl text-base text-muted-foreground">
          Quorum is evaluated three ways: a decontaminated, run-once accuracy
          benchmark on NEJM cases; a calibration story the closed reference
          system never reports; and direct conversations with practicing
          clinicians about what would make decision support usable at the
          bedside.
        </p>
      </section>

      {/* 1. Benchmark --------------------------------------------------- */}
      <Card className="shadow-card-2">
        <CardHeader>
          <SectionLabel>1 · Benchmark accuracy</SectionLabel>
          <CardTitle>NEJM-2026 holdout — decontaminated, run once</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            12 NEJM Clinical-Pathological-Conference cases from 2026, screened
            for training-data contamination and scored a single time — no tuning
            on the holdout. Both arms call the same underlying model; Quorum adds
            the five-agent deliberation and SafetyChecker on top of it.
          </p>

          <BenchmarkChart />

          <p className="text-sm text-ink-2">
            Deliberation + safety gating <b>2.5× the exact-match rate</b> (16.7%
            → 41.7%) over the same model called once, on cases neither arm had
            seen.
          </p>

          <div className="rounded-xl border border-line bg-surface-2 p-4 text-[13px] text-muted-foreground">
            <b className="text-ink-2">Reference points (literature).</b> On the
            broader 304-case SDBench set, the closed MAI-DxO reaches 85.5% and a
            cohort of unaided physicians ~20%.<RefSup ids={[1]} /> Those numbers
            are not directly comparable to our 12-case holdout — they frame the
            ceiling and floor, not a head-to-head.
          </div>

          <div>
            <Button asChild variant="outline" size="sm">
              <a href="https://github.com/lskarada/Quorum/blob/main/docs/eval_methodology.md">
                Read the eval methodology →
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 2. Calibration ------------------------------------------------- */}
      <Card className="shadow-card-2">
        <CardHeader>
          <SectionLabel>2 · Calibration</SectionLabel>
          <CardTitle>Honest uncertainty, not just an answer</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground">
          <p>
            Medical LLMs are systematically overconfident — even the
            best-calibrated frontier models report confidence poorly on clinical
            reasoning.<RefSup ids={[3]} /> A confidently wrong diagnosis is the
            failure mode clinicians fear most.
          </p>
          <p>
            So Quorum treats calibration as a <b>first-class, reported metric</b>
            : every diagnosis carries a posterior probability, and runs are
            scored with Brier score and Expected Calibration Error (ECE) on the
            held-out set. The closed MAI-DxO reference reports <i>no</i>{" "}
            calibration at all<RefSup ids={[1]} /> — measuring it is a
            deliberate point of difference. Improving multi-agent calibration
            over a single model is active work; current numbers and limitations
            live in the results docs.
          </p>
        </CardContent>
      </Card>

      {/* 3. Clinician engagement --------------------------------------- */}
      <Card className="shadow-card-2">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <SectionLabel>3 · Clinician engagement</SectionLabel>
            {ENGAGEMENT_DRAFT && (
              <Badge
                variant="outline"
                className="border-warn/40 bg-warn/10 text-warn"
              >
                Draft — pending confirmation
              </Badge>
            )}
          </div>
          <CardTitle>What practitioners told us they need</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Beyond the benchmark, Quorum's design is grounded in the author's
            research in the Nigam Shah lab at Stanford: a survey of physicians,
            nurses, physician assistants, and nurse practitioners across Stanford
            Health asked which uses of AI in care they considered riskiest, and
            differential diagnosis came back at the top — because a diagnostic
            suggestion that can't be verified is the one clinicians won't act on.
            The design was refined through follow-up conversations across several
            care settings. To respect privacy, participants are described by
            setting and role only, not by name.
          </p>

          <div className="flex flex-wrap gap-2">
            {SETTINGS.map((s) => (
              <span
                key={s}
                className="rounded-full border border-line bg-surface-2 px-3 py-1 text-[12.5px] font-medium text-ink-2"
              >
                {s}
              </span>
            ))}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {ENGAGEMENT_THEMES.map((t) => (
              <div
                key={t.heard}
                className="flex flex-col gap-2 rounded-xl border border-line bg-card p-4"
              >
                <p className="text-sm font-medium italic text-ink-2">
                  {t.heard}
                </p>
                <p className="text-[13px] text-muted-foreground">
                  <span className="font-semibold text-primary">
                    How Quorum responds:{" "}
                  </span>
                  {t.response}
                </p>
              </div>
            ))}
          </div>

          <p className="text-[12.5px] text-faint">
            These themes match what the published literature finds clinicians
            value in decision support: transparency about reasoning and sources,
            honest uncertainty, avoidance of information overload, and a
            clinician-in-the-loop posture.<RefSup ids={[2]} />
          </p>
        </CardContent>
      </Card>

      {/* 4. Regulatory ------------------------------------------------- */}
      <Card className="shadow-card-2">
        <CardHeader>
          <SectionLabel>4 · Regulatory posture</SectionLabel>
          <CardTitle>Built for the non-device CDS lane</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground">
          <p>
            The FDA's 2026 final guidance on Clinical Decision Support Software
            <RefSup ids={[5]} /> keeps the criterion that matters most here: a
            health-care professional must be able to{" "}
            <b>independently review the basis</b> of a recommendation rather than
            rely on it primarily. Quorum's auditable transcript and cited
            reasoning are designed precisely so a clinician can do that.
          </p>
          <p>
            The 2026 revision also emphasizes resting recommendations on
            well-accepted sources, avoiding information overload, and steering
            clear of urgent, time-pressured use — all of which inform how Quorum
            is scoped: non-urgent, clinician-in-loop deliberation support.
          </p>
          <div>
            <Button asChild variant="outline" size="sm">
              <Link to="/regulatory">
                Full regulatory analysis — the four-criteria gate &rarr;
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* References ----------------------------------------------------- */}
      <Card>
        <CardHeader>
          <SectionLabel>References</SectionLabel>
        </CardHeader>
        <CardContent>
          <ol className="flex flex-col gap-2 text-[12.5px] text-muted-foreground">
            {REFS.map((r) => (
              <li key={r.n} className="flex gap-2">
                <span className="font-semibold text-primary">[{r.n}]</span>
                <a
                  href={r.url}
                  className="underline decoration-line underline-offset-2 hover:text-ink-2"
                >
                  {r.cite}
                </a>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      {/* Footer CTA ---------------------------------------------------- */}
      <section className="flex flex-wrap items-center justify-center gap-3 py-4">
        <Button asChild size="lg">
          <Link to="/diagnose">Watch a live deliberation</Link>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link to="/compare">Compare panels</Link>
        </Button>
      </section>
    </main>
  );
}
