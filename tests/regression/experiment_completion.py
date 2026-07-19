from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path


def _semantic_trace(events: list[dict]) -> object:
    from algolab.schemas.semantic_trace import SemanticTrace

    return SemanticTrace.model_validate(
        {
            "algorithm": "validator-test",
            "input_data": {"nums": [1, 2]},
            "result": 2,
            "events": events,
        }
    )


def _event(
    step: int,
    op: str,
    *,
    targets: list[str] | None = None,
    deps: list[str] | None = None,
    state: dict | None = None,
    before: object = None,
    after: object = None,
    role: str = "",
) -> dict:
    return {
        "step": step,
        "op": op,
        "targets": [{"id": target} for target in (targets or [])],
        "deps": [{"id": dep} for dep in (deps or [])],
        "state": state or {},
        "before": before,
        "after": after,
        "role": role,
        "reason": f"{op} step",
        "code_line": 1,
    }


def test_scene_validator_rejects_dangling_object_references() -> None:
    from algolab.schemas.scene_graph import SceneGraph
    from algolab.verification.scene_validator import validate_scene

    scene = SceneGraph.model_validate(
        {
            "algorithm": "scene-reference-test",
            "input_data": {},
            "frames": [
                {
                    "step": 0,
                    "title": "broken",
                    "description": "broken refs",
                    "operation": "create",
                    "objects": [
                        {"id": "cell:0", "type": "cell", "parent": "missing:parent"},
                        {
                            "id": "edge:0",
                            "type": "edge",
                            "source": "missing:source",
                            "target": "missing:target",
                        },
                    ],
                    "marks": [{"target": "missing:mark", "role": "current"}],
                }
            ],
        }
    )

    errors, _warnings = validate_scene(scene)

    assert any("missing:mark" in error for error in errors)
    assert any("missing:parent" in error for error in errors)
    assert any("missing:source" in error for error in errors)
    assert any("missing:target" in error for error in errors)


def test_process_validator_rejects_reversed_trace_even_after_step_renumbering() -> None:
    from algolab.verification.process_validator import validate_process

    trace = _semantic_trace(
        [
            _event(0, "mark", targets=["answer"], state={"nums": [2, 1], "answer": 2}, role="answer"),
            _event(1, "set", targets=["nums[0]"], state={"nums": [2, 1]}, before=1, after=2),
            _event(2, "create", targets=["nums"], state={"nums": [1, 2]}),
        ]
    )

    errors, _warnings = validate_process(trace)

    assert errors
    assert any("初始化" in error or "因果" in error or "状态" in error for error in errors)


def test_process_validator_rejects_explicit_before_after_discontinuity() -> None:
    from algolab.verification.process_validator import validate_process

    trace = _semantic_trace(
        [
            _event(0, "create", targets=["nums"], state={"nums": [1, 2]}),
            _event(1, "set", targets=["nums[0]"], state={"nums": [2, 2]}, before=999, after=2),
        ]
    )

    errors, _warnings = validate_process(trace)

    assert any("before" in error for error in errors)


def test_process_validator_rejects_unbalanced_phase_events() -> None:
    from algolab.verification.process_validator import validate_process

    trace = _semantic_trace(
        [
            _event(0, "create", targets=["nums"], state={"nums": [1, 2]}),
            _event(1, "exit", targets=["frame:phase/search"], state={"nums": [1, 2]}),
        ]
    )

    errors, _warnings = validate_process(trace)

    assert any("exit" in error or "阶段" in error for error in errors)


def test_browser_repair_detects_external_resources_without_hidden_metrics() -> None:
    from scripts.run_direct_browser_repair_baseline import (
        build_browser_repair_prompt,
        external_resource_urls,
    )

    html = '''
    <html>
      <head>
        <link href="https://fonts.example/x.css">
        <style>.hero { background-image: url("https://cdn.example/hero.png"); }</style>
      </head>
      <body>
        <svg xmlns="http://www.w3.org/2000/svg"></svg>
        <script src="/local.js"></script>
        <p>复杂度提示：https://2=2，不是网络资源。</p>
      </body>
    </html>
    '''
    assert external_resource_urls(html) == [
        "https://cdn.example/hero.png",
        "https://fonts.example/x.css",
    ]

    prompt = build_browser_repair_prompt(
        title="Binary Search",
        problem="find target",
        family="binary search",
        strategy="binary search",
        input_data={"nums": [1, 2], "target": 2},
        expected=1,
        previous_html="<html><body>draft</body></html>",
        feedback={"console_errors": ["ReferenceError: x"], "interactive_elements": 2},
        round_index=2,
    )

    assert "ReferenceError: x" in prompt
    assert "#answer" not in prompt
    assert "correct_feedback_ok" not in prompt
    assert "hidden" not in prompt.lower()


def test_browser_repair_budget_report_uses_latest_available_round(tmp_path: Path) -> None:
    from scripts.run_direct_browser_repair_baseline import (
        build_budget_report,
        refresh_external_resource_annotations,
    )

    final_html = tmp_path / "a3.html"
    final_html.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
    final_feedback = tmp_path / "a3.feedback.json"
    final_feedback.write_text(
        '{"external_requests": ["https://api.example/data.json"]}',
        encoding="utf-8",
    )
    final_report = {
        "results": [
            {
                "case_id": "a",
                "title": "A",
                "family": "f",
                "input_data": {"x": 1},
                "expected": 2,
                "attempts": [
                    {"call_index": 1, "html": "a1.html", "json": "a1.json"},
                    {"call_index": 2, "html": "a2.html", "json": "a2.json"},
                    {
                        "call_index": 3,
                        "html": str(final_html),
                        "json": "a3.json",
                        "feedback": str(final_feedback),
                        "external_resource_urls": ["http://www.w3.org/2000/svg"],
                    },
                ],
            }
        ]
    }

    budget = build_budget_report(final_report, call_budget=5)

    assert budget["results"][0]["html"] == str(final_html)
    assert budget["results"][0]["selected_call_index"] == 3
    assert budget["results"][0]["call_budget"] == 5
    assert budget["results"][0]["external_resource_urls"] == []
    assert budget["results"][0]["observed_external_requests"] == ["https://api.example/data.json"]

    refreshed = refresh_external_resource_annotations(final_report)

    assert refreshed["results"][0]["attempts"][-1]["external_resource_urls"] == []
    assert refreshed["external_resource_cases_final"] == 1


def test_browser_repair_refreshes_cached_feedback_resource_urls(tmp_path: Path) -> None:
    from scripts.run_direct_browser_repair_baseline import _ensure_feedback

    html_path = tmp_path / "attempt_01.html"
    html_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
    metadata_path = tmp_path / "attempt_01.json"
    feedback_path = tmp_path / "attempt_01.feedback.json"
    feedback_path.write_text(
        '{"page_load_ok": true, "external_resource_urls": ["http://www.w3.org/2000/svg"]}',
        encoding="utf-8",
    )
    attempt = {
        "html": str(html_path),
        "json": str(metadata_path),
        "external_resource_urls": ["http://www.w3.org/2000/svg"],
    }

    feedback = _ensure_feedback(attempt, timeout_ms=1000)

    assert feedback["external_resource_urls"] == []
    assert attempt["external_resource_urls"] == []


def test_nondegenerate_ablation_selection_is_deterministic_and_covers_families() -> None:
    from scripts.run_direct_to_scenegraph_ablation import select_ablation_rows

    rows = [
        {"case_id": f"case-{family}-{index}", "family_id": family, "subfamily_id": f"sub-{index}"}
        for family in (f"family-{index}" for index in range(23))
        for index in range(3)
    ]

    selected_a = select_ablation_rows(rows, count=50, seed=20260713)
    selected_b = select_ablation_rows(rows, count=50, seed=20260713)

    assert [row["case_id"] for row in selected_a] == [row["case_id"] for row in selected_b]
    assert len({row["case_id"] for row in selected_a}) == 50
    assert {row["family_id"] for row in selected_a} == {f"family-{index}" for index in range(23)}


def test_direct_scenegraph_artifact_keeps_runtime_but_has_no_verified_trace() -> None:
    from scripts.run_direct_to_scenegraph_ablation import build_artifact_from_scene

    scene = {
        "algorithm": "direct-scene",
        "input_data": {"nums": [1, 2]},
        "result": 2,
        "pseudocode": ["return len(nums)"],
        "frames": [
            {
                "step": 0,
                "title": "answer",
                "description": "show result",
                "operation": "explain",
                "objects": [{"id": "answer", "type": "label", "value": 2}],
                "marks": [{"target": "answer", "role": "answer"}],
                "state": {"answer": 2},
                "interaction": {
                    "type": "judge",
                    "prompt": "The answer is 2",
                    "answer": True,
                    "explanation": "Correct",
                    "wrong_explanation": "Check the length",
                },
                "teaching": {"what": "Return the length", "why": "It is requested", "hint": "Count"},
            }
        ],
    }

    artifact = build_artifact_from_scene(
        title="Length",
        strategy="count",
        expected=2,
        scene_data=scene,
    )

    assert artifact.scenes["direct_scenegraph"].result == 2
    assert artifact.variants[0].trace is None
    assert artifact.validation.release_gate.visual_ready is True
    assert artifact.validation.release_gate.process_ready is False


def test_verified_trace_html_prompt_preserves_trace_facts_without_runtime_contract() -> None:
    from scripts.run_verified_trace_to_html_ablation import build_verified_trace_html_prompt

    prompt = build_verified_trace_html_prompt(
        title="Binary Search",
        problem="find target",
        family="binary search",
        strategy="halve interval",
        input_data={"nums": [1, 2], "target": 2},
        expected=1,
        trace={"algorithm": "binary search", "result": 1, "events": [{"step": 0, "op": "create"}]},
    )

    assert '"result": 1' in prompt
    assert "SceneGraph" not in prompt
    assert "fixed Runtime" not in prompt
    assert "self-contained" in prompt


def test_cross_model_candidates_exclude_primary_and_preserve_priority() -> None:
    from scripts.run_cross_model_generation_experiment import candidate_models

    assert candidate_models(
        primary_model="DeepSeek-V4-Pro",
        configured="gemini-3-flash-preview,DeepSeek-V4-Pro,qwen3-coder",
    ) == ["gemini-3-flash-preview", "qwen3-coder"]


def test_cross_model_commands_use_identical_case_selection(tmp_path: Path) -> None:
    from scripts.run_cross_model_generation_experiment import build_method_commands

    commands = build_method_commands(
        python_executable="/fixed/python3",
        case_ids=["a", "b"],
        output_dir=tmp_path,
    )

    assert set(commands) == {"stage1", "direct"}
    for command in commands.values():
        assert command.count("--case") == 2
        assert "a" in command and "b" in command
        assert command[0] == "/fixed/python3"


def test_heldout_benchmark_has_40_new_oracle_checked_cases() -> None:
    from benchmark.cases import benchmark_cases
    from scripts.freeze_heldout_benchmark import build_heldout_benchmark
    from scripts.run_llm_benchmark import load_family_capabilities, strong_family_ids_from_capabilities

    payload = build_heldout_benchmark()
    cases = payload["cases"]
    ids = [case["id"] for case in cases]
    existing = {case.id for case in benchmark_cases()}

    assert len(cases) == 40
    assert len(set(ids)) == 40
    assert not (set(ids) & existing)
    assert {case["family_id"] for case in cases} == strong_family_ids_from_capabilities(load_family_capabilities())
    assert all(case["samples"][0]["expected_sha256"] for case in cases)
    assert all(case["source"]["url"].startswith("https://") for case in cases)


def test_audit_condition_selection_supports_algolab_only() -> None:
    from scripts.run_interaction_semantic_eval import audit_condition_names, output_condition_name

    assert audit_condition_names(algolab_only=True, direct_only=False) == ("algolab_full",)
    assert audit_condition_names(algolab_only=False, direct_only=True) == ("direct_html",)
    assert audit_condition_names(algolab_only=False, direct_only=False) == ("algolab_full", "direct_html")
    assert output_condition_name(
        "direct_html",
        algolab_condition="algolab_full",
        direct_condition="direct_browser_repair_5",
    ) == "direct_browser_repair_5"


def test_swapped_blind_order_reverses_frozen_assignment() -> None:
    from scripts.run_external_eval_methods import blind_labels_for_case

    frozen = blind_labels_for_case("binary_search", order="frozen")
    swapped = blind_labels_for_case("binary_search", order="swapped")

    assert swapped == {"A": frozen["B"], "B": frozen["A"]}


def test_ablation_swapped_order_reverses_frozen_assignment() -> None:
    from scripts.run_ablation_pair_reviews import ablation_blind_map

    frozen = ablation_blind_map("binary_search", "no_teaching", order="frozen")
    swapped = ablation_blind_map("binary_search", "no_teaching", order="swapped")

    assert swapped == {"A": frozen["B"], "B": frozen["A"]}
    assert set(frozen.values()) == {"full", "no_teaching"}


def test_component_ablation_report_preserves_source_metadata(tmp_path: Path) -> None:
    from scripts.build_full200_ablation_conditions import build_variant_report

    source_report = {
        "results": [
            {
                "case_id": "binary_search",
                "title": "Binary Search",
                "family_id": "binary_search",
                "subfamily_id": "closed_interval_search",
                "sample_index": 0,
                "input_data": {"nums": [1, 2], "target": 2},
                "expected": 1,
                "ok": True,
                "json": "source.json",
                "html": "source.html",
            }
        ]
    }
    manifest = {
        "exports": [
            {
                "source_artifact": "source.json",
                "variant": "no_interaction",
                "json": str(tmp_path / "derived.json"),
                "html": str(tmp_path / "derived.html"),
                "counts": {"scene_interaction_frames": 0},
            }
        ]
    }

    report = build_variant_report(source_report, manifest, "no_interaction")

    assert report["total"] == 1
    assert report["results"][0]["case_id"] == "binary_search"
    assert report["results"][0]["condition"] == "no_interaction"
    assert report["results"][0]["html"].endswith("derived.html")
    assert report["results"][0]["component_counts"]["scene_interaction_frames"] == 0


def test_no_repair_report_marks_missing_primary_cases_as_failures() -> None:
    from scripts.build_full200_ablation_conditions import build_no_repair_report

    final_report = {
        "results": [
            {"case_id": "a", "ok": True, "json": "a.json", "html": "a.html"},
            {"case_id": "b", "ok": True, "json": "b-final.json", "html": "b-final.html"},
        ]
    }
    primary_report = {
        "results": [
            {"case_id": "a", "ok": True, "json": "a.json", "html": "a.html"},
            {"case_id": "b", "ok": False, "error": "generation failed"},
        ]
    }

    report = build_no_repair_report(primary_report, final_report)

    assert report["total"] == 2
    assert report["passed"] == 1
    failed = next(row for row in report["results"] if row["case_id"] == "b")
    assert failed["condition"] == "no_repair"
    assert failed["ok"] is False
    assert failed["generation_failed"] is True


def test_fault_injection_supports_extended_trace_faults() -> None:
    from scripts.run_gate_fault_injection import inject_fault

    artifact = {
        "expected_result": 1,
        "variants": [
            {
                "code": "def solve(input_data):\n    return 1",
                "tracker_code": (
                    "def trace(input_data):\n"
                    "    return {'input_data': input_data, 'result': 1, 'events': ["
                    "{'step': 0, 'op': 'create', 'targets': [{'id': 'nums'}], 'state': {'x': 1}, "
                    "'interaction': {'type': 'input', 'prompt': 'x?', 'answer': 1}}]}"
                ),
            }
        ],
    }

    deleted = inject_fault(copy.deepcopy(artifact), "trace_event_deleted")
    reordered = inject_fault(copy.deepcopy(artifact), "trace_event_reordered")
    state = inject_fault(copy.deepcopy(artifact), "trace_state_wrong")
    interaction = inject_fault(copy.deepcopy(artifact), "interaction_answer_wrong")
    missing_target = inject_fault(copy.deepcopy(artifact), "trace_target_missing")

    assert "events'] = t.get('events', [])[1:]" in deleted["variants"][0]["tracker_code"]
    assert "events.reverse()" in reordered["variants"][0]["tracker_code"]
    assert "__algolab_fault_state__" in state["variants"][0]["tracker_code"]
    assert "__algolab_fault_answer__" in interaction["variants"][0]["tracker_code"]
    assert "__algolab_missing__[999999]" in missing_target["variants"][0]["tracker_code"]


def test_fault_summary_separates_clean_control_false_rejections() -> None:
    from scripts.run_gate_fault_injection import summarize_fault_rows

    rows = [
        {"fault_type": "clean_control", "is_control": True, "rejected": False, "family_id": "f"},
        {"fault_type": "clean_control", "is_control": True, "rejected": True, "family_id": "f"},
        {
            "fault_type": "trace_result_wrong",
            "is_control": False,
            "rejected": True,
            "family_id": "f",
            "validation_layer": "trace_result",
        },
    ]

    summary = summarize_fault_rows(rows)

    assert summary["overall"]["injected"] == 1
    assert summary["controls"]["total"] == 2
    assert summary["controls"]["false_rejected"] == 1
    assert summary["controls"]["false_reject_rate"] == 0.5
    assert summary["by_family"]["f"]["rejected"] == 1
    assert summary["by_validation_layer"]["trace_result"]["rejected"] == 1


def test_exact_mcnemar_and_bootstrap_are_deterministic() -> None:
    from scripts.analyze_paired_experiments import exact_mcnemar, paired_binary_summary

    assert exact_mcnemar(4, 11) == exact_mcnemar(11, 4)
    summary_a = paired_binary_summary([True, True, False, False], [True, False, True, False], seed=7, draws=200)
    summary_b = paired_binary_summary([True, True, False, False], [True, False, True, False], seed=7, draws=200)

    assert summary_a == summary_b
    assert summary_a["pairs"] == 4
    assert summary_a["a_only"] == 1
    assert summary_a["b_only"] == 1


def test_generic_machine_pair_analysis_supports_non_200_experiments() -> None:
    from scripts.analyze_paired_experiments import analyze_machine_conditions

    report = {
        "records": [
            {"condition": "method_a", "case_id": "a", "machine_ok": True},
            {"condition": "method_a", "case_id": "b", "machine_ok": True},
            {"condition": "method_a", "case_id": "c", "machine_ok": False},
            {"condition": "method_b", "case_id": "a", "machine_ok": True},
            {"condition": "method_b", "case_id": "b", "machine_ok": False},
            {"condition": "method_b", "case_id": "c", "machine_ok": True},
        ]
    }

    results, case_ids = analyze_machine_conditions(
        report,
        left_condition="method_a",
        right_condition="method_b",
        expected_pairs=3,
        metrics=["machine_ok"],
    )

    assert case_ids == ["a", "b", "c"]
    assert results["machine_ok"]["pairs"] == 3
    assert results["machine_ok"]["a_pass"] == 2
    assert results["machine_ok"]["b_pass"] == 2
    assert "holm_adjusted_p" in results["machine_ok"]


def test_generic_machine_pair_payload_records_conditions_and_pair_count() -> None:
    from scripts.analyze_paired_experiments import build_machine_pair_payload

    report = {
        "records": [
            {"condition": "full", "case_id": "a", "machine_ok": True},
            {"condition": "full", "case_id": "b", "machine_ok": False},
            {"condition": "ablation", "case_id": "a", "machine_ok": False},
            {"condition": "ablation", "case_id": "b", "machine_ok": False},
        ]
    }

    payload = build_machine_pair_payload(
        report,
        source="audit.json",
        left_condition="full",
        right_condition="ablation",
        expected_pairs=2,
        metrics=["machine_ok"],
    )

    assert payload["kind"] == "paired_machine_statistics"
    assert payload["pair_completeness"] == 2
    assert payload["conditions"] == {"left": "full", "right": "ablation"}
    assert payload["machine_boolean"]["machine_ok"]["difference"] == 0.5


def test_paired_ordinal_summary_uses_signed_ranks() -> None:
    from scripts.analyze_paired_experiments import paired_ordinal_summary

    summary = paired_ordinal_summary([5, 5, 1], [4, 3, 4])

    # Absolute differences are 1, 2, 3, so W+ = 3 and W- = 3.
    assert summary["matched_pairs_rank_biserial"] == 0.0
    assert summary["pairs"] == 3


def test_index_unique_rows_rejects_duplicate_case_ids() -> None:
    import pytest

    from scripts.analyze_paired_experiments import index_unique_rows

    with pytest.raises(ValueError, match="duplicate case_id"):
        index_unique_rows([{"case_id": "a"}, {"case_id": "a"}], label="test")


def test_in_memory_replay_uses_replacement_input_and_expected() -> None:
    from scripts.replay_llm_specs import replay_artifact_data

    artifact = {
        "input_data": {"x": 1},
        "expected_result": 2,
        "variants": [
            {
                "id": "v1",
                "name": "double",
                "strategy": "double",
                "code": "def solve(input_data):\n    return input_data['x'] * 2",
                "tracker_code": (
                    "def trace(input_data):\n"
                    "    result = input_data['x'] * 2\n"
                    "    return {'schema_version':'semantic-trace-v1','algorithm':'double',"
                    "'input_data':input_data,'result':result,'pseudocode':['double'],"
                    "'events':[{'step':0,'op':'create','targets':[{'id':'x'}],"
                    "'state':{'x':input_data['x']},'reason':'start','code_line':1}]}"
                ),
            }
        ],
    }

    row = replay_artifact_data(
        artifact,
        case_id="double",
        input_data={"x": 3},
        expected=6,
    )

    assert row["ok"] is True
    assert row["input_data"] == {"x": 3}
    assert row["expected"] == 6
    assert row["stage_status"]["solve"] is True
    assert row["stage_status"]["scene"] is True


def test_freeze_manifest_hashes_required_inputs(tmp_path: Path) -> None:
    from scripts.freeze_completion_experiment_inputs import freeze_inputs

    source = tmp_path / "source.json"
    source.write_text(json.dumps({"cases": [{"id": "a", "family_id": "f"}]}), encoding="utf-8")

    result = freeze_inputs({"benchmark": source})

    assert result["inputs"]["benchmark"]["exists"] is True
    assert len(result["inputs"]["benchmark"]["sha256"]) == 64


def test_cross_input_jobs_cover_every_case_sample_pair() -> None:
    from scripts.run_cross_input_replay import build_jobs

    benchmark = {
        "cases": [
            {"id": "a", "family_id": "f1", "samples": [{"index": 0, "input_data": {"x": 1}, "expected": 2}]},
            {
                "id": "b",
                "family_id": "f2",
                "samples": [
                    {"index": 0, "input_data": {"x": 2}, "expected": 4},
                    {"index": 1, "input_data": {"x": 3}, "expected": 6},
                ],
            },
        ]
    }
    report = {"results": [{"case_id": "a", "json": "a.json"}, {"case_id": "b", "json": "b.json"}]}

    jobs = build_jobs(benchmark, report)

    assert [(job["case_id"], job["sample_index"]) for job in jobs] == [("a", 0), ("b", 0), ("b", 1)]
    assert [job["sample_role"] for job in jobs] == ["primary_sample0", "primary_sample0", "additional_sample"]


def test_judge_agreement_reports_kappa_and_flip_rate() -> None:
    from scripts.analyze_judge_robustness import compare_review_sets

    baseline = {
        "pair_reviews": [
            {"case_id": "a", "winner": "algolab_full", "conditions": {}},
            {"case_id": "b", "winner": "direct_html", "conditions": {}},
        ]
    }
    candidate = {
        "pair_reviews": [
            {"case_id": "a", "winner": "algolab_full", "conditions": {}},
            {"case_id": "b", "winner": "algolab_full", "conditions": {}},
        ]
    }

    summary = compare_review_sets(baseline, candidate)

    assert summary["pairs"] == 2
    assert summary["winner_agreement"] == 0.5
    assert summary["winner_flip_rate"] == 0.5
    assert -1.0 <= summary["cohen_kappa"] <= 1.0


def test_judge_report_validation_rejects_duplicate_cases() -> None:
    import pytest

    from scripts.analyze_judge_robustness import validate_review_report

    report = {"pair_reviews": [{"case_id": "a"}, {"case_id": "a"}]}
    with pytest.raises(ValueError, match="duplicate case_id"):
        validate_review_report(report, label="duplicate", expected_pairs=2)


def test_ablation_review_analysis_is_paired_by_case() -> None:
    from scripts.analyze_ablation_reviews import analyze_ablation_report

    def review(case_id: str, full: int, ablated: int) -> dict:
        scores_full = {key: full for key in (
            "content_quality", "learning_goal_alignment", "feedback_adaptation",
            "interaction_usability", "presentation_design", "teaching_effectiveness", "ease_of_use",
        )}
        scores_ablated = {key: ablated for key in scores_full}
        return {
            "case_id": case_id,
            "conditions": {"full": {"scores": scores_full}, "no_teaching": {"scores": scores_ablated}},
        }

    report = {"condition": "no_teaching", "pair_reviews": [review("a", 5, 2), review("b", 4, 3)]}
    result = analyze_ablation_report(report, expected_pairs=2)

    assert result["pair_count"] == 2
    assert result["metrics"]["content_quality"]["mean_difference"] == 2.0


def test_no_repair_machine_report_reuses_retained_records_and_marks_failures() -> None:
    from scripts.build_full200_ablation_conditions import build_no_repair_machine_report

    no_repair = {
        "results": [
            {"case_id": "a", "ok": True, "generation_failed": False},
            {"case_id": "b", "ok": False, "generation_failed": True},
        ]
    }
    machine = {
        "records": [
            {"case_id": "a", "condition": "algolab_full", "machine_ok": True, "page_load_ok": True},
            {"case_id": "b", "condition": "algolab_full", "machine_ok": True, "page_load_ok": True},
        ]
    }

    report = build_no_repair_machine_report(no_repair, machine)

    assert report["summary"]["no_repair"]["total"] == 2
    assert report["summary"]["no_repair"]["machine_ok"] == 1
    failed = next(row for row in report["records"] if row["case_id"] == "b")
    assert failed["machine_ok"] is False
    assert failed["page_load_ok"] is False


def test_completion_scripts_run_as_direct_entrypoints() -> None:
    root = Path(__file__).resolve().parents[2]
    for relative in (
        "scripts/build_full200_ablation_conditions.py",
        "scripts/run_cross_input_replay.py",
        "scripts/analyze_judge_robustness.py",
    ):
        completed = subprocess.run(
            [sys.executable, str(root / relative), "--help"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr


def test_final_completion_material_audit_verifies_blind_packages() -> None:
    from scripts.audit_plan_completion_materials import audit_materials

    root = Path(__file__).resolve().parents[2]
    experiment_root = root / "output/experiments/algotutorgen_plan_completion_20260713"

    result = audit_materials(experiment_root)

    assert result["status"] == "automated_complete_human_pending"
    assert result["all_checks_passed"] is True
    assert result["automated_experiments"]["main_machine_ok"] == {
        "algotutorgen": [198, 200],
        "direct": [98, 200],
        "webgen": [45, 200],
        "htmlcure_strict": [40, 200],
    }
    assert result["automated_experiments"]["browser_repair_machine_ok"] == {
        "1": [106, 200],
        "2": [10, 200],
        "3": [15, 200],
        "5": [6, 200],
    }
    assert result["automated_experiments"]["nondegenerate_ablations"] == {
        "direct_to_scenegraph": {"algotutorgen": [49, 50], "ablation": [1, 50]},
        "verified_trace_to_html": {"algotutorgen": [49, 50], "ablation": [0, 50]},
    }
    assert result["automated_experiments"]["cross_model"] == {
        "algotutorgen": [31, 50],
        "direct": [1, 50],
    }
    assert result["automated_experiments"]["heldout"] == {
        "algotutorgen": [39, 40],
        "direct": [18, 40],
    }
    assert result["automated_experiments"]["validator_faults"] == {
        "rejected": [2246, 2400],
        "clean_accepted": [200, 200],
    }
    assert result["automated_experiments"]["long_trace"] == {
        "materialized": [54, 54],
        "browser_passed": [52, 54],
    }
    assert result["evaluator_calibration"]["pages"] == 120
    assert result["evaluator_calibration"]["families"] == 23
    assert result["evaluator_calibration"]["annotator_rows"] == {"a": 120, "b": 120}
    assert result["trace_correctness"]["items"] == 40
    assert result["trace_correctness"]["families"] == 23
    assert result["human_study"]["expert_pairs"] == 90
    assert result["human_study"]["student_trials"] == 288
    assert result["human_study"]["x_first_balance"] == {"algotutorgen": 12, "direct": 12}
    assert result["human_study"]["analysis_status"] == {
        "expert": "pending_human_data",
        "student": "pending_human_data",
    }


def test_kimi_text_models_use_provider_required_temperature() -> None:
    from llm_client import _temperature_for_model

    assert _temperature_for_model("Kimi-K2.5", default=0.2) == 1.0
    assert _temperature_for_model("kimi-k2.7-code", default=0.3) == 1.0
    assert _temperature_for_model("DeepSeek-V4-Flash", default=0.2) == 0.2
    assert _temperature_for_model("GLM-5.2", default=0.3) == 0.3
