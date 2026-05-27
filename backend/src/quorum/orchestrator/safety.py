"""Deterministic safety layer: 5 hard rules enforced before commit.

These are Python-checked, NOT LLM-judged. That is what makes them
auditable: a reviewer can replay the rules against any audit trail.

Rule order matters. Cost overrun (rule 4) is evaluated first — once
spend exceeds the threshold, the system forces a commit regardless of
the other rules. Otherwise rules are applied in order:
  1. At least N findings queried
  2. Checklist has no unresolved concerns
  3. Committed Dx is in the current Hypothesis shortlist
  5. Hypothesis top-1 and Challenger top-1 agree (within disagreement margin)
"""
from __future__ import annotations

from dataclasses import dataclass

_NO_ALT_VALUES = {"none", "n/a", "na", ""}


@dataclass
class SafetyVerdict:
    blocked: bool
    forced: bool = False
    reason: str = ""


class SafetyChecker:
    def __init__(
        self,
        *,
        min_findings_to_commit: int = 3,
        force_commit_cost_usd: float = 5000.0,
        max_disagreement_pp: float = 0.30,
    ):
        self.min_findings = min_findings_to_commit
        self.force_commit_cost = force_commit_cost_usd
        self.max_disagreement_pp = max_disagreement_pp

    def check_commit(
        self,
        *,
        committed_dx: str,
        hypothesis_shortlist: dict[str, float],
        challenger_top: str,
        checklist_concerns: list[str],
        n_findings_queried: int,
        simulated_cost: float,
    ) -> SafetyVerdict:
        # Rule 4 (FIRST): cost overrun forces commit regardless
        if simulated_cost >= self.force_commit_cost:
            return SafetyVerdict(
                blocked=False, forced=True, reason="cost overrun: forced commit"
            )

        # Rule 1: at least N findings queried
        if n_findings_queried < self.min_findings:
            return SafetyVerdict(
                blocked=True,
                reason=(
                    f"need >= {self.min_findings} queried findings "
                    f"(have {n_findings_queried})"
                ),
            )

        # Rule 2: checklist concerns active
        if checklist_concerns:
            return SafetyVerdict(
                blocked=True,
                reason=f"checklist has {len(checklist_concerns)} unresolved concerns",
            )

        # Rule 3: committed dx must be in current shortlist
        if committed_dx not in hypothesis_shortlist:
            return SafetyVerdict(
                blocked=True,
                reason=f"committed Dx {committed_dx!r} not in Hypothesis shortlist",
            )

        # Rule 5: substantive disagreement between Hypothesis top-1 and Challenger top-1
        if challenger_top and challenger_top.strip().lower() not in _NO_ALT_VALUES:
            hypothesis_top = max(hypothesis_shortlist, key=hypothesis_shortlist.get)
            hyp_top_p = hypothesis_shortlist[hypothesis_top]
            challenger_p = hypothesis_shortlist.get(challenger_top, 0.0)
            if (
                hypothesis_top != challenger_top
                and (hyp_top_p - challenger_p) > self.max_disagreement_pp
            ):
                return SafetyVerdict(
                    blocked=True,
                    reason=(
                        f"Hypothesis/Challenger disagreement "
                        f">{self.max_disagreement_pp * 100:.0f}pp"
                    ),
                )

        return SafetyVerdict(blocked=False)
