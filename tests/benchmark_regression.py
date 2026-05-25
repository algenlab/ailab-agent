"""Real-problem benchmark regression.

This suite does not call the LLM. It validates that generated-style specs for
real algorithm tasks can pass the full materialization pipeline on multiple
inputs.
"""

from __future__ import annotations

from pathlib import Path

from algolab.pipeline import _try_materialize
from algolab.generation.solution_generator import normalize_solution_spec
from algolab.renderer.capabilities import capabilities_prompt_context, runtime_capabilities
from algolab.renderer.creative import render_creative_html
from algolab.renderer.export import save_html
from algolab.schemas.input import ProblemInput
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport
from tests.benchmark_cases import BenchmarkCase, benchmark_cases
from scripts.run_llm_benchmark import (
    average_duration,
    build_artifact_timed,
    classify_failure,
    completed_phase_timings,
    last_phase,
    last_phase_elapsed_s,
    make_request,
    selected_samples,
    summarize_phase_timings,
    write_report,
)
from scripts.build_demo_dashboard import CUSTOM_SUBSET_SUM_ID, build_dashboard, selected_demo_definitions
from scripts.check_benchmark_html import html_paths_from_report
from scripts.build_evaluation_manifest import build_manifest, write_manifest
from scripts.build_evaluation_report import build_evaluation_report, comparison_protocols, compute_metrics
from llm_client import parse_json_content
import argparse
import json
import os
import tempfile


def spec_for_case(case: BenchmarkCase) -> dict:
    return {
        "problem_title": case.title,
        "input_contract": case.input_contract,
        "correctness_contract": contract_for_case(case) if case.id in contract_enabled_case_ids() else None,
        "variants": [
            {
                "id": case.id,
                "name": case.variant_name,
                "strategy": case.strategy,
                "time_complexity": case.time_complexity,
                "space_complexity": case.space_complexity,
                "code": case.code,
                "tracker_code": case.tracker_code,
            }
        ],
        "verifier_code": case.verifier_code,
    }


def contract_enabled_case_ids() -> set[str]:
    return {"house_robber", "binary_search", "unique_paths", "graph_bfs", "two_sum"}


def contract_for_case(case: BenchmarkCase) -> dict:
    first = case.samples[0]
    return {
        "schema_version": "correctness-contract-v1",
        "input_schema": {key: _type_expr(value) for key, value in first.input_data.items()},
        "output_schema": _type_expr(first.expected),
        "postconditions": [f"{case.title} solve output must satisfy deterministic verifier"],
        "oracle_strategy": "generated_verifier",
        "oracle_code": case.verifier_code,
        "test_cases": [
            {
                "name": f"{case.id}_sample_{index}",
                "input": sample.input_data,
                "expected": sample.expected,
            }
            for index, sample in enumerate(case.samples)
        ],
        "process_invariants": [f"expected layout: {layout}" for layout in case.expected_layouts],
    }


def _type_expr(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        if not value:
            return "any[]"
        return f"{_type_expr(value[0])}[]"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return "any"


def materialize_case(case: BenchmarkCase, sample_index: int = 0):
    sample = case.samples[sample_index]
    request = ProblemInput(problem=case.title, input_data=sample.input_data, expected_result=sample.expected)
    return _try_materialize(request, spec_for_case(case))


def test_benchmark_cases_are_multi_input_release_ready():
    cases = benchmark_cases()
    assert len(cases) >= 5
    for case in cases:
        assert len(case.samples) >= 2
        for index, sample in enumerate(case.samples):
            request = ProblemInput(problem=case.title, input_data=sample.input_data, expected_result=sample.expected)
            artifact, errors = _try_materialize(request, spec_for_case(case))
            assert errors == [], (case.id, index, errors)
            assert artifact.validation.release_gate.release_ready, (case.id, index, artifact.validation.release_gate)
            assert len(artifact.variants) == 1
            assert artifact.variants[0].result == sample.expected
            assert artifact.verifier_result == sample.expected
            assert artifact.variants[0].trace is not None
            assert len(artifact.variants[0].trace.events) >= 1
            if case.id in contract_enabled_case_ids():
                assert artifact.correctness_contract is not None
                assert artifact.validation.contract_validation is not None
                assert artifact.validation.contract_validation.release_gate.contract_ready
                assert artifact.validation.contract_test_results
                assert all(item["ok"] for item in artifact.validation.contract_test_results)
            if index == 0:
                scene = artifact.scenes[case.id]
                layouts = {
                    obj.meta.get("layout")
                    for frame in scene.frames
                    for obj in frame.objects
                    if obj.type.value == "container"
                }
                for expected_layout in case.expected_layouts:
                    assert expected_layout in layouts, (case.id, index, expected_layout, layouts)


def test_convex_hull_trace_exposes_scan_phases_and_pop_steps():
    case = next(item for item in benchmark_cases() if item.id == "convex_hull")
    artifact, errors = materialize_case(case, sample_index=0)

    assert errors == []
    trace = artifact.variants[0].trace
    assert trace is not None
    events = trace.events
    states = [event.state for event in events]
    phases = [state.get("phase") for state in states]
    pop_events = [event for event in events if event.op.value == "pop"]
    current_values = [tuple(state.get("current")) for state in states if state.get("current") is not None]
    hull_snapshots = {
        tuple((state.get("geometry") or {}).get("hull") or [])
        for state in states
        if state.get("geometry")
    }
    scene = artifact.scenes[case.id]
    hull_edge_counts = [
        sum(1 for obj in frame.objects if obj.type.value == "edge" and obj.meta.get("shape") == "hull")
        for frame in scene.frames
    ]

    assert "lower" in phases
    assert "upper" in phases
    assert pop_events
    assert any("非左转" in event.reason for event in pop_events)
    assert len(set(current_values)) >= 3
    assert len(hull_snapshots) >= 4
    assert max(hull_edge_counts) > min(hull_edge_counts)


def test_contract_tests_block_bad_solve():
    case = next(item for item in benchmark_cases() if item.id == "two_sum")
    spec = spec_for_case(case)
    spec["variants"][0]["code"] = "def solve(input_data):\n    return [0, 1]"
    sample = case.samples[0]
    request = ProblemInput(problem=case.title, input_data=sample.input_data, expected_result=sample.expected)

    artifact, errors = _try_materialize(request, spec)

    assert errors
    assert not artifact.validation.release_gate.release_ready
    assert artifact.validation.contract_test_results
    assert any(not item["ok"] for item in artifact.validation.contract_test_results)
    assert any("contract test_cases" in error for error in errors)


def test_benchmark_aggregate_artifact(tmp_path: Path):
    artifact = benchmark_coverage_artifact()
    assert len(artifact.variants) == len(benchmark_cases())
    assert len(artifact.scenes) == len(benchmark_cases())
    out = save_html(artifact, tmp_path / "benchmark_coverage.html")
    html = out.read_text(encoding="utf-8")
    assert "真实题型 Benchmark 覆盖" in html
    assert out.with_suffix(".json").exists()


def test_creative_renderer_contains_theme_controls_and_stage():
    artifact = benchmark_coverage_artifact()
    html = render_creative_html(artifact)
    assert "创意演示模式" in html
    assert 'data-theme-btn="fantasy"' in html
    assert 'data-theme-btn="cyber"' in html
    assert 'id="metaphor"' in html
    assert "renderMetaphor" in html


def test_llm_benchmark_request_uses_problem_and_expected():
    case = benchmark_cases()[0]
    sample = case.samples[0]
    request = make_request(case, sample, solutions=2)
    assert request.problem == case.problem
    assert request.input_data == sample.input_data
    assert request.expected_result == sample.expected
    assert request.strategy_hint == case.strategy
    assert request.solution_count == 2


def test_llm_client_reads_local_api_settings_without_committing_key(tmp_path: Path):
    settings_path = tmp_path / "api_settings.yaml"
    settings_path.write_text(
        "\n".join(
            [
                "api_settings:",
                '  base_url: "http://example.test/v1"',
                '  api_key: "sk-test-local-only"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    import llm_client

    old_env = {
        key: os.environ.get(key)
        for key in ("ALGOLAB_LLM_API_KEY", "ALGOLAB_LLM_BASE_URL", "ALGOLAB_LLM_SETTINGS_FILE")
    }
    old_cache = llm_client._LOCAL_API_SETTINGS
    try:
        os.environ.pop("ALGOLAB_LLM_API_KEY", None)
        os.environ.pop("ALGOLAB_LLM_BASE_URL", None)
        os.environ["ALGOLAB_LLM_SETTINGS_FILE"] = str(settings_path)
        llm_client._LOCAL_API_SETTINGS = None
        config = llm_client.llm_config()
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        llm_client._LOCAL_API_SETTINGS = old_cache

    assert config["base_url"] == "http://example.test/v1"
    assert config["api_key_configured"] is True
    assert config["api_key_source"] == str(settings_path)
    assert "sk-test-local-only" not in json.dumps(config)


def test_llm_benchmark_sample_selection_and_failure_classification(tmp_path: Path):
    case = benchmark_cases()[0]
    args = argparse.Namespace(sample=1, all_samples=False)
    selected = selected_samples(case, args)
    assert len(selected) == 1
    assert selected[0][0] == 1
    assert classify_failure("RuntimeError: 缺少 ALGOLAB_LLM_API_KEY 环境变量") == "configuration"
    assert classify_failure("TimeoutError: LLM benchmark 超过 1 秒") == "timeout"
    assert classify_failure("严格模式拒绝 warning：x") == "visual_warning"
    assert classify_failure("第 3 步 dp[2] 不满足 0-1 背包可达性") == "process_invariant"
    assert classify_failure("scene validator 渲染布局失败") == "visual_scene"
    assert classify_failure("solve 执行失败：NameError") == "execution"
    assert classify_failure("结果 1 与 expected 2 不一致") == "correctness"

    report_args = argparse.Namespace(
        case=[case.id],
        sample=1,
        all_samples=False,
        solutions=1,
        max_rounds=2,
        timeout_s=1,
        strict_warnings=True,
        browser_smoke=False,
        write_each=True,
        concurrency=1,
    )
    report_path = write_report(
        [
            {
                "case_id": case.id,
                "title": case.title,
                "family": case.family,
                "sample_index": 1,
                "ok": False,
                "failure_type": "timeout",
                "duration_s": 1.0,
            }
        ],
        tmp_path,
        args=report_args,
        started_at="2026-01-01T00:00:00",
        ended_at="2026-01-01T00:00:01",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["cached"] is False
    assert report["config"]["model"]
    assert report["config"]["sample"] == 1
    assert report["config"]["write_each"] is True
    assert report["config"]["concurrency"] == 1
    assert report["failure_summary"] == {"timeout": 1}
    assert report["avg_duration_s"] == 1.0


def test_llm_benchmark_phase_timing_helpers():
    phase_log = [
        {"event": "start", "phase": "generate", "at": 10.0},
        {"event": "end", "phase": "generate", "status": "ok", "duration_s": 2.5, "at": 12.5},
        {"event": "start", "phase": "repair_round_0", "at": 13.0},
    ]
    timings = completed_phase_timings(phase_log)
    assert timings == [{"phase": "generate", "duration_s": 2.5, "status": "ok"}]
    assert last_phase(phase_log) == "repair_round_0:中"
    assert last_phase_elapsed_s(phase_log, now=16.0) == 3.0
    results = [
        {"duration_s": 10, "phase_timings": timings},
        {"duration_s": 20, "phase_timings": [{"phase": "generate", "duration_s": 3.5, "status": "ok"}]},
    ]
    assert average_duration(results) == 15.0
    assert summarize_phase_timings(results)["generate"] == {"count": 2, "avg_s": 3.0, "max_s": 3.5}


def test_llm_benchmark_strict_warning_enters_repair(monkeypatch):
    request = ProblemInput(problem="警告修复测试", input_data={"nums": [2, 1]}, expected_result=[1, 2])
    gate = ReleaseGate(
        artifact_ready=True,
        process_ready=True,
        trace_ready=True,
        visual_ready=True,
        release_ready=True,
    )
    warned = BuildArtifact(
        problem_title="警告修复测试",
        input_contract="",
        input_data=request.input_data,
        expected_result=request.expected_result,
        variants=[],
        scenes={},
        validation=ValidationReport(warnings=["第 1 步 after 与 state 不一致：nums[0]"], release_gate=gate),
    )
    clean = BuildArtifact(
        problem_title="警告修复测试",
        input_contract="",
        input_data=request.input_data,
        expected_result=request.expected_result,
        variants=[],
        scenes={},
        validation=ValidationReport(warnings=[], release_gate=gate),
    )
    calls = {"materialize": 0, "repair_errors": []}

    def fake_generate(_request):
        return {"variants": []}

    def fake_materialize(_request, _spec):
        calls["materialize"] += 1
        return (warned if calls["materialize"] == 1 else clean), []

    def fake_repair(_request, spec, errors):
        calls["repair_errors"].append(errors)
        return spec

    monkeypatch.setattr("scripts.run_llm_benchmark.generate_solution_spec", fake_generate)
    monkeypatch.setattr("scripts.run_llm_benchmark._try_materialize", fake_materialize)
    monkeypatch.setattr("scripts.run_llm_benchmark.repair_solution_spec", fake_repair)

    artifact = build_artifact_timed(request, max_rounds=1, strict_warnings=True)

    assert artifact.validation.warnings == []
    assert calls["materialize"] == 2
    assert calls["repair_errors"] == [["严格模式拒绝 warning：第 1 步 after 与 state 不一致：nums[0]"]]


def test_llm_json_and_spec_normalization_helpers():
    parsed = parse_json_content('```json\n{"ok": true}\n```')
    assert parsed == {"ok": True}
    parsed = parse_json_content('说明\n{"ok": true, "items": [1, 2]}\n结束')
    assert parsed == {"ok": True, "items": [1, 2]}

    spec = normalize_solution_spec([{"id": "x", "code": "", "tracker_code": ""}])
    assert spec["problem_title"] == "算法可视化实验"
    assert len(spec["variants"]) == 1
    assert spec["variants"][0]["id"] == "x"
    spec = normalize_solution_spec({"variants": {"id": "y", "code": "", "tracker_code": ""}})
    assert len(spec["variants"]) == 1
    assert spec["variants"][0]["id"] == "y"


def test_existing_benchmark_html_report_helper(tmp_path: Path):
    report_path = tmp_path / "llm_benchmark_report.json"
    report_path.write_text(
        json.dumps(
            {
                "results": [
                    {"ok": True, "html": "output/a.html"},
                    {"ok": False, "html": "output/b.html"},
                    {"ok": True, "html": "output/c.html"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert html_paths_from_report(report_path) == [Path("output/a.html"), Path("output/c.html")]


def test_demo_dashboard_selection_defaults_to_curated_showcase():
    definitions = selected_demo_definitions()
    ids = [definition.id for definition in definitions]
    assert ids[0] == CUSTOM_SUBSET_SUM_ID
    assert len(ids) == 8
    assert "binary_search" in ids
    assert "graph_bfs" in ids
    assert "daily_temperatures" in ids
    assert "trie_prefix" in ids
    assert "provinces" in ids
    assert "permutations" in ids
    assert "convex_hull" in ids


def test_demo_dashboard_writes_bundle_and_index(tmp_path: Path):
    index = build_dashboard(
        tmp_path / "dashboard",
        demo_ids=[CUSTOM_SUBSET_SUM_ID, "binary_search"],
        style="both",
    )
    assert index.exists()
    report_path = index.with_name("dashboard.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["kind"] == "algolab_demo_dashboard"
    assert report["total"] == 2
    assert report["passed"] == 2
    assert report["failed"] == 0
    for demo in report["demos"]:
        bundle = index.parent / demo["bundle_dir"]
        assert (bundle / "request.json").exists()
        assert (bundle / "generated_spec.json").exists()
        assert (bundle / "correctness_contract.json").exists()
        assert (bundle / "visual_plan.json").exists()
        assert (bundle / "render_report.json").exists()
        assert (bundle / "capabilities.json").exists()
        assert (bundle / "artifact.json").exists()
        assert (bundle / "validation_report.json").exists()
        assert (bundle / "repair_log.json").exists()
        assert (bundle / "stable.html").exists()
        assert (bundle / "creative.html").exists()
        assert demo["ok"] is True
        assert demo["contract_gate_ready"] is True
        assert demo["oracle_strategy"] in {"generated_verifier", "expected_only"}
        assert "interaction_coverage" in demo
        interaction_count, frame_count = [int(part) for part in demo["interaction_coverage"].split("/", 1)]
        assert interaction_count >= 2
        assert frame_count >= interaction_count
        assert set(demo["interaction_types"]) <= {"choice", "input", "judge"}
        assert demo["interaction_types"]
        assert demo["visual_plan_stage"] in {"teaching_2d", "spatial_3d", "hybrid_2_5d", "creative"}
        assert demo["requested_render_target"] == demo["visual_plan_stage"]
        assert demo["actual_render_target"] in {"teaching_2d", "spatial_3d", "creative"}
        assert isinstance(demo["used_baseline_renderer"], bool)
        assert demo["correctness_contract_json"].endswith("correctness_contract.json")
        assert demo["visual_plan_json"].endswith("visual_plan.json")
        assert demo["render_report_json"].endswith("render_report.json")
        assert demo["capabilities_json"].endswith("capabilities.json")
        contract = json.loads((bundle / "correctness_contract.json").read_text(encoding="utf-8"))
        visual_plan = json.loads((bundle / "visual_plan.json").read_text(encoding="utf-8"))
        render_report = json.loads((bundle / "render_report.json").read_text(encoding="utf-8"))
        capabilities = json.loads((bundle / "capabilities.json").read_text(encoding="utf-8"))
        artifact = json.loads((bundle / "artifact.json").read_text(encoding="utf-8"))
        interactions = [
            frame["interaction"]
            for scene in artifact["scenes"].values()
            for frame in scene["frames"]
            if frame.get("interaction")
        ]
        assert len(interactions) >= 2
        assert contract["schema_version"] == "correctness-contract-v1"
        assert visual_plan["schema_version"] == "visual-plan-v1"
        assert render_report["schema_version"] == "render-report-v1"
        assert capabilities["schema_version"] == "runtime-capabilities-v1"
        assert {"teaching_2d", "spatial_3d", "hybrid_2_5d", "creative"} <= set(capabilities["render_targets"])
        assert "array" in capabilities["supported_layouts"]
        assert "node" in capabilities["primitive_3d_support"]
        assert capabilities["device_constraints"]["mobile_prefer_2d"] is True
        assert artifact["correctness_contract"]["schema_version"] == "correctness-contract-v1"
        assert artifact["visual_plan"]["schema_version"] == "visual-plan-v1"
        assert artifact["render_report"]["requested_target"] == demo["requested_render_target"]
        assert "contract_test_pass_rate" in demo
        assert demo["contract_test_pass_rate"] in {"", "0/0"} or "/" in demo["contract_test_pass_rate"]
        assert demo["stable_html"].endswith("stable.html")
        assert demo["creative_html"].endswith("creative.html")
    html = index.read_text(encoding="utf-8")
    core_table = index.with_name("dashboard_core_table.csv")
    assert core_table.exists()
    core_table_text = core_table.read_text(encoding="utf-8")
    assert "contract_test_pass_rate" in core_table_text
    assert "interaction_coverage" in core_table_text
    assert "actual_render_target" in core_table_text
    assert "AlgoLab Demo Dashboard" in html
    assert "contract" in html
    assert "VisualPlan" in html
    assert "render report" in html
    assert "capabilities" in html
    assert "oracle=" in html
    assert "交互题" in html
    assert "target" in html
    assert "稳定版" in html
    assert "创意版" in html


def test_runtime_capabilities_prompt_context_is_json():
    capabilities = runtime_capabilities()
    assert capabilities["schema_version"] == "runtime-capabilities-v1"
    assert "teaching_2d" in capabilities["render_targets"]
    assert "graph" in capabilities["supported_layouts"]
    assert "camera_focus" in capabilities["primitive_3d_support"]
    assert capabilities["device_constraints"]["max_nodes_3d"] == 120
    prompt_context = capabilities_prompt_context()
    parsed = json.loads(prompt_context)
    assert parsed == capabilities


def test_evaluation_manifest_covers_phase10_datasets(tmp_path: Path):
    manifest = build_manifest()
    assert manifest["schema_version"] == "evaluation-manifest-v1"
    assert manifest["summary"]["benchmark_case_count"] == len(benchmark_cases())
    assert manifest["summary"]["ml_demo_count"] >= 2
    assert manifest["summary"]["sample_count"] >= 35
    strata = manifest["strata"]
    assert "LeetCode 基础算法集" in strata
    assert "数据结构算法集" in strata
    assert "DP / graph / stack / tree / geometry 分层" in strata
    assert "ML demo 集" in strata
    assert {"linear_regression_single_step", "logistic_regression_boundary"} <= set(strata["ML demo 集"]["case_ids"])
    case_ids = {case["id"] for case in manifest["cases"]}
    assert {"two_sum", "daily_temperatures", "unique_paths", "graph_bfs"} <= case_ids

    path = write_manifest(tmp_path)
    assert path.exists()
    csv_path = tmp_path / "evaluation_cases.csv"
    assert csv_path.exists()
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written == manifest
    assert "linear_regression_single_step" in csv_path.read_text(encoding="utf-8")


def test_evaluation_report_exports_phase10_metrics_and_core_tables(tmp_path: Path):
    manifest = build_manifest()
    dashboard = {
        "kind": "algolab_demo_dashboard",
        "total": 2,
        "passed": 2,
        "failed": 0,
        "demos": [
            {
                "id": "binary_search",
                "ok": True,
                "contract_gate_ready": True,
                "contract_test_pass_rate": "3/3",
                "interaction_coverage": "2/5",
                "actual_render_target": "teaching_2d",
            },
            {
                "id": "graph_bfs",
                "ok": True,
                "contract_gate_ready": True,
                "contract_test_pass_rate": "2/2",
                "interaction_coverage": "3/6",
                "actual_render_target": "spatial_3d",
            },
        ],
    }
    llm_report = {
        "kind": "llm_benchmark_report",
        "total": 2,
        "passed": 1,
        "failed": 1,
        "browser_smoke": [{"ok": True}, {"ok": False}],
        "results": [
            {
                "ok": True,
                "phase_timings": [
                    {"phase": "generate", "status": "ok"},
                    {"phase": "materialize_round_0", "status": "error"},
                    {"phase": "repair_round_0", "status": "ok"},
                    {"phase": "materialize_round_1", "status": "ok"},
                ],
            },
            {
                "ok": False,
                "phase_timings": [
                    {"phase": "generate", "status": "ok"},
                    {"phase": "materialize_round_0", "status": "error"},
                ],
            },
        ],
    }
    metrics = compute_metrics(manifest=manifest, dashboard=dashboard, llm_report=llm_report)
    by_name = {metric["name"]: metric for metric in metrics}
    assert by_name["generation_success_rate"]["value"] == 1.0
    assert by_name["contract_pass_rate"]["value"] == 1.0
    assert by_name["correctness_gate_pass_rate"]["value"] == 0.5
    assert by_name["repair_success_rate"]["value"] == 1.0
    assert by_name["visual_smoke_pass_rate"]["value"] == 0.5
    assert by_name["interaction_coverage"]["value"] == round(5 / 11, 6)
    assert by_name["human_teaching_quality_score"]["status"] == "missing"
    comparisons = comparison_protocols()
    assert {item["baseline"] for item in comparisons} == {
        "pure_llm_judge",
        "code2video_manim",
        "no_correctness_gate_renderer",
    }

    manifest_path = tmp_path / "evaluation_manifest.json"
    dashboard_path = tmp_path / "dashboard.json"
    llm_path = tmp_path / "llm_benchmark_report.json"
    human_path = tmp_path / "human.csv"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    dashboard_path.write_text(json.dumps(dashboard, ensure_ascii=False), encoding="utf-8")
    llm_path.write_text(json.dumps(llm_report, ensure_ascii=False), encoding="utf-8")
    human_path.write_text("case_id,score\nbinary_search,4\ngraph_bfs,5\n", encoding="utf-8")

    report_path = build_evaluation_report(
        output_dir=tmp_path,
        manifest_path=manifest_path,
        dashboard_path=dashboard_path,
        llm_report_path=llm_path,
        human_ratings_path=human_path,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_metrics = {metric["name"]: metric for metric in report["metrics"]}
    assert report_metrics["human_teaching_quality_score"]["value"] == 4.5
    assert {item["baseline"] for item in report["comparisons"]} == {
        "pure_llm_judge",
        "code2video_manim",
        "no_correctness_gate_renderer",
    }
    assert (tmp_path / "evaluation_metrics.csv").exists()
    assert (tmp_path / "evaluation_comparisons.csv").exists()
    assert (tmp_path / "evaluation_core_cases.csv").exists()
    assert (tmp_path / "evaluation_report.md").exists()
    assert "generation_success_rate" in (tmp_path / "evaluation_metrics.csv").read_text(encoding="utf-8")
    assert "纯 LLM judge" in (tmp_path / "evaluation_comparisons.csv").read_text(encoding="utf-8")
    assert "## Comparisons" in (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")


def benchmark_coverage_artifact() -> BuildArtifact:
    variants = []
    scenes = {}
    checks = []
    for case in benchmark_cases():
        artifact, errors = materialize_case(case, sample_index=0)
        if errors or not artifact.validation.release_gate.release_ready:
            raise AssertionError((case.id, errors, artifact.validation.release_gate))
        variant = artifact.variants[0]
        variants.append(variant)
        scenes[variant.id] = artifact.scenes[variant.id]
        checks.append(f"{case.title}：首个 benchmark 输入通过")
    return BuildArtifact(
        problem_title="真实题型 Benchmark 覆盖",
        input_contract="离线多输入 benchmark，聚合每题首个输入的可视化产物。",
        input_data={"benchmark_cases": [case.id for case in benchmark_cases()]},
        variants=variants,
        scenes=scenes,
        validation=ValidationReport(
            checks=checks,
            release_gate=ReleaseGate(
                artifact_ready=True,
                process_ready=True,
                trace_ready=True,
                visual_ready=True,
                multi_solution_ready=True,
                release_ready=True,
            ),
        ),
    )


def run_all():
    test_benchmark_cases_are_multi_input_release_ready()
    test_convex_hull_trace_exposes_scan_phases_and_pop_steps()
    test_contract_tests_block_bad_solve()
    test_llm_benchmark_request_uses_problem_and_expected()
    test_llm_benchmark_sample_selection_and_failure_classification(Path(tempfile.gettempdir()))
    test_llm_benchmark_phase_timing_helpers()
    test_llm_json_and_spec_normalization_helpers()
    test_existing_benchmark_html_report_helper(Path(tempfile.gettempdir()))
    test_demo_dashboard_selection_defaults_to_curated_showcase()
    test_runtime_capabilities_prompt_context_is_json()

    with tempfile.TemporaryDirectory() as d:
        test_llm_client_reads_local_api_settings_without_committing_key(Path(d))
        test_benchmark_aggregate_artifact(Path(d))
        test_demo_dashboard_writes_bundle_and_index(Path(d))
        test_evaluation_manifest_covers_phase10_datasets(Path(d))
        test_evaluation_report_exports_phase10_metrics_and_core_tables(Path(d))
    test_creative_renderer_contains_theme_controls_and_stage()


if __name__ == "__main__":
    run_all()
    print("benchmark_regression: PASS")
