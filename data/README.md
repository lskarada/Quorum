# Data

## Layout

```
data/
├── cases/
│   ├── nejm/
│   │   ├── _schema.json   # JSON Schema for NEJM CPC cases
│   │   └── *.json         # One case per file (gitignored; add yours locally)
│   └── medqa/
│       ├── _schema.json   # JSON Schema for MedQA cases
│       └── *.json
├── results/               # Eval run outputs (gitignored)
└── schemas/               # Generated Pydantic JSON schemas (gitignored;
                           # rebuild with `uv run python scripts/dump_schemas.py`)
```

## Adding a case

1. Create `data/cases/nejm/<case_id>.json` matching `_schema.json`.
2. The required fields are `case_id`, `presentation`, `ground_truth_diagnosis`.
3. Validate locally with any JSON-Schema linter, or simply run the eval —
   `quorum.eval.corpus.load_corpus` validates on read.

## Sourcing NEJM CPC cases

Microsoft's MAI-DxO paper (arXiv 2506.22405) describes how 304 cases were
reconstructed from the NEJM Clinical Pathology Conference series. The
methodology is summarized in `docs/eval_methodology.md`.

## Sourcing MedQA

MedQA is publicly available. Use the official USMLE split as the v1 corpus;
cite the original MedQA paper in any results report.

## Schemas

`data/schemas/quorum.schema.json` is generated from Pydantic
(`quorum.orchestrator.schemas`) via `scripts/dump_schemas.py`. The frontend
uses it to verify TypeScript-Pydantic shape parity.
