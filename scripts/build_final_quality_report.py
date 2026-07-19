"""Build a final-quality benchmark report from a primary run and retries.

The primary report defines the frozen case set. Retry rows may replace only
primary failures. Exact target-budget retries are preferred; successful rows
from a larger exploratory budget are accepted only when the selected
candidate and round are within the requested target bounds. The latter are
marked explicitly and must not be described as a strict counterfactual run.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_llm_benchmark import (
    build_family_summary,
    summarize_candidate_selection,
    summarize_failures,
    summarize_field_counts,
    summarize_model_usage,
    summarize_phase_timings,
    summarize_repair_failure_types,
)


def load_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report.get("results"), list):
        raise ValueError(f"{path} missing results list")
    return report


def index_results(report: dict[str, Any], *, path: Path) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in report["results"]:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError(f"{path}: result missing case_id")
        if case_id in indexed:
            raise ValueError(f"{path}: duplicate case_id {case_id}")
        indexed[case_id] = row
    return indexed


def source_budget(report: dict[str, Any]) -> tuple[int, int]:
    config = report.get("config") if isinstance(report.get("config"), dict) else {}
    return int(config.get("max_candidates") or 1), int(config.get("max_rounds") or 0)


def selected_within_budget(row: dict[str, Any], *, max_candidates: int, max_rounds: int) -> bool:
    summary = row.get("candidate_summary") if isinstance(row.get("candidate_summary"), dict) else {}
    selected_candidate = summary.get("selected_candidate")
    selected_round = summary.get("selected_round")
    return (
        row.get("ok") is True
        and isinstance(selected_candidate, int)
        and isinstance(selected_round, int)
        and selected_candidate < max_candidates
        and selected_round <= max_rounds
    )


def usage_sum(reports: list[dict[str, Any]]) -> dict[str, Any]:
    usages = [report.get("model_usage") or {} for report in reports]
    all_available = all(usage.get("usage_available") is True for usage in usages)
    call_count = sum(int(usage.get("call_count") or 0) for usage in usages)
    duration_s = round(sum(float(usage.get("duration_s") or 0.0) for usage in usages), 3)

    def total(key: str) -> int | None:
        if not all_available:
            return None
        return sum(int(usage.get(key) or 0) for usage in usages)

    total_tokens = total("total_tokens")
    return {
        "usage_available": all_available,
        "call_count": call_count,
        "prompt_tokens": total("prompt_tokens"),
        "completion_tokens": total("completion_tokens"),
        "total_tokens": total_tokens,
        "duration_s": duration_s,
        "avg_duration_s": duration_s / call_count if call_count else 0.0,
        "avg_total_tokens": total_tokens / call_count if total_tokens is not None and call_count else None,
        "note": "Observed cumulative primary plus retry execution cost; exploratory retries may exceed the target budget.",
    }


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def report_time(reports: list[dict[str, Any]], key: str, *, earliest: bool) -> str:
    values = [parse_time(report.get(key)) for report in reports]
    valid = [value for value in values if value is not None]
    if not valid:
        return ""
    selected = min(valid) if earliest else max(valid)
    return selected.isoformat(timespec="seconds")


def average_duration(results: list[dict[str, Any]]) -> float:
    durations = [float(row.get("duration_s") or 0.0) for row in results]
    return round(sum(durations) / len(durations), 3) if durations else 0.0


def build_report(
    primary_path: Path,
    retry_paths: list[Path],
    *,
    max_candidates: int,
    max_rounds: int,
    expected_cases: int,
    output_dir: Path,
) -> dict[str, Any]:
    primary = load_report(primary_path)
    retries = [(path, load_report(path)) for path in retry_paths]
    primary_rows = index_results(primary, path=primary_path)
    if len(primary_rows) != expected_cases:
        raise ValueError(f"primary expected {expected_cases} cases, found {len(primary_rows)}")

    retry_by_case: dict[str, list[tuple[Path, dict[str, Any], dict[str, Any]]]] = {}
    for path, report in retries:
        for case_id, row in index_results(report, path=path).items():
            if case_id not in primary_rows:
                raise ValueError(f"{path}: retry case {case_id} is absent from primary")
            retry_by_case.setdefault(case_id, []).append((path, report, row))

    results: list[dict[str, Any]] = []
    selection_counts = {
        "primary_retained_pass": 0,
        "primary_retained_failure": 0,
        "exact_target_retry_pass": 0,
        "compatible_larger_budget_retry_pass": 0,
        "target_retry_failure": 0,
    }
    replaced_case_ids: list[str] = []
    unresolved_case_ids: list[str] = []

    for case_id, primary_row in primary_rows.items():
        candidates = retry_by_case.get(case_id, [])
        if primary_row.get("ok") is True:
            selected_path, selected_report, selected_row = primary_path, primary, primary_row
            selection_kind = "primary_retained_pass"
        else:
            exact_successes = []
            compatible_successes = []
            exact_failures = []
            other_failures = []
            for item in candidates:
                path, report, row = item
                candidate_budget, round_budget = source_budget(report)
                exact_budget = candidate_budget == max_candidates and round_budget == max_rounds
                if selected_within_budget(row, max_candidates=max_candidates, max_rounds=max_rounds):
                    (exact_successes if exact_budget else compatible_successes).append(item)
                elif exact_budget:
                    exact_failures.append(item)
                else:
                    other_failures.append(item)

            if exact_successes:
                selected_path, selected_report, selected_row = exact_successes[-1]
                selection_kind = "exact_target_retry_pass"
                replaced_case_ids.append(case_id)
            elif compatible_successes:
                selected_path, selected_report, selected_row = compatible_successes[-1]
                selection_kind = "compatible_larger_budget_retry_pass"
                replaced_case_ids.append(case_id)
            elif exact_failures:
                selected_path, selected_report, selected_row = exact_failures[-1]
                selection_kind = "target_retry_failure"
                unresolved_case_ids.append(case_id)
            elif other_failures:
                selected_path, selected_report, selected_row = other_failures[-1]
                selection_kind = "target_retry_failure"
                unresolved_case_ids.append(case_id)
            else:
                selected_path, selected_report, selected_row = primary_path, primary, primary_row
                selection_kind = "primary_retained_failure"
                unresolved_case_ids.append(case_id)

        source_candidates, source_rounds = source_budget(selected_report)
        exact_target_run = source_candidates == max_candidates and source_rounds == max_rounds
        source_within_target = source_candidates <= max_candidates and source_rounds <= max_rounds
        row = deepcopy(selected_row)
        selected_summary = row.get("candidate_summary") if isinstance(row.get("candidate_summary"), dict) else {}
        selected_candidate = selected_summary.get("selected_candidate")
        within_target = selected_within_budget(
            row,
            max_candidates=max_candidates,
            max_rounds=max_rounds,
        )
        strict_counterfactual = (
            exact_target_run
            or (source_within_target and within_target)
            or (within_target and selected_candidate == 0)
        )
        if exact_target_run:
            compatibility_note = "Exact target-budget execution."
        elif source_within_target and within_target:
            compatibility_note = "Successful execution used a budget no larger than the target and stopped within the target bounds."
        elif within_target and selected_candidate == 0:
            compatibility_note = "The larger source budget was not exercised before the candidate-0 success, so the execution prefix is identical under the target cap."
        elif within_target:
            compatibility_note = (
                "Selected candidate/round is within the target bounds, but earlier candidates may have used the larger exploratory repair cap."
            )
        else:
            compatibility_note = "The source execution does not establish success within the target budget."
        row["final_source_report"] = str(selected_path)
        row["final_selection_kind"] = selection_kind
        row["target_budget_compatibility"] = {
            "max_candidates": max_candidates,
            "max_rounds": max_rounds,
            "source_max_candidates": source_candidates,
            "source_max_rounds": source_rounds,
            "exact_target_run": exact_target_run,
            "source_budget_within_target": source_within_target,
            "selected_within_target": within_target,
            "strict_counterfactual": strict_counterfactual,
            "note": compatibility_note,
        }
        row["retry_history"] = [
            {
                "report": str(path),
                "ok": retry_row.get("ok") is True,
                "failure_type": retry_row.get("failure_type"),
                "source_max_candidates": source_budget(report)[0],
                "source_max_rounds": source_budget(report)[1],
                "selected_candidate": (retry_row.get("candidate_summary") or {}).get("selected_candidate"),
                "selected_round": (retry_row.get("candidate_summary") or {}).get("selected_round"),
            }
            for path, report, retry_row in candidates
        ]
        results.append(row)
        selection_counts[selection_kind] += 1

    results.sort(key=lambda row: str(row["case_id"]))
    ids = [str(row["case_id"]) for row in results]
    if len(ids) != expected_cases or len(set(ids)) != expected_cases:
        raise ValueError("final report must contain the expected number of unique case IDs")

    started_at = report_time([primary, *[report for _path, report in retries]], "started_at", earliest=True)
    ended_at = report_time([primary, *[report for _path, report in retries]], "ended_at", earliest=False)
    config = deepcopy(primary.get("config") or {})
    config.update(
        {
            "cases": ids,
            "max_candidates": max_candidates,
            "max_rounds": max_rounds,
            "benchmark_condition": "algolab_full",
            "final_quality_composite": True,
            "primary_report": str(primary_path),
            "retry_reports": [str(path) for path in retry_paths],
            "composite_policy": (
                "Keep primary passes; replace primary failures with exact target-budget retry passes, "
                "then successful larger-budget rows whose selected candidate/round lies within target bounds."
            ),
        }
    )
    args = argparse.Namespace(
        condition="algolab_full",
        family=config.get("family") or [],
        gate_layer=config.get("gate_layer") or [],
        limit_per_family=int(config.get("limit_per_family") or 0),
        all_samples=bool(config.get("all_samples")),
        sample=config.get("sample"),
        case_set=config.get("case_set") or "deterministic",
        family_sets=config.get("family_sets") or "benchmark/llm_family_sets.json",
        unseen_cases=config.get("unseen_cases") or "benchmark/unseen_family_cases.json",
    )
    family_summary = build_family_summary(results, args=args, started_at=started_at, ended_at=ended_at)
    family_summary_path = output_dir / "family_summary.json"
    report = {
        "kind": "llm_benchmark_report",
        "cached": False,
        "started_at": started_at,
        "ended_at": ended_at,
        "config": config,
        "total": len(results),
        "passed": sum(1 for row in results if row.get("ok") is True),
        "failed": sum(1 for row in results if row.get("ok") is not True),
        "pass_rate": sum(1 for row in results if row.get("ok") is True) / len(results),
        "avg_duration_s": average_duration(results),
        "failure_summary": summarize_failures(results),
        "repair_failure_summary": summarize_repair_failure_types(results),
        "case_set_summary": summarize_field_counts(results, "case_set", "deterministic"),
        "case_style_summary": summarize_field_counts(results, "case_style"),
        "family_summary_path": str(family_summary_path),
        "family_summary": family_summary["families"],
        "phase_summary": summarize_phase_timings(results),
        "model_usage": summarize_model_usage(results),
        "observed_experiment_usage": usage_sum([primary, *[report for _path, report in retries]]),
        "candidate_selection": summarize_candidate_selection(results),
        "final_quality_selection": {
            **selection_counts,
            "replaced_case_ids": sorted(replaced_case_ids),
            "unresolved_case_ids": sorted(unresolved_case_ids),
        },
        "browser_smoke": [],
        "results": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    family_summary_path.write_text(json.dumps(family_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "llm_benchmark_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Final Quality LLM Benchmark Report",
        "",
        f"- Total: {report['total']}",
        f"- Passed: {report['passed']}",
        f"- Failed: {report['failed']}",
        f"- Pass rate: {report['pass_rate']:.2%}",
        f"- Target budget: {max_candidates} candidates x {max_rounds} repair rounds",
        f"- Exact target retry passes: {selection_counts['exact_target_retry_pass']}",
        f"- Compatible larger-budget retry passes: {selection_counts['compatible_larger_budget_retry_pass']}",
        f"- Unresolved: {', '.join(sorted(unresolved_case_ids)) or 'none'}",
    ]
    (output_dir / "llm_benchmark_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-report", type=Path, required=True)
    parser.add_argument("--retry-report", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--expected-cases", type=int, default=200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        args.primary_report,
        args.retry_report,
        max_candidates=args.max_candidates,
        max_rounds=args.max_rounds,
        expected_cases=args.expected_cases,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "output": str(args.output_dir / "llm_benchmark_report.json"),
                "total": report["total"],
                "passed": report["passed"],
                "failed": report["failed"],
                "selection": report["final_quality_selection"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
