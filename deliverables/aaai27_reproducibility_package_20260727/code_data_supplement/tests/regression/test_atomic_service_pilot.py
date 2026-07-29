from __future__ import annotations

from pathlib import Path

import pytest

from scripts.analyze_atomic_service_pilot import build_atomic_service_pilot_report


ROOT = Path(__file__).resolve().parents[2]


def _generation(mode: str, outcomes: list[tuple[str, bool, bool]], tokens: list[int]) -> dict:
    rows = []
    for (case_id, ok, evidence_ok), total_tokens in zip(outcomes, tokens):
        rows.append(
            {
                "case_id": case_id,
                "family_id": f"family-{case_id}",
                "sample_index": 0,
                "input_data": {"case": case_id},
                "expected": 1,
                "ok": ok,
                "duration_s": 10.0,
                "candidate_summary": {"repair_attempts": 0 if ok else 1},
                "variants": [
                    {
                        "execution_validation": {
                            "ok": evidence_ok,
                            "same_execution_binding": evidence_ok,
                            "prefix_replay_ok": evidence_ok,
                            "unlogged_mutation_count": 0 if evidence_ok else 1,
                            "state_event_mismatch_count": 0,
                        }
                    }
                ],
                "errors": [] if evidence_ok else ["single-execution validation failed: unlogged"],
                "model_calls": [
                    {
                        "usage_available": True,
                        "prompt_tokens": total_tokens // 2,
                        "completion_tokens": total_tokens - total_tokens // 2,
                        "total_tokens": total_tokens,
                        "duration_s": 5.0,
                    }
                ],
            }
        )
    return {
        "config": {
            "execution_mode": mode,
            "benchmark_condition": f"{mode}_service",
            "solutions": 2,
            "max_rounds": 2,
            "max_candidates": 2,
            "model": "demo",
            "llm": {"json_temperature": 0.2},
            "execution_mode_metadata": {"execution_mode": mode},
        },
        "results": rows,
    }


def _machine(condition: str, values: list[tuple[str, bool]]) -> dict:
    return {
        "records": [
            {"case_id": case_id, "condition": condition, "machine_ok": value}
            for case_id, value in values
        ]
    }


def test_pilot_analysis_pairs_outcomes_and_uses_atomic_minus_decoupled_direction() -> None:
    atomic = _generation("atomic", [("a", True, True), ("b", True, True)], [100, 120])
    decoupled = _generation("decoupled", [("a", True, True), ("b", False, False)], [110, 150])

    report = build_atomic_service_pilot_report(
        atomic,
        decoupled,
        _machine("atomic_service", [("a", True), ("b", True)]),
        _machine("decoupled_service", [("a", True), ("b", False)]),
        expected_pairs=2,
        draws=1000,
    )

    assert report["difference_direction"] == "atomic_minus_decoupled"
    assert report["pair_completeness"] == 2
    assert report["binary_metrics"]["machine_ok"]["a_pass"] == 2
    assert report["binary_metrics"]["machine_ok"]["b_pass"] == 1
    assert report["binary_metrics"]["execution_binding"]["a_pass"] == 2
    assert report["binary_metrics"]["execution_binding"]["b_pass"] == 1
    assert report["conditions"]["atomic"]["total_tokens"] == 220
    assert report["conditions"]["decoupled"]["total_tokens"] == 260


def test_full_analysis_reports_sensitivity_after_excluding_pilot_cases() -> None:
    atomic = _generation("atomic", [("a", True, True), ("b", True, True)], [100, 120])
    decoupled = _generation("decoupled", [("a", False, False), ("b", True, True)], [110, 130])

    report = build_atomic_service_pilot_report(
        atomic,
        decoupled,
        _machine("atomic_service", [("a", True), ("b", True)]),
        _machine("decoupled_service", [("a", False), ("b", True)]),
        expected_pairs=2,
        exclude_case_ids={"a"},
        draws=100,
    )

    sensitivity = report["sensitivity_excluding_cases"]
    assert report["excluded_case_ids"] == ["a"]
    assert sensitivity["pair_completeness"] == 1
    assert sensitivity["case_ids"] == ["b"]
    assert sensitivity["binary_metrics"]["machine_ok"]["difference"] == 0


def test_pilot_analysis_rejects_unmatched_cases_and_non_mode_configuration_drift() -> None:
    atomic = _generation("atomic", [("a", True, True), ("b", True, True)], [100, 120])
    decoupled = _generation("decoupled", [("a", True, True)], [110])

    with pytest.raises(ValueError, match="unmatched case IDs"):
        build_atomic_service_pilot_report(
            atomic,
            decoupled,
            _machine("atomic_service", [("a", True), ("b", True)]),
            _machine("decoupled_service", [("a", True)]),
            expected_pairs=2,
        )


def test_pilot_cost_per_valid_tutor_uses_machine_ok_and_missing_evidence_is_unobserved() -> None:
    atomic = _generation("atomic", [("a", True, True)], [100])
    decoupled = _generation("decoupled", [("a", True, True)], [120])
    atomic["results"][0]["variants"] = []

    report = build_atomic_service_pilot_report(
        atomic,
        decoupled,
        _machine("atomic_service", [("a", False)]),
        _machine("decoupled_service", [("a", True)]),
        expected_pairs=1,
        draws=100,
    )

    assert report["conditions"]["atomic"]["tokens_per_machine_ok"] is None
    assert report["conditions"]["decoupled"]["tokens_per_machine_ok"] == 120
    assert report["mechanism_observability"]["execution_validation"]["atomic_observed"] == 0
    assert report["mechanism_observability"]["execution_validation"]["decoupled_observed"] == 1
    assert report["binary_metrics"]["execution_validation"]["pairs"] == 0
    assert "holm_adjusted_p" in report["binary_metrics"]["final_generation_pass"]

    decoupled = _generation("decoupled", [("a", True, True), ("b", True, True)], [110, 130])
    decoupled["config"]["solutions"] = 1
    with pytest.raises(ValueError, match="controlled configuration mismatch.*solutions"):
        build_atomic_service_pilot_report(
            atomic,
            decoupled,
            _machine("atomic_service", [("a", True), ("b", True)]),
            _machine("decoupled_service", [("a", True), ("b", True)]),
            expected_pairs=2,
        )


def test_confirmatory_runner_isolates_outputs_and_freezes_v2_prompt_hash() -> None:
    runner = (ROOT / "scripts" / "run_atomic_service_pilot.sh").read_text(encoding="utf-8")

    assert "atomic_service_manual_claim_pilot" in runner
    assert 'EXPECTED_PROFILE_VERSION="single-execution-pilot-v2"' in runner
    assert "expected_generation_hash" in runner
    assert ".config.execution_mode_metadata.generation_prompt_sha256 == $prompt_hash" in runner


def test_full200_runner_freezes_all_cases_v2_hash_and_pair_count() -> None:
    runner = (ROOT / "scripts" / "run_atomic_service_full200.sh").read_text(encoding="utf-8")

    assert "atomic_service_manual_claim_full200" in runner
    assert "EXPECTED=200" in runner
    assert 'EXPECTED_PROFILE_VERSION="single-execution-pilot-v2"' in runner
    assert "expected_generation_hash" in runner
    assert 'case_args' not in runner
    assert '--expected-pairs "$EXPECTED"' in runner
    assert '--exclude-manifest "$PILOT_MANIFEST"' in runner
    assert 'CONCURRENCY_PER_CONDITION="${CONCURRENCY_PER_CONDITION:-16}"' in runner
    assert '--concurrency "$CONCURRENCY_PER_CONDITION"' in runner
    assert "--resume" in runner
    assert 'local benchmark_status=0' in runner
    assert '|| benchmark_status=$?' in runner
    assert 'generation_complete "$report" "$mode" "$condition" "$prompt_hash"' in runner
