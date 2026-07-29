"""Merge LLM benchmark reports while preserving condition labels."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_report_spec(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("--report must use CONDITION=PATH")
    condition, path = raw.split("=", 1)
    condition = condition.strip()
    if not condition:
        raise argparse.ArgumentTypeError("--report condition cannot be empty")
    return condition, Path(path.strip())


def condition_from_report(report: dict[str, Any]) -> str:
    config = report.get("config") if isinstance(report.get("config"), dict) else {}
    for key in ("benchmark_condition", "condition", "experiment_condition"):
        value = config.get(key)
        if isinstance(value, str) and value:
            return value
    return "algolab_full"


def failure_type_for_result(item: dict[str, Any]) -> str:
    failure_type = item.get("failure_type")
    if isinstance(failure_type, str) and failure_type:
        return failure_type
    errors = item.get("errors")
    text = "; ".join(str(error) for error in errors) if isinstance(errors, list) else str(item.get("error") or "")
    if "failure_type=" in text:
        marker = text.split("failure_type=", 1)[1]
        return marker.split(":", 1)[0].split(";", 1)[0].strip() or "unknown"
    if "timeout" in text.lower():
        return "timeout"
    return "unknown"


def merge_results(report_specs: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for condition, path in report_specs:
        report = load_json(path)
        source_condition = condition_from_report(report)
        results = report.get("results")
        if not isinstance(results, list):
            raise ValueError(f"{path} missing results list")
        for result in results:
            if not isinstance(result, dict):
                continue
            item = dict(result)
            original_condition = str(item.get("condition") or source_condition)
            item["source_condition"] = original_condition
            item["condition"] = condition
            item["source_llm_report"] = str(path)
            merged.append(item)
    return merged


def merge_browser_smoke(report_specs: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for condition, path in report_specs:
        report = load_json(path)
        checks = report.get("browser_smoke") or []
        if isinstance(checks, dict):
            checks = checks.get("items") or []
        if not isinstance(checks, list):
            continue
        for check in checks:
            if not isinstance(check, dict):
                continue
            item = dict(check)
            item["condition"] = condition
            item["source_llm_report"] = str(path)
            merged.append(item)
    return merged


def model_from_report(report: dict[str, Any]) -> str:
    config = report.get("config") if isinstance(report.get("config"), dict) else {}
    llm = config.get("llm") if isinstance(config.get("llm"), dict) else {}
    for value in (config.get("model"), llm.get("model"), report.get("model")):
        if isinstance(value, str) and value:
            return value
    return ""


def source_report_summaries(report_specs: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for condition, path in report_specs:
        report = load_json(path)
        config = report.get("config") if isinstance(report.get("config"), dict) else {}
        summaries.append(
            {
                "condition": condition,
                "source_condition": condition_from_report(report),
                "path": str(path),
                "model": model_from_report(report),
                "config": dict(config),
                "total": int(report.get("total") or 0),
                "passed": int(report.get("passed") or 0),
                "failed": int(report.get("failed") or 0),
                "pass_rate": report.get("pass_rate"),
                "model_usage": report.get("model_usage") if isinstance(report.get("model_usage"), dict) else {},
            }
        )
    return summaries


def summarize_model_usage(results: list[dict[str, Any]]) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    for result in results:
        result_calls = result.get("model_calls")
        if isinstance(result_calls, list):
            calls.extend(call for call in result_calls if isinstance(call, dict))
        elif isinstance(result.get("model_call"), dict):
            calls.append(result["model_call"])
    call_count = len(calls)
    usage_calls = [call for call in calls if call.get("usage_available") is True]
    all_usage_available = call_count > 0 and len(usage_calls) == call_count
    duration_s = round(sum(float(call.get("duration_s") or 0.0) for call in calls), 3)
    total_tokens = sum(int(call["total_tokens"]) for call in usage_calls) if all_usage_available else None
    return {
        "usage_available": all_usage_available,
        "usage_available_rate": (len(usage_calls) / call_count) if call_count else 0.0,
        "call_count": call_count,
        "prompt_tokens": sum(int(call["prompt_tokens"]) for call in usage_calls) if all_usage_available else None,
        "completion_tokens": sum(int(call["completion_tokens"]) for call in usage_calls) if all_usage_available else None,
        "total_tokens": total_tokens,
        "duration_s": duration_s,
        "avg_duration_s": (duration_s / call_count) if call_count else 0.0,
        "avg_total_tokens": (total_tokens / call_count) if all_usage_available and call_count else None,
        "estimated_cost": None,
        "cost_estimation_available": False,
        "pricing_source": "",
    }


def count_by(items: list[dict[str, Any]], key: str, default: str = "unknown") -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or default)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def build_report(report_specs: list[tuple[str, Path]]) -> dict[str, Any]:
    results = merge_results(report_specs)
    browser_smoke = merge_browser_smoke(report_specs)
    source_reports = source_report_summaries(report_specs)
    models = sorted({item["model"] for item in source_reports if item.get("model")})
    failed = [item for item in results if not item.get("ok")]
    failure_summary: dict[str, int] = {}
    for item in failed:
        failure_type = failure_type_for_result(item)
        failure_summary[failure_type] = failure_summary.get(failure_type, 0) + 1
    passed = len(results) - len(failed)
    return {
        "schema_version": "merged-llm-benchmark-report-v1",
        "kind": "llm_benchmark",
        "created_at": now_iso(),
        "started_at": "",
        "ended_at": "",
        "cached": False,
        "config": {
            "benchmark_condition": "merged",
            "conditions": [condition for condition, _path in report_specs],
            "reports": [{"condition": condition, "path": str(path)} for condition, path in report_specs],
            "source_reports": source_reports,
            "models": models,
        },
        "total": len(results),
        "passed": passed,
        "failed": len(failed),
        "pass_rate": (passed / len(results)) if results else 0.0,
        "failure_summary": dict(sorted(failure_summary.items())),
        "case_set_summary": count_by(results, "case_set", "deterministic"),
        "case_style_summary": count_by(results, "case_style", "unknown"),
        "browser_smoke": browser_smoke,
        "model_usage": summarize_model_usage(results),
        "results": results,
    }


def write_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "merged_llm_benchmark_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=parse_report_spec, required=True, help="CONDITION=llm_benchmark_report.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.report)
    path = write_report(report, args.output_dir)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
