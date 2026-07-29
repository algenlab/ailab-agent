from __future__ import annotations

from scripts.generate_llm_simulated_trace_audit_preview import build_preview


def _cases() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for family_index in range(23):
        for case_index in range(3):
            rows.append(
                {
                    "case_id": f"family_{family_index:02d}_case_{case_index}",
                    "title": f"Synthetic case {family_index}-{case_index}",
                    "family_id": f"family_{family_index:02d}",
                    "variant_ids": ["v1", "v2"],
                    "event_counts": [28 + case_index, 31 + case_index],
                }
            )
    return rows


def test_build_preview_is_stratified_reproducible_and_clearly_synthetic() -> None:
    first = build_preview(_cases(), count=60, seed=20260723)
    second = build_preview(_cases(), count=60, seed=20260723)

    assert first == second
    assert first["summary"]["evidence_status"] == "SYNTHETIC_LLM_PREVIEW"
    assert first["summary"]["task_count"] == 60
    assert first["summary"]["family_count"] == 23
    assert first["summary"]["variant_count"] == 120
    assert first["summary"]["critical_error_task_count"] == 1
    assert 55 <= first["summary"]["trace_perfect_task_count"] < 60
    assert all(
        row["evidence_status"] == "SYNTHETIC_LLM_PREVIEW"
        for row in first["task_rows"] + first["variant_rows"] + first["reviewer_rows"]
    )


def test_build_preview_contains_plausible_imperfections_and_reviewer_disagreement() -> None:
    preview = build_preview(_cases(), count=60, seed=20260723)
    summary = preview["summary"]

    assert 0.94 <= summary["source_line_exact_plus_adjacent_rate"] <= 0.99
    assert 0.97 <= summary["reason_state_consistency_rate"] < 1.0
    assert summary["reviewer_disagreement_count"] > 0
    assert 0.60 <= summary["reviewer_trace_perfect_cohen_kappa"] <= 0.90
    assert 0.60 <= summary["reviewer_critical_error_cohen_kappa"] <= 0.90
    assert summary["strong_claim_gate"]["passed"] is False
    assert summary["research_use"] == "workflow_preview_only_not_human_evidence"


def test_build_preview_keeps_a_singleton_family_without_duplicating_its_task() -> None:
    cases = [
        row
        for row in _cases()
        if row["family_id"] != "family_00" or row["case_id"] == "family_00_case_0"
    ]

    preview = build_preview(cases, count=60, seed=20260723)
    singleton_rows = [
        row for row in preview["task_rows"] if row["family_id"] == "family_00"
    ]

    assert len(singleton_rows) == 1
    assert preview["summary"]["family_count"] == 23
