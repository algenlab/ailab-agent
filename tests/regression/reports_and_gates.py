"""Split regression tests: reports and gates."""

from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile

from algolab.compiler.scene_compiler import compile_scene
from algolab.generation import solution_generator
from algolab.generation.solution_generator import normalize_solution_spec
from algolab.renderer.capabilities import capabilities_prompt_context, runtime_capabilities
from algolab.renderer.creative import render_creative_html
from algolab.renderer.export import save_html
from algolab.schemas.input import ProblemInput
from algolab.runtime.executor import execute_variant
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.verification.demo_readiness import validate_variant_demo_readiness
from algolab.verification.process_validator import process_validation_registry, validate_process
from algolab.verification.repair_context import build_repair_context, repair_failure_types
from algolab.verification.scene_validator import validate_scene
from algolab.verification.trace_validator import validate_trace
from tests.benchmark_cases import BENCHMARK_CASE_METADATA, benchmark_cases
from scripts.run_llm_benchmark import (
    average_duration, build_artifact_timed, build_family_summary, case_style_for_sample, classify_failure,
    completed_phase_timings, last_phase, last_phase_elapsed_s, load_family_capabilities, load_llm_family_sets,
    load_unseen_family_cases, make_request, selected_cases, selected_samples, selected_tasks, strong_family_ids_from_capabilities,
    result_metadata, summarize_model_usage, summarize_phase_timings, validate_llm_family_sets, validate_unseen_family_cases, write_report,
)
from scripts.build_demo_dashboard import CUSTOM_SUBSET_SUM_ID, build_dashboard, selected_demo_definitions
from scripts.check_benchmark_html import html_paths_from_report, resolve_required_case_htmls
from scripts.build_evaluation_manifest import build_manifest, write_manifest
from scripts.build_evaluation_report import (
    build_evaluation_report,
    case_style_summary,
    comparison_protocols,
    compute_metrics,
    condition_summary,
    degradation_summary,
)
from scripts.build_reproducibility_package import build_reproducibility_package, write_reproducibility_package
from scripts.check_v1_release_gate import build_v1_release_gate_report, write_v1_release_gate_report
from llm_client import parse_json_content
import llm_client

from tests.regression.helpers import *

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
    assert request.teaching_enrichment is True

    no_teaching_request = make_request(case, sample, solutions=2, teaching_enrichment=False)
    assert no_teaching_request.teaching_enrichment is False


def test_llm_client_reads_local_api_settings_without_committing_key(tmp_path: Path):
    settings_path = tmp_path / "api_settings.yaml"
    settings_path.write_text(
        "\n".join(
            [
                "api_settings:",
                '  base_url: "http://example.test/v1"',
                '  api_key: "sk-test-local-only"',
                '  model: "test-local-model"',
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
    assert config["model"] == "test-local-model"
    assert config["api_key_configured"] is True
    assert config["api_key_source"] == str(settings_path)
    assert "sk-test-local-only" not in json.dumps(config)


def test_llm_client_retries_transient_api_499_json_call():
    class TransientStatusError(Exception):
        status_code = 499

    class Message:
        content = '{"ok": true}'

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]
        usage = {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}

    class Completions:
        def __init__(self):
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise TransientStatusError("Error code: 499 - upstream_error: The operation was cancelled.")
            return Response()

    class Chat:
        def __init__(self):
            self.completions = Completions()

    class FakeClient:
        def __init__(self):
            self.chat = Chat()

    old_client = llm_client._client
    old_env = {
        key: os.environ.get(key)
        for key in ("ALGOLAB_LLM_API_RETRIES", "ALGOLAB_LLM_API_RETRY_DELAY_S")
    }
    fake = FakeClient()
    try:
        llm_client._client = fake
        os.environ["ALGOLAB_LLM_API_RETRIES"] = "1"
        os.environ["ALGOLAB_LLM_API_RETRY_DELAY_S"] = "0"
        llm_client.clear_model_calls()
        result = llm_client.chat_json_with_metadata("system", "user")
    finally:
        llm_client._client = old_client
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        llm_client.clear_model_calls()

    assert fake.chat.completions.calls == 2
    assert result["content"] == {"ok": True}
    assert result["model_call"]["total_tokens"] == 3


def test_llm_benchmark_sample_selection_and_failure_classification(tmp_path: Path):
    case = benchmark_cases()[0]
    args = argparse.Namespace(sample=1, all_samples=False)
    selected = selected_samples(case, args)
    assert len(selected) == 1
    assert selected[0][0] == 1
    assert classify_failure("RuntimeError: 缺少 ALGOLAB_LLM_API_KEY 环境变量") == "configuration"
    assert classify_failure("BadRequestError: Access denied, type: Arrearage") == "configuration"
    assert classify_failure("TimeoutError: LLM benchmark 超过 1 秒") == "timeout"
    assert classify_failure("严格模式拒绝 warning：x") == "visual_warning"
    assert classify_failure("严格模式拒绝 warning：failure_type=coverage_error: BFS 小图缺少关键步骤覆盖：check_edge") == "coverage_error"
    assert classify_failure("第 3 步 dp[2] 不满足 0-1 背包可达性") == "generation"
    assert classify_failure("failure_type=coverage_error: 小 DP 表缺少逐帧状态转移") == "coverage_error"
    assert classify_failure("failure_type=process_uncovered: 未注册算法族只执行基础门禁") == "process_uncovered"
    assert classify_failure("第 1 步 union_find 存在非根环") == "generation"
    assert classify_failure("第 2 步 二分收缩方向错误：nums[1] < target") == "generation"
    assert classify_failure("第 4 步 BFS 首次发现 node:B 来源应为上一层相邻节点") == "generation"
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
        condition="direct_html_baseline",
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
    assert report["config"]["benchmark_condition"] == "direct_html_baseline"
    assert report["results"][0]["condition"] == "direct_html_baseline"
    assert report["failure_summary"] == {"timeout": 1}
    assert report["avg_duration_s"] == 1.0
    assert report["model_usage"]["call_count"] == 0
    assert report["model_usage"]["usage_available"] is False


def test_llm_benchmark_model_usage_summary_records_tokens_by_kind():
    results = [
        {
            "ok": True,
            "model_calls": [
                {
                    "kind": "generation",
                    "model": "fake-model",
                    "started_at": "2026-05-30T00:00:00",
                    "ended_at": "2026-05-30T00:00:01",
                    "duration_s": 1.0,
                    "usage_available": True,
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
                {
                    "kind": "repair",
                    "model": "fake-model",
                    "started_at": "2026-05-30T00:00:02",
                    "ended_at": "2026-05-30T00:00:04",
                    "duration_s": 2.0,
                    "usage_available": True,
                    "prompt_tokens": 40,
                    "completion_tokens": 50,
                    "total_tokens": 90,
                },
            ],
        }
    ]
    usage = summarize_model_usage(results)
    assert usage["usage_available"] is True
    assert usage["call_count"] == 2
    assert usage["prompt_tokens"] == 50
    assert usage["completion_tokens"] == 70
    assert usage["total_tokens"] == 120
    assert usage["by_kind"]["generation"]["total_tokens"] == 30
    assert usage["by_kind"]["repair"]["total_tokens"] == 90


def test_llm_benchmark_family_split_selection_and_summary(tmp_path: Path):
    family_sets = load_llm_family_sets()
    family_errors = validate_llm_family_sets(family_sets)
    assert family_errors == []

    hash_cases = selected_cases(families={"hash_map"}, gate_layers={"family_core"}, family_sets=family_sets)
    assert [case.id for case in hash_cases] == ["two_sum", "subarray_sum_equals_k"]
    assert case_style_for_sample(hash_cases[0], 0, family_sets) == "seen_style"
    assert case_style_for_sample(hash_cases[0], 1, family_sets) == "unseen_style"
    assert case_style_for_sample(hash_cases[1], 0, family_sets) == "seen_style"

    greedy_cases = selected_cases(families={"greedy"}, gate_layers={"family_core"}, family_sets=family_sets)
    assert "merge_intervals" in [case.id for case in greedy_cases]

    args = argparse.Namespace(sample=None, all_samples=False, limit_per_family=2)
    array_cases = selected_cases(families={"array_pointer"}, family_sets=family_sets)
    tasks = selected_tasks(array_cases, args)
    assert len(tasks) == 2
    assert {task[0].subfamily_id for task in tasks} == {"binary_answer", "two_pointer"}

    report_args = argparse.Namespace(
        case=[],
        sample=None,
        all_samples=False,
        solutions=1,
        max_rounds=2,
        timeout_s=1,
        strict_warnings=True,
        browser_smoke=False,
        write_each=True,
        concurrency=1,
        condition="algolab_full",
        family=["array_pointer"],
        gate_layer=["family_core"],
        limit_per_family=2,
        family_sets=Path("benchmark/llm_family_sets.json"),
    )
    results = [
        {
            "case_id": "binary_answer_sqrt",
            "title": "二分答案整数平方根",
            "family": "数组指针 / 窗口 / 前缀",
            "family_id": "array_pointer",
            "subfamily_id": "binary_answer",
            "gate_layer": "family_core",
            "support_level": "strong",
            "process_profile": "array_pointer",
            "case_style": "seen_style",
            "sample_index": 0,
            "ok": True,
            "duration_s": 1.0,
            "repair_failure_types": ["schema_error"],
            "phase_timings": [{"phase": "repair_round_0", "status": "ok", "duration_s": 0.2}],
        },
        {
            "case_id": "two_pointer_pair_sum",
            "title": "有序数组两数之和",
            "family": "数组指针 / 窗口 / 前缀",
            "family_id": "array_pointer",
            "subfamily_id": "two_pointer",
            "gate_layer": "family_core",
            "support_level": "strong",
            "process_profile": "array_pointer",
            "case_style": "unseen_style",
            "sample_index": 1,
            "ok": False,
            "failure_type": "process_invariant",
            "duration_s": 1.0,
            "phase_timings": [],
        },
    ]
    family_summary = build_family_summary(
        results,
        args=report_args,
        started_at="2026-01-01T00:00:00",
        ended_at="2026-01-01T00:00:01",
    )
    family = family_summary["families"][0]
    assert family["family_id"] == "array_pointer"
    assert family["generation_success_rate"] == 0.5
    assert family["repair_success_rate"] == 1.0
    assert family["failure_types"] == {"process_invariant": 1}
    assert family["case_styles"] == {"seen_style": 1, "unseen_style": 1}

    report_path = write_report(
        results,
        tmp_path,
        args=report_args,
        started_at="2026-01-01T00:00:00",
        ended_at="2026-01-01T00:00:01",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    family_summary_path = tmp_path / "family_summary.json"
    written_family_summary = json.loads(family_summary_path.read_text(encoding="utf-8"))
    assert report["family_summary_path"] == str(family_summary_path)
    assert report["family_summary"][0]["family_id"] == "array_pointer"
    assert written_family_summary["summary"]["failure_types"] == {"process_invariant": 1}


def test_phase15_unseen_family_cases_are_independent_and_reported(tmp_path: Path):
    unseen_config = load_unseen_family_cases()
    capabilities = load_family_capabilities()
    errors = validate_unseen_family_cases(unseen_config, capabilities=capabilities)
    assert errors == []

    strong_families = strong_family_ids_from_capabilities(capabilities)
    configured_families = {item["family_id"] for item in unseen_config["cases"]}
    assert strong_families <= configured_families

    def assert_no_code_fields(value):
        if isinstance(value, dict):
            assert not ({"code", "tracker_code", "verifier_code"} & set(value))
            for child in value.values():
                assert_no_code_fields(child)
        elif isinstance(value, list):
            for child in value:
                assert_no_code_fields(child)

    assert_no_code_fields(unseen_config)

    unseen_cases = selected_cases(
        families={"array_pointer"},
        gate_layers={"llm_eval"},
        case_set="unseen",
        unseen_cases_config=unseen_config,
    )
    assert [case.id for case in unseen_cases] == ["unseen_container_with_most_water"]
    unseen_case = unseen_cases[0]
    assert not hasattr(unseen_case, "tracker_code")
    assert not hasattr(unseen_case, "code")
    assert not hasattr(unseen_case, "verifier_code")

    args = argparse.Namespace(sample=None, all_samples=False, limit_per_family=1, case_set="unseen")
    tasks = selected_tasks(unseen_cases, args)
    assert len(tasks) == 1
    case, sample_index, sample = tasks[0]
    request = make_request(case, sample, solutions=1)
    assert request.problem == case.problem
    assert request.input_data == sample.input_data
    assert request.expected_result == sample.expected

    metadata_args = argparse.Namespace(case_set="unseen", family_sets_config=load_llm_family_sets())
    metadata = result_metadata(case, sample_index, metadata_args)
    assert metadata["case_set"] == "unseen"
    assert metadata["case_style"] == "unseen_style"

    report_args = argparse.Namespace(
        case=[],
        sample=None,
        all_samples=False,
        solutions=1,
        max_rounds=2,
        timeout_s=1,
        strict_warnings=True,
        browser_smoke=False,
        write_each=True,
        concurrency=1,
        condition="algolab_full",
        family=["array_pointer"],
        gate_layer=["llm_eval"],
        limit_per_family=1,
        case_set="unseen",
        family_sets=Path("benchmark/llm_family_sets.json"),
        unseen_cases=Path("benchmark/unseen_family_cases.json"),
    )
    results = [
        {
            "case_id": "binary_answer_sqrt",
            "title": "二分答案整数平方根",
            "family": "数组指针 / 窗口 / 前缀",
            "family_id": "array_pointer",
            "subfamily_id": "binary_answer",
            "gate_layer": "family_core",
            "support_level": "strong",
            "process_profile": "array_pointer",
            "case_set": "deterministic",
            "case_style": "seen_style",
            "sample_index": 0,
            "ok": True,
            "duration_s": 1.0,
            "phase_timings": [],
        },
        {
            "case_id": "unseen_container_with_most_water",
            "title": "盛最多水的容器",
            "family": "数组指针 / 窗口 / 前缀",
            "family_id": "array_pointer",
            "subfamily_id": "two_pointer",
            "gate_layer": "llm_eval",
            "support_level": "strong",
            "process_profile": "array_pointer",
            "case_set": "unseen",
            "case_style": "unseen_style",
            "sample_index": 0,
            "ok": False,
            "failure_type": "process_invariant",
            "duration_s": 1.0,
            "phase_timings": [],
        },
    ]
    report_path = write_report(
        results,
        tmp_path,
        args=report_args,
        started_at="2026-01-01T00:00:00",
        ended_at="2026-01-01T00:00:01",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    family_summary = json.loads((tmp_path / "family_summary.json").read_text(encoding="utf-8"))
    assert report["case_set_summary"] == {"deterministic": 1, "unseen": 1}
    assert report["case_style_summary"] == {"seen_style": 1, "unseen_style": 1}
    assert family_summary["families"][0]["case_sets"] == {"deterministic": 1, "unseen": 1}
    assert family_summary["families"][0]["case_styles"] == {"seen_style": 1, "unseen_style": 1}

    manifest_path = tmp_path / "evaluation_manifest.json"
    llm_path = tmp_path / "llm_benchmark_report.json"
    manifest_path.write_text(json.dumps(build_manifest(), ensure_ascii=False), encoding="utf-8")
    llm_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    evaluation_path = build_evaluation_report(output_dir=tmp_path, manifest_path=manifest_path, llm_report_path=llm_path)
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    style_rows = case_style_summary(report)
    by_style = {(row["case_set"], row["case_style"]): row for row in style_rows}
    assert by_style[("deterministic", "seen_style")]["passed"] == 1
    assert by_style[("unseen", "unseen_style")]["failed"] == 1
    assert evaluation["case_style_summary"] == style_rows
    assert "unseen_style" in (tmp_path / "evaluation_case_styles.csv").read_text(encoding="utf-8")
    assert "Seen / Unseen Style Summary" in (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")


def test_benchmark_report_summarizes_process_registry_failure_types(tmp_path: Path):
    case = benchmark_cases()[0]
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
        condition="algolab_full",
    )

    report_path = write_report(
        [
            {
                "case_id": case.id,
                "title": case.title,
                "family": case.family,
                "sample_index": 1,
                "ok": False,
                "errors": ["failure_type=coverage_error: 小 DP 表缺少逐帧状态转移"],
                "duration_s": 1.0,
            },
            {
                "case_id": case.id,
                "title": case.title,
                "family": "未注册算法族",
                "sample_index": 1,
                "ok": False,
                "errors": ["failure_type=process_uncovered: 未注册算法族只执行基础门禁"],
                "duration_s": 1.0,
            },
        ],
        tmp_path,
        args=report_args,
        started_at="2026-01-01T00:00:00",
        ended_at="2026-01-01T00:00:01",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["failure_summary"] == {"coverage_error": 1, "process_uncovered": 1}
    assert [item["failure_type"] for item in report["results"]] == ["coverage_error", "process_uncovered"]


def test_phase15_family_repair_context_and_prompt_distinguish_failure_categories():
    request = ProblemInput(
        problem="LeetCode 62. 不同路径，使用动态规划计算路径数。",
        input_data={"m": 2, "n": 2},
        expected_result=2,
        strategy_hint="动态规划",
    )
    previous = {
        "problem_title": "不同路径",
        "input_contract": "m,n",
        "variants": [
            {
                "id": "dp",
                "name": "二维 DP",
                "strategy": "动态规划",
                "code": "",
                "tracker_code": "",
            }
        ],
        "verifier_code": "",
    }
    errors = [
        "结果 3 与 expected 2 不一致",
        "ValidationError: events[0].targets Field required",
        "第 2 步 deps 未出现在 state：dp[0][1]",
        "第 3 步 dp[1][1] 不满足不同路径转移",
        "第 4 步 trace 跳步：直接从初始化跳到最终答案",
        "failure_type=demo_missing_deps: step 3 DP 转移缺少来源 deps",
    ]

    contexts = build_repair_context(errors, request=request, previous=previous)
    categories = {item["repair_category"] for item in contexts}
    failure_types = repair_failure_types(errors)

    assert categories == {"generation", "trace_schema"}
    assert set(failure_types) == {"generation", "trace_schema"}
    assert all(item["family"] == "" for item in contexts)
    assert all(item["family_guidance"] == [] for item in contexts)

    captured: dict[str, str] = {}

    def fake_chat_json(system_prompt, user_prompt):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        return {
            "problem_title": "不同路径",
            "input_contract": "m,n",
            "variants": [{"id": "dp", "name": "二维 DP", "code": "", "tracker_code": ""}],
            "verifier_code": "",
        }

    original = solution_generator.chat_json
    solution_generator.chat_json = fake_chat_json
    try:
        solution_generator.repair_solution_spec(request, previous, errors)
    finally:
        solution_generator.chat_json = original

    prompt = captured["user_prompt"]
    assert "generation" in prompt
    assert "trace_schema" in prompt
    assert "family=unknown" in prompt
    assert "dynamic_programming" not in prompt
    assert "dp_contract" not in prompt
    assert "不要生成 HTML" in prompt
    assert "failure_type=demo_missing_deps" in prompt
    assert "不要回退到旧 `Tracer` API" in captured["system_prompt"]


def test_demo_readiness_schema_passes_family_core_and_blocks_missing_demo_evidence():
    case = next(item for item in benchmark_cases() if item.id == "unique_paths")
    artifact, errors = materialize_case(case)

    assert errors == []
    assert artifact.validation.demo_readiness.status == "pass"
    assert artifact.validation.demo_readiness.variants[0].variant_id == "unique_paths"
    assert artifact.validation.demo_readiness.variants[0].phase_coverage["initialization"] is True
    assert artifact.validation.demo_readiness.variants[0].phase_coverage["transition"] is True
    assert artifact.validation.demo_readiness.variants[0].phase_coverage["answer"] is True

    bad_spec = {
        "problem_title": "演示证据缺失",
        "input_contract": "输入任意对象，返回固定结果。",
        "variants": [
            {
                "id": "bad_demo",
                "name": "缺失演示证据",
                "strategy": "构造缺少 reason/deps/state 的 trace。",
                "time_complexity": "O(1)",
                "space_complexity": "O(1)",
                "code": "def solve(input_data):\n    return 2\n",
                "tracker_code": """
def trace(input_data):
    return {
        "schema_version": "semantic-trace-v1",
        "algorithm": "演示证据缺失",
        "input_data": input_data,
        "result": 2,
        "pseudocode": ["写入答案"],
        "events": [
            {"step": 0, "op": "create", "targets": [{"id": "dp"}], "state": {"dp": [[1, 1], [1, 1]]}, "reason": "初始化。", "code_line": 1},
            {"step": 1, "op": "set", "targets": [{"id": "dp[1][1]"}], "value": 2, "state": {}, "code_line": 2},
            {"step": 2, "op": "mark", "targets": [{"id": "dp[1][1]"}], "state": {"dp": [[1, 1], [1, 2]], "answer": 2}, "role": "answer", "reason": "标记答案。", "code_line": 3},
        ],
    }
""",
            }
        ],
        "verifier_code": "def verify(input_data):\n    return 2\n",
    }

    bad_artifact, bad_errors = _try_materialize(
        ProblemInput(problem="演示证据缺失", input_data={"n": 1}, expected_result=2),
        bad_spec,
    )

    assert bad_errors
    assert bad_artifact.validation.demo_readiness.status == "fail"
    assert not bad_artifact.validation.release_gate.release_ready
    assert any("demo_missing_reason" in error for error in bad_errors)
    assert any("demo_missing_deps" in error for error in bad_errors)
    assert any("demo_missing_state" in error for error in bad_errors)


def test_demo_readiness_phase14_covers_each_strong_process_profile():
    cases_by_profile = {}
    for case in benchmark_cases():
        family_id = BENCHMARK_CASE_METADATA[case.id]["family_id"]
        cases_by_profile.setdefault(family_id, case)
    strong_profiles = {
        profile.family
        for profile in process_validation_registry()
        if profile.status == "strong"
    }

    assert strong_profiles <= set(cases_by_profile), strong_profiles - set(cases_by_profile)

    for profile in sorted(strong_profiles):
        case = cases_by_profile[profile]
        artifact, errors = materialize_case(case)
        assert errors == [], (profile, case.id, errors)
        assert artifact.validation.demo_readiness.status == "pass", (profile, case.id)

        trace = artifact.variants[0].trace
        assert trace is not None
        broken = trace.model_dump(mode="json")
        for event in broken["events"]:
            if event["op"] != "explain":
                event["reason"] = ""
                break
        report = validate_variant_demo_readiness(
            f"{case.id}_missing_reason",
            f"{case.variant_name} missing reason",
            SemanticTrace.model_validate(broken),
        )
        assert report.status == "fail", (profile, case.id, report)
        assert any("demo_missing_reason" in error for error in report.errors), (profile, case.id, report.errors)


def test_demo_readiness_phase14_family_rules_reject_group_specific_gaps():
    def report_for(raw_trace: dict):
        return validate_variant_demo_readiness(
            "phase14_bad",
            "P14.2 bad trace",
            SemanticTrace.model_validate(raw_trace),
        )

    report = report_for(
        _dp_contract_trace(
            "DP family-specific heuristics disabled",
            {"nums": [1]},
            1,
            [
                _dp_contract_event(0, "create", ["dp"], state={"dp": [0, 1], "dp_contract": {"subfamily": "1d"}}, reason="初始化 DP。"),
                _dp_contract_event(1, "mark", ["answer"], state={"dp": [0, 1], "answer": 1}, role="answer", reason="返回答案。"),
            ],
            pseudocode=["dp transition"],
        )
    )
    assert report.status == "pass", report
    assert report.errors == []
    return

    def assert_fails(raw_trace: dict, failure_type: str):
        report = report_for(raw_trace)
        assert report.status == "fail", report
        assert any(failure_type in error for error in report.errors), report.errors

    dp_contract = {"containers": ["dp"], "answer_position": "dp[1]", "expected_targets": ["dp[1]"], "subfamily": "1d"}
    assert_fails(
        _dp_contract_trace(
            "DP missing formula and answer position",
            {"nums": [1]},
            1,
            [
                _dp_contract_event(0, "create", ["dp"], state={"dp": [0, 0], "dp_contract": dp_contract}, reason="初始化 DP。"),
                _dp_contract_event(1, "set", ["dp[1]"], value=1, deps=["dp[0]"], state={"dp": [0, 1], "i": 1, "dp_contract": dp_contract}, reason="从前一项转移。"),
                _dp_contract_event(2, "mark", ["answer"], state={"dp": [0, 1], "answer": 1, "dp_contract": dp_contract}, role="answer", reason="返回答案。"),
            ],
            pseudocode=["dp transition"],
        ),
        "demo_algorithm_mismatch",
    )

    graph_contract = {"submode": "bfs", "source": "A", "expected_nodes": ["A", "B"]}
    assert_fails(
        _graph_contract_trace(
            "BFS missing edge check",
            {"graph": {"A": ["B"]}, "start": "A"},
            {"A": 0, "B": 1},
            [
                _graph_contract_event(0, "create", ["queue", "node:A"], state={"graph": {"A": ["B"]}, "queue": ["A"], "dist": {"A": 0}, "graph_contract": graph_contract}, reason="起点入队。"),
                _graph_contract_event(1, "pop", ["queue", "node:A"], state={"graph": {"A": ["B"]}, "queue": [], "dist": {"A": 0}, "graph_contract": graph_contract}, reason="弹出队首。"),
                _graph_contract_event(2, "mark", ["node:B"], state={"graph": {"A": ["B"]}, "queue": ["B"], "dist": {"A": 0, "B": 1}, "graph_contract": graph_contract}, role="visited", reason="首次访问 B。"),
                _graph_contract_event(3, "mark", ["dist"], state={"graph": {"A": ["B"]}, "dist": {"A": 0, "B": 1}, "answer": {"A": 0, "B": 1}, "graph_contract": graph_contract}, role="answer", reason="返回距离。"),
            ],
        ),
        "demo_missing_deps",
    )

    assert_fails(
        _array_contract_trace(
            "Binary search unexplained state jump",
            {"nums": [1, 3, 5, 7, 9, 11], "target": 11},
            5,
            [
                _family_contract_event(0, "create", ["nums", "pointer:left", "pointer:right"], state={"nums": [1, 3, 5, 7, 9, 11], "left": 0, "right": 5, "target": 11, "array_contract": {"submode": "binary_answer"}}, reason="初始化搜索区间。"),
                _family_contract_event(1, "move", ["pointer:left"], value=4, state={"nums": [1, 3, 5, 7, 9, 11], "left": 4, "right": 5, "target": 11, "array_contract": {"submode": "binary_answer"}}, reason="移动左指针。"),
                _family_contract_event(2, "mark", ["nums[5]"], state={"nums": [1, 3, 5, 7, 9, 11], "left": 5, "right": 5, "answer": 5, "array_contract": {"submode": "binary_answer"}}, role="answer", reason="返回答案。"),
            ],
        ),
        "demo_state_jump",
    )

    assert_fails(
        _family_contract_trace(
            "Monotonic stack missing popped contribution",
            {"temperatures": [70, 75]},
            [1, 0],
            [
                _family_contract_event(0, "create", ["stack", "answer"], state={"temperatures": [70, 75], "stack": [], "answer": [0, 0], "stack_order": "decreasing"}, reason="初始化单调栈。"),
                _family_contract_event(1, "push", ["stack", "temperatures[0]"], state={"temperatures": [70, 75], "stack": [0], "answer": [0, 0], "stack_order": "decreasing", "i": 0}, reason="下标入栈。"),
                _family_contract_event(2, "pop", ["stack", "temperatures[0]"], state={"temperatures": [70, 75], "stack": [], "answer": [0, 0], "stack_order": "decreasing", "i": 1}, reason="弹出栈顶。"),
                _family_contract_event(3, "mark", ["answer"], state={"temperatures": [70, 75], "stack": [1], "answer": [1, 0], "answer_ready": True}, role="answer", reason="返回答案。"),
            ],
        ),
        "demo_missing_deps",
    )

    assert_fails(
        _family_contract_trace(
            "KMP missing table pointer evidence",
            {"text": "ababa", "pattern": "aba"},
            0,
            [
                _family_contract_event(0, "create", ["text", "pattern"], state={"text": "ababa", "pattern": "aba", "family_contract": {"family": "string", "submode": "kmp"}}, reason="初始化字符串匹配。"),
                _family_contract_event(1, "mark", ["text[0:3]"], state={"text": "ababa", "pattern": "aba", "answer": 0, "family_contract": {"family": "string", "submode": "kmp"}}, role="answer", reason="找到匹配。"),
            ],
        ),
        "demo_algorithm_mismatch",
    )

    assert_fails(
        _family_contract_trace(
            "Backtracking missing undo",
            {"nums": [1]},
            [[1]],
            [
                _family_contract_event(0, "create", ["recursion_tree"], state={"nums": [1], "path": [], "used": [False], "call_stack": ["root"], "family_contract": {"family": "backtracking", "submode": "permutations"}}, reason="初始化搜索树。"),
                _family_contract_event(1, "enter", ["frame:perm(root_0)"], deps=["node:root_0"], state={"nums": [1], "path": [1], "used": [True], "call_stack": ["root", "root_0"], "family_contract": {"family": "backtracking", "submode": "permutations"}}, reason="选择数字进入下一层。"),
                _family_contract_event(2, "mark", ["recursion_tree"], state={"nums": [1], "path": [1], "used": [True], "answer": [[1]], "call_stack": ["root", "root_0"], "family_contract": {"family": "backtracking", "submode": "permutations"}}, role="answer", reason="记录答案。"),
            ],
        ),
        "demo_state_jump",
    )

    assert_fails(
        _family_contract_trace(
            "Heap missing invariant",
            {"nums": [3, 1], "k": 1},
            3,
            [
                _family_contract_event(0, "create", ["heap"], state={"nums": [3, 1], "heap": [], "family_contract": {"family": "heap", "submode": "topk_min_heap"}}, reason="初始化堆。"),
                _family_contract_event(1, "push", ["heap", "nums[0]"], state={"nums": [3, 1], "heap": [3], "i": 0, "family_contract": {"family": "heap", "submode": "topk_min_heap"}}, reason="入堆。"),
                _family_contract_event(2, "mark", ["heap"], state={"nums": [3, 1], "heap": [3], "answer": 3, "family_contract": {"family": "heap", "submode": "topk_min_heap"}}, role="answer", reason="返回堆顶。"),
            ],
        ),
        "demo_algorithm_mismatch",
    )

    assert_fails(
        _family_contract_trace(
            "Union find missing structure after union",
            {"isConnected": [[1, 1], [1, 1]]},
            1,
            [
                _family_contract_event(0, "create", ["union_find"], state={"isConnected": [[1, 1], [1, 1]], "union_find": {"parent": {"0": "0", "1": "1"}}}, reason="初始化并查集。"),
                _family_contract_event(1, "link", ["node:0"], deps=["node:1"], state={"isConnected": [[1, 1], [1, 1]], "i": 0, "j": 1}, reason="合并相连城市。"),
                _family_contract_event(2, "mark", ["union_find"], state={"isConnected": [[1, 1], [1, 1]], "answer": 1}, role="answer", reason="返回集合数量。"),
            ],
        ),
        "demo_algorithm_mismatch",
    )


def test_demo_readiness_phase14_accepts_topological_sort_indegree_edge_deps():
    case = next(item for item in benchmark_cases() if item.id == "graph_topological_sort")
    sample = case.samples[0]
    variant = SolutionVariant(
        id=case.id,
        name=case.variant_name,
        strategy=case.strategy,
        time_complexity=case.time_complexity,
        space_complexity=case.space_complexity,
        code=case.code,
        tracker_code=case.tracker_code,
    )
    trace = execute_variant(variant, sample.input_data).trace

    assert trace is not None
    assert any(
        event.op.value == "set"
        and any(target.id.startswith("indegree[") for target in event.targets)
        and any(dep.id.startswith("edge:") for dep in event.deps)
        for event in trace.events
    )

    report = validate_variant_demo_readiness(case.id, case.variant_name, trace)

    assert report.status == "pass", report.errors
    assert not any("图演示缺少边检查帧" in error for error in report.errors)


def test_r7_demo_readiness_accepts_declared_tree_dp_take_skip_transition_targets():
    contract = {
        "containers": ["dp_take", "dp_skip", "answer"],
        "answer_position": "answer",
        "expected_targets": ["dp_take[1]", "dp_skip[1]", "answer"],
        "subfamily": "tree",
    }
    family_contract = {"family": "tree", "submode": "tree_dp", "expected_nodes": ["1"], "expected_frames": ["frame:tree_dp(1)"]}
    tree = {"nodes": [{"id": "1", "value": 3}], "edges": []}
    trace = SemanticTrace.model_validate(
        _family_contract_trace(
            "树形 DP take/skip demo",
            {"tree": tree},
            3,
            [
                _family_contract_event(
                    0,
                    "create",
                    ["tree"],
                    state={"tree": tree, "current": "1", "dp_take": {}, "dp_skip": {}, "dp_contract": contract, "family_contract": family_contract},
                    reason="初始化树形 DP。",
                ),
                _family_contract_event(
                    1,
                    "enter",
                    ["frame:tree_dp(1)"],
                    deps=["node:1"],
                    state={"tree": tree, "current": "1", "dp_take": {}, "dp_skip": {}, "dp_contract": contract, "family_contract": family_contract},
                    reason="进入节点 1 的后序 frame。",
                ),
                _family_contract_event(
                    2,
                    "set",
                    ["dp_take[1]"],
                    value=3,
                    deps=["node:1"],
                    state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {}, "formula": "dp_take[1]=weight[1]", "dp_contract": contract, "family_contract": family_contract},
                    reason="选择节点 1，写入 take 状态。",
                ),
                _family_contract_event(
                    3,
                    "set",
                    ["dp_skip[1]"],
                    value=0,
                    deps=["node:1"],
                    state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "formula": "dp_skip[1]=0", "dp_contract": contract, "family_contract": family_contract},
                    reason="不选叶子节点时收益为 0。",
                ),
                _family_contract_event(
                    4,
                    "exit",
                    ["frame:tree_dp(1)"],
                    deps=["node:1"],
                    state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "return_values": {"1": {"take": 3, "skip": 0}}, "dp_contract": contract, "family_contract": family_contract},
                    reason="节点 1 返回 take/skip。",
                ),
                _family_contract_event(
                    5,
                    "set",
                    ["answer"],
                    value=3,
                    deps=["dp_take[1]", "dp_skip[1]"],
                    role="answer",
                    state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "answer": 3, "formula": "answer=max(dp_take[1],dp_skip[1])", "dp_contract": contract, "family_contract": family_contract},
                    reason="根节点 take/skip 取最大作为答案。",
                ),
            ],
        )
    )

    report = validate_variant_demo_readiness("tree_dp_r7", "树形 DP", trace)

    assert report.status == "pass", report.errors
    assert not any("DP 演示缺少状态转移写入帧" in error for error in report.errors)


def test_r7_demo_readiness_accepts_tree_dp_state_derived_take_skip_transitions_without_deps():
    contract = {
        "containers": ["dp_take", "dp_skip", "answer"],
        "answer_position": "answer",
        "expected_targets": ["dp_take[1]", "dp_skip[1]", "answer"],
        "subfamily": "tree",
    }
    family_contract = {"family": "tree", "submode": "tree_dp", "expected_nodes": ["1"], "expected_frames": ["frame:tree_dp(1)"]}
    tree = {"nodes": [{"id": "1", "value": 3}], "edges": []}
    trace = SemanticTrace.model_validate(
        _family_contract_trace(
            "树形 DP state-derived take/skip demo",
            {"tree": tree},
            3,
            [
                _family_contract_event(
                    0,
                    "create",
                    ["tree"],
                    state={"tree": tree, "current": "1", "dp_take": {}, "dp_skip": {}, "dp_contract": contract, "family_contract": family_contract},
                    reason="初始化树形 DP。",
                ),
                _family_contract_event(
                    1,
                    "enter",
                    ["frame:tree_dp(1)"],
                    deps=["node:1"],
                    state={"tree": tree, "current": "1", "dp_take": {}, "dp_skip": {}, "dp_contract": contract, "family_contract": family_contract},
                    reason="进入节点 1 的后序 frame。",
                ),
                _family_contract_event(
                    2,
                    "set",
                    ["dp_take[1]"],
                    value=3,
                    state={
                        "tree": tree,
                        "current": "1",
                        "dp_take": {"1": 3},
                        "dp_skip": {},
                        "formula": "dp_take[1]=weight[1]",
                        "dp_contract": contract,
                        "family_contract": family_contract,
                    },
                    reason="写入节点 1 选择当前节点的状态。",
                ),
                _family_contract_event(
                    3,
                    "set",
                    ["dp_skip[1]"],
                    value=0,
                    state={
                        "tree": tree,
                        "current": "1",
                        "dp_take": {"1": 3},
                        "dp_skip": {"1": 0},
                        "formula": "dp_skip[1]=0",
                        "dp_contract": contract,
                        "family_contract": family_contract,
                    },
                    reason="写入节点 1 不选择当前节点的状态。",
                ),
                _family_contract_event(
                    4,
                    "exit",
                    ["frame:tree_dp(1)"],
                    deps=["node:1"],
                    state={
                        "tree": tree,
                        "current": "1",
                        "dp_take": {"1": 3},
                        "dp_skip": {"1": 0},
                        "return_values": {"1": {"take": 3, "skip": 0}},
                        "dp_contract": contract,
                        "family_contract": family_contract,
                    },
                    reason="节点 1 返回 take/skip。",
                ),
                _family_contract_event(
                    5,
                    "set",
                    ["answer"],
                    value=3,
                    deps=["dp_take[1]", "dp_skip[1]"],
                    role="answer",
                    state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "answer": 3, "formula": "answer=max(dp_take[1],dp_skip[1])", "dp_contract": contract, "family_contract": family_contract},
                    reason="根节点 take/skip 取最大作为答案。",
                ),
            ],
        )
    )

    report = validate_variant_demo_readiness("tree_dp_r7_state_derived", "树形 DP", trace)

    assert report.status == "pass", report.errors
    assert not any("DP 转移帧缺少来源 deps" in error for error in report.errors)


def test_demo_readiness_phase14_does_not_treat_bipartite_graph_as_binary_search():
    case = next(item for item in benchmark_cases() if item.id == "graph_bipartite_coloring")
    sample = case.samples[0]
    variant = SolutionVariant(
        id=case.id,
        name=case.variant_name,
        strategy=case.strategy,
        time_complexity=case.time_complexity,
        space_complexity=case.space_complexity,
        code=case.code,
        tracker_code=case.tracker_code,
    )
    trace = execute_variant(variant, sample.input_data).trace

    assert trace is not None
    assert trace.algorithm == "二分图染色"
    assert any("graph_contract" in event.state for event in trace.events)

    report = validate_variant_demo_readiness(case.id, case.variant_name, trace)

    assert report.status == "pass", report.errors
    assert not any("二分演示" in error for error in report.errors)


def test_demo_readiness_phase14_accepts_kruskal_mst_union_find_state():
    case = next(item for item in benchmark_cases() if item.id == "kruskal_mst_weight")
    sample = case.samples[0]
    variant = SolutionVariant(
        id=case.id,
        name=case.variant_name,
        strategy=case.strategy,
        time_complexity=case.time_complexity,
        space_complexity=case.space_complexity,
        code=case.code,
        tracker_code=case.tracker_code,
    )
    trace = execute_variant(variant, sample.input_data).trace

    assert trace is not None
    assert any("union_find" in event.state and "mst_edges" in event.state for event in trace.events)
    assert any(
        event.op.value == "compare" and any(target.id.startswith("edge:") for target in event.targets)
        for event in trace.events
    )

    report = validate_variant_demo_readiness(case.id, case.variant_name, trace)

    assert report.status == "pass", report.errors
    assert not any("图演示缺少 frontier/visited/dist" in error for error in report.errors)


def test_demo_readiness_phase14_accepts_empty_pattern_string_short_path():
    case = next(item for item in benchmark_cases() if item.id == "kmp")
    sample = case.samples[2]
    variant = SolutionVariant(
        id=case.id,
        name=case.variant_name,
        strategy=case.strategy,
        time_complexity=case.time_complexity,
        space_complexity=case.space_complexity,
        code=case.code,
        tracker_code=case.tracker_code,
    )
    trace = execute_variant(variant, sample.input_data).trace

    assert trace is not None
    assert sample.input_data["pattern"] == ""
    assert len(trace.events) == 1
    assert trace.events[0].state["pattern"] == ""

    report = validate_variant_demo_readiness(case.id, case.variant_name, trace)

    assert report.status == "pass", report.errors
    assert not any("字符串演示缺少文本/模式指针" in error for error in report.errors)


def test_demo_readiness_phase14_accepts_pattern_longer_than_text_short_path():
    case = next(item for item in benchmark_cases() if item.id == "rabin_karp")
    sample = case.samples[2]
    variant = SolutionVariant(
        id=case.id,
        name=case.variant_name,
        strategy=case.strategy,
        time_complexity=case.time_complexity,
        space_complexity=case.space_complexity,
        code=case.code,
        tracker_code=case.tracker_code,
    )
    trace = execute_variant(variant, sample.input_data).trace

    assert trace is not None
    assert len(sample.input_data["pattern"]) > len(sample.input_data["text"])
    assert all(event.state.get("window_hashes") == [] for event in trace.events)

    report = validate_variant_demo_readiness(case.id, case.variant_name, trace)

    assert report.status == "pass", report.errors
    assert not any("字符串演示缺少文本/模式指针" in error for error in report.errors)


def test_r2_demo_readiness_uses_string_submode_specific_evidence():
    rabin_trace = _family_contract_trace(
        "Rabin-Karp rolling hash demo",
        {"text": "abcab", "pattern": "ab"},
        [0, 3],
        [
            _family_contract_event(
                0,
                "create",
                ["text", "pattern"],
                state={
                    "text": "abcab",
                    "pattern": "ab",
                    "i": 0,
                    "j": 0,
                    "pattern_hash": 25027,
                    "window_hashes": [25027, 25285, 25540, 25027],
                    "array_contract": {"submode": "sliding_window"},
                    "family_contract": {"family": "string", "submode": "rabin_karp", "expected_tables": ["pattern_hash", "window_hashes"]},
                },
                reason="Rabin-Karp 使用窗口哈希作为聚合状态。",
            ),
            _family_contract_event(
                1,
                "compare",
                ["text[0]", "pattern[0]"],
                deps=["window_hashes[0]", "pattern_hash"],
                state={
                    "text": "abcab",
                    "pattern": "ab",
                    "i": 0,
                    "j": 0,
                    "pattern_hash": 25027,
                    "window_hashes": [25027, 25285, 25540, 25027],
                    "answer": [0, 3],
                    "array_contract": {"submode": "sliding_window"},
                    "family_contract": {"family": "string", "submode": "rabin_karp", "expected_tables": ["pattern_hash", "window_hashes"]},
                },
                reason="窗口哈希命中后比较字符。",
            ),
        ],
    )
    rabin_report = validate_variant_demo_readiness("rabin_r2", "Rabin-Karp", SemanticTrace.model_validate(rabin_trace))
    assert rabin_report.status == "pass", rabin_report.errors
    assert not any("窗口演示缺少窗口边界或聚合状态" in error for error in rabin_report.errors)

    manacher_trace = _family_contract_trace(
        "Manacher missing radius demo",
        {"s": "aba"},
        3,
        [
            _family_contract_event(
                0,
                "create",
                ["text"],
                state={"text": "aba", "center": 1, "family_contract": {"family": "string", "submode": "manacher", "expected_tables": ["radius"]}},
                reason="初始化 Manacher。",
            ),
            _family_contract_event(
                1,
                "compare",
                ["text[0]", "text[2]"],
                state={"text": "aba", "center": 1, "answer": 3, "family_contract": {"family": "string", "submode": "manacher", "expected_tables": ["radius"]}},
                reason="中心扩展。",
            ),
        ],
    )
    manacher_report = validate_variant_demo_readiness("manacher_r2", "Manacher", SemanticTrace.model_validate(manacher_trace))
    assert manacher_report.status == "pass", manacher_report.errors
    assert not any("Manacher 演示缺少 radius / p 半径表" in error for error in manacher_report.errors), manacher_report.errors
    assert not any("字符串演示缺少表项、哈希、半径或前缀计数状态" in error for error in manacher_report.errors)


def test_demo_readiness_failure_types_enter_llm_and_evaluation_reports(tmp_path: Path):
    for failure_type in (
        "demo_missing_reason",
        "demo_missing_deps",
        "demo_state_jump",
        "demo_algorithm_mismatch",
    ):
        assert classify_failure(f"failure_type={failure_type}: synthetic demo failure") == failure_type

    manifest = build_manifest()
    llm_report = {
        "kind": "llm_benchmark_report",
        "config": {"model": "demo-model", "benchmark_condition": "algolab_full"},
        "results": [
            {"case_id": "unique_paths", "family": "DP 基础", "ok": False, "errors": ["failure_type=demo_missing_reason: step 1 缺少 reason"]},
            {"case_id": "graph_bfs", "family": "BFS/DFS 基础图", "ok": False, "errors": ["failure_type=demo_missing_deps: step 2 缺少 deps"]},
            {"case_id": "binary_search", "family": "二分", "ok": False, "errors": ["failure_type=demo_state_jump: pointer:left 无解释跳变"]},
            {"case_id": "kmp", "family": "字符串高级算法", "ok": False, "errors": ["failure_type=demo_algorithm_mismatch: 缺少 KMP 表项"]},
        ],
    }
    manifest_path = tmp_path / "evaluation_manifest.json"
    llm_path = tmp_path / "llm_benchmark_report.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    llm_path.write_text(json.dumps(llm_report, ensure_ascii=False), encoding="utf-8")

    report_path = build_evaluation_report(output_dir=tmp_path, manifest_path=manifest_path, llm_report_path=llm_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["failure_type_summary"] == {
        "demo_algorithm_mismatch": 1,
        "demo_missing_deps": 1,
        "demo_missing_reason": 1,
        "demo_state_jump": 1,
    }
    assert "demo_state_jump" in (tmp_path / "evaluation_failure_types.csv").read_text(encoding="utf-8")


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


def test_llm_benchmark_regenerates_after_candidate_repair_fails(monkeypatch):
    request = ProblemInput(problem="候选重生成测试", input_data={"nums": [2, 1]}, expected_result=[1, 2])
    fail_gate = ReleaseGate(
        artifact_ready=True,
        process_ready=False,
        trace_ready=False,
        visual_ready=True,
        release_ready=False,
        blocking_reasons=["结果错误"],
    )
    pass_gate = ReleaseGate(
        artifact_ready=True,
        process_ready=True,
        trace_ready=True,
        visual_ready=True,
        release_ready=True,
    )
    failed = BuildArtifact(
        problem_title="候选重生成测试",
        input_contract="",
        input_data=request.input_data,
        expected_result=request.expected_result,
        variants=[],
        scenes={},
        validation=ValidationReport(errors=["结果错误"], release_gate=fail_gate),
    )
    passed = BuildArtifact(
        problem_title="候选重生成测试",
        input_contract="",
        input_data=request.input_data,
        expected_result=request.expected_result,
        variants=[],
        scenes={},
        validation=ValidationReport(errors=[], release_gate=pass_gate),
    )
    calls = {"generate": 0, "repair": 0, "materialized": []}

    def fake_generate(_request):
        calls["generate"] += 1
        return {"candidate": calls["generate"], "variants": []}

    def fake_repair(_request, spec, _errors):
        calls["repair"] += 1
        repaired = dict(spec)
        repaired["repaired"] = True
        return repaired

    def fake_materialize(_request, spec):
        calls["materialized"].append((spec.get("candidate"), bool(spec.get("repaired"))))
        if spec.get("candidate") == 2:
            return passed, []
        return failed, ["结果错误"]

    monkeypatch.setattr("scripts.run_llm_benchmark.generate_solution_spec", fake_generate)
    monkeypatch.setattr("scripts.run_llm_benchmark._try_materialize", fake_materialize)
    monkeypatch.setattr("scripts.run_llm_benchmark.repair_solution_spec", fake_repair)

    artifact = build_artifact_timed(request, max_rounds=1, max_candidates=2)

    assert artifact.validation.release_gate.release_ready is True
    assert calls == {
        "generate": 2,
        "repair": 1,
        "materialized": [(1, False), (1, True), (2, False)],
    }


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


def test_llm_json_with_metadata_records_usage_present_and_missing():
    class FakeCompletions:
        def __init__(self, responses):
            self.responses = list(responses)

        def create(self, **_kwargs):
            return self.responses.pop(0)

    class FakeClient:
        def __init__(self, responses):
            self.chat = type("Chat", (), {})()
            self.chat.completions = FakeCompletions(responses)

    def response(content, usage=None):
        message = type("Message", (), {"content": content})()
        choice = type("Choice", (), {"message": message})()
        data = type("Response", (), {"choices": [choice]})()
        if usage is not None:
            data.usage = usage
        return data

    old_client = llm_client._client
    old_env = os.environ.get("ALGOLAB_LLM_JSON_RETRIES")
    try:
        os.environ["ALGOLAB_LLM_JSON_RETRIES"] = "0"
        llm_client.clear_model_calls()
        llm_client._client = FakeClient([
            response(
                '{"ok": true}',
                type("Usage", (), {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3})(),
            )
        ])
        first = llm_client.chat_json_with_metadata("system", "user", model="fake-model", kind="generation")
        assert first["content"] == {"ok": True}
        assert first["model_call"]["usage_available"] is True
        assert first["model_call"]["prompt_tokens"] == 1
        assert llm_client.consume_model_calls()[0]["total_tokens"] == 3

        llm_client._client = FakeClient([response('{"ok": true}')])
        second = llm_client.chat_json_with_metadata("system", "user", model="fake-model", kind="repair")
        assert second["model_call"]["usage_available"] is False
        assert second["model_call"]["prompt_tokens"] is None
        assert llm_client.consume_model_calls()[0]["kind"] == "repair"
    finally:
        llm_client._client = old_client
        llm_client.clear_model_calls()
        if old_env is None:
            os.environ.pop("ALGOLAB_LLM_JSON_RETRIES", None)
        else:
            os.environ["ALGOLAB_LLM_JSON_RETRIES"] = old_env


def test_llm_json_default_retries_allow_four_empty_responses_then_success():
    class FakeCompletions:
        def __init__(self, responses):
            self.responses = list(responses)
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            return self.responses.pop(0)

    class FakeClient:
        def __init__(self, responses):
            self.chat = type("Chat", (), {})()
            self.chat.completions = FakeCompletions(responses)

    def response(content):
        message = type("Message", (), {"content": content})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()

    old_client = llm_client._client
    old_env = os.environ.get("ALGOLAB_LLM_JSON_RETRIES")
    fake = FakeClient([response(""), response(""), response(""), response(""), response('{"ok": true}')])
    try:
        os.environ.pop("ALGOLAB_LLM_JSON_RETRIES", None)
        llm_client.clear_model_calls()
        llm_client._client = fake
        result = llm_client.chat_json_with_metadata("system", "user", model="fake-model")
    finally:
        llm_client._client = old_client
        llm_client.clear_model_calls()
        if old_env is None:
            os.environ.pop("ALGOLAB_LLM_JSON_RETRIES", None)
        else:
            os.environ["ALGOLAB_LLM_JSON_RETRIES"] = old_env

    assert fake.chat.completions.calls == 5
    assert result["content"] == {"ok": True}


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


def test_benchmark_html_checker_resolves_required_phase8_cases(tmp_path: Path):
    report = {
        "results": [
            {"case_id": "unique_paths", "ok": True, "html": str(tmp_path / "unique.html")},
            {"case_id": "graph_bfs", "ok": True, "html": str(tmp_path / "bfs.html")},
            {"case_id": "binary_search", "ok": True, "html": str(tmp_path / "binary.html")},
            {"case_id": "daily_temperatures", "ok": True, "html": str(tmp_path / "daily.html")},
            {"case_id": "two_sum", "ok": True, "html": str(tmp_path / "two_sum.html")},
        ]
    }
    report_path = tmp_path / "llm_benchmark_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    required = ["unique_paths", "graph_bfs", "binary_search", "daily_temperatures"]
    paths = resolve_required_case_htmls(report_path, required_cases=required)
    assert [path.name for path in paths] == ["unique.html", "bfs.html", "binary.html", "daily.html"]

    incomplete_path = tmp_path / "incomplete_report.json"
    incomplete_path.write_text(json.dumps({"results": report["results"][:3]}), encoding="utf-8")
    try:
        resolve_required_case_htmls(incomplete_path, required_cases=required)
    except ValueError as exc:
        assert "daily_temperatures" in str(exc)
    else:
        raise AssertionError("missing required case should fail")


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
    family_coverage = {item["family"]: item for item in report["family_coverage"]}
    assert {"0-1 背包 / 子集和", "二分"} <= set(family_coverage)
    assert family_coverage["0-1 背包 / 子集和"]["total"] == 1
    assert family_coverage["0-1 背包 / 子集和"]["passed"] == 1
    assert family_coverage["二分"]["layouts"]
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
        assert demo["artifact_json"].endswith("artifact.json")
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
    assert "算法族覆盖" in html
    assert 'id="family-coverage"' in html
    assert 'id="family"' in html
    assert "artifact.json" in html


def test_demo_dashboard_groups_by_family_and_gate_layer(tmp_path: Path):
    index = build_dashboard(
        tmp_path / "dashboard",
        demo_ids=["binary_search", "graph_bfs"],
        style="stable",
    )
    report = json.loads(index.with_name("dashboard.json").read_text(encoding="utf-8"))

    for demo in report["demos"]:
        assert demo["family_id"]
        assert demo["subfamily_id"]
        assert demo["gate_layer"] == "family_core"
        assert demo["support_level"] == "strong"
        assert demo["process_profile"] in {"binary_search", "bfs"}
        assert demo["oracle_type"] in {"independent_reference", "property"}
        assert demo["oracle_risk"] == "none"
        assert demo["oracle_notes"]
        assert demo["demo_required"] is True

    coverage = {(row["family"], row["gate_layer"]): row for row in report["family_coverage"]}
    assert ("二分", "family_core") in coverage
    assert ("BFS/DFS 基础图", "family_core") in coverage
    assert coverage[("二分", "family_core")]["family_id"] == "binary_search"
    assert coverage[("BFS/DFS 基础图", "family_core")]["process_profile"] == "bfs"

    core_table = index.with_name("dashboard_core_table.csv").read_text(encoding="utf-8")
    for field in (
        "family_id",
        "subfamily_id",
        "gate_layer",
        "support_level",
        "process_profile",
        "oracle_type",
        "oracle_risk",
        "oracle_reference",
        "demo_required",
    ):
        assert field in core_table
    html = index.read_text(encoding="utf-8")
    assert "Gate layer" in html
    assert "family_core" in html


def test_demo_dashboard_exposes_phase14_family_layer_statuses_and_reports(tmp_path: Path):
    index = build_dashboard(
        tmp_path / "dashboard",
        demo_ids=["binary_search", "graph_bfs"],
        style="stable",
    )
    report = json.loads(index.with_name("dashboard.json").read_text(encoding="utf-8"))

    required_layers = {"answer", "process", "demo", "scene", "html"}
    for demo in report["demos"]:
        assert set(demo["layer_statuses"]) == required_layers
        assert all(demo["layer_statuses"][layer]["status"] == "pass" for layer in required_layers)
        assert demo["demo_readiness_report_json"].endswith("demo_readiness_report.json")
        assert (index.parent / demo["demo_readiness_report_json"]).exists()
        assert demo["artifact_json"].endswith("artifact.json")
        assert demo["validation_report_json"].endswith("validation_report.json")

    for row in report["family_coverage"]:
        assert set(row["gate_statuses"]) == required_layers
        assert all(row["gate_statuses"][layer]["status"] == "pass" for layer in required_layers)
        assert row["current_level"] == "strong"
        assert row["process_status"] == "strong"
        assert row["process_failure_type"] == ""

    html = index.read_text(encoding="utf-8")
    for phrase in (
        "算法族能力等级",
        "Answer",
        "Process",
        "Demo",
        "Scene",
        "HTML",
        "Fallback / uncovered",
        "demo readiness",
        'id="support-level"',
        "demo_readiness_report.json",
    ):
        assert phrase in html


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
    cases_by_id = {case["id"]: case for case in manifest["cases"]}
    two_sum = cases_by_id["two_sum"]
    assert two_sum["problem"]
    assert two_sum["visual_forms"] == two_sum["expected_layouts"]
    assert "artifact_json" in two_sum["artifact_paths"]
    assert "html" in two_sum["artifact_paths"]
    assert len(two_sum["samples"]) == two_sum["sample_count"]
    assert two_sum["samples"][0]["input_data"] == next(case for case in benchmark_cases() if case.id == "two_sum").samples[0].input_data
    assert two_sum["samples"][0]["expected"] == next(case for case in benchmark_cases() if case.id == "two_sum").samples[0].expected
    assert two_sum["samples"][0]["artifact_paths"]["json"].endswith("llm_two_sum_0.json")
    assert two_sum["samples"][0]["artifact_paths"]["html"].endswith("llm_two_sum_0.html")

    path = write_manifest(tmp_path)
    assert path.exists()
    csv_path = tmp_path / "evaluation_cases.csv"
    sample_csv_path = tmp_path / "evaluation_samples.csv"
    assert csv_path.exists()
    assert sample_csv_path.exists()
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written == manifest
    assert "linear_regression_single_step" in csv_path.read_text(encoding="utf-8")
    sample_csv_text = sample_csv_path.read_text(encoding="utf-8")
    assert "two_sum" in sample_csv_text
    assert "llm_two_sum_0.json" in sample_csv_text


def test_evaluation_manifest_exports_phase10_case_metadata_and_summaries(tmp_path: Path):
    manifest = build_manifest()
    summary = manifest["summary"]

    assert "families_by_id" in summary
    assert "subfamilies" in summary
    assert "gate_layers" in summary
    assert "support_levels" in summary
    assert "process_profiles" in summary
    assert "oracle_types" in summary
    assert "oracle_risks" in summary
    assert "demo_required_count" in summary
    assert summary["gate_layers"]["family_core"] >= 1
    assert summary["process_profiles"]["dp"] >= 1

    cases_by_id = {case["id"]: case for case in manifest["cases"]}
    binary = cases_by_id["binary_search"]
    assert binary["family_id"] == "binary_search"
    assert binary["subfamily_id"] == "closed_interval_search"
    assert binary["gate_layer"] == "family_core"
    assert binary["support_level"] == "strong"
    assert binary["process_profile"] == "binary_search"
    assert binary["oracle_type"] == "independent_reference"
    assert binary["oracle_risk"] == "none"
    assert binary["oracle_notes"]
    assert binary["demo_required"] is True

    two_sum = cases_by_id["two_sum"]
    assert two_sum["family_id"] == "hash_map"
    assert two_sum["support_level"] == "medium_plus"
    assert two_sum["process_profile"] == "hash"
    assert two_sum["oracle_type"] == "bruteforce"
    assert two_sum["oracle_risk"] == "none"

    tarjan = cases_by_id["tarjan_scc"]
    assert tarjan["oracle_risk"] == "verifier_matches_solve"
    assert tarjan["oracle_reference"] == "tests.oracles.advanced_graph_oracle_examples"

    path = write_manifest(tmp_path)
    csv_text = (tmp_path / "evaluation_cases.csv").read_text(encoding="utf-8")
    for field in (
        "family_id",
        "subfamily_id",
        "gate_layer",
        "support_level",
        "process_profile",
        "oracle_type",
        "oracle_risk",
        "oracle_notes",
        "oracle_reference",
        "demo_required",
    ):
        assert field in csv_text
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["summary"]["gate_layers"] == summary["gate_layers"]


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
        "config": {
            "model": "demo-model",
            "max_rounds": 2,
            "llm": {"model": "demo-model", "base_url": "http://example.invalid/v1"},
        },
        "total": 2,
        "passed": 1,
        "failed": 1,
        "failure_summary": {"process_invariant": 1},
        "repair_failure_summary": {"schema_error": 1},
        "browser_smoke": [{"ok": True}, {"ok": False}],
        "results": [
            {
                "case_id": "binary_search",
                "family": "二分",
                "ok": True,
                "phase_timings": [
                    {"phase": "generate", "status": "ok"},
                    {"phase": "materialize_round_0", "status": "error"},
                    {"phase": "repair_round_0", "status": "ok"},
                    {"phase": "materialize_round_1", "status": "ok"},
                ],
            },
            {
                "case_id": "graph_bfs",
                "family": "BFS/DFS 基础图",
                "ok": False,
                "failure_type": "process_invariant",
                "phase_timings": [
                    {"phase": "generate", "status": "ok"},
                    {"phase": "materialize_round_0", "status": "error"},
                ],
            },
        ],
    }
    family_gate = {
        "schema_version": "family-release-gate-v1",
        "overall_ready": True,
        "summary": {
            "case_count": 47,
            "sample_count": 131,
            "answer_pass_rate": 1.0,
            "process_pass_rate": 1.0,
            "demo_readiness_pass_rate": 1.0,
            "process_fallback_cases": 1,
            "process_uncovered_cases": 5,
            "degraded_family_count": 6,
        },
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
    assert {item["baseline"] for item in comparisons} >= {
        "pure_llm_judge",
        "code2video_manim",
        "no_correctness_gate_renderer",
        "direct_html_baseline",
        "no_process_validator_ablation",
        "no_scenegraph_compiler_ablation",
    }

    manifest_path = tmp_path / "evaluation_manifest.json"
    dashboard_path = tmp_path / "dashboard.json"
    llm_path = tmp_path / "llm_benchmark_report.json"
    family_gate_path = tmp_path / "family_release_gate.json"
    human_path = tmp_path / "human.csv"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    dashboard_path.write_text(json.dumps(dashboard, ensure_ascii=False), encoding="utf-8")
    llm_path.write_text(json.dumps(llm_report, ensure_ascii=False), encoding="utf-8")
    family_gate_path.write_text(json.dumps(family_gate, ensure_ascii=False), encoding="utf-8")
    human_path.write_text("case_id,score\nbinary_search,4\ngraph_bfs,5\n", encoding="utf-8")

    report_path = build_evaluation_report(
        output_dir=tmp_path,
        manifest_path=manifest_path,
        dashboard_path=dashboard_path,
        llm_report_path=llm_path,
        human_ratings_path=human_path,
        family_gate_path=family_gate_path,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_metrics = {metric["name"]: metric for metric in report["metrics"]}
    assert report_metrics["human_teaching_quality_score"]["value"] == 4.5
    assert report["model_config"]["model"] == "demo-model"
    assert report["model_config"]["llm"]["base_url"] == "http://example.invalid/v1"
    assert report["repair_summary"]["max_rounds_configured"] == 2
    assert report["repair_summary"]["cases_with_repair"] == 1
    assert report["repair_summary"]["repair_rounds_attempted"] == 1
    assert report["repair_summary"]["repair_successes"] == 1
    assert report["family_release_gate"]["status"] == "ok"
    assert report["family_release_gate"]["sample_count"] == 131
    assert report["family_release_gate"]["process_uncovered_cases"] == 5
    family_by_name = {item["family"]: item for item in report["family_summary"]}
    assert family_by_name["二分"]["pass_rate"] == 1.0
    assert family_by_name["BFS/DFS 基础图"]["failure_types"] == {"process_invariant": 1}
    assert {item["baseline"] for item in report["comparisons"]} >= {
        "pure_llm_judge",
        "code2video_manim",
        "no_correctness_gate_renderer",
        "direct_html_baseline",
        "no_process_validator_ablation",
        "no_scenegraph_compiler_ablation",
    }
    assert (tmp_path / "evaluation_metrics.csv").exists()
    assert (tmp_path / "evaluation_comparisons.csv").exists()
    assert (tmp_path / "evaluation_core_cases.csv").exists()
    assert (tmp_path / "evaluation_family_summary.csv").exists()
    assert (tmp_path / "evaluation_report.md").exists()
    assert "generation_success_rate" in (tmp_path / "evaluation_metrics.csv").read_text(encoding="utf-8")
    assert "纯 LLM judge" in (tmp_path / "evaluation_comparisons.csv").read_text(encoding="utf-8")
    assert "process_invariant" in (tmp_path / "evaluation_family_summary.csv").read_text(encoding="utf-8")
    assert "## Family Summary" in (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")
    assert "## Family Release Gate" in (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")
    assert "## Comparisons" in (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")


def test_evaluation_report_summarizes_baseline_ablation_conditions(tmp_path: Path):
    manifest = build_manifest()
    llm_report = {
        "kind": "llm_benchmark_report",
        "config": {"model": "demo-model", "benchmark_condition": "algolab_full"},
        "results": [
            {
                "case_id": "two_sum",
                "family": "哈希 / 双指针",
                "ok": True,
                "condition": "algolab_full",
            },
            {
                "case_id": "binary_search",
                "family": "二分",
                "ok": False,
                "condition": "direct_html_baseline",
                "failure_type": "html_error",
            },
            {
                "case_id": "graph_bfs",
                "family": "BFS/DFS 基础图",
                "ok": False,
                "ablation": "no_process_validator",
                "error": "failure_type=process_invariant: BFS 层级错误未被过程校验拦截",
            },
            {
                "case_id": "unique_paths",
                "family": "DP 基础",
                "ok": False,
                "experiment_condition": "no_scenegraph_compiler",
                "errors": ["scene compiler disabled caused scene validator failure"],
            },
        ],
    }

    summary = condition_summary(llm_report)
    by_condition = {row["condition"]: row for row in summary}
    assert by_condition["algolab_full"]["pass_rate"] == 1.0
    assert by_condition["direct_html_baseline"]["kind"] == "baseline"
    assert by_condition["direct_html_baseline"]["failure_types"] == {"html_error": 1}
    assert by_condition["no_process_validator"]["kind"] == "ablation"
    assert by_condition["no_process_validator"]["failure_types"] == {"process_invariant": 1}
    assert by_condition["no_scenegraph_compiler"]["kind"] == "ablation"
    assert by_condition["no_scenegraph_compiler"]["failure_types"] == {"scene_error": 1}

    manifest_path = tmp_path / "evaluation_manifest.json"
    llm_path = tmp_path / "llm_benchmark_report.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    llm_path.write_text(json.dumps(llm_report, ensure_ascii=False), encoding="utf-8")
    report_path = build_evaluation_report(output_dir=tmp_path, manifest_path=manifest_path, llm_report_path=llm_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert {row["condition"] for row in report["condition_summary"]} >= {
        "algolab_full",
        "direct_html_baseline",
        "no_process_validator",
        "no_scenegraph_compiler",
    }
    assert report["failure_type_summary"] == {
        "html_error": 1,
        "process_invariant": 1,
        "scene_error": 1,
    }
    assert {item["baseline"] for item in report["comparisons"]} >= {
        "direct_html_baseline",
        "no_process_validator_ablation",
        "no_scenegraph_compiler_ablation",
    }
    assert "direct_html_baseline" in (tmp_path / "evaluation_condition_summary.csv").read_text(encoding="utf-8")
    md = (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")
    assert "## Baseline And Ablation Summary" in md
    assert "no_scenegraph_compiler" in md


def test_reproducibility_package_records_environment_commands_samples_and_modes(tmp_path: Path):
    package = build_reproducibility_package()

    assert package["schema_version"] == "reproducibility-package-v1"
    assert package["environment"]["python"] == "/ssd1/liaokunpeng/agent-py310-cu/bin/python3"
    assert package["model_config"]["secret_policy"]
    assert "ALGOLAB_LLM_MODEL" in package["model_config"]["env_vars"]
    assert package["commands"]["deterministic_quality_check"] == (
        "bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py"
    )
    assert package["commands"]["browser_smoke_container"] == "bash scripts/run_browser_smoke_container.sh"
    assert package["commands"]["host_benchmark_regression"].endswith("-m tests.benchmark_regression")
    assert package["commands"]["llm_benchmark"].startswith(
        "/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py"
    )

    modes = package["benchmark_modes"]
    assert modes["deterministic"]["calls_llm"] is False
    assert modes["deterministic"]["source"] == "tests/benchmark_cases.py"
    assert modes["llm"]["calls_llm"] is True
    assert modes["llm"]["source"] == "scripts/run_llm_benchmark.py"
    assert modes["deterministic"]["output_paths"] != modes["llm"]["output_paths"]

    samples = package["sample_inputs"]
    assert len(samples) >= build_manifest()["summary"]["sample_count"]
    first = samples[0]
    assert {"case_id", "sample_index", "input_data", "expected", "suite", "output_paths"} <= set(first)
    assert first["output_paths"].get("artifact_json")
    assert first["output_paths"].get("html")

    written = write_reproducibility_package(tmp_path)
    assert written.name == "reproducibility_package.json"
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == package
    readme = tmp_path / "README.md"
    commands = tmp_path / "commands.sh"
    assert readme.exists()
    assert commands.exists()
    readme_text = readme.read_text(encoding="utf-8")
    commands_text = commands.read_text(encoding="utf-8")
    for token in ("确定性质量检查", "LLM benchmark", "deterministic benchmark", "输出路径"):
        assert token in readme_text
    assert "scripts/run_browser_smoke_container.sh" in commands_text
    assert "scripts/run_quality_checks.py" in commands_text
    assert "scripts/run_llm_benchmark.py" in commands_text


def test_v1_release_gate_report_records_release_requirements(tmp_path: Path):
    report = build_v1_release_gate_report()

    assert report["schema_version"] == "v1-release-gate-v1"
    assert report["overall_ready"] is True
    assert report["commands"]["quality_checks"] == (
        "bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py"
    )
    assert report["commands"]["browser_smoke"] == "bash scripts/run_browser_smoke_container.sh"
    deterministic = report["checks"]["deterministic_benchmark"]
    assert 80 <= deterministic["v1_gate_sample_count"] <= 230
    assert deterministic["benchmark_sample_count"] == sum(len(case.samples) for case in benchmark_cases())
    assert deterministic["v1_gate_sample_count"] == sum(
        len(case.samples) for case in benchmark_cases() if case.gate_layer in {"smoke", "family_core"}
    )
    assert deterministic["benchmark_sample_count"] >= deterministic["v1_gate_sample_count"]
    assert deterministic["v1_gate_layers"] == ["family_core", "smoke"]
    assert deterministic["status"] == "pass"

    golden = report["checks"]["golden_browser_smoke"]
    assert golden["status"] == "pass"
    assert {"unique_paths", "graph_bfs", "binary_search", "daily_temperatures"} <= set(golden["required_cases"])
    assert golden["covered_by"] == "scripts/run_browser_smoke_container.sh -> tests.browser_smoke.run_all"

    debug = report["checks"]["debug_drawer_evidence"]
    assert debug["status"] == "pass"
    for selector in ("#debug-validation-json", "#debug-release", "#debug-state", "#debug-artifact"):
        assert selector in debug["required_selectors"]

    evaluation = report["checks"]["evaluation_failure_types"]
    assert evaluation["status"] == "pass"
    assert evaluation["synthetic_failure_type_summary"] == {"process_invariant": 1, "scene_error": 1}
    assert "output/evaluation/evaluation_failure_types.csv" in evaluation["output_paths"]

    docs = report["checks"]["pinned_python_docs"]
    assert docs["status"] == "pass"
    assert docs["python"] == "/ssd1/liaokunpeng/agent-py310-cu/bin/python3"
    assert docs["disallowed_commands"] == []

    written = write_v1_release_gate_report(tmp_path)
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == report
    assert (tmp_path / "v1_release_gate.md").exists()
    assert "V1 Release Gate" in (tmp_path / "v1_release_gate.md").read_text(encoding="utf-8")


def test_family_capabilities_registry_covers_existing_benchmark_families(tmp_path: Path):
    from scripts.check_family_capabilities import (
        build_family_capabilities_report,
        load_family_capabilities,
        validate_family_capabilities,
        write_family_capabilities_report,
    )

    capabilities = load_family_capabilities()
    report = build_family_capabilities_report(capabilities)

    assert report["schema_version"] == "family-capabilities-report-v1"
    assert report["overall_ready"] is True
    assert report["benchmark_family_count"] == len({case.family for case in benchmark_cases()})
    assert report["registered_family_count"] >= report["benchmark_family_count"]
    assert report["missing_benchmark_families"] == []
    assert report["unknown_process_profiles"] == []

    raw_entries_by_label = {entry["label"]: entry for entry in capabilities["families"]}
    report_entries_by_label = {entry["label"]: entry for entry in report["families"]}
    for case in benchmark_cases():
        assert case.family in raw_entries_by_label, case.family
        raw_entry = raw_entries_by_label[case.family]
        entry = report_entries_by_label[case.family]
        assert raw_entry["process_profile"] == entry["process_profile"]
        assert entry["family_id"]
        assert entry["target_level"] in {"strong", "medium_plus", "medium", "basic", "planned"}
        assert entry["current_level"] in {"strong", "medium_plus", "medium", "basic", "planned"}
        assert entry["process_profile"] in report["known_process_profiles"]
        assert entry["process_status"] in {"strong", "fallback", "uncovered"}
        assert entry["core_subfamilies"]
        assert entry["visual_primitives"]
        assert entry["benchmark_target"]["min_cases"] >= 1
        if entry["process_status"] != "strong":
            assert entry["fallback_boundaries"]

    broken = dict(capabilities)
    broken["families"] = [entry for entry in capabilities["families"] if entry["label"] != benchmark_cases()[0].family]
    broken_report = validate_family_capabilities(broken, benchmark_cases())
    assert broken_report["overall_ready"] is False
    assert benchmark_cases()[0].family in broken_report["missing_benchmark_families"]

    written = write_family_capabilities_report(tmp_path)
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == report
    assert (tmp_path / "family_capabilities.md").exists()
    assert "Family Capabilities" in (tmp_path / "family_capabilities.md").read_text(encoding="utf-8")


def test_family_release_gate_reports_layered_family_readiness_and_strong_fallback_failures(tmp_path: Path):
    from scripts.check_family_capabilities import load_family_capabilities
    from scripts.check_family_release_gate import (
        build_family_release_gate_report,
        validate_family_release_gate,
        write_family_release_gate_report,
    )

    capabilities = load_family_capabilities()
    report = build_family_release_gate_report(capabilities)

    assert report["schema_version"] == "family-release-gate-v1"
    assert report["overall_ready"] is True
    assert report["v1_release_gate"]["schema_version"] == "v1-release-gate-v1"
    assert report["v1_release_gate"]["overall_ready"] is True
    assert report["summary"]["case_count"] == len(benchmark_cases())
    assert report["summary"]["sample_count"] == sum(len(case.samples) for case in benchmark_cases())

    rows_by_label = {row["label"]: row for row in report["families"]}
    assert rows_by_label["二分"]["current_level"] == "strong"
    assert rows_by_label["二分"]["answer"]["passed_samples"] == rows_by_label["二分"]["sample_count"]
    assert rows_by_label["二分"]["process"]["passed_samples"] == rows_by_label["二分"]["sample_count"]
    assert rows_by_label["二分"]["demo_readiness"]["ready_cases"] == rows_by_label["二分"]["case_count"]
    assert rows_by_label["二分"]["fallback"]["process_fallback_cases"] == 0
    assert rows_by_label["二分"]["fallback"]["process_uncovered_cases"] == 0

    sorting = rows_by_label["排序"]
    assert sorting["current_level"] == "medium_plus"
    assert sorting["fallback"]["process_uncovered_cases"] == 0
    assert sorting["process"]["passed_samples"] == sorting["sample_count"]
    assert sorting["status"] == "pass"
    assert sorting["warnings"] == []

    written = write_family_release_gate_report(tmp_path)
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == report
    md = (tmp_path / "family_release_gate.md").read_text(encoding="utf-8")
    assert "Family Release Gate" in md
    assert "medium_plus" in md

    broken = dict(capabilities)
    broken["families"] = [dict(entry) for entry in capabilities["families"]]
    broken["families"][0]["process_profile"] = "uncovered"
    broken_report = validate_family_release_gate(broken, benchmark_cases())
    assert broken_report["overall_ready"] is False
    broken_row = next(row for row in broken_report["families"] if row["label"] == broken["families"][0]["label"])
    assert broken_row["current_level"] == "strong"
    assert broken_row["fallback"]["process_uncovered_cases"] == broken_row["case_count"]
    assert broken_row["fallback"]["family_core_degradation_cases"] >= 1
    assert broken_report["summary"]["degradation_summary"]["process_uncovered"]["cases"] >= broken_row["case_count"]
    assert any("strong family" in error for error in broken_row["errors"])


def test_phase16_degradation_policy_enters_evaluation_reports_and_artifact_debug(tmp_path: Path):
    from algolab.pipeline import _try_materialize
    from scripts.check_family_capabilities import load_family_capabilities
    from scripts.check_family_release_gate import validate_family_release_gate

    assert classify_failure("failure_type=demo_warn: 教学字段不足但可降级演示") == "demo_warn"

    llm_report = {
        "kind": "llm_benchmark_report",
        "config": {"model": "demo-model", "benchmark_condition": "algolab_full"},
        "results": [
            {
                "case_id": "answer_only_case",
                "family": "合成",
                "ok": False,
                "degradations": [{"type": "answer_only", "reason": "只有 expected/verifier 证据"}],
            },
            {
                "case_id": "schema_scene_case",
                "family": "合成",
                "ok": False,
                "release_gate": {"trace_ready": True, "visual_ready": True, "process_ready": False},
            },
            {
                "case_id": "fallback_case",
                "family": "合成",
                "ok": False,
                "errors": ["failure_type=process_fallback: 只有基础过程证据"],
            },
            {
                "case_id": "demo_warn_case",
                "family": "合成",
                "ok": True,
                "warnings": ["failure_type=demo_missing_reason: step 2 缺少 reason"],
            },
        ],
    }
    capabilities = load_family_capabilities()
    broken = dict(capabilities)
    broken["families"] = [dict(entry) for entry in capabilities["families"]]
    broken["families"][0]["process_profile"] = "uncovered"
    family_gate = validate_family_release_gate(broken, benchmark_cases())

    summary = degradation_summary(llm_report, family_gate)
    assert summary["by_source"]["llm_report"]["answer_only"] == 1
    assert summary["by_source"]["llm_report"]["schema_scene_only"] == 1
    assert summary["by_source"]["llm_report"]["process_fallback"] == 1
    assert summary["by_source"]["llm_report"]["demo_warn"] == 1
    assert summary["by_source"]["family_release_gate"]["process_uncovered"] >= 1

    manifest_path = tmp_path / "evaluation_manifest.json"
    llm_path = tmp_path / "llm_benchmark_report.json"
    family_gate_path = tmp_path / "family_release_gate.json"
    manifest_path.write_text(json.dumps(build_manifest(), ensure_ascii=False), encoding="utf-8")
    llm_path.write_text(json.dumps(llm_report, ensure_ascii=False), encoding="utf-8")
    family_gate_path.write_text(json.dumps(family_gate, ensure_ascii=False), encoding="utf-8")

    report_path = build_evaluation_report(
        output_dir=tmp_path,
        manifest_path=manifest_path,
        llm_report_path=llm_path,
        family_gate_path=family_gate_path,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["degradation_summary"]["total"]["answer_only"] == 1
    assert report["degradation_summary"]["total"]["process_uncovered"] >= 1
    assert "schema_scene_only" in (tmp_path / "evaluation_degradations.csv").read_text(encoding="utf-8")
    assert "## Degradation Summary" in (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")

    trace_literal = {
        "schema_version": "semantic-trace-v1",
        "algorithm": "未注册教学算法",
        "input_data": {"x": 1},
        "result": 1,
        "events": [
            {
                "step": 0,
                "op": "create",
                "targets": [{"id": "answer"}],
                "state": {"answer": 1},
                "reason": "初始化答案。",
                "code_line": 1,
            },
            {
                "step": 1,
                "op": "mark",
                "targets": [{"id": "answer"}],
                "value": 1,
                "state": {"answer": 1},
                "role": "answer",
                "reason": "返回答案。",
                "code_line": 2,
            },
        ],
    }
    spec = {
        "problem_title": "未注册教学算法",
        "input_contract": "读取 x。",
        "variants": [
            {
                "id": "uncovered",
                "name": "未覆盖解法",
                "strategy": "返回 1。",
                "time_complexity": "O(1)",
                "space_complexity": "O(1)",
                "code": "def solve(input_data):\n    return 1",
                "tracker_code": f"def trace(input_data):\n    return {trace_literal!r}",
            }
        ],
    }
    artifact, errors = _try_materialize(ProblemInput(problem="未注册教学算法", input_data={"x": 1}, expected_result=1), spec)
    assert errors == []
    assert artifact.validation.release_gate.release_ready
    assert [item.type for item in artifact.validation.degradations] == ["process_uncovered"]

    html = save_html(artifact, tmp_path / "degradation_debug.html").read_text(encoding="utf-8")
    assert "Degradation policy" in html
    assert "process_uncovered" in html


def test_phase16_core_family_sample_window_and_gates_are_ready():
    from scripts.check_family_capabilities import load_family_capabilities
    from scripts.check_family_release_gate import build_family_release_gate_report

    report = build_family_release_gate_report(load_family_capabilities())
    summary = report["summary"]
    core_samples = summary["gate_layer_samples"].get("family_core", 0)

    assert report["overall_ready"] is True
    assert 160 <= core_samples <= 220
    assert summary["gate_layers"]["family_core"] >= 60
    assert summary["gate_layer_samples"]["family_core"] == core_samples
    assert summary["answer_pass_rate"] == 1.0
    assert summary["process_pass_rate"] == 1.0
    assert summary["demo_readiness_pass_rate"] == 1.0

    p16_family_ids = {
        "dp_1d",
        "dp_2d",
        "dp_core",
        "binary_search",
        "array_pointer",
        "basic_graph",
        "string_advanced",
        "tree_bst_lca",
        "tree_dp",
        "monotonic_stack",
        "union_find",
        "range_structure",
    }
    rows_by_family_id = {row["family_id"]: row for row in report["families"]}
    assert p16_family_ids <= set(rows_by_family_id)

    for family_id in p16_family_ids:
        row = rows_by_family_id[family_id]
        assert row["case_count"] >= 1, family_id
        assert row["sample_count"] >= 2, family_id
        assert row["gate_layers"] == {"family_core": row["case_count"]}, family_id
        assert row["gate_layer_samples"] == {"family_core": row["sample_count"]}, family_id
        assert row["answer"]["passed_samples"] == row["sample_count"], family_id
        assert row["process"]["passed_samples"] == row["sample_count"], family_id
        assert row["demo_readiness"]["ready_cases"] == row["demo_readiness"]["required_cases"], family_id
        if row["current_level"] == "strong":
            assert row["process"]["pass_rate"] == 1.0, family_id
            assert row["fallback"]["process_fallback_cases"] == 0, family_id
            assert row["fallback"]["process_uncovered_cases"] == 0, family_id


def test_phase16_expansion_family_samples_and_dashboard_pages_are_ready(tmp_path: Path):
    from scripts.check_family_capabilities import load_family_capabilities
    from scripts.check_family_release_gate import build_family_release_gate_report

    expansion_family_ids = {
        "greedy",
        "shortest_path_mst",
        "heap_topk_huffman",
        "trie",
        "backtracking_recursion",
        "math_bit",
        "geometry_sweep",
        "linked_list_cache",
        "advanced_graph",
    }
    expansion_cases = [case for case in benchmark_cases() if case.gate_layer == "expansion"]
    report = build_family_release_gate_report(load_family_capabilities())
    summary = report["summary"]
    rows_by_family_id = {row["family_id"]: row for row in report["families"]}

    assert report["overall_ready"] is True
    assert 250 <= summary["sample_count"] <= 350
    assert summary["gate_layers"]["expansion"] == len(expansion_cases)
    assert summary["gate_layer_samples"]["expansion"] == sum(len(case.samples) for case in expansion_cases)
    assert summary["process_uncovered_cases"] == 0
    assert {case.family_id for case in expansion_cases} == expansion_family_ids
    assert all(case.process_profile != "uncovered" for case in expansion_cases)

    for family_id in expansion_family_ids:
        row = rows_by_family_id[family_id]
        assert row["gate_layers"].get("expansion", 0) >= 1, family_id
        assert row["gate_layer_samples"].get("expansion", 0) >= 4, family_id
        assert row["answer"]["passed_samples"] == row["sample_count"], family_id
        assert row["process"]["passed_samples"] == row["sample_count"], family_id
        assert row["demo_readiness"]["ready_cases"] == row["demo_readiness"]["required_cases"], family_id
        assert row["fallback"]["process_uncovered_cases"] == 0, family_id
        assert row["fallback"]["process_uncovered_samples"] == 0, family_id

    index = build_dashboard(
        tmp_path / "expansion_dashboard",
        demo_ids=[case.id for case in expansion_cases],
        style="stable",
    )
    dashboard = json.loads(index.with_name("dashboard.json").read_text(encoding="utf-8"))
    assert dashboard["total"] == len(expansion_cases)
    assert dashboard["failed"] == 0
    assert {demo["family_id"] for demo in dashboard["demos"]} == expansion_family_ids
    assert all(demo["gate_layer"] == "expansion" for demo in dashboard["demos"])
    assert all(demo["stable_html"].endswith("stable.html") for demo in dashboard["demos"])
    coverage = {(row["family_id"], row["gate_layer"]): row for row in dashboard["family_coverage"]}
    for family_id in expansion_family_ids:
        assert (family_id, "expansion") in coverage
        assert coverage[(family_id, "expansion")]["html_links"] >= 1


def test_property_benchmark_generates_seeded_robustness_report(tmp_path: Path):
    from tests.property_cases import DEFAULT_PROPERTY_SEED, property_cases
    from scripts.run_property_benchmark import build_property_benchmark_report, write_property_benchmark_report

    cases = property_cases()
    subfamilies = {case.subfamily_id for case in cases}
    assert {
        "house_robber",
        "subset_sum",
        "lcs",
        "edit_distance",
        "knapsack_01",
        "bfs_layers",
        "dfs_connected",
        "topological_sort",
        "dijkstra_positive",
        "kmp",
        "z_algorithm",
        "manacher",
        "insertion_sort",
        "merge_sort",
        "quickselect",
        "union_find_connectivity",
        "range_sum_update",
    } <= subfamilies

    report_a = build_property_benchmark_report(seed=DEFAULT_PROPERTY_SEED, sample_count=3)
    report_b = build_property_benchmark_report(seed=DEFAULT_PROPERTY_SEED, sample_count=3)
    assert report_a == report_b
    assert report_a["schema_version"] == "property-benchmark-v1"
    assert report_a["release_gate_included"] is False
    assert report_a["summary"]["seed"] == DEFAULT_PROPERTY_SEED
    assert report_a["summary"]["total"] == len(cases) * 3
    assert report_a["summary"]["failed"] == 0
    assert report_a["summary"]["passed"] == report_a["summary"]["total"]
    assert set(report_a["summary"]["families"]) >= {
        "dynamic_programming",
        "basic_graph",
        "string_matching",
        "sorting",
        "union_find",
        "range_structure",
    }
    for family_id, row in report_a["summary"]["family_robustness"].items():
        assert row["total"] > 0, family_id
        assert row["passed"] == row["total"], family_id
        assert row["failed"] == 0, family_id
        assert row["pass_rate"] == 1.0, family_id

    for result in report_a["results"]:
        assert {
            "family",
            "family_id",
            "subfamily",
            "subfamily_id",
            "input",
            "expected",
            "actual",
            "ok",
            "failure_type",
        } <= set(result), result

    json_path = write_property_benchmark_report(tmp_path, seed=DEFAULT_PROPERTY_SEED, sample_count=2)
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded == build_property_benchmark_report(seed=DEFAULT_PROPERTY_SEED, sample_count=2)
    md = (tmp_path / "property_benchmark_report.md").read_text(encoding="utf-8")
    assert "Property Benchmark" in md
    assert "not included in V1 release gate" in md


def test_boundary_case_registry_reports_family_core_coverage_and_strong_upgrade_gate(tmp_path: Path):
    from scripts.check_boundary_cases import (
        BOUNDARY_CATEGORIES,
        build_boundary_case_report,
        load_boundary_cases,
        validate_boundary_cases,
        write_boundary_case_report,
    )

    registry = load_boundary_cases()
    report = build_boundary_case_report(registry)
    family_core_cases = [case for case in benchmark_cases() if case.gate_layer == "family_core"]
    strong_core_cases = [case for case in family_core_cases if case.support_level == "strong"]

    assert registry["schema_version"] == "boundary-cases-v1"
    assert set(BOUNDARY_CATEGORIES) == {"empty", "single", "duplicate", "zero_or_negative", "extreme", "no_solution", "multiple_solutions"}
    assert report["schema_version"] == "boundary-case-report-v1"
    assert report["summary"]["family_core_case_count"] == len(family_core_cases)
    assert report["summary"]["strong_family_core_case_count"] == len(strong_core_cases)
    assert report["summary"]["missing_family_core_cases"] == []
    assert report["summary"]["strong_upgrade_blocked_cases"] == []
    assert report["summary"]["overall_ready"] is True
    assert report["summary"]["strong_upgrade_ready"] is True

    rows_by_case = {row["case_id"]: row for row in report["cases"]}
    for case in family_core_cases:
        row = rows_by_case[case.id]
        assert row["gate_layer"] == "family_core", case.id
        assert row["covered_categories"] or row["not_applicable_categories"], case.id
        assert set(row["covered_categories"]) | set(row["not_applicable_categories"]) == set(BOUNDARY_CATEGORIES), case.id
        assert row["missing_categories"] == [], case.id
        assert row["status"] == "pass", case.id
        for item in row["not_applicable"]:
            assert item["reason"], (case.id, item)

    for family_id, row in report["families"].items():
        assert row["case_count"] > 0, family_id
        assert row["boundary_counts"], family_id
        assert row["missing_case_count"] == 0, family_id

    written = write_boundary_case_report(tmp_path)
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == report
    md = (tmp_path / "boundary_cases.md").read_text(encoding="utf-8")
    assert "Boundary Cases" in md
    assert "strong_upgrade_ready" in md

    broken = dict(registry)
    broken["cases"] = [dict(item) for item in registry["cases"]]
    broken["cases"][0] = dict(broken["cases"][0])
    broken["cases"][0]["coverage"] = []
    broken["cases"][0]["not_applicable"] = []
    broken_report = validate_boundary_cases(broken, benchmark_cases())
    assert broken_report["summary"]["overall_ready"] is False
    if rows_by_case[broken["cases"][0]["case_id"]]["support_level"] == "strong":
        assert broken_report["summary"]["strong_upgrade_ready"] is False
        assert broken_report["summary"]["strong_upgrade_blocked_cases"]
    assert broken_report["summary"]["missing_boundary_cases"]


__all__ = [name for name in globals() if name.startswith("test_")]
