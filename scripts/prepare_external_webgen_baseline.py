#!/usr/bin/env python3
"""Freeze one sample per benchmark case and prepare WebGen-Agent inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmark" / "algo_learn_env_benchmark.json"
DEFAULT_MANIFEST = ROOT / "benchmark" / "external_baseline_all200_sample0.json"
DEFAULT_JSONL = ROOT / "benchmark" / "external_baseline_all200_sample0_webgen.jsonl"
DEFAULT_SMOKE_JSONL = ROOT / "benchmark" / "external_baseline_webgen_smoke2.jsonl"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def make_instruction(case: dict[str, Any], sample: dict[str, Any]) -> str:
    tasks = case.get("interaction_tasks", [])
    task_lines = []
    for index, task in enumerate(tasks, start=1):
        task_lines.append(f"{index}. {task.get('prompt', '').strip()}")
    tasks_text = "\n".join(task_lines) or "Create at least one prediction checkpoint."

    return f"""Build a polished, fully functional interactive educational webpage for the following algorithm problem.

Title: {case.get('title') or case['id']}
Algorithm family: {case.get('family', '')}
Problem:
{case.get('problem', '')}

Concrete input (JSON):
{json.dumps(sample['input_data'], ensure_ascii=False, indent=2)}

Expected final answer (JSON):
{json.dumps(sample['expected'], ensure_ascii=False)}

Reference strategy:
{case.get('strategy', '')}

Learning objectives:
{json.dumps(case.get('learning_objectives', []), ensure_ascii=False, indent=2)}

Suggested learner questions:
{tasks_text}

Functional requirements:
- Clearly display the concrete input and the final answer.
- Provide a meaningful step-by-step visualization of the algorithm state with working navigation controls.
- Include at least one learner prediction/checkpoint interaction.
- Provide distinct, visible feedback for both correct and incorrect answers.
- Include a working hint action and a working show-answer action.
- Keep a visible learning/activity log that updates after learner actions.
- Learner interactions must not silently alter the original problem input or expected final answer.
- All primary functionality must work locally without accounts, remote data, or backend services.
- Avoid runtime dependencies on external fonts, images, CDNs, or network APIs. Package dependencies installed during the build are allowed.
- Make the page responsive and usable at 1024x768 and mobile widths.

Use your native framework and workflow. Do not assume any private DOM schema, selector names, SemanticTrace, or SceneGraph contract."""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--smoke-jsonl", type=Path, default=DEFAULT_SMOKE_JSONL)
    args = parser.parse_args()

    raw = args.benchmark.read_bytes()
    benchmark = json.loads(raw)
    selected = benchmark["cases"]
    if len(selected) != 200:
        raise ValueError(f"Expected exactly 200 benchmark cases, found {len(selected)}")
    ids = [case["id"] for case in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("benchmark case IDs must be unique")

    records = []
    webgen_records = []
    for index, case in enumerate(selected):
        samples = case.get("samples", [])
        if not samples or samples[0].get("index") != 0:
            raise ValueError(f"{case['id']} has no deterministic sample 0")
        sample = samples[0]
        instruction = make_instruction(case, sample)
        record = {
            "case_id": case["id"],
            "algorithm_id": case.get("algorithm_id", case["id"]),
            "title": case.get("title", case["id"]),
            "family": case.get("family", ""),
            "family_id": case.get("family_id", ""),
            "subfamily_id": case.get("subfamily_id", ""),
            "gate_layer": case["gate_layer"],
            "sample_index": 0,
            "input_data": sample["input_data"],
            "expected": sample["expected"],
            "shard_id": index % 8,
            "instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
        }
        records.append(record)
        webgen_records.append({"id": case["id"], "instruction": instruction})

    manifest = {
        "schema_version": "external-baseline-subset-v1",
        "benchmark_path": str(args.benchmark.relative_to(ROOT)),
        "benchmark_sha256": hashlib.sha256(raw).hexdigest(),
        "selection_rule": "Preserve all 200 benchmark cases in source order; use samples[0] where index == 0 for each case.",
        "evaluation_scope": "Full case-level benchmark coverage with one deterministic sample per case (200 of 646 samples).",
        "concurrency": 8,
        "case_count": len(records),
        "shard_sizes": [sum(r["shard_id"] == shard for r in records) for shard in range(8)],
        "cases": records,
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with args.jsonl.open("w", encoding="utf-8") as handle:
        for record in webgen_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    smoke_ids = {"binary_search", "unique_paths"}
    smoke_records = [record for record in webgen_records if record["id"] in smoke_ids]
    if len(smoke_records) != 2:
        raise ValueError(f"Expected two smoke cases, found {len(smoke_records)}")
    with args.smoke_jsonl.open("w", encoding="utf-8") as handle:
        for record in smoke_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} cases to {args.manifest}")
    print(f"Wrote WebGen-Agent input to {args.jsonl}")
    print(f"Wrote smoke input to {args.smoke_jsonl}")
    print(f"Shard sizes: {manifest['shard_sizes']}")


if __name__ == "__main__":
    main()
