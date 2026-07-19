"""Validate family-core boundary coverage registry.

The registry is metadata only: it records which deterministic benchmark samples
or documented exceptions cover required boundary categories.  It does not call
the LLM and does not alter V1 release gate execution.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.cases import BenchmarkCase, benchmark_cases


PYTHON = "/ssd1/liaokunpeng/agent-py310-cu/bin/python3"
REGISTRY_PATH = ROOT / "benchmark" / "boundary_cases.json"
BOUNDARY_CATEGORIES = (
    "empty",
    "single",
    "duplicate",
    "zero_or_negative",
    "extreme",
    "no_solution",
    "multiple_solutions",
)
VALID_CATEGORIES = set(BOUNDARY_CATEGORIES)
REQUIRED_FIELDS = {"case_id", "coverage", "not_applicable"}


def load_boundary_cases(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_boundary_case_report(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate_boundary_cases(registry or load_boundary_cases(), benchmark_cases())


def validate_boundary_cases(
    registry: dict[str, Any],
    cases: list[BenchmarkCase] | tuple[BenchmarkCase, ...],
) -> dict[str, Any]:
    family_core_cases = [case for case in cases if case.gate_layer == "family_core"]
    family_core_ids = {case.id for case in family_core_cases}
    cases_by_id = {case.id: case for case in family_core_cases}
    entries = list(registry.get("cases") or [])
    entries_by_case = {
        str(entry.get("case_id")): entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("case_id")
    }

    errors: list[str] = []
    warnings: list[str] = []
    if registry.get("schema_version") != "boundary-cases-v1":
        errors.append("schema_version must be boundary-cases-v1")
    if sorted(registry.get("categories") or []) != sorted(BOUNDARY_CATEGORIES):
        errors.append("categories must match required boundary categories")
    if not entries:
        errors.append("cases must not be empty")

    duplicate_case_ids = sorted(case_id for case_id, count in Counter(str(entry.get("case_id")) for entry in entries).items() if case_id and count > 1)
    if duplicate_case_ids:
        errors.append("duplicate boundary case entries: " + ", ".join(duplicate_case_ids))

    missing_entry_ids = sorted(family_core_ids - set(entries_by_case))
    extra_entry_ids = sorted(set(entries_by_case) - family_core_ids)
    if missing_entry_ids:
        errors.append("family_core cases missing from boundary registry: " + ", ".join(missing_entry_ids))
    if extra_entry_ids:
        warnings.append("boundary registry entries not in current family_core layer: " + ", ".join(extra_entry_ids))

    rows: list[dict[str, Any]] = []
    for case in family_core_cases:
        row = _case_row(case, entries_by_case.get(case.id))
        rows.append(row)
        errors.extend(f"{case.id}: {error}" for error in row["errors"])

    family_rows = _family_rows(rows)
    missing_boundary_cases = sorted(row["case_id"] for row in rows if row["missing_categories"])
    strong_upgrade_blocked_cases = sorted(
        row["case_id"]
        for row in rows
        if row["support_level"] == "strong" and row["missing_categories"]
    )
    summary = {
        "family_core_case_count": len(family_core_cases),
        "strong_family_core_case_count": sum(1 for case in family_core_cases if case.support_level == "strong"),
        "registered_case_count": len(entries_by_case),
        "missing_family_core_cases": missing_entry_ids,
        "extra_registered_cases": extra_entry_ids,
        "missing_boundary_cases": missing_boundary_cases,
        "strong_upgrade_blocked_cases": strong_upgrade_blocked_cases,
        "family_count": len(family_rows),
        "overall_ready": not errors and not missing_boundary_cases,
        "strong_upgrade_ready": not strong_upgrade_blocked_cases,
    }
    return {
        "schema_version": "boundary-case-report-v1",
        "registry_path": str(REGISTRY_PATH.relative_to(ROOT)),
        "categories": list(BOUNDARY_CATEGORIES),
        "summary": summary,
        "families": family_rows,
        "cases": rows,
        "errors": errors,
        "warnings": warnings,
        "commands": {
            "boundary_cases": f"{PYTHON} scripts/check_boundary_cases.py",
            "benchmark_regression": f"{PYTHON} -m tests.benchmark_regression",
        },
    }


def _case_row(case: BenchmarkCase, entry: dict[str, Any] | None) -> dict[str, Any]:
    errors: list[str] = []
    if entry is None:
        entry = {"case_id": case.id, "coverage": [], "not_applicable": []}
        errors.append("missing boundary registry entry")
    missing_fields = sorted(REQUIRED_FIELDS - set(entry))
    if missing_fields:
        errors.append("missing fields: " + ", ".join(missing_fields))

    coverage_items = list(entry.get("coverage") or [])
    not_applicable_items = list(entry.get("not_applicable") or [])
    covered_categories: list[str] = []
    not_applicable_categories: list[str] = []

    for index, item in enumerate(coverage_items):
        if not isinstance(item, dict):
            errors.append(f"coverage[{index}] must be an object")
            continue
        category = str(item.get("category") or "")
        if category not in VALID_CATEGORIES:
            errors.append(f"coverage[{index}] category {category!r} is invalid")
            continue
        if category in covered_categories:
            errors.append(f"coverage category {category!r} is duplicated")
        covered_categories.append(category)
        sample_index = item.get("sample_index")
        if not isinstance(sample_index, int) or sample_index < 0 or sample_index >= len(case.samples):
            errors.append(f"coverage[{index}] sample_index must reference an existing sample")
        if not item.get("evidence"):
            errors.append(f"coverage[{index}] evidence must be non-empty")

    for index, item in enumerate(not_applicable_items):
        if not isinstance(item, dict):
            errors.append(f"not_applicable[{index}] must be an object")
            continue
        category = str(item.get("category") or "")
        if category not in VALID_CATEGORIES:
            errors.append(f"not_applicable[{index}] category {category!r} is invalid")
            continue
        if category in not_applicable_categories:
            errors.append(f"not_applicable category {category!r} is duplicated")
        not_applicable_categories.append(category)
        if not item.get("reason"):
            errors.append(f"not_applicable[{index}] reason must be non-empty")

    overlap = sorted(set(covered_categories) & set(not_applicable_categories))
    if overlap:
        errors.append("categories cannot be both covered and not_applicable: " + ", ".join(overlap))
    missing_categories = sorted(VALID_CATEGORIES - set(covered_categories) - set(not_applicable_categories))
    if missing_categories:
        errors.append("missing boundary categories: " + ", ".join(missing_categories))

    return {
        "case_id": case.id,
        "family": case.family,
        "family_id": case.family_id,
        "subfamily_id": case.subfamily_id,
        "gate_layer": case.gate_layer,
        "support_level": case.support_level,
        "sample_count": len(case.samples),
        "covered_categories": sorted(set(covered_categories)),
        "not_applicable_categories": sorted(set(not_applicable_categories)),
        "missing_categories": missing_categories,
        "coverage": coverage_items,
        "not_applicable": not_applicable_items,
        "status": "fail" if errors else "pass",
        "errors": errors,
    }


def _family_rows(case_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        grouped[row["family_id"]].append(row)

    families: dict[str, dict[str, Any]] = {}
    for family_id in sorted(grouped):
        rows = grouped[family_id]
        boundary_counts: Counter[str] = Counter()
        not_applicable_counts: Counter[str] = Counter()
        missing_counts: Counter[str] = Counter()
        for row in rows:
            boundary_counts.update(row["covered_categories"])
            not_applicable_counts.update(row["not_applicable_categories"])
            missing_counts.update(row["missing_categories"])
        families[family_id] = {
            "family": rows[0]["family"],
            "case_count": len(rows),
            "strong_case_count": sum(1 for row in rows if row["support_level"] == "strong"),
            "missing_case_count": sum(1 for row in rows if row["missing_categories"]),
            "case_ids": [row["case_id"] for row in rows],
            "boundary_counts": dict(sorted(boundary_counts.items())),
            "not_applicable_counts": dict(sorted(not_applicable_counts.items())),
            "missing_counts": dict(sorted(missing_counts.items())),
        }
    return families


def write_boundary_case_report(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_boundary_case_report()
    json_path = output_dir / "boundary_cases.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "boundary_cases.md").write_text(render_markdown(report), encoding="utf-8")
    return json_path


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Boundary Cases",
        "",
        f"- overall_ready: `{summary['overall_ready']}`",
        f"- strong_upgrade_ready: `{summary['strong_upgrade_ready']}`",
        f"- family_core_case_count: `{summary['family_core_case_count']}`",
        f"- missing_boundary_cases: `{len(summary['missing_boundary_cases'])}`",
        "",
        "## Families",
        "",
        "| family_id | family | cases | missing cases | covered categories | missing categories |",
        "|---|---|---:|---:|---|---|",
    ]
    for family_id, row in report["families"].items():
        lines.append(
            "| {family_id} | {family} | {case_count} | {missing_case_count} | {covered} | {missing} |".format(
                family_id=family_id,
                family=row["family"],
                case_count=row["case_count"],
                missing_case_count=row["missing_case_count"],
                covered=", ".join(row["boundary_counts"]),
                missing=", ".join(row["missing_counts"]),
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
    parser = argparse.ArgumentParser(description="校验 AlgoLab family_core 边界样例覆盖登记")
    parser.add_argument("--output-dir", type=Path, default=Path("output/boundary_cases"))
    args = parser.parse_args()
    path = write_boundary_case_report(args.output_dir)
    report = json.loads(path.read_text(encoding="utf-8"))
    print(path)
    return 0 if report["summary"]["overall_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
