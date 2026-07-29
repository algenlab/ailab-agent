from __future__ import annotations

from scripts.build_plan2_pilot_manifest import (
    allocate_family_quotas,
    build_pilot_manifest,
)


def _records() -> list[dict]:
    records: list[dict] = []
    sizes = {"family_a": 5, "family_b": 3, "family_c": 2}
    for family_id, size in sizes.items():
        for index in range(size):
            records.append(
                {
                    "case_id": f"{family_id}_{index}",
                    "family_id": family_id,
                    "family": family_id,
                    "subfamily_id": f"sub_{index % 2}",
                    "gate_layer": "expansion" if index % 2 else "family_core",
                    "sample_index": 0,
                    "ok": True,
                    "attempt_source": "retry_success" if family_id == "family_b" and index == 1 else "primary",
                }
            )
    return records


def test_allocate_family_quotas_is_capacity_bounded_and_exact() -> None:
    quotas = allocate_family_quotas(_records(), total=6)

    assert quotas == {"family_a": 3, "family_b": 2, "family_c": 1}
    assert sum(quotas.values()) == 6


def test_build_pilot_manifest_is_deterministic_stratified_and_keeps_retry_cases() -> None:
    report = {"results": _records()}

    first = build_pilot_manifest(report, total=6, seed=20260722)
    second = build_pilot_manifest(report, total=6, seed=20260722)

    assert first == second
    assert first["schema_version"] == "plan2-prompt-pilot-manifest-v1"
    assert len(first["case_ids"]) == 6
    assert len(set(first["case_ids"])) == 6
    assert set(first["family_quotas"]) == {"family_a", "family_b", "family_c"}
    assert "family_b_1" in first["case_ids"]
    assert first["coverage"]["family_count"] == 3
    assert first["coverage"]["historical_retry_cases_selected"] == 1
    assert first["protocol"]["sample_index"] == 0
    assert first["protocol"]["shared_order_across_profiles"] is True

