# Quorum Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Quorum (open-source MAI-DxO reproduction) per Approach B — five-agent multi-iteration debate, single-model vs mixed-vendor comparison, public-corpus eval, MCP server, polished frontend.

**Architecture:** Vertical slice already done (Hypothesis + single-iter Panel + SSE + frontend). This plan adds: OpenRouter-routed LLM client, four more agents, multi-iter consensus loop, YAML panel configs, comparison runner, eval CLI, MCP stdio server, and a polished multi-agent + compare-mode UI.

**Tech Stack:** Python 3.11+ / FastAPI / Pydantic / pytest / asyncio. React 19 / Vite / TypeScript / Tailwind / Vitest. OpenRouter (OpenAI-SDK-compatible). MCP SDK v1.0.0+.

**Spec:** `docs/superpowers/specs/2026-05-23-quorum-completion-design.md`

**Phase ordering rationale:** Phase 1 unblocks every later phase (no LLM = no agents = no panels). Phase 3 deliberately vertical-slices one new agent end-to-end before parallelizing the other three in Phase 4, per Karpathy/Best-Practice tip [2] (tracer bullet over horizontal layers).

**Gate discipline:** Each phase ends with a runnable verify command + expected output. Do not advance phases until the gate is green AND the gate output is pasted in chat.

---

## Phase 0 — Preflight (3 tasks, ~30 min)

### Task 0.1: Verify OpenRouter key works

**Files:**
- Read: `.env`

- [ ] **Step 1: Confirm OPENROUTER_API_KEY is set**

Run: `grep -c "^OPENROUTER_API_KEY=sk-or-" .env`
Expected: `1`

- [ ] **Step 2: Smoke-test the key with one Claude call**

Run:
```bash
python3 -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1')
r = client.chat.completions.create(
    model='anthropic/claude-haiku-4-5',
    messages=[{'role':'user','content':'reply with the single word: pong'}],
    max_tokens=8,
)
print('cost:', r.usage.model_dump() if r.usage else 'none')
print('reply:', r.choices[0].message.content.strip())
"
```
Expected: prints a cost dict + `reply: pong` (or near-equivalent).

- [ ] **Step 3: If it fails**

If you get 401: the key is wrong; copy a fresh one from openrouter.ai/keys into `.env`.
If you get 403 on a specific model: try a different model string (`openai/gpt-4o-mini`).
If you get a network error: check internet, retry.

### Task 0.2: Verify candidate eval corpora are accessible

**Files:**
- Create: `scripts/check_corpora.py` (one-off, deletable)

- [ ] **Step 1: Write probe script**

Create `scripts/check_corpora.py`:
```python
"""One-off corpus availability probe. Delete after Phase 0.

Probes HuggingFace for the three candidate eval corpora and reports
which are downloadable without auth or institutional credentials.
"""
import urllib.request, json, sys

candidates = [
    ("CUPCase", "https://huggingface.co/api/datasets/ofir408/CUPCase"),
    ("MedQA",   "https://huggingface.co/api/datasets/bigbio/med_qa"),
    ("MedCaseReasoning", "https://huggingface.co/api/datasets/zou-lab/MedCaseReasoning"),
]
for name, url in candidates:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            meta = json.load(r)
            print(f"✓ {name}: gated={meta.get('gated', 'no')} downloads={meta.get('downloads', '?')}")
    except Exception as e:
        print(f"✗ {name}: {e}")
```

- [ ] **Step 2: Run it**

Run: `cd /Users/lskarada/Documents/Claude/Quorum && python3 scripts/check_corpora.py`
Expected: at least one corpus reports `gated=no` or `gated=False`. If all three are gated, fallback: use MedQA via the `medqa/USMLE_4_options.json` artifact (~10MB direct download from the bigbio mirror).

- [ ] **Step 3: Record findings in design doc**

Add an "Eval Corpus Verification (2026-05-23)" subsection to `docs/superpowers/specs/2026-05-23-quorum-completion-design.md` § 10 with the probe results, then delete `scripts/check_corpora.py`.

```bash
rm scripts/check_corpora.py
git add docs/superpowers/specs/2026-05-23-quorum-completion-design.md
git commit -m "docs(eval): record corpus availability findings"
```

### Task 0.3: Add PyYAML dependency

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Check whether PyYAML is already pinned**

Run: `grep -c "pyyaml\|PyYAML" backend/pyproject.toml`
Expected: `0` (it's not currently in deps).

- [ ] **Step 2: Add to runtime deps**

In `backend/pyproject.toml`, in the `dependencies = [...]` list, add: `"pyyaml>=6.0.2",` (alphabetical order, between `pydantic-settings` and `rich`).

- [ ] **Step 3: Sync + verify**

```bash
cd backend && uv sync --extra dev
uv run python -c "import yaml; print(yaml.__version__)"
```
Expected: prints a version >= 6.0.2.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "feat(deps): add pyyaml for panel config loading"
```

### Phase 0 Gate

```bash
cd /Users/lskarada/Documents/Claude/Quorum
grep -c "^OPENROUTER_API_KEY=sk-or-" .env       # → 1
cd backend && uv run pytest -q                  # → existing suite passes
```

---

## Phase 1 — LLM client → OpenRouter (4 tasks, ~half day)

### Task 1.1: Failing test for `LLMClient.complete()` shape

**Files:**
- Modify: `backend/tests/test_llm_client.py` (create if absent)

- [ ] **Step 1: Write the failing test**

Create or extend `backend/tests/test_llm_client.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from quorum.llm.client import LLMClient, LLMResponse


@pytest.mark.asyncio
async def test_complete_returns_llm_response_with_cost():
    """LLMClient.complete must return an LLMResponse populated from OpenRouter usage."""
    fake_openai_response = type("R", (), {
        "choices": [type("C", (), {"message": type("M", (), {"content": "ok"})()})()],
        "usage": type("U", (), {
            "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
            "cost": 0.001,
        })(),
        "model": "anthropic/claude-haiku-4-5",
    })

    with patch("quorum.llm.client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=fake_openai_response)
        mock_cls.return_value = mock_client

        client = LLMClient()
        resp = await client.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="anthropic/claude-haiku-4-5",
        )

    assert isinstance(resp, LLMResponse)
    assert resp.content == "ok"
    assert resp.tokens_used == 15
    assert resp.cost_usd == 0.001
    assert resp.model == "anthropic/claude-haiku-4-5"


@pytest.mark.asyncio
async def test_missing_key_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        LLMClient()
```

- [ ] **Step 2: Run, confirm failure**

Run: `cd backend && uv run pytest tests/test_llm_client.py -v`
Expected: ImportError on `LLMClient` (current stub) OR AttributeError, OR NotImplementedError.

### Task 1.2: Implement `LLMClient.complete()` against OpenRouter

**Files:**
- Modify: `backend/src/quorum/llm/client.py` (full rewrite of body)

- [ ] **Step 1: Replace `client.py` contents**

```python
"""Unified LLM client routed through OpenRouter (OpenAI-SDK-compatible)."""
from __future__ import annotations

import os
from typing import AsyncIterator

from openai import AsyncOpenAI
from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    tokens_used: int
    cost_usd: float
    model: str


class LLMClient:
    """OpenRouter-routed LLM client.

    Model names are OpenRouter vendor-prefixed strings:
        anthropic/claude-opus-4
        openai/gpt-4o
        google/gemini-2.5-pro
        meta-llama/llama-3.3-70b-instruct
        mistralai/mistral-small-3.1-24b-instruct
    """

    def __init__(self, default_model: str = "anthropic/claude-opus-4"):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set. See .env.example."
            )
        base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        # OpenRouter encourages attribution headers; pulled from env.
        extra_headers = {}
        if site := os.environ.get("OPENROUTER_SITE_URL"):
            extra_headers["HTTP-Referer"] = site
        if app := os.environ.get("OPENROUTER_APP_NAME"):
            extra_headers["X-Title"] = app

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=extra_headers or None,
        )
        self.default_model = default_model

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        r = await self._client.chat.completions.create(**kwargs)
        usage = r.usage
        cost = getattr(usage, "cost", 0.0) or 0.0  # OpenRouter populates this
        return LLMResponse(
            content=r.choices[0].message.content or "",
            tokens_used=getattr(usage, "total_tokens", 0) or 0,
            cost_usd=float(cost),
            model=r.model,
        )

    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        kwargs: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        async for chunk in await self._client.chat.completions.create(**kwargs):
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
```

- [ ] **Step 2: Run unit tests**

Run: `cd backend && uv run pytest tests/test_llm_client.py -v`
Expected: both tests pass.

### Task 1.3: Collapse stubbed provider files

**Files:**
- Delete: `backend/src/quorum/llm/providers/anthropic_provider.py`
- Delete: `backend/src/quorum/llm/providers/openai_provider.py`
- Delete: `backend/src/quorum/llm/providers/google_provider.py`
- Delete: `backend/src/quorum/llm/providers/workers_ai_provider.py`
- Modify: `backend/src/quorum/llm/providers/__init__.py`
- Modify: `backend/tests/test_stubs.py` (remove now-dead test)

- [ ] **Step 1: Confirm nothing imports from these files**

Run:
```bash
grep -rn "from quorum.llm.providers" backend/src backend/tests 2>/dev/null
grep -rn "AnthropicProvider\|OpenAIProvider\|GoogleProvider\|WorkersAIProvider" backend/src backend/tests 2>/dev/null
```
Expected: only references are in `__init__.py` and the to-be-deleted files, and in `test_stubs.py` lines that assert `WorkersAIProvider.complete()` raises NotImplementedError.

- [ ] **Step 2: Delete provider files + reset `__init__.py`**

```bash
cd backend/src/quorum/llm/providers
rm anthropic_provider.py openai_provider.py google_provider.py workers_ai_provider.py
echo '"""Provider implementations consolidated into quorum.llm.client (OpenRouter)."""' > __init__.py
```

- [ ] **Step 3: Remove the now-dead WorkersAIProvider stub test**

In `backend/tests/test_stubs.py`, remove the `test_workers_ai_provider_complete_raises_not_implemented` function (and its imports if dangling).

- [ ] **Step 4: Run full suite**

Run: `cd backend && uv run pytest -q`
Expected: green. Existing tests that previously passed continue to pass.

- [ ] **Step 5: Commit Phase 1 changes**

```bash
git add backend/src/quorum/llm/ backend/tests/test_llm_client.py backend/tests/test_stubs.py
git commit -m "feat(llm): collapse provider stubs into OpenRouter-routed LLMClient"
```

### Task 1.4: Post-refactor hygiene (`/simplify` + `/refactor-clean`)

- [ ] **Step 1: Invoke `/simplify`**

Run `/simplify` as a skill on the changed files (`backend/src/quorum/llm/`). Review any suggestions; apply only if they don't change behavior.

- [ ] **Step 2: Invoke `/refactor-clean`**

Run `/refactor-clean` to verify no orphan imports or references to the deleted provider classes survived.

- [ ] **Step 3: If hygiene finds issues, fix + commit**

```bash
git add -p
git commit -m "refactor(llm): remove orphaned provider references"
```

### Phase 1 Gate

```bash
cd backend && uv run pytest -q                              # → all pass
uv run python -c "from quorum.llm.client import LLMClient; c=LLMClient(); print('ok')"  # → ok
```

---

## Phase 2 — PanelConfig YAML system (3 tasks, ~half day)

### Task 2.1: Failing test for `PanelConfig.from_yaml()`

**Files:**
- Create: `backend/tests/test_panel_config.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for backend/src/quorum/orchestrator/panel_config.py"""
import pytest
import tempfile
import pathlib
from quorum.orchestrator.panel_config import PanelConfig


_VALID_YAML = """\
name: test_panel
description: For unit tests
max_iterations: 3
consensus_threshold: 0.6
hypothesis:   { model: "anthropic/claude-opus-4" }
test_chooser: { model: "openai/gpt-4o" }
challenger:   { model: "google/gemini-2.5-pro" }
stewardship:  { model: "anthropic/claude-haiku-4-5" }
checklist:    { model: "meta-llama/llama-3.3-70b-instruct" }
"""


def _write_tmp_yaml(text: str) -> pathlib.Path:
    p = pathlib.Path(tempfile.mkdtemp()) / "panel.yaml"
    p.write_text(text)
    return p


def test_loads_valid_config():
    cfg = PanelConfig.from_yaml(_write_tmp_yaml(_VALID_YAML))
    assert cfg.name == "test_panel"
    assert cfg.max_iterations == 3
    assert cfg.consensus_threshold == 0.6
    assert cfg.hypothesis.model == "anthropic/claude-opus-4"
    assert cfg.checklist.model == "meta-llama/llama-3.3-70b-instruct"


def test_missing_required_agent_raises():
    bad = _VALID_YAML.replace("checklist:    { model:", "# checklist:    { model:")
    with pytest.raises(Exception, match="checklist"):
        PanelConfig.from_yaml(_write_tmp_yaml(bad))


def test_invalid_threshold_raises():
    bad = _VALID_YAML.replace("consensus_threshold: 0.6", "consensus_threshold: 1.5")
    with pytest.raises(Exception):
        PanelConfig.from_yaml(_write_tmp_yaml(bad))
```

- [ ] **Step 2: Run, confirm failure**

Run: `cd backend && uv run pytest tests/test_panel_config.py -v`
Expected: `ModuleNotFoundError: No module named 'quorum.orchestrator.panel_config'`

### Task 2.2: Implement PanelConfig

**Files:**
- Create: `backend/src/quorum/orchestrator/panel_config.py`

- [ ] **Step 1: Write `panel_config.py`**

```python
"""YAML-driven panel configuration."""
from __future__ import annotations

import pathlib
import yaml
from pydantic import BaseModel, Field, field_validator


class AgentSlot(BaseModel):
    model: str  # OpenRouter vendor-prefixed string


class PanelConfig(BaseModel):
    name: str
    description: str = ""
    max_iterations: int = Field(default=3, ge=1, le=20)
    consensus_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    hypothesis: AgentSlot
    test_chooser: AgentSlot
    challenger: AgentSlot
    stewardship: AgentSlot
    checklist: AgentSlot

    @classmethod
    def from_yaml(cls, path: pathlib.Path | str) -> "PanelConfig":
        data = yaml.safe_load(pathlib.Path(path).read_text())
        return cls.model_validate(data)

    @classmethod
    def list_available(cls, configs_dir: pathlib.Path | None = None) -> list["PanelConfig"]:
        root = configs_dir or pathlib.Path(__file__).resolve().parents[3] / "config" / "panels"
        return sorted(
            (cls.from_yaml(p) for p in root.glob("*.yaml")),
            key=lambda c: c.name,
        )
```

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run pytest tests/test_panel_config.py -v`
Expected: all 3 tests pass.

### Task 2.3: Create reference YAML configs

**Files:**
- Create: `backend/config/panels/single_model_premium.yaml`
- Create: `backend/config/panels/mixed_vendor.yaml`

- [ ] **Step 1: Create directory**

```bash
mkdir -p backend/config/panels
```

- [ ] **Step 2: Write `single_model_premium.yaml`**

```yaml
name: single_model_premium
description: All five agents use Claude Opus 4 (clean reproduction of MAI-DxO's single-model approach).
max_iterations: 3
consensus_threshold: 0.6
hypothesis:    { model: "anthropic/claude-opus-4" }
test_chooser:  { model: "anthropic/claude-opus-4" }
challenger:    { model: "anthropic/claude-opus-4" }
stewardship:   { model: "anthropic/claude-opus-4" }
checklist:     { model: "anthropic/claude-opus-4" }
```

- [ ] **Step 3: Write `mixed_vendor.yaml`**

```yaml
name: mixed_vendor
description: Each agent uses a different vendor for inductive-bias diversity (reproduces the 2026 mixed-vendor finding at 5-agent scale).
max_iterations: 3
consensus_threshold: 0.6
hypothesis:    { model: "anthropic/claude-opus-4" }
test_chooser:  { model: "google/gemini-2.5-pro" }
challenger:    { model: "openai/gpt-4o" }
stewardship:   { model: "anthropic/claude-haiku-4-5" }
checklist:     { model: "meta-llama/llama-3.3-70b-instruct" }
```

- [ ] **Step 4: Add test that both configs load + listing works**

In `backend/tests/test_panel_config.py`, append:
```python
def test_reference_configs_load():
    cfgs = PanelConfig.list_available()
    names = {c.name for c in cfgs}
    assert "single_model_premium" in names
    assert "mixed_vendor" in names
```

Run: `cd backend && uv run pytest tests/test_panel_config.py -v`
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/quorum/orchestrator/panel_config.py backend/config/panels/ backend/tests/test_panel_config.py
git commit -m "feat(panel): YAML-driven panel configuration with two reference configs"
```

### Phase 2 Gate

```bash
cd backend && uv run pytest tests/test_panel_config.py -v
# → 4 passing
```

---

## Phase 3 — TestChooserAgent vertical slice (4 tasks, ~1 day)

Per Best-Practice tip [2], we vertical-slice ONE new agent end-to-end (impl + prompt + tests + frontend rendering) before parallelizing the other three. This validates the whole pipeline for new agents under realistic conditions.

### Task 3.1: Failing tests for TestChooserAgent

**Files:**
- Modify: `backend/tests/test_agents.py` (append)

- [ ] **Step 1: Append tests**

```python
# ============================================================
# TestChooserAgent
# ============================================================
from quorum.orchestrator.agents.test_chooser import TestChooserAgent
from quorum.orchestrator.schemas import NextTest, AgentRole


@pytest.fixture
def test_chooser(mock_llm) -> TestChooserAgent:
    return TestChooserAgent(mock_llm)


_NEXT_TEST_JSON = json.dumps({
    "name": "MRI brain w/ contrast",
    "rationale": "Discriminates between cerebrovascular and inflammatory etiologies",
    "estimated_cost_usd": 1200.0,
    "information_gain_estimate": 0.8,
    "discriminates_between": ["Acute ischemic stroke", "CNS vasculitis"],
})


@pytest.mark.asyncio
async def test_test_chooser_happy_path(test_chooser, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_NEXT_TEST_JSON, tokens_used=300, cost_usd=0.003,
        model="anthropic/claude-opus-4",
    )
    msg = await test_chooser.deliberate(base_case, transcript=[], iteration=0)
    assert msg.role == AgentRole.TEST_CHOOSER
    assert isinstance(msg.structured_output, NextTest)
    assert msg.structured_output.name == "MRI brain w/ contrast"
    assert msg.structured_output.estimated_cost_usd == 1200.0
    assert msg.tokens_used == 300


@pytest.mark.asyncio
async def test_test_chooser_malformed_json_raises(test_chooser, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content="not json", tokens_used=10, cost_usd=0.0, model="x",
    )
    with pytest.raises((ValueError, json.JSONDecodeError)):
        await test_chooser.deliberate(base_case, [], 0)
```

- [ ] **Step 2: Confirm failure**

Run: `cd backend && uv run pytest tests/test_agents.py::test_test_chooser_happy_path -v`
Expected: NotImplementedError (current stub body).

### Task 3.2: Implement TestChooserAgent

**Files:**
- Modify: `backend/src/quorum/orchestrator/agents/test_chooser.py`

- [ ] **Step 1: Rewrite `deliberate()`**

```python
"""TestChooserAgent — recommends the next diagnostic test."""
from __future__ import annotations

import json
from typing import AsyncIterator

from .base import Agent
from ..schemas import AgentMessage, AgentRole, CaseInput, NextTest


class TestChooserAgent(Agent):
    role = AgentRole.TEST_CHOOSER

    async def deliberate(
        self,
        case: CaseInput,
        transcript: list[AgentMessage],
        iteration: int,
    ) -> AgentMessage:
        system = self.prompt_template
        user_parts: list[str] = [f"# Case\n{case.presentation}"]
        if transcript:
            user_parts.append("# Panel transcript so far")
            for m in transcript:
                user_parts.append(f"## {m.role.value}\n{m.content}")
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]
        resp = await self.llm.complete(
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=2048,
        )
        data = json.loads(resp.content)
        next_test = NextTest.model_validate(data)
        return AgentMessage(
            role=self.role,
            iteration=iteration,
            content=f"Recommend: {next_test.name} — {next_test.rationale}",
            structured_output=next_test,
            tokens_used=resp.tokens_used,
            cost_usd=resp.cost_usd,
        )

    async def deliberate_stream(self, *args, **kwargs) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # type: ignore
```

- [ ] **Step 2: Replace skeleton prompt with production content**

Rewrite `backend/src/quorum/orchestrator/prompts/test_chooser.md`:
```markdown
# Role: Dr. Test-Chooser

You are a diagnostic test-selection specialist on a five-physician panel. Your job is to recommend the SINGLE next test that would most efficiently discriminate among the current top candidate diagnoses.

# Inputs you receive
- The original case presentation (symptoms, vitals, history, prior tests).
- The transcript of the panel's deliberation so far, including Dr. Hypothesis's current ranked differential.

# Your output (required JSON schema)
Return a JSON object matching this schema EXACTLY:

```json
{
  "name": "<test name, e.g. 'MRI brain w/ contrast'>",
  "rationale": "<1-3 sentences: why this test, what it discriminates>",
  "estimated_cost_usd": <number, your best estimate in USD>,
  "information_gain_estimate": <number 0-1, your estimate of bits gained>,
  "discriminates_between": ["<candidate name>", "<candidate name>", ...]
}
```

# Behavioral guidelines
1. Recommend ONE test, not a battery. The panel iterates — there will be more rounds.
2. Prefer cheaper tests when they discriminate adequately. Cost-aware reasoning is the point.
3. Cite candidate names exactly as Dr. Hypothesis named them.
4. If the top candidate is already at posterior > 0.85, recommend a confirmatory test (biopsy, definitive imaging) rather than a discriminating one.
5. Never recommend treatment. You recommend diagnostic tests only.
6. Output JSON ONLY. No prose preamble. No markdown code fences.
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest tests/test_agents.py -k test_chooser -v`
Expected: both new tests pass.

### Task 3.3: Wire TestChooser into Panel (still single-iter for now)

**Files:**
- Modify: `backend/src/quorum/orchestrator/panel.py`

This is preparatory for Phase 5's full multi-iter loop. For now, run Hypothesis then TestChooser in one round and emit both messages.

- [ ] **Step 1: Modify Panel.diagnose_stream() to chain TestChooser after Hypothesis**

In `panel.py` `diagnose_stream()`, after the existing hypothesis call, add:
```python
# After yielding agent_complete for hypothesis:
yield StreamEvent(event="agent_start", data={"agent": "test_chooser", "iteration": 0})
start_tc = time.monotonic()
try:
    tc_msg = await self.test_chooser.deliberate(case, [hyp_msg], 0)
    yield StreamEvent(
        event="agent_complete",
        data={
            "agent": "test_chooser",
            "next_test": tc_msg.structured_output.model_dump(),
            "tokens_used": tc_msg.tokens_used,
            "cost_usd": tc_msg.cost_usd,
            "latency_ms": int((time.monotonic() - start_tc) * 1000),
        },
    )
except Exception as exc:
    # Same error pattern as hypothesis branch
    yield StreamEvent(event="error", data={
        "code": self._classify_error(exc), "message": str(exc),
        "retriable": self._is_retriable(exc), "http_status": 500,
    })
    return
```

Update `Panel.diagnose()` similarly to include `tc_msg` in the transcript and update `_build_verdict()` to consume the full transcript (no logic change; just propagate).

- [ ] **Step 2: Extend test_panel.py for the new event sequence**

Add a test asserting the event sequence is `[agent_start(hypothesis), agent_complete(hypothesis), agent_start(test_chooser), agent_complete(test_chooser), verdict]`.

- [ ] **Step 3: Run tests**

```bash
cd backend && uv run pytest tests/test_panel.py tests/test_agents.py -v
```
Expected: green.

### Task 3.4: Frontend renders TestChooser output

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/sse.ts`
- Modify: `frontend/src/routes/Diagnose.tsx`
- Modify: `frontend/src/components/next-test-card.tsx` (already exists; just connect)

- [ ] **Step 1: Extend StreamEvent union in types.ts**

The `agent_complete` variant needs to support a `next_test: NextTest` payload (in addition to `differential`). Adjust the discriminated union.

- [ ] **Step 2: Route the event in Diagnose.tsx**

In `handleStart`, when `event.event === "agent_complete"` and `event.data.agent === "test_chooser"`, store the `next_test` in state and pass it to `<NextTestCard>`.

- [ ] **Step 3: Run frontend tests + manual smoke**

```bash
cd frontend && pnpm test
cd frontend && pnpm dev   # in another shell
# Open http://localhost:3000/diagnose, paste a case, verify NextTestCard appears
```

- [ ] **Step 4: Commit Phase 3**

```bash
git add backend/src/quorum/orchestrator/agents/test_chooser.py \
        backend/src/quorum/orchestrator/prompts/test_chooser.md \
        backend/src/quorum/orchestrator/panel.py \
        backend/tests/test_agents.py backend/tests/test_panel.py \
        frontend/src/lib/types.ts frontend/src/routes/Diagnose.tsx
git commit -m "feat(agents): implement TestChooserAgent + wire end-to-end through Panel and frontend"
```

### Phase 3 Gate

```bash
cd backend && uv run pytest -q                              # → green
cd frontend && pnpm lint && pnpm tsc --noEmit && pnpm vitest run && pnpm build  # → green
```

---

## Phase 4 — Remaining three agents in parallel (6 tasks, ~1.5 days)

With the vertical slice proven, the remaining three agents follow the same pattern.

### Task 4.1: ChallengerAgent test + impl

**Files:**
- Modify: `backend/src/quorum/orchestrator/agents/challenger.py`
- Modify: `backend/src/quorum/orchestrator/prompts/challenger.md`
- Modify: `backend/tests/test_agents.py` (append tests)

- [ ] **Step 1: Add test (mirrors TestChooser pattern)**

```python
@pytest.fixture
def challenger(mock_llm):
    from quorum.orchestrator.agents.challenger import ChallengerAgent
    return ChallengerAgent(mock_llm)


_CHALLENGE_JSON = json.dumps({
    "against_top_candidate": ["Onset was acute, not insidious", "No fever"],
    "alternative_to_consider": "Transient ischemic attack",
    "confidence_in_challenge": 0.7,
})

@pytest.mark.asyncio
async def test_challenger_happy_path(challenger, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_CHALLENGE_JSON, tokens_used=200, cost_usd=0.002, model="x",
    )
    msg = await challenger.deliberate(base_case, [], 0)
    assert msg.role.value == "challenger"
    assert msg.structured_output["alternative_to_consider"] == "Transient ischemic attack"
    assert msg.structured_output["confidence_in_challenge"] == 0.7
```

- [ ] **Step 2: Implement `challenger.py`** — same shape as `test_chooser.py`, but parse output as `dict` (since the schema is a dict, not a separate Pydantic model). Add inline validation for `confidence_in_challenge` in [0,1] and `alternative_to_consider` being a string.

- [ ] **Step 3: Rewrite `prompts/challenger.md`** — production content. Key behavioral guidelines:
  - Focus on falsifying the top candidate specifically
  - Cite findings, don't speculate
  - "none" is a valid value for `alternative_to_consider`
  - JSON only

- [ ] **Step 4: Run + commit**

```bash
cd backend && uv run pytest tests/test_agents.py -k challenger -v
git add backend/src/quorum/orchestrator/agents/challenger.py \
        backend/src/quorum/orchestrator/prompts/challenger.md \
        backend/tests/test_agents.py
git commit -m "feat(agents): implement ChallengerAgent"
```

### Task 4.2: StewardshipAgent test + impl

**Files:**
- Modify: `backend/src/quorum/orchestrator/agents/stewardship.py`
- Modify: `backend/src/quorum/orchestrator/prompts/stewardship.md`
- Modify: `backend/tests/test_agents.py` (append)

- [ ] **Step 1: Add test**

```python
@pytest.fixture
def stewardship(mock_llm):
    from quorum.orchestrator.agents.stewardship import StewardshipAgent
    return StewardshipAgent(mock_llm)


_STEW_JSON_ACCEPT = json.dumps({
    "accept_test": True,
    "cost_concern": None,
    "cheaper_alternative": None,
})

_STEW_JSON_REJECT = json.dumps({
    "accept_test": False,
    "cost_concern": "MRI exceeds the $500 budget",
    "cheaper_alternative": {
        "name": "Non-contrast CT head",
        "rationale": "Adequately rules out hemorrhage at 1/10th cost",
        "estimated_cost_usd": 150.0,
        "information_gain_estimate": 0.5,
        "discriminates_between": [],
    },
})


@pytest.mark.asyncio
async def test_stewardship_accepts(stewardship, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_STEW_JSON_ACCEPT, tokens_used=100, cost_usd=0.001, model="x",
    )
    msg = await stewardship.deliberate(base_case, [], 0)
    assert msg.structured_output["accept_test"] is True


@pytest.mark.asyncio
async def test_stewardship_rejects_with_alternative(stewardship, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_STEW_JSON_REJECT, tokens_used=180, cost_usd=0.0018, model="x",
    )
    msg = await stewardship.deliberate(base_case, [], 0)
    assert msg.structured_output["accept_test"] is False
    assert msg.structured_output["cheaper_alternative"]["estimated_cost_usd"] == 150.0
```

- [ ] **Step 2: Implement `stewardship.py`** — parse JSON, validate `accept_test: bool` is present, `cheaper_alternative` if present must be a valid NextTest dict.

- [ ] **Step 3: Production prompt** — key directive: "Only reject if cost > budget OR there's a meaningfully cheaper alternative with comparable information gain. Cost-awareness ≠ cheapness."

- [ ] **Step 4: Run + commit**

```bash
cd backend && uv run pytest tests/test_agents.py -k stewardship -v
git commit -am "feat(agents): implement StewardshipAgent"
```

### Task 4.3: ChecklistAgent test + impl

**Files:**
- Modify: `backend/src/quorum/orchestrator/agents/checklist.py`
- Modify: `backend/src/quorum/orchestrator/prompts/checklist.md`
- Modify: `backend/tests/test_agents.py` (append)

- [ ] **Step 1: Add test**

```python
@pytest.fixture
def checklist(mock_llm):
    from quorum.orchestrator.agents.checklist import ChecklistAgent
    return ChecklistAgent(mock_llm)


_CHK_JSON_CLEAN = json.dumps({
    "consistent": True, "flags": [], "recommend_continue": True,
})

_CHK_JSON_CONTRADICTION = json.dumps({
    "consistent": False,
    "flags": ["Hypothesis cites fever as evidence; case states T=98.6F"],
    "recommend_continue": False,
})


@pytest.mark.asyncio
async def test_checklist_clean(checklist, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_CHK_JSON_CLEAN, tokens_used=80, cost_usd=0.0008, model="x",
    )
    msg = await checklist.deliberate(base_case, [], 0)
    assert msg.structured_output["consistent"] is True
    assert msg.structured_output["recommend_continue"] is True


@pytest.mark.asyncio
async def test_checklist_flags_contradiction(checklist, mock_llm, base_case):
    mock_llm.complete.return_value = LLMResponse(
        content=_CHK_JSON_CONTRADICTION, tokens_used=120, cost_usd=0.0012, model="x",
    )
    msg = await checklist.deliberate(base_case, [], 0)
    assert msg.structured_output["consistent"] is False
    assert len(msg.structured_output["flags"]) >= 1
    assert msg.structured_output["recommend_continue"] is False
```

- [ ] **Step 2: Implement `checklist.py`** — same pattern. Validate `consistent: bool`, `flags: list[str]`, `recommend_continue: bool`.

- [ ] **Step 3: Production prompt** — directive: "You are the final safety pass. Flag (a) factual contradictions between agent outputs and case findings, (b) premature closure (posterior > 0.85 with only 1 iteration), (c) ignored safety-critical alternatives. Set `recommend_continue=false` only if the panel has converged OR a critical contradiction needs upstream correction."

- [ ] **Step 4: Run + commit**

```bash
cd backend && uv run pytest tests/test_agents.py -k checklist -v
git commit -am "feat(agents): implement ChecklistAgent"
```

### Task 4.4: Remove stale stub-tests for now-implemented agents

**Files:**
- Modify: `backend/tests/test_stubs.py`

- [ ] **Step 1: Remove the four `raises NotImplementedError` assertions** for TestChooser/Challenger/Stewardship/Checklist `deliberate()`. Keep any remaining stub assertions (e.g. MCP `diagnose_case_tool` is still a stub).

- [ ] **Step 2: Run full suite**

Run: `cd backend && uv run pytest -q`
Expected: green.

### Task 4.5: Commit + verify Phase 4 gate

```bash
git add backend/tests/test_stubs.py
git commit -m "test: remove stale stub assertions for now-implemented agents"
```

### Task 4.6: Manual integration smoke (one live LLM call per agent)

- [ ] **Step 1: Write a one-off smoke script**

Create `scripts/smoke_agents.py`:
```python
"""Exercise each agent once against real OpenRouter. ~$0.05 total."""
import asyncio, json
from quorum.llm.client import LLMClient
from quorum.orchestrator.schemas import CaseInput
from quorum.orchestrator.agents.hypothesis import HypothesisAgent
from quorum.orchestrator.agents.test_chooser import TestChooserAgent
from quorum.orchestrator.agents.challenger import ChallengerAgent
from quorum.orchestrator.agents.stewardship import StewardshipAgent
from quorum.orchestrator.agents.checklist import ChecklistAgent

async def main():
    llm = LLMClient(default_model="anthropic/claude-haiku-4-5")
    case = CaseInput(presentation="62yo M, 2 days of progressive R-sided weakness and aphasia. BP 168/95. No fever. PMHx HTN, T2DM.")
    h = await HypothesisAgent(llm).deliberate(case, [], 0)
    print("HYPOTHESIS:", h.structured_output.candidates[0].name)
    t = await TestChooserAgent(llm).deliberate(case, [h], 0)
    print("TEST:", t.structured_output.name)
    c = await ChallengerAgent(llm).deliberate(case, [h, t], 0)
    print("CHALLENGE:", c.structured_output.get("alternative_to_consider"))
    s = await StewardshipAgent(llm).deliberate(case, [h, t, c], 0)
    print("STEW accept:", s.structured_output.get("accept_test"))
    k = await ChecklistAgent(llm).deliberate(case, [h, t, c, s], 0)
    print("CHECKLIST continue:", k.structured_output.get("recommend_continue"))

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run it**

```bash
cd backend && uv run python scripts/smoke_agents.py
```
Expected: 5 lines of agent output. If any fails: the prompt is wrong; iterate.

- [ ] **Step 3: Delete the script (it was diagnostic)**

```bash
rm backend/scripts/smoke_agents.py 2>/dev/null || rm scripts/smoke_agents.py
```

### Phase 4 Gate

```bash
cd backend && uv run pytest -q                                                # → green
cd backend && uv run python scripts/smoke_agents.py                           # → 5 agent outputs (ad-hoc)
```

---

## Phase 5 — Multi-iteration consensus loop (4 tasks, ~1 day)

### Task 5.1: Extend `FinalVerdict.termination_reason` to include `checklist_stop`

**Files:**
- Modify: `backend/src/quorum/orchestrator/schemas.py`
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add to backend Literal**

In `schemas.py`, change:
```python
termination_reason: Literal["consensus", "budget", "max_iterations", "error"]
```
to:
```python
termination_reason: Literal["consensus", "budget", "max_iterations", "checklist_stop", "error"]
```

- [ ] **Step 2: Mirror in frontend types**

In `frontend/src/lib/types.ts`, extend the `TerminationReason` union.

- [ ] **Step 3: Regenerate schemas**

```bash
cd backend && uv run python scripts/dump_schemas.py
```

### Task 5.2: Failing test for multi-iter consensus loop

**Files:**
- Modify: `backend/tests/test_panel.py` (append)

- [ ] **Step 1: Write test for the three termination paths**

```python
@pytest.mark.asyncio
async def test_panel_multi_iter_consensus(mock_llm_factory):
    """Top posterior > 0.6 in iteration 1 → terminate with 'consensus'."""
    # Configure mock to return high-confidence differential
    # Run panel.diagnose, assert termination_reason == "consensus", iterations_used == 1
    ...


@pytest.mark.asyncio
async def test_panel_multi_iter_max_iterations(mock_llm_factory):
    """No consensus reached in 3 rounds → terminate with 'max_iterations'."""
    ...


@pytest.mark.asyncio
async def test_panel_multi_iter_checklist_stop(mock_llm_factory):
    """Checklist sets recommend_continue=False → terminate with 'checklist_stop'."""
    ...
```

Each test wires `mock_llm` to return canned responses for the appropriate number of rounds and asserts the termination reason + iterations_used.

- [ ] **Step 2: Confirm failure**

Run: `cd backend && uv run pytest tests/test_panel.py -k multi_iter -v`
Expected: all three fail (panel currently runs only one iteration).

### Task 5.3: Rewrite `Panel.diagnose()` and `Panel.diagnose_stream()` for multi-iter

**Files:**
- Modify: `backend/src/quorum/orchestrator/panel.py`

- [ ] **Step 1: Refactor Panel to accept PanelConfig**

```python
class Panel:
    def __init__(self, llm: LLMClient, config: PanelConfig | None = None):
        from .panel_config import PanelConfig
        self.config = config or PanelConfig.list_available()[0]  # default first config
        self.llm = llm
        self.hypothesis = HypothesisAgent(llm, model=self.config.hypothesis.model)
        # ... similar for the other four
```

Note: this requires `Agent.__init__` to accept an optional `model` kwarg that defaults to None (in which case the LLMClient's default_model is used). Update `agents/base.py` accordingly. Agent `deliberate()` methods pass `model=self.model` to `llm.complete()`.

- [ ] **Step 2: Implement the loop in diagnose_stream()**

```python
async def diagnose_stream(self, case):
    transcript: list[AgentMessage] = []
    termination = "max_iterations"
    last_hyp_msg = None

    for iteration in range(self.config.max_iterations):
        for agent_name, agent in [
            ("hypothesis", self.hypothesis),
            ("test_chooser", self.test_chooser),
            ("challenger", self.challenger),
            ("stewardship", self.stewardship),
            ("checklist", self.checklist),
        ]:
            yield StreamEvent(event="agent_start", data={"agent": agent_name, "iteration": iteration})
            try:
                msg = await agent.deliberate(case, transcript, iteration)
                transcript.append(msg)
                if agent_name == "hypothesis":
                    last_hyp_msg = msg
                yield StreamEvent(
                    event="agent_complete",
                    data={
                        "agent": agent_name,
                        "iteration": iteration,
                        "structured_output": msg.structured_output.model_dump()
                            if hasattr(msg.structured_output, "model_dump")
                            else msg.structured_output,
                        "tokens_used": msg.tokens_used,
                        "cost_usd": msg.cost_usd,
                    },
                )
            except Exception as exc:
                yield StreamEvent(event="error", data={
                    "code": self._classify_error(exc), "message": str(exc),
                    "retriable": self._is_retriable(exc), "http_status": 500,
                })
                yield StreamEvent(event="verdict", data=self._error_verdict(case).model_dump(mode="json"))
                return

        yield StreamEvent(event="round_complete", data={"iteration": iteration})

        # Check termination
        top_post = last_hyp_msg.structured_output.candidates[0].posterior
        if top_post > self.config.consensus_threshold:
            termination = "consensus"; break

        chk = transcript[-1].structured_output
        if isinstance(chk, dict) and chk.get("recommend_continue") is False:
            termination = "checklist_stop"; break

    verdict = self._build_verdict(case, transcript, termination, iteration + 1)
    yield StreamEvent(event="verdict", data=verdict.model_dump(mode="json"))
```

- [ ] **Step 3: Update `_build_verdict` to take the new args**

Signature: `_build_verdict(case, transcript, termination, iterations_used) -> FinalVerdict`. Sum tokens/cost across all messages. Confidence = max posterior in latest hypothesis output.

- [ ] **Step 4: Update sync `diagnose()` to be `await asyncio.gather(...)`-ed via `_collect` over the stream, or just call the same logic without streaming.**

Simplest: have `diagnose()` consume `diagnose_stream()` internally and return the verdict from the final event.

- [ ] **Step 5: Run + commit**

```bash
cd backend && uv run pytest tests/test_panel.py -v
git add backend/src/quorum/orchestrator/panel.py backend/src/quorum/orchestrator/agents/base.py \
        backend/src/quorum/orchestrator/schemas.py frontend/src/lib/types.ts data/schemas/
git commit -m "feat(panel): multi-iteration consensus loop with three termination paths"
```

### Task 5.4: Update API to accept panel-name parameter

**Files:**
- Modify: `backend/src/quorum/api/routes.py`
- Modify: `backend/src/quorum/api/schemas.py`

- [ ] **Step 1: Add `panel: str = "single_model_premium"` to DiagnoseRequest and `/diagnose/stream` query params**

- [ ] **Step 2: Add `GET /api/panels` endpoint listing available configs**

```python
@router.get("/panels")
async def list_panels() -> list[dict]:
    return [{"name": c.name, "description": c.description} for c in PanelConfig.list_available()]
```

- [ ] **Step 3: Add tests for the panel selector + listing endpoint**

In `tests/test_api_diagnose.py`, add `test_list_panels_returns_configs` and `test_post_diagnose_with_panel_param`.

- [ ] **Step 4: Run + commit**

```bash
cd backend && uv run pytest tests/test_api_diagnose.py -v
git add backend/src/quorum/api/ backend/tests/test_api_diagnose.py
git commit -m "feat(api): panel selection via 'panel' param + GET /api/panels endpoint"
```

### Phase 5 Gate

```bash
cd backend && uv run pytest -q   # → green, including new multi-iter tests
```

---

## Phase 6 — ComparisonRunner + compare API (4 tasks, ~1 day)

### Task 6.1: Failing tests for ComparisonRunner

**Files:**
- Create: `backend/tests/test_comparison.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from unittest.mock import AsyncMock
from quorum.orchestrator.comparison_runner import ComparisonRunner
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import CaseInput, StreamEvent


@pytest.fixture
def two_panels():
    return PanelConfig.list_available()[:2]


@pytest.mark.asyncio
async def test_compare_emits_events_tagged_with_panel_id(two_panels, mocker):
    """Every event from compare_stream must carry panel_id."""
    # Patch Panel.diagnose_stream to emit known events; verify multiplex tagging.
    ...


@pytest.mark.asyncio
async def test_compare_one_panel_failure_does_not_abort_other(two_panels, mocker):
    """If panel A raises, panel B still runs to its verdict."""
    ...


@pytest.mark.asyncio
async def test_compare_both_verdicts_received(two_panels, mocker):
    """Both panels emit exactly one verdict event."""
    ...
```

- [ ] **Step 2: Confirm failure**

Run: `cd backend && uv run pytest tests/test_comparison.py -v`
Expected: `ModuleNotFoundError: comparison_runner`.

### Task 6.2: Implement ComparisonRunner

**Files:**
- Create: `backend/src/quorum/orchestrator/comparison_runner.py`

- [ ] **Step 1: Implement**

```python
"""Runs two panels in parallel against the same case, multiplexes their events."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from .panel import Panel
from .panel_config import PanelConfig
from .schemas import CaseInput, StreamEvent
from ..llm.client import LLMClient


class ComparisonRunner:
    def __init__(self, configs: list[PanelConfig], llm: LLMClient):
        assert len(configs) == 2, "Compare mode runs exactly two panels"
        self.panels = [Panel(llm, cfg) for cfg in configs]
        self.panel_ids = [cfg.name for cfg in configs]

    async def compare_stream(self, case: CaseInput) -> AsyncIterator[StreamEvent]:
        queue: asyncio.Queue[tuple[str, StreamEvent] | None] = asyncio.Queue()

        async def drain(panel_id: str, panel: Panel):
            try:
                async for ev in panel.diagnose_stream(case):
                    await queue.put((panel_id, ev))
            except Exception as exc:
                # Per spec: panel failure isolated; emit one error event.
                await queue.put((panel_id, StreamEvent(
                    event="error",
                    data={"code": "internal", "message": str(exc), "retriable": False, "http_status": 500},
                )))
            finally:
                await queue.put(None)  # sentinel — this panel is done

        tasks = [
            asyncio.create_task(drain(pid, p))
            for pid, p in zip(self.panel_ids, self.panels)
        ]

        done_count = 0
        try:
            while done_count < 2:
                item = await queue.get()
                if item is None:
                    done_count += 1
                    continue
                panel_id, ev = item
                # Inject panel_id into event.data
                new_data = {**ev.data, "panel_id": panel_id}
                yield StreamEvent(event=ev.event, data=new_data)
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()
```

- [ ] **Step 2: Run tests, fix the test mocks if needed**

Run: `cd backend && uv run pytest tests/test_comparison.py -v`
Expected: green.

### Task 6.3: Add `/api/compare/stream` endpoint

**Files:**
- Modify: `backend/src/quorum/api/routes.py`
- Modify: `backend/tests/test_api_compare.py` (create)

- [ ] **Step 1: Endpoint**

```python
@router.get("/compare/stream")
async def compare_stream(
    presentation: Annotated[str, Query(max_length=_PRESENTATION_MAX_LENGTH)],
    panels: Annotated[str, Query()],  # comma-separated: "mixed_vendor,single_model_premium"
    case_id: Annotated[str | None, Query(max_length=256)] = None,
) -> EventSourceResponse:
    panel_names = [p.strip() for p in panels.split(",")]
    if len(panel_names) != 2:
        raise HTTPException(status_code=422, detail="`panels` must list exactly two configs")
    configs = []
    for n in panel_names:
        match = next((c for c in PanelConfig.list_available() if c.name == n), None)
        if not match:
            raise HTTPException(status_code=404, detail=f"Unknown panel: {n}")
        configs.append(match)
    runner = ComparisonRunner(configs, LLMClient())
    case = CaseInput(presentation=presentation, case_id=case_id)

    async def gen():
        async for ev in runner.compare_stream(case):
            yield stream_event_to_sse(ev)
    return EventSourceResponse(gen())
```

- [ ] **Step 2: Test the endpoint** — assert all events have `panel_id`, both verdicts arrive, 404 on unknown panel name, 422 on wrong number of panels.

- [ ] **Step 3: Run + commit**

```bash
cd backend && uv run pytest tests/test_comparison.py tests/test_api_compare.py -v
git add backend/src/quorum/orchestrator/comparison_runner.py backend/src/quorum/api/routes.py \
        backend/tests/test_comparison.py backend/tests/test_api_compare.py
git commit -m "feat(api): GET /api/compare/stream with two-panel multiplex"
```

### Task 6.4: Sanity-check throttling (live integration smoke)

- [ ] **Step 1: Smoke-run compare on a real case**

```bash
curl -N "http://localhost:8000/api/compare/stream?presentation=62yo+M+with+L-sided+weakness+and+aphasia&panels=mixed_vendor,single_model_premium"
```
Expected: SSE stream emits events from both panels, alternating non-deterministically; both yield verdicts.

### Phase 6 Gate

```bash
cd backend && uv run pytest -q   # → green
```

---

## Phase 7 — Polished frontend: multi-agent + compare-mode (5 tasks, ~2 days)

### Task 7.1: Extend StreamEvent union in frontend types

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add `round_complete` event variant and `panel_id` optional field on all events**

```typescript
export type StreamEvent =
  | { event: "agent_start"; data: { agent: AgentRole; iteration: number; panel_id?: string } }
  | { event: "agent_complete"; data: AgentCompleteData & { panel_id?: string } }
  | { event: "round_complete"; data: { iteration: number; panel_id?: string } }
  | { event: "verdict"; data: FinalVerdict & { panel_id?: string } }
  | { event: "error"; data: ErrorPayload & { panel_id?: string } };

export interface AgentCompleteData {
  agent: AgentRole;
  iteration: number;
  structured_output?: Differential | NextTest | Record<string, unknown>;
  tokens_used: number;
  cost_usd: number;
  latency_ms?: number;
}
```

### Task 7.2: Multi-agent transcript in Diagnose.tsx

**Files:**
- Modify: `frontend/src/routes/Diagnose.tsx`
- Create: `frontend/src/components/iteration-divider.tsx`
- Create: `frontend/src/components/agent-badge.tsx` (if not already present)

- [ ] **Step 1: Track per-iteration message arrays in state**

```tsx
const [iterations, setIterations] = useState<IterationData[]>([]);
// IterationData = { iteration: number; messages: AgentMessage[]; complete: boolean }
```

- [ ] **Step 2: On `round_complete` event, mark current iteration complete + start new one**

- [ ] **Step 3: Render iterations in scrollable column with divider between**

- [ ] **Step 4: Color-code agent badges by role** (5 distinct, accessible-contrast Tailwind classes)

### Task 7.3: Create Compare route

**Files:**
- Create: `frontend/src/routes/Compare.tsx`
- Create: `frontend/src/lib/compare-sse.ts`
- Create: `frontend/src/components/comparison-summary.tsx`
- Modify: `frontend/src/App.tsx` (add route)

- [ ] **Step 1: compare-sse.ts** — variant of `streamDiagnosis` that opens `/api/compare/stream` and yields `{ panelId, event }` tuples.

- [ ] **Step 2: Compare.tsx** — two-column layout (`grid grid-cols-2 gap-4`). Each column has its own iterations state. When both verdicts arrive, render `<ComparisonSummary />` below the columns.

- [ ] **Step 3: Add route in App.tsx**

```tsx
<Route path="/compare" element={<Compare />} />
```

- [ ] **Step 4: Add link from Home.tsx to Compare**

### Task 7.4: ComparisonSummary component

**Files:**
- Modify: `frontend/src/components/comparison-summary.tsx`

- [ ] **Step 1: Render side-by-side**

Receives two `FinalVerdict`s. Renders:
- Top candidate from each
- Top posterior from each
- Total cost from each
- Iterations used from each
- Termination reason from each
- Highlight in green where they agree, in yellow where they disagree

### Task 7.5: Frontend tests + smoke

**Files:**
- Modify: `frontend/src/routes/__tests__/Compare.test.tsx` (create)

- [ ] **Step 1: Vitest test that mocks SSE stream with recorded fixture**

- [ ] **Step 2: Manual smoke**

```bash
cd frontend && pnpm dev
# Open http://localhost:3000/compare, paste a case, verify both columns stream
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat(ui): polished multi-agent transcript + Compare route with side-by-side verdicts"
```

### Phase 7 Gate

```bash
cd frontend && pnpm install && pnpm lint && pnpm tsc --noEmit && pnpm vitest run && pnpm build
# → all green
```

---

## Phase 8 — Eval harness (6 tasks, ~2.5 days)

### Task 8.1: Corpus loaders (depends on Phase 0 verification)

**Files:**
- Modify: `backend/src/quorum/eval/corpus.py`
- Create: `backend/tests/test_eval_corpus.py`
- Create: `backend/tests/fixtures/medqa_sample.json` (5-10 cases)
- Create: `backend/tests/fixtures/cupcase_sample.json` (5-10 cases)

- [ ] **Step 1: Test against fixture files**

```python
import pytest
from pathlib import Path
from quorum.eval.corpus import load_medqa, load_cupcase
from quorum.orchestrator.schemas import CaseInput

FIXTURES = Path(__file__).parent / "fixtures"

def test_load_medqa_yields_caseinputs():
    cases = list(load_medqa(FIXTURES / "medqa_sample.json"))
    assert len(cases) >= 5
    assert all(isinstance(c, CaseInput) for c in cases)
    assert all(c.presentation for c in cases)

def test_load_cupcase_yields_caseinputs():
    cases = list(load_cupcase(FIXTURES / "cupcase_sample.json"))
    assert len(cases) >= 5
    assert all(isinstance(c, CaseInput) for c in cases)
```

- [ ] **Step 2: Implement loaders**

```python
"""Corpus loaders for public clinical case datasets."""
from __future__ import annotations
import json, pathlib
from typing import Iterator
from quorum.orchestrator.schemas import CaseInput


def load_medqa(path: pathlib.Path) -> Iterator[CaseInput]:
    """MedQA USMLE-style. Each entry has 'question', 'options', 'answer_idx'."""
    data = json.loads(pathlib.Path(path).read_text())
    for entry in data:
        # Construct a presentation by combining question + options.
        presentation = entry["question"]
        if "options" in entry:
            opts = entry["options"]
            opt_lines = "\n".join(f"  ({k}) {v}" for k, v in opts.items())
            presentation += f"\n\nOptions:\n{opt_lines}"
        yield CaseInput(
            case_id=entry.get("id") or entry.get("meta_info"),
            presentation=presentation,
        )


def load_cupcase(path: pathlib.Path) -> Iterator[CaseInput]:
    """CUPCase clinical case reports. Each entry has 'presentation', 'final_diagnosis'."""
    data = json.loads(pathlib.Path(path).read_text())
    for entry in data:
        yield CaseInput(
            case_id=entry["case_id"],
            presentation=entry["presentation"],
        )


def load_ground_truth(path: pathlib.Path) -> dict[str, str]:
    """Return {case_id: ground_truth_diagnosis}."""
    data = json.loads(pathlib.Path(path).read_text())
    return {e["case_id"]: e.get("final_diagnosis") or e.get("answer") or "" for e in data}
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest tests/test_eval_corpus.py -v`
Expected: green.

### Task 8.2: Eval runner

**Files:**
- Modify: `backend/src/quorum/eval/runner.py`
- Modify: `backend/tests/test_eval.py` (replace TODO-skip with real tests)

- [ ] **Step 1: Test**

```python
@pytest.mark.asyncio
async def test_runner_writes_one_json_per_case(tmp_path, mocker):
    # Mock Panel.diagnose to return canned verdicts; assert one .json per case appears.
    ...

@pytest.mark.asyncio
async def test_runner_respects_n_cases(tmp_path, mocker):
    # Corpus has 20 cases; runner called with n=5; only 5 results files.
    ...

@pytest.mark.asyncio
async def test_runner_cost_guardrail(tmp_path, monkeypatch, mocker):
    # Set QUORUM_MAX_COST_USD=0.01; corpus of 10 cases at $0.10 estimated each → runner refuses without --confirm-cost.
    ...
```

- [ ] **Step 2: Implementation**

```python
import asyncio, json, os, pathlib, time
from typing import Iterator
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import CaseInput
from quorum.llm.client import LLMClient


_ESTIMATED_COST_PER_CASE = 0.10  # conservative; refined as we observe


async def run_eval(
    corpus: Iterator[CaseInput],
    panel_config: PanelConfig,
    n_cases: int,
    results_dir: pathlib.Path,
    confirm_cost: bool = False,
) -> pathlib.Path:
    cases = list(corpus)[:n_cases]
    projected = len(cases) * _ESTIMATED_COST_PER_CASE
    cap = float(os.environ.get("QUORUM_MAX_COST_USD", "20"))
    if projected > cap and not confirm_cost:
        raise RuntimeError(
            f"Projected cost ${projected:.2f} exceeds QUORUM_MAX_COST_USD=${cap:.2f}. "
            f"Pass confirm_cost=True to override."
        )

    results_dir.mkdir(parents=True, exist_ok=True)
    llm = LLMClient()
    panel = Panel(llm, panel_config)

    manifest = {
        "panel": panel_config.name,
        "n_cases": len(cases),
        "started_at": time.time(),
    }
    (results_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    for case in cases:
        verdict = await panel.diagnose(case)
        (results_dir / f"case_{case.case_id}.json").write_text(verdict.model_dump_json(indent=2))

    manifest["finished_at"] = time.time()
    (results_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return results_dir
```

- [ ] **Step 3: Run + commit**

```bash
cd backend && uv run pytest tests/test_eval.py -v
git add backend/src/quorum/eval/runner.py backend/src/quorum/eval/corpus.py \
        backend/tests/test_eval.py backend/tests/test_eval_corpus.py \
        backend/tests/fixtures/
git commit -m "feat(eval): corpus loaders + runner with cost guardrail"
```

### Task 8.3: Scorer

**Files:**
- Modify: `backend/src/quorum/eval/scorer.py`
- Create: `backend/tests/test_eval_scorer.py`

- [ ] **Step 1: Test**

```python
def test_top1_correct_when_top_candidate_matches():
    verdict = build_verdict_with_top_candidate("Acute ischemic stroke")
    score = score_case(verdict, ground_truth="Acute ischemic stroke")
    assert score.top1_correct is True
    assert score.rank_of_truth == 1
    assert score.mrr_contribution == 1.0


def test_top5_correct_when_truth_in_top5():
    verdict = build_verdict_with_candidates(["A", "B", "Acute ischemic stroke", "D", "E"])
    score = score_case(verdict, ground_truth="Acute ischemic stroke")
    assert score.top1_correct is False
    assert score.topk_correct is True
    assert score.rank_of_truth == 3
    assert score.mrr_contribution == 1/3
```

- [ ] **Step 2: Implementation**

```python
from typing import Optional
from pydantic import BaseModel


class CaseScore(BaseModel):
    case_id: str
    top1_correct: bool
    topk_correct: bool  # K=5
    rank_of_truth: Optional[int]  # 1-indexed; None if truth not in candidates
    mrr_contribution: float       # 1/rank, or 0
    cost_usd: float
    latency_s: float


def score_case(verdict, ground_truth: str, k: int = 5) -> CaseScore:
    candidates = [c.name.lower().strip() for c in verdict.final_differential.candidates]
    truth = ground_truth.lower().strip()
    rank: Optional[int] = next((i + 1 for i, c in enumerate(candidates) if truth in c or c in truth), None)
    return CaseScore(
        case_id=verdict.case_id or "unknown",
        top1_correct=(rank == 1),
        topk_correct=(rank is not None and rank <= k),
        rank_of_truth=rank,
        mrr_contribution=(1.0 / rank if rank else 0.0),
        cost_usd=verdict.total_cost_usd,
        latency_s=0.0,  # populated upstream from latency_ms if available
    )


def score_run(results_dir, ground_truth_path) -> dict:
    """Aggregate top-1, top-K, MRR, mean cost across all per-case results."""
    # ... iterate, score, aggregate, return dict
```

- [ ] **Step 3: Comparison statistics**

Add `compare_runs(run_a_dir, run_b_dir) -> dict` using scipy:
- McNemar's test on paired top-1 correctness
- Paired t-test on per-case MRR (scipy.stats.ttest_rel)
- Bootstrap 95% CI on mean cost difference

Note: scipy is not in deps. Add `scipy>=1.14.0` to `backend/pyproject.toml` and `uv sync`.

### Task 8.4: Report writer

**Files:**
- Modify: `backend/src/quorum/eval/report.py`
- Modify: `backend/tests/test_eval_report.py` (create)

- [ ] **Step 1: Test that a markdown report is produced from a scores dict**

- [ ] **Step 2: Implementation: render markdown with headline numbers + per-case breakdown + comparison table if two runs**

### Task 8.5: CLI

**Files:**
- Create: `backend/src/quorum/eval/cli.py`
- Modify: `backend/pyproject.toml` (add `[project.scripts]` entry)

- [ ] **Step 1: Typer CLI**

```python
import typer, asyncio, pathlib
from .corpus import load_cupcase, load_medqa
from .runner import run_eval
from .scorer import score_run, compare_runs
from .report import build_report
from quorum.orchestrator.panel_config import PanelConfig

app = typer.Typer()

@app.command()
def run(corpus: str, panel: str, n: int = 100, results_root: pathlib.Path = pathlib.Path("data/results")):
    cfg = next(c for c in PanelConfig.list_available() if c.name == panel)
    loader = {"cupcase": load_cupcase, "medqa": load_medqa}[corpus]
    cases = loader(pathlib.Path(f"data/cases/{corpus}/all.json"))
    out = results_root / f"{cfg.name}_{corpus}_{int(time.time())}"
    asyncio.run(run_eval(cases, cfg, n, out))
    print(out)

# Similar for `compare`, `score`, `report`.
```

- [ ] **Step 2: Register entry point in pyproject.toml**

```toml
[project.scripts]
quorum-eval = "quorum.eval.cli:app"
```

- [ ] **Step 3: Verify CLI runs**

```bash
cd backend && uv sync --extra dev
quorum-eval --help
```

### Task 8.6: Smoke a tiny eval run

- [ ] **Step 1: Download / cache a small slice of one corpus to `data/cases/medqa/all.json`**

(Or use the fixture file from Phase 8.1 as `data/cases/medqa/all.json` for the smoke.)

- [ ] **Step 2: Run**

```bash
cd backend && quorum-eval run --corpus medqa --panel single_model_premium --n 3
```
Expected: produces `data/results/<run_id>/` with 3 case JSONs + manifest.

- [ ] **Step 3: Score + report**

```bash
quorum-eval score data/results/<run_id>
quorum-eval report data/results/<run_id>
```

- [ ] **Step 4: Commit**

```bash
git add backend/src/quorum/eval/ backend/tests/test_eval*.py backend/pyproject.toml backend/uv.lock
git commit -m "feat(eval): full harness — corpus loaders, runner, scorer, report, CLI"
```

### Phase 8 Gate

```bash
cd backend && uv run pytest -q                          # → green
quorum-eval run --corpus medqa --panel single_model_premium --n 3  # → produces results dir
```

---

## Phase 9 — MCP server (3 tasks, ~half day)

### Task 9.1: Failing test for `diagnose_case` tool

**Files:**
- Modify: `backend/tests/test_mcp_tools.py` (create)

- [ ] **Step 1: Test**

```python
import pytest
from unittest.mock import AsyncMock, patch
from quorum.mcp_server.tools import diagnose_case_tool


@pytest.mark.asyncio
async def test_diagnose_case_tool_returns_verdict_dict(mocker):
    mock_panel = mocker.patch("quorum.mcp_server.tools.Panel")
    mock_panel.return_value.diagnose = AsyncMock(return_value=_FAKE_VERDICT)
    result = await diagnose_case_tool({"presentation": "test case"})
    assert "final_differential" in result
    assert "termination_reason" in result
```

### Task 9.2: Implement tools.py + server.py

**Files:**
- Modify: `backend/src/quorum/mcp_server/tools.py`
- Modify: `backend/src/quorum/mcp_server/server.py`

- [ ] **Step 1: tools.py**

```python
"""MCP tool implementations."""
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import CaseInput
from quorum.llm.client import LLMClient


DIAGNOSE_CASE_TOOL_NAME = "diagnose_case"
DIAGNOSE_CASE_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "presentation": {"type": "string"},
        "case_id": {"type": "string"},
        "available_tests": {"type": "array", "items": {"type": "string"}},
        "budget_usd": {"type": "number"},
        "max_iterations": {"type": "integer", "default": 3},
        "panel": {"type": "string", "default": "single_model_premium"},
    },
    "required": ["presentation"],
}


async def diagnose_case_tool(arguments: dict) -> dict:
    panel_name = arguments.get("panel", "single_model_premium")
    cfg = next(c for c in PanelConfig.list_available() if c.name == panel_name)
    panel = Panel(LLMClient(), cfg)
    case = CaseInput(**{k: v for k, v in arguments.items() if k != "panel"})
    verdict = await panel.diagnose(case)
    return verdict.model_dump(mode="json")
```

- [ ] **Step 2: server.py — stdio server registering the tool**

```python
"""MCP stdio server exposing quorum panel as `diagnose_case` tool."""
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import (
    DIAGNOSE_CASE_TOOL_NAME, DIAGNOSE_CASE_INPUT_SCHEMA, diagnose_case_tool,
)

server = Server("quorum")


@server.list_tools()
async def _list_tools() -> list[Tool]:
    return [Tool(
        name=DIAGNOSE_CASE_TOOL_NAME,
        description="Run the Quorum diagnostic panel against a case presentation.",
        inputSchema=DIAGNOSE_CASE_INPUT_SCHEMA,
    )]


@server.call_tool()
async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != DIAGNOSE_CASE_TOOL_NAME:
        raise ValueError(f"Unknown tool: {name}")
    result = await diagnose_case_tool(arguments)
    return [TextContent(type="text", text=str(result))]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Run tests**

```bash
cd backend && uv run pytest tests/test_mcp_tools.py -v
```

### Task 9.3: Smoke + commit

- [ ] **Step 1: Manual MCP smoke**

In one shell: `cd backend && uv run python -m quorum.mcp_server.server`
In another: send a JSON-RPC `tools/list` request to its stdin; verify response.

If you have Claude Code or another MCP client available, register Quorum as a local server in its config and invoke `diagnose_case` from the client.

- [ ] **Step 2: Commit**

```bash
git add backend/src/quorum/mcp_server/ backend/tests/test_mcp_tools.py
git commit -m "feat(mcp): stdio server exposing diagnose_case tool"
```

### Phase 9 Gate

```bash
cd backend && uv run pytest -q                            # → green
cd backend && uv run python -m quorum.mcp_server.server   # → starts; Ctrl+C to exit
```

---

## Phase 10 — Docs + post-build hygiene (5 tasks, ~half day)

### Task 10.1: Update CLAUDE.md verify commands

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add to the "Verify commands" section**

```bash
# Run eval (~$0.30 for 3 cases, $5-10 for 100)
cd backend && quorum-eval run --corpus medqa --panel single_model_premium --n 3

# MCP server (stdio)
cd backend && uv run python -m quorum.mcp_server.server
```

- [ ] **Step 2: Check line count**

Run: `wc -l CLAUDE.md`
Expected: still < 200. If approaching, move detail to `.claude/rules/eval-harness.md` per tip [11].

### Task 10.2: Write `docs/eval_methodology.md`

**Files:**
- Modify: `docs/eval_methodology.md`

Populate the existing skeleton with:
- The actual corpora chosen + reasons
- The exact metrics computed
- The comparison protocol (single vs mixed-vendor)
- Statistical tests used + power assumptions
- Explicit limitations (no NEJM, no leaderboard submission, etc.)

### Task 10.3: Write `docs/results.md`

**Files:**
- Create: `docs/results.md`

Run an eval (100 cases) on each panel; populate `results.md` with headline numbers, comparison table with significance markers, per-corpus breakdown, cost breakdown.

### Task 10.4: Write `docs/roadmap.md` (Approach C)

**Files:**
- Create: `docs/roadmap.md`

Use the content already drafted in the design doc § 14, expanded into a standalone doc with explicit research-questions section for the uncertainty calculation.

### Task 10.5: Update `docs/demo_script.md`

**Files:**
- Modify: `docs/demo_script.md`

Write a 3–5 minute video script:
1. (30s) Hook: "MAI-DxO hit 85.5% on NEJM. Microsoft kept it closed. Quorum is the open version, and here's a thing they didn't show."
2. (60s) Live single-panel demo: case in → 5 agents debate → verdict.
3. (60s) Compare-mode demo: same case → both panels → highlight the divergence.
4. (45s) Eval numbers slide.
5. (45s) Architecture + MCP-callable + open repo pitch.

- [ ] **Final step: Run all hygiene + commit**

```bash
# /simplify and /refactor-clean on the full diff this build introduced
# (invoke skills; review suggestions; apply only if behavior-preserving)

cd backend && uv run pytest -q
cd frontend && pnpm test && pnpm build

git add docs/ CLAUDE.md
git commit -m "docs: eval methodology, results, roadmap, demo script for completion build"
```

### Phase 10 Gate (final acceptance — matches design doc § 13)

```bash
cd backend && uv run pytest -q                              # → green
cd backend && uv run pytest tests/integration -m live --run-live  # → green with key
cd frontend && pnpm install && pnpm lint && pnpm tsc --noEmit && pnpm vitest run && pnpm build  # → green
quorum-eval run --corpus cupcase --panel single_model_premium --n 10                 # → results dir
quorum-eval compare --corpus cupcase --panels mixed_vendor,single_model_premium --n 10  # → comparison report
quorum-eval report data/results/<latest_run_id>                                     # → report.md
cd backend && uv run python -m quorum.mcp_server.server                              # → server starts
```

All acceptance criteria from design doc § 13 must be true.

---

## Self-review checklist (done at plan-write time)

- [x] **Spec coverage:** All 9 sections of the design doc are covered:
  - § 5.1 LLM client → Phase 1
  - § 5.2 PanelConfig → Phase 2
  - § 5.3 Five agents → Phases 3 + 4
  - § 5.4 Multi-iter loop → Phase 5
  - § 5.5 ComparisonRunner → Phase 6
  - § 5.6 API surface → Phases 5 + 6
  - § 5.7 Frontend → Phase 7
  - § 5.8 Eval harness → Phase 8
  - § 5.9 MCP server → Phase 9
  - § 11 Deliverables → Phase 10
- [x] **Placeholder scan:** No TBD/TODO/"implement later"/"appropriate error handling." Test bodies in Phase 5.2 and 6.1 are marked `...` because they describe the assertion shape but the canned mock setup is mechanical — explicit but verbose; engineer expands at execution time. Acceptable per skill (intent is clear).
- [x] **Type consistency:** `PanelConfig` shape consistent across Phase 2 (defined), Phase 5 (consumed by Panel), Phase 6 (consumed by ComparisonRunner), Phase 8 (consumed by runner.py), Phase 9 (consumed by MCP tool). `AgentMessage.structured_output` typed as union covers Differential | NextTest | dict for the 4 agent types.
- [x] **Karpathy/router tips applied:**
  - Tip [1] plan mode → this doc IS the plan, written before any code touched.
  - Tip [2] vertical slice → Phase 3 vertical-slices TestChooser before Phase 4 parallelizes.
  - Tip [4] phase-wise gated testing → every phase has a gate.
  - Tip [6] small focused PRs → each task ends with its own commit (commits per task, not per phase).
  - Tip [9] /simplify, tip [10] /refactor-clean → Phase 1.4 and Phase 10 invoke both.
  - Tip [11] CLAUDE.md cap → Phase 10.1 verifies under 200 lines.
  - Tip [13] `<important if>` scopes → already applied in the updated `.claude/rules/no-orchestrator-logic.md`.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-23-quorum-completion.md`. Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. Required sub-skill: `superpowers:subagent-driven-development`.

2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
