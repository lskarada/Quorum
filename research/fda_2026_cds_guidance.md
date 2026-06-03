# FDA 2026 Clinical Decision Support Guidance — Notes for Quorum

## Document

- **Title:** Clinical Decision Support Software — Guidance for Industry and FDA Staff (FDA)
- **Issued (draft of this round):** January 6, 2026
- **Finalized:** March 11, 2026 (date per secondary legal analyses; see below)
- **Reference URL:** https://www.fda.gov/media/191560/download
- **Retrieval status:** WebFetch of the reference URL did not return the PDF content during drafting. The summary below is the project brief's framing; the URL is recorded for the team to confirm out-of-band before any external use. **Do not cite specific page numbers, criterion text, or quoted regulatory language from this file** — only the high-level positioning is asserted here.

## Why this guidance matters for Quorum

FDA distinguishes "non-device" clinical decision support software (which falls outside FDA's medical-device authority) from "device" CDS based on a four-criterion test grounded in **21 U.S.C. § 360j(o)(1)(E)** (the 21st Century Cures Act software-exclusion). Whether Quorum looks like a regulated medical device or like an unregulated information tool turns on how its outputs are framed and how transparently a clinician can review them.

### The four criteria (all must hold)

> **Sourcing:** wording below is **paraphrased from the statute** and cross-checked against independently retrieved legal analyses (Covington 2026, Faegre 2026, Sidley 2022). It is **not** quoted from the FDA guidance PDF, which blocks automated retrieval — confirm verbatim text against the primary source before external use.

| # | Criterion (paraphrased) | Quorum |
|---|--------------------------|--------|
| 1 | Not intended to acquire, process, or analyze a medical **image**, an IVD **signal**, or a pattern/signal from a signal-acquisition system. | Reasons over **textual case findings only** — no pixels, waveforms, or raw signals. ✓ |
| 2 | Intended to **display, analyze, or print medical information** about a patient. | Ingests and analyzes structured patient findings. ✓ |
| 3 | Intended to **support or provide recommendations to an HCP** about prevention, diagnosis, or treatment. | Outputs a ranked differential + suggested next test to a clinician — not patient-facing, not autonomous. ✓ |
| 4 | Intended to enable the HCP to **independently review the basis** for the recommendations, so the HCP does **not rely primarily** on them. | The load-bearing criterion for an LLM system — addressed in detail below. ✓ (most design margin here) |

The exclusion is **conjunctive**: failing any single criterion makes the software a device.

### Criterion 4 — independent HCP review

The criterion that does most of the work for Quorum is the requirement that the software's basis must be transparent enough for the health-care professional to independently review and reach their own conclusion, rather than relying on the software's output.

Quorum is built to satisfy this by construction:
- **Citation-backed verdicts.** Every claim in the final differential is required to point back to evidence in the case packet.
- **Full audit transcript.** The complete panel deliberation — every agent's contribution, every round of debate — is streamed to the UI and archivable as a structured record, not a black-box recommendation.
- **Ranked differential, not a singular directive.** The output is a list of weighted candidate diagnoses with reasoning, not an instruction.

These properties were chosen for engineering and research-transparency reasons first; their alignment with Criterion 4 is convenient but is a downstream observation, not a regulatory claim.

To support independent review (and reduce automation-bias / "black box" risk — FDA's operative principle is that *the more a tool is a black box to the HCP, the greater the device risk*), guidance points to four kinds of disclosure. Each maps to something Quorum already ships:

| What review requires | How Quorum provides it |
|----------------------|------------------------|
| Plain-language description of algorithm **development & validation** | Open-source code, versioned agent prompts, written eval methodology — all public in the repo |
| The **data** relied upon (so the HCP can judge representativeness) | Corpus described; holdout screened for contamination; per-case inputs shown in the transcript |
| **Results of studies** validating the algorithm | Decontaminated run-once NEJM benchmark with accuracy + calibration (Brier/ECE). *Honest caveat: a research benchmark, not a prospective clinical study.* |
| Summary of the **logic/methods** behind each recommendation | The append-only audit trail — every agent message, challenge, and safety verdict, replayable per case |

### Single-recommendation enforcement discretion

Per secondary legal analyses of the 2026 final guidance, FDA now extends
enforcement discretion to software that issues a *single* specific
recommendation (a posture shift from earlier framing, under which a single
directive leaned toward the device side). Quorum produces a **ranked
differential** rather than a singular directive, so it sits conservatively on
the non-device side either way — but the ranked form is no longer the only thing
keeping it there.

### Other 2026-revision changes relevant to Quorum

Secondary analyses (see references) report three further emphases in the 2026
final guidance that map onto Quorum's design:

- **Recommendations should rest on "well-understood and accepted sources"** (clinical guidelines, peer-reviewed literature). Reinforces Quorum's citation-backed verdicts.
- **Stronger usability emphasis — present decision-relevant detail and avoid information overload.** Supports a progressive-disclosure UI (headline differential first, full transcript on demand) rather than dumping the entire deliberation.
- **Non-device CDS is a poor fit for urgent, time-pressured decisions** where independent review is unlikely. Quorum is therefore scoped as non-urgent, clinician-in-loop deliberation support.

## References

**Primary**
- 21 U.S.C. § 360j(o)(1)(E) — statutory basis for the non-device CDS exclusion (21st Century Cures Act). https://www.law.cornell.edu/uscode/text/21/360j *(statute retrieved; criterion text above paraphrased from it)*
- FDA, "Clinical Decision Support Software," final guidance (rev. Jan 6, 2026; ver. Mar 11, 2026). https://www.fda.gov/media/191560/download *(**not** independently retrieved — FDA blocks bots; confirm verbatim wording here)*

**Secondary** (law-firm/industry analyses — corroborate the 2026 changes; retrieved in full)
- Covington & Burling, "5 Key Takeaways from FDA's Revised CDS Software Guidance" (Jan 2026). https://www.cov.com/news-and-insights/insights/2026/01/5-key-takeaways-from-fdas-revised-clinical-decision-support-cds-software-guidance
- Faegre Drinker, "Key Updates in FDA's 2026 General Wellness and CDS Software Guidance" (Jan 2026). https://www.faegredrinker.com/en/insights/publications/2026/1/key-updates-in-fdas-2026-general-wellness-and-clinical-decision-support-software-guidance
- Sidley Austin, "One Step Forward, Two Steps Back: FDA's Final Guidance on CDS Software" (Oct 2022). https://www.sidley.com/en/insights/newsupdates/2022/10/one-step-forward-two-steps-back-fdas-final-guidance-on-clinical-decision-software

## Caveats

- This document is project-internal positioning, **not legal advice and not a regulatory submission**.
- The four-criterion framing is paraphrased from the statute (§ 360j(o)(1)(E)) and cross-checked against secondary legal analyses; specific quoted text, page numbers, and detailed criterion definitions must still be confirmed against the actual FDA PDF before being used externally.
- Quorum is a research project (Stanford CS153, pre-alpha). It is not currently deployed to clinicians and makes no regulatory claim.
