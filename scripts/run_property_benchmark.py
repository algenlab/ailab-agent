"""Run fixed-seed small randomized property benchmarks.

This P11.2 benchmark is a robustness report only.  It does not call the LLM,
does not materialize HTML, and is intentionally excluded from the V1 release
gate.
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

from tests.property_cases import DEFAULT_PROPERTY_SEED, PropertyCase, generate_property_samples, property_cases


PYTHON = "/ssd1/liaokunpeng/agent-py310-cu/bin/python3"


def build_property_benchmark_report(
    *,
    seed: int = DEFAULT_PROPERTY_SEED,
    sample_count: int | None = None,
    cases: list[PropertyCase] | None = None,
) -> dict[str, Any]:
    selected_cases = cases or property_cases()
    results = [
        _run_property_sample(sample)
        for sample in generate_property_samples(seed=seed, sample_count=sample_count, cases=selected_cases)
    ]
    summary = _summary(results, seed=seed)
    return {
        "schema_version": "property-benchmark-v1",
        "description": "Fixed-seed small randomized oracle/property benchmark for family robustness. Not included in V1 release gate.",
        "release_gate_included": False,
        "commands": {
            "property_benchmark": f"{PYTHON} scripts/run_property_benchmark.py --output-dir output/property_benchmark",
        },
        "summary": summary,
        "results": results,
    }


def write_property_benchmark_report(
    output_dir: Path,
    *,
    seed: int = DEFAULT_PROPERTY_SEED,
    sample_count: int | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_property_benchmark_report(seed=seed, sample_count=sample_count)
    json_path = output_dir / "property_benchmark_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown(output_dir / "property_benchmark_report.md", report)
    return json_path


def _run_property_sample(sample: dict[str, Any]) -> dict[str, Any]:
    case: PropertyCase = sample["case"]
    input_data = sample["input"]
    expected: Any = None
    actual: Any = None
    ok = False
    failure_type = ""
    error = ""
    try:
        expected = case.expected_solver(input_data)
    except Exception as exc:  # pragma: no cover - regression tests exercise success path
        failure_type = "oracle_error"
        error = f"{type(exc).__name__}: {exc}"
    else:
        try:
            actual = case.actual_solver(input_data)
        except Exception as exc:  # pragma: no cover - regression tests exercise success path
            failure_type = "exception"
            error = f"{type(exc).__name__}: {exc}"
        else:
            ok = expected == actual
            failure_type = "" if ok else "answer_mismatch"

    return {
        "case_id": case.id,
        "sample_index": sample["sample_index"],
        "family": case.family,
        "family_id": case.family_id,
        "subfamily": case.subfamily,
        "subfamily_id": case.subfamily_id,
        "oracle_type": case.oracle_type,
        "input": input_data,
        "expected": expected,
        "actual": actual,
        "ok": ok,
        "failure_type": failure_type,
        "error": error,
    }


def _summary(results: list[dict[str, Any]], *, seed: int) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result["ok"])
    failed = total - passed
    families = sorted({result["family_id"] for result in results})
    return {
        "seed": seed,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total else 0.0,
        "families": families,
        "failure_types": dict(sorted(Counter(result["failure_type"] or "pass" for result in results).items())),
        "family_robustness": _family_robustness(results),
    }


def _family_robustness(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        by_family[result["family_id"]].append(result)

    rows: dict[str, dict[str, Any]] = {}
    for family_id in sorted(by_family):
        family_results = by_family[family_id]
        total = len(family_results)
        passed = sum(1 for result in family_results if result["ok"])
        failed = total - passed
        rows[family_id] = {
            "family": family_results[0]["family"],
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total else 0.0,
            "subfamilies": sorted({result["subfamily_id"] for result in family_results}),
            "failure_types": dict(sorted(Counter(result["failure_type"] or "pass" for result in family_results).items())),
        }
    return rows


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# Property Benchmark",
        "",
        "Fixed-seed randomized small samples for family robustness; not included in V1 release gate.",
        "",
        f"- Seed: `{summary['seed']}`",
        f"- Total: `{summary['total']}`",
        f"- Passed: `{summary['passed']}`",
        f"- Failed: `{summary['failed']}`",
        f"- Pass rate: `{summary['pass_rate']:.3f}`",
        "",
        "## Family Robustness",
        "",
        "| family_id | family | total | passed | failed | pass_rate | subfamilies |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for family_id, row in summary["family_robustness"].items():
        lines.append(
            "| {family_id} | {family} | {total} | {passed} | {failed} | {pass_rate:.3f} | {subfamilies} |".format(
                family_id=family_id,
                family=row["family"],
                total=row["total"],
                passed=row["passed"],
                failed=row["failed"],
                pass_rate=row["pass_rate"],
                subfamilies=", ".join(row["subfamilies"]),
            )
        )

    failed = [result for result in report["results"] if not result["ok"]]
    lines.extend(["", "## Failures", ""])
    if not failed:
        lines.append("No property benchmark failures.")
    else:
        lines.append("| family | subfamily | sample | failure_type | input | expected | actual |")
        lines.append("|---|---|---:|---|---|---|---|")
        for result in failed:
            lines.append(
                "| {family} | {subfamily} | {sample} | {failure_type} | `{input}` | `{expected}` | `{actual}` |".format(
                    family=result["family_id"],
                    subfamily=result["subfamily_id"],
                    sample=result["sample_index"],
                    failure_type=result["failure_type"],
                    input=json.dumps(result["input"], ensure_ascii=False, sort_keys=True),
                    expected=json.dumps(result["expected"], ensure_ascii=False, sort_keys=True),
                    actual=json.dumps(result["actual"], ensure_ascii=False, sort_keys=True),
                )
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixed-seed property benchmark robustness samples.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/property_benchmark"))
    parser.add_argument("--seed", type=int, default=DEFAULT_PROPERTY_SEED)
    parser.add_argument("--sample-count", type=int, default=None)
    args = parser.parse_args()
    json_path = write_property_benchmark_report(args.output_dir, seed=args.seed, sample_count=args.sample_count)
    print(f"wrote {json_path}")


if __name__ == "__main__":
    main()
