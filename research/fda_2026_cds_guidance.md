# FDA 2026 Clinical Decision Support Guidance — Notes for Quorum

## Document

- **Title:** Clinical Decision Support Software — Guidance for Industry and FDA Staff (FDA)
- **Issued (draft of this round):** January 6, 2026
- **Finalized:** March 2026
- **Reference URL:** https://www.fda.gov/media/191560/download
- **Retrieval status:** WebFetch of the reference URL did not return the PDF content during drafting. The summary below is the project brief's framing; the URL is recorded for the team to confirm out-of-band before any external use. **Do not cite specific page numbers, criterion text, or quoted regulatory language from this file** — only the high-level positioning is asserted here.

## Why this guidance matters for Quorum

FDA distinguishes "non-device" clinical decision support software (which falls outside FDA's medical-device authority) from "device" CDS based on a four-criterion test. Whether Quorum looks like a regulated medical device or like an unregulated information tool turns on how its outputs are framed and how transparently a clinician can review them.

### Criterion 4 — independent HCP review

The criterion that does most of the work for Quorum is the requirement that the software's basis must be transparent enough for the health-care professional to independently review and reach their own conclusion, rather than relying on the software's output.

Quorum is built to satisfy this by construction:
- **Citation-backed verdicts.** Every claim in the final differential is required to point back to evidence in the case packet.
- **Full audit transcript.** The complete panel deliberation — every agent's contribution, every round of debate — is streamed to the UI and archivable as a structured record, not a black-box recommendation.
- **Ranked differential, not a singular directive.** The output is a list of weighted candidate diagnoses with reasoning, not an instruction.

These properties were chosen for engineering and research-transparency reasons first; their alignment with Criterion 4 is convenient but is a downstream observation, not a regulatory claim.

### Single-recommendation enforcement discretion

The guidance also reflects ongoing enforcement-discretion thinking about software that issues a single specific recommendation. Quorum produces a **ranked differential** rather than a singular recommendation, which keeps it on the non-device side of this line regardless of how the discretion question evolves.

## Caveats

- This document is project-internal positioning, **not legal advice and not a regulatory submission**.
- The four-criterion framing is the user-supplied brief; specific quoted text, page numbers, and detailed criterion definitions must be confirmed against the actual FDA PDF before being used externally.
- Quorum is a research project (Stanford CS153, pre-alpha). It is not currently deployed to clinicians and makes no regulatory claim.
