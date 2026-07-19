"""Analyze failed cases in an llm_benchmark_report.json."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT_CAUSES = (
    "legacy_schema_or_target_format",
    "runtime_api_or_generated_code_error",
    "missing_key_events_or_coverage",
    "missing_evidence_or_deps",
    "actual_algorithm_state_mismatch",
    "scene_object_binding_warning",
    "string_contract_overgeneralized",
    "validator_acceptance_bug",
    "unknown",
)


def _compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    elif isinstance(value, (list, tuple)):
        text = "; ".join(_compact_text(item) for item in value if item is not None)
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    return re.sub(r"\s+", " ", text).strip()


def error_summary(result: dict[str, Any], *, max_chars: int = 240) -> str:
    text = _compact_text(result.get("error")) or _compact_text(result.get("errors"))
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def classify_failure(result: dict[str, Any]) -> str:
    failure_type = _compact_text(result.get("failure_type")).lower()
    family = _compact_text(result.get("family")).lower()
    family_id = _compact_text(result.get("family_id")).lower()
    subfamily_id = _compact_text(result.get("subfamily_id")).lower()
    error = error_summary(result, max_chars=1000).lower()
    text = " ".join([failure_type, family, family_id, subfamily_id, error])

    if any(
        token in text
        for token in (
            "validator_acceptance",
            "acceptance bug",
            "bad solve accepted",
            "accepted invalid",
            "未支持的 family",
            "unsupported family",
        )
    ):
        return "validator_acceptance_bug"
    if any(
        token in text
        for token in (
            "llmjsonerror",
            "jsondecodeerror",
            "syntaxerror",
            "nameerror",
            "typeerror",
            "referenceerror",
            "importerror",
            "indentationerror",
            "modulenotfounderror",
            "traceback",
            "timeout",
            "timed out",
            "trace 执行失败",
            "trace 执行超时",
            "模型返回空内容",
            "无法解析 json",
            "不是合法 json",
            "generated code",
            "execution_error",
            "runtime",
        )
    ) or failure_type in {"runtime_error", "execution_error", "timeout"}:
        return "runtime_api_or_generated_code_error"
    if any(
        token in text
        for token in (
            "validationerror",
            "field required",
            "schema",
            "legacy",
            "旧式",
            "废弃",
            "target format",
            "targets field required",
            "不存在的索引 target",
            "引用了不存在的索引 target",
            "map target",
        )
    ) or failure_type in {"schema_error", "target_error", "target_or_deps"}:
        return "legacy_schema_or_target_format"
    if any(
        token in text
        for token in (
            "scenegraph",
            "scene warning",
            "visual_warning",
            "visible object",
            "可见对象",
            "对象集合",
            "edge binding",
            "node binding",
        )
    ):
        return "scene_object_binding_warning"
    if (
        "string" in family_id
        or "string" in family
        or any(token in text for token in ("kmp", "rabin", "prefix_function", "z_algorithm", "rolling_hash"))
    ) and any(token in text for token in ("overgeneralized", "over-generalized", "泛化")):
        return "string_contract_overgeneralized"
    if any(
        token in text
        for token in (
            "demo_missing_deps",
            "demo_missing_reason",
            "missing deps",
            "缺少 deps",
            "缺 deps",
            "missing evidence",
            "缺少 evidence",
            "缺少证据",
            "无比较证据",
            "字符路径证据",
            "缺少 reason",
            "missing reason",
            "reason 提到",
            "缺少可复原公式",
            "缺少公式",
            "缺少循环变量",
            "缺少当前节点",
            "缺少子树返回值",
            "缺少 count",
            "缺少 submode",
            "必须记录 stack",
            "recursion frame frontier",
            "deps 未出现在 state",
            "formula",
            "deps",
        )
    ):
        return "missing_evidence_or_deps"
    if any(
        token in text
        for token in (
            "demo_key_step_missing",
            "coverage_error",
            "missing key",
            "key step",
            "关键步骤",
            "关键事件",
            "关键更新",
            "coverage",
            "expected_events",
            "状态转移写入帧",
            "边检查帧",
            "pop 事件",
        )
    ):
        return "missing_key_events_or_coverage"
    if any(
        token in text
        for token in (
            "process_invariant",
            "demo_algorithm_mismatch",
            "demo_state_jump",
            "state_jump",
            "mismatch",
            "不满足",
            "错误",
            "应为",
            "状态跳变",
            "跳变",
            "algorithm_mismatch",
        )
    ):
        return "actual_algorithm_state_mismatch"
    return "unknown"


def _browser_summary(report: dict[str, Any]) -> dict[str, int]:
    checks = report.get("browser_smoke") or []
    total = len(checks)
    ok = sum(1 for item in checks if item.get("ok"))
    return {"browser_total": total, "browser_ok": ok, "browser_failed": total - ok}


def _model_usage(report: dict[str, Any]) -> dict[str, Any]:
    usage = report.get("model_usage") or {}
    return {
        "call_count": usage.get("call_count", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "usage_available_rate": usage.get("usage_available_rate", 0),
    }


def _failure_record(result: dict[str, Any]) -> dict[str, str]:
    return {
        "case_id": _compact_text(result.get("case_id")),
        "family": _compact_text(result.get("family")),
        "subfamily_id": _compact_text(result.get("subfamily_id")),
        "failure_type": _compact_text(result.get("failure_type")),
        "root_cause": classify_failure(result),
        "error_summary": error_summary(result),
    }


def _summarize_by_family(failures: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for item in failures:
        grouped[item["family"] or "(unknown)"][item["root_cause"]] += 1

    rows: list[dict[str, Any]] = []
    for family in sorted(grouped):
        counts = grouped[family]
        row: dict[str, Any] = {"family": family, "failed": sum(counts.values())}
        for root_cause in ROOT_CAUSES:
            row[root_cause] = counts.get(root_cause, 0)
        rows.append(row)
    return rows


def _summarize_by_root_cause(failures: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in failures:
        grouped[item["root_cause"]].append(item)

    rows: list[dict[str, Any]] = []
    for root_cause in ROOT_CAUSES:
        items = grouped.get(root_cause, [])
        rows.append(
            {
                "root_cause": root_cause,
                "count": len(items),
                "families": "; ".join(sorted({item["family"] or "(unknown)" for item in items})),
                "failure_types": "; ".join(sorted({item["failure_type"] or "(missing)" for item in items})),
                "case_ids": "; ".join(item["case_id"] for item in items),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_markdown(path: Path, summary: dict[str, Any]) -> None:
    report_summary = summary["report_summary"]
    browser_summary = summary["browser_summary"]
    model_usage = summary["model_usage"]
    lines = [
        "# LLM Failure Attribution",
        "",
        "## Summary",
        "",
        f"- total: {report_summary['total']}",
        f"- passed: {report_summary['passed']}",
        f"- failed: {report_summary['failed']}",
        f"- pass_rate: {report_summary['pass_rate']}",
        f"- failure_summary: `{json.dumps(report_summary['failure_summary'], ensure_ascii=False, sort_keys=True)}`",
        f"- root_cause_summary: `{json.dumps(summary['root_cause_summary'], ensure_ascii=False, sort_keys=True)}`",
        f"- browser_total: {browser_summary['browser_total']}",
        f"- browser_ok: {browser_summary['browser_ok']}",
        f"- browser_failed: {browser_summary['browser_failed']}",
        f"- model_usage: call_count={model_usage['call_count']}, total_tokens={model_usage['total_tokens']}, usage_available_rate={model_usage['usage_available_rate']}",
        "",
        "## Failures",
        "",
        "| case_id | family | subfamily_id | failure_type | root_cause | error_summary |",
        "|---|---|---|---|---|---|",
    ]
    for item in summary["failures"]:
        lines.append(
            "| {case_id} | {family} | {subfamily_id} | {failure_type} | {root_cause} | {error_summary} |".format(
                **{key: _escape_md_cell(value) for key, value in item.items()}
            )
        )
    lines.extend(
        [
            "",
            "## By Root Cause",
            "",
            "| root_cause | count | families | failure_types | case_ids |",
            "|---|---:|---|---|---|",
        ]
    )
    for row in summary["summary_by_root_cause"]:
        lines.append(
            f"| {_escape_md_cell(row['root_cause'])} | {row['count']} | {_escape_md_cell(row['families'])} | {_escape_md_cell(row['failure_types'])} | {_escape_md_cell(row['case_ids'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _escape_md_cell(value: Any) -> str:
    return _compact_text(value).replace("|", "\\|")


def analyze_report(report_path: Path | str, output_dir: Path | str) -> dict[str, Any]:
    report_path = Path(report_path)
    output_dir = Path(output_dir)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = [_failure_record(item) for item in report.get("results", []) if not item.get("ok")]
    root_cause_summary = Counter(item["root_cause"] for item in failures)
    summary_by_family = _summarize_by_family(failures)
    summary_by_root_cause = _summarize_by_root_cause(failures)
    summary = {
        "kind": "failure_attribution_report",
        "source_report": str(report_path),
        "root_cause_enum": list(ROOT_CAUSES),
        "report_summary": {
            "total": report.get("total", len(report.get("results", []))),
            "passed": report.get("passed", 0),
            "failed": report.get("failed", len(failures)),
            "pass_rate": report.get("pass_rate", 0),
            "failure_summary": report.get("failure_summary", {}),
        },
        "browser_summary": _browser_summary(report),
        "model_usage": _model_usage(report),
        "root_cause_summary": {root_cause: root_cause_summary.get(root_cause, 0) for root_cause in ROOT_CAUSES},
        "summary_by_family": summary_by_family,
        "summary_by_root_cause": summary_by_root_cause,
        "failures": failures,
    }

    (output_dir / "failure_attribution.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(output_dir / "failure_attribution.md", summary)
    _write_csv(
        output_dir / "failure_attribution_by_family.csv",
        summary_by_family,
        ["family", "failed", *ROOT_CAUSES],
    )
    _write_csv(
        output_dir / "failure_attribution_by_root_cause.csv",
        summary_by_root_cause,
        ["root_cause", "count", "families", "failure_types", "case_ids"],
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze failed cases in an LLM benchmark report.")
    parser.add_argument("--report", type=Path, required=True, help="Path to llm_benchmark_report.json")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for attribution outputs")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = analyze_report(args.report, args.output_dir)
    print(
        "failure_attribution: "
        f"failed={summary['report_summary']['failed']} "
        f"root_causes={json.dumps(summary['root_cause_summary'], ensure_ascii=False, sort_keys=True)}"
    )
    print(f"outputs: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
