"""Generate a clearly labeled synthetic LLM preview for the expert trace audit.

This output is workflow-test data. It must never be reported as human evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_STATUS = "SYNTHETIC_LLM_PREVIEW"
RESEARCH_USE = "workflow_preview_only_not_human_evidence"


def build_preview(
    cases: list[dict[str, Any]],
    *,
    count: int = 60,
    seed: int = 20260723,
) -> dict[str, Any]:
    """Build deterministic task-, variant-, and reviewer-level synthetic labels."""

    selected = _select_stratified(cases, count=count, seed=seed)
    ranked = sorted(
        selected,
        key=lambda row: (
            sum(int(value) for value in row["event_counts"]),
            _seeded_key(seed, str(row["case_id"])),
        ),
        reverse=True,
    )
    critical_case = str(ranked[0]["case_id"])
    minor_cases = {str(row["case_id"]) for row in ranked[1:3]}

    variant_rows: list[dict[str, Any]] = []
    for case in selected:
        case_id = str(case["case_id"])
        variant_ids = [str(value) for value in case["variant_ids"]]
        event_counts = [int(value) for value in case["event_counts"]]
        critical_variant = variant_ids[event_counts.index(max(event_counts))]
        minor_variant = variant_ids[0]
        for variant_id, event_count in zip(variant_ids, event_counts):
            is_critical = case_id == critical_case and variant_id == critical_variant
            is_minor = case_id in minor_cases and variant_id == minor_variant
            counts = _event_counts(
                event_count,
                seed=seed,
                identity=f"{case_id}:{variant_id}",
                elevated_source_issue=is_minor and case_id == sorted(minor_cases)[0],
                elevated_reason_issue=is_minor and case_id == sorted(minor_cases)[1],
                critical=is_critical,
            )
            variant_rows.append(
                {
                    "evidence_status": EVIDENCE_STATUS,
                    "research_use": RESEARCH_USE,
                    "case_id": case_id,
                    "title": str(case.get("title") or case_id),
                    "family_id": str(case["family_id"]),
                    "variant_id": variant_id,
                    "event_count": event_count,
                    **counts,
                    "strategy_fidelity": "fail" if is_critical else "pass",
                    "step_completeness": "pass",
                    "temporal_ordering": "pass",
                    "final_state_consistency": "fail" if is_critical else "pass",
                    "critical_semantic_error": "yes" if is_critical else "no",
                    "trace_perfect": "no" if is_critical or is_minor else "yes",
                    "simulated_issue": (
                        "wrong algorithmic state update"
                        if is_critical
                        else "non-critical source-line concentration"
                        if is_minor and case_id == sorted(minor_cases)[0]
                        else "non-critical explanation imprecision"
                        if is_minor
                        else ""
                    ),
                }
            )

    task_rows = _aggregate_tasks(selected, variant_rows)
    reviewer_rows = _simulate_reviewers(variant_rows, seed=seed)
    summary = _summarize(task_rows, variant_rows, reviewer_rows, seed=seed)
    return {
        "summary": summary,
        "task_rows": task_rows,
        "variant_rows": variant_rows,
        "reviewer_rows": reviewer_rows,
    }


def _select_stratified(
    cases: list[dict[str, Any]],
    *,
    count: int,
    seed: int,
) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cases:
        if len(row.get("variant_ids") or []) != 2:
            continue
        if len(row.get("event_counts") or []) != 2:
            continue
        by_family[str(row.get("family_id") or "unknown")].append(row)
    if len(by_family) != 23:
        raise ValueError(f"expected 23 families, got {len(by_family)}")
    selected: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    for family, rows in sorted(by_family.items()):
        ordered = sorted(
            rows,
            key=lambda row: _seeded_key(seed, f"{family}:{row['case_id']}"),
        )
        base_count = min(2, len(ordered))
        selected.extend(ordered[:base_count])
        remaining.extend(ordered[base_count:])
    if count < len(selected):
        raise ValueError(
            f"count {count} is smaller than the minimum family-coverage sample {len(selected)}"
        )
    remaining.sort(key=lambda row: _seeded_key(seed + 1, str(row["case_id"])))
    selected.extend(remaining[: count - len(selected)])
    if len(selected) != count:
        raise ValueError(f"not enough eligible tasks: requested {count}, got {len(selected)}")
    return sorted(selected, key=lambda row: _seeded_key(seed + 2, str(row["case_id"])))


def _event_counts(
    total: int,
    *,
    seed: int,
    identity: str,
    elevated_source_issue: bool,
    elevated_reason_issue: bool,
    critical: bool,
) -> dict[str, Any]:
    unit = int(_seeded_key(seed, identity)[:8], 16) / 0xFFFFFFFF
    unverifiable = min(total, int(round(total * (0.004 + 0.006 * unit))))
    wrong_rate = 0.012 + 0.008 * (1 - unit)
    adjacent_rate = 0.052 + 0.018 * unit
    if elevated_source_issue:
        wrong_rate += 0.09
    wrong = min(total - unverifiable, int(round(total * wrong_rate)))
    adjacent = min(total - unverifiable - wrong, int(round(total * adjacent_rate)))
    exact = total - unverifiable - wrong - adjacent

    reason_error_rate = 0.004 + 0.006 * unit
    if elevated_reason_issue:
        reason_error_rate += 0.10
    reason_inconsistent = min(total, int(round(total * reason_error_rate)))
    state_incorrect = 1 if critical else 0
    operation_incorrect = 1 if critical else 0
    return {
        "source_line_exact_count": exact,
        "source_line_adjacent_count": adjacent,
        "source_line_wrong_count": wrong,
        "source_line_unverifiable_count": unverifiable,
        "state_transition_correct_count": total - state_incorrect,
        "state_transition_incorrect_count": state_incorrect,
        "algorithmic_operation_correct_count": total - operation_incorrect,
        "algorithmic_operation_incorrect_count": operation_incorrect,
        "reason_state_consistent_count": total - reason_inconsistent,
        "reason_state_inconsistent_count": reason_inconsistent,
    }


def _aggregate_tasks(
    selected: list[dict[str, Any]],
    variant_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in variant_rows:
        by_case[str(row["case_id"])].append(row)
    meta = {str(row["case_id"]): row for row in selected}
    task_rows: list[dict[str, Any]] = []
    for case_id, variants in sorted(by_case.items()):
        event_count = sum(int(row["event_count"]) for row in variants)
        verifiable = event_count - sum(int(row["source_line_unverifiable_count"]) for row in variants)
        aligned = sum(
            int(row["source_line_exact_count"]) + int(row["source_line_adjacent_count"])
            for row in variants
        )
        reason_consistent = sum(int(row["reason_state_consistent_count"]) for row in variants)
        task_rows.append(
            {
                "evidence_status": EVIDENCE_STATUS,
                "research_use": RESEARCH_USE,
                "case_id": case_id,
                "title": str(meta[case_id].get("title") or case_id),
                "family_id": str(meta[case_id]["family_id"]),
                "variant_count": len(variants),
                "event_count": event_count,
                "trace_perfect_task": "yes" if all(row["trace_perfect"] == "yes" for row in variants) else "no",
                "critical_error_task": "yes" if any(row["critical_semantic_error"] == "yes" for row in variants) else "no",
                "source_line_exact_plus_adjacent_rate": _ratio(aligned, verifiable),
                "reason_state_consistency_rate": _ratio(reason_consistent, event_count),
                "simulated_issue": "; ".join(
                    row["simulated_issue"] for row in variants if row["simulated_issue"]
                ),
            }
        )
    return task_rows


def _simulate_reviewers(
    variant_rows: list[dict[str, Any]],
    *,
    seed: int,
) -> list[dict[str, Any]]:
    ordered = sorted(
        variant_rows,
        key=lambda row: _seeded_key(seed + 10, f"{row['case_id']}:{row['variant_id']}"),
    )
    final_nonperfect = {
        (str(row["case_id"]), str(row["variant_id"]))
        for row in variant_rows
        if row["trace_perfect"] == "no"
    }
    final_critical = {
        (str(row["case_id"]), str(row["variant_id"]))
        for row in variant_rows
        if row["critical_semantic_error"] == "yes"
    }
    clean = [
        (str(row["case_id"]), str(row["variant_id"]))
        for row in ordered
        if (str(row["case_id"]), str(row["variant_id"])) not in final_nonperfect
    ]
    a_extra_nonperfect = {clean[0]}
    b_extra_nonperfect = {clean[0], clean[1]}
    a_extra_critical = {clean[3]}

    rows: list[dict[str, Any]] = []
    for reviewer in ("A", "B"):
        for variant in ordered:
            key = (str(variant["case_id"]), str(variant["variant_id"]))
            trace_perfect = key not in final_nonperfect
            critical = key in final_critical
            if reviewer == "A" and key in a_extra_nonperfect:
                trace_perfect = False
            if reviewer == "B" and key in b_extra_nonperfect:
                trace_perfect = False
            if reviewer == "A" and key in a_extra_critical:
                critical = True
                trace_perfect = False
            rows.append(
                {
                    "evidence_status": EVIDENCE_STATUS,
                    "research_use": RESEARCH_USE,
                    "reviewer_id": f"LLM_SIM_{reviewer}",
                    "case_id": variant["case_id"],
                    "family_id": variant["family_id"],
                    "variant_id": variant["variant_id"],
                    "strategy_fidelity": "fail" if critical else "pass",
                    "step_completeness": "pass",
                    "temporal_ordering": "pass",
                    "final_state_consistency": "fail" if key in final_critical else "pass",
                    "critical_semantic_error": "yes" if critical else "no",
                    "trace_perfect": "yes" if trace_perfect else "no",
                    "notes": "LLM-simulated label; not produced by a human expert",
                }
            )
    return rows


def _summarize(
    task_rows: list[dict[str, Any]],
    variant_rows: list[dict[str, Any]],
    reviewer_rows: list[dict[str, Any]],
    *,
    seed: int,
) -> dict[str, Any]:
    task_count = len(task_rows)
    perfect_tasks = sum(row["trace_perfect_task"] == "yes" for row in task_rows)
    critical_tasks = sum(row["critical_error_task"] == "yes" for row in task_rows)
    perfect_variants = sum(row["trace_perfect"] == "yes" for row in variant_rows)
    total_events = sum(int(row["event_count"]) for row in variant_rows)
    source_verifiable = total_events - sum(
        int(row["source_line_unverifiable_count"]) for row in variant_rows
    )
    source_exact = sum(int(row["source_line_exact_count"]) for row in variant_rows)
    source_aligned = source_exact + sum(
        int(row["source_line_adjacent_count"]) for row in variant_rows
    )
    state_correct = sum(int(row["state_transition_correct_count"]) for row in variant_rows)
    operation_correct = sum(
        int(row["algorithmic_operation_correct_count"]) for row in variant_rows
    )
    reason_consistent = sum(int(row["reason_state_consistent_count"]) for row in variant_rows)
    source_macro = [float(row["source_line_exact_plus_adjacent_rate"]) for row in task_rows]
    source_ci = _bootstrap_mean_ci(source_macro, seed=seed + 30)

    by_reviewer: dict[str, dict[tuple[str, str], dict[str, Any]]] = defaultdict(dict)
    for row in reviewer_rows:
        by_reviewer[str(row["reviewer_id"])][
            (str(row["case_id"]), str(row["variant_id"]))
        ] = row
    keys = sorted(set.intersection(*(set(rows) for rows in by_reviewer.values())))
    left = by_reviewer["LLM_SIM_A"]
    right = by_reviewer["LLM_SIM_B"]
    trace_a = [left[key]["trace_perfect"] == "yes" for key in keys]
    trace_b = [right[key]["trace_perfect"] == "yes" for key in keys]
    critical_a = [left[key]["critical_semantic_error"] == "yes" for key in keys]
    critical_b = [right[key]["critical_semantic_error"] == "yes" for key in keys]
    disagreement_count = sum(
        trace_a[index] != trace_b[index] or critical_a[index] != critical_b[index]
        for index in range(len(keys))
    )

    task_ci = _wilson_interval(perfect_tasks, task_count)
    critical_upper = _clopper_pearson_one_sided_upper(critical_tasks, task_count)
    trace_kappa = _cohen_kappa(trace_a, trace_b)
    critical_kappa = _cohen_kappa(critical_a, critical_b)
    gate = {
        "trace_perfect_task_ci_lower_ge_0_90": task_ci[0] >= 0.90,
        "critical_error_upper_le_0_05": critical_upper <= 0.05,
        "source_exact_plus_adjacent_ci_lower_ge_0_90": source_ci[0] >= 0.90,
        "key_label_kappa_ge_0_60": min(trace_kappa or 0.0, critical_kappa or 0.0) >= 0.60,
    }
    gate["passed"] = all(gate.values())
    family_task_counts = Counter(str(row["family_id"]) for row in task_rows)
    return {
        "kind": "llm_simulated_expert_trace_audit_preview",
        "evidence_status": EVIDENCE_STATUS,
        "research_use": RESEARCH_USE,
        "warning": "Synthetic LLM preview only; do not report as human expert evidence.",
        "seed": seed,
        "task_count": task_count,
        "family_count": len({row["family_id"] for row in task_rows}),
        "family_task_counts": dict(sorted(family_task_counts.items())),
        "families_with_one_selected_task": sorted(
            family for family, family_count in family_task_counts.items() if family_count == 1
        ),
        "variant_count": len(variant_rows),
        "event_count": total_events,
        "trace_perfect_task_count": perfect_tasks,
        "trace_perfect_task_rate": _ratio(perfect_tasks, task_count),
        "trace_perfect_task_wilson_ci_95": task_ci,
        "critical_error_task_count": critical_tasks,
        "critical_error_task_rate": _ratio(critical_tasks, task_count),
        "critical_error_task_cp_one_sided_upper_95": critical_upper,
        "trace_perfect_variant_count": perfect_variants,
        "trace_perfect_variant_rate": _ratio(perfect_variants, len(variant_rows)),
        "source_line_exact_rate": _ratio(source_exact, source_verifiable),
        "source_line_exact_plus_adjacent_rate": _ratio(source_aligned, source_verifiable),
        "source_line_exact_plus_adjacent_task_macro_ci_95": source_ci,
        "state_transition_accuracy": _ratio(state_correct, total_events),
        "algorithmic_operation_accuracy": _ratio(operation_correct, total_events),
        "reason_state_consistency_rate": _ratio(reason_consistent, total_events),
        "reviewer_disagreement_count": disagreement_count,
        "reviewer_trace_perfect_raw_agreement": _agreement(trace_a, trace_b),
        "reviewer_trace_perfect_cohen_kappa": trace_kappa,
        "reviewer_critical_error_raw_agreement": _agreement(critical_a, critical_b),
        "reviewer_critical_error_cohen_kappa": critical_kappa,
        "strong_claim_gate": gate,
        "simulated_error_types": dict(
            Counter(row["simulated_issue"] for row in variant_rows if row["simulated_issue"])
        ),
    }


def load_cases(report_path: Path) -> list[dict[str, Any]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for row in report.get("results") or []:
        variants = list(row.get("variants") or [])
        if not row.get("ok") or len(variants) != 2:
            continue
        cases.append(
            {
                "case_id": str(row["case_id"]),
                "title": str(row.get("title") or row["case_id"]),
                "family_id": str(row.get("family_id") or "unknown"),
                "variant_ids": [str(variant.get("id") or f"v{index + 1}") for index, variant in enumerate(variants)],
                "event_counts": [int(variant.get("steps") or 0) for variant in variants],
            }
        )
    return cases


def write_preview(preview: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "simulated_task_results.csv", preview["task_rows"])
    _write_csv(output_dir / "simulated_variant_results.csv", preview["variant_rows"])
    _write_csv(output_dir / "simulated_reviewer_labels.csv", preview["reviewer_rows"])
    (output_dir / "simulation_summary.json").write_text(
        json.dumps(preview["summary"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")
    (output_dir / "simulation_report.md").write_text(
        _report(preview["summary"]), encoding="utf-8"
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["evidence_status"])
        writer.writeheader()
        writer.writerows(rows)


def _readme() -> str:
    return """# LLM-Simulated Expert Trace Audit Preview

> **SYNTHETIC_LLM_PREVIEW：这不是人工专家评估结果。**

本目录只用于预演 `Expert Audit of Algorithmic Trace Fidelity` 的数据结构、统计表和论文呈现方式。数据由固定 seed 模拟生成，不得写成“专家发现”“人工审计证明”或与真实人工标签合并。

- `simulated_task_results.csv`：60 个模拟 task-level 结果；
- `simulated_variant_results.csv`：120 个模拟 variant-level 结果；
- `simulated_reviewer_labels.csv`：两位模拟 LLM reviewer 的 variant 标签；
- `simulation_summary.json`：汇总指标和门禁；
- `simulation_report.md`：可读结果说明。

真实论文证据必须由两位算法专家独立完成完整 trace 审计后另行生成。
"""


def _report(summary: dict[str, Any]) -> str:
    task_ci = summary["trace_perfect_task_wilson_ci_95"]
    source_ci = summary["source_line_exact_plus_adjacent_task_macro_ci_95"]
    gate = summary["strong_claim_gate"]
    return f"""# LLM 模拟预评估结果

> **SYNTHETIC_LLM_PREVIEW：以下数据不是人工专家结果，只能用于流程预演。**

模拟样本包含 {summary['task_count']} 个任务、{summary['family_count']} 个算法族、{summary['variant_count']} 条 traces 和 {summary['event_count']} 个事件。

| 指标 | 模拟结果 | 区间/上界 |
| --- | --- | --- |
| Trace-perfect task | {summary['trace_perfect_task_count']}/{summary['task_count']}（{_percent(summary['trace_perfect_task_rate'])}） | Wilson 95% CI [{_percent(task_ci[0])}, {_percent(task_ci[1])}] |
| Critical-error task | {summary['critical_error_task_count']}/{summary['task_count']}（{_percent(summary['critical_error_task_rate'])}） | 单侧95%上界 {_percent(summary['critical_error_task_cp_one_sided_upper_95'])} |
| Trace-perfect variant | {summary['trace_perfect_variant_count']}/{summary['variant_count']}（{_percent(summary['trace_perfect_variant_rate'])}） | 描述性 |
| Source-line exact | {_percent(summary['source_line_exact_rate'])} | 描述性 |
| Source-line exact+adjacent | {_percent(summary['source_line_exact_plus_adjacent_rate'])} | task-macro 95% CI [{_percent(source_ci[0])}, {_percent(source_ci[1])}] |
| State-transition accuracy | {_percent(summary['state_transition_accuracy'], digits=2)} | 描述性 |
| Algorithmic-operation accuracy | {_percent(summary['algorithmic_operation_accuracy'], digits=2)} | 描述性 |
| Reason-state consistency | {_percent(summary['reason_state_consistency_rate'])} | 描述性 |

模拟双评审的 trace-perfect 原始一致率为 {_percent(summary['reviewer_trace_perfect_raw_agreement'])}，Cohen's κ={summary['reviewer_trace_perfect_cohen_kappa']:.3f}；critical-error 原始一致率为 {_percent(summary['reviewer_critical_error_raw_agreement'])}，κ={summary['reviewer_critical_error_cohen_kappa']:.3f}。

本次模拟故意保留 1 个关键错误任务以及少量 source-line、解释一致性问题。严格门禁结果为 **{'PASS' if gate['passed'] else 'FAIL'}**：它展示了总体结果较好，但 60 题中出现 1 个关键错误后，关键错误率单侧95%上界无法压到5%以内，因此不能据此使用最强正确性表述。
"""


def _bootstrap_mean_ci(values: list[float], *, seed: int, repetitions: int = 10_000) -> list[float]:
    rng = random.Random(seed)
    means = []
    for _ in range(repetitions):
        means.append(sum(rng.choice(values) for _ in values) / len(values))
    means.sort()
    return [round(means[int(0.025 * repetitions)], 12), round(means[int(0.975 * repetitions) - 1], 12)]


def _wilson_interval(successes: int, total: int) -> list[float]:
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    ) / denominator
    return [round(max(0.0, center - radius), 12), round(min(1.0, center + radius), 12)]


def _clopper_pearson_one_sided_upper(successes: int, total: int, alpha: float = 0.05) -> float:
    if successes >= total:
        return 1.0
    low = successes / total
    high = 1.0
    for _ in range(100):
        middle = (low + high) / 2
        cdf = sum(
            math.comb(total, index) * middle**index * (1 - middle) ** (total - index)
            for index in range(successes + 1)
        )
        if cdf > alpha:
            low = middle
        else:
            high = middle
    return round((low + high) / 2, 12)


def _cohen_kappa(left: list[bool], right: list[bool]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    observed = _agreement(left, right)
    left_positive = sum(left) / len(left)
    right_positive = sum(right) / len(right)
    expected = left_positive * right_positive + (1 - left_positive) * (1 - right_positive)
    if expected == 1.0:
        return None
    return round((observed - expected) / (1 - expected), 12)


def _agreement(left: list[bool], right: list[bool]) -> float:
    return _ratio(sum(a == b for a, b in zip(left, right)), len(left))


def _seeded_key(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 12) if denominator else 0.0


def _percent(value: float, *, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT
        / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20260723)
    args = parser.parse_args()
    preview = build_preview(load_cases(args.report), count=args.count, seed=args.seed)
    write_preview(preview, args.output_dir)
    print(json.dumps(preview["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
