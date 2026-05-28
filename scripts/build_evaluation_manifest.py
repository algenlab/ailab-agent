"""Build the research evaluation dataset manifest.

The manifest is deterministic and does not call the LLM. It records the task
sets used by benchmark and dashboard evaluation so Phase 10 metrics and reports
can share the same source of truth.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_demo_dashboard import CUSTOM_SUBSET_SUM_ID, selected_demo_definitions
from tests.benchmark_cases import BenchmarkCase, benchmark_cases


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    title: str
    problem: str
    input_contract: str
    source: str
    suite: str
    family: str
    family_id: str
    subfamily_id: str
    gate_layer: str
    support_level: str
    process_profile: str
    oracle_type: str
    oracle_risk: str
    oracle_notes: str
    oracle_reference: str
    demo_required: bool
    strata: list[str]
    sample_count: int
    expected_layouts: list[str]
    visual_forms: list[str]
    samples: list[dict[str, Any]]
    artifact_paths: dict[str, str]
    has_verifier: bool
    has_contract_seed: bool
    is_ml_demo: bool = False


ML_DEMO_CASES: tuple[EvaluationCase, ...] = (
    EvaluationCase(
        id="linear_regression_single_step",
        title="线性回归单步梯度",
        problem="线性回归单步梯度下降演示。",
        input_contract="输入一组二维样本、当前参数和学习率。",
        source="phase9_ml_fixture",
        suite="ml_demo",
        family="ML / regression",
        family_id="ml_regression",
        subfamily_id="linear_regression_single_step",
        gate_layer="smoke",
        support_level="basic",
        process_profile="uncovered",
        oracle_type="property",
        oracle_risk="none",
        oracle_notes="ML fixture uses deterministic expected property evidence.",
        oracle_reference="phase9_ml_fixture",
        demo_required=True,
        strata=["ML demo 集"],
        sample_count=1,
        expected_layouts=["ml", "matrix", "loss_curve"],
        visual_forms=["ml", "matrix", "loss_curve"],
        samples=[
            {
                "index": 0,
                "input_data": {"fixture": "linear_regression_single_step"},
                "expected": {"loss_decreases": True},
                "artifact_paths": {
                    "json": "output/evaluation/ml_demo/linear_regression_single_step.json",
                    "html": "output/evaluation/ml_demo/linear_regression_single_step.html",
                },
            }
        ],
        artifact_paths={
            "artifact_json": "output/evaluation/ml_demo/linear_regression_single_step.json",
            "html": "output/evaluation/ml_demo/linear_regression_single_step.html",
        },
        has_verifier=True,
        has_contract_seed=False,
        is_ml_demo=True,
    ),
    EvaluationCase(
        id="logistic_regression_boundary",
        title="逻辑回归决策边界",
        problem="逻辑回归决策边界教学演示。",
        input_contract="输入二维分类样本、当前参数和阈值。",
        source="phase9_ml_fixture",
        suite="ml_demo",
        family="ML / classification",
        family_id="ml_classification",
        subfamily_id="logistic_regression_boundary",
        gate_layer="smoke",
        support_level="basic",
        process_profile="uncovered",
        oracle_type="property",
        oracle_risk="none",
        oracle_notes="ML fixture uses deterministic expected property evidence.",
        oracle_reference="phase9_ml_fixture",
        demo_required=True,
        strata=["ML demo 集"],
        sample_count=1,
        expected_layouts=["ml", "computational_graph", "decision_boundary"],
        visual_forms=["ml", "computational_graph", "decision_boundary"],
        samples=[
            {
                "index": 0,
                "input_data": {"fixture": "logistic_regression_boundary"},
                "expected": {"boundary_visible": True},
                "artifact_paths": {
                    "json": "output/evaluation/ml_demo/logistic_regression_boundary.json",
                    "html": "output/evaluation/ml_demo/logistic_regression_boundary.html",
                },
            }
        ],
        artifact_paths={
            "artifact_json": "output/evaluation/ml_demo/logistic_regression_boundary.json",
            "html": "output/evaluation/ml_demo/logistic_regression_boundary.html",
        },
        has_verifier=True,
        has_contract_seed=False,
        is_ml_demo=True,
    ),
)


def build_manifest() -> dict[str, Any]:
    benchmark = benchmark_cases()
    default_demo_ids = {definition.id for definition in selected_demo_definitions()}
    cases = [
        case
        for benchmark_case in benchmark
        for case in [_evaluation_case_from_benchmark(benchmark_case, default_demo_ids)]
    ]
    cases.extend(ML_DEMO_CASES)
    summary = _summary(cases)
    return {
        "schema_version": "evaluation-manifest-v1",
        "description": "AlgoLab deterministic research evaluation dataset manifest.",
        "summary": summary,
        "strata": _strata_summary(cases),
        "cases": [asdict(case) for case in cases],
    }


def _evaluation_case_from_benchmark(case: BenchmarkCase, default_demo_ids: set[str]) -> EvaluationCase:
    suite = "default_dashboard" if case.id in default_demo_ids else "benchmark"
    return EvaluationCase(
        id=case.id,
        title=case.title,
        problem=case.problem,
        input_contract=case.input_contract,
        source="tests.benchmark_cases",
        suite=suite,
        family=case.family,
        family_id=case.family_id,
        subfamily_id=case.subfamily_id,
        gate_layer=case.gate_layer,
        support_level=case.support_level,
        process_profile=case.process_profile,
        oracle_type=case.oracle_type,
        oracle_risk=case.oracle_risk,
        oracle_notes=case.oracle_notes,
        oracle_reference=case.oracle_reference,
        demo_required=case.demo_required,
        strata=_strata_for_case(case),
        sample_count=len(case.samples),
        expected_layouts=list(case.expected_layouts),
        visual_forms=list(case.expected_layouts),
        samples=_samples_for_case(case),
        artifact_paths=_artifact_paths_for_case(case.id, suite),
        has_verifier=bool(case.verifier_code.strip()),
        has_contract_seed=case.id in _contract_seed_case_ids() or case.id in default_demo_ids,
    )


def _strata_for_case(case: BenchmarkCase) -> list[str]:
    family = case.family.lower()
    layouts = set(case.expected_layouts)
    strata: list[str] = []
    if case.problem.startswith("LeetCode"):
        strata.append("LeetCode 基础算法集")
    if layouts & {"stack", "queue", "map", "heap", "trie", "union_find"}:
        strata.append("数据结构算法集")
    if "dp" in family or "graph" in family or "bfs" in family or "stack" in family or "tree" in family or "geometry" in layouts:
        strata.append("DP / graph / stack / tree / geometry 分层")
    if not strata:
        strata.append("LeetCode 基础算法集")
    return strata


def _contract_seed_case_ids() -> set[str]:
    return {"house_robber", "binary_search", "unique_paths", "graph_bfs", "two_sum"}


def _artifact_paths_for_case(case_id: str, suite: str) -> dict[str, str]:
    if suite == "default_dashboard":
        base = f"output/dashboard/demos/{case_id}"
        return {
            "artifact_json": f"{base}/artifact.json",
            "validation_report_json": f"{base}/validation_report.json",
            "repair_log_json": f"{base}/repair_log.json",
            "html": f"{base}/stable.html",
        }
    stem = f"output/llm_benchmark/llm_{case_id}_0"
    return {
        "artifact_json": f"{stem}.json",
        "html": f"{stem}.html",
    }


def _sample_artifact_paths(case_id: str, sample_index: int) -> dict[str, str]:
    stem = f"output/llm_benchmark/llm_{case_id}_{sample_index}"
    return {
        "json": f"{stem}.json",
        "html": f"{stem}.html",
    }


def _samples_for_case(case: BenchmarkCase) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "artifact_paths": _sample_artifact_paths(case.id, index),
        }
        for index, sample in enumerate(case.samples)
    ]


def _summary(cases: list[EvaluationCase]) -> dict[str, Any]:
    return {
        "case_count": len(cases),
        "benchmark_case_count": sum(1 for case in cases if case.source == "tests.benchmark_cases"),
        "ml_demo_count": sum(1 for case in cases if case.is_ml_demo),
        "sample_count": sum(case.sample_count for case in cases),
        "families": sorted({case.family for case in cases}),
        "families_by_id": dict(sorted(Counter(case.family_id for case in cases).items())),
        "subfamilies": dict(sorted(Counter(case.subfamily_id for case in cases).items())),
        "gate_layers": dict(sorted(Counter(case.gate_layer for case in cases).items())),
        "support_levels": dict(sorted(Counter(case.support_level for case in cases).items())),
        "process_profiles": dict(sorted(Counter(case.process_profile for case in cases).items())),
        "oracle_types": dict(sorted(Counter(case.oracle_type for case in cases).items())),
        "oracle_risks": dict(sorted(Counter(case.oracle_risk for case in cases).items())),
        "demo_required_count": sum(1 for case in cases if case.demo_required),
        "suites": dict(sorted(Counter(case.suite for case in cases).items())),
    }


def _strata_summary(cases: list[EvaluationCase]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for case in cases:
        for stratum in case.strata:
            item = result.setdefault(stratum, {"case_count": 0, "sample_count": 0, "case_ids": []})
            item["case_count"] += 1
            item["sample_count"] += case.sample_count
            item["case_ids"].append(case.id)
    return dict(sorted(result.items()))


def write_manifest(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    json_path = output_dir / "evaluation_manifest.json"
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = output_dir / "evaluation_cases.csv"
    _write_cases_csv(csv_path, manifest["cases"])
    _write_samples_csv(output_dir / "evaluation_samples.csv", manifest["cases"])
    return json_path


def _write_cases_csv(path: Path, cases: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "title",
        "problem",
        "input_contract",
        "source",
        "suite",
        "family",
        "family_id",
        "subfamily_id",
        "gate_layer",
        "support_level",
        "process_profile",
        "oracle_type",
        "oracle_risk",
        "oracle_notes",
        "oracle_reference",
        "demo_required",
        "strata",
        "sample_count",
        "expected_layouts",
        "visual_forms",
        "artifact_json",
        "html",
        "has_verifier",
        "has_contract_seed",
        "is_ml_demo",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            row = dict(case)
            row["strata"] = ";".join(row["strata"])
            row["expected_layouts"] = ";".join(row["expected_layouts"])
            row["visual_forms"] = ";".join(row["visual_forms"])
            row["artifact_json"] = row["artifact_paths"].get("artifact_json", "")
            row["html"] = row["artifact_paths"].get("html", "")
            row.pop("samples", None)
            row.pop("artifact_paths", None)
            writer.writerow(row)


def _write_samples_csv(path: Path, cases: list[dict[str, Any]]) -> None:
    fields = ["case_id", "sample_index", "input_data", "expected", "artifact_json", "html"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            for sample in case.get("samples", []):
                paths = sample.get("artifact_paths") or {}
                writer.writerow(
                    {
                        "case_id": case["id"],
                        "sample_index": sample.get("index", ""),
                        "input_data": json.dumps(sample.get("input_data"), ensure_ascii=False, sort_keys=True),
                        "expected": json.dumps(sample.get("expected"), ensure_ascii=False, sort_keys=True),
                        "artifact_json": paths.get("json", ""),
                        "html": paths.get("html", ""),
                    }
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 AlgoLab 科研评估数据集 manifest")
    parser.add_argument("--output-dir", type=Path, default=Path("output/evaluation"), help="输出目录")
    args = parser.parse_args()
    path = write_manifest(args.output_dir)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
