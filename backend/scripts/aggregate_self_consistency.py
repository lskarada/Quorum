"""Self-consistency vote aggregator for Quorum v2 eval runs.

Collects k repeated panel runs for the same case corpus, clusters
clinically-equivalent diagnosis strings into equivalence classes, votes on
canonical classes, and writes a merged audit directory that judge_v2_run.py
and compute_v2_metrics.py can read identically to a normal single run.

Usage
-----
    python backend/scripts/aggregate_self_consistency.py OUT_DIR RUN0 RUN1 [RUN2 ...]

    OUT_DIR   — new directory to create; must not already exist.
    RUN0 ...  — existing run directories, each containing *.audit.jsonl files
                written by quorum.eval.v2_runner.

The voted output preserves the REAL audit.jsonl schema:
- Line 0 (header): schema_version, case_id, run_id, model, panel_config_name,
  started_at, completed_at, turns (empty list), final_committed_diagnosis,
  final_posterior, simulated_cost_usd, real_cost_usd, plus sc_k,
  sc_confidence, judge_score=None, judge_rationale=None.
- Lines 1+ (turns): omitted in the voted output (turns=[] in header is
  sufficient for judge_v2_run.py + compute_v2_metrics.py).

Synonym clustering
------------------
By default (cluster_fn=None), one LLM call per case groups the k raw strings
into named equivalence classes.  For tests, pass a deterministic cluster_fn:

    cluster_fn(strings: list[str]) -> dict[str, str]
        Maps each raw string to a canonical label.  Strings absent from the
        returned dict are left as-is (self-canonical).

WHY clustering is mandatory: "SLE" / "lupus" / "systemic lupus erythematosus"
are clinically identical but differ as strings, splitting a 4/5 agreement into
three 1-2 count buckets.  Clustering collapses them before the vote so SC
achieves its correctness benefit.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


# ---------------------------------------------------------------------------
# Default LLM clusterer (reuses judge's LLMClient + Sonnet model)
# ---------------------------------------------------------------------------

CLUSTER_SYSTEM = (
    "You are a medical terminologist. Given a list of diagnosis strings, "
    "group clinically equivalent entries into equivalence classes and assign "
    "each class a canonical standard label."
)

CLUSTER_USER_TEMPLATE = """Here are {n} diagnosis strings from repeated runs of a clinical diagnostic AI:

{strings_json}

Group strings that refer to the same clinical entity (synonyms, abbreviations,
varying specificity that still points to the same diagnosis) into equivalence
classes. Assign each class a canonical label (the most specific, standard
clinical name).

Respond as strict JSON:
{{
  "classes": [
    {{
      "canonical": "<standard label>",
      "members": ["<raw string 1>", "<raw string 2>", ...]
    }},
    ...
  ]
}}

Every input string must appear in exactly one class."""


def _make_default_cluster_fn() -> Callable[[list[str]], dict[str, str]]:
    """Return a cluster_fn backed by one LLM call per case.

    Lazily imports LLMClient (requires OPENROUTER_API_KEY in env).
    NOT called during tests.
    """
    import asyncio

    from quorum.llm.client import LLMClient

    llm = LLMClient()

    def cluster_fn(strings: list[str]) -> dict[str, str]:
        unique = list(dict.fromkeys(strings))  # deduplicate preserving order
        user_msg = CLUSTER_USER_TEMPLATE.format(
            n=len(unique),
            strings_json=json.dumps(unique, indent=2),
        )
        response = asyncio.run(
            llm.complete(
                messages=[
                    {"role": "system", "content": CLUSTER_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                model="anthropic/claude-sonnet-4-6",
                response_format={"type": "json_object"},
                max_tokens=1024,
            )
        )
        try:
            obj = json.loads(response.content)
            mapping: dict[str, str] = {}
            for cls in obj.get("classes", []):
                canonical = cls["canonical"]
                for member in cls.get("members", []):
                    mapping[member] = canonical
            # Any string not returned by LLM stays self-canonical
            for s in unique:
                if s not in mapping:
                    mapping[s] = s
            return mapping
        except (json.JSONDecodeError, KeyError, TypeError):
            # Fall back to identity mapping on parse failure
            return {s: s for s in unique}

    return cluster_fn


# ---------------------------------------------------------------------------
# Core aggregation logic
# ---------------------------------------------------------------------------

def _load_headers(run_dirs: list[Path]) -> dict[str, list[dict]]:
    """Return {case_id: [header_dict, ...]} across all run dirs.

    Each entry is the first-line header from <case_id>.audit.jsonl.
    """
    cases: dict[str, list[dict]] = {}
    for run_dir in run_dirs:
        for audit_path in sorted(run_dir.glob("*.audit.jsonl")):
            case_id = audit_path.stem.replace(".audit", "")
            lines = audit_path.read_text().strip().splitlines()
            if not lines:
                continue
            header = json.loads(lines[0])
            cases.setdefault(case_id, []).append(header)
    return cases


def _vote(
    headers: list[dict],
    cluster_fn: Callable[[list[str]], dict[str, str]],
) -> dict:
    """Aggregate k headers into one voted header dict."""
    k = len(headers)

    # Collect raw committed diagnoses
    raw_strings = [
        h.get("final_committed_diagnosis") or "(none)" for h in headers
    ]

    # Cluster synonyms -> canonical labels
    mapping = cluster_fn(raw_strings)
    canonical_labels = [mapping.get(s, s) for s in raw_strings]

    # Vote
    counts = Counter(canonical_labels)
    winner_label, winner_votes = counts.most_common(1)[0]
    sc_confidence = winner_votes / k

    # Posterior: fraction of votes for each canonical class
    final_posterior = {label: cnt / k for label, cnt in counts.items()}

    # Aggregate cost from all runs
    total_real_cost = sum(h.get("real_cost_usd", 0.0) for h in headers)
    total_simulated_cost = sum(h.get("simulated_cost_usd", 0.0) for h in headers)

    # Use first header as template for metadata fields
    ref = headers[0]

    return {
        "schema_version": "audit.v1",
        "case_id": ref["case_id"],
        "run_id": f"sc_aggregate_k{k}",
        "model": ref.get("model", ""),
        "panel_config_name": ref.get("panel_config_name", ""),
        "started_at": ref.get("started_at", ""),
        "completed_at": headers[-1].get("completed_at", ""),
        "turns": [],
        "final_committed_diagnosis": winner_label,
        "final_posterior": final_posterior,
        "simulated_cost_usd": total_simulated_cost,
        "real_cost_usd": total_real_cost,
        "judge_score": None,
        "judge_rationale": None,
        # SC-specific provenance fields
        "sc_k": k,
        "sc_confidence": sc_confidence,
    }


def aggregate(
    run_dirs: list[Path],
    out_dir: Path,
    cluster_fn: Callable[[list[str]], dict[str, str]] | None = None,
) -> Path:
    """Aggregate k run dirs into a voted output dir readable by judge + metrics.

    Parameters
    ----------
    run_dirs:
        List of existing run directories, each containing *.audit.jsonl files.
    out_dir:
        Destination directory (created by this function).
    cluster_fn:
        Optional synonym-clustering function.  If None, a default LLM-backed
        clusterer is created (requires OPENROUTER_API_KEY).

    Returns
    -------
    Path
        The out_dir that was created.
    """
    if not run_dirs:
        raise ValueError("run_dirs must not be empty")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if cluster_fn is None:
        cluster_fn = _make_default_cluster_fn()

    all_cases = _load_headers([Path(d) for d in run_dirs])

    for case_id, headers in sorted(all_cases.items()):
        voted = _vote(headers, cluster_fn)
        out_path = out_dir / f"{case_id}.audit.jsonl"
        # Write header line only (turns=[]) — same shape judge_v2_run.py reads
        out_path.write_text(json.dumps(voted) + "\n")

    # Write a manifest so compute_v2_metrics.py can identify this as a run dir
    manifest = {
        "schema_version": "v2.run.v1",
        "arm": "sc_aggregate",
        "panel": "self_consistency_vote",
        "n_cases": len(all_cases),
        "started_at": datetime.now(timezone.utc).timestamp(),
        "finished_at": datetime.now(timezone.utc).timestamp(),
        "sc_k": len(run_dirs),
        "source_run_dirs": [str(d) for d in run_dirs],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return out_dir


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: aggregate_self_consistency.py OUT_DIR RUN0 RUN1 [RUN2 ...]",
            file=sys.stderr,
        )
        sys.exit(2)

    out_dir = Path(sys.argv[1])
    run_dirs = [Path(p) for p in sys.argv[2:]]

    for rd in run_dirs:
        if not rd.exists():
            print(f"ERROR: run dir not found: {rd}", file=sys.stderr)
            sys.exit(1)

    print(f"Aggregating {len(run_dirs)} run(s) -> {out_dir} ...")
    result = aggregate(run_dirs, out_dir)

    audits = list(result.glob("*.audit.jsonl"))
    print(f"Done. Wrote {len(audits)} voted audit files to {result}")


if __name__ == "__main__":
    main()
