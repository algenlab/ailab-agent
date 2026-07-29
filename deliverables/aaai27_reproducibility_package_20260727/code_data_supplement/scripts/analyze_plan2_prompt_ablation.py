#!/usr/bin/env python3
"""Paired statistics for Plan-2 hybrid_current versus service_only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_paired_experiments import holm_adjust, paired_binary_summary


MACHINE_METRICS = (
    "machine_ok",
    "page_load_ok",
    "visible_answer_match",
    "interaction_reachable",
    "correct_feedback_ok",
    "wrong_feedback_ok",
    "hint_ok",
    "show_answer_ok",
    "learning_log_ok",
    "mutation_free_ok",
)

CONTROLLED_CONFIG_FIELDS = (
    "sample",
    "solutions",
    "max_rounds",
    "max_candidates",
    "timeout_s",
    "strict_warnings",
    "browser_smoke",
    "teaching_enrichment",
    "write_each",
    "concurrency",
    "case_set",
    "language",
    "benchmark_condition",
    "case_overrides",
    "model",
    "llm.max_tokens",
    "llm.timeout_s",
    "llm.json_retries",
    "llm.api_retries",
    "llm.json_temperature",
)

INFRASTRUCTURE_FAILURE_TYPES = {
    "configuration",
    "runner_error",
    "api_transport",
    "infrastructure_timeout",
}

PAIRED_PAYLOAD_FIELDS = (
    "case_id",
    "problem",
    "strategy",
    "input_data",
    "expected",
    "sample_index",
    "family_id",
    "subfamily_id",
    "case_set",
    "condition",
)


def build_prompt_ablation_statistics(
    hybrid_report: dict[str, Any],
    service_report: dict[str, Any],
    hybrid_machine_report: dict[str, Any],
    service_machine_report: dict[str, Any],
    *,
    hybrid_service_bundle: dict[str, Any] | None = None,
    service_service_bundle: dict[str, Any] | None = None,
    expected_pairs: int,
    seed: int = 20260722,
    draws: int = 10000,
) -> dict[str, Any]:
    configuration_parity = _configuration_parity(
        hybrid_report.get("config") or {},
        service_report.get("config") or {},
    )
    if not configuration_parity["all_controlled_fields_match"]:
        mismatches = [
            field
            for field, values in configuration_parity["controlled_fields"].items()
            if not values["match"]
        ]
        raise ValueError(
            "controlled configuration mismatch: " + ", ".join(mismatches)
        )
    _reject_infrastructure_failures(hybrid_report, "hybrid_current")
    _reject_infrastructure_failures(service_report, "service_only")

    hybrid_generation = _index_generation(hybrid_report, "hybrid_current")
    service_generation = _index_generation(service_report, "service_only")
    case_ids = _require_same_ids(
        hybrid_generation,
        service_generation,
        expected_pairs=expected_pairs,
        label="generation",
    )
    hybrid_machine = _index_machine(hybrid_machine_report, "hybrid_current")
    service_machine = _index_machine(service_machine_report, "service_only")
    machine_ids = _require_same_ids(
        hybrid_machine,
        service_machine,
        expected_pairs=expected_pairs,
        label="machine",
    )
    if case_ids != machine_ids:
        raise ValueError("generation and machine reports do not cover the same case IDs")
    paired_payload = _validate_paired_payload(
        hybrid_generation,
        service_generation,
        case_ids,
    )
    paired_payload_sha256 = hashlib.sha256(
        json.dumps(
            paired_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    binary_vectors: dict[str, tuple[list[bool], list[bool]]] = {
        "first_pass_specification_validity": (
            [_first_pass(service_generation[case_id]) for case_id in case_ids],
            [_first_pass(hybrid_generation[case_id]) for case_id in case_ids],
        ),
        "final_generation_pass": (
            [service_generation[case_id].get("ok") is True for case_id in case_ids],
            [hybrid_generation[case_id].get("ok") is True for case_id in case_ids],
        ),
        "unknown_dsl_call_free": (
            [_unknown_dsl_call_free(service_generation[case_id]) for case_id in case_ids],
            [_unknown_dsl_call_free(hybrid_generation[case_id]) for case_id in case_ids],
        ),
    }
    for metric in MACHINE_METRICS:
        binary_vectors[metric] = (
            [service_machine[case_id].get(metric) is True for case_id in case_ids],
            [hybrid_machine[case_id].get(metric) is True for case_id in case_ids],
        )
    service_composition: dict[str, Any] = {"status": "not_provided"}
    service_continuous: dict[str, tuple[list[float | None], list[float | None]]] = {}
    if (hybrid_service_bundle is None) != (service_service_bundle is None):
        raise ValueError("both service audit bundles must be provided together")
    if hybrid_service_bundle is not None and service_service_bundle is not None:
        hybrid_service_cases = _index_service_audit_cases(hybrid_service_bundle)
        service_service_cases = _index_service_audit_cases(service_service_bundle)
        unknown_hybrid = sorted(set(hybrid_service_cases) - set(case_ids))
        unknown_service = sorted(set(service_service_cases) - set(case_ids))
        if unknown_hybrid or unknown_service:
            raise ValueError(
                "service audit contains cases outside the paired generation set: "
                f"hybrid={unknown_hybrid[:5]} service={unknown_service[:5]}"
            )
        service_case_ids = sorted(set(hybrid_service_cases) & set(service_service_cases))
        if not service_case_ids:
            raise ValueError("service audits have no paired successful cases")
        binary_vectors.update(
            {
                "unknown_dsl_call_free": (
                    [
                        _unknown_dsl_call_free(service_generation[case_id])
                        and service_service_cases.get(case_id, {}).get(
                            "unknown_dsl_call_free", True
                        )
                        for case_id in case_ids
                    ],
                    [
                        _unknown_dsl_call_free(hybrid_generation[case_id])
                        and hybrid_service_cases.get(case_id, {}).get(
                            "unknown_dsl_call_free", True
                        )
                        for case_id in case_ids
                    ],
                ),
                "single_line_collapse_free": (
                    [not service_service_cases[case_id]["single_line_collapse"] for case_id in service_case_ids],
                    [not hybrid_service_cases[case_id]["single_line_collapse"] for case_id in service_case_ids],
                ),
                "first_line_collapse_free": (
                    [not service_service_cases[case_id]["first_line_collapse"] for case_id in service_case_ids],
                    [not hybrid_service_cases[case_id]["first_line_collapse"] for case_id in service_case_ids],
                ),
            }
        )
        service_continuous = {
            "case_service_count": (
                [service_service_cases[case_id]["case_service_count"] for case_id in service_case_ids],
                [hybrid_service_cases[case_id]["case_service_count"] for case_id in service_case_ids],
            ),
            "dominant_code_line_share": (
                [service_service_cases[case_id]["dominant_code_line_share"] for case_id in service_case_ids],
                [hybrid_service_cases[case_id]["dominant_code_line_share"] for case_id in service_case_ids],
            ),
        }
        service_composition = {
            "status": "complete",
            "definitions": {
                "paired_service_unit": "case successful in both prompt profiles",
                "case_service_count": "union of TraceSession factory services across variants",
                "unknown_dsl_call_free": "no out-of-catalog TraceSession call and no tracker syntax error",
                "collapse_case_rule": "a case is collapsed when any successful variant is collapsed",
                "dominant_code_line_share": "mean variant-level dominant-line share within a case",
            },
            "paired_cases": len(service_case_ids),
            "paired_case_ids": service_case_ids,
            "hybrid_only_successful_cases": sorted(
                set(hybrid_service_cases) - set(service_service_cases)
            ),
            "service_only_successful_cases": sorted(
                set(service_service_cases) - set(hybrid_service_cases)
            ),
            "hybrid_current": _service_condition_summary(
                hybrid_service_bundle, hybrid_service_cases
            ),
            "service_only": _service_condition_summary(
                service_service_bundle, service_service_cases
            ),
        }
    binary_metrics = {
        metric: paired_binary_summary(a, b, seed=seed, draws=draws)
        for metric, (a, b) in binary_vectors.items()
    }
    adjusted = holm_adjust(
        {metric: float(summary["mcnemar_exact_p"]) for metric, summary in binary_metrics.items()}
    )
    for metric, value in adjusted.items():
        binary_metrics[metric]["holm_adjusted_p"] = value

    continuous_extractors: dict[str, Callable[[dict[str, Any]], float | None]] = {
        "model_calls": lambda row: float(len(row.get("model_calls") or [])),
        "total_tokens": _total_tokens,
        "api_latency_s": _api_latency,
        "end_to_end_latency_s": lambda row: _as_float(row.get("duration_s")),
    }
    continuous_metrics = {
        metric: _paired_continuous_summary(
            [extractor(service_generation[case_id]) for case_id in case_ids],
            [extractor(hybrid_generation[case_id]) for case_id in case_ids],
            seed=seed,
            draws=draws,
        )
        for metric, extractor in continuous_extractors.items()
    }
    continuous_metrics.update(
        {
            metric: _paired_continuous_summary(left, right, seed=seed, draws=draws)
            for metric, (left, right) in service_continuous.items()
        }
    )

    machine_summary = binary_metrics["machine_ok"]
    ci_low = float(machine_summary["bootstrap_ci_95"][0])
    return {
        "kind": "plan2_prompt_ablation_paired_statistics",
        "schema_version": "plan2-prompt-ablation-statistics-v2",
        "conditions": {"left": "service_only", "right": "hybrid_current"},
        "difference_direction": "service_only_minus_hybrid_current",
        "pair_completeness": len(case_ids),
        "case_ids": case_ids,
        "paired_payload_sha256": paired_payload_sha256,
        "bootstrap": {"seed": seed, "draws": draws, "unit": "case"},
        "configuration_parity": configuration_parity,
        "binary_metrics": binary_metrics,
        "continuous_metrics": continuous_metrics,
        "service_composition": service_composition,
        "noninferiority": {
            "metric": "machine_ok",
            "margin": -0.03,
            "observed_difference": float(machine_summary["difference"]),
            "bootstrap_ci_95": list(machine_summary["bootstrap_ci_95"]),
            "ci_lower_bound": ci_low,
            "passed": ci_low >= -0.03,
            "decision_rule": "service_only_minus_hybrid_current_ci_lower_ge_minus_0.03",
        },
    }


def _index_generation(report: dict[str, Any], expected_profile: str) -> dict[str, dict[str, Any]]:
    config = report.get("config") if isinstance(report.get("config"), dict) else {}
    profile = str(config.get("prompt_profile") or "")
    if profile != expected_profile:
        raise ValueError(f"generation report profile={profile!r}, expected {expected_profile!r}")
    metadata = config.get("prompt_profile_metadata")
    expected_policy = {
        "hybrid_current": "benchmark_strategy",
        "service_only": "removed",
    }[expected_profile]
    if not isinstance(metadata, dict) or any(
        (
            metadata.get("profile_version") != "plan2-prompt-profile-v2",
            metadata.get("prompt_profile") != expected_profile,
            metadata.get("strategy_hint_policy") != expected_policy,
        )
    ):
        raise ValueError(f"generation {expected_profile} has invalid profile metadata")
    indexed = _index_unique(
        report.get("results") or [],
        label=f"generation {expected_profile}",
    )
    for case_id, row in indexed.items():
        if row.get("ok") is not True:
            continue
        variants = row.get("variants")
        if not isinstance(variants, list) or len(variants) != 2:
            raise ValueError(
                f"generation {expected_profile} case {case_id} must contain exactly 2 valid variants"
            )
        variant_ids: list[str] = []
        for index, variant in enumerate(variants):
            if not isinstance(variant, dict):
                raise ValueError(
                    f"generation {expected_profile} case {case_id} variant {index} must be a dict"
                )
            variant_id = variant.get("id")
            if not isinstance(variant_id, str) or not variant_id.strip():
                raise ValueError(
                    f"generation {expected_profile} case {case_id} variant {index} has invalid id"
                )
            variant_ids.append(variant_id.strip())
        if len(set(variant_ids)) != 2:
            raise ValueError(
                f"generation {expected_profile} case {case_id} must have unique variant ids"
            )
        release_gate = row.get("release_gate")
        if not isinstance(release_gate, dict) or (
            release_gate.get("release_ready") is not True
            or release_gate.get("multi_solution_ready") is not True
        ):
            raise ValueError(
                f"generation {expected_profile} case {case_id} has invalid release gate"
            )
    return indexed


def _index_machine(report: dict[str, Any], expected_profile: str) -> dict[str, dict[str, Any]]:
    rows = list(report.get("records") or [])
    for row in rows:
        if str(row.get("condition") or "") != expected_profile:
            raise ValueError(
                f"machine {expected_profile}: record has invalid condition "
                f"{row.get('condition')!r}"
            )
        invalid_metrics = [
            metric for metric in MACHINE_METRICS if type(row.get(metric)) is not bool
        ]
        if invalid_metrics:
            raise ValueError(
                f"machine {expected_profile}: case {row.get('case_id')!r} has "
                f"non-boolean metrics: {', '.join(invalid_metrics)}"
            )
        expected_machine_ok = all(
            row[metric] for metric in MACHINE_METRICS if metric != "machine_ok"
        )
        if row["machine_ok"] != expected_machine_ok:
            raise ValueError(
                f"machine {expected_profile}: case {row.get('case_id')!r} machine_ok "
                "must equal the logical conjunction of the other nine metrics"
            )
    return _index_unique(rows, label=f"machine {expected_profile}")


def _index_unique(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError(f"{label}: missing case_id")
        if case_id in indexed:
            raise ValueError(f"{label}: duplicate case_id {case_id}")
        indexed[case_id] = row
    return indexed


def _index_service_audit_cases(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    usage_by_case: dict[str, list[dict[str, Any]]] = {}
    for row in bundle.get("service_usage_rows") or []:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError("service usage row is missing case_id")
        usage_by_case.setdefault(case_id, []).append(row)
    source_by_case: dict[str, list[dict[str, Any]]] = {}
    for row in bundle.get("source_line_rows") or []:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError("source-line row is missing case_id")
        source_by_case.setdefault(case_id, []).append(row)
    if set(usage_by_case) != set(source_by_case):
        raise ValueError(
            "service usage and source-line audits cover different cases: "
            f"usage_only={sorted(set(usage_by_case) - set(source_by_case))[:5]} "
            f"source_only={sorted(set(source_by_case) - set(usage_by_case))[:5]}"
        )
    result: dict[str, dict[str, Any]] = {}
    for case_id in sorted(usage_by_case):
        usage_rows = usage_by_case[case_id]
        source_rows = source_by_case[case_id]
        service_counts = {_csv_int(row.get("case_service_count")) for row in usage_rows}
        if len(service_counts) != 1:
            raise ValueError(f"inconsistent case_service_count for {case_id}: {service_counts}")
        dominant_values = [_csv_float(row.get("dominant_code_line_share")) for row in source_rows]
        result[case_id] = {
            "case_service_count": float(next(iter(service_counts))),
            "unknown_dsl_call_free": all(
                _csv_int(row.get("out_of_catalog_call_count")) == 0
                and not str(row.get("tracker_syntax_error") or "").strip()
                for row in usage_rows
            ),
            "single_line_collapse": any(
                _csv_bool(row.get("single_line_collapse")) for row in source_rows
            ),
            "first_line_collapse": any(
                _csv_bool(row.get("first_line_collapse")) for row in source_rows
            ),
            "dominant_code_line_share": sum(dominant_values) / len(dominant_values),
        }
    return result


def _service_condition_summary(
    bundle: dict[str, Any],
    indexed_cases: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    summary = bundle.get("summary") or {}
    coverage = summary.get("coverage") or {}
    usage = summary.get("service_usage") or {}
    reuse = summary.get("reuse") or {}
    return {
        "audited_successful_cases": len(indexed_cases),
        "skipped_failed_case_ids": list(coverage.get("skipped_failed_case_ids") or []),
        "used_service_count": int(usage.get("used_service_count") or 0),
        "multi_service_cases": usage.get("multi_service_cases") or {},
        "unknown_dsl_call_cases": sum(
            not row["unknown_dsl_call_free"] for row in indexed_cases.values()
        ),
        "single_line_collapse_cases": sum(
            bool(row["single_line_collapse"]) for row in indexed_cases.values()
        ),
        "first_line_collapse_cases": sum(
            bool(row["first_line_collapse"]) for row in indexed_cases.values()
        ),
        "cross_family_reused_services": len(
            reuse.get("services_crossing_2plus_families") or []
        ),
        "cross_macro_reused_services": len(
            reuse.get("services_crossing_2plus_macro_groups") or []
        ),
    }


def _csv_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _csv_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"expected integer CSV value, got {value!r}") from exc


def _csv_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"expected numeric CSV value, got {value!r}") from exc


def _require_same_ids(
    left: dict[str, dict[str, Any]],
    right: dict[str, dict[str, Any]],
    *,
    expected_pairs: int,
    label: str,
) -> list[str]:
    if set(left) != set(right):
        raise ValueError(
            f"{label}: unmatched IDs; left_only={sorted(set(left) - set(right))[:5]} "
            f"right_only={sorted(set(right) - set(left))[:5]}"
        )
    if len(left) != expected_pairs:
        raise ValueError(f"{label}: expected {expected_pairs} pairs, found {len(left)}")
    return sorted(left)


def _first_pass(row: dict[str, Any]) -> bool:
    explicit = row.get("first_pass_specification_valid")
    if isinstance(explicit, bool):
        return explicit
    raise ValueError(
        f"case {row.get('case_id')!r} has invalid first_pass_specification_valid"
    )


def _unknown_dsl_call_free(row: dict[str, Any]) -> bool:
    summary = row.get("candidate_summary")
    if not isinstance(summary, dict):
        raise ValueError(
            f"case {row.get('case_id')!r} is missing candidate_summary for unknown DSL audit"
        )
    value = summary.get("unknown_dsl_call_failure_count")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(
            f"case {row.get('case_id')!r} has invalid unknown_dsl_call_failure_count"
        )
    return value == 0


def _reject_infrastructure_failures(report: dict[str, Any], label: str) -> None:
    contaminated = [
        str(row.get("case_id") or "")
        for row in report.get("results") or []
        if str(row.get("failure_type") or "") in INFRASTRUCTURE_FAILURE_TYPES
    ]
    if contaminated:
        raise ValueError(
            f"infrastructure failure in {label}: {', '.join(contaminated[:5])}"
        )


def _validate_paired_payload(
    hybrid: dict[str, dict[str, Any]],
    service: dict[str, dict[str, Any]],
    case_ids: list[str],
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    mismatches: list[str] = []
    for case_id in case_ids:
        hybrid_payload = {
            field: hybrid[case_id].get(field)
            for field in PAIRED_PAYLOAD_FIELDS
        }
        service_payload = {
            field: service[case_id].get(field)
            for field in PAIRED_PAYLOAD_FIELDS
        }
        if hybrid_payload != service_payload:
            mismatches.append(case_id)
            continue
        payload.append(hybrid_payload)
    if mismatches:
        raise ValueError(
            "paired payload mismatch: " + ", ".join(mismatches[:5])
        )
    return payload


def _total_tokens(row: dict[str, Any]) -> float | None:
    values = [
        call.get("total_tokens")
        for call in row.get("model_calls") or []
        if isinstance(call, dict)
    ]
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    return sum(numeric) if numeric else None


def _api_latency(row: dict[str, Any]) -> float | None:
    values = [
        call.get("duration_s")
        for call in row.get("model_calls") or []
        if isinstance(call, dict)
    ]
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    return sum(numeric) if numeric else None


def _as_float(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _paired_continuous_summary(
    left: list[float | None],
    right: list[float | None],
    *,
    seed: int,
    draws: int,
) -> dict[str, Any]:
    pairs = [(float(a), float(b)) for a, b in zip(left, right) if a is not None and b is not None]
    if not pairs:
        return {
            "pairs": 0,
            "a_mean": None,
            "b_mean": None,
            "mean_difference": None,
            "median_difference": None,
            "bootstrap_ci_95": [None, None],
        }
    a_values = np.asarray([pair[0] for pair in pairs], dtype=float)
    b_values = np.asarray([pair[1] for pair in pairs], dtype=float)
    differences = a_values - b_values
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(pairs), size=(draws, len(pairs)))
    bootstrap = differences[indices].mean(axis=1)
    low, high = np.quantile(bootstrap, [0.025, 0.975]).tolist()
    return {
        "pairs": len(pairs),
        "a_mean": float(a_values.mean()),
        "b_mean": float(b_values.mean()),
        "mean_difference": float(differences.mean()),
        "median_difference": float(np.median(differences)),
        "bootstrap_ci_95": [float(low), float(high)],
    }


def _configuration_parity(hybrid: dict[str, Any], service: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, dict[str, Any]] = {}
    for field in CONTROLLED_CONFIG_FIELDS:
        hybrid_value = _nested_value(hybrid, field)
        service_value = _nested_value(service, field)
        fields[field] = {
            "hybrid_current": hybrid_value,
            "service_only": service_value,
            "match": hybrid_value == service_value,
        }
    return {
        "controlled_fields": fields,
        "all_controlled_fields_match": all(item["match"] for item in fields.values()),
        "intentional_difference": {
            "prompt_profile": {
                "hybrid_current": hybrid.get("prompt_profile"),
                "service_only": service.get("prompt_profile"),
            },
            "prompt_profile_metadata": {
                "hybrid_current": hybrid.get("prompt_profile_metadata"),
                "service_only": service.get("prompt_profile_metadata"),
            },
        },
    }


def _nested_value(payload: dict[str, Any], dotted: str) -> Any:
    value: Any = payload
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def load_service_audit_bundle(directory: Path) -> dict[str, Any]:
    def read_csv(name: str) -> list[dict[str, str]]:
        path = directory / name
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))

    return {
        "summary": json.loads(
            (directory / "service_usage_summary.json").read_text(encoding="utf-8")
        ),
        "service_usage_rows": read_csv("service_usage_per_case.csv"),
        "source_line_rows": read_csv("source_line_diagnostics.csv"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hybrid-report", type=Path, required=True)
    parser.add_argument("--service-report", type=Path, required=True)
    parser.add_argument("--hybrid-machine", type=Path, required=True)
    parser.add_argument("--service-machine", type=Path, required=True)
    parser.add_argument("--hybrid-service-dir", type=Path)
    parser.add_argument("--service-service-dir", type=Path)
    parser.add_argument("--expected-pairs", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--draws", type=int, default=10000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/experiments/plan2_20260722/p0_2_prompt_ablation/prompt_ablation_paired_statistics.json"),
    )
    args = parser.parse_args()
    if (args.hybrid_service_dir is None) != (args.service_service_dir is None):
        parser.error("--hybrid-service-dir and --service-service-dir must be provided together")
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    payload = build_prompt_ablation_statistics(
        load(args.hybrid_report),
        load(args.service_report),
        load(args.hybrid_machine),
        load(args.service_machine),
        hybrid_service_bundle=load_service_audit_bundle(args.hybrid_service_dir)
        if args.hybrid_service_dir
        else None,
        service_service_bundle=load_service_audit_bundle(args.service_service_dir)
        if args.service_service_dir
        else None,
        expected_pairs=args.expected_pairs,
        seed=args.seed,
        draws=args.draws,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "noninferiority": payload["noninferiority"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
