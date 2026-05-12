# Trustworthy AI for Medicine: Continuous Hallucination Detection and Elimination with CHECK

**Authors:** Carlos Garcia-Fernandez, Luis Felipe, Monique Shotande, et al.
**Year:** 2025
**Venue:** arXiv preprint (cs.CL)
**Link:** https://arxiv.org/abs/2506.11129
**arXiv ID / DOI:** 2506.11129

## TL;DR
CHECK is a continuous-learning hallucination-detection framework that pairs structured clinical databases with an information-theory-grounded classifier to flag both factual and reasoning errors in medical LLM outputs. Evaluated across medical benchmarks and a corpus drawn from 100 clinical trials (1,500 questions), it reduces Llama-3.3-70B-Instruct's hallucination rate from 31% to 0.3% and raises GPT-4o's USMLE passing rate to 92.1%. The authors frame the system as a way to push residual error below clinically acceptable thresholds.

## Key claim
Llama-3.3-70B-Instruct's hallucination rate drops from 31% to 0.3% on a 1,500-question clinical-trial QA set when CHECK's detector–rewriter loop is applied, with AUCs of 0.95–0.96 on medical hallucination benchmarks including MedQA.

## Relevance to Quorum
Content-level safety comparison: Quorum's "no confabulated citations" rule (CLAUDE.md §Anti-hallucination protocol) is upstream of CHECK's concern — we are trying to prevent the generation of unsupported clinical claims in the first place via a structured 5-agent deliberation contract, whereas CHECK is a detect-and-correct loop layered onto a single model. CHECK is the natural post-hoc filter to bolt onto Quorum's `FinalVerdict` output if we later want a defense-in-depth layer beyond panel disagreement. The 0.95–0.96 AUC on MedQA is a useful target ceiling for any verifier we add to the Challenger agent's role.

## How we cite it
- `research/prior_art_map.md` — under "hallucination-detection prior art," contrasting Quorum's pre-generation deliberation with CHECK's post-generation verification.
- `docs/eval-methodology.md` — when we discuss the residual-error budget for clinical deployment.
- README §"Safety & limitations" — to acknowledge CHECK as a complementary layer Quorum does not itself implement.
