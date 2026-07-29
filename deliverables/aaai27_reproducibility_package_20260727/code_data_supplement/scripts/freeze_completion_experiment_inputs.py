"""Freeze hashes and coverage metadata for the completion experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def freeze_inputs(paths: dict[str, Path]) -> dict[str, Any]:
    inputs = {}
    for name, raw_path in sorted(paths.items()):
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        inputs[name] = {
            "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else 0,
            "sha256": _sha256(path) if path.exists() else "",
        }
    return {
        "kind": "completion_experiment_frozen_inputs",
        "created_at": datetime.now().astimezone().isoformat(),
        "inputs": inputs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources = {
        "benchmark": Path("benchmark/algo_learn_env_benchmark.json"),
        "stage1_primary": Path("output/experiments/algotutorgen_full_200_20260706/algolab_full/llm_benchmark_report.json"),
        "stage1_final": Path("output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"),
        "direct": Path("output/experiments/algotutorgen_full_200_20260706/direct_html_expected_visible/llm_benchmark_report.json"),
        "machine": Path("output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine/interaction_semantic_eval_report.json"),
        "external_review": Path("output/experiments/algotutorgen_full_200_20260706/external_eval_methods/external_eval_methods_report.json"),
        "stage2": Path("output/experiments/algotutorgen_full_200_20260706/stage2_eval/stage2_visual_eval_report.json"),
        "direct_visual": Path("output/experiments/algotutorgen_full_200_20260706/direct_visual_eval/visual_baseline_eval_report.json"),
    }
    report = freeze_inputs(sources)
    benchmark = json.loads((ROOT / sources["benchmark"]).read_text(encoding="utf-8"))
    report["coverage"] = {
        "cases": len(benchmark.get("cases") or []),
        "samples": sum(len(case.get("samples") or []) for case in benchmark.get("cases") or []),
        "families": len({case.get("family_id") for case in benchmark.get("cases") or []}),
    }
    missing = [name for name, item in report["inputs"].items() if not item["exists"]]
    if missing:
        raise SystemExit(f"missing required inputs: {missing}")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "coverage": report["coverage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
