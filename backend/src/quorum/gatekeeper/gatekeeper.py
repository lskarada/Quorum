"""Gatekeeper: SDBench-style turn-based information-reveal game.

Holds a case's available findings and reveals them only when an agent
queries with sufficient specificity. Tracks simulated cost via a
CMS-style schedule (test_costs.yaml) and enforces hard limits on the
number of turns and the cumulative cost.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from quorum.eval.eval_case import EvalCase, Finding
from quorum.llm.client import LLMClient

COSTS_PATH = Path(__file__).parent / "test_costs.yaml"


def _load_costs() -> dict:
    return yaml.safe_load(COSTS_PATH.read_text())


@dataclass
class GatekeeperResponse:
    matched: bool
    content: str
    cost_usd: float
    matched_label: str | None = None
    turn_index: int = 0


class Gatekeeper:
    DEFAULT_MAX_TURNS = 30
    DEFAULT_MAX_COST = 5000.0
    # Use Haiku for the matcher: this is a deterministic "pick an index from
    # a short list" task, not a clinical reasoning call. The five agents
    # remain Sonnet 4.6 per the v2 rule.
    MATCHER_MODEL = "anthropic/claude-haiku-4-5"

    def __init__(
        self,
        case: EvalCase,
        *,
        llm_client: LLMClient | None = None,
        max_turns: int = DEFAULT_MAX_TURNS,
        max_cost_usd: float = DEFAULT_MAX_COST,
    ):
        self.case = case
        self.llm_client = llm_client
        self.max_turns = max_turns
        self.max_cost_usd = max_cost_usd
        self.simulated_cost: float = 0.0
        self.turn_index: int = 0
        self._costs = _load_costs()

    async def query(self, question: str) -> GatekeeperResponse:
        if self.turn_index >= self.max_turns:
            raise RuntimeError(f"Gatekeeper exceeded max turns ({self.max_turns})")
        if self.simulated_cost >= self.max_cost_usd:
            raise RuntimeError(f"Gatekeeper exceeded max cost (${self.max_cost_usd})")

        self.turn_index += 1
        idx = await self._llm_match(question, self.case.available_findings)

        if idx < 0:
            return GatekeeperResponse(
                matched=False,
                content="That information is not available in this case.",
                cost_usd=0.0,
                turn_index=self.turn_index,
            )

        finding = self.case.available_findings[idx]
        cost = self._cost_for(finding)
        self.simulated_cost += cost
        return GatekeeperResponse(
            matched=True,
            content=finding.content,
            cost_usd=cost,
            matched_label=finding.label,
            turn_index=self.turn_index,
        )

    async def _llm_match(self, question: str, findings: list[Finding]) -> int:
        """Return index of matched finding, or -1 if no match.

        Two-stage match for cost efficiency:
          1. Substring keyword match against label tokens (free).
          2. If substring misses and an llm_client is configured, fall back
             to Haiku 4.5 for a one-shot fuzzy semantic match (~$0.0005/call).
        Tests monkey-patch this method directly to stay hermetic.
        """
        if not findings:
            return -1
        idx = self._substring_match(question, findings)
        if idx >= 0:
            return idx
        if self.llm_client is None:
            return -1

        messages = [
            {
                "role": "system",
                "content": (
                    "You match a clinical query to one available finding by index, "
                    "or -1 if none apply."
                ),
            },
            {"role": "user", "content": self._build_match_prompt(question, findings)},
        ]
        response = await self.llm_client.complete(
            messages=messages,
            model=self.MATCHER_MODEL,
            max_tokens=20,
        )
        try:
            idx = int(response.content.strip().splitlines()[0].strip())
        except (ValueError, IndexError):
            return -1
        if 0 <= idx < len(findings):
            return idx
        return -1

    @staticmethod
    def _substring_match(question: str, findings: list[Finding]) -> int:
        ql = question.lower()
        for i, f in enumerate(findings):
            for tok in re.findall(r"\w+", f.label.lower()):
                if len(tok) > 3 and tok in ql:
                    return i
        return -1

    def _build_match_prompt(self, question: str, findings: list[Finding]) -> str:
        lines = [
            "You are a clinical gatekeeper. A diagnostic AI is asking for information.",
            "Match the question to ONE of the available findings, or say -1 if none match.",
            "",
            f"QUESTION: {question}",
            "",
            "AVAILABLE FINDINGS:",
        ]
        for i, f in enumerate(findings):
            lines.append(f"  [{i}] ({f.category}) {f.label}")
        lines.append("")
        lines.append("Respond with ONLY the index number (0, 1, 2, ...) or -1. No other text.")
        return "\n".join(lines)

    def _cost_for(self, finding: Finding) -> float:
        """Lookup cost via category + label keyword match against test_costs.yaml."""
        cat = finding.category.lower()
        if cat not in self._costs:
            return float(self._costs.get("default_cost", 0.0))
        cat_costs = self._costs[cat]
        label_tokens = [t for t in re.findall(r"\w+", finding.label.lower()) if len(t) > 2]
        for token in label_tokens:
            for test_name, price in cat_costs.items():
                if token in test_name or test_name in token:
                    return float(price)
        return float(self._costs.get("default_cost", 0.0))
