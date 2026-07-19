"""Merge HTMLCure shards and analyze paired behavior-audit results."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BOOL_KEYS = [
    "page_load_ok",
    "visible_answer_match",
    "interaction_reachable",
    "correct_feedback_ok",
    "wrong_feedback_ok",
    "hint_ok",
    "show_answer_ok",
    "learning_log_ok",
    "mutation_free_ok",
]


def exact_mcnemar_pvalue(discordant_a: int, discordant_b: int) -> float:
    """Return the two-sided exact McNemar p-value."""
    n = discordant_a + discordant_b
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(discordant_a, discordant_b) + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def path(value: str | Path) -> Path:
    item = Path(value)
    return item if item.is_absolute() else ROOT / item


def load(value: str | Path) -> dict[str, Any]:
    return json.loads(path(value).read_text(encoding="utf-8"))


def merge(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load(args.manifest)
    order = [item["case_id"] for item in manifest["cases"]]
    by_case: dict[str, dict[str, Any]] = {}
    shard_reports = []
    for shard in args.shard_report:
        report = load(shard)
        shard_reports.append(report)
        for row in report.get("results") or []:
            by_case[str(row["case_id"])] = row
    missing = [case_id for case_id in order if case_id not in by_case]
    if missing:
        raise ValueError(f"Missing shard results: {missing}")
    records = [by_case[case_id] for case_id in order]
    merged = {
        "kind": "direct_htmlcure_baseline_report",
        "created_at": datetime.now().astimezone().isoformat(),
        "manifest": str(path(args.manifest).relative_to(ROOT)),
        "htmlcure_commit": shard_reports[0].get("htmlcure_commit"),
        "mode": shard_reports[0].get("mode"),
        "repair_model": shard_reports[0].get("repair_model"),
        "evaluator_model": shard_reports[0].get("evaluator_model"),
        "max_iterations": shard_reports[0].get("max_iterations"),
        "vision_in_repair": shard_reports[0].get("vision_in_repair"),
        "browser_use_agent": shard_reports[0].get("browser_use_agent"),
        "parallel_shards": len(shard_reports),
        "sum_case_duration_s": round(sum(float(row.get("duration_s") or 0) for row in records), 3),
        "wall_duration_s": round(max(float(item.get("duration_s") or 0) for item in shard_reports), 3),
        "results": records,
    }
    output = path(args.output_report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def analyze(args: argparse.Namespace, merged: dict[str, Any]) -> dict[str, Any]:
    original = load(args.original_audit)
    repaired = load(args.repaired_audit)
    wanted = {row["case_id"] for row in merged["results"]}
    before = {
        row["case_id"]: row
        for row in original.get("records") or []
        if row.get("condition") == "direct_html" and row.get("case_id") in wanted
    }
    after = {
        row["case_id"]: row
        for row in repaired.get("records") or []
        if row.get("condition") == "direct_html" and row.get("case_id") in wanted
    }
    if set(before) != wanted or set(after) != wanted:
        raise ValueError("Behavior audit does not cover all manifest cases")

    transitions = {"fail_to_pass": [], "pass_to_fail": [], "pass_to_pass": [], "fail_to_fail": []}
    paired = []
    for repair_row in merged["results"]:
        case_id = repair_row["case_id"]
        old = before[case_id]
        new = after[case_id]
        old_ok = bool(old.get("machine_ok"))
        new_ok = bool(new.get("machine_ok"))
        non_resource_errors = [
            error for error in new.get("console_page_errors") or []
            if not (
                "Failed to load resource" in error
                and ("ERR_ADDRESS_UNREACHABLE" in error or "ERR_CONNECTION_TIMED_OUT" in error)
            )
        ]
        behavior_ok_ignoring_resource_errors = not non_resource_errors and all(
            new.get(metric) is True for metric in BOOL_KEYS if metric != "page_load_ok"
        )
        key = ("pass" if old_ok else "fail") + "_to_" + ("pass" if new_ok else "fail")
        transitions[key].append(case_id)
        paired.append(
            {
                "case_id": case_id,
                "before_machine_ok": old_ok,
                "after_machine_ok": new_ok,
                "behavior_ok_ignoring_resource_errors": behavior_ok_ignoring_resource_errors,
                "htmlcure_original_score": repair_row.get("htmlcure_original_score"),
                "htmlcure_final_score": repair_row.get("htmlcure_final_score"),
                "htmlcure_improvement": repair_row.get("htmlcure_improvement"),
                "htmlcure_accepted_change": bool((repair_row.get("htmlcure_improvement") or 0) > 0),
                "before_failed": [key for key in BOOL_KEYS if not old.get(key)],
                "after_failed": [key for key in BOOL_KEYS if not new.get(key)],
                "improved_metrics": [key for key in BOOL_KEYS if not old.get(key) and new.get(key)],
                "regressed_metrics": [key for key in BOOL_KEYS if old.get(key) and not new.get(key)],
                "duration_s": repair_row.get("duration_s"),
                "repair_llm_calls": repair_row.get("htmlcure_repair_llm_calls", 0),
            }
        )

    metric_summary = {}
    for key in BOOL_KEYS:
        before_n = sum(bool(before[case_id].get(key)) for case_id in wanted)
        after_n = sum(bool(after[case_id].get(key)) for case_id in wanted)
        fail_to_pass = sum(
            not bool(before[case_id].get(key)) and bool(after[case_id].get(key))
            for case_id in wanted
        )
        pass_to_fail = sum(
            bool(before[case_id].get(key)) and not bool(after[case_id].get(key))
            for case_id in wanted
        )
        metric_summary[key] = {
            "before": before_n,
            "after": after_n,
            "delta": after_n - before_n,
            "fail_to_pass": fail_to_pass,
            "pass_to_fail": pass_to_fail,
            "mcnemar_exact_p": exact_mcnemar_pvalue(fail_to_pass, pass_to_fail),
        }
    accepted = [row for row in paired if row["htmlcure_accepted_change"]]
    summary = {
        "total": len(wanted),
        "before_machine_ok": sum(bool(row.get("machine_ok")) for row in before.values()),
        "after_machine_ok": sum(bool(row.get("machine_ok")) for row in after.values()),
        "machine_ok_delta": sum(bool(row.get("machine_ok")) for row in after.values())
        - sum(bool(row.get("machine_ok")) for row in before.values()),
        "after_behavior_ok_ignoring_resource_errors": sum(
            row["behavior_ok_ignoring_resource_errors"] for row in paired
        ),
        "transitions": transitions,
        "htmlcure_accepted_changes": len(accepted),
        "htmlcure_rejected_or_unchanged": len(paired) - len(accepted),
        "total_repair_llm_candidates": sum(int(row["repair_llm_calls"] or 0) for row in paired),
        "wall_duration_s": merged.get("wall_duration_s"),
        "sum_case_duration_s": merged.get("sum_case_duration_s"),
        "metric_summary": metric_summary,
        "machine_ok_mcnemar_exact_p": exact_mcnemar_pvalue(
            len(transitions["fail_to_pass"]), len(transitions["pass_to_fail"])
        ),
    }
    report = {
        "kind": "htmlcure_smoke_analysis",
        "created_at": datetime.now().astimezone().isoformat(),
        "summary": summary,
        "paired_records": paired,
    }
    output = path(args.output_analysis)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    is_full = summary["total"] == 200
    lines = [
        "# Direct + HTMLCure Full Analysis" if is_full else "# Direct + HTMLCure Smoke Analysis",
        "",
        f"- Cases: `{summary['total']}`" + (
            " (full benchmark, sample 0 per case)"
            if is_full else " (diagnostic balanced sample, not a full-200 estimator)"
        ),
        f"- Machine OK: `{summary['before_machine_ok']}/{summary['total']}` -> `{summary['after_machine_ok']}/{summary['total']}`",
        f"- Behavior OK ignoring external-resource load errors: `{summary['after_behavior_ok_ignoring_resource_errors']}/{summary['total']}`",
        f"- HTMLCure-accepted changes: `{summary['htmlcure_accepted_changes']}/{summary['total']}`",
        f"- Repair candidates: `{summary['total_repair_llm_candidates']}`",
        f"- Generation wall time: `{summary['wall_duration_s']}s`",
        "",
        "## Metric Changes",
        "",
        "| Metric | Before | After | Delta | Fail -> pass | Pass -> fail | Exact McNemar p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, item in metric_summary.items():
        lines.append(
            f"| {key} | {item['before']} | {item['after']} | {item['delta']:+d} | "
            f"{item['fail_to_pass']} | {item['pass_to_fail']} | {item['mcnemar_exact_p']:.6g} |"
        )
    lines.extend(
        [
            "",
            "## Case Transitions",
            "",
            f"- Fail -> pass: `{json.dumps(transitions['fail_to_pass'], ensure_ascii=False)}`",
            f"- Pass -> fail: `{json.dumps(transitions['pass_to_fail'], ensure_ascii=False)}`",
            f"- Pass -> pass: `{json.dumps(transitions['pass_to_pass'], ensure_ascii=False)}`",
            f"- Fail -> fail: `{json.dumps(transitions['fail_to_fail'], ensure_ascii=False)}`",
            "",
            "## Per Case",
            "",
            "| Case | Machine OK | HTMLCure score | Improved metrics | Regressed metrics |",
            "|---|---|---|---|---|",
        ]
    )
    for row in paired:
        lines.append(
            f"| {row['case_id']} | {row['before_machine_ok']} -> {row['after_machine_ok']} | "
            f"{row['htmlcure_original_score']} -> {row['htmlcure_final_score']} | "
            f"{', '.join(row['improved_metrics']) or '-'} | {', '.join(row['regressed_metrics']) or '-'} |"
        )
    path(args.output_markdown).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--shard-report", action="append", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--merge-only", action="store_true")
    parser.add_argument("--original-audit")
    parser.add_argument("--repaired-audit")
    parser.add_argument("--output-analysis")
    parser.add_argument("--output-markdown")
    args = parser.parse_args()
    merged = merge(args)
    if args.merge_only:
        print(json.dumps({"merged": len(merged["results"])}, ensure_ascii=False))
        return 0
    required = [args.original_audit, args.repaired_audit, args.output_analysis, args.output_markdown]
    if not all(required):
        parser.error("analysis mode requires both audit inputs and both analysis outputs")
    report = analyze(args, merged)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
