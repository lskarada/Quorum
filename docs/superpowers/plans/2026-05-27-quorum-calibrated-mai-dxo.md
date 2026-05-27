# Quorum Calibrated-Auditable MAI-DxO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the calibrated, auditable, MCP-exposed open implementation of MAI-DxO-style cost-aware sequential diagnostic deliberation on Claude Sonnet 4.6, evaluated on n=30 held-out NEJM+MCR+RareBench cases with full audit trails, Brier/ECE calibration metrics, and a hard $80 budget cap.

**Architecture:** Extend the existing 5-agent Quorum panel with three new modules — a Gatekeeper (turn-based information-reveal game), an AuditTrail (per-turn JSONL logging), and a Calibration layer (Brier + ECE on panel posteriors). Add a deterministic safety layer (5 hard rules) and a new `sequential_diagnosis` orchestrator mode. Run a three-arm headline eval: Arm A (full system, Sonnet 4.6 + thinking), Arm B (single Sonnet 4.6 floor), reference (Microsoft's published MAI-DxO+o3 = 85% and physician 20%).

**Tech Stack:** Python 3.11+ (uv workspace), Pydantic v2, Anthropic SDK (Sonnet 4.6 with extended thinking + prompt caching + Batch API), pytest, typer CLI. No new runtime deps — all already in `backend/pyproject.toml`.

**Spec:** `docs/superpowers/specs/2026-05-26-quorum-calibrated-auditable-mai-dxo-design.md` — read this before starting.

---

## File Structure

**New (will be created):**

| Path | Responsibility |
|---|---|
| `backend/src/quorum/gatekeeper/__init__.py` | Public exports for Gatekeeper |
| `backend/src/quorum/gatekeeper/gatekeeper.py` | `Gatekeeper` class: holds case, matches agent queries to findings via LLM-as-matcher, accrues simulated cost |
| `backend/src/quorum/gatekeeper/test_costs.yaml` | Static CMS-style simulated cost table for common tests |
| `backend/src/quorum/audit/__init__.py` | Public exports for AuditTrail |
| `backend/src/quorum/audit/schemas.py` | `TurnRecord`, `CaseAudit` Pydantic models |
| `backend/src/quorum/audit/writer.py` | `AuditWriter` streams JSONL |
| `backend/src/quorum/calibration/__init__.py` | Public exports for Calibration |
| `backend/src/quorum/calibration/metrics.py` | `compute_brier`, `compute_ece` |
| `backend/src/quorum/orchestrator/safety.py` | `SafetyChecker`: 5 deterministic hard rules |
| `backend/src/quorum/eval/judge.py` | LLM-as-judge for diagnostic scoring (Sonnet 4.6 fallback) |
| `backend/scripts/build_eval_splits.py` | Writes `data/cases/eval_corpus_v2/splits.json` |
| `backend/scripts/load_eval_corpus.py` | Loads all 35 cases into unified `EvalCase` model |
| `backend/scripts/run_v2_benchmark.py` | Main entrypoint for Arm A and Arm B runs |
| `backend/config/panels/v2_quorum_calibrated.yaml` | Arm A panel config |
| `backend/config/panels/v2_single_sonnet.yaml` | Arm B panel config |
| `data/cases/eval_corpus_v2/splits.json` | TUNE/EVAL split (created by build_eval_splits.py) |
| `backend/tests/test_gatekeeper.py` | Gatekeeper unit tests |
| `backend/tests/test_audit_trail.py` | AuditTrail unit tests |
| `backend/tests/test_calibration.py` | Brier/ECE metric tests |
| `backend/tests/test_safety_checker.py` | Deterministic safety rule tests |
| `backend/tests/test_sequential_panel.py` | Sequential-mode panel integration tests |
| `backend/tests/test_judge.py` | LLM-as-judge tests |
| `docs/results_v2.md` | Final headline results write-up |

**Modified:**

| Path | Change |
|---|---|
| `backend/src/quorum/orchestrator/panel.py` | Add `run_sequential(case, gatekeeper, audit_writer)` method |
| `backend/src/quorum/orchestrator/schemas.py` | Add `posterior_over_shortlist: Dict[str, float]` to Hypothesis output |
| `backend/src/quorum/orchestrator/panel_config.py` | Add `mode: sequential_diagnosis` enum value |
| `backend/src/quorum/orchestrator/prompts/hypothesis.md` | Tune for sequential workflow + posterior emission |
| `backend/src/quorum/orchestrator/prompts/test_chooser.md` | Tune to propose 1-2 next Gatekeeper queries |
| `backend/src/quorum/orchestrator/prompts/challenger.md` | Tune to surface missed diagnoses after each new finding |
| `backend/src/quorum/orchestrator/prompts/stewardship.md` | Tune to vote on stop / continue based on cost-benefit |
| `backend/src/quorum/orchestrator/prompts/checklist.md` | Tune to enforce coherence + safety conditions before commit |
| `backend/src/quorum/llm/llm_client.py` | Verify extended thinking + cache_control + Batch API flags (likely already present) |
| `backend/src/quorum/eval/cli.py` | Add `v2-benchmark` subcommand |
| `docs/results.md` | Add v2 section linking to results_v2.md |
| `docs/eval_methodology.md` | Add v2 corpus + three-arm + judge methodology section |
| `README.md` | Update headline to reflect v2 positioning |

---

## Budget Gate (CRITICAL — read before every phase)

**Hard ceiling: $80 total Anthropic spend.** Current spent: $5.21. Remaining envelope: ~$75.

Before every Bash invocation that hits the Anthropic API, the operator MUST:

1. Check the current spend from the Anthropic dashboard (or the v2 spend tracker if implemented).
2. If projected next-step cost would push total over $75, STOP and ask the user before proceeding.
3. If spend reaches $70, suspend all non-essential runs and gather the operator's confirmation before continuing.

**Cost estimates** (Sonnet 4.6 with caching + thinking):
- Tuning iteration: ~$2 per 5-case TUNE run (10 iters → ~$20)
- Headline EVAL Arm A: ~$15 (30 cases × $0.40 batched)
- Headline EVAL Arm B: ~$5 (30 cases × ~$0.15 single call)
- Judge scoring (Sonnet 4.6 as judge): ~$3-5
- **Total floor**: ~$45-55

---

## Phase 1 — Splits + corpus loader (Day 1, 4 hours)

### Task 1.1: Verify corpus state

**Files:**
- Read: `data/cases/eval_corpus_v2/nejm_sample.json` (must contain 20 cases)
- Read: `data/cases/eval_corpus_v2/mcr_sample.json` (must contain 10 cases)
- Read: `data/cases/eval_corpus_v2/rarebench_sample.json` (must contain 5 cases)

- [ ] **Step 1: Smoke-check corpus**

Run: `cd /Users/lskarada/Documents/Claude/Quorum && python3 -c "
import json
for f, n in [('nejm_sample.json',20),('mcr_sample.json',10),('rarebench_sample.json',5)]:
    cases = json.load(open(f'data/cases/eval_corpus_v2/{f}'))
    assert len(cases)==n, f'{f}: expected {n} got {len(cases)}'
    print(f'{f}: {len(cases)} cases OK')
"`

Expected output:
```
nejm_sample.json: 20 cases OK
mcr_sample.json: 10 cases OK
rarebench_sample.json: 5 cases OK
```

If any assertion fails, STOP and re-pull the corpus.

### Task 1.2: Build splits.json

**Files:**
- Create: `backend/scripts/build_eval_splits.py`
- Create: `data/cases/eval_corpus_v2/splits.json`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_splits.py`:
```python
import json
from pathlib import Path

def test_splits_file_structure():
    splits_path = Path("data/cases/eval_corpus_v2/splits.json")
    assert splits_path.exists(), "splits.json must exist"
    splits = json.loads(splits_path.read_text())
    assert "tune" in splits and "eval" in splits
    assert len(splits["tune"]) == 5
    assert len(splits["eval"]) == 30
    # No overlap
    assert set(splits["tune"]).isdisjoint(set(splits["eval"]))
    # All IDs come from the three sample files
    all_ids = set(splits["tune"]) | set(splits["eval"])
    assert len(all_ids) == 35

def test_split_deterministic():
    """Re-running the build script should produce identical splits."""
    splits_path = Path("data/cases/eval_corpus_v2/splits.json")
    snapshot = json.loads(splits_path.read_text())
    # Re-run via subprocess and compare
    import subprocess
    subprocess.run(["python3", "backend/scripts/build_eval_splits.py"], check=True)
    re_run = json.loads(splits_path.read_text())
    assert snapshot == re_run, "splits.json must be deterministic"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_splits.py -v`
Expected: FAIL — splits.json doesn't exist.

- [ ] **Step 3: Write the build script**

Create `backend/scripts/build_eval_splits.py`:
```python
"""Build deterministic TUNE/EVAL split for the v2 benchmark corpus.

Seed is fixed at 20260526 (the spec date). Re-running this script must
produce byte-identical output.
"""
import json
import random
from pathlib import Path

SEED = 20260526
CORPUS_DIR = Path(__file__).parent.parent.parent / "data" / "cases" / "eval_corpus_v2"
SAMPLE_FILES = ["nejm_sample.json", "mcr_sample.json", "rarebench_sample.json"]
TUNE_N = 5
EVAL_N = 30


def main() -> None:
    all_ids: list[str] = []
    for f in SAMPLE_FILES:
        cases = json.loads((CORPUS_DIR / f).read_text())
        all_ids.extend(c["case_id"] for c in cases)

    assert len(all_ids) == TUNE_N + EVAL_N, f"Expected 35 cases, got {len(all_ids)}"

    rng = random.Random(SEED)
    all_ids_sorted = sorted(all_ids)  # deterministic regardless of file load order
    shuffled = all_ids_sorted[:]
    rng.shuffle(shuffled)

    splits = {
        "tune": sorted(shuffled[:TUNE_N]),
        "eval": sorted(shuffled[TUNE_N:]),
        "_provenance": {
            "seed": SEED,
            "source_files": SAMPLE_FILES,
            "tune_n": TUNE_N,
            "eval_n": EVAL_N,
        },
    }
    (CORPUS_DIR / "splits.json").write_text(json.dumps(splits, indent=2) + "\n")
    print(f"Wrote splits: {TUNE_N} TUNE + {EVAL_N} EVAL")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the script**

Run: `cd /Users/lskarada/Documents/Claude/Quorum && python3 backend/scripts/build_eval_splits.py`
Expected: `Wrote splits: 5 TUNE + 30 EVAL`

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_splits.py -v`
Expected: PASS, 2 tests

- [ ] **Step 6: Commit**

```bash
cd /Users/lskarada/Documents/Claude/Quorum
git add backend/scripts/build_eval_splits.py backend/tests/test_splits.py data/cases/eval_corpus_v2/splits.json
git commit -m "feat(eval): deterministic TUNE/EVAL split for v2 corpus

5 TUNE + 30 EVAL with seed=20260526. Splits are byte-stable
across re-runs so the held-out set never drifts."
```

### Task 1.3: Unified EvalCase loader

**Files:**
- Create: `backend/scripts/load_eval_corpus.py`
- Create: `backend/src/quorum/eval/eval_case.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_eval_case_loader.py`:
```python
from quorum.eval.eval_case import EvalCase, load_corpus

def test_load_corpus_returns_35_cases():
    cases = load_corpus()
    assert len(cases) == 35
    assert all(isinstance(c, EvalCase) for c in cases)

def test_eval_case_has_required_fields():
    cases = load_corpus()
    for c in cases:
        assert c.case_id
        assert c.initial_presentation
        assert c.ground_truth_diagnosis
        assert isinstance(c.available_findings, list)
        assert c.corpus in ("nejm", "mcr", "rarebench")

def test_load_split_works():
    """Should be able to load only TUNE or only EVAL cases."""
    tune = load_corpus(split="tune")
    evaluation = load_corpus(split="eval")
    assert len(tune) == 5
    assert len(evaluation) == 30
    assert set(c.case_id for c in tune).isdisjoint(set(c.case_id for c in evaluation))
```

- [ ] **Step 2: Run test, expect failure**

Run: `cd backend && uv run pytest tests/test_eval_case_loader.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Write EvalCase model and loader**

Create `backend/src/quorum/eval/eval_case.py`:
```python
"""Unified EvalCase for the v2 benchmark.

Wraps the three sample formats (NEJM, MCR, RareBench) into a single
shape the orchestrator and Gatekeeper can consume identically.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    category: str
    label: str
    content: str


class EvalCase(BaseModel):
    case_id: str
    corpus: Literal["nejm", "mcr", "rarebench"]
    source: str
    initial_presentation: str
    available_findings: list[Finding] = Field(default_factory=list)
    ground_truth_diagnosis: str
    acceptable_partial_credit: list[str] = Field(default_factory=list)
    difficulty: Optional[str] = "hard"
    specialty_tags: list[str] = Field(default_factory=list)


CORPUS_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "cases" / "eval_corpus_v2"


def _load_nejm(raw: dict) -> EvalCase:
    findings = [Finding(**f) for f in raw.get("available_findings", [])]
    return EvalCase(
        case_id=raw["case_id"],
        corpus="nejm",
        source=raw.get("source", "NEJM CPC"),
        initial_presentation=raw["initial_presentation"],
        available_findings=findings,
        ground_truth_diagnosis=raw["ground_truth_diagnosis"],
        acceptable_partial_credit=raw.get("acceptable_partial_credit", []),
        specialty_tags=raw.get("specialty_tags", []),
    )


def _load_mcr(raw: dict) -> EvalCase:
    # MCR cases come without structured available_findings; the full reasoning
    # trace stays hidden. The "case_prompt"-style presentation is shown as-is.
    return EvalCase(
        case_id=raw["case_id"],
        corpus="mcr",
        source=raw.get("source", "MedCaseReasoning"),
        initial_presentation=raw["presentation"],
        available_findings=[],  # MCR cases run as single-turn for v2
        ground_truth_diagnosis=raw["ground_truth_diagnosis"],
        acceptable_partial_credit=[],
        specialty_tags=[],
    )


def _load_rarebench(raw: dict) -> EvalCase:
    # RareBench cases run single-turn against the HPO-phenotype presentation.
    return EvalCase(
        case_id=raw["case_id"],
        corpus="rarebench",
        source=raw.get("source", "RareBench LIRICAL"),
        initial_presentation=raw["presentation"],
        available_findings=[],
        ground_truth_diagnosis=raw["ground_truth_diagnosis"],
        acceptable_partial_credit=raw.get("all_ground_truth_names", []),
        specialty_tags=["rare_disease"],
    )


def load_corpus(split: Optional[Literal["tune", "eval"]] = None) -> list[EvalCase]:
    nejm = [_load_nejm(c) for c in json.loads((CORPUS_DIR / "nejm_sample.json").read_text())]
    mcr = [_load_mcr(c) for c in json.loads((CORPUS_DIR / "mcr_sample.json").read_text())]
    rb = [_load_rarebench(c) for c in json.loads((CORPUS_DIR / "rarebench_sample.json").read_text())]
    all_cases = nejm + mcr + rb

    if split is None:
        return all_cases

    splits = json.loads((CORPUS_DIR / "splits.json").read_text())
    ids = set(splits[split])
    return [c for c in all_cases if c.case_id in ids]
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_eval_case_loader.py -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Commit**

```bash
git add backend/src/quorum/eval/eval_case.py backend/tests/test_eval_case_loader.py
git commit -m "feat(eval): unified EvalCase loader for v2 corpus

Wraps NEJM/MCR/RareBench formats into a single Pydantic model.
load_corpus(split='tune'|'eval'|None) reads splits.json for the
held-out partition."
```

---

## Phase 2 — Gatekeeper module (Days 1-2, 8 hours)

### Task 2.1: Test cost table

**Files:**
- Create: `backend/src/quorum/gatekeeper/test_costs.yaml`

- [ ] **Step 1: Write cost table**

Create `backend/src/quorum/gatekeeper/test_costs.yaml`:
```yaml
# Simulated test costs in USD, modeled on CMS allowable charges.
# Categories match Gatekeeper finding categories.
# Default cost for an unrecognized query is $0 (no penalty for asking).

labs:
  cbc: 11
  cmp: 12
  bmp: 8
  lft: 14
  coagulation_panel: 18
  urinalysis: 5
  blood_culture: 32
  esr: 8
  crp: 14
  thyroid_panel: 23
  lipid_panel: 18
  troponin: 22
  bnp_or_ntprobnp: 28
  lactate_dehydrogenase: 7
  hemoglobin_a1c: 14
  arterial_blood_gas: 35

imaging:
  chest_xray: 45
  abdominal_xray: 45
  ultrasound_abdomen: 200
  ct_chest: 300
  ct_abdomen_pelvis: 350
  ct_head: 300
  ct_angiography: 500
  mri_head: 600
  mri_abdomen: 700
  mri_spine: 700
  echocardiogram: 350
  transesophageal_echocardiogram: 1200

serology:
  hiv_test: 25
  hepatitis_panel: 60
  syphilis_serology: 18
  ana: 35
  anca: 55
  rheumatoid_factor: 22
  cryoglobulin: 110
  immunoglobulins: 65
  complement_c3_c4: 55

microbiology:
  blood_culture_extended: 65
  fungal_culture: 70
  mycobacterial_culture: 95
  pcr_panel: 145

pathology:
  skin_biopsy: 350
  liver_biopsy: 850
  kidney_biopsy: 950
  bone_marrow_biopsy: 1100
  lymph_node_biopsy: 750

procedures:
  lumbar_puncture: 280
  thoracentesis: 320
  paracentesis: 280
  pericardiocentesis: 800
  bronchoscopy: 950
  endoscopy_upper: 700
  endoscopy_lower: 800

default_cost: 0
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/quorum/gatekeeper/test_costs.yaml
git commit -m "feat(gatekeeper): seed CMS-style simulated test cost table"
```

### Task 2.2: Gatekeeper class

**Files:**
- Create: `backend/src/quorum/gatekeeper/__init__.py`
- Create: `backend/src/quorum/gatekeeper/gatekeeper.py`
- Create: `backend/tests/test_gatekeeper.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_gatekeeper.py`:
```python
import pytest
from quorum.gatekeeper.gatekeeper import Gatekeeper, GatekeeperResponse
from quorum.eval.eval_case import EvalCase, Finding


@pytest.fixture
def toy_case():
    return EvalCase(
        case_id="toy-1",
        corpus="nejm",
        source="test",
        initial_presentation="patient with chest pain",
        available_findings=[
            Finding(category="labs", label="Troponin", content="Troponin 0.15 ng/mL (elevated)"),
            Finding(category="imaging", label="Chest x-ray", content="No cardiomegaly, clear lungs"),
        ],
        ground_truth_diagnosis="acute myocardial infarction",
        acceptable_partial_credit=[],
    )


def test_gatekeeper_matches_known_finding(toy_case, monkeypatch):
    """Direct keyword match returns the troponin finding."""
    gk = Gatekeeper(toy_case)
    # Monkey-patch the matcher to return a deterministic match
    monkeypatch.setattr(gk, "_llm_match", lambda q, findings: 0)
    resp = gk.query("What is the troponin level?")
    assert resp.matched is True
    assert "Troponin" in resp.content
    assert resp.cost_usd > 0  # CMS-table lookup found troponin


def test_gatekeeper_returns_not_available_for_unrelated(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case)
    monkeypatch.setattr(gk, "_llm_match", lambda q, findings: -1)
    resp = gk.query("What is the patient's astrological sign?")
    assert resp.matched is False
    assert "not available" in resp.content.lower()


def test_gatekeeper_accumulates_cost(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case)
    monkeypatch.setattr(gk, "_llm_match", lambda q, findings: 0)
    assert gk.simulated_cost == 0
    gk.query("Troponin?")
    assert gk.simulated_cost > 0


def test_gatekeeper_turn_limit(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case, max_turns=2)
    monkeypatch.setattr(gk, "_llm_match", lambda q, findings: 0)
    gk.query("q1"); gk.query("q2")
    with pytest.raises(RuntimeError, match="max turns"):
        gk.query("q3")


def test_gatekeeper_cost_limit(toy_case, monkeypatch):
    gk = Gatekeeper(toy_case, max_cost_usd=10)
    monkeypatch.setattr(gk, "_llm_match", lambda q, findings: 0)
    gk.query("CT chest")  # CT chest = $300 in our table; should exceed $10
    # Next query should be blocked
    with pytest.raises(RuntimeError, match="max cost"):
        gk.query("CT chest")
```

- [ ] **Step 2: Run test, expect failure**

Run: `cd backend && uv run pytest tests/test_gatekeeper.py -v`
Expected: FAIL — Gatekeeper class doesn't exist.

- [ ] **Step 3: Write Gatekeeper**

Create `backend/src/quorum/gatekeeper/__init__.py`:
```python
from .gatekeeper import Gatekeeper, GatekeeperResponse

__all__ = ["Gatekeeper", "GatekeeperResponse"]
```

Create `backend/src/quorum/gatekeeper/gatekeeper.py`:
```python
"""Gatekeeper: SDBench-style turn-based information-reveal game.

The Gatekeeper holds a case's available findings and reveals them
only when an agent queries with sufficient specificity. It tracks
simulated cost via a CMS-style schedule (test_costs.yaml).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from quorum.eval.eval_case import EvalCase, Finding
from quorum.llm.llm_client import LLMClient  # existing client

COSTS_PATH = Path(__file__).parent / "test_costs.yaml"


def _load_costs() -> dict:
    return yaml.safe_load(COSTS_PATH.read_text())


@dataclass
class GatekeeperResponse:
    matched: bool
    content: str
    cost_usd: float
    matched_label: Optional[str] = None
    turn_index: int = 0


class Gatekeeper:
    DEFAULT_MAX_TURNS = 30
    DEFAULT_MAX_COST = 5000.0

    def __init__(
        self,
        case: EvalCase,
        *,
        llm_client: Optional[LLMClient] = None,
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

    # --- public ---

    def query(self, question: str) -> GatekeeperResponse:
        if self.turn_index >= self.max_turns:
            raise RuntimeError(f"Gatekeeper exceeded max turns ({self.max_turns})")
        if self.simulated_cost >= self.max_cost_usd:
            raise RuntimeError(f"Gatekeeper exceeded max cost (${self.max_cost_usd})")

        self.turn_index += 1
        idx = self._llm_match(question, self.case.available_findings)

        if idx < 0:
            return GatekeeperResponse(
                matched=False,
                content="That information is not available in this case.",
                cost_usd=0.0,
                turn_index=self.turn_index,
            )

        finding = self.case.available_findings[idx]
        cost = self._cost_for(question, finding)
        self.simulated_cost += cost
        return GatekeeperResponse(
            matched=True,
            content=finding.content,
            cost_usd=cost,
            matched_label=finding.label,
            turn_index=self.turn_index,
        )

    # --- internal ---

    def _llm_match(self, question: str, findings: list[Finding]) -> int:
        """Return index of matched finding, or -1 if no match.

        Real implementation calls Sonnet 4.6 as a semantic matcher. Tests
        monkey-patch this method to keep them hermetic.
        """
        if not findings:
            return -1
        if self.llm_client is None:
            # Fallback to simple substring search on label
            ql = question.lower()
            for i, f in enumerate(findings):
                if any(tok in ql for tok in re.findall(r"\w+", f.label.lower()) if len(tok) > 3):
                    return i
            return -1

        prompt = self._build_match_prompt(question, findings)
        response = self.llm_client.complete(prompt, model="sonnet-4.6", max_tokens=20)
        try:
            idx = int(response.strip())
        except ValueError:
            return -1
        if 0 <= idx < len(findings):
            return idx
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

    def _cost_for(self, question: str, finding: Finding) -> float:
        """Lookup cost via category + label keyword match against test_costs.yaml."""
        cat = finding.category.lower()
        if cat not in self._costs:
            return self._costs.get("default_cost", 0.0)
        cat_costs = self._costs[cat]
        label_tokens = re.findall(r"\w+", finding.label.lower())
        for token in label_tokens:
            for test_name, price in cat_costs.items():
                if token in test_name or test_name in token:
                    return float(price)
        return self._costs.get("default_cost", 0.0)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_gatekeeper.py -v`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/src/quorum/gatekeeper/ backend/tests/test_gatekeeper.py
git commit -m "feat(gatekeeper): turn-based information-reveal Gatekeeper

Implements SDBench-style query/reveal game. LLM-as-matcher with
fallback keyword match. Tracks simulated CMS-cost ledger and
enforces hard limits on turns and cost."
```

---

## Phase 3 — AuditTrail module (Day 2, 4 hours)

### Task 3.1: TurnRecord schema

**Files:**
- Create: `backend/src/quorum/audit/__init__.py`
- Create: `backend/src/quorum/audit/schemas.py`
- Create: `backend/tests/test_audit_schemas.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_audit_schemas.py`:
```python
from datetime import datetime, timezone
from quorum.audit.schemas import TurnRecord, CaseAudit


def test_turnrecord_roundtrip():
    t = TurnRecord(
        turn_index=3,
        timestamp=datetime.now(timezone.utc),
        agent="hypothesis",
        message_role="out",
        content="Posterior: {SLE: 0.6, AML: 0.2}",
        tokens=350,
        cost_usd=0.012,
        posterior_at_turn={"SLE": 0.6, "AML": 0.2, "MCTD": 0.2},
    )
    d = t.model_dump()
    t2 = TurnRecord.model_validate(d)
    assert t == t2


def test_case_audit_aggregates_turns():
    audit = CaseAudit(case_id="toy-1", run_id="abc", model="sonnet-4.6")
    audit.turns.append(TurnRecord(
        turn_index=1, timestamp=datetime.now(timezone.utc),
        agent="hypothesis", message_role="out", content="x", tokens=1, cost_usd=0.0,
        posterior_at_turn={},
    ))
    assert len(audit.turns) == 1


def test_case_audit_jsonl_format():
    audit = CaseAudit(case_id="toy-1", run_id="abc", model="sonnet-4.6")
    lines = audit.to_jsonl()
    # 1 header line + 0 turns
    assert len(lines.splitlines()) == 1
```

- [ ] **Step 2: Run test, expect failure**

Run: `cd backend && uv run pytest tests/test_audit_schemas.py -v`
Expected: FAIL.

- [ ] **Step 3: Write schemas**

Create `backend/src/quorum/audit/__init__.py`:
```python
from .schemas import TurnRecord, CaseAudit
from .writer import AuditWriter

__all__ = ["TurnRecord", "CaseAudit", "AuditWriter"]
```

Create `backend/src/quorum/audit/schemas.py`:
```python
"""AuditTrail Pydantic schemas (v1, append-only).

A CaseAudit is one JSONL file per case with a header line followed by
one line per turn. The header captures run-level metadata; each turn
record captures everything the agent/gatekeeper did.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "audit.v1"


class TurnRecord(BaseModel):
    schema_version: Literal["audit.v1"] = SCHEMA_VERSION
    turn_index: int
    timestamp: datetime
    agent: str
    message_role: Literal["in", "out", "gatekeeper_query", "gatekeeper_response", "safety_check"]
    content: str
    tokens: int = 0
    cost_usd: float = 0.0
    posterior_at_turn: dict[str, float] = Field(default_factory=dict)
    extra: dict = Field(default_factory=dict)


class CaseAudit(BaseModel):
    schema_version: Literal["audit.v1"] = SCHEMA_VERSION
    case_id: str
    run_id: str
    model: str
    panel_config_name: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    turns: list[TurnRecord] = Field(default_factory=list)
    final_committed_diagnosis: Optional[str] = None
    simulated_cost_usd: float = 0.0
    real_cost_usd: float = 0.0
    judge_score: Optional[Literal["full_credit", "partial_credit", "no_credit"]] = None
    judge_rationale: Optional[str] = None

    def to_jsonl(self) -> str:
        header = self.model_copy(update={"turns": []}).model_dump_json()
        lines = [header]
        for turn in self.turns:
            lines.append(turn.model_dump_json())
        return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_audit_schemas.py -v`
Expected: PASS.

### Task 3.2: AuditWriter

**Files:**
- Create: `backend/src/quorum/audit/writer.py`
- Create: `backend/tests/test_audit_writer.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_audit_writer.py`:
```python
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from quorum.audit.writer import AuditWriter


def test_writer_creates_dir_and_writes_file():
    with tempfile.TemporaryDirectory() as td:
        run_id = "test-run-123"
        writer = AuditWriter(root=Path(td), run_id=run_id, case_id="toy-1", model="sonnet-4.6")
        writer.record_turn(agent="hypothesis", message_role="out", content="hello", tokens=10, cost_usd=0.001)
        writer.set_final(committed_diagnosis="SLE", real_cost_usd=0.5)
        writer.close()

        path = Path(td) / run_id / "toy-1.audit.jsonl"
        assert path.exists()
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2  # header + 1 turn
        header = json.loads(lines[0])
        assert header["case_id"] == "toy-1"
        assert header["final_committed_diagnosis"] == "SLE"
        turn = json.loads(lines[1])
        assert turn["agent"] == "hypothesis"
```

- [ ] **Step 2: Run test, expect failure**

Run: `cd backend && uv run pytest tests/test_audit_writer.py -v`
Expected: FAIL.

- [ ] **Step 3: Write writer**

Create `backend/src/quorum/audit/writer.py`:
```python
"""AuditWriter: streams CaseAudit JSONL to disk."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schemas import CaseAudit, TurnRecord


class AuditWriter:
    def __init__(self, root: Path, run_id: str, case_id: str, model: str, panel_config_name: Optional[str] = None):
        self.root = root
        self.run_id = run_id
        self.case_id = case_id
        self.dir = root / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{case_id}.audit.jsonl"
        self.audit = CaseAudit(
            case_id=case_id, run_id=run_id, model=model, panel_config_name=panel_config_name
        )

    def record_turn(self, **kwargs) -> None:
        if "turn_index" not in kwargs:
            kwargs["turn_index"] = len(self.audit.turns) + 1
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.now(timezone.utc)
        self.audit.turns.append(TurnRecord(**kwargs))

    def set_final(self, committed_diagnosis: Optional[str] = None, real_cost_usd: float = 0.0, simulated_cost_usd: float = 0.0) -> None:
        self.audit.final_committed_diagnosis = committed_diagnosis
        self.audit.real_cost_usd = real_cost_usd
        self.audit.simulated_cost_usd = simulated_cost_usd
        self.audit.completed_at = datetime.now(timezone.utc)

    def set_judge(self, score: str, rationale: str) -> None:
        self.audit.judge_score = score
        self.audit.judge_rationale = rationale

    def close(self) -> None:
        self.path.write_text(self.audit.to_jsonl())
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_audit_writer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/quorum/audit/ backend/tests/test_audit_*.py
git commit -m "feat(audit): TurnRecord + CaseAudit + AuditWriter

Append-only JSONL audit trail per case. Captures every agent
message, gatekeeper query, posterior, safety-check outcome."
```

---

## Phase 4 — Calibration module (Day 3, 4 hours)

### Task 4.1: Brier and ECE

**Files:**
- Create: `backend/src/quorum/calibration/__init__.py`
- Create: `backend/src/quorum/calibration/metrics.py`
- Create: `backend/tests/test_calibration.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_calibration.py`:
```python
import pytest
from quorum.calibration.metrics import compute_brier, compute_ece


def test_brier_perfect_prediction():
    # Posterior assigns 1.0 to truth → Brier = 0.0
    assert compute_brier({"a": 1.0, "b": 0.0}, "a") == pytest.approx(0.0)


def test_brier_uniform_two_outcomes():
    # 0.5 each, truth = "a" → Brier = (1-0.5)^2 + (0-0.5)^2 = 0.5
    assert compute_brier({"a": 0.5, "b": 0.5}, "a") == pytest.approx(0.5)


def test_brier_wrong_prediction():
    # Truth = "a", posterior gives 0 → (1-0)^2 + (0-1)^2 = 2.0
    assert compute_brier({"a": 0.0, "b": 1.0}, "a") == pytest.approx(2.0)


def test_brier_handles_missing_truth_label():
    """If ground truth isn't in posterior, treat as 0 probability."""
    assert compute_brier({"a": 1.0, "b": 0.0}, "c") == pytest.approx(2.0)


def test_ece_perfect_calibration():
    # 10 cases where confidence equals accuracy
    posteriors = [{"a": 0.5, "b": 0.5}] * 10
    truths = ["a"] * 5 + ["b"] * 5
    # When binned, confidence 0.5 → accuracy 0.5 → ECE = 0
    assert compute_ece(posteriors, truths, n_bins=2) < 0.01


def test_ece_total_miscalibration():
    # Confident wrong on all cases
    posteriors = [{"a": 0.95, "b": 0.05}] * 10
    truths = ["b"] * 10
    ece = compute_ece(posteriors, truths, n_bins=5)
    # Top-1 prediction is "a" but truth is "b" — accuracy 0, confidence ~0.95
    assert ece > 0.8
```

- [ ] **Step 2: Run test, expect failure**

Run: `cd backend && uv run pytest tests/test_calibration.py -v`
Expected: FAIL.

- [ ] **Step 3: Write metrics**

Create `backend/src/quorum/calibration/__init__.py`:
```python
from .metrics import compute_brier, compute_ece

__all__ = ["compute_brier", "compute_ece"]
```

Create `backend/src/quorum/calibration/metrics.py`:
```python
"""Calibration metrics: Brier score and Expected Calibration Error.

For ECE we use the standard 10-bin equal-frequency formulation
(Naeini et al, 2015). For Brier we use the multi-class form summed
over all candidate diagnoses in the posterior.
"""
from __future__ import annotations


def compute_brier(posterior: dict[str, float], ground_truth: str) -> float:
    """Multi-class Brier: sum over classes of (p_class - y_class)^2.

    If ground_truth is not in the posterior, treat it as if a key with
    probability 0 was implicitly present.
    """
    score = 0.0
    seen_truth = False
    for label, p in posterior.items():
        y = 1.0 if label == ground_truth else 0.0
        if label == ground_truth:
            seen_truth = True
        score += (p - y) ** 2
    if not seen_truth:
        # Truth was missing entirely (model gave it 0 probability)
        score += 1.0  # (0 - 1)^2
    return score


def compute_ece(posteriors: list[dict[str, float]], truths: list[str], n_bins: int = 10) -> float:
    """Expected Calibration Error using equal-frequency bins on top-1 confidence."""
    assert len(posteriors) == len(truths), "posteriors and truths must align"
    if not posteriors:
        return 0.0

    confidences = []
    correct = []
    for post, truth in zip(posteriors, truths):
        if not post:
            continue
        top_label = max(post, key=post.get)
        confidences.append(post[top_label])
        correct.append(1.0 if top_label == truth else 0.0)

    if not confidences:
        return 0.0

    # Equal-frequency binning
    pairs = sorted(zip(confidences, correct), key=lambda x: x[0])
    bin_size = max(1, len(pairs) // n_bins)
    ece = 0.0
    total = len(pairs)
    for b in range(0, total, bin_size):
        chunk = pairs[b:b + bin_size]
        if not chunk:
            continue
        avg_conf = sum(c for c, _ in chunk) / len(chunk)
        avg_acc = sum(a for _, a in chunk) / len(chunk)
        ece += (len(chunk) / total) * abs(avg_conf - avg_acc)
    return ece
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_calibration.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/src/quorum/calibration/ backend/tests/test_calibration.py
git commit -m "feat(calibration): Brier score and ECE metrics

Multi-class Brier and 10-bin equal-frequency ECE for panel
posteriors. Will be hooked into AuditTrail in Phase 5."
```

---

## Phase 5 — Sequential Diagnosis orchestrator mode (Days 3-4, 8 hours)

> ⚠️ **Phase 5 critical-fix preamble (from code-reviewer audit, 2026-05-27):** the plan's original Task 5.3 made several incorrect assumptions about the existing agent return contracts. Read the contract-audit task (Task 5.0) BEFORE writing any Phase 5 code.
>
> **Confirmed facts from the actual codebase:**
>
> 1. `Panel.__init__(llm: LLMClient, config: PanelConfig | None = None)` — first positional kwarg is `llm` (NOT `llm_client`).
> 2. All agents are async. `await self.llm.complete(messages=..., model=..., response_format=...)` — NOT `self.llm.complete(prompt, ...)`. Test stubs MUST be async.
> 3. Every agent's `deliberate(case, transcript, iteration)` returns `AgentMessage` with `structured_output: Optional[Union[Differential, NextTest, dict]]`.
> 4. There is NO `HypothesisOutput`, NO `_call_agent` helper, NO `posterior_over_shortlist` flat field, NO `accept_test` / `top_alternative` / `unresolved_concerns` flat fields. The plan's Task 5.3 sketch uses these names — they are placeholders, not real attributes.
> 5. The posterior lives in `Differential.candidates[i].posterior` (each `DiagnosisCandidate` has `name: str` and `posterior: float` already). No schema extension required to surface a posterior — adapt the accessor instead.
>
> **Implication for Task 5.3**: do not write `run_sequential` until you have completed Task 5.0 and produced `backend/src/quorum/orchestrator/AGENT_CONTRACTS.md`. After Task 5.0, REWRITE Task 5.3's `run_sequential` code and test fixture from scratch — do NOT copy the plan's sketch verbatim. The TDD test in Task 5.3 should use an async `AsyncMock` (from `unittest.mock`) for the `LLMClient`, with `complete()` returning JSON strings matching the real Differential/NextTest schemas.

### Task 5.0: Audit existing agent return contracts (NEW — added 2026-05-27)

**Files:**
- Read: `backend/src/quorum/orchestrator/schemas.py`
- Read: `backend/src/quorum/orchestrator/agents/{hypothesis,test_chooser,challenger,stewardship,checklist}.py`
- Read: `backend/src/quorum/orchestrator/panel.py`
- Read: `backend/src/quorum/llm/llm_client.py`
- Create: `backend/src/quorum/orchestrator/AGENT_CONTRACTS.md`

- [ ] **Step 1: Read each agent's `deliberate` signature and the JSON contract it expects/produces**

For each of the 5 agent files, find:
- The async method signature
- What it parses from the LLM JSON (the keys it accesses from `data`)
- What concrete type goes into `structured_output` (Differential? NextTest? dict?)
- The fields downstream code reads from the AgentMessage

- [ ] **Step 2: Read Panel orchestration to find how it currently consumes agent outputs**

Look at the existing `Panel.run_multi_iter` (or equivalent existing method) in `panel.py`. Note:
- How is `await self.hypothesis.deliberate(case, transcript, iteration)` called?
- How does Panel extract a "top diagnosis" or posterior from the returned AgentMessage?
- Is there an existing helper method or is it inlined?

- [ ] **Step 3: Read LLMClient interface**

Look at `backend/src/quorum/llm/llm_client.py`. Note:
- Is `complete` async? Yes.
- What are its kwargs? (`messages`, `model`, `response_format`, `max_tokens`, etc.)
- Does it return a string, or an object with `.content` / `.tokens_used` / `.cost_usd`?

- [ ] **Step 4: Write AGENT_CONTRACTS.md**

Write a concise reference doc at `backend/src/quorum/orchestrator/AGENT_CONTRACTS.md` capturing:

```markdown
# Agent return contracts (snapshot $(date +%Y-%m-%d))

## Panel
- Constructor: `Panel(llm: LLMClient, config: PanelConfig | None = None)`
- All agent calls are async (`await`).

## LLMClient.complete (async)
- Signature: `await llm.complete(messages=..., model=..., response_format=..., ...) -> LLMResponse`
- Returns: object with `.content` (str), `.tokens_used` (int), `.cost_usd` (float).

## HypothesisAgent
- Call: `await hyp.deliberate(case: CaseInput, transcript: list[AgentMessage], iteration: int) -> AgentMessage`
- AgentMessage.structured_output: `Differential` with `.candidates: list[DiagnosisCandidate]`
- DiagnosisCandidate: `.name (str)`, `.posterior (float, 0-1)`, `.icd10`, `.rationale`, `.supporting_findings`, `.against_findings`, `.citations`
- To extract posterior dict: `{c.name: c.posterior for c in msg.structured_output.candidates}`

## TestChooserAgent
- Returns AgentMessage with structured_output: NextTest
- NextTest: .name, .rationale, .estimated_cost_usd, .information_gain_estimate, .discriminates_between

## ChallengerAgent / StewardshipAgent / ChecklistAgent
- Each returns AgentMessage with structured_output: dict (free-form JSON depending on agent's prompt)
- Inspect the actual prompts at backend/src/quorum/orchestrator/prompts/{challenger,stewardship,checklist}.md to find the expected keys
- Adapt Task 5.3's accessor layer to whatever keys these prompts ask the LLM to emit
```

Fill in any details left blank from Steps 1-3.

- [ ] **Step 5: Commit**

```bash
cd /Users/lskarada/Documents/Claude/Quorum
git add backend/src/quorum/orchestrator/AGENT_CONTRACTS.md
git commit -m "docs(orchestrator): snapshot of actual agent return contracts

Reference for Phase 5 implementation. Replaces the plan's incorrect
assumptions about field names with the real Differential/NextTest/
AgentMessage structure."
```

### Task 5.1: SafetyChecker

**Files:**
- Create: `backend/src/quorum/orchestrator/safety.py`
- Create: `backend/tests/test_safety_checker.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_safety_checker.py`:
```python
import pytest
from quorum.orchestrator.safety import SafetyChecker, SafetyVerdict


def test_block_commit_without_enough_findings():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85},
        challenger_top="SLE",
        checklist_concerns=[],
        n_findings_queried=2,  # < 3
        simulated_cost=200,
    )
    assert v.blocked
    assert "3 queried findings" in v.reason


def test_block_commit_when_checklist_flagged():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85},
        challenger_top="SLE",
        checklist_concerns=["consider lymphoma given lymphadenopathy"],
        n_findings_queried=10,
        simulated_cost=500,
    )
    assert v.blocked


def test_block_commit_dx_not_in_shortlist():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="thyrotoxicosis",
        hypothesis_shortlist={"SLE": 0.85, "MCTD": 0.10},
        challenger_top="SLE",
        checklist_concerns=[],
        n_findings_queried=10,
        simulated_cost=500,
    )
    assert v.blocked


def test_force_commit_on_cost_overrun():
    sc = SafetyChecker(force_commit_cost_usd=5000)
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85},
        challenger_top="SLE",
        checklist_concerns=[],
        n_findings_queried=10,
        simulated_cost=6000,
    )
    # Cost overrun: commit must proceed regardless
    assert not v.blocked
    assert v.forced


def test_disagreement_triggers_extra_turn():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85, "AML": 0.05},
        challenger_top="lymphoma",  # disagrees substantially
        checklist_concerns=[],
        n_findings_queried=10,
        simulated_cost=500,
    )
    assert v.blocked
    assert "disagreement" in v.reason.lower()


def test_clean_commit_passes():
    sc = SafetyChecker()
    v = sc.check_commit(
        committed_dx="SLE",
        hypothesis_shortlist={"SLE": 0.85, "MCTD": 0.10},
        challenger_top="SLE",
        checklist_concerns=[],
        n_findings_queried=10,
        simulated_cost=500,
    )
    assert not v.blocked
```

- [ ] **Step 2: Run test, expect failure**

Run: `cd backend && uv run pytest tests/test_safety_checker.py -v`
Expected: FAIL.

- [ ] **Step 3: Write SafetyChecker**

Create `backend/src/quorum/orchestrator/safety.py`:
```python
"""Deterministic safety layer: 5 hard rules enforced before commit.

These are Python-checked, not LLM-judged. That's what makes them
auditable: a reviewer can replay the rules against any audit trail.
"""
from __future__ import annotations

from dataclasses import dataclass


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
        # Rule 4: cost overrun forces commit regardless
        if simulated_cost >= self.force_commit_cost:
            return SafetyVerdict(blocked=False, forced=True, reason="cost overrun: forced commit")

        # Rule 1: at least N findings queried
        if n_findings_queried < self.min_findings:
            return SafetyVerdict(
                blocked=True,
                reason=f"need ≥{self.min_findings} queried findings (have {n_findings_queried})",
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
        hypothesis_top = max(hypothesis_shortlist, key=hypothesis_shortlist.get)
        hyp_top_p = hypothesis_shortlist[hypothesis_top]
        challenger_p = hypothesis_shortlist.get(challenger_top, 0.0)
        if hypothesis_top != challenger_top and (hyp_top_p - challenger_p) > self.max_disagreement_pp:
            return SafetyVerdict(
                blocked=True,
                reason=f"Hypothesis/Challenger disagreement >{self.max_disagreement_pp*100:.0f}pp",
            )

        return SafetyVerdict(blocked=False)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_safety_checker.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/src/quorum/orchestrator/safety.py backend/tests/test_safety_checker.py
git commit -m "feat(safety): deterministic 5-rule safety layer

Hard Python rules enforce minimum findings, checklist concerns,
shortlist membership, cost forcing, and panel disagreement
before allowing a commit."
```

### Task 5.2: Extend Hypothesis schema with posterior (REVISED 2026-05-27)

> ⚠️ **Revision note**: the existing `Differential` already has per-candidate `posterior` floats (each `DiagnosisCandidate.posterior`). No new `HypothesisOutput` class needed. Task 5.2's purpose collapses to: ensure the existing posterior values **sum to 1.0** (or close) and add a Pydantic validator. Adapt accordingly. If schema extension turns out unnecessary, skip the test below and mark Task 5.2 complete after writing a one-line validator.

**Files:**
- Modify: `backend/src/quorum/orchestrator/schemas.py`

- [ ] **Step 1: Write failing test (extend existing)**

Add to `backend/tests/test_schemas_smoke.py` (or create new):
```python
from quorum.orchestrator.schemas import HypothesisOutput

def test_hypothesis_output_includes_posterior():
    out = HypothesisOutput(
        reasoning="x",
        top_diagnoses=["SLE", "MCTD"],
        posterior_over_shortlist={"SLE": 0.7, "MCTD": 0.2, "other": 0.1},
        confidence=0.7,
    )
    # Posterior must sum to (approximately) 1.0
    assert abs(sum(out.posterior_over_shortlist.values()) - 1.0) < 0.01
```

- [ ] **Step 2: Read current schemas**

Run: `cd backend && cat src/quorum/orchestrator/schemas.py | grep -A 5 "HypothesisOutput"`

- [ ] **Step 3: Add posterior field**

Edit `backend/src/quorum/orchestrator/schemas.py` to add:
```python
posterior_over_shortlist: dict[str, float] = Field(default_factory=dict)
```

to the existing `HypothesisOutput` model (place after `top_diagnoses`).

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_schemas_smoke.py -v -k posterior`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/quorum/orchestrator/schemas.py backend/tests/test_schemas_smoke.py
git commit -m "feat(schemas): Hypothesis emits posterior_over_shortlist

Required for calibration. Posterior is a dict[diagnosis, prob]
that must sum to ~1.0 (validated downstream by SafetyChecker)."
```

### Task 5.3: Sequential mode in Panel (REWRITTEN per Task 5.0 audit — 2026-05-27)

> ⚠️ **The original Task 5.3 code (test fixture + `run_sequential` body) is a sketch with wrong attribute names.** Replace it with code that uses the actual contracts you documented in AGENT_CONTRACTS.md. Key adjustments:
> - Stub LLM client must be `async`. Use `unittest.mock.AsyncMock` for `llm.complete`, configured to return objects with `.content`, `.tokens_used`, `.cost_usd`.
> - Panel constructor: `Panel(llm=stub, config=...)` — kwarg is `llm`, NOT `llm_client`.
> - To get posterior from Hypothesis: `{c.name: c.posterior for c in hyp_msg.structured_output.candidates}`.
> - To get TestChooser query: `tc_msg.structured_output.name` (NOT `.next_query`).
> - Challenger/Stewardship/Checklist `structured_output` is dict; read the keys their actual prompts emit (inspect prompts in Task 5.0 Step 1).
> - There is no `_call_agent` helper — invoke each agent directly: `await self.hypothesis.deliberate(case, transcript, iteration)`.

**Files:**
- Modify: `backend/src/quorum/orchestrator/panel.py`
- Modify: `backend/src/quorum/orchestrator/panel_config.py`
- Create: `backend/tests/test_sequential_panel.py`

- [ ] **Step 1: Write integration test**

Create `backend/tests/test_sequential_panel.py`:
```python
"""Integration test for sequential_diagnosis mode.

Uses a stubbed LLM client to avoid API calls. Verifies the panel
queries the Gatekeeper, accumulates posteriors, and commits within
the safety layer's rules.
"""
import pytest
from quorum.eval.eval_case import EvalCase, Finding
from quorum.gatekeeper.gatekeeper import Gatekeeper


@pytest.fixture
def toy_case():
    return EvalCase(
        case_id="toy-seq",
        corpus="nejm",
        source="test",
        initial_presentation="50yo with fatigue and joint pain",
        available_findings=[
            Finding(category="labs", label="ANA", content="ANA 1:640 homogeneous"),
            Finding(category="labs", label="anti-dsDNA", content="negative"),
            Finding(category="labs", label="anti-Smith", content="positive"),
            Finding(category="imaging", label="echo", content="normal"),
        ],
        ground_truth_diagnosis="systemic lupus erythematosus",
        acceptable_partial_credit=["SLE"],
    )


def test_panel_sequential_runs_end_to_end(toy_case, monkeypatch, tmp_path):
    """Full integration: panel queries gatekeeper, commits diagnosis."""
    from quorum.orchestrator.panel import Panel
    from quorum.orchestrator.panel_config import PanelConfig
    from quorum.audit.writer import AuditWriter

    # Use stub LLM client - returns deterministic responses
    class StubClient:
        call_count = 0
        def complete(self, prompt, **kwargs):
            StubClient.call_count += 1
            if "Hypothesis" in prompt:
                return '{"top_diagnoses": ["SLE", "RA"], "posterior_over_shortlist": {"SLE": 0.85, "RA": 0.15}, "reasoning": "x", "confidence": 0.85, "commit": true}'
            if "Gatekeeper" in prompt or "Match the question" in prompt:
                return "0"  # match first finding
            if "TestChooser" in prompt:
                return '{"next_query": "What is the ANA titer?"}'
            return "{}"

    gk = Gatekeeper(toy_case, llm_client=StubClient())
    writer = AuditWriter(root=tmp_path, run_id="t1", case_id=toy_case.case_id, model="stub")
    panel = Panel(config=PanelConfig.load("v2_quorum_calibrated"), llm_client=StubClient())

    result = panel.run_sequential(toy_case, gk, writer)

    assert result.committed_diagnosis is not None
    assert writer.audit.turns  # audit has events
    assert gk.turn_index >= 1
```

- [ ] **Step 2: Run test, expect failure**

Run: `cd backend && uv run pytest tests/test_sequential_panel.py -v`
Expected: FAIL — `run_sequential` doesn't exist yet, panel config name unknown.

- [ ] **Step 3: Add sequential mode to PanelConfig**

Edit `backend/src/quorum/orchestrator/panel_config.py` to add `sequential_diagnosis` to the mode enum/Literal. Create the YAML config (Task 5.4 below).

- [ ] **Step 4: Implement `run_sequential` in panel.py**

Add to `backend/src/quorum/orchestrator/panel.py` (near the existing `run_multi_iter`):

```python
def run_sequential(
    self,
    case: "EvalCase",
    gatekeeper: "Gatekeeper",
    audit_writer: "AuditWriter",
    *,
    max_turns: int = 30,
    commit_threshold: float = 0.7,
) -> "SequentialResult":
    """Sequential diagnostic encounter à la SDBench.

    Flow per turn:
      1. Hypothesis updates posterior given current evidence
      2. TestChooser proposes next Gatekeeper query
      3. Gatekeeper reveals finding (if matched)
      4. Challenger probes the new evidence
      5. Stewardship votes continue/stop
      6. Checklist enforces safety
      7. If Hypothesis posterior_top > commit_threshold or Stewardship stop
         → run SafetyChecker.check_commit. If clean → commit and return.
    """
    from quorum.orchestrator.safety import SafetyChecker
    from quorum.calibration.metrics import compute_brier

    safety = SafetyChecker()
    findings_revealed: list[Finding] = []

    for turn in range(1, max_turns + 1):
        # === Hypothesis ===
        hypothesis_out = self._call_agent(
            "hypothesis",
            case=case,
            findings=findings_revealed,
            audit_writer=audit_writer,
        )
        # === TestChooser ===
        next_query = self._call_agent(
            "test_chooser",
            case=case,
            findings=findings_revealed,
            audit_writer=audit_writer,
        )
        # === Gatekeeper ===
        gk_response = gatekeeper.query(next_query.next_query)
        audit_writer.record_turn(
            agent="gatekeeper",
            message_role="gatekeeper_response",
            content=gk_response.content,
            cost_usd=gk_response.cost_usd,
            extra={"matched_label": gk_response.matched_label},
        )
        if gk_response.matched:
            # Wrap as Finding to add to context
            findings_revealed.append(
                Finding(
                    category="(gatekeeper)",
                    label=gk_response.matched_label or "(unknown)",
                    content=gk_response.content,
                )
            )

        # === Challenger ===
        challenger_out = self._call_agent("challenger", case=case, findings=findings_revealed, audit_writer=audit_writer)

        # === Stewardship ===
        stewardship_out = self._call_agent("stewardship", case=case, findings=findings_revealed, audit_writer=audit_writer)

        # === Checklist ===
        checklist_out = self._call_agent("checklist", case=case, findings=findings_revealed, audit_writer=audit_writer)

        # === Commit decision ===
        post = hypothesis_out.posterior_over_shortlist
        if not post:
            continue
        top_dx = max(post, key=post.get)
        top_p = post[top_dx]

        if top_p >= commit_threshold or stewardship_out.vote == "stop":
            verdict = safety.check_commit(
                committed_dx=top_dx,
                hypothesis_shortlist=post,
                challenger_top=challenger_out.top_alternative,
                checklist_concerns=checklist_out.unresolved_concerns,
                n_findings_queried=len(findings_revealed),
                simulated_cost=gatekeeper.simulated_cost,
            )
            audit_writer.record_turn(
                agent="safety_checker",
                message_role="safety_check",
                content=verdict.reason or "OK",
                extra={"blocked": verdict.blocked, "forced": verdict.forced},
            )
            if not verdict.blocked:
                audit_writer.set_final(committed_diagnosis=top_dx, simulated_cost_usd=gatekeeper.simulated_cost)
                return SequentialResult(committed_diagnosis=top_dx, final_posterior=post, n_turns=turn)

    # max turns exhausted; force a commit on current top
    final_post = hypothesis_out.posterior_over_shortlist
    if final_post:
        top_dx = max(final_post, key=final_post.get)
    else:
        top_dx = "(no diagnosis)"
    audit_writer.set_final(committed_diagnosis=top_dx, simulated_cost_usd=gatekeeper.simulated_cost)
    return SequentialResult(committed_diagnosis=top_dx, final_posterior=final_post, n_turns=max_turns)


@dataclass
class SequentialResult:
    committed_diagnosis: str
    final_posterior: dict[str, float]
    n_turns: int
```

(`_call_agent` is assumed to exist or be added as a private helper that uses the existing per-agent prompt + LLMClient infrastructure. If it doesn't exist as a unified helper, refactor the existing per-agent methods into one.)

- [ ] **Step 5: Run integration test**

Run: `cd backend && uv run pytest tests/test_sequential_panel.py -v`
Expected: PASS (with stubbed LLM).

- [ ] **Step 6: Commit**

```bash
git add backend/src/quorum/orchestrator/panel.py backend/src/quorum/orchestrator/panel_config.py backend/tests/test_sequential_panel.py
git commit -m "feat(orchestrator): sequential_diagnosis mode

Implements SDBench-style multi-turn deliberation loop. Each turn:
Hypothesis → TestChooser → Gatekeeper → Challenger → Stewardship
→ Checklist → SafetyChecker. Commits when top posterior >= 0.7
or Stewardship votes stop, gated by deterministic safety rules."
```

### Task 5.4: v2 panel configs

**Files:**
- Create: `backend/config/panels/v2_quorum_calibrated.yaml`
- Create: `backend/config/panels/v2_single_sonnet.yaml`

- [ ] **Step 1: Write v2 panel YAMLs**

Create `backend/config/panels/v2_quorum_calibrated.yaml`:
```yaml
name: v2_quorum_calibrated
description: Calibrated, auditable Quorum with sequential diagnosis (Arm A)
mode: sequential_diagnosis
cost_prior_usd: 0.40
agents:
  hypothesis:
    model: claude-sonnet-4-6
    thinking: true
    cache_control: true
  test_chooser:
    model: claude-sonnet-4-6
    thinking: true
    cache_control: true
  challenger:
    model: claude-sonnet-4-6
    thinking: true
    cache_control: true
  stewardship:
    model: claude-sonnet-4-6
    thinking: false
    cache_control: true
  checklist:
    model: claude-sonnet-4-6
    thinking: false
    cache_control: true
sequential:
  max_turns: 30
  commit_threshold: 0.70
  gatekeeper_max_cost_usd: 5000
safety:
  min_findings_to_commit: 3
  max_disagreement_pp: 0.30
```

Create `backend/config/panels/v2_single_sonnet.yaml`:
```yaml
name: v2_single_sonnet
description: Single Sonnet 4.6 (no orchestration) baseline (Arm B)
mode: single_call
cost_prior_usd: 0.15
agents:
  single:
    model: claude-sonnet-4-6
    thinking: true
    cache_control: true
```

- [ ] **Step 2: Test that they load**

Run: `cd backend && uv run pytest tests/test_panel_config.py tests/test_new_panels_load.py -v` (add `v2_quorum_calibrated` and `v2_single_sonnet` to the loader tests if needed).

- [ ] **Step 3: Commit**

```bash
git add backend/config/panels/v2_*.yaml
git commit -m "feat(panels): v2 Arm A (Quorum-Calibrated) + Arm B (Single Sonnet) configs"
```

---

## Phase 6 — Per-agent prompt tuning (Days 4-5, 12 hours)

This phase is **iterative** and human-judgment driven. The /goal agent should:

### Task 6.1: Run smoke evaluation on 1 TUNE case

- [ ] **Step 1: Pick one TUNE case**

Run: `cd /Users/lskarada/Documents/Claude/Quorum && python3 -c "
import json
splits = json.load(open('data/cases/eval_corpus_v2/splits.json'))
print('TUNE case:', splits['tune'][0])
"`

- [ ] **Step 2: Run sequential panel on that case**

Run: `cd backend && uv run quorum-eval run --corpus eval_v2 --panel v2_quorum_calibrated --case-id <ID> --n 1`

Expected: writes `data/results/<run_id>/<ID>.audit.jsonl`.

- [ ] **Step 3: Read the audit trail**

Run: `cd /Users/lskarada/Documents/Claude/Quorum && cat data/results/<run_id>/<ID>.audit.jsonl | jq '.'`

Inspect: does Hypothesis emit a coherent posterior? Does TestChooser ask sensible queries? Does Gatekeeper match correctly? Does the commit happen at the right turn?

### Task 6.2: Iterate prompts (5 TUNE cases × ~10 iterations)

This is the longest phase by wall-clock. For each iteration:

- [ ] **Step 1: Run all 5 TUNE cases**

Run: `cd backend && uv run quorum-eval run --corpus eval_v2 --panel v2_quorum_calibrated --split tune`

Track real API spend. Per iteration: ~$2.

- [ ] **Step 2: Score with LLM-as-judge (use Sonnet 4.6 to save budget during tuning)**

Run: `cd backend && uv run quorum-eval judge data/results/<run_id> --judge-model claude-sonnet-4-6`

- [ ] **Step 3: Inspect failures**

Look for these patterns in the audit trails:
1. **Premature commit**: Hypothesis posterior > 0.7 before enough findings queried.
   → Tune Hypothesis prompt to be more uncertain early; tune SafetyChecker `min_findings_to_commit`.
2. **Weak TestChooser queries**: queries match no findings repeatedly.
   → Add few-shot examples of good queries to TestChooser prompt.
3. **Challenger doesn't surface alternatives**: top_alternative always matches Hypothesis top.
   → Tune Challenger prompt to explicitly probe "what diagnoses have we NOT considered."
4. **Checklist always silent**: never flags concerns.
   → Tune Checklist to actively look for incoherence (e.g., commit with <3 findings, posterior inconsistent with evidence).

- [ ] **Step 4: Edit ONE prompt at a time** in `backend/src/quorum/orchestrator/prompts/*.md`.

- [ ] **Step 5: Re-run TUNE**, compare audit trails to previous run.

- [ ] **Step 6: Commit each prompt iteration separately**:

```bash
git add backend/src/quorum/orchestrator/prompts/<agent>.md
git commit -m "tune(<agent>): <one-line description of change>

Iter #N. Observed failure mode: <X>. Hypothesis for fix: <Y>.
Result on TUNE: <accuracy or audit-completeness delta>."
```

### Task 6.3: Budget gate

- [ ] **Step 1: Check total spend after each TUNE iteration**

If accumulated tuning spend > $25, STOP and:
- Freeze prompts at current best state
- Move directly to Phase 7

### Task 6.4: Prompt freeze

- [ ] **Step 1: Tag git**

Run:
```bash
cd /Users/lskarada/Documents/Claude/Quorum
git tag v2-prompts-frozen
git push origin v2-prompts-frozen
```

- [ ] **Step 2: Document final TUNE performance**

Append to `docs/results_v2.md` (create if absent) the TUNE accuracy + Brier + ECE at freeze.

---

## Phase 7 — Headline EVAL run (Day 6, 3 hours real time + ~30 min compute)

### Task 7.1: Verify freeze and config

- [ ] **Step 1: Confirm tag exists**

Run: `git describe --tags --exact-match` (should match `v2-prompts-frozen`).

- [ ] **Step 2: Set MAX_SPEND_USD cap in env**

Run: `export QUORUM_MAX_SPEND_USD=80`

### Task 7.2: Run Arm A (Quorum-Calibrated)

- [ ] **Step 1: Run via Batch API**

Run: `cd backend && uv run quorum-eval run --corpus eval_v2 --panel v2_quorum_calibrated --split eval --batch-api --run-id v2-arm-a-final`

Expected: ~30 minutes wall clock (Batch API queue), ~$15 real spend. Outputs `data/results/v2-arm-a-final/*.audit.jsonl`.

- [ ] **Step 2: Track spend during the run**

If real spend approaches $20 for Arm A alone, investigate (cost outlier case) before continuing.

### Task 7.3: Run Arm B (Single Sonnet)

- [ ] **Step 1: Run**

Run: `cd backend && uv run quorum-eval run --corpus eval_v2 --panel v2_single_sonnet --split eval --batch-api --run-id v2-arm-b-final`

Expected: ~10 minutes, ~$5 real spend.

### Task 7.4: Score with LLM-as-judge

- [ ] **Step 1: Write judge module**

Create `backend/src/quorum/eval/judge.py`:
```python
"""LLM-as-judge for diagnostic scoring."""
from __future__ import annotations
import json
from typing import Literal
from quorum.llm.llm_client import LLMClient

JUDGE_PROMPT = """You are evaluating whether a diagnostic AI's final committed diagnosis matches the ground truth from a published clinical case.

GROUND_TRUTH: {ground_truth}
ACCEPTABLE_PARTIAL_CREDIT: {acceptable}
AI_COMMITTED: {ai_committed}

Score one of three:
- "full_credit": AI committed to the GROUND_TRUTH, or a synonymous/equivalent rephrasing.
- "partial_credit": AI committed to one of ACCEPTABLE_PARTIAL_CREDIT entries, or a diagnosis capturing disease category but missing specifics.
- "no_credit": AI committed to something not in either list.

Provide a one-sentence rationale.

Respond as strict JSON: {{"score": ..., "rationale": "..."}}
"""

def judge_case(
    *,
    ground_truth: str,
    acceptable_partial_credit: list[str],
    ai_committed: str,
    llm: LLMClient,
    model: str = "claude-sonnet-4-6",
) -> tuple[Literal["full_credit", "partial_credit", "no_credit"], str]:
    prompt = JUDGE_PROMPT.format(
        ground_truth=ground_truth,
        acceptable=json.dumps(acceptable_partial_credit),
        ai_committed=ai_committed,
    )
    resp = llm.complete(prompt, model=model, max_tokens=200)
    try:
        obj = json.loads(resp)
        return obj["score"], obj["rationale"]
    except (json.JSONDecodeError, KeyError):
        return "no_credit", f"judge parse failure: {resp[:100]}"
```

- [ ] **Step 2: Run judge on both arms**

Run:
```bash
cd backend && uv run quorum-eval judge data/results/v2-arm-a-final --judge-model claude-sonnet-4-6 --output data/results/v2-arm-a-final/judge_results.json
cd backend && uv run quorum-eval judge data/results/v2-arm-b-final --judge-model claude-sonnet-4-6 --output data/results/v2-arm-b-final/judge_results.json
```

Expected: ~$3 each.

### Task 7.5: Compute headline metrics

- [ ] **Step 1: Aggregate metrics**

Create `backend/scripts/compute_v2_metrics.py`:
```python
"""Aggregate v2 headline metrics from audit files + judge results."""
import json
from pathlib import Path
from quorum.calibration.metrics import compute_brier, compute_ece


def main(run_dir: Path) -> dict:
    audits = []
    for p in run_dir.glob("*.audit.jsonl"):
        lines = p.read_text().strip().splitlines()
        header = json.loads(lines[0])
        audits.append(header)
    judge = json.loads((run_dir / "judge_results.json").read_text())

    n = len(audits)
    n_full = sum(1 for a in audits if judge.get(a["case_id"], {}).get("score") == "full_credit")
    n_partial = sum(1 for a in audits if judge.get(a["case_id"], {}).get("score") == "partial_credit")

    return {
        "n_cases": n,
        "n_full_credit": n_full,
        "n_partial_credit": n_partial,
        "top_1_accuracy": n_full / n if n else 0,
        "top_1_or_partial": (n_full + n_partial) / n if n else 0,
        "mean_real_cost_usd": sum(a.get("real_cost_usd", 0) for a in audits) / n if n else 0,
        "total_real_cost_usd": sum(a.get("real_cost_usd", 0) for a in audits),
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(main(Path(sys.argv[1])), indent=2))
```

Run:
```bash
python3 backend/scripts/compute_v2_metrics.py data/results/v2-arm-a-final
python3 backend/scripts/compute_v2_metrics.py data/results/v2-arm-b-final
```

- [ ] **Step 2: Write `docs/results_v2.md`**

Create `docs/results_v2.md` with:
```markdown
# Quorum v2 Headline Results (Calibrated-Auditable MAI-DxO)

**Run date**: <YYYY-MM-DD>
**Eval set**: 30 held-out cases (20 NEJM CPC + 10 MedCaseReasoning + 5 RareBench)
**Models**: Sonnet 4.6 with extended thinking, prompt caching, Batch API

## Headline numbers

| Metric | Arm A (Quorum-Calibrated) | Arm B (Single Sonnet) | Reference |
|---|---|---|---|
| Top-1 accuracy | XX% | YY% | MAI-DxO+o3: 85% (Microsoft) |
| Top-1+partial | XX% | YY% | — |
| Brier (mean) | 0.XX | n/a | — |
| ECE | 0.XX | n/a | — |
| Audit completeness | XX% | n/a | — |
| Real cost / case | $0.XX | $0.XX | — |
| Total spend | $XX | $YY | — |

## Reproducibility

- Corpus: `data/cases/eval_corpus_v2/` with `splits.json` for the held-out partition
- Frozen at git tag `v2-prompts-frozen`
- Audit trails at `data/results/v2-arm-a-final/*.audit.jsonl`

## Interpretation

<one paragraph honest interpretation>
```

- [ ] **Step 3: Commit**

```bash
git add docs/results_v2.md backend/scripts/compute_v2_metrics.py
git commit -m "feat(eval): v2 headline metrics + results write-up"
git tag v2-eval-complete
```

---

## Phase 8 — Optional Opus arm (Day 6 evening, IF BUDGET ALLOWS)

### Task 8.1: Budget check

- [ ] **Step 1: Verify remaining envelope**

Compute: `$80 - (current spend)`. If remaining ≥ $20, proceed. Else skip.

### Task 8.2: Run Quorum-Calibrated on Opus 4.7 (10 cases)

- [ ] **Step 1: Add v2_quorum_opus.yaml**

Create `backend/config/panels/v2_quorum_opus.yaml` (same as `v2_quorum_calibrated.yaml` but with `model: claude-opus-4-7` for all agents).

- [ ] **Step 2: Run on 10 random EVAL cases**

Run: `cd backend && uv run quorum-eval run --corpus eval_v2 --panel v2_quorum_opus --split eval --n 10 --batch-api --run-id v2-arm-c-opus`

Expected: ~$15.

- [ ] **Step 3: Score and write up**

Append to `docs/results_v2.md` an Opus mini-arm section.

---

## Phase 9 — Write-up + demo prep (Days 7-9)

### Task 9.1: Update `docs/results.md`

- [ ] **Step 1: Add v2 section linking to results_v2.md**

Edit `docs/results.md` to prepend a "v2 headline (current)" section pointing to `docs/results_v2.md`.

### Task 9.2: Update `docs/eval_methodology.md`

- [ ] **Step 1: Add v2 methodology section**

Document: corpus construction, TUNE/EVAL discipline, three-arm design, Gatekeeper protocol, safety rules, calibration metrics, judge methodology.

### Task 9.3: Update `README.md`

- [ ] **Step 1: Rewrite README with new positioning**

Headline: "Quorum: the open-source, calibrated, auditable implementation of cost-aware sequential diagnostic deliberation. Reproduces the architectural shape of Microsoft's MAI-DxO on Claude Sonnet 4.6, with full audit trails and Brier/ECE calibration that closed implementations don't report."

### Task 9.4: Record demo video (~5 min)

- [ ] **Step 1: Start backend + frontend**

Run:
```bash
cd backend && uv run python scripts/serve_api.py &
cd frontend && pnpm dev
```

- [ ] **Step 2: Demo flow**

Record screen showing:
1. Pick a NEJM case from the eval corpus.
2. Click "Run Quorum-Calibrated."
3. Show panel deliberation streaming in.
4. Show Gatekeeper queries being made and findings being revealed.
5. Show running cost meter and audit trail expanding.
6. Show commit + final posterior chart.
7. Show audit trail JSON.

### Task 9.5: Push public

- [ ] **Step 1: Confirm repo is clean**

Run: `git status` — should show clean tree.

- [ ] **Step 2: Set GitHub repo to public**

Via GitHub UI or `gh repo edit --visibility public`.

- [ ] **Step 3: Tag v2.0**

```bash
git tag -a v2.0 -m "Quorum v2.0: Calibrated-Auditable MAI-DxO

Open-source reference implementation of cost-aware sequential
diagnostic deliberation. Sonnet 4.6 + extended thinking. n=30
held-out NEJM+MCR+RareBench eval. Brier/ECE calibration. Full
audit trails. MIT licensed."
git push origin v2.0
```

---

## Phase 10 — Stretch / fallback (Days 9-10)

### Task 10.1: Confirmation EVAL (if budget allows)

- [ ] **Step 1: Check remaining budget**

If ≥ $15 remaining, re-run Arm A on EVAL once more with different random seed for batch ordering.

- [ ] **Step 2: Compare variance**

Append variance analysis to `docs/results_v2.md`.

### Task 10.2: Fallback playbook (if anything failed)

- [ ] **If Arm A < Arm B accuracy:** Honest write-up that orchestration doesn't help on this corpus. Discuss why (e.g., Gatekeeper match quality, prompt tuning gaps).
- [ ] **If ECE > 0.30:** Document as "calibration is harder than accuracy" finding.
- [ ] **If audit completeness < 95%:** Find missing event types in `AuditWriter`, add hooks, re-run only EVAL Arm A.

---

## Acceptance Criteria (from spec §8)

Implementation is shipped when ALL of these are TRUE:

- [ ] Corpus at `data/cases/eval_corpus_v2/` with 35 cases, README, splits.json ✅ already done
- [ ] Gatekeeper unit tests pass
- [ ] AuditTrail unit tests pass; sample JSONL is human-readable
- [ ] Calibration tests pass against hand-rolled fixtures
- [ ] Sequential Diagnosis runs end-to-end on a TUNE case
- [ ] SafetyChecker demonstrably blocks a premature commit in TUNE
- [ ] Arm A top-1 ≥ Arm B top-1 (or honest write-up if not)
- [ ] Arm A reports Brier + ECE
- [ ] Audit completeness ≥ 95%
- [ ] Total real API spend ≤ $80
- [ ] GitHub repo public, MIT, with docs and demo
- [ ] CS153 deliverable submitted

---

## Self-Review (spec coverage check)

Spec section → Plan task mapping:

| Spec § | Coverage |
|---|---|
| §1 Strategic context | Documented in plan header |
| §2 Hard constraints | Budget Gate section + per-phase budget checks |
| §3 Corpus | Phase 1 Tasks 1.1-1.3 |
| §4.1 Gatekeeper | Phase 2 Task 2.2 |
| §4.1 AuditTrail | Phase 3 Tasks 3.1-3.2 |
| §4.1 Calibration | Phase 4 Task 4.1 |
| §4.2 Panel extension | Phase 5 Tasks 5.2-5.4 |
| §4.3 Safety layer | Phase 5 Task 5.1 |
| §5.1 Three-arm design | Phase 7 Tasks 7.2-7.5 + Phase 8 |
| §5.2 Scoring | Phase 7 Task 7.4 |
| §5.3 TUNE/EVAL discipline | Phase 1 Task 1.2 + Phase 6 |
| §6 Budget breakdown | Budget Gate section + Task 6.3 |
| §7 Phases | All phases mapped |
| §8 Acceptance | Final checklist |
| §9 Risks | Phase 10 fallback playbook |
| §10 Judge prompt | Phase 7 Task 7.4 |
| §11 Repo layout | File Structure section |
| §12 Out of scope | Honored throughout (no image reasoning, no real EHR tools, no genetic data) |
| §13 Open questions | Defaults applied; if /goal changes a default, it commits with rationale |
| §14 References | Embedded in spec; not re-listed here |

Gaps: none identified.
