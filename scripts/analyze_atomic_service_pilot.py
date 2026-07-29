"""Analyze the paired 23-family Atomic versus Decoupled service pilot."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_paired_experiments import holm_adjust, paired_binary_summary


CONTROLLED_CONFIG_FIELDS = (
    "solutions",
    "max_rounds",
    "max_candidates",
    "timeout_s",
    "strict_warnings",
    "browser_smoke",
    "teaching_enrichment",
    "case_set",
    "language",
    "prompt_profile",
    "model",
    "llm",
)

BINARY_METRICS = (
    "final_generation_pass",
    "machine_ok",
    "execution_validation",
    "execution_binding",
    "prefix_replay",
    "unlogged_mutation_free",
    "state_event_mismatch_free",
)


def _index(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError(f"{label}: missing case_id")
        if case_id in indexed:
            raise ValueError(f"{label}: duplicate case_id {case_id}")
        indexed[case_id] = row
    return indexed


def _same_ids(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    expected_pairs: int,
    label: str,
) -> list[str]:
    if set(left) != set(right):
        raise ValueError(
            f"{label}: unmatched case IDs; "
            f"missing_left={sorted(set(right) - set(left))[:10]} "
            f"missing_right={sorted(set(left) - set(right))[:10]}"
        )
    if len(left) != expected_pairs:
        raise ValueError(f"{label}: expected {expected_pairs} pairs, found {len(left)}")
    return sorted(left)


def _validate_config(atomic: dict[str, Any], decoupled: dict[str, Any]) -> dict[str, Any]:
    if atomic.get("execution_mode") != "atomic":
        raise ValueError("atomic report config does not declare execution_mode=atomic")
    if decoupled.get("execution_mode") != "decoupled":
        raise ValueError("decoupled report config does not declare execution_mode=decoupled")
    comparisons = {}
    mismatches = []
    for field in CONTROLLED_CONFIG_FIELDS:
        left = atomic.get(field)
        right = decoupled.get(field)
        match = left == right
        comparisons[field] = {"atomic": left, "decoupled": right, "match": match}
        if not match:
            mismatches.append(field)
    if mismatches:
        raise ValueError("controlled configuration mismatch: " + ", ".join(mismatches))
    return {
        "all_controlled_fields_match": True,
        "controlled_fields": comparisons,
        "declared_difference": "execution_mode and its frozen prompt appendix",
    }


def _machine_index(report: dict[str, Any], condition: str) -> dict[str, dict[str, Any]]:
    return _index(
        [row for row in report.get("records") or [] if row.get("condition") == condition],
        label=f"machine {condition}",
    )


def _execution_validations(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item["execution_validation"]
        for item in row.get("variants") or []
        if isinstance(item.get("execution_validation"), dict)
        and item["execution_validation"]
    ]


def _evidence_metric(row: dict[str, Any], metric: str) -> bool | None:
    validations = _execution_validations(row)
    if not validations:
        return None
    if metric == "execution_validation":
        return all(item.get("ok") is True for item in validations)
    if metric == "execution_binding":
        return all(item.get("same_execution_binding") is True for item in validations)
    if metric == "prefix_replay":
        return all(item.get("prefix_replay_ok") is True for item in validations)
    if metric == "unlogged_mutation_free":
        return all(int(item.get("unlogged_mutation_count") or 0) == 0 for item in validations)
    if metric == "state_event_mismatch_free":
        return all(int(item.get("state_event_mismatch_count") or 0) == 0 for item in validations)
    raise KeyError(metric)


def _usage(row: dict[str, Any]) -> dict[str, float | int]:
    calls = row.get("model_calls") or []
    prompt = completion = total = 0
    duration = 0.0
    for index, call in enumerate(calls):
        if call.get("usage_available") is not True:
            raise ValueError(f"{row.get('case_id')} model call {index}: usage unavailable")
        values = [call.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens")]
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
            raise ValueError(f"{row.get('case_id')} model call {index}: invalid token usage")
        if values[0] + values[1] != values[2]:
            raise ValueError(f"{row.get('case_id')} model call {index}: token total mismatch")
        prompt += values[0]
        completion += values[1]
        total += values[2]
        duration += float(call.get("duration_s") or 0.0)
    return {
        "model_calls": len(calls),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "api_latency_seconds": duration,
        "repair_calls": sum(call.get("kind") == "repair" for call in calls),
    }


def _condition_summary(
    rows: dict[str, dict[str, Any]],
    machine_rows: dict[str, dict[str, Any]],
    case_ids: list[str],
) -> dict[str, Any]:
    usages = [_usage(rows[case_id]) for case_id in case_ids]
    total = lambda key: sum(float(item[key]) for item in usages)
    cases = len(case_ids)
    passed = sum(rows[case_id].get("ok") is True for case_id in case_ids)
    machine_passed = sum(
        machine_rows[case_id].get("machine_ok") is True for case_id in case_ids
    )
    return {
        "cases": cases,
        "generation_pass": passed,
        "generation_pass_rate": passed / cases,
        "machine_ok": machine_passed,
        "machine_ok_rate": machine_passed / cases,
        "model_calls": int(total("model_calls")),
        "model_calls_per_task": total("model_calls") / cases,
        "repair_calls": int(total("repair_calls")),
        "repair_calls_per_task": total("repair_calls") / cases,
        "prompt_tokens": int(total("prompt_tokens")),
        "completion_tokens": int(total("completion_tokens")),
        "total_tokens": int(total("total_tokens")),
        "tokens_per_task": total("total_tokens") / cases,
        "tokens_per_generation_pass": total("total_tokens") / passed if passed else None,
        "tokens_per_machine_ok": total("total_tokens") / machine_passed if machine_passed else None,
        "tokens_per_valid_tutor": total("total_tokens") / machine_passed if machine_passed else None,
        "api_latency_seconds": total("api_latency_seconds"),
        "api_latency_seconds_per_task": total("api_latency_seconds") / cases,
        "end_to_end_seconds_per_task": statistics.fmean(
            float(rows[case_id].get("duration_s") or 0.0) for case_id in case_ids
        ),
    }


def _paired_continuous(
    atomic: list[float],
    decoupled: list[float],
    *,
    seed: int,
    draws: int,
) -> dict[str, Any]:
    diffs = np.asarray(atomic, dtype=float) - np.asarray(decoupled, dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(diffs), size=(draws, len(diffs)))
    boot = diffs[indices].mean(axis=1)
    low, high = np.quantile(boot, [0.025, 0.975]).tolist()
    return {
        "pairs": len(diffs),
        "atomic_mean": float(np.mean(atomic)),
        "decoupled_mean": float(np.mean(decoupled)),
        "mean_difference": float(np.mean(diffs)),
        "bootstrap_ci_95": [float(low), float(high)],
    }


def build_atomic_service_pilot_report(
    atomic_report: dict[str, Any],
    decoupled_report: dict[str, Any],
    atomic_machine_report: dict[str, Any],
    decoupled_machine_report: dict[str, Any],
    *,
    expected_pairs: int = 23,
    seed: int = 20260725,
    draws: int = 10_000,
    exclude_case_ids: set[str] | None = None,
) -> dict[str, Any]:
    config_parity = _validate_config(
        atomic_report.get("config") or {}, decoupled_report.get("config") or {}
    )
    atomic = _index(atomic_report.get("results") or [], label="atomic generation")
    decoupled = _index(decoupled_report.get("results") or [], label="decoupled generation")
    case_ids = _same_ids(
        atomic, decoupled, expected_pairs=expected_pairs, label="generation"
    )
    atomic_machine = _machine_index(atomic_machine_report, "atomic_service")
    decoupled_machine = _machine_index(decoupled_machine_report, "decoupled_service")
    machine_ids = _same_ids(
        atomic_machine,
        decoupled_machine,
        expected_pairs=expected_pairs,
        label="machine",
    )
    if machine_ids != case_ids:
        raise ValueError("generation and machine reports have unmatched case IDs")

    binary: dict[str, dict[str, Any]] = {}
    mechanism_observability: dict[str, dict[str, Any]] = {}
    for metric in BINARY_METRICS:
        if metric == "final_generation_pass":
            left = [atomic[case_id].get("ok") is True for case_id in case_ids]
            right = [decoupled[case_id].get("ok") is True for case_id in case_ids]
        elif metric == "machine_ok":
            left = [atomic_machine[case_id].get("machine_ok") is True for case_id in case_ids]
            right = [decoupled_machine[case_id].get("machine_ok") is True for case_id in case_ids]
        else:
            atomic_values = {
                case_id: _evidence_metric(atomic[case_id], metric) for case_id in case_ids
            }
            decoupled_values = {
                case_id: _evidence_metric(decoupled[case_id], metric) for case_id in case_ids
            }
            eligible = [
                case_id
                for case_id in case_ids
                if atomic_values[case_id] is not None and decoupled_values[case_id] is not None
            ]
            left = [bool(atomic_values[case_id]) for case_id in eligible]
            right = [bool(decoupled_values[case_id]) for case_id in eligible]
            mechanism_observability[metric] = {
                "atomic_observed": sum(value is not None for value in atomic_values.values()),
                "atomic_pass": sum(value is True for value in atomic_values.values()),
                "decoupled_observed": sum(value is not None for value in decoupled_values.values()),
                "decoupled_pass": sum(value is True for value in decoupled_values.values()),
                "paired_observed": len(eligible),
            }
        binary[metric] = paired_binary_summary(left, right, seed=seed, draws=draws)

    secondary_names = [name for name in BINARY_METRICS if name != "machine_ok"]
    adjusted = holm_adjust(
        {name: float(binary[name]["mcnemar_exact_p"]) for name in secondary_names}
    )
    for name, value in adjusted.items():
        binary[name]["holm_adjusted_p"] = value

    atomic_usage = [_usage(atomic[case_id]) for case_id in case_ids]
    decoupled_usage = [_usage(decoupled[case_id]) for case_id in case_ids]
    continuous = {}
    for metric in ("model_calls", "repair_calls", "total_tokens", "api_latency_seconds"):
        continuous[metric] = _paired_continuous(
            [float(row[metric]) for row in atomic_usage],
            [float(row[metric]) for row in decoupled_usage],
            seed=seed,
            draws=draws,
        )
    continuous["end_to_end_seconds"] = _paired_continuous(
        [float(atomic[case_id].get("duration_s") or 0.0) for case_id in case_ids],
        [float(decoupled[case_id].get("duration_s") or 0.0) for case_id in case_ids],
        seed=seed,
        draws=draws,
    )
    report = {
        "kind": "atomic_service_pilot",
        "schema_version": "atomic-service-pilot-v1",
        "difference_direction": "atomic_minus_decoupled",
        "pair_completeness": len(case_ids),
        "case_ids": case_ids,
        "configuration_parity": config_parity,
        "conditions": {
            "atomic": _condition_summary(atomic, atomic_machine, case_ids),
            "decoupled": _condition_summary(decoupled, decoupled_machine, case_ids),
        },
        "binary_metrics": binary,
        "mechanism_observability": mechanism_observability,
        "continuous_metrics": continuous,
        "bootstrap": {"seed": seed, "draws": draws, "unit": "case"},
    }
    excluded = {str(case_id) for case_id in (exclude_case_ids or set())}
    if excluded:
        unknown = excluded - set(case_ids)
        if unknown:
            raise ValueError("excluded case IDs are not present: " + ", ".join(sorted(unknown)))
        remaining = set(case_ids) - excluded

        def filter_generation(source: dict[str, Any]) -> dict[str, Any]:
            return {
                **source,
                "results": [
                    row for row in source.get("results") or [] if row.get("case_id") in remaining
                ],
            }

        def filter_machine(source: dict[str, Any]) -> dict[str, Any]:
            return {
                **source,
                "records": [
                    row for row in source.get("records") or [] if row.get("case_id") in remaining
                ],
            }

        report["excluded_case_ids"] = sorted(excluded)
        report["sensitivity_excluding_cases"] = build_atomic_service_pilot_report(
            filter_generation(atomic_report),
            filter_generation(decoupled_report),
            filter_machine(atomic_machine_report),
            filter_machine(decoupled_machine_report),
            expected_pairs=len(remaining),
            seed=seed,
            draws=draws,
        )
    return report


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    def append_binary_table(lines: list[str], title: str, section: dict[str, Any]) -> None:
        lines.extend(
            [
                f"## {title}",
                "",
                "| Metric | Atomic | Decoupled | Difference (pp) | 95% bootstrap CI (pp) | McNemar p |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for metric, row in section["binary_metrics"].items():
            ci = row["bootstrap_ci_95"]
            lines.append(
                f"| {metric} | {row['a_pass']}/{row['pairs']} | {row['b_pass']}/{row['pairs']} | "
                f"{row['difference'] * 100:.2f} | [{ci[0] * 100:.2f}, {ci[1] * 100:.2f}] | "
                f"{row['mcnemar_exact_p']:.6g} |"
            )

    lines = [
        f"# Atomic-Service Full-{report['pair_completeness']}",
        "",
        f"配对样本：{report['pair_completeness']}；差值方向：Atomic - Decoupled。",
        "",
    ]
    append_binary_table(lines, "主结果", report)
    lines.extend(
        [
            "",
            "## 成本与延迟",
            "",
            "| Condition | Generation pass | Machine OK | Tokens/task | Tokens/valid tutor | Model calls/task | Repair calls/task | API latency/task |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for condition, row in report["conditions"].items():
        valid_cost = row["tokens_per_valid_tutor"]
        lines.append(
            f"| {condition} | {row['generation_pass']}/{row['cases']} | {row['machine_ok']}/{row['cases']} | {row['tokens_per_task']:.1f} | "
            f"{valid_cost:.1f} | {row['model_calls_per_task']:.3f} | "
            f"{row['repair_calls_per_task']:.3f} | {row['api_latency_seconds_per_task']:.1f}s |"
            if valid_cost is not None
            else f"| {condition} | {row['generation_pass']}/{row['cases']} | {row['machine_ok']}/{row['cases']} | {row['tokens_per_task']:.1f} | n/a | "
            f"{row['model_calls_per_task']:.3f} | {row['repair_calls_per_task']:.3f} | "
            f"{row['api_latency_seconds_per_task']:.1f}s |"
        )
    sensitivity = report.get("sensitivity_excluding_cases")
    if sensitivity:
        lines.extend(["", f"排除 Pilot 的 {len(report.get('excluded_case_ids') or [])} 个 case 后："])
        append_binary_table(lines, f"敏感性分析（{sensitivity['pair_completeness']} 对）", sensitivity)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atomic-report", type=Path, required=True)
    parser.add_argument("--decoupled-report", type=Path, required=True)
    parser.add_argument("--atomic-machine-report", type=Path, required=True)
    parser.add_argument("--decoupled-machine-report", type=Path, required=True)
    parser.add_argument("--expected-pairs", type=int, default=23)
    parser.add_argument("--exclude-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    exclude_case_ids: set[str] | None = None
    if args.exclude_manifest is not None:
        manifest = load(args.exclude_manifest)
        exclude_case_ids = {str(case_id) for case_id in manifest.get("case_ids") or []}
        if not exclude_case_ids:
            raise ValueError("exclude manifest has no case_ids")
    report = build_atomic_service_pilot_report(
        load(args.atomic_report),
        load(args.decoupled_report),
        load(args.atomic_machine_report),
        load(args.decoupled_machine_report),
        expected_pairs=args.expected_pairs,
        exclude_case_ids=exclude_case_ids,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown(args.output.with_suffix(".md"), report)
    with args.output.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["analysis_set", "metric", "atomic_pass", "decoupled_pass", "difference", "ci_low", "ci_high", "mcnemar_p"],
        )
        writer.writeheader()
        sections = [("full200", report)]
        if report.get("sensitivity_excluding_cases"):
            sections.append(("excluding_pilot", report["sensitivity_excluding_cases"]))
        for analysis_set, section in sections:
            for metric, row in section["binary_metrics"].items():
                writer.writerow(
                    {
                        "analysis_set": analysis_set,
                        "metric": metric,
                        "atomic_pass": row["a_pass"],
                        "decoupled_pass": row["b_pass"],
                        "difference": row["difference"],
                        "ci_low": row["bootstrap_ci_95"][0],
                        "ci_high": row["bootstrap_ci_95"][1],
                        "mcnemar_p": row["mcnemar_exact_p"],
                    }
                )
    print(json.dumps({"output": str(args.output), "pairs": report["pair_completeness"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
