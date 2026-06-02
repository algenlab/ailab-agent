"""Merge per-condition VLM screenshot reports into condition comparison artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_vlm_screenshot_eval import SCORE_FIELDS, score_averages, summarize_model_usage


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reports(paths: list[Path]) -> list[dict[str, Any]]:
    reports = []
    for path in paths:
        report = load_json(path)
        results = report.get("results")
        if not isinstance(results, list):
            raise ValueError(f"{path} missing results list")
        reports.append({"path": str(path), "report": report})
    return reports


def condition_for_result(result: dict[str, Any], report: dict[str, Any]) -> str:
    return str(result.get("condition") or report.get("condition") or "")


def merged_results(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in reports:
        report = item["report"]
        source_path = item["path"]
        for result in report["results"]:
            if not isinstance(result, dict):
                continue
            normalized = dict(result)
            normalized["condition"] = condition_for_result(normalized, report)
            normalized["source_vlm_report"] = source_path
            results.append(normalized)
    return results


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok_results = [result for result in results if result.get("ok")]
    failed_results = [result for result in results if not result.get("ok")]
    failure_types: dict[str, int] = {}
    for result in failed_results:
        failure_type = str(result.get("failure_type") or "unknown")
        failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
    low_score_results = [
        result
        for result in ok_results
        if isinstance(result.get("scores"), dict) and any(int(result["scores"][field]) <= 2 for field in SCORE_FIELDS)
    ]
    high_confidence_issue_results = [
        result
        for result in ok_results
        if float(result.get("confidence") or 0.0) >= 0.7 and result.get("issues")
    ]
    return {
        "total": len(results),
        "passed": len(ok_results),
        "failed": len(failed_results),
        "pass_rate": (len(ok_results) / len(results)) if results else 0.0,
        "failure_types": failure_types,
        "score_averages": score_averages(results),
        "low_score_count": len(low_score_results),
        "high_confidence_issue_count": len(high_confidence_issue_results),
        "model_usage": summarize_model_usage(results),
    }


def condition_summaries(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in sorted({str(result.get("condition") or "") for result in results}):
        condition_results = [result for result in results if str(result.get("condition") or "") == condition]
        summary = summarize_results(condition_results)
        rows.append({"condition": condition, **summary})
    return rows


def summary_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in sorted({str(result.get("condition") or "") for result in results}):
        condition_results = [result for result in results if str(result.get("condition") or "") == condition]
        groups: list[tuple[str, list[dict[str, Any]]]] = [("all", condition_results)]
        for viewport in sorted({str(result.get("viewport") or "") for result in condition_results if result.get("viewport")}):
            groups.append((f"viewport:{viewport}", [result for result in condition_results if result.get("viewport") == viewport]))
        for screenshot_type in sorted(
            {str(result.get("screenshot_type") or "") for result in condition_results if result.get("screenshot_type")}
        ):
            groups.append(
                (
                    f"type:{screenshot_type}",
                    [result for result in condition_results if result.get("screenshot_type") == screenshot_type],
                )
            )
        for group, group_results in groups:
            summary = summarize_results(group_results)
            row = {
                "condition": condition,
                "group": group,
                "total": summary["total"],
                "passed": summary["passed"],
                "failed": summary["failed"],
                "pass_rate": summary["pass_rate"],
                "low_score_count": summary["low_score_count"],
                "high_confidence_issue_count": summary["high_confidence_issue_count"],
                "failure_types": json.dumps(summary["failure_types"], ensure_ascii=False, sort_keys=True),
            }
            for field, value in summary["score_averages"].items():
                row[f"avg_{field}"] = value
            rows.append(row)
    return rows


def build_report(paths: list[Path]) -> dict[str, Any]:
    reports = load_reports(paths)
    results = merged_results(reports)
    return {
        "schema_version": "vlm-condition-scores-v1",
        "created_at": now_iso(),
        "source_reports": [item["path"] for item in reports],
        "conditions": sorted({str(result.get("condition") or "") for result in results}),
        "summary": {
            "total": len(results),
            "conditions": condition_summaries(results),
            "model_usage": summarize_model_usage(results),
        },
        "results": results,
    }


def write_scores_csv(report: dict[str, Any], path: Path) -> None:
    fields = [
        "condition",
        "case_id",
        "viewport",
        "kind",
        "screenshot_type",
        "screenshot",
        "ok",
        "failure_type",
        *SCORE_FIELDS,
        "confidence",
        "issue_count",
        "suggested_caption",
        "judge_model",
        "usage_available",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "duration_s",
        "error",
        "source_vlm_report",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for result in report["results"]:
            scores = result.get("scores") or {}
            model_call = result.get("model_call") or {}
            row = {
                "condition": result.get("condition", ""),
                "case_id": result.get("case_id", ""),
                "viewport": result.get("viewport", ""),
                "kind": result.get("kind", ""),
                "screenshot_type": result.get("screenshot_type", ""),
                "screenshot": result.get("screenshot", ""),
                "ok": result.get("ok", False),
                "failure_type": result.get("failure_type", ""),
                "confidence": result.get("confidence", 0.0),
                "issue_count": len(result.get("issues") or []),
                "suggested_caption": result.get("suggested_caption", ""),
                "judge_model": result.get("judge_model", ""),
                "usage_available": model_call.get("usage_available", False),
                "prompt_tokens": model_call.get("prompt_tokens"),
                "completion_tokens": model_call.get("completion_tokens"),
                "total_tokens": model_call.get("total_tokens"),
                "duration_s": model_call.get("duration_s", 0.0),
                "error": result.get("error", ""),
                "source_vlm_report": result.get("source_vlm_report", ""),
            }
            for field in SCORE_FIELDS:
                row[field] = scores.get(field)
            writer.writerow(row)


def write_summary_csv(report: dict[str, Any], path: Path) -> None:
    fields = [
        "condition",
        "group",
        "total",
        "passed",
        "failed",
        "pass_rate",
        "low_score_count",
        "high_confidence_issue_count",
        "failure_types",
        *(f"avg_{field}" for field in SCORE_FIELDS),
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary_rows(report["results"]))


def write_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "vlm_condition_scores.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_scores_csv(report, output_dir / "vlm_condition_scores.csv")
    write_summary_csv(report, output_dir / "vlm_condition_summary.csv")
    return json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=Path, required=True, help="per-condition vlm_screenshot_scores.json")
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
