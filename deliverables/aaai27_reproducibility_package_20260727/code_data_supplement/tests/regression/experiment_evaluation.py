from __future__ import annotations

import copy
import concurrent.futures
import json
import subprocess
import sys
import threading
from pathlib import Path


def test_model_call_logs_are_isolated_between_concurrent_benchmark_workers() -> None:
    from llm_client import clear_model_calls, consume_model_calls, record_model_call

    cleared = threading.Barrier(2)
    recorded = threading.Barrier(2)

    def worker(label: str) -> list[dict]:
        clear_model_calls()
        cleared.wait()
        record_model_call({"kind": "generation", "worker": label})
        recorded.wait()
        return consume_model_calls()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(worker, ["a", "b"]))

    assert sorted(result[0]["worker"] for result in results) == ["a", "b"]
    assert all(len(result) == 1 for result in results)


def test_retry_policy_local_resume_repairs_current_spec_while_global_restart_regenerates() -> None:
    from scripts.run_local_vs_global_retry import execute_retry_policy

    local_calls: list[str] = []
    local_materialize = iter([(None, ["scene contract failed"]), ({"artifact": True}, [])])

    local = execute_retry_policy(
        strategy="local_resume",
        max_llm_calls=2,
        generate=lambda: local_calls.append("generate") or {"version": 1},
        repair=lambda spec, errors: local_calls.append(f"repair:{spec['version']}") or {"version": 2},
        materialize=lambda spec: next(local_materialize),
        is_valid=lambda artifact, errors: artifact is not None and not errors,
    )

    global_calls: list[str] = []
    global_materialize = iter([(None, ["scene contract failed"]), ({"artifact": True}, [])])
    restarted = execute_retry_policy(
        strategy="global_restart",
        max_llm_calls=2,
        generate=lambda: global_calls.append("generate") or {"version": len(global_calls)},
        repair=lambda spec, errors: (_ for _ in ()).throw(AssertionError("global restart must not repair")),
        materialize=lambda spec: next(global_materialize),
        is_valid=lambda artifact, errors: artifact is not None and not errors,
    )

    assert local["ok"] is True
    assert local["llm_calls"] == 2
    assert local["generate_calls"] == 1
    assert local["repair_calls"] == 1
    assert local_calls == ["generate", "repair:1"]
    assert restarted["ok"] is True
    assert restarted["llm_calls"] == 2
    assert restarted["generate_calls"] == 2
    assert restarted["repair_calls"] == 0
    assert global_calls == ["generate", "generate"]


def test_retry_cost_model_counts_failed_case_spend_and_matches_two_stage_prediction() -> None:
    from scripts.run_local_vs_global_retry import estimate_strategy_cost

    def call(tokens: int) -> dict:
        return {"usage_available": True, "total_tokens": tokens}

    estimate = estimate_strategy_cost(
        [
            {"ok": True, "actual_model_calls": 1, "attempts": [{"valid": True, "model_calls": [call(10)]}]},
            {
                "ok": True,
                "actual_model_calls": 2,
                "attempts": [
                    {"valid": False, "model_calls": [call(10)]},
                    {"valid": True, "model_calls": [call(5)]},
                ],
            },
        ],
        strategy="local_resume",
        max_policy_calls=2,
    )

    assert estimate["initial_success_rate"] == 0.5
    assert estimate["recovery_success_rate"] == 1.0
    assert estimate["predicted_success_rate_at_cap"] == 1.0
    assert estimate["observed_success_rate_at_cap"] == 1.0
    assert estimate["success_prediction_absolute_error"] == 0.0
    assert estimate["predicted_tokens_per_success_at_cap"] == 12.5
    assert estimate["observed_tokens_per_success"] == 12.5
    assert estimate["token_prediction_relative_error"] == 0.0


def test_retry_summary_emits_actual_call_and_token_budget_curves() -> None:
    from scripts.run_local_vs_global_retry import summarize_results

    def call(tokens: int) -> dict:
        return {
            "kind": "generation",
            "usage_available": True,
            "prompt_tokens": tokens,
            "completion_tokens": 0,
            "total_tokens": tokens,
            "duration_s": 1.0,
        }

    rows = [
        {
            "strategy": "local_resume",
            "ok": True,
            "duration_s": 1.0,
            "actual_model_calls": 1,
            "model_calls": [call(10)],
            "attempts": [{"valid": True, "model_calls": [call(10)]}],
        },
        {
            "strategy": "local_resume",
            "ok": False,
            "duration_s": 2.0,
            "actual_model_calls": 2,
            "model_calls": [call(20)],
            "attempts": [{"valid": False, "model_calls": [call(20)]}],
        },
    ]

    summary = summarize_results(rows, max_policy_calls=2)

    assert summary["fixed_actual_call_budget_curve"]["local_resume"][0] == {
        "actual_model_call_budget": 1,
        "successes": 1,
        "total": 2,
    }
    assert summary["fixed_token_budget_curve"]["local_resume"][0] == {
        "token_budget": 10,
        "successes": 1,
        "total": 2,
    }


def test_retry_failure_metadata_uses_validator_emitted_contract_stage() -> None:
    from scripts.run_local_vs_global_retry import annotate_failure_metadata, summarize_results

    rows = [
        {
            "strategy": "local_resume",
            "ok": False,
            "actual_model_calls": 1,
            "model_calls": [],
            "attempts": [
                {
                    "valid": False,
                    "materialized": True,
                    "errors": [
                        "严格模式拒绝 warning：候选: teaching_contract step 1: 缺少错误反馈",
                        "候选失败：solve 结果 1 与 trace 结果 2 不一致",
                    ],
                    "model_calls": [],
                }
            ],
        }
    ]

    annotate_failure_metadata(rows)
    attempt = rows[0]["attempts"][0]
    assert attempt["failure_types"] == ["generation", "result_mismatch"]
    assert attempt["failure_stages"] == ["teaching", "solver_trace_consistency"]

    summary = summarize_results(rows, max_policy_calls=1)["strategies"]["local_resume"]
    assert summary["failure_stage_counts"] == {
        "solver_trace_consistency": 1,
        "teaching": 1,
    }
    assert summary["failed_attempt_stage_localization_rate"] == 1.0


def test_retry_summary_reports_paired_strategy_outcomes() -> None:
    from scripts.run_local_vs_global_retry import summarize_results

    outcomes = {
        "a": (True, True),
        "b": (True, False),
        "c": (False, True),
        "d": (False, False),
    }
    rows = []
    for case_id, (local_ok, global_ok) in outcomes.items():
        for strategy, ok in (("local_resume", local_ok), ("global_restart", global_ok)):
            rows.append(
                {
                    "case_id": case_id,
                    "strategy": strategy,
                    "ok": ok,
                    "actual_model_calls": 0,
                    "model_calls": [],
                    "attempts": [],
                }
            )

    paired = summarize_results(rows, max_policy_calls=1)["paired_comparison"]

    assert paired == {
        "matched_cases": 4,
        "both_pass": 1,
        "local_only_pass": 1,
        "global_only_pass": 1,
        "neither_pass": 1,
        "local_minus_global_pass_rate": 0.0,
        "mcnemar_exact_two_sided_p": 1.0,
    }


def test_retry_failure_stage_maps_explicit_release_gate_messages() -> None:
    from scripts.run_local_vs_global_retry import failure_stage_for_message

    assert failure_stage_for_message("解法 1 失败：solve 代码为空") == "solver"
    assert failure_stage_for_message("没有可发布的产物") == "release_gate"
    assert failure_stage_for_message("缺少独立 verifier、expected 或多解法交叉校验") == "oracle_consistency"
    assert failure_stage_for_message("缺少可渲染 scene graph") == "scene_graph"


def test_semantic_projection_compares_trace_and_scene_state_without_layout_or_teaching() -> None:
    from scripts.run_semantic_preservation_audit import compare_trace_scene

    trace = {
        "result": 2,
        "events": [
            {"step": 0, "state": {"queue": [0, 1], "dist": {"1": 4, "0": 0}}},
            {"step": 1, "state": {"queue": [1], "dist": {"0": 0, "1": 4}}},
        ],
    }
    scene = {
        "result": 2,
        "frames": [
            {
                "step": 0,
                "state": {"dist": {"0": 0, "1": 4}, "queue": [0, 1]},
                "objects": [{"id": "node:0", "x": 120, "y": 30}],
                "teaching": {"what": "任意教学文案"},
            },
            {
                "step": 1,
                "state": {"dist": {"1": 4, "0": 0}, "queue": [1]},
                "objects": [{"id": "node:0", "x": 400, "y": 200}],
                "teaching": {"what": "另一段文案"},
            },
        ],
    }

    result = compare_trace_scene(trace, scene)

    assert result["all_frames_equivalent"] is True
    assert result["equivalent_frames"] == 2
    assert result["first_mismatch"] is None

    scene["frames"][1]["state"]["queue"] = [0]
    mismatch = compare_trace_scene(trace, scene)
    assert mismatch["all_frames_equivalent"] is False
    assert mismatch["first_mismatch"]["step"] == 1


def test_semantic_audit_follows_artifact_paths_from_merged_benchmark_report(tmp_path: Path) -> None:
    from scripts.run_semantic_preservation_audit import artifact_paths_from_source

    artifact = tmp_path / "artifacts" / "llm_case_0.json"
    artifact.parent.mkdir()
    artifact.write_text('{"schema_version":"algolab-build-v1"}', encoding="utf-8")
    report = tmp_path / "llm_benchmark_report.json"
    report.write_text(
        json.dumps({"results": [{"case_id": "case", "ok": True, "json": str(artifact)}]}),
        encoding="utf-8",
    )

    assert artifact_paths_from_source(report) == [artifact]


def test_noninterference_distinguishes_teaching_and_navigation_actions() -> None:
    from scripts.run_noninterference_stress import check_action_transition

    before = {
        "artifact_hash": "artifact-1",
        "current_state_hash": "frame-0",
        "current_step": 0,
    }
    after_hint = {**before, "teaching_state_hash": "hint-open"}
    assert check_action_transition("hint", before, after_hint)["ok"] is True

    after_navigation = {
        "artifact_hash": "artifact-1",
        "current_state_hash": "frame-1",
        "current_step": 1,
        "target_state_hash": "frame-1",
    }
    assert check_action_transition("next", before, after_navigation)["ok"] is True

    mutated = {**after_hint, "artifact_hash": "artifact-2"}
    violation = check_action_transition("submit_wrong", before, mutated)
    assert violation["ok"] is False
    assert "artifact_hash_changed" in violation["violations"]


def test_noninterference_shard_merge_recomputes_totals() -> None:
    from scripts.run_noninterference_stress import merge_reports

    merged = merge_reports(
        [
            {
                "results": [{"case_id": "a", "ok": True, "sequences": 100, "actions_executed": 3000, "violations": []}],
                "overlay_results": [{"artifact": "a.json", "ok": True}],
            },
            {
                "results": [{"case_id": "b", "ok": False, "sequences": 100, "actions_executed": 4000, "violations": [{"kind": "changed"}]}],
                "overlay_results": [{"artifact": "b.json", "ok": True}],
            },
        ]
    )

    assert merged["summary"] == {
        "pages": 2,
        "pages_passed": 1,
        "sequences": 200,
        "actions": 7000,
        "violations": 1,
        "overlay_artifacts": 2,
        "overlay_artifacts_passed": 2,
    }


def test_cross_model_overlay_extracts_only_teaching_fields() -> None:
    from scripts.run_noninterference_stress import extract_teaching_overlay

    overlay = extract_teaching_overlay(
        {
            "frames": [
                {
                    "step": 3,
                    "state": {"answer": 9},
                    "objects": [{"id": "answer", "value": 9}],
                    "teaching": {"what": "解释", "why": "理由"},
                    "interaction": {"type": "judge", "prompt": "完成了吗？", "answer": True},
                }
            ]
        }
    )

    assert overlay == {
        "frames": [
            {
                "step": 3,
                "teaching": {"what": "解释", "why": "理由"},
                "interaction": {"type": "judge", "prompt": "完成了吗？", "answer": True},
            }
        ]
    }


def test_overlay_audit_rejects_directory_paths_without_reading_them(tmp_path: Path) -> None:
    from scripts.run_noninterference_stress import overlay_audit

    result = overlay_audit(tmp_path)

    assert result == {
        "artifact": str(tmp_path),
        "ok": False,
        "error": "missing_artifact",
    }


def test_nested_contract_survival_uses_cumulative_and_conditional_rates() -> None:
    from scripts.analyze_nested_contract_survival import summarize_condition

    rows = [
        {
            "visible_answer_match": True,
            "page_load_ok": True,
            "interaction_reachable": True,
            "correct_feedback_ok": True,
            "wrong_feedback_ok": True,
            "hint_ok": True,
            "show_answer_ok": True,
            "learning_log_ok": True,
            "mutation_free_ok": True,
        },
        {
            "visible_answer_match": True,
            "page_load_ok": True,
            "interaction_reachable": False,
            "correct_feedback_ok": False,
            "wrong_feedback_ok": False,
            "hint_ok": False,
            "show_answer_ok": False,
            "learning_log_ok": False,
            "mutation_free_ok": True,
        },
        {
            "visible_answer_match": True,
            "page_load_ok": False,
            "interaction_reachable": True,
            "correct_feedback_ok": True,
            "wrong_feedback_ok": True,
            "hint_ok": True,
            "show_answer_ok": True,
            "learning_log_ok": True,
            "mutation_free_ok": True,
        },
        {
            "visible_answer_match": False,
            "page_load_ok": True,
            "interaction_reachable": True,
            "correct_feedback_ok": True,
            "wrong_feedback_ok": True,
            "hint_ok": True,
            "show_answer_ok": True,
            "learning_log_ok": True,
            "mutation_free_ok": True,
        },
    ]

    summary = summarize_condition(rows)

    assert [item["passed"] for item in summary["contracts"]] == [3, 2, 1, 1, 1, 1]
    assert summary["contracts"][0]["cumulative_rate"] == 0.75
    assert summary["contracts"][1]["conditional_survival"] == 2 / 3
    assert summary["contracts"][2]["conditional_survival"] == 0.5
    assert summary["product_of_conditional_survival"] == 0.25


def test_semantic_mutation_summary_separates_violation_rejection_and_preservation_acceptance() -> None:
    from scripts.run_semantic_mutation_analysis import summarize_semantic_mutations

    summary = summarize_semantic_mutations(
        [
            {"mutation_class": "semantic_violation", "accepted": False},
            {"mutation_class": "semantic_violation", "accepted": True},
            {"mutation_class": "semantics_preserving", "accepted": True},
            {"mutation_class": "semantics_preserving", "accepted": True},
        ]
    )

    assert summary["semantic_violation"]["total"] == 2
    assert summary["semantic_violation"]["rejection_rate"] == 0.5
    assert summary["semantics_preserving"]["total"] == 2
    assert summary["semantics_preserving"]["acceptance_rate"] == 1.0


def test_expected_result_reordering_is_classified_by_case_semantics() -> None:
    from scripts.run_semantic_mutation_analysis import expected_mutation_is_equivalent

    original = [[1], [2], [1, 2]]
    reordered = [[1, 2], [2], [1]]

    assert expected_mutation_is_equivalent(
        original,
        reordered,
        case_id="bitmask_subsets",
        family_id="backtracking",
        subfamily_id="subset_generation",
    ) is True


def test_interaction_audit_maps_host_absolute_paths_inside_container(tmp_path: Path, monkeypatch) -> None:
    from scripts import run_interaction_semantic_eval as semantic_eval

    host_root = tmp_path / "host-checkout"
    container_root = tmp_path / "container-checkout"
    artifact = container_root / "output" / "page.html"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("<html><body>ok</body></html>", encoding="utf-8")

    monkeypatch.setattr(semantic_eval, "ROOT", container_root)
    monkeypatch.setenv("ALGOLAB_HOST_PROJECT_ROOT", str(host_root))

    assert semantic_eval._repo_path(host_root / "output" / "page.html") == artifact


def test_noninterference_audit_maps_host_absolute_paths_inside_container(tmp_path: Path, monkeypatch) -> None:
    from scripts import run_noninterference_stress as stress

    host_root = tmp_path / "host-checkout"
    container_root = tmp_path / "container-checkout"
    artifact = container_root / "output" / "page.html"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("<html><body>ok</body></html>", encoding="utf-8")

    monkeypatch.setattr(stress, "ROOT", container_root)
    monkeypatch.setenv("ALGOLAB_HOST_PROJECT_ROOT", str(host_root))

    assert stress._repo_path(host_root / "output" / "page.html") == artifact


def test_long_trace_jobs_keep_three_scales_with_bounded_state_growth() -> None:
    from scripts.run_long_trace_scalability import scalability_jobs

    jobs = scalability_jobs()
    by_case: dict[str, list[dict]] = {}
    for row in jobs:
        by_case.setdefault(row["case_id"], []).append(row)

    assert len(by_case) == 18
    assert all([row["size"] for row in rows] == ["small", "medium", "large"] for rows in by_case.values())
    assert len(by_case["edit_distance"][-1]["input_data"]["word1"]) <= 18
    assert len(by_case["prefix_sum_range"][-1]["input_data"]["nums"]) <= 256
    assert len(by_case["dp_max_subarray_full_core"][-1]["input_data"]["nums"]) <= 192
    assert by_case["unique_paths"][-1]["input_data"]["m"] * by_case["unique_paths"][-1]["input_data"]["n"] <= 270
    assert len(by_case["kmp"][-1]["input_data"]["text"]) <= 512
    assert len(by_case["daily_temperatures"][-1]["input_data"]["temperatures"]) <= 192
    assert by_case["union_count_components_full_core"][-1]["input_data"]["n"] <= 256


def test_self_contained_annotation_adds_strict_joint_metric(tmp_path: Path) -> None:
    from scripts.annotate_self_contained_audit import annotate_report

    self_contained_html = tmp_path / "a.html"
    self_contained_html.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
    external_html = tmp_path / "b.html"
    external_html.write_text('<link href="https://fonts.example/font.css">', encoding="utf-8")
    dynamic_html = tmp_path / "c.html"
    dynamic_html.write_text("<html><body>offline shell</body></html>", encoding="utf-8")
    machine_report = {
        "records": [
            {"condition": "algolab_full", "case_id": "a", "machine_ok": True},
            {"condition": "direct_html", "case_id": "a", "machine_ok": True},
            {"condition": "algolab_full", "case_id": "b", "machine_ok": False},
            {"condition": "direct_html", "case_id": "b", "machine_ok": True},
            {"condition": "algolab_full", "case_id": "c", "machine_ok": False},
            {"condition": "direct_html", "case_id": "c", "machine_ok": True},
        ]
    }
    method_report = {
        "results": [
            {
                "case_id": "a",
                "html": str(self_contained_html),
                "external_resource_urls": ["http://www.w3.org/2000/svg"],
            },
            {"case_id": "b", "html": str(external_html), "external_resource_urls": []},
            {
                "case_id": "c",
                "html": str(dynamic_html),
                "external_resource_urls": [],
                "observed_external_requests": ["https://api.example/data.json"],
            },
        ]
    }

    annotated = annotate_report(machine_report, method_report, method_condition="direct_html")

    rows = {(row["condition"], row["case_id"]): row for row in annotated["records"]}
    assert rows[("direct_html", "a")]["self_contained_ok"] is True
    assert rows[("direct_html", "a")]["strict_machine_ok"] is True
    assert rows[("direct_html", "b")]["self_contained_ok"] is False
    assert rows[("direct_html", "b")]["strict_machine_ok"] is False
    assert rows[("direct_html", "c")]["self_contained_ok"] is False
    assert rows[("direct_html", "c")]["strict_machine_ok"] is False
    assert annotated["self_contained_summary"]["direct_html"]["strict_machine_ok"] == 1


def test_self_contained_annotation_cli_loads_from_repo_root() -> None:
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "scripts/annotate_self_contained_audit.py", "--help"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_browser_repair_budget_curve_summarizes_cost_and_strict_passes() -> None:
    from scripts.summarize_browser_repair_budget_curve import summarize_budget

    method_report = {
        "results": [
            {
                "case_id": "a",
                "model_calls": [
                    {"total_tokens": 10, "duration_s": 1.5},
                    {"total_tokens": 20, "duration_s": 2.5},
                ],
                "external_resource_urls": [],
            },
            {
                "case_id": "b",
                "model_calls": [
                    {"total_tokens": 30, "duration_s": 3.0},
                    {"total_tokens": 40, "duration_s": 4.0},
                ],
                "external_resource_urls": ["https://cdn.example/x.js"],
            },
        ]
    }
    strict_audit = {
        "summary": {"direct_browser_repair_2": {"total": 2, "machine_ok": 1}},
        "self_contained_summary": {
            "direct_browser_repair_2": {
                "total": 2,
                "self_contained_ok": 1,
                "strict_machine_ok": 1,
            }
        },
    }
    paired = {
        "machine_boolean": {
            "machine_ok": {"difference": 0.5, "bootstrap_ci_95": [0.0, 1.0], "mcnemar_exact_p": 0.5}
        }
    }
    paired_strict = {
        "machine_boolean": {
            "strict_machine_ok": {"difference": 0.5, "bootstrap_ci_95": [0.0, 1.0], "mcnemar_exact_p": 0.25}
        }
    }

    summary = summarize_budget(
        call_budget=2,
        method_report=method_report,
        strict_audit=strict_audit,
        paired_statistics=paired,
        paired_strict_statistics=paired_strict,
        token_target=50,
    )

    assert summary["cases"] == 2
    assert summary["avg_calls"] == 2.0
    assert summary["avg_total_tokens"] == 50.0
    assert summary["avg_generation_seconds"] == 5.5
    assert summary["over_token_target_cases"] == 1
    assert summary["machine_ok"] == 1
    assert summary["self_contained_ok"] == 1
    assert summary["strict_machine_ok"] == 1
    assert summary["paired_machine_ok"]["mcnemar_exact_p"] == 0.5
    assert summary["paired_strict_machine_ok"]["mcnemar_exact_p"] == 0.25


def test_calibration_confusion_metrics_and_kappa() -> None:
    from scripts.analyze_evaluator_calibration import cohen_kappa, confusion_metrics

    metrics = confusion_metrics(
        machine=[True, True, False, False],
        human=[True, False, True, False],
    )

    assert metrics["tp"] == 1
    assert metrics["fp"] == 1
    assert metrics["fn"] == 1
    assert metrics["tn"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["false_positive_rate"] == 0.5
    assert metrics["false_negative_rate"] == 0.5
    assert cohen_kappa([True, True, False, False], [True, False, False, False]) == 0.5


def test_calibration_analysis_stays_pending_without_two_human_labels() -> None:
    from scripts.analyze_evaluator_calibration import analyze_rows

    result = analyze_rows(
        key_rows=[{"blind_id": "P001", "method": "stage1", "machine_ok": True}],
        annotator_a=[{"blind_id": "P001", "human_machine_ok": "1"}],
        annotator_b=[{"blind_id": "P001", "human_machine_ok": ""}],
    )

    assert result["status"] == "pending_human_labels"
    assert result["complete_pairs"] == 0


def test_calibration_sampling_and_blind_ids_are_deterministic() -> None:
    from scripts.prepare_evaluator_calibration import blind_id, select_stratified_cases

    candidates = [
        {"case_id": "a", "family_id": "f1", "interaction_type": "choice", "status_bits": "1111"},
        {"case_id": "b", "family_id": "f1", "interaction_type": "input", "status_bits": "0000"},
        {"case_id": "c", "family_id": "f2", "interaction_type": "judge", "status_bits": "1010"},
        {"case_id": "d", "family_id": "f3", "interaction_type": "choice", "status_bits": "0101"},
    ]

    selected_a = select_stratified_cases(candidates, count=3, seed=17)
    selected_b = select_stratified_cases(candidates, count=3, seed=17)

    assert selected_a == selected_b
    assert len({row["case_id"] for row in selected_a}) == 3
    assert {row["family_id"] for row in selected_a} == {"f1", "f2", "f3"}
    assert blind_id("a", "stage1", seed=17) == blind_id("a", "stage1", seed=17)
    assert blind_id("a", "stage1", seed=17) != blind_id("a", "direct", seed=17)


def test_trace_audit_keyframes_include_initial_middle_and_terminal() -> None:
    from scripts.prepare_trace_correctness_audit import select_keyframe_indices

    frames = [
        {"step": 0, "evidence": {}},
        {"step": 1, "evidence": {"deps": ["nums[0]"]}},
        {"step": 2, "interaction": {"type": "choice"}, "evidence": {}},
        {"step": 3, "evidence": {}},
        {"step": 4, "evidence": {}},
    ]

    assert select_keyframe_indices(frames, count=3) == [0, 2, 4]
    assert select_keyframe_indices(frames[:1], count=3) == [0]


def test_trace_audit_analysis_is_pending_without_real_double_labels() -> None:
    from scripts.analyze_trace_correctness_audit import analyze_trace_rows

    result = analyze_trace_rows(
        key_rows=[{"audit_id": "T001", "family_id": "f1"}],
        annotator_a=[{"audit_id": "T001", "critical_error": "0"}],
        annotator_b=[{"audit_id": "T001", "critical_error": ""}],
    )

    assert result["status"] == "pending_human_labels"
    assert result["agreed_cases"] == 0
    assert result["critical_semantic_error_rate"] is None


def test_interaction_semantic_summary_counts_machine_and_judge_scores() -> None:
    from scripts.run_interaction_semantic_eval import summarize_condition_results

    records = [
        {
            "condition": "algolab_full",
            "case_id": "binary_search",
            "machine_ok": True,
            "visible_answer_match": True,
            "interaction_reachable": True,
            "correct_feedback_ok": True,
            "wrong_feedback_ok": True,
            "hint_ok": True,
            "show_answer_ok": True,
            "learning_log_ok": True,
            "mutation_free_ok": True,
            "llm_judge": {
                "scores": {
                    "process_accuracy": 5,
                    "interaction_semantics": 5,
                    "teaching_alignment": 4,
                    "visual_clarity": 3,
                }
            },
        },
        {
            "condition": "direct_html",
            "case_id": "binary_search",
            "machine_ok": False,
            "visible_answer_match": True,
            "interaction_reachable": True,
            "correct_feedback_ok": False,
            "wrong_feedback_ok": True,
            "hint_ok": True,
            "show_answer_ok": False,
            "learning_log_ok": True,
            "mutation_free_ok": True,
            "llm_judge": {
                "scores": {
                    "process_accuracy": 3,
                    "interaction_semantics": 2,
                    "teaching_alignment": 3,
                    "visual_clarity": 5,
                }
            },
        },
    ]

    summary = summarize_condition_results(records)

    assert summary["algolab_full"]["total"] == 1
    assert summary["algolab_full"]["machine_ok"] == 1
    assert summary["algolab_full"]["avg_process_accuracy"] == 5.0
    assert summary["direct_html"]["total"] == 1
    assert summary["direct_html"]["correct_feedback_ok"] == 0
    assert summary["direct_html"]["avg_visual_clarity"] == 5.0


def test_browser_audit_rejects_missing_html_without_opening_browser() -> None:
    from scripts.run_interaction_semantic_eval import audit_browser_record

    class BrowserMustNotOpen:
        def new_page(self, **_: object) -> object:
            raise AssertionError("browser must not open for a missing HTML artifact")

    record = audit_browser_record(
        BrowserMustNotOpen(),
        {
            "case_id": "missing_html",
            "condition": "algolab_full",
            "html": "",
            "expected": 1,
        },
    )

    assert record["page_load_ok"] is False
    assert record["machine_ok"] is False
    assert "MissingHtmlArtifact" in record["console_page_errors"][0]


def test_llm_judge_result_is_normalized_and_clamped() -> None:
    from scripts.run_interaction_semantic_eval import normalize_llm_judge_result

    result = normalize_llm_judge_result(
        {
            "winner": "direct",
            "scores": {
                "algolab": {
                    "process_accuracy": 6,
                    "interaction_semantics": 5,
                    "teaching_alignment": 0,
                    "visual_clarity": 4,
                },
                "direct_html": {
                    "process_accuracy": "2",
                    "interaction_semantics": 3,
                    "teaching_alignment": 4,
                    "visual_clarity": 9,
                },
            },
            "rationale": "direct looks better, algolab is more grounded",
        }
    )

    assert result["winner"] == "direct_html"
    assert result["algolab_full"]["scores"]["process_accuracy"] == 5
    assert result["algolab_full"]["scores"]["teaching_alignment"] == 1
    assert result["direct_html"]["scores"]["process_accuracy"] == 2
    assert result["direct_html"]["scores"]["visual_clarity"] == 5


def test_expected_text_matching_handles_structured_values() -> None:
    from scripts.run_interaction_semantic_eval import _expected_matches_text

    assert _expected_matches_text('当前输出 {"A":0,"B":2,"C":3}', {"A": 0, "B": 2, "C": 3})
    assert _expected_matches_text("结果 answer = [1,1,4,2,1,1,0,0]", [1, 1, 4, 2, 1, 1, 0, 0])
    assert not _expected_matches_text('当前输出 {"A":0,"B":2,"C":9}', {"A": 0, "B": 2, "C": 3})


def test_feedback_classifiers_distinguish_correct_and_wrong() -> None:
    from scripts.run_interaction_semantic_eval import _feedback_is_correct, _feedback_is_wrong

    assert _feedback_is_correct("✅ 正确！mid 应该右移")
    assert not _feedback_is_correct("❌ 不正确。应该继续松弛")
    assert _feedback_is_wrong("错误：混淆了索引和值")


def test_feedback_classifier_recognizes_renderer_wrong_option_prefix() -> None:
    from scripts.run_interaction_semantic_eval import _feedback_is_correct, _feedback_is_wrong

    feedback = "错误选项解释：参考答案：1。你可能忽略了当前状态。"

    assert _feedback_is_wrong(feedback)
    assert not _feedback_is_correct(feedback)


def test_fault_injection_mutates_expected_and_tracker_result() -> None:
    from scripts.run_gate_fault_injection import inject_fault

    artifact = {
        "expected_result": 4,
        "variants": [
            {
                "code": "def solve(input_data):\n    return 4",
                "tracker_code": "def trace(input_data):\n    return {'input_data': input_data, 'result': 4, 'events': []}",
            }
        ],
    }

    expected_fault = inject_fault(copy.deepcopy(artifact), "expected_result_wrong")
    trace_fault = inject_fault(copy.deepcopy(artifact), "trace_result_wrong")

    assert expected_fault["expected_result"] != 4
    assert "_algolab_original_trace_for_fault" in trace_fault["variants"][0]["tracker_code"]
    assert "t['result']" in trace_fault["variants"][0]["tracker_code"]


def test_fault_summary_reports_rejection_rate() -> None:
    from scripts.run_gate_fault_injection import summarize_fault_rows

    rows = [
        {"fault_type": "expected_result_wrong", "rejected": True},
        {"fault_type": "expected_result_wrong", "rejected": False},
        {"fault_type": "trace_result_wrong", "rejected": True},
    ]

    summary = summarize_fault_rows(rows)

    assert summary["overall"]["injected"] == 3
    assert summary["overall"]["rejected"] == 2
    assert summary["overall"]["false_accepted"] == 1
    assert summary["by_fault_type"]["expected_result_wrong"]["rejection_rate"] == 0.5


def test_scalability_matrix_has_18_tasks_and_three_ordered_sizes() -> None:
    from scripts.run_long_trace_scalability import scalability_jobs

    jobs = scalability_jobs()

    assert len(jobs) == 54
    assert len({job["case_id"] for job in jobs}) == 18
    for case_id in {job["case_id"] for job in jobs}:
        rows = [job for job in jobs if job["case_id"] == case_id]
        assert [row["size"] for row in rows] == ["small", "medium", "large"]
        assert [row["scale_rank"] for row in rows] == [1, 2, 3]


def test_scalability_summary_reports_growth_by_size() -> None:
    from scripts.run_long_trace_scalability import summarize_rows

    summary = summarize_rows(
        [
            {"size": "small", "ok": True, "trace_events": 10, "html_bytes": 1000, "load_ms": 20},
            {"size": "medium", "ok": True, "trace_events": 20, "html_bytes": 2000, "load_ms": 30},
            {"size": "large", "ok": False, "trace_events": 40, "html_bytes": 4000, "load_ms": 50},
        ]
    )

    assert summary["small"]["pass_rate"] == 1.0
    assert summary["large"]["pass_rate"] == 0.0
    assert summary["large"]["avg_trace_events"] == 40.0


def test_human_study_analysis_stays_pending_without_real_participants() -> None:
    from scripts.analyze_human_study import analyze_expert_rows, analyze_student_rows

    assert analyze_expert_rows([])["status"] == "pending_human_data"
    assert analyze_student_rows([])["status"] == "pending_human_data"


def test_human_study_completed_student_pairs_report_condition_means() -> None:
    from scripts.analyze_human_study import analyze_student_rows

    rows = [
        {"participant_id": "P1", "condition": "algotutorgen", "correct": "1", "completion_time_s": "20", "cognitive_load": "2", "sus_score": "85"},
        {"participant_id": "P1", "condition": "direct", "correct": "0", "completion_time_s": "30", "cognitive_load": "5", "sus_score": "60"},
        {"participant_id": "P2", "condition": "algotutorgen", "correct": "1", "completion_time_s": "22", "cognitive_load": "3", "sus_score": "80"},
        {"participant_id": "P2", "condition": "direct", "correct": "1", "completion_time_s": "28", "cognitive_load": "4", "sus_score": "65"},
    ]

    result = analyze_student_rows(rows)

    assert result["status"] == "complete"
    assert result["participants_with_both_conditions"] == 2
    assert result["by_condition"]["algotutorgen"]["accuracy"] == 1.0
    assert result["by_condition"]["direct"]["accuracy"] == 0.5


def test_human_study_wilcoxon_uses_signed_ranks_for_rank_biserial() -> None:
    from scripts.analyze_human_study import _wilcoxon

    result = _wilcoxon([2, 4, 1, 7], [1, 2, 3, 3])

    assert result is not None
    assert result["positive_rank_sum"] == 7.5
    assert result["negative_rank_sum"] == 2.5
    assert result["rank_biserial"] == 0.5


def test_human_study_expert_analysis_reports_ci_holm_and_sensitivity() -> None:
    from scripts.analyze_human_study import EXPERT_METRICS, analyze_expert_rows

    rows = []
    for expert_id in ("E1", "E2"):
        for index, family_id in enumerate(("graph", "dp"), 1):
            row = {
                "expert_id": expert_id,
                "pair_id": f"{expert_id}-{family_id}",
                "family_id": family_id,
                "method_a": "algotutorgen" if index % 2 else "direct",
                "method_b": "direct" if index % 2 else "algotutorgen",
                "preference": "a" if index % 2 else "b",
            }
            for metric in EXPERT_METRICS:
                row[f"{metric}_a"] = "5" if row["method_a"] == "algotutorgen" else "2"
                row[f"{metric}_b"] = "5" if row["method_b"] == "algotutorgen" else "2"
            rows.append(row)

    result = analyze_expert_rows(rows, seed=7, bootstrap_draws=200)

    assert result["status"] == "complete"
    assert result["by_method"]["algotutorgen"]["process_correctness"]["mean"] == 5.0
    assert len(result["by_method"]["algotutorgen"]["process_correctness"]["bootstrap_ci_95"]) == 2
    assert len(result["paired_difference_ci_95"]["process_correctness"]) == 2
    assert result["paired_wilcoxon"]["process_correctness"]["holm_adjusted_p"] >= result["paired_wilcoxon"]["process_correctness"]["p_value"]
    assert set(result["by_expert"]) == {"E1", "E2"}
    assert set(result["by_family"]) == {"dp", "graph"}


def test_human_study_scores_standard_sus_items() -> None:
    from scripts.analyze_human_study import score_sus

    perfect = {f"sus_{item}": "5" if item % 2 else "1" for item in range(1, 11)}
    neutral = {f"sus_{item}": "3" for item in range(1, 11)}

    assert score_sus(perfect) == 100.0
    assert score_sus(neutral) == 50.0
    assert score_sus({**perfect, "sus_10": ""}) is None


def test_human_study_merges_questionnaires_with_private_condition_codes() -> None:
    from scripts.analyze_human_study import analyze_student_rows

    observations = [
        {"participant_id": participant, "condition": condition, "correct": "1", "completion_time_s": "20", "cognitive_load": "2", "hint_used": "1", "show_answer_used": "0"}
        for participant in ("P1", "P2")
        for condition in ("algotutorgen", "direct")
    ]
    questionnaires = []
    condition_codes = {
        "P1": {"X": "algotutorgen", "Y": "direct"},
        "P2": {"X": "direct", "Y": "algotutorgen"},
    }
    for participant, mapping in condition_codes.items():
        for code, condition in mapping.items():
            perfect = condition == "algotutorgen"
            questionnaires.append({
                "participant_id": participant,
                "condition_code": code,
                "cognitive_load": "2" if perfect else "5",
                **{
                    f"sus_{item}": ("5" if item % 2 else "1") if perfect else ("1" if item % 2 else "5")
                    for item in range(1, 11)
                },
            })

    result = analyze_student_rows(
        observations,
        questionnaire_rows=questionnaires,
        condition_codes=condition_codes,
    )

    assert result["by_condition"]["algotutorgen"]["mean_sus_score"] == 100.0
    assert result["by_condition"]["direct"]["mean_sus_score"] == 0.0
    assert result["by_condition"]["algotutorgen"]["mean_questionnaire_cognitive_load"] == 2.0
    assert result["by_condition"]["direct"]["mean_questionnaire_cognitive_load"] == 5.0
    assert result["by_condition"]["algotutorgen"]["hint_use_rate"] == 1.0
    assert "rank_biserial" in result["paired_wilcoxon"]["sus_score"]


def test_human_study_student_primary_tests_report_rank_biserial() -> None:
    from scripts.analyze_human_study import analyze_student_rows

    rows = [
        {"participant_id": participant, "condition": condition, "correct": correct, "completion_time_s": time_s}
        for participant, values in {
            "P1": (("1", "20"), ("0", "31")),
            "P2": (("1", "21"), ("0", "30")),
            "P3": (("1", "22"), ("1", "29")),
        }.items()
        for condition, (correct, time_s) in zip(("algotutorgen", "direct"), values)
    ]

    result = analyze_student_rows(rows)

    assert "rank_biserial" in result["paired_wilcoxon"]["accuracy"]
    assert "rank_biserial" in result["paired_wilcoxon"]["completion_time_s"]
    assert "holm_adjusted_p" in result["paired_wilcoxon"]["accuracy"]


def test_human_study_package_has_decodable_counterbalanced_condition_codes(tmp_path) -> None:
    import json

    from scripts.analyze_human_study import prepare_protocol_package

    calibration_root = tmp_path / "calibration"
    pages_dir = calibration_root / "pages"
    pages_dir.mkdir(parents=True)
    pages = []
    for index in range(30):
        case_id = f"case_{index:02d}"
        for method in ("stage1", "direct"):
            page_name = f"{case_id}_{method}.html"
            (pages_dir / page_name).write_text("<html></html>", encoding="utf-8")
            pages.append({
                "case_id": case_id,
                "family_id": f"family_{index % 3}",
                "method": method,
                "page_ref": f"pages/{page_name}",
            })
    calibration_key = calibration_root / "private_blind_key.json"
    calibration_key.write_text(json.dumps({"pages": pages}), encoding="utf-8")
    output_dir = tmp_path / "human"

    prepare_protocol_package(
        calibration_key=calibration_key,
        calibration_root=calibration_root,
        output_dir=output_dir,
        seed=17,
    )

    student_key = json.loads((output_dir / "student_private_key.json").read_text(encoding="utf-8"))
    mappings = student_key["condition_codes"]
    assert len(mappings) == 24
    assert sum(mapping["X"] == "algotutorgen" for mapping in mappings.values()) == 12
    assert all(set(mapping.values()) == {"algotutorgen", "direct"} for mapping in mappings.values())
    trials_by_participant = {}
    for row in student_key["trials"]:
        trials_by_participant.setdefault(row["participant_id"], []).append(row)
    for participant, trials in trials_by_participant.items():
        ordered = sorted(trials, key=lambda row: row["trial"])
        assert {row["condition_code"] for row in ordered[:6]} == {"X"}
        assert {row["condition_code"] for row in ordered[6:]} == {"Y"}
        assert all(row["condition"] == mappings[participant][row["condition_code"]] for row in ordered)
    expert_key = json.loads((output_dir / "expert_private_key.json").read_text(encoding="utf-8"))
    assert all(row["family_id"].startswith("family_") for row in expert_key["rows"])
