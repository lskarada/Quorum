"""YAML-driven panel configuration."""
from __future__ import annotations

import pathlib

import yaml
from pydantic import BaseModel, Field


class AgentSlot(BaseModel):
    model: str                       # OpenRouter vendor-prefixed string
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: int | None = None          # optional determinism handle
    max_tokens: int = Field(default=4096, ge=1, le=32000)


class PanelConfig(BaseModel):
    name: str
    description: str = ""
    max_iterations: int = Field(default=3, ge=1, le=20)
    consensus_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    schema_version: int = 1
    # NOTE: `hypothesis` is the only required slot. The four others may be omitted
    # for the baseline_single_call config — see Task 2.3. Panel.diagnose()
    # skips agents whose slot is None.
    hypothesis: AgentSlot
    test_chooser: AgentSlot | None = None
    challenger: AgentSlot | None = None
    stewardship: AgentSlot | None = None
    checklist: AgentSlot | None = None

    @classmethod
    def from_yaml(cls, path: pathlib.Path | str) -> PanelConfig:
        data = yaml.safe_load(pathlib.Path(path).read_text())
        return cls.model_validate(data)

    @classmethod
    def list_available(cls, configs_dir: pathlib.Path | None = None) -> list[PanelConfig]:
        root = configs_dir or pathlib.Path(__file__).resolve().parents[3] / "config" / "panels"
        return sorted(
            (cls.from_yaml(p) for p in root.glob("*.yaml")),
            key=lambda c: c.name,
        )
