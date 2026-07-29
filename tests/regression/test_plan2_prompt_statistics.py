from __future__ import annotations

import pytest

from algolab.generation.prompt_profiles import prompt_profile_metadata
from scripts.analyze_plan2_prompt_ablation import (
    MACHINE_METRICS,
    build_prompt_ablation_statistics,
)


def _generation(profile: str, rows: list[tuple[str, bool, str]]) -> dict:
    return {
        "config": {
            "sample": 0,
            "solutions": 2,
            "max_rounds": 2,
            "max_candidates": 2,
            "timeout_s": 3000,
            "strict_warnings": True,
            "teaching_enrichment": True,
            "concurrency": 16,
            "prompt_profile": profile,
            "prompt_profile_metadata": prompt_profile_metadata(profile),
            "model": "DeepSeek-V4-Pro",
            "llm": {"max_tokens": 32768, "json_temperature": 0.2},
        },
        "results": [
            {
                "case_id": case_id,
                "ok": ok,
                "problem": f"Problem {case_id}",
                "strategy": f"Strategy {case_id}",
                "input_data": {"value": index},
                "expected": index,
                "sample_index": 0,
                "family_id": "array_pointer",
                "subfamily_id": "scan",
                "case_set": "deterministic",
                "condition": "algolab_full",
                "first_pass_specification_valid": selection == "first_try",
                "candidate_summary": {
                    "selection": selection,
                    "unknown_dsl_call_failure_count": 0,
                },
                **(
                    {
                        "variants": [{"id": "v1"}, {"id": "v2"}],
                        "release_gate": {"multi_solution_ready": True, "release_ready": True},
                    }
                    if ok
                    else {"failure_type": "generation"}
                ),
                "duration_s": 10 + index,
                "model_calls": [
                    {"total_tokens": 100 + index, "duration_s": 2.0},
                    {"total_tokens": 50, "duration_s": 1.0},
                ],
            }
            for index, (case_id, ok, selection) in enumerate(rows)
        ],
    }


def _machine(profile: str, values: list[tuple[str, bool]]) -> dict:
    return {
        "records": [
            {
                "case_id": case_id,
                "condition": profile,
                "machine_ok": value,
                "page_load_ok": True,
                "visible_answer_match": True,
                "interaction_reachable": value,
                "correct_feedback_ok": value,
                "wrong_feedback_ok": value,
                "hint_ok": value,
                "show_answer_ok": value,
                "learning_log_ok": value,
                "mutation_free_ok": True,
            }
            for case_id, value in values
        ]
    }


def _service_bundle(
    *,
    case_values: list[tuple[str, int, int, bool, bool, float]],
    family_reuse: list[str],
    macro_reuse: list[str],
) -> dict:
    usage_rows = []
    source_rows = []
    for case_id, service_count, unknown_count, single_collapse, first_collapse, dominant in case_values:
        usage_rows.append(
            {
                "case_id": case_id,
                "case_service_count": str(service_count),
                "out_of_catalog_call_count": str(unknown_count),
                "tracker_syntax_error": "",
            }
        )
        source_rows.append(
            {
                "case_id": case_id,
                "single_line_collapse": str(single_collapse),
                "first_line_collapse": str(first_collapse),
                "dominant_code_line_share": str(dominant),
            }
        )
    return {
        "summary": {
            "coverage": {"case_count": len(case_values), "skipped_failed_case_ids": []},
            "service_usage": {
                "used_service_count": 6,
                "multi_service_cases": {
                    "numerator": sum(service_count >= 2 for _, service_count, *_ in case_values),
                    "denominator": len(case_values),
                },
                "outside_catalog_calls": [],
            },
            "reuse": {
                "services_crossing_2plus_families": family_reuse,
                "services_crossing_2plus_macro_groups": macro_reuse,
            },
        },
        "service_usage_rows": usage_rows,
        "source_line_rows": source_rows,
    }


def test_prompt_ablation_statistics_are_paired_and_apply_noninferiority_rule() -> None:
    hybrid = _generation(
        "hybrid_current",
        [("a", True, "first_try"), ("b", True, "repair"), ("c", False, "failed")],
    )
    service = _generation(
        "service_only",
        [("a", True, "first_try"), ("b", False, "failed"), ("c", True, "regen_first_try")],
    )
    hybrid_machine = _machine("hybrid_current", [("a", True), ("b", True), ("c", False)])
    service_machine = _machine("service_only", [("a", True), ("b", False), ("c", True)])

    result = build_prompt_ablation_statistics(
        hybrid,
        service,
        hybrid_machine,
        service_machine,
        expected_pairs=3,
        seed=7,
        draws=2000,
    )

    assert result["pair_completeness"] == 3
    assert result["conditions"] == {"left": "service_only", "right": "hybrid_current"}
    assert result["binary_metrics"]["final_generation_pass"]["a_pass"] == 2
    assert result["binary_metrics"]["final_generation_pass"]["b_pass"] == 2
    assert result["binary_metrics"]["first_pass_specification_validity"]["a_pass"] == 1
    assert result["binary_metrics"]["machine_ok"]["a_only"] == 1
    assert result["binary_metrics"]["machine_ok"]["b_only"] == 1
    assert "holm_adjusted_p" in result["binary_metrics"]["machine_ok"]
    assert result["continuous_metrics"]["model_calls"]["pairs"] == 3
    assert result["continuous_metrics"]["total_tokens"]["pairs"] == 3
    assert result["configuration_parity"]["all_controlled_fields_match"] is True
    assert result["configuration_parity"]["controlled_fields"]["llm.json_temperature"] == {
        "hybrid_current": 0.2,
        "service_only": 0.2,
        "match": True,
    }
    assert result["noninferiority"]["margin"] == -0.03
    assert result["noninferiority"]["metric"] == "machine_ok"
    assert result["noninferiority"]["passed"] is False
    assert result["paired_payload_sha256"]
    assert result["binary_metrics"]["unknown_dsl_call_free"]["a_pass"] == 3


def test_prompt_ablation_statistics_include_service_and_source_line_metrics() -> None:
    generation_rows = [("a", True, "first_try"), ("b", True, "first_try"), ("c", True, "repair")]
    machine_rows = [("a", True), ("b", True), ("c", True)]
    hybrid_bundle = _service_bundle(
        case_values=[
            ("a", 2, 0, False, False, 0.4),
            ("b", 3, 0, True, True, 1.0),
            ("c", 1, 1, False, False, 0.5),
        ],
        family_reuse=["array", "scalar"],
        macro_reuse=["array"],
    )
    service_bundle = _service_bundle(
        case_values=[
            ("a", 1, 0, False, False, 0.3),
            ("b", 2, 0, False, False, 0.6),
            ("c", 2, 0, False, False, 0.4),
        ],
        family_reuse=["array", "scalar", "table"],
        macro_reuse=["array", "table"],
    )

    result = build_prompt_ablation_statistics(
        _generation("hybrid_current", generation_rows),
        _generation("service_only", generation_rows),
        _machine("hybrid_current", machine_rows),
        _machine("service_only", machine_rows),
        hybrid_service_bundle=hybrid_bundle,
        service_service_bundle=service_bundle,
        expected_pairs=3,
        seed=9,
        draws=1000,
    )

    assert result["service_composition"]["paired_cases"] == 3
    assert result["binary_metrics"]["unknown_dsl_call_free"]["a_pass"] == 3
    assert result["binary_metrics"]["unknown_dsl_call_free"]["b_pass"] == 2
    assert result["binary_metrics"]["single_line_collapse_free"]["a_pass"] == 3
    assert result["binary_metrics"]["single_line_collapse_free"]["b_pass"] == 2
    assert result["continuous_metrics"]["case_service_count"]["pairs"] == 3
    assert result["continuous_metrics"]["dominant_code_line_share"]["pairs"] == 3
    assert result["service_composition"]["service_only"]["cross_family_reused_services"] == 3
    assert result["service_composition"]["hybrid_current"]["cross_macro_reused_services"] == 1
    assert result["service_composition"]["definitions"]["paired_service_unit"] == (
        "case successful in both prompt profiles"
    )


def test_prompt_ablation_statistics_reject_config_payload_and_infrastructure_mismatch() -> None:
    rows = [("a", True, "first_try"), ("b", True, "first_try")]
    machine = [("a", True), ("b", True)]

    bad_config = _generation("service_only", rows)
    bad_config["config"]["solutions"] = 1
    with pytest.raises(ValueError, match="controlled configuration mismatch"):
        build_prompt_ablation_statistics(
            _generation("hybrid_current", rows),
            bad_config,
            _machine("hybrid_current", machine),
            _machine("service_only", machine),
            expected_pairs=2,
            draws=100,
        )

    bad_payload = _generation("service_only", rows)
    bad_payload["results"][0]["expected"] = 999
    with pytest.raises(ValueError, match="paired payload mismatch"):
        build_prompt_ablation_statistics(
            _generation("hybrid_current", rows),
            bad_payload,
            _machine("hybrid_current", machine),
            _machine("service_only", machine),
            expected_pairs=2,
            draws=100,
        )

    infrastructure = _generation("service_only", rows)
    infrastructure["results"][0].update(ok=False, failure_type="api_transport")
    infrastructure["results"][0].pop("variants", None)
    infrastructure["results"][0].pop("release_gate", None)
    with pytest.raises(ValueError, match="infrastructure failure"):
        build_prompt_ablation_statistics(
            _generation("hybrid_current", rows),
            infrastructure,
            _machine("hybrid_current", machine),
            _machine("service_only", machine),
            expected_pairs=2,
            draws=100,
        )


def test_first_pass_metric_uses_recorded_initial_spec_validity_not_selection_label() -> None:
    rows = [("a", True, "first_try")]
    service = _generation("service_only", rows)
    service["results"][0]["first_pass_specification_valid"] = False

    result = build_prompt_ablation_statistics(
        _generation("hybrid_current", rows),
        service,
        _machine("hybrid_current", [("a", True)]),
        _machine("service_only", [("a", True)]),
        expected_pairs=1,
        draws=100,
    )

    assert result["binary_metrics"]["first_pass_specification_validity"]["a_pass"] == 0
    assert result["binary_metrics"]["first_pass_specification_validity"]["b_pass"] == 1


@pytest.mark.parametrize("invalid_value", [None, "true", 1])
def test_prompt_ablation_statistics_reject_missing_or_non_boolean_first_pass(
    invalid_value: object,
) -> None:
    rows = [("a", True, "first_try")]
    service = _generation("service_only", rows)
    if invalid_value is None:
        service["results"][0].pop("first_pass_specification_valid")
    else:
        service["results"][0]["first_pass_specification_valid"] = invalid_value

    with pytest.raises(ValueError, match="first_pass_specification_valid"):
        build_prompt_ablation_statistics(
            _generation("hybrid_current", rows),
            service,
            _machine("hybrid_current", [("a", True)]),
            _machine("service_only", [("a", True)]),
            expected_pairs=1,
            draws=100,
        )


@pytest.mark.parametrize(
    ("pollution", "message"),
    [
        ("metadata_not_dict", "profile metadata"),
        ("profile_metadata", "profile metadata"),
        ("metadata_profile", "profile metadata"),
        ("metadata_strategy_policy", "profile metadata"),
        ("single_variant", "exactly 2 valid variants"),
        ("bad_gate", "release gate"),
    ],
)
def test_prompt_ablation_statistics_reject_profile_metadata_and_invalid_success_release(
    pollution: str,
    message: str,
) -> None:
    rows = [("a", True, "first_try")]
    machine = [("a", True)]
    service = _generation("service_only", rows)
    if pollution == "metadata_not_dict":
        service["config"]["prompt_profile_metadata"] = "stale"
    elif pollution == "profile_metadata":
        service["config"]["prompt_profile_metadata"]["profile_version"] = "stale"
    elif pollution == "metadata_profile":
        service["config"]["prompt_profile_metadata"]["prompt_profile"] = "hybrid_current"
    elif pollution == "metadata_strategy_policy":
        service["config"]["prompt_profile_metadata"]["strategy_hint_policy"] = "benchmark_strategy"
    elif pollution == "single_variant":
        service["results"][0]["variants"] = [{"id": "v1"}]
    else:
        service["results"][0]["release_gate"]["multi_solution_ready"] = False

    with pytest.raises(ValueError, match=message):
        build_prompt_ablation_statistics(
            _generation("hybrid_current", rows),
            service,
            _machine("hybrid_current", machine),
            _machine("service_only", machine),
            expected_pairs=1,
            draws=100,
        )


@pytest.mark.parametrize(
    ("variants", "message"),
    [
        ([None, None], "variant 0 must be a dict"),
        ([{"id": "v1"}, "v2"], "variant 1 must be a dict"),
        ([{"id": "   "}, {"id": "v2"}], "variant 0 has invalid id"),
        ([{"id": "same"}, {"id": " same "}], "unique variant ids"),
    ],
)
def test_prompt_ablation_statistics_reject_invalid_success_variants(
    variants: list[object],
    message: str,
) -> None:
    rows = [("a", True, "first_try")]
    service = _generation("service_only", rows)
    service["results"][0]["variants"] = variants

    with pytest.raises(ValueError, match=message):
        build_prompt_ablation_statistics(
            _generation("hybrid_current", rows),
            service,
            _machine("hybrid_current", [("a", True)]),
            _machine("service_only", [("a", True)]),
            expected_pairs=1,
            draws=100,
        )


@pytest.mark.parametrize("pollution", ["missing_metric", "non_boolean_metric", "wrong_condition"])
def test_prompt_ablation_statistics_reject_machine_record_pollution(pollution: str) -> None:
    rows = [("a", True, "first_try")]
    service_machine = _machine("service_only", [("a", True)])
    if pollution == "missing_metric":
        service_machine["records"][0].pop("hint_ok")
    elif pollution == "non_boolean_metric":
        service_machine["records"][0]["hint_ok"] = 1
    else:
        service_machine["records"].append(
            {
                **service_machine["records"][0],
                "case_id": "polluted",
                "condition": "hybrid_current",
            }
        )

    with pytest.raises(ValueError, match="machine service_only"):
        build_prompt_ablation_statistics(
            _generation("hybrid_current", rows),
            _generation("service_only", rows),
            _machine("hybrid_current", [("a", True)]),
            service_machine,
            expected_pairs=1,
            draws=100,
        )


@pytest.mark.parametrize("mismatch", ["false_positive", "false_negative"])
def test_prompt_ablation_statistics_reject_inconsistent_machine_ok(mismatch: str) -> None:
    rows = [("a", True, "first_try")]
    service_machine = _machine("service_only", [("a", True)])
    record = service_machine["records"][0]
    for metric in MACHINE_METRICS:
        record[metric] = True
    if mismatch == "false_positive":
        record["hint_ok"] = False
    else:
        record["machine_ok"] = False

    with pytest.raises(ValueError, match="machine_ok must equal"):
        build_prompt_ablation_statistics(
            _generation("hybrid_current", rows),
            _generation("service_only", rows),
            _machine("hybrid_current", [("a", True)]),
            service_machine,
            expected_pairs=1,
            draws=100,
        )
