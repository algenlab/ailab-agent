#!/usr/bin/env python3
"""Build the deterministic stratified 60-case pilot for Plan-2 P0-2."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def allocate_family_quotas(records: list[dict[str, Any]], *, total: int) -> dict[str, int]:
    grouped = _group_records(records)
    family_ids = sorted(grouped)
    if total < len(family_ids):
        raise ValueError(f"total={total} cannot cover all {len(family_ids)} families")
    if total > len(records):
        raise ValueError(f"total={total} exceeds available records={len(records)}")

    quotas = {family_id: 1 for family_id in family_ids}
    remaining = total - len(family_ids)
    capacities = {family_id: len(grouped[family_id]) - 1 for family_id in family_ids}
    capacity_total = sum(capacities.values())
    if not remaining:
        return quotas
    if capacity_total < remaining:
        raise ValueError("family capacities cannot satisfy requested pilot size")

    raw_extra = {
        family_id: remaining * capacities[family_id] / capacity_total
        for family_id in family_ids
    }
    for family_id in family_ids:
        quotas[family_id] += min(capacities[family_id], math.floor(raw_extra[family_id]))

    unassigned = total - sum(quotas.values())
    order = sorted(
        family_ids,
        key=lambda family_id: (
            -(raw_extra[family_id] - math.floor(raw_extra[family_id])),
            family_id,
        ),
    )
    while unassigned:
        progressed = False
        for family_id in order:
            if quotas[family_id] >= len(grouped[family_id]):
                continue
            quotas[family_id] += 1
            unassigned -= 1
            progressed = True
            if not unassigned:
                break
        if not progressed:
            raise ValueError("could not assign all pilot slots")
    return quotas


def build_pilot_manifest(
    report: dict[str, Any],
    *,
    total: int = 60,
    seed: int = 20260722,
    report_path: str = "",
    report_sha256: str = "",
) -> dict[str, Any]:
    records = [dict(row) for row in report.get("results") or []]
    _validate_records(records)
    quotas = allocate_family_quotas(records, total=total)
    grouped = _group_records(records)
    index_by_case = {str(row["case_id"]): index for index, row in enumerate(records)}
    selected: list[dict[str, Any]] = []
    for family_id in sorted(grouped):
        selected.extend(_select_family_records(grouped[family_id], quotas[family_id], seed=seed))
    selected.sort(key=lambda row: index_by_case[str(row["case_id"])])

    case_ids = [str(row["case_id"]) for row in selected]
    retry_all = {
        str(row["case_id"])
        for row in records
        if str(row.get("attempt_source") or "primary") != "primary"
    }
    retry_selected = retry_all & set(case_ids)
    entries = [
        {
            "order": order,
            "case_id": str(row["case_id"]),
            "family_id": str(row.get("family_id") or ""),
            "family": str(row.get("family") or ""),
            "subfamily_id": str(row.get("subfamily_id") or ""),
            "gate_layer": str(row.get("gate_layer") or ""),
            "attempt_source": str(row.get("attempt_source") or "primary"),
            "source_report_order": index_by_case[str(row["case_id"])],
        }
        for order, row in enumerate(selected)
    ]
    return {
        "kind": "plan2_prompt_ablation_pilot_manifest",
        "schema_version": "plan2-prompt-pilot-manifest-v1",
        "inputs": {
            "report_path": report_path,
            "report_sha256": report_sha256,
            "source_case_count": len(records),
        },
        "protocol": {
            "seed": seed,
            "target_cases": total,
            "sample_index": 0,
            "allocation": "one_per_family_then_hamilton_over_remaining_capacity",
            "within_family_selection": "retry_first_then_gate_and_subfamily_diversity_then_seeded_hash",
            "shared_order_across_profiles": True,
            "prompt_profiles": ["hybrid_current", "service_only"],
        },
        "family_quotas": quotas,
        "coverage": {
            "case_count": len(case_ids),
            "family_count": len({str(row.get("family_id") or "") for row in selected}),
            "subfamily_count": len({str(row.get("subfamily_id") or "") for row in selected}),
            "gate_layers": sorted({str(row.get("gate_layer") or "") for row in selected}),
            "historical_retry_cases_available": len(retry_all),
            "historical_retry_cases_selected": len(retry_selected),
            "all_historical_retry_cases_included": retry_selected == retry_all,
        },
        "case_ids": case_ids,
        "cases": entries,
    }


def _validate_records(records: list[dict[str, Any]]) -> None:
    if not records:
        raise ValueError("source report has no results")
    case_ids = [str(row.get("case_id") or "") for row in records]
    if not all(case_ids) or len(set(case_ids)) != len(case_ids):
        raise ValueError("source report case ids must be non-empty and unique")
    bad_samples = [case_id for case_id, row in zip(case_ids, records) if row.get("sample_index") != 0]
    if bad_samples:
        raise ValueError(f"source report contains non-zero sample rows: {bad_samples[:5]}")
    failed = [case_id for case_id, row in zip(case_ids, records) if row.get("ok") is not True]
    if failed:
        raise ValueError(f"source report contains failed rows: {failed[:5]}")
    missing_family = [case_id for case_id, row in zip(case_ids, records) if not row.get("family_id")]
    if missing_family:
        raise ValueError(f"source report rows missing family_id: {missing_family[:5]}")


def _group_records(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[str(row.get("family_id") or "")].append(row)
    return dict(grouped)


def _select_family_records(
    records: list[dict[str, Any]],
    quota: int,
    *,
    seed: int,
) -> list[dict[str, Any]]:
    remaining = list(records)
    selected: list[dict[str, Any]] = []
    covered_gates: set[str] = set()
    covered_subfamilies: set[str] = set()
    while len(selected) < quota:
        if not remaining:
            raise ValueError("family quota exceeds family capacity")
        choice = min(
            remaining,
            key=lambda row: (
                0 if str(row.get("attempt_source") or "primary") != "primary" else 1,
                0 if str(row.get("gate_layer") or "") not in covered_gates else 1,
                0 if str(row.get("subfamily_id") or "") not in covered_subfamilies else 1,
                _stable_hash(seed, str(row.get("case_id") or "")),
            ),
        )
        selected.append(choice)
        remaining.remove(choice)
        covered_gates.add(str(choice.get("gate_layer") or ""))
        covered_subfamilies.add(str(choice.get("subfamily_id") or ""))
    return selected


def _stable_hash(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/experiments/plan2_20260722/p0_2_prompt_ablation/pilot_manifest.json"),
    )
    parser.add_argument("--total", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20260722)
    args = parser.parse_args()
    report_bytes = args.report.read_bytes()
    report = json.loads(report_bytes)
    manifest = build_pilot_manifest(
        report,
        total=args.total,
        seed=args.seed,
        report_path=str(args.report.resolve()),
        report_sha256=hashlib.sha256(report_bytes).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "coverage": manifest["coverage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

