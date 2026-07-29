#!/usr/bin/env python3
"""Audit TraceSession service composition in frozen AlgoTutorGen artifacts."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from itertools import combinations_with_replacement
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.runtime.dsl_guard import _ALLOWED_ATTRIBUTES, _FACTORY_TO_CLASS
from algolab.runtime.dsl import TraceSession


SERVICE_CATALOG = tuple(sorted(_FACTORY_TO_CLASS))
SESSION_API = frozenset(_ALLOWED_ATTRIBUTES[TraceSession])

FAMILY_TO_MACRO_GROUP = {
    "advanced_graph": "graph_algorithms",
    "array_pointer": "sequence_search_sort",
    "backtracking_recursion": "combinatorial_optimization",
    "basic_graph": "graph_algorithms",
    "binary_search": "sequence_search_sort",
    "dp_1d": "dynamic_programming",
    "dp_2d": "dynamic_programming",
    "dp_core": "dynamic_programming",
    "geometry_sweep": "math_geometry",
    "greedy": "combinatorial_optimization",
    "hash_map": "strings_hash",
    "heap_topk_huffman": "sequence_search_sort",
    "linked_list_cache": "trees_and_structures",
    "math_bit": "math_geometry",
    "monotonic_stack": "sequence_search_sort",
    "range_structure": "trees_and_structures",
    "shortest_path_mst": "graph_algorithms",
    "sorting": "sequence_search_sort",
    "string_advanced": "strings_hash",
    "tree_bst_lca": "trees_and_structures",
    "tree_dp": "dynamic_programming",
    "trie": "strings_hash",
    "union_find": "graph_algorithms",
}

MACRO_GROUPS = tuple(sorted(set(FAMILY_TO_MACRO_GROUP.values())))


@dataclass(frozen=True)
class ServiceCallSite:
    method: str
    line: int


@dataclass(frozen=True)
class ServiceExtraction:
    services: tuple[str, ...]
    unknown_session_calls: tuple[str, ...]
    syntax_error: str | None = None
    factory_call_sites: tuple[ServiceCallSite, ...] = ()
    unknown_call_sites: tuple[ServiceCallSite, ...] = ()


@dataclass(frozen=True)
class SourceLineDiagnostics:
    event_count: int
    code_line_one_count: int
    code_line_one_ratio: float
    dominant_line: int | None
    dominant_line_count: int
    dominant_line_ratio: float
    single_line_dominated: bool
    out_of_range_count: int
    answer_event_count: int
    answer_return_line_match_count: int
    answer_return_line_match_rate: float | None
    source_line_count: int
    return_lines: tuple[int, ...]
    code_line_present_count: int
    code_line_missing_count: int
    code_line_invalid_count: int
    distinct_valid_code_line_count: int
    single_line_collapse: bool
    first_line_collapse: bool


def extract_trace_services(tracker_code: str) -> ServiceExtraction:
    """Return distinct TraceSession factories and calls outside its API catalog."""

    try:
        tree = ast.parse(tracker_code)
    except SyntaxError as exc:
        return ServiceExtraction((), (), f"{exc.msg} (line {exc.lineno})")

    session_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if not _is_trace_session_constructor(value):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    session_names.add(target.id)

    services: set[str] = set()
    unknown: set[str] = set()
    factory_sites: list[ServiceCallSite] = []
    unknown_sites: list[ServiceCallSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if not isinstance(owner, ast.Name) or owner.id not in session_names:
            continue
        method = node.func.attr
        if method in _FACTORY_TO_CLASS:
            services.add(method)
            factory_sites.append(ServiceCallSite(method, int(node.lineno)))
        elif method not in SESSION_API:
            unknown.add(method)
            unknown_sites.append(ServiceCallSite(method, int(node.lineno)))
    return ServiceExtraction(
        tuple(sorted(services)),
        tuple(sorted(unknown)),
        factory_call_sites=tuple(sorted(factory_sites, key=lambda item: (item.line, item.method))),
        unknown_call_sites=tuple(sorted(unknown_sites, key=lambda item: (item.line, item.method))),
    )


def analyze_source_lines(source: str, events: Iterable[dict[str, Any]]) -> SourceLineDiagnostics:
    """Compute structural source-line collapse and answer/return diagnostics."""

    event_list = list(events)
    source_line_count = len(source.splitlines())
    return_lines = _solve_return_lines(source)
    present_count = sum("code_line" in event and event.get("code_line") is not None for event in event_list)
    missing_count = len(event_list) - present_count
    invalid_count = sum(
        1
        for event in event_list
        if "code_line" in event
        and event.get("code_line") is not None
        and (not isinstance(event.get("code_line"), int) or int(event["code_line"]) < 1)
    )
    in_range_line_values = [
        int(event.get("code_line"))
        for event in event_list
        if isinstance(event.get("code_line"), int)
        and 1 <= int(event["code_line"]) <= source_line_count
    ]
    counts = Counter(in_range_line_values)
    if counts:
        dominant_line, dominant_count = min(
            counts.items(), key=lambda item: (-item[1], item[0])
        )
    else:
        dominant_line, dominant_count = None, 0
    event_count = len(event_list)
    line_one_count = counts.get(1, 0)
    dominant_ratio = dominant_count / event_count if event_count else 0.0
    answer_events = [event for event in event_list if _is_answer_event(event)]
    answer_matches = sum(
        1 for event in answer_events if event.get("code_line") in return_lines
    )
    return SourceLineDiagnostics(
        event_count=event_count,
        code_line_one_count=line_one_count,
        code_line_one_ratio=line_one_count / event_count if event_count else 0.0,
        dominant_line=dominant_line,
        dominant_line_count=dominant_count,
        dominant_line_ratio=dominant_ratio,
        single_line_dominated=bool(event_count and dominant_ratio >= 0.5),
        out_of_range_count=sum(
            1
            for event in event_list
            if isinstance(event.get("code_line"), int)
            and int(event["code_line"]) > source_line_count
        ),
        answer_event_count=len(answer_events),
        answer_return_line_match_count=answer_matches,
        answer_return_line_match_rate=(answer_matches / len(answer_events) if answer_events else None),
        source_line_count=source_line_count,
        return_lines=return_lines,
        code_line_present_count=present_count,
        code_line_missing_count=missing_count,
        code_line_invalid_count=invalid_count,
        distinct_valid_code_line_count=len(counts),
        single_line_collapse=bool(
            event_count
            and len(counts) == 1
            and not missing_count
            and not invalid_count
            and len(in_range_line_values) == event_count
        ),
        first_line_collapse=bool(
            event_count
            and len(counts) == 1
            and 1 in counts
            and not missing_count
            and not invalid_count
            and len(in_range_line_values) == event_count
        ),
    )


def macro_group_for_family(family_id: str) -> str:
    return FAMILY_TO_MACRO_GROUP.get(family_id, "unmapped")


def run_service_audit(
    report_path: Path,
    output_dir: Path,
    *,
    expected_cases: int = 200,
    require_all_ok: bool = True,
) -> dict[str, Any]:
    report_path = report_path.resolve()
    output_dir = output_dir.resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    records = list(report.get("results") or [])
    _validate_report_records(
        records,
        expected_cases=expected_cases,
        require_all_ok=require_all_ok,
    )
    audited_records = [record for record in records if record.get("ok") is True]
    skipped_failed_case_ids = sorted(
        str(record.get("case_id") or "") for record in records if record.get("ok") is not True
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    variant_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    case_services: dict[str, set[str]] = {}
    case_families: dict[str, str] = {}
    case_macros: dict[str, str] = {}
    case_variant_counts: Counter[str] = Counter()
    artifact_hashes: dict[str, str] = {}
    outside_catalog: list[dict[str, Any]] = []

    for record in sorted(records, key=lambda item: str(item.get("case_id") or "")):
        case_id = str(record["case_id"])
        if record.get("ok") is not True:
            continue
        family_id = str(record.get("family_id") or "")
        macro_group = macro_group_for_family(family_id)
        if macro_group == "unmapped":
            raise ValueError(f"family_id has no macro-group mapping: {family_id}")
        artifact_path = _resolve_artifact_path(record.get("json"), report_path)
        artifact_bytes = artifact_path.read_bytes()
        artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
        artifact_hashes[case_id] = artifact_sha256
        artifact = json.loads(artifact_bytes)
        variants = list(artifact.get("variants") or [])
        if not variants:
            raise ValueError(f"artifact has no variants: {case_id}")
        variant_ids = [str(variant.get("id") or "") for variant in variants]
        if not all(variant_ids) or len(set(variant_ids)) != len(variant_ids):
            raise ValueError(f"artifact has empty or duplicate variant ids: {case_id}")
        case_variant_counts[case_id] = len(variants)
        case_families[case_id] = family_id
        case_macros[case_id] = macro_group
        case_services.setdefault(case_id, set())

        for variant in sorted(variants, key=lambda item: str(item.get("id") or "")):
            variant_id = str(variant["id"])
            extraction = extract_trace_services(str(variant.get("tracker_code") or ""))
            services = set(extraction.services)
            case_services[case_id].update(services)
            for site in extraction.unknown_call_sites:
                outside_catalog.append(
                    {
                        "case_id": case_id,
                        "variant_id": variant_id,
                        "method": site.method,
                        "tracker_line": site.line,
                    }
                )
            trace = variant.get("trace") if isinstance(variant.get("trace"), dict) else {}
            diagnostics = analyze_source_lines(
                str(variant.get("code") or ""),
                list(trace.get("events") or []),
            )
            common = {
                "case_id": case_id,
                "title": str(record.get("title") or ""),
                "family_id": family_id,
                "family_label": str(record.get("family") or ""),
                "subfamily_id": str(record.get("subfamily_id") or ""),
                "macro_group": macro_group,
                "process_profile": str(record.get("process_profile") or ""),
                "gate_layer": str(record.get("gate_layer") or ""),
                "support_level": str(record.get("support_level") or ""),
                "sample_index": record.get("sample_index"),
                "attempt_source": str(record.get("attempt_source") or "primary"),
                "artifact_path": str(artifact_path),
                "artifact_sha256": artifact_sha256,
                "variant_id": variant_id,
                "variant_name": str(variant.get("name") or ""),
            }
            variant_rows.append(
                {
                    **common,
                    "service_count": len(services),
                    "services": sorted(services),
                    "factory_call_site_count": len(extraction.factory_call_sites),
                    "factory_call_sites": [
                        {"method": site.method, "tracker_line": site.line}
                        for site in extraction.factory_call_sites
                    ],
                    "out_of_catalog_call_count": len(extraction.unknown_call_sites),
                    "out_of_catalog_calls": [
                        {"method": site.method, "tracker_line": site.line}
                        for site in extraction.unknown_call_sites
                    ],
                    "tracker_syntax_error": extraction.syntax_error or "",
                }
            )
            source_rows.append(
                {
                    **common,
                    "solve_line_count": diagnostics.source_line_count,
                    "return_line_numbers": list(diagnostics.return_lines),
                    "event_count": diagnostics.event_count,
                    "code_line_present_count": diagnostics.code_line_present_count,
                    "code_line_missing_count": diagnostics.code_line_missing_count,
                    "code_line_invalid_count": diagnostics.code_line_invalid_count,
                    "code_line_out_of_range_count": diagnostics.out_of_range_count,
                    "code_line_1_count": diagnostics.code_line_one_count,
                    "code_line_1_rate": diagnostics.code_line_one_ratio,
                    "distinct_valid_code_line_count": diagnostics.distinct_valid_code_line_count,
                    "dominant_code_line": diagnostics.dominant_line,
                    "dominant_code_line_count": diagnostics.dominant_line_count,
                    "dominant_code_line_share": diagnostics.dominant_line_ratio,
                    "single_line_collapse": diagnostics.single_line_collapse,
                    "first_line_collapse": diagnostics.first_line_collapse,
                    "canonical_answer_event_count": diagnostics.answer_event_count,
                    "canonical_answer_event_return_match_count": diagnostics.answer_return_line_match_count,
                    "canonical_answer_event_return_match_rate": diagnostics.answer_return_line_match_rate,
                    "canonical_answer_events_all_match": bool(
                        diagnostics.answer_event_count
                        and diagnostics.answer_event_count == diagnostics.answer_return_line_match_count
                    ),
                }
            )

    for row in variant_rows:
        case_id = str(row["case_id"])
        row["case_variant_count"] = case_variant_counts[case_id]
        row["case_service_count"] = len(case_services[case_id])
        row["case_services"] = sorted(case_services[case_id])

    service_case_sets = {
        service: {case_id for case_id, services in case_services.items() if service in services}
        for service in SERVICE_CATALOG
    }
    service_variant_sets = {
        service: {
            (str(row["case_id"]), str(row["variant_id"]))
            for row in variant_rows
            if service in row["services"]
        }
        for service in SERVICE_CATALOG
    }
    reuse_rows = _build_reuse_rows(
        records=audited_records,
        variant_rows=variant_rows,
        service_case_sets=service_case_sets,
        service_variant_sets=service_variant_sets,
        case_families=case_families,
        case_macros=case_macros,
    )
    cooccurrence_rows = _build_cooccurrence_rows(
        service_case_sets,
        service_variant_sets,
        case_count=len(records),
        variant_count=len(variant_rows),
    )

    _write_csv(output_dir / "service_usage_per_case.csv", variant_rows)
    _write_csv(output_dir / "service_reuse_matrix.csv", reuse_rows)
    _write_csv(output_dir / "service_cooccurrence.csv", cooccurrence_rows)
    _write_csv(output_dir / "source_line_diagnostics.csv", source_rows)

    summary = _build_summary(
        report_path=report_path,
        report_bytes=report_path.read_bytes(),
        artifact_hashes=artifact_hashes,
        records=audited_records,
        source_record_count=len(records),
        skipped_failed_case_ids=skipped_failed_case_ids,
        variant_rows=variant_rows,
        source_rows=source_rows,
        case_services=case_services,
        service_case_sets=service_case_sets,
        outside_catalog=outside_catalog,
        output_dir=output_dir,
        reuse_rows=reuse_rows,
        cooccurrence_row_count=len(cooccurrence_rows),
    )
    (output_dir / "service_usage_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def _validate_report_records(
    records: list[dict[str, Any]],
    *,
    expected_cases: int,
    require_all_ok: bool,
) -> None:
    if expected_cases and len(records) != expected_cases:
        raise ValueError(f"expected {expected_cases} report rows, found {len(records)}")
    case_ids = [str(record.get("case_id") or "") for record in records]
    if not all(case_ids) or len(set(case_ids)) != len(case_ids):
        raise ValueError("report case_id values must be non-empty and unique")
    bad_samples = [case_id for case_id, record in zip(case_ids, records) if record.get("sample_index") != 0]
    if bad_samples:
        raise ValueError(f"report contains non-zero sample indexes: {bad_samples[:5]}")
    failed = [case_id for case_id, record in zip(case_ids, records) if record.get("ok") is not True]
    if require_all_ok and failed:
        raise ValueError(f"report contains failed rows: {failed[:5]}")


def _resolve_artifact_path(value: Any, report_path: Path) -> Path:
    candidate = Path(str(value or ""))
    choices = [candidate] if candidate.is_absolute() else [Path.cwd() / candidate]
    choices.extend(parent / candidate for parent in report_path.parents)
    for choice in choices:
        if choice.is_file():
            return choice.resolve()
    raise FileNotFoundError(f"artifact not found: {value}")


def _build_reuse_rows(
    *,
    records: list[dict[str, Any]],
    variant_rows: list[dict[str, Any]],
    service_case_sets: dict[str, set[str]],
    service_variant_sets: dict[str, set[tuple[str, str]]],
    case_families: dict[str, str],
    case_macros: dict[str, str],
) -> list[dict[str, Any]]:
    family_ids = tuple(sorted(FAMILY_TO_MACRO_GROUP))
    case_count = len(records)
    variant_count = len(variant_rows)
    rows: list[dict[str, Any]] = []
    for service in SERVICE_CATALOG:
        cases = service_case_sets[service]
        variants = service_variant_sets[service]
        families = sorted({case_families[case_id] for case_id in cases})
        macros = sorted({case_macros[case_id] for case_id in cases})
        row: dict[str, Any] = {
            "service": service,
            "catalog_status": "catalog",
            "case_count": len(cases),
            "case_rate": _safe_rate(len(cases), case_count),
            "variant_count": len(variants),
            "variant_rate": _safe_rate(len(variants), variant_count),
            "factory_call_site_count": sum(
                sum(
                    1
                    for site in item["factory_call_sites"]
                    if site["method"] == service
                )
                for item in variant_rows
                if service in item["services"]
            ),
            "family_count": len(families),
            "families": families,
            "macro_group_count": len(macros),
            "macro_groups": macros,
        }
        row.update(
            {
                f"family__{family}": sum(case_families[case_id] == family for case_id in cases)
                for family in family_ids
            }
        )
        row.update(
            {
                f"macro__{macro}": sum(case_macros[case_id] == macro for case_id in cases)
                for macro in MACRO_GROUPS
            }
        )
        rows.append(row)
    return rows


def _build_cooccurrence_rows(
    service_case_sets: dict[str, set[str]],
    service_variant_sets: dict[str, set[tuple[str, str]]],
    *,
    case_count: int,
    variant_count: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for service_a, service_b in combinations_with_replacement(SERVICE_CATALOG, 2):
        case_intersection = service_case_sets[service_a] & service_case_sets[service_b]
        case_union = service_case_sets[service_a] | service_case_sets[service_b]
        variant_intersection = service_variant_sets[service_a] & service_variant_sets[service_b]
        variant_union = service_variant_sets[service_a] | service_variant_sets[service_b]
        rows.append(
            {
                "service_a": service_a,
                "service_b": service_b,
                "case_cooccurrence_count": len(case_intersection),
                "case_cooccurrence_rate": _safe_rate(len(case_intersection), case_count),
                "case_jaccard": _safe_rate(len(case_intersection), len(case_union)),
                "variant_cooccurrence_count": len(variant_intersection),
                "variant_cooccurrence_rate": _safe_rate(len(variant_intersection), variant_count),
                "variant_jaccard": _safe_rate(len(variant_intersection), len(variant_union)),
            }
        )
    return rows


def _build_summary(
    *,
    report_path: Path,
    report_bytes: bytes,
    artifact_hashes: dict[str, str],
    records: list[dict[str, Any]],
    source_record_count: int,
    skipped_failed_case_ids: list[str],
    variant_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    case_services: dict[str, set[str]],
    service_case_sets: dict[str, set[str]],
    outside_catalog: list[dict[str, Any]],
    output_dir: Path,
    reuse_rows: list[dict[str, Any]],
    cooccurrence_row_count: int,
) -> dict[str, Any]:
    case_count = len(records)
    variant_count = len(variant_rows)
    multi_case_count = sum(len(services) >= 2 for services in case_services.values())
    multi_variant_count = sum(int(row["service_count"]) >= 2 for row in variant_rows)
    used_services = sorted(service for service, cases in service_case_sets.items() if cases)
    event_count = sum(int(row["event_count"]) for row in source_rows)
    line_one_count = sum(int(row["code_line_1_count"]) for row in source_rows)
    out_of_range_count = sum(int(row["code_line_out_of_range_count"]) for row in source_rows)
    answer_count = sum(int(row["canonical_answer_event_count"]) for row in source_rows)
    answer_matches = sum(int(row["canonical_answer_event_return_match_count"]) for row in source_rows)
    answer_covered_variants = sum(int(row["canonical_answer_event_count"]) > 0 for row in source_rows)
    dominant_shares = [float(row["dominant_code_line_share"]) for row in source_rows]
    artifact_set_payload = "\n".join(
        f"{case_id}:{artifact_hashes[case_id]}" for case_id in sorted(artifact_hashes)
    ).encode("utf-8")
    return {
        "kind": "full200_service_composition_audit",
        "schema_version": "full200-service-audit-v1",
        "inputs": {
            "report_path": str(report_path),
            "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
            "artifact_set_sha256": hashlib.sha256(artifact_set_payload).hexdigest(),
        },
        "definitions": {
            "service_catalog": list(SERVICE_CATALOG),
            "service_catalog_source": "algolab/runtime/dsl_guard.py::_FACTORY_TO_CLASS",
            "excluded_session_methods": ["note", "result", "step", "to_trace"],
            "case_service_rule": "union_across_variants",
            "macro_group_source": "explicit_family_mapping_v1",
            "family_to_macro_group": dict(sorted(FAMILY_TO_MACRO_GROUP.items())),
            "answer_event_rule": "role_equals_answer",
            "dominant_line_denominator": "all_trace_events",
            "single_line_dominated_threshold": 0.5,
        },
        "coverage": {
            "source_case_count": source_record_count,
            "case_count": case_count,
            "variant_count": variant_count,
            "artifact_count": len(artifact_hashes),
            "family_count": len({str(record.get("family_id") or "") for record in records}),
            "macro_group_count": len({macro_group_for_family(str(record.get("family_id") or "")) for record in records}),
            "skipped_failed_case_ids": skipped_failed_case_ids,
        },
        "service_usage": {
            "catalog_service_count": len(SERVICE_CATALOG),
            "used_service_count": len(used_services),
            "used_services": used_services,
            "unused_services": sorted(set(SERVICE_CATALOG) - set(used_services)),
            "outside_catalog_calls": sorted(
                outside_catalog,
                key=lambda item: (item["case_id"], item["variant_id"], item["tracker_line"], item["method"]),
            ),
            "case_service_count_distribution": _counter_dict(len(value) for value in case_services.values()),
            "variant_service_count_distribution": _counter_dict(int(row["service_count"]) for row in variant_rows),
            "multi_service_cases": _ratio_record(multi_case_count, case_count),
            "multi_service_variants": _ratio_record(multi_variant_count, variant_count),
        },
        "reuse": {
            "by_service": {
                str(row["service"]): {
                    "case_count": int(row["case_count"]),
                    "variant_count": int(row["variant_count"]),
                    "family_count": int(row["family_count"]),
                    "families": list(row["families"]),
                    "macro_group_count": int(row["macro_group_count"]),
                    "macro_groups": list(row["macro_groups"]),
                }
                for row in reuse_rows
            },
            "services_crossing_2plus_families": sorted(
                service
                for service in SERVICE_CATALOG
                if len(
                    {
                        str(record.get("family_id") or "")
                        for record in records
                        if str(record.get("case_id")) in service_case_sets[service]
                    }
                )
                >= 2
            ),
            "services_crossing_2plus_macro_groups": sorted(
                service
                for service in SERVICE_CATALOG
                if len(
                    {
                        macro_group_for_family(str(record.get("family_id") or ""))
                        for record in records
                        if str(record.get("case_id")) in service_case_sets[service]
                    }
                )
                >= 2
            ),
        },
        "source_line": {
            "events": event_count,
            "code_line_1": _ratio_record(line_one_count, event_count),
            "out_of_range": _ratio_record(out_of_range_count, event_count),
            "dominant_line_share": _distribution_summary(dominant_shares),
            "dominant_share_ge_0_5_variants": _ratio_record(
                sum(value >= 0.5 for value in dominant_shares), variant_count
            ),
            "dominant_share_ge_0_8_variants": _ratio_record(
                sum(value >= 0.8 for value in dominant_shares), variant_count
            ),
            "single_line_collapse_variants": _ratio_record(
                sum(bool(row["single_line_collapse"]) for row in source_rows), variant_count
            ),
            "first_line_collapse_variants": _ratio_record(
                sum(bool(row["first_line_collapse"]) for row in source_rows), variant_count
            ),
            "canonical_answer_event_coverage": _ratio_record(answer_covered_variants, variant_count),
            "canonical_answer_event_return_match": _ratio_record(answer_matches, answer_count),
        },
        "outputs": {
            "service_usage_per_case.csv": {"path": str(output_dir / "service_usage_per_case.csv"), "rows": variant_count},
            "service_reuse_matrix.csv": {"path": str(output_dir / "service_reuse_matrix.csv"), "rows": len(reuse_rows)},
            "service_cooccurrence.csv": {"path": str(output_dir / "service_cooccurrence.csv"), "rows": cooccurrence_row_count},
            "source_line_diagnostics.csv": {"path": str(output_dir / "source_line_diagnostics.csv"), "rows": variant_count},
        },
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path.name}")
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: _csv_value(row.get(key))
                    for key in fieldnames
                }
            )


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    if isinstance(value, float):
        return f"{value:.6f}"
    if value is None:
        return ""
    return value


def _safe_rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _ratio_record(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": _safe_rate(numerator, denominator),
    }


def _counter_dict(values: Iterable[int]) -> dict[str, int]:
    return {str(key): value for key, value in sorted(Counter(values).items())}


def _distribution_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "p90": None, "p95": None}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "mean": round(statistics.fmean(ordered), 6),
        "median": round(statistics.median(ordered), 6),
        "p90": round(_nearest_rank(ordered, 0.90), 6),
        "p95": round(_nearest_rank(ordered, 0.95), 6),
    }


def _nearest_rank(values: list[float], quantile: float) -> float:
    index = max(0, min(len(values) - 1, int((len(values) * quantile + 0.999999999) // 1) - 1))
    return values[index]


def _is_trace_session_constructor(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "TraceSession"
    )


def _solve_return_lines(source: str) -> tuple[int, ...]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "solve":
            return tuple(
                sorted(
                    child.lineno
                    for child in ast.walk(node)
                    if isinstance(child, ast.Return)
                )
            )
    return ()


def _is_answer_event(event: dict[str, Any]) -> bool:
    return str(event.get("role") or "").lower() == "answer"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/experiments/plan2_20260722/p0_1_service_audit"),
    )
    parser.add_argument("--expected-cases", type=int, default=200)
    parser.add_argument(
        "--allow-failed",
        action="store_true",
        help="审计成功 artifact，同时在 summary 中保留失败 case 列表。",
    )
    args = parser.parse_args()
    summary = run_service_audit(
        args.report,
        args.output_dir,
        expected_cases=args.expected_cases,
        require_all_ok=not args.allow_failed,
    )
    print(json.dumps({"output_dir": str(args.output_dir), "coverage": summary["coverage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
