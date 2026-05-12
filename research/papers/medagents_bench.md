# MedAgentsBench: Benchmarking Thinking Models and Agent Frameworks for Complex Medical Reasoning

**Authors:** Xiangru Tang, Daniel Shao, Jiwoong Sohn, Jiapeng Chen, Jiayi Zhang, Jinyu Xiang, Fang Wu, Yilun Zhao, Chenglin Wu, Wenqi Shi, Arman Cohan, Mark Gerstein
**Year:** 2025
**Venue:** arXiv preprint (cs.CL)
**Link:** https://arxiv.org/abs/2503.07459
**arXiv ID / DOI:** arXiv:2503.07459

## TL;DR
MedAgentsBench targets the gap left by saturated medical-QA leaderboards: it filters seven established medical datasets down to hard multi-step questions requiring clinical reasoning, diagnosis formulation, and treatment planning, and standardizes the evaluation protocol across both single-model and agent-framework setups. Findings: thinking models (DeepSeek R1, OpenAI o3) lead on hard medical reasoning, and search-based agent methods give competitive performance/cost ratios versus heavier orchestration. The benchmark is open-source.

## Key claim
On the hard subset of clinical reasoning, frontier "thinking" models substantially outperform earlier LLMs, and search-based agent frameworks offer the best cost-adjusted accuracy among orchestration strategies.

## Relevance to Quorum
MedAgentsBench is a natural third evaluation surface for Quorum alongside NEJM CPC cases and MedQA. It directly addresses the two methodological problems Quorum's evaluation faces: (a) easy-question saturation that hides orchestration value, and (b) inconsistent protocols across papers. Running Quorum's panel on MedAgentsBench's hard subset would let us claim, with a third party's filtering, that multi-agent debate adds value over a single thinking model — or, more honestly, would tell us when it does not. It also gives us a published comparison axis against bare DeepSeek R1 / o3 baselines, which is exactly the "is the debate worth the latency?" question reviewers will ask.

## How we cite it
In `docs/eval_methodology.md` as the third evaluation surface, and in the project write-up's evaluation section when reporting Quorum vs single-model baselines.
