"""Build a layered deterministic family release gate report.

The family gate is intentionally separate from the V1 release gate.  V1 keeps
its existing deterministic sample range and browser/debug evidence; this report
adds algorithm-family visibility over the same deterministic benchmark cases.
It does not call the LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_family_capabilities import (
    known_process_profiles,
    load_family_capabilities,
    validate_family_capabilities,
)
from scripts.check_v1_release_gate import build_v1_release_gate_report
from algolab.runtime.executor import canonical, execute_variant, run_verifier
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.verification.degradation import DEGRADATION_TYPES
from algolab.verification.process_validator import validate_process
from benchmark.cases import BenchmarkCase, benchmark_cases


PYTHON = "python3"
QUALITY_CHECKS = f"{PYTHON} scripts/run_quality_checks.py"


def build_family_release_gate_report(capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate_family_release_gate(capabilities or load_family_capabilities(), benchmark_cases())


def validate_family_release_gate(
    capabilities: dict[str, Any],
    cases: list[BenchmarkCase] | tuple[BenchmarkCase, ...],
) -> dict[str, Any]:
    capability_report = validate_family_capabilities(capabilities, cases)
    v1_report = build_v1_release_gate_report()
    cases_by_family = _cases_by_family(cases)
    rows = [
        _family_row(entry, cases_by_family.get(str(entry.get("label")), ()))
        for entry in capabilities.get("families") or []
    ]

    gate_errors = [
        error
        for row in rows
        for error in row["errors"]
    ]
    summary = _summary(rows)
    overall_ready = bool(capability_report.get("overall_ready")) and bool(v1_report.get("overall_ready")) and not gate_errors
    return {
        "schema_version": "family-release-gate-v1",
        "description": "Layered deterministic family release gate for AlgoLab benchmark families.",
        "overall_ready": overall_ready,
        "summary": summary,
        "commands": {
            "family_release_gate": f"{PYTHON} scripts/check_family_release_gate.py --output-dir output/release_gate",
            "v1_release_gate": f"{PYTHON} scripts/check_v1_release_gate.py --output-dir output/release_gate",
            "quality_checks": QUALITY_CHECKS,
        },
        "rules": {
            "v1_preserved": "This report embeds but does not alter the existing V1 release gate conclusion.",
            "strong_process_gate": "current_level=strong families fail if their process profile is fallback or uncovered.",
            "medium_basic_policy": "medium/basic families may use process_fallback or process_uncovered, but the report must show it explicitly.",
        },
        "v1_release_gate": {
            "schema_version": v1_report["schema_version"],
            "overall_ready": v1_report["overall_ready"],
            "checks": {
                name: check.get("status")
                for name, check in v1_report.get("checks", {}).items()
            },
        },
        "capability_registry": {
            "overall_ready": capability_report["overall_ready"],
            "errors": capability_report["errors"],
            "warnings": capability_report["warnings"],
        },
        "families": rows,
        "errors": [*capability_report["errors"], *gate_errors],
        "warnings": [*capability_report["warnings"], *[warning for row in rows for warning in row["warnings"]]],
    }


def _cases_by_family(cases: list[BenchmarkCase] | tuple[BenchmarkCase, ...]) -> dict[str, tuple[BenchmarkCase, ...]]:
    groups: dict[str, list[BenchmarkCase]] = defaultdict(list)
    for case in cases:
        groups[case.family].append(case)
    return {family: tuple(items) for family, items in groups.items()}


def _family_row(entry: dict[str, Any], cases: tuple[BenchmarkCase, ...]) -> dict[str, Any]:
    process_profile = str(entry.get("process_profile") or "")
    process_status = _process_status(process_profile)
    failure_type = _process_failure_type(process_profile, process_status)
    current_level = str(entry.get("current_level") or "")
    sample_count = sum(len(case.samples) for case in cases)
    case_count = len(cases)
    gate_layers = Counter(case.gate_layer for case in cases)
    gate_layer_samples = Counter()
    for case in cases:
        gate_layer_samples[case.gate_layer] += len(case.samples)
    subfamilies = sorted({case.subfamily_id for case in cases})
    errors: list[str] = []
    warnings: list[str] = []

    for case in cases:
        if case.family_id != entry.get("family_id"):
            errors.append(f"{case.id}: family_id {case.family_id} does not match registry {entry.get('family_id')}")
        if case.process_profile != process_profile:
            errors.append(f"{case.id}: process_profile {case.process_profile} does not match registry {process_profile}")
        if case.support_level != current_level:
            errors.append(f"{case.id}: support_level {case.support_level} does not match registry {current_level}")
        if case.gate_layer not in set(entry.get("gate_layers") or []):
            errors.append(f"{case.id}: gate_layer {case.gate_layer} is not declared by registry")

    fallback_cases = case_count if process_status == "fallback" else 0
    uncovered_cases = case_count if process_status == "uncovered" else 0
    fallback_samples = sample_count if process_status == "fallback" else 0
    uncovered_samples = sample_count if process_status == "uncovered" else 0
    family_core_degradation_cases = sum(
        1 for case in cases if process_status != "strong" and case.gate_layer in {"smoke", "family_core"}
    )
    family_core_degradation_samples = sum(
        len(case.samples) for case in cases if process_status != "strong" and case.gate_layer in {"smoke", "family_core"}
    )
    degradations = _row_degradations(
        failure_type=failure_type,
        process_status=process_status,
        case_count=case_count,
        sample_count=sample_count,
        reason=str(entry.get("coverage_rule") or entry.get("label") or ""),
    )

    if current_level == "strong" and process_status != "strong":
        errors.append(
            "strong family family_core cannot use "
            f"{failure_type}; process_profile={process_profile}"
        )
    if current_level in {"medium_plus", "medium", "basic"} and process_status != "strong":
        warnings.append(
            f"{entry.get('label')} uses {failure_type}; fallback boundaries must remain visible in reports."
        )
    if case_count == 0:
        warnings.append(f"{entry.get('label')} has no deterministic benchmark cases yet.")

    sample_results = _sample_results(cases)
    answer_passed_samples = sum(1 for item in sample_results if item["answer_ok"])
    process_passed_samples = sum(1 for item in sample_results if item["process_ok"])
    demo_ready_cases = _demo_ready_cases(cases)
    required_demo_cases = sum(1 for case in cases if case.demo_required)
    sample_errors = [
        f"{item['case_id']}[{item['sample_index']}]: {error}"
        for item in sample_results
        for error in item["errors"]
    ]
    errors.extend(sample_errors)

    status = "fail" if errors else "pass"
    return {
        "family_id": entry.get("family_id", ""),
        "label": entry.get("label", ""),
        "target_level": entry.get("target_level", ""),
        "current_level": current_level,
        "process_profile": process_profile,
        "process_status": process_status,
        "case_count": case_count,
        "sample_count": sample_count,
        "case_ids": [case.id for case in cases],
        "subfamilies": subfamilies,
        "gate_layers": dict(sorted(gate_layers.items())),
        "gate_layer_samples": dict(sorted(gate_layer_samples.items())),
        "answer": {
            "status": "pass" if answer_passed_samples == sample_count else "fail",
            "passed_samples": answer_passed_samples,
            "total_samples": sample_count,
            "pass_rate": _rate(answer_passed_samples, sample_count),
            "covered_by": "scripts.check_family_release_gate executes solve/trace/verify for deterministic samples",
        },
        "process": {
            "status": process_status,
            "passed_samples": process_passed_samples,
            "total_samples": sample_count,
            "pass_rate": _rate(process_passed_samples, sample_count),
            "failure_type": failure_type,
            "covered_by": "scripts.check_family_release_gate executes validate_process on deterministic traces",
        },
        "demo_readiness": {
            "status": "pass" if demo_ready_cases == required_demo_cases else "fail",
            "ready_cases": demo_ready_cases,
            "required_cases": required_demo_cases,
            "pass_rate": _rate(demo_ready_cases, required_demo_cases),
            "covered_by": "BenchmarkCase.demo_required + expected_layouts metadata",
        },
        "fallback": {
            "failure_type": failure_type,
            "process_fallback_cases": fallback_cases,
            "process_uncovered_cases": uncovered_cases,
            "process_fallback_samples": fallback_samples,
            "process_uncovered_samples": uncovered_samples,
            "family_core_degradation_cases": family_core_degradation_cases,
            "family_core_degradation_samples": family_core_degradation_samples,
            "fallback_boundaries": list(entry.get("fallback_boundaries") or []),
        },
        "degradations": degradations,
        "sample_failures": [item for item in sample_results if item["errors"]],
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }


def _process_status(process_profile: str) -> str:
    if process_profile == "uncovered":
        return "uncovered"
    shorthand_profiles = {
        "backtracking": "strong",
        "bfs": "strong",
        "dp": "strong",
        "geometry": "strong",
        "hash": "strong",
        "heap": "strong",
        "linked_list": "strong",
        "string": "strong",
        "tree": "strong",
    }
    return known_process_profiles().get(process_profile) or shorthand_profiles.get(process_profile, "unknown")


def _process_failure_type(process_profile: str, process_status: str) -> str:
    if process_status == "strong":
        return ""
    if process_profile == "uncovered" or process_status == "uncovered":
        return "process_uncovered"
    if process_status == "fallback":
        return "process_fallback"
    return "process_uncovered"


def _row_degradations(
    *,
    failure_type: str,
    process_status: str,
    case_count: int,
    sample_count: int,
    reason: str,
) -> list[dict[str, Any]]:
    if process_status == "strong" or failure_type not in {"process_fallback", "process_uncovered"}:
        return []
    return [
        {
            "type": failure_type,
            "source": "family_capabilities",
            "reason": reason or f"process_status={process_status}",
            "case_count": case_count,
            "sample_count": sample_count,
        }
    ]


def _sample_results(cases: tuple[BenchmarkCase, ...]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in cases:
        for index, sample in enumerate(case.samples):
            result = _check_sample(case, index, sample.input_data, sample.expected)
            results.append(result)
    return results


def _check_sample(case: BenchmarkCase, sample_index: int, input_data: dict[str, Any], expected: Any) -> dict[str, Any]:
    errors: list[str] = []
    answer_ok = False
    process_ok = False
    try:
        variant = SolutionVariant(
            id=case.id,
            name=case.variant_name,
            strategy=case.strategy,
            time_complexity=case.time_complexity,
            space_complexity=case.space_complexity,
            code=case.code,
            tracker_code=case.tracker_code,
        )
        executed = execute_variant(variant, input_data)
        if canonical(executed.result) != canonical(expected):
            errors.append(f"answer_mismatch: result {executed.result!r} != expected {expected!r}")
        if case.verifier_code.strip():
            verifier_result = run_verifier(case.verifier_code, input_data)
            if canonical(executed.result) != canonical(verifier_result):
                errors.append(f"answer_mismatch: verifier {verifier_result!r} != result {executed.result!r}")
        answer_ok = not any(error.startswith("answer_mismatch") for error in errors)
        if executed.trace is None:
            errors.append("schema_error: trace is missing")
        else:
            process_errors, _warnings = validate_process(executed.trace)
            if process_errors:
                errors.extend(process_errors)
            process_ok = not process_errors
    except Exception as exc:
        errors.append(f"execution_error: {type(exc).__name__}: {exc}")
    return {
        "case_id": case.id,
        "sample_index": sample_index,
        "answer_ok": answer_ok,
        "process_ok": process_ok,
        "errors": errors,
    }


def _demo_ready_cases(cases: tuple[BenchmarkCase, ...]) -> int:
    return sum(1 for case in cases if case.demo_required and bool(case.expected_layouts))


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    case_count = sum(row["case_count"] for row in rows)
    sample_count = sum(row["sample_count"] for row in rows)
    answer_passed_samples = sum(row["answer"]["passed_samples"] for row in rows)
    process_passed_samples = sum(row["process"]["passed_samples"] for row in rows)
    demo_ready_cases = sum(row["demo_readiness"]["ready_cases"] for row in rows)
    demo_required_cases = sum(row["demo_readiness"]["required_cases"] for row in rows)
    fallback_cases = sum(row["fallback"]["process_fallback_cases"] for row in rows)
    uncovered_cases = sum(row["fallback"]["process_uncovered_cases"] for row in rows)
    gate_layers: Counter[str] = Counter()
    gate_layer_samples: Counter[str] = Counter()
    for row in rows:
        gate_layers.update(row.get("gate_layers") or {})
        gate_layer_samples.update(row.get("gate_layer_samples") or {})
    return {
        "family_count": len(rows),
        "case_count": case_count,
        "sample_count": sample_count,
        "gate_layers": dict(sorted(gate_layers.items())),
        "gate_layer_samples": dict(sorted(gate_layer_samples.items())),
        "answer_passed_samples": answer_passed_samples,
        "answer_pass_rate": _rate(answer_passed_samples, sample_count),
        "process_passed_samples": process_passed_samples,
        "process_pass_rate": _rate(process_passed_samples, sample_count),
        "demo_ready_cases": demo_ready_cases,
        "demo_required_cases": demo_required_cases,
        "demo_readiness_pass_rate": _rate(demo_ready_cases, demo_required_cases),
        "process_fallback_cases": fallback_cases,
        "process_uncovered_cases": uncovered_cases,
        "degradation_summary": _degradation_summary(rows),
        "strong_family_count": sum(1 for row in rows if row["current_level"] == "strong"),
        "degraded_family_count": sum(1 for row in rows if row["process_status"] != "strong"),
    }


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _degradation_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary = {
        degradation_type: {"cases": 0, "samples": 0, "reasons": []}
        for degradation_type in DEGRADATION_TYPES
    }
    for row in rows:
        for entry in row.get("degradations") or []:
            degradation_type = entry.get("type")
            if degradation_type not in summary:
                continue
            summary[degradation_type]["cases"] += int(entry.get("case_count") or 0)
            summary[degradation_type]["samples"] += int(entry.get("sample_count") or 0)
            reason = str(entry.get("reason") or "")
            if reason and reason not in summary[degradation_type]["reasons"]:
                summary[degradation_type]["reasons"].append(reason)
    return summary


def write_family_release_gate_report(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_family_release_gate_report()
    json_path = output_dir / "family_release_gate.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "family_release_gate.md").write_text(render_markdown(report), encoding="utf-8")
    return json_path


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Family Release Gate",
        "",
        f"- Overall ready: `{report['overall_ready']}`",
        f"- V1 release gate ready: `{report['v1_release_gate']['overall_ready']}`",
        f"- Cases: `{report['summary']['case_count']}`",
        f"- Samples: `{report['summary']['sample_count']}`",
        f"- Gate layers: `{json.dumps(report['summary'].get('gate_layers', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- Gate layer samples: `{json.dumps(report['summary'].get('gate_layer_samples', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- Process fallback cases: `{report['summary']['process_fallback_cases']}`",
        f"- Process uncovered cases: `{report['summary']['process_uncovered_cases']}`",
        f"- Degradation summary: `{json.dumps(report['summary'].get('degradation_summary', {}), ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Families",
        "",
        "| Family | Level | Cases | Samples | Answer Pass | Process Pass | Demo Readiness | Fallback / Uncovered | Status |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in sorted(report["families"], key=lambda item: item["label"]):
        answer = _fraction(row["answer"]["passed_samples"], row["answer"]["total_samples"])
        process = _fraction(row["process"]["passed_samples"], row["process"]["total_samples"])
        demo = _fraction(row["demo_readiness"]["ready_cases"], row["demo_readiness"]["required_cases"])
        fallback = (
            f"{row['fallback']['failure_type'] or 'none'}: "
            f"{row['fallback']['process_fallback_cases']} / {row['fallback']['process_uncovered_cases']}"
        )
        lines.append(
            "| {label} | {level} | {cases} | {samples} | {answer} | {process} | {demo} | {fallback} | {status} |".format(
                label=row["label"],
                level=row["current_level"],
                cases=row["case_count"],
                samples=row["sample_count"],
                answer=answer,
                process=process,
                demo=demo,
                fallback=fallback,
                status=row["status"],
            )
        )
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"


def _fraction(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "N/A"
    return f"{numerator}/{denominator}"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 AlgoLab 算法族分层发布门禁报告")
    parser.add_argument("--output-dir", type=Path, default=Path("output/release_gate"), help="输出目录")
    args = parser.parse_args()
    path = write_family_release_gate_report(args.output_dir)
    report = json.loads(path.read_text(encoding="utf-8"))
    print(path)
    return 0 if report.get("overall_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
