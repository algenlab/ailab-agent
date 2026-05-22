"""Real-problem benchmark regression.

This suite does not call the LLM. It validates that generated-style specs for
real algorithm tasks can pass the full materialization pipeline on multiple
inputs.
"""

from __future__ import annotations

from pathlib import Path

from algolab.pipeline import _try_materialize
from algolab.generation.solution_generator import normalize_solution_spec
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
from scripts.check_benchmark_html import html_paths_from_report
from llm_client import parse_json_content
import argparse
import json
import tempfile


def spec_for_case(case: BenchmarkCase) -> dict:
    return {
        "problem_title": case.title,
        "input_contract": case.input_contract,
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


def test_llm_benchmark_sample_selection_and_failure_classification(tmp_path: Path):
    case = benchmark_cases()[0]
    args = argparse.Namespace(sample=1, all_samples=False)
    selected = selected_samples(case, args)
    assert len(selected) == 1
    assert selected[0][0] == 1
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
    test_llm_benchmark_request_uses_problem_and_expected()
    test_llm_benchmark_sample_selection_and_failure_classification(Path(tempfile.gettempdir()))
    test_llm_benchmark_phase_timing_helpers()
    test_llm_json_and_spec_normalization_helpers()
    test_existing_benchmark_html_report_helper(Path(tempfile.gettempdir()))

    with tempfile.TemporaryDirectory() as d:
        test_benchmark_aggregate_artifact(Path(d))
    test_creative_renderer_contains_theme_controls_and_stage()


if __name__ == "__main__":
    run_all()
    print("benchmark_regression: PASS")
