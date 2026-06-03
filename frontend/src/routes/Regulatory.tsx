import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TopBar } from "@/components/top-bar";

/* ------------------------------------------------------------------ *
 * Content model. Criterion wording is PARAPHRASED from the statute
 * (21 U.S.C. § 360j(o)(1)(E)) and secondary legal analyses — not quoted
 * from the FDA PDF (which blocks automated retrieval). See §4 sourcing.
 * ------------------------------------------------------------------ */

type Status = "met" | "conservative";

const CRITERIA: {
  n: number;
  title: string;
  statute: string;
  status: Status;
  mapping: string;
  loadBearing?: boolean;
}[] = [
  {
    n: 1,
    title: "Not an image / signal analyzer",
    statute:
      "The software does not acquire, process, or analyze a medical image, a signal from an in-vitro diagnostic device, or a pattern/signal from a signal-acquisition system.",
    status: "met",
    mapping:
      "Quorum reasons over textual case findings only. It never ingests pixels, waveforms, or raw device signals.",
  },
  {
    n: 2,
    title: "Displays / analyzes medical information",
    statute:
      "The software is intended to display, analyze, or print medical information about a patient (or other medical information).",
    status: "met",
    mapping:
      "The panel reads structured patient findings and produces an analysis of them — squarely the kind of medical-information processing the criterion contemplates.",
  },
  {
    n: 3,
    title: "Supports recommendations to an HCP",
    statute:
      "The software supports or provides recommendations to a health-care professional about prevention, diagnosis, or treatment — not to a patient, and not as an automated directive.",
    status: "met",
    mapping:
      "Output is addressed to a clinician: a ranked differential and a suggested next test — decision support, not a patient-facing or autonomous action.",
  },
  {
    n: 4,
    title: "Enables independent HCP review",
    statute:
      "The software is intended to let the HCP independently review the basis of its recommendations, so the professional does not rely primarily on them to make a diagnosis or treatment decision.",
    status: "met",
    loadBearing: true,
    mapping:
      "This is the criterion that does the work for an LLM system. Quorum exposes the full reasoning, cites its evidence, and returns a ranked differential rather than a single directive — see §2.",
  },
];

const TRANSPARENCY: { need: string; quorum: string }[] = [
  {
    need:
      "Plain-language description of how the algorithm was developed and validated",
    quorum:
      "Open-source code, versioned agent prompts, and a written eval methodology — all public in the repository.",
  },
  {
    need: "The data the recommendation relies upon (so the HCP can judge fit)",
    quorum:
      "The case corpus is described and the holdout was screened for training-data contamination; per-case inputs are shown in the transcript.",
  },
  {
    need: "Results of studies validating the algorithm",
    quorum:
      "A decontaminated, run-once NEJM benchmark with accuracy + calibration (Brier/ECE). Honest caveat: this is a research benchmark, not a prospective clinical study.",
  },
  {
    need: "A summary of the logic / methods behind each recommendation",
    quorum:
      "The append-only audit trail is exactly this: every agent message, every challenge, every safety verdict, replayable per case.",
  },
];

const CHANGES_2026: { tag: string; before: string; after: string }[] = [
  {
    tag: "Single recommendations",
    before:
      "A single specific directive pushed software toward device status; outputs were expected as a list of options.",
    after:
      "FDA will exercise enforcement discretion for a singular output where only one recommendation is clinically appropriate.",
  },
  {
    tag: "Accepted sources",
    before: "Recommendations had to rest on the practice of medicine.",
    after:
      "Broadened to recommendations grounded in well-understood, accepted sources — clinical guidelines and peer-reviewed literature.",
  },
  {
    tag: "Usability",
    before: "Limited treatment of how information is presented.",
    after:
      "Strengthened: prioritize decision-relevant detail and avoid information overload for the clinician.",
  },
  {
    tag: "Time-critical use",
    before: "Time-critical use sat under Criterion 3.",
    after:
      "Relocated to Criterion 4 — reframed as time pressure that would prevent meaningful independent review.",
  },
];

type Ref = {
  n: number;
  cite: string;
  url: string;
  status: "primary" | "secondary";
  note?: string;
};

const REFS: Ref[] = [
  {
    n: 1,
    cite:
      "21 U.S.C. § 360j(o)(1)(E) — statutory basis for the non-device CDS exclusion (21st Century Cures Act).",
    url: "https://www.law.cornell.edu/uscode/text/21/360j",
    status: "primary",
    note: "Statute retrieved; criterion text on this page is paraphrased from it.",
  },
  {
    n: 2,
    cite:
      "FDA, “Clinical Decision Support Software,” final guidance (revised Jan 6, 2026; version dated Mar 11, 2026).",
    url: "https://www.fda.gov/media/191560/download",
    status: "primary",
    note: "FDA blocks automated retrieval — NOT independently fetched while building this page. Confirm verbatim wording against this source before any external use.",
  },
  {
    n: 3,
    cite: "Covington & Burling, “5 Key Takeaways from FDA’s Revised CDS Software Guidance” (Jan 2026).",
    url: "https://www.cov.com/news-and-insights/insights/2026/01/5-key-takeaways-from-fdas-revised-clinical-decision-support-cds-software-guidance",
    status: "secondary",
  },
  {
    n: 4,
    cite: "Faegre Drinker, “Key Updates in FDA’s 2026 General Wellness and CDS Software Guidance” (Jan 2026).",
    url: "https://www.faegredrinker.com/en/insights/publications/2026/1/key-updates-in-fdas-2026-general-wellness-and-clinical-decision-support-software-guidance",
    status: "secondary",
  },
  {
    n: 5,
    cite: "Sidley Austin, “One Step Forward, Two Steps Back: FDA’s Final Guidance on CDS Software” (Oct 2022).",
    url: "https://www.sidley.com/en/insights/newsupdates/2022/10/one-step-forward-two-steps-back-fdas-final-guidance-on-clinical-decision-software",
    status: "secondary",
  },
];

/* --- small presentational helpers --------------------------------- */

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-[12px] font-bold uppercase tracking-[0.14em] text-faint">
      {children}
    </p>
  );
}

function RefSup({ ids }: { ids: number[] }) {
  return (
    <sup className="ml-0.5 font-mono text-[10px] font-semibold text-primary">
      [{ids.join(",")}]
    </sup>
  );
}

function StatusChip({ status }: { status: Status }) {
  const map = {
    met: { label: "Satisfied by design", cls: "border-ok/40 bg-ok/10 text-ok" },
    conservative: {
      label: "Conservative margin",
      cls: "border-primary/40 bg-primary/10 text-primary",
    },
  } as const;
  const s = map[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11.5px] font-semibold ${s.cls}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {s.label}
    </span>
  );
}

export default function Regulatory() {
  return (
    <main className="mx-auto flex min-h-screen max-w-[1080px] flex-col gap-5 bg-background p-4 text-foreground">
      <TopBar status="Regulatory grounding" />

      {/* Header + abstract ---------------------------------------------- */}
      <section className="flex flex-col gap-3 px-1 pt-2">
        <div className="flex flex-wrap items-center gap-2">
          <SectionLabel>Regulatory grounding</SectionLabel>
          <Badge
            variant="outline"
            className="border-warn/40 bg-warn/10 text-warn"
          >
            Research positioning · not legal advice
          </Badge>
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight">
          Quorum and the FDA non-device CDS lane
        </h1>
        <div className="rounded-xl border-l-4 border-primary bg-card p-4 shadow-card-1">
          <p className="text-[12px] font-bold uppercase tracking-[0.14em] text-faint">
            Abstract
          </p>
          <p className="mt-1.5 max-w-3xl text-[15px] leading-relaxed text-ink-2">
            U.S. law excludes certain clinical decision support software from
            FDA device regulation when it meets a four-part test under{" "}
            <span className="font-mono text-[13px]">
              21 U.S.C. § 360j(o)(1)(E)
            </span>
            .<RefSup ids={[1]} /> The decisive part for any language-model system
            is the fourth: a clinician must be able to{" "}
            <b>independently review the basis</b> of a recommendation rather than
            rely on it primarily. Quorum's auditable transcript, cited evidence,
            and ranked-differential output were engineered to make that review
            possible by construction. Below, each criterion is mapped to a
            concrete design property, the 2026 guidance revision is summarized,
            and sources are disclosed with their retrieval status.
          </p>
        </div>
      </section>

      {/* The gate ------------------------------------------------------- */}
      <Card className="shadow-card-2">
        <CardContent className="flex flex-col gap-4 p-5">
          <SectionLabel>The exclusion is a conjunctive gate</SectionLabel>
          <div className="flex flex-col items-stretch gap-3 lg:flex-row lg:items-center">
            <div className="grid flex-1 grid-cols-2 gap-2 sm:grid-cols-4">
              {CRITERIA.map((c) => (
                <div
                  key={c.n}
                  className="flex flex-col items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-2 py-3 text-center"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-ok/15 font-mono text-[13px] font-bold text-ok">
                    {c.n}
                  </span>
                  <span className="text-[11.5px] font-semibold leading-tight text-ink-2">
                    {c.title}
                  </span>
                  <span className="text-ok" aria-hidden>
                    &#10003;
                  </span>
                </div>
              ))}
            </div>
            <div
              className="hidden text-2xl text-faint lg:block"
              aria-hidden
            >
              &rarr;
            </div>
            <div className="flex flex-col items-center justify-center gap-1 rounded-xl border border-ok/30 bg-ok/10 px-5 py-4 text-center lg:w-56">
              <span className="text-[12px] font-bold uppercase tracking-wide text-ok">
                All four met
              </span>
              <span className="text-[13px] font-semibold leading-tight text-ink-2">
                Non-device CDS — outside FDA device authority
              </span>
            </div>
          </div>
          <p className="text-[12.5px] text-muted-foreground">
            All four conditions must hold simultaneously; failing any one makes
            the software a regulated device. Quorum is designed to clear every
            one, with the most margin on the criterion that matters most for
            AI.<RefSup ids={[2, 3]} />
          </p>
        </CardContent>
      </Card>

      {/* §1 Criteria --------------------------------------------------- */}
      <section className="flex flex-col gap-3">
        <div className="flex items-baseline gap-2 px-1">
          <span className="font-mono text-sm font-bold text-primary">§ 1</span>
          <h2 className="text-xl font-bold tracking-tight">
            The four-criteria test, mapped to Quorum
          </h2>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {CRITERIA.map((c) => (
            <Card
              key={c.n}
              className={
                c.loadBearing
                  ? "border-primary/40 shadow-card-2 ring-1 ring-primary/20"
                  : "shadow-card-1"
              }
            >
              <CardHeader className="gap-2 p-5 pb-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 font-mono text-sm font-bold text-primary">
                      {c.n}
                    </span>
                    <CardTitle className="text-base">{c.title}</CardTitle>
                  </div>
                  {c.loadBearing && (
                    <Badge className="bg-primary text-[10.5px]">
                      Load-bearing
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 p-5 pt-0">
                <p className="border-l-2 border-line pl-3 text-[13px] italic leading-relaxed text-muted-foreground">
                  {c.statute}
                </p>
                <StatusChip status={c.status} />
                <p className="text-[13px] leading-relaxed text-ink-2">
                  {c.mapping}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* §2 Independent review ----------------------------------------- */}
      <section className="flex flex-col gap-3">
        <div className="flex items-baseline gap-2 px-1">
          <span className="font-mono text-sm font-bold text-primary">§ 2</span>
          <h2 className="text-xl font-bold tracking-tight">
            Criterion 4 in practice — defeating the black box
          </h2>
        </div>
        <Card className="shadow-card-2">
          <CardContent className="flex flex-col gap-4 p-5">
            <p className="text-sm text-muted-foreground">
              FDA's operative principle: the more a tool is a “black box” to the
              clinician, the more likely it is regulated as a device — a concern
              tied directly to automation bias in AI systems.<RefSup ids={[4, 5]} />{" "}
              To support independent review, guidance points to four kinds of
              disclosure. Each maps to something Quorum already ships.
            </p>
            <div className="overflow-hidden rounded-xl border border-line">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-surface-2 text-left text-ink-2">
                    <th className="w-[44%] px-4 py-2.5 font-semibold">
                      What review requires
                    </th>
                    <th className="px-4 py-2.5 font-semibold">
                      How Quorum provides it
                    </th>
                  </tr>
                </thead>
                <tbody className="[&>tr]:border-t [&>tr]:border-line">
                  {TRANSPARENCY.map((t) => (
                    <tr key={t.need} className="align-top">
                      <td className="px-4 py-3 font-medium text-ink-2">
                        {t.need}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {t.quorum}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* §3 2026 changes ----------------------------------------------- */}
      <section className="flex flex-col gap-3">
        <div className="flex items-baseline gap-2 px-1">
          <span className="font-mono text-sm font-bold text-primary">§ 3</span>
          <h2 className="text-xl font-bold tracking-tight">
            What the 2026 revision changed
          </h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {CHANGES_2026.map((c) => (
            <Card key={c.tag} className="shadow-card-1">
              <CardContent className="flex flex-col gap-2.5 p-5">
                <span className="w-fit rounded-md bg-surface-2 px-2 py-0.5 font-mono text-[11.5px] font-semibold text-ink-2">
                  {c.tag}
                </span>
                <div className="flex flex-col gap-1 text-[13px]">
                  <p className="text-muted-foreground line-through decoration-faint/60">
                    {c.before}
                  </p>
                  <p className="flex gap-1.5 text-ink-2">
                    <span className="font-bold text-ok">2026 &rarr;</span>
                    <span>{c.after}</span>
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* §4 Sourcing + refs -------------------------------------------- */}
      <section className="flex flex-col gap-3">
        <div className="flex items-baseline gap-2 px-1">
          <span className="font-mono text-sm font-bold text-primary">§ 4</span>
          <h2 className="text-xl font-bold tracking-tight">
            Sourcing, verification & caveats
          </h2>
        </div>
        <Card>
          <CardContent className="flex flex-col gap-4 p-5">
            <div className="rounded-xl border border-warn/30 bg-warn/5 p-4 text-[13px] leading-relaxed text-ink-2">
              <b className="text-warn">Honest sourcing note.</b> The FDA's own
              PDFs block automated retrieval, so the criterion wording here is{" "}
              <b>paraphrased</b> from the underlying statute
              <RefSup ids={[1]} /> and cross-checked against independently
              retrieved legal analyses<RefSup ids={[3, 4, 5]} /> — it is{" "}
              <b>not</b> quoted from the FDA guidance PDF<RefSup ids={[2]} />,
              which was not fetched while building this page. Confirm verbatim
              text against the primary source before any external or regulatory
              use. This page is a research-project positioning summary, not legal
              advice, and Quorum makes no regulatory claim and is not deployed to
              clinicians.
            </div>
            <ol className="flex flex-col gap-2.5 text-[12.5px] text-muted-foreground">
              {REFS.map((r) => (
                <li key={r.n} className="flex gap-2">
                  <span className="font-mono font-semibold text-primary">
                    [{r.n}]
                  </span>
                  <span className="flex flex-col gap-0.5">
                    <a
                      href={r.url}
                      className="underline decoration-line underline-offset-2 hover:text-ink-2"
                    >
                      {r.cite}
                    </a>
                    <span className="flex items-center gap-1.5">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                          r.status === "primary"
                            ? "bg-primary/10 text-primary"
                            : "bg-surface-2 text-faint"
                        }`}
                      >
                        {r.status}
                      </span>
                      {r.note && (
                        <span className="text-[11.5px] text-faint">
                          {r.note}
                        </span>
                      )}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </section>

      {/* Footer CTA ---------------------------------------------------- */}
      <section className="flex flex-wrap items-center justify-center gap-3 py-4">
        <Button asChild size="lg" variant="outline">
          <Link to="/evidence">&larr; Back to evidence</Link>
        </Button>
        <Button asChild size="lg">
          <Link to="/diagnose">See an auditable deliberation</Link>
        </Button>
      </section>
    </main>
  );
}
