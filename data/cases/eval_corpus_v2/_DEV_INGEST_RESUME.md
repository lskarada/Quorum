# DEV ingest — resume note (2026-05-30)

User pasted 11 full NEJM CPC case texts (full clinical narratives are in the
session transcript 6e57b7c5...jsonl, user turn) + the final Accuracy-Maximization
Campaign. Task: ingest cases as gitignored DEV set, update campaign, produce
spec + brief + writing-plans plan + <4000-char /goal prompt.

## 11 cases (ALL leakage-free: 2025 #15-25 vs used 2025 #26-36, 2026 #2-14)
- nejm-cpc-25-2025  NEJMcpc2412535  93F dyspnea/fatigue → Aortic stenosis (Heyde's)
- nejm-cpc-24-2025  NEJMcpc2312739  32F fatigue/myalgias → Lyme carditis
- nejm-cpc-23-2025  NEJMcpc2309348  28F resp failure → PVOD/PCH
- nejm-cpc-22-2025  NEJMcpc2412531  19F seizure/odd behavior → mixed germ-cell tumor + anti-NMDA encephalitis
- nejm-cpc-21-2025  NEJMcpc2412532  75M cough/dyspnea/hypoxemia → Nocardia farcinica + M. abscessus coinfection
- nejm-cpc-20-2025  NEJMcpc2412527  86F neck swelling/dysphagia → S. aureus infected carotid pseudoaneurysm + atypical lipomatous tumor
- nejm-cpc-19-2025  NEJMcpc2412528  69M headache/ataxia → Powassan virus encephalitis
- nejm-cpc-18-2025  NEJMcpc2300897  63F dyspnea on exertion → Erdheim-Chester disease
- nejm-cpc-17-2025  NEJMcpc2412510  61M resp failure/shock post kidney tx → donor-derived disseminated strongyloidiasis
- nejm-cpc-16-2025  NEJMcpc2412524  34M nasopharyngeal mass → granulomatosis with polyangiitis (GPA)
- nejm-cpc-15-2025  NEJMcpc2412526  52M fever/nausea/resp failure → hantavirus cardiopulmonary syndrome

## NEXT STEPS (resume here)
1. Read splits.json + nejm_sample.json (first case) to confirm exact schema +
   that EVAL/TUNE IDs don't collide. Confirm .gitignore covers this dir's _dev/raw.
2. Parse the 11 transcript narratives into rich NEJM schema (keys: case_id, source,
   citation, doi, published, corpus, title, discussant, patient_demographics,
   initial_presentation, available_findings[] (drives Gatekeeper reveal),
   hidden_discussant_differential, discussant_diagnosis, ground_truth_diagnosis,
   ground_truth_components, acceptable_partial_credit, specialty_tags, difficulty).
   Write to data/cases/eval_corpus_v2/dev_nejm_sample.json (GITIGNORED — paywalled).
3. Python assert: DEV ∩ (EVAL ∪ TUNE) = ∅.
4. Optionally auto-pull fresh MCR/RareBench (seed-pinned, disjoint) to reach ~25-30 DEV.
5. Update campaign P1 (DEV = these 11 + augmentation; precondition now satisfied).
6. Produce: spec docs/superpowers/specs/2026-05-30-*.md; brief docs/overnight/2026-05-30-brief.md;
   writing-plans plan; <4000-char /goal prompt.

## Guardrails (unchanged)
No push/force/reset unless asked. Never edit splits.json. Never commit NEJM text.
EVAL touched ≤2x (baseline + final). 5 agents, Sonnet 4.6, no new deps.
$100 incremental ceiling; log every paid run via backend/scripts/log_spend.sh.
