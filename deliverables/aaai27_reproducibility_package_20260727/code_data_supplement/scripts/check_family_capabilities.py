"""Validate the deterministic benchmark family capability registry."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.verification.process_validator import process_validation_registry
from benchmark.cases import BenchmarkCase, benchmark_cases


PYTHON = "python3"
REGISTRY_PATH = ROOT / "benchmark" / "family_capabilities.json"
VALID_LEVELS = {"strong", "medium_plus", "medium", "basic", "planned"}
VALID_PROCESS_STATUSES = {"strong", "fallback", "uncovered"}
VALID_GATE_LAYERS = {"smoke", "family_core", "expansion", "llm_eval"}
REQUIRED_FIELDS = {
    "family_id",
    "label",
    "target_level",
    "current_level",
    "core_subfamilies",
    "visual_primitives",
    "process_profile",
    "gate_layers",
    "benchmark_target",
    "fallback_boundaries",
}


def load_family_capabilities(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def known_process_profiles() -> dict[str, str]:
    profiles = {profile.family: profile.status for profile in process_validation_registry()}
    profiles["uncovered"] = "uncovered"
    return profiles


def build_family_capabilities_report(capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate_family_capabilities(capabilities or load_family_capabilities(), benchmark_cases())


def validate_family_capabilities(
    capabilities: dict[str, Any],
    cases: list[BenchmarkCase] | tuple[BenchmarkCase, ...],
) -> dict[str, Any]:
    families = list(capabilities.get("families") or [])
    benchmark_family_counts = Counter(case.family for case in cases)
    benchmark_sample_counts = Counter({family: 0 for family in benchmark_family_counts})
    for case in cases:
        benchmark_sample_counts[case.family] += len(case.samples)

    labels = [entry.get("label") for entry in families]
    labels_set = {label for label in labels if isinstance(label, str)}
    family_ids = [entry.get("family_id") for entry in families]
    process_profiles = known_process_profiles()

    errors: list[str] = []
    warnings: list[str] = []
    missing_benchmark_families = sorted(set(benchmark_family_counts) - labels_set)
    extra_registered_families = sorted(labels_set - set(benchmark_family_counts))
    duplicate_labels = sorted(label for label, count in Counter(labels).items() if label and count > 1)
    duplicate_family_ids = sorted(family_id for family_id, count in Counter(family_ids).items() if family_id and count > 1)
    unknown_process_profiles: list[str] = []
    invalid_entries: list[dict[str, Any]] = []

    if capabilities.get("schema_version") != "family-capabilities-v1":
        errors.append("schema_version must be family-capabilities-v1")
    if not families:
        errors.append("families must not be empty")
    if missing_benchmark_families:
        errors.append("benchmark families missing from registry: " + ", ".join(missing_benchmark_families))
    if duplicate_labels:
        errors.append("duplicate family labels: " + ", ".join(duplicate_labels))
    if duplicate_family_ids:
        errors.append("duplicate family ids: " + ", ".join(duplicate_family_ids))
    if extra_registered_families:
        warnings.append("registered families not yet used by deterministic benchmark: " + ", ".join(extra_registered_families))

    entries: list[dict[str, Any]] = []
    for entry in families:
        normalized, entry_errors = _validate_entry(entry, process_profiles, benchmark_family_counts, benchmark_sample_counts)
        if normalized["process_status"] == "unknown" and normalized["process_profile"] not in unknown_process_profiles:
            unknown_process_profiles.append(normalized["process_profile"])
        if entry_errors:
            invalid_entries.append({"label": normalized["label"], "errors": entry_errors})
            errors.extend(f"{normalized['label']}: {error}" for error in entry_errors)
        entries.append(normalized)

    if unknown_process_profiles:
        errors.append("unknown process profiles: " + ", ".join(sorted(unknown_process_profiles)))

    return {
        "schema_version": "family-capabilities-report-v1",
        "registry_path": str(REGISTRY_PATH.relative_to(ROOT)),
        "overall_ready": not errors,
        "benchmark_case_count": len(cases),
        "benchmark_sample_count": sum(len(case.samples) for case in cases),
        "benchmark_family_count": len(benchmark_family_counts),
        "registered_family_count": len(families),
        "known_process_profiles": sorted(process_profiles),
        "missing_benchmark_families": missing_benchmark_families,
        "extra_registered_families": extra_registered_families,
        "unknown_process_profiles": sorted(unknown_process_profiles),
        "duplicate_family_labels": duplicate_labels,
        "duplicate_family_ids": duplicate_family_ids,
        "invalid_entries": invalid_entries,
        "families": entries,
        "errors": errors,
        "warnings": warnings,
        "commands": {
            "family_capabilities": f"{PYTHON} scripts/check_family_capabilities.py",
            "benchmark_regression": f"{PYTHON} -m tests.benchmark_regression",
        },
    }


def _validate_entry(
    entry: dict[str, Any],
    process_profiles: dict[str, str],
    benchmark_family_counts: Counter[str],
    benchmark_sample_counts: Counter[str],
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    missing_fields = sorted(REQUIRED_FIELDS - set(entry))
    if missing_fields:
        errors.append("missing fields: " + ", ".join(missing_fields))

    label = entry.get("label", "")
    family_id = entry.get("family_id", "")
    process_profile = entry.get("process_profile", "")
    process_status = (
        "uncovered"
        if process_profile == "uncovered"
        else process_profiles.get(family_id) or process_profiles.get(process_profile, "unknown")
    )
    benchmark_target = entry.get("benchmark_target") if isinstance(entry.get("benchmark_target"), dict) else {}
    min_cases = benchmark_target.get("min_cases")
    min_samples = benchmark_target.get("min_samples")

    if not isinstance(entry.get("family_id"), str) or not entry.get("family_id"):
        errors.append("family_id must be a non-empty string")
    if not isinstance(label, str) or not label:
        errors.append("label must be a non-empty string")
    if entry.get("target_level") not in VALID_LEVELS:
        errors.append("target_level must be one of " + ", ".join(sorted(VALID_LEVELS)))
    if entry.get("current_level") not in VALID_LEVELS:
        errors.append("current_level must be one of " + ", ".join(sorted(VALID_LEVELS)))
    if not isinstance(entry.get("core_subfamilies"), list) or not entry.get("core_subfamilies"):
        errors.append("core_subfamilies must be a non-empty list")
    if not isinstance(entry.get("visual_primitives"), list) or not entry.get("visual_primitives"):
        errors.append("visual_primitives must be a non-empty list")
    if family_id not in process_profiles and process_profile not in process_profiles:
        errors.append(f"process_profile {process_profile!r} is not registered")
    if process_status not in VALID_PROCESS_STATUSES:
        errors.append(f"process_status {process_status!r} is invalid")
    if not isinstance(entry.get("gate_layers"), list) or not entry.get("gate_layers"):
        errors.append("gate_layers must be a non-empty list")
    else:
        unknown_layers = sorted(set(entry["gate_layers"]) - VALID_GATE_LAYERS)
        if unknown_layers:
            errors.append("unknown gate_layers: " + ", ".join(unknown_layers))
    if not isinstance(benchmark_target, dict):
        errors.append("benchmark_target must be an object")
    if not isinstance(min_cases, int) or min_cases < 1:
        errors.append("benchmark_target.min_cases must be a positive integer")
    if not isinstance(min_samples, int) or min_samples < 1:
        errors.append("benchmark_target.min_samples must be a positive integer")
    if process_status != "strong" and not entry.get("fallback_boundaries"):
        errors.append("fallback_boundaries must explain every non-strong process profile")
    if label in benchmark_family_counts and isinstance(min_cases, int) and benchmark_family_counts[label] < min_cases:
        errors.append(f"benchmark case count {benchmark_family_counts[label]} is below target {min_cases}")
    if label in benchmark_sample_counts and isinstance(min_samples, int) and benchmark_sample_counts[label] < min_samples:
        errors.append(f"benchmark sample count {benchmark_sample_counts[label]} is below target {min_samples}")

    normalized = dict(entry)
    normalized["process_status"] = process_status
    normalized["benchmark_cases"] = benchmark_family_counts.get(label, 0)
    normalized["benchmark_samples"] = benchmark_sample_counts.get(label, 0)
    return normalized, errors


def write_family_capabilities_report(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_family_capabilities_report()
    json_path = output_dir / "family_capabilities.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "family_capabilities.md").write_text(render_markdown(report), encoding="utf-8")
    return json_path


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Family Capabilities",
        "",
        f"- Overall ready: `{report['overall_ready']}`",
        f"- Benchmark families: `{report['benchmark_family_count']}`",
        f"- Registered families: `{report['registered_family_count']}`",
        "",
        "## Families",
        "",
        "| Family | Current Level | Process Profile | Process Status | Cases | Samples |",
        "|---|---|---|---|---:|---:|",
    ]
    for entry in sorted(report["families"], key=lambda item: item["label"]):
        lines.append(
            "| {label} | {current_level} | {process_profile} | {process_status} | {cases} | {samples} |".format(
                label=entry["label"],
                current_level=entry["current_level"],
                process_profile=entry["process_profile"],
                process_status=entry["process_status"],
                cases=entry["benchmark_cases"],
                samples=entry["benchmark_samples"],
            )
        )
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 AlgoLab 算法族能力注册表")
    parser.add_argument("--output-dir", type=Path, default=Path("output/release_gate"), help="输出目录")
    args = parser.parse_args()
    path = write_family_capabilities_report(args.output_dir)
    report = json.loads(path.read_text(encoding="utf-8"))
    print(path)
    return 0 if report.get("overall_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
