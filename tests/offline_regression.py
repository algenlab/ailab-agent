"""Offline regression suite.

This test suite does not call the LLM. It validates the stable architecture:
schema -> validator -> scene compiler -> renderer -> sandbox.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from algolab.compiler.scene_compiler import compile_scene
from app import benchmark_preset_choices, load_benchmark_preset
import algolab.generation.solution_generator as solution_generator
from algolab.generation.solution_generator import (
    build_contract_with_repair,
    normalize_contract_spec,
    normalize_visual_plan_spec,
)
from algolab.renderer.layout_registry import LAYOUT_RENDERERS
from algolab.renderer.capabilities import runtime_capabilities
from algolab.pipeline import _try_materialize
from algolab.renderer.export import save_html
from algolab.runtime.sandbox import SandboxError, run_function
from algolab.runtime.executor import execute_variant
from algolab.schemas.correctness import CorrectnessContract, OracleStrategy
from algolab.schemas.render_report import RenderReport
from algolab.schemas.semantic_trace import SemanticTrace, TeachingStep
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.schemas.input import ProblemInput
from algolab.schemas.scene_graph import SceneGraph
from algolab.schemas.validation import BuildArtifact
from algolab.schemas.visual_plan import RenderTarget, VisualPlan
from algolab.verification.scene_validator import validate_scene
from algolab.verification.contract_validator import validate_contract
from algolab.verification.process_validator import validate_process
from algolab.verification.trace_validator import validate_trace
from algolab.verification.visual_plan_validator import validate_visual_plan
from tests.fixtures import (
    algorithm_subfamily_traces,
    algorithm_family_traces,
    bfs_trace,
    fixture_artifact,
    geometry_trace,
    heap_trace,
    house_robber_trace,
    recursion_trace,
    string_trace,
    tree_trace,
    trie_trace,
    union_find_trace,
)
from tests.benchmark_cases import benchmark_cases


def _two_sum_contract_payload() -> dict:
    return {
        "schema_version": "correctness-contract-v1",
        "input_schema": {"nums": "int[]", "target": "int"},
        "output_schema": "int[2] | []",
        "preconditions": ["nums contains integers"],
        "postconditions": [
            "if output is [i,j], then 0 <= i < j < len(nums)",
            "if output is [i,j], then nums[i] + nums[j] == target",
            "if output is [], no valid pair exists",
        ],
        "oracle_strategy": "brute_force",
        "oracle_code": (
            "def brute_force(input_data):\n"
            "    nums = input_data['nums']\n"
            "    target = input_data['target']\n"
            "    for i in range(len(nums)):\n"
            "        for j in range(i + 1, len(nums)):\n"
            "            if nums[i] + nums[j] == target:\n"
            "                return [i, j]\n"
            "    return []\n"
        ),
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
        ],
        "metamorphic_relations": [
            "appending a number that cannot participate keeps an existing answer valid",
        ],
        "process_invariants": ["seen only contains values from previous indices"],
    }


def test_correctness_contract_accepts_minimal_two_sum():
    contract = CorrectnessContract.model_validate(_two_sum_contract_payload())
    assert contract.schema_version == "correctness-contract-v1"
    assert contract.input_schema.root == {"nums": "int[]", "target": "int"}
    assert contract.output_schema.root == "int[2] | []"
    assert contract.oracle_strategy == OracleStrategy.BRUTE_FORCE
    assert contract.test_cases[0].input == {"nums": [2, 7, 11, 15], "target": 9}
    assert contract.postconditions[0].expression.startswith("if output")


def test_correctness_contract_rejects_invalid_contract():
    bad_version = _two_sum_contract_payload()
    bad_version["schema_version"] = "correctness-contract-v0"
    try:
        CorrectnessContract.model_validate(bad_version)
    except ValidationError:
        pass
    else:
        raise AssertionError("CorrectnessContract should reject an unknown schema_version")

    empty_output = _two_sum_contract_payload()
    empty_output["output_schema"] = ""
    try:
        CorrectnessContract.model_validate(empty_output)
    except ValidationError:
        pass
    else:
        raise AssertionError("CorrectnessContract should reject an empty output_schema")

    no_postconditions = _two_sum_contract_payload()
    no_postconditions["postconditions"] = []
    try:
        CorrectnessContract.model_validate(no_postconditions)
    except ValidationError:
        pass
    else:
        raise AssertionError("CorrectnessContract should reject missing postconditions")


def test_visual_plan_accepts_2d_3d_hybrid_and_rejects_invalid_target():
    for target in ("teaching_2d", "spatial_3d", "hybrid_2_5d", "creative"):
        plan = VisualPlan.model_validate(
            {
                "schema_version": "visual-plan-v1",
                "mode": "hybrid" if target == "hybrid_2_5d" else "teaching",
                "stage": target,
                "camera": {
                    "type": "orbit" if target == "spatial_3d" else "fixed",
                    "default_view": "isometric" if target == "spatial_3d" else "top_down",
                    "focus_policy": "current_target",
                },
                "animation": {
                    "pace": "medium",
                    "transition": "smooth",
                    "emphasize": ["current", "dependency"],
                },
                "teaching": {
                    "level": "beginner",
                    "show_invariant": True,
                    "quiz_density": "medium",
                },
                "layout_preferences": {"graph": "layered_depth"},
                "baseline_target": "teaching_2d",
            }
        )
        assert plan.stage == RenderTarget(target)
        assert plan.baseline_target == RenderTarget.TEACHING_2D

    try:
        VisualPlan.model_validate({"schema_version": "visual-plan-v1", "stage": "concept_video"})
    except ValidationError:
        pass
    else:
        raise AssertionError("VisualPlan should reject an unsupported render target")


def test_visual_plan_prompt_and_validator_use_capabilities():
    prompt = Path("algolab/generation/prompts/visual_plan_system.txt").read_text(encoding="utf-8")
    assert "只能输出 JSON" in prompt
    assert "visual-plan-v1" in prompt
    assert "capabilities.render_targets" in prompt
    assert "不要输出 HTML" in prompt
    assert "不能改变算法结果" in prompt

    plan = normalize_visual_plan_spec(
        {
            "schema_version": "visual-plan-v1",
            "mode": "teaching",
            "stage": "spatial_3d",
            "camera": {"type": "orbit", "default_view": "isometric", "focus_policy": "current_target"},
            "animation": {"pace": "medium", "transition": "smooth", "emphasize": ["current"]},
            "teaching": {"level": "beginner", "show_invariant": True, "quiz_density": "low"},
            "layout_preferences": {"graph": "layered_depth"},
            "baseline_target": "teaching_2d",
        }
    )
    validated, report = validate_visual_plan(plan, runtime_capabilities())
    assert validated.stage == RenderTarget.SPATIAL_3D
    assert report["requested_target"] == "spatial_3d"
    assert report["actual_target"] == "spatial_3d"
    assert report["used_baseline_renderer"] is False

    try:
        normalize_visual_plan_spec({"schema_version": "visual-plan-v1", "stage": "concept_video"})
    except ValidationError:
        pass
    else:
        raise AssertionError("invalid VisualPlan stage should be rejected")

    cleaned, report = validate_visual_plan(
        {
            "schema_version": "visual-plan-v1",
            "stage": "teaching_2d",
            "layout_preferences": {"unknown_layout": "x", "array": "array"},
        },
        runtime_capabilities(),
    )
    assert "unknown_layout" not in cleaned.layout_preferences.root
    assert report["warnings"]


def test_app_benchmark_presets_cover_documented_benchmark_samples():
    choices = benchmark_preset_choices()
    cases = benchmark_cases()
    expected_count = sum(len(case.samples) for case in cases)

    assert len(choices) == expected_count
    for case in cases:
        assert any(f"({case.id})" in choice for choice in choices), case.id

    first = choices[0]
    problem, input_json, strategy, expected_json, user_code, solutions = load_benchmark_preset(first)
    first_case = cases[0]
    first_sample = first_case.samples[0]

    assert problem == first_case.problem
    assert json.loads(input_json) == first_sample.input_data
    assert strategy == first_case.strategy
    assert json.loads(expected_json) == first_sample.expected
    assert user_code == ""
    assert solutions == 1


def test_layout_registry_declares_phase6_components():
    expected = {
        "array": "array",
        "matrix": "matrix",
        "graph": "graph",
        "queue": "queue",
        "stack": "stack",
        "map": "map",
        "tree": "tree",
        "recursion_tree": "tree",
        "heap": "heap",
        "trie": "tree",
        "union_find": "tree",
        "string": "string",
        "geometry": "geometry",
        "generic": "map",
    }
    for layout, renderer in expected.items():
        assert LAYOUT_RENDERERS.get(layout) == renderer


def test_teaching_schema_compiles_explicit_fields_and_reason_fallback(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "教学字段测试",
            "input_data": {"nums": [1, 2]},
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [1, 2]},
                    "reason": "创建输入数组。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "set",
                    "targets": [{"id": "answer"}],
                    "deps": [{"id": "nums[0]"}, {"id": "nums[1]"}],
                    "state": {"nums": [1, 2], "answer": 3},
                    "reason": "合并两个数。",
                    "code_line": 2,
                    "teaching": {
                        "what": "写入 answer",
                        "why": "两个元素都已经读到。",
                        "formula": "answer = nums[0] + nums[1]",
                        "invariant": "answer 等于已处理元素之和。",
                        "common_mistake": "不要漏掉第二个元素。",
                        "hint": "先看 deps。",
                    },
                },
            ],
        }
    )

    scene = compile_scene(trace)

    fallback = scene.frames[0].teaching
    explicit = scene.frames[1].teaching
    evidence = scene.frames[1].evidence
    assert fallback is not None
    assert fallback["what"].startswith("初始化结构")
    assert fallback["why"] == "创建输入数组。"
    assert fallback["hint"] == "关注 nums"
    assert explicit == {
        "what": "写入 answer",
        "why": "两个元素都已经读到。",
        "formula": "answer = nums[0] + nums[1]",
        "invariant": "answer 等于已处理元素之和。",
        "common_mistake": "不要漏掉第二个元素。",
        "hint": "先看 deps。",
    }
    assert evidence["operation"] == "set"
    assert evidence["targets"] == ["answer"]
    assert evidence["deps"] == ["nums[0]", "nums[1]"]
    assert evidence["reason"] == "合并两个数。"

    artifact = fixture_artifact().model_copy(deep=True)
    first_scene_id = artifact.variants[0].id
    artifact.scenes[first_scene_id] = scene
    out = save_html(artifact, tmp_path / "teaching.html")
    html = out.read_text(encoding="utf-8")
    assert 'id="teaching"' in html
    assert "function renderTeaching" in html
    assert "common_mistake" in html


def test_stable_renderer_exposes_correctness_and_step_evidence(tmp_path: Path):
    artifact = fixture_artifact().model_copy(deep=True)
    artifact.correctness_contract = CorrectnessContract.model_validate(_two_sum_contract_payload())
    artifact.validation.checks.extend(
        [
            "独立 verifier 执行通过",
            "动态规划：solve/trace/process/scene 均通过",
            "contract tests：1/1 passed",
        ]
    )
    artifact.validation.contract_test_results = [
        {
            "case_index": 0,
            "variant_id": "dp",
            "ok": True,
            "input": {"nums": [2, 7, 11, 15], "target": 9},
            "expected": [0, 1],
            "oracle_result": [0, 1],
            "solve_result": [0, 1],
            "error": "",
        }
    ]

    out = save_html(artifact, tmp_path / "stable_evidence.html")
    html = out.read_text(encoding="utf-8")

    assert 'id="evidence"' in html
    assert 'id="step-evidence"' in html
    assert "function renderEvidence" in html
    assert "function renderStepEvidence" in html
    assert "function stateDiff" in html
    assert "CorrectnessContract" in html
    assert "Contract tests" in html
    assert "目标写入核对" in html
    assert "seen only contains values from previous indices" in html


def test_scene_compiler_hides_internal_trace_meta_from_rendered_state(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "内部字段过滤",
            "input_data": {"x": 1},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "answer"}],
                    "state": {
                        "answer": 1,
                        "_trace_meta": {
                            "policy": "full",
                            "max_events": 80,
                            "raw_event_count": 1,
                            "emitted_event_count": 1,
                            "sampled": False,
                            "expected_updates": {"answer": 1},
                            "recorded_updates": {"answer": 1},
                            "coverage": {"answer": 1.0},
                        },
                    },
                    "value": 1,
                    "reason": "记录答案。",
                    "code_line": 1,
                }
            ],
        }
    )
    scene = compile_scene(trace)

    assert "_trace_meta" in trace.events[-1].state
    assert "_trace_meta" not in scene.frames[-1].state

    artifact = fixture_artifact().model_copy(deep=True)
    artifact.variants[0].id = "internal_state"
    artifact.variants[0].trace = trace
    artifact.scenes = {"internal_state": scene}
    out = save_html(artifact, tmp_path / "internal_state.html")
    html = out.read_text(encoding="utf-8")
    artifact_json = out.with_suffix(".json").read_text(encoding="utf-8")

    assert "_trace_meta" not in html
    assert "coverage" not in html
    assert "_trace_meta" in artifact_json


def test_teaching_schema_rejects_unknown_fields():
    try:
        TeachingStep.model_validate({"what": "做一步", "unknown": "x"})
    except ValidationError:
        pass
    else:
        raise AssertionError("TeachingStep should reject unknown fields")


def test_build_artifact_accepts_old_payload_without_new_optional_fields():
    payload = fixture_artifact().model_dump()
    payload.pop("correctness_contract", None)
    payload.pop("visual_plan", None)
    payload.pop("render_report", None)

    restored = BuildArtifact.model_validate(payload)

    assert restored.correctness_contract is None
    assert restored.visual_plan is None
    assert restored.render_report is None
    assert restored.validation.release_gate.release_ready


def test_build_artifact_dumps_optional_contract_visual_plan_and_render_report():
    payload = fixture_artifact().model_dump()
    payload["correctness_contract"] = _two_sum_contract_payload()
    payload["visual_plan"] = {
        "schema_version": "visual-plan-v1",
        "mode": "hybrid",
        "stage": "spatial_3d",
        "metaphor": "BFS wavefront",
        "camera": {"type": "orbit", "default_view": "isometric", "focus_policy": "current_target"},
        "animation": {"pace": "medium", "transition": "smooth", "emphasize": ["current", "answer"]},
        "teaching": {"level": "interview", "show_invariant": True, "quiz_density": "low"},
        "layout_preferences": {"graph": "layered_depth", "queue": "dock_bottom"},
        "baseline_target": "teaching_2d",
    }
    payload["render_report"] = {
        "requested_target": "spatial_3d",
        "actual_target": "teaching_2d",
        "fallback_reasons": ["spatial runtime unavailable"],
    }

    artifact = BuildArtifact.model_validate(payload)
    dumped = artifact.model_dump_json()
    restored = BuildArtifact.model_validate_json(dumped)

    assert restored.correctness_contract is not None
    assert restored.correctness_contract.oracle_strategy == OracleStrategy.BRUTE_FORCE
    assert restored.visual_plan is not None
    assert restored.visual_plan.stage == RenderTarget.SPATIAL_3D
    assert restored.render_report is not None
    assert restored.render_report.actual_target == RenderTarget.TEACHING_2D


def test_render_report_schema_records_target_fallback_and_browser_smoke():
    report = RenderReport.model_validate(
        {
            "schema_version": "render-report-v1",
            "requested_target": "spatial_3d",
            "actual_target": "teaching_2d",
            "baseline_target": "teaching_2d",
            "used_baseline_renderer": True,
            "fallback_reasons": ["spatial runtime is planned"],
            "browser_smoke": {
                "checked": True,
                "passed": False,
                "reason": "canvas target unavailable",
            },
            "release_ready": True,
        }
    )
    assert report.requested_target == RenderTarget.SPATIAL_3D
    assert report.actual_target == RenderTarget.TEACHING_2D
    assert report.baseline_target == RenderTarget.TEACHING_2D
    assert report.used_baseline_renderer is True
    assert report.fallback_reasons == ["spatial runtime is planned"]
    assert report.browser_smoke.checked is True
    assert report.browser_smoke.passed is False


def test_contract_validator_rejects_bad_schema_and_expected_mismatch():
    request = ProblemInput(
        problem="Two Sum",
        input_data={"nums": [2, 7, 11, 15], "target": 9},
        expected_result=[0, 1],
    )
    bad = _two_sum_contract_payload()
    bad["schema_version"] = "bad-version"
    report = validate_contract(bad, request)
    assert report.errors
    assert not report.release_gate.schema_ready
    assert not report.release_gate.contract_ready

    mismatch = _two_sum_contract_payload()
    mismatch["test_cases"][0]["expected"] = [1, 2]
    report = validate_contract(mismatch, request)
    assert any("expected_result" in error for error in report.errors), report
    assert report.release_gate.schema_ready
    assert not report.release_gate.expected_consistent
    assert not report.release_gate.contract_ready


def test_contract_validator_accepts_expected_only_partial_contract():
    request = ProblemInput(
        problem="Two Sum",
        input_data={"nums": [2, 7, 11, 15], "target": 9},
        expected_result=[0, 1],
    )
    payload = _two_sum_contract_payload()
    payload["oracle_strategy"] = "none"
    payload["oracle_code"] = ""

    report = validate_contract(payload, request)

    assert report.errors == []
    assert report.release_gate.schema_ready
    assert not report.release_gate.oracle_ready
    assert report.release_gate.expected_consistent
    assert report.release_gate.generated_tests_pass
    assert report.release_gate.contract_ready
    assert any("部分校验" in warning for warning in report.warnings), report.warnings


def test_contract_validator_rejects_unusable_test_cases():
    request = ProblemInput(problem="Two Sum", input_data={"nums": [2], "target": 3}, expected_result=[])
    payload = _two_sum_contract_payload()
    payload["test_cases"][0]["input"] = {"nums": [2]}

    report = validate_contract(payload, request)

    assert any("缺少字段" in error for error in report.errors), report.errors
    assert not report.release_gate.generated_tests_pass
    assert not report.release_gate.contract_ready


def test_contract_validator_executes_two_sum_brute_force_oracle():
    request = ProblemInput(
        problem="Two Sum",
        input_data={"nums": [3, 2, 4], "target": 6},
        expected_result=[1, 2],
    )
    payload = _two_sum_contract_payload()
    payload["test_cases"].append({"input": request.input_data, "expected": request.expected_result})

    report = validate_contract(payload, request)

    assert report.errors == []
    assert report.release_gate.oracle_ready
    assert report.release_gate.contract_ready
    assert any("oracle 执行通过" in check for check in report.checks), report.checks


def test_contract_validator_executes_daily_temperatures_brute_force_oracle():
    request = ProblemInput(
        problem="Daily Temperatures",
        input_data={"temperatures": [73, 74, 75, 71, 69, 72, 76, 73]},
        expected_result=[1, 1, 4, 2, 1, 1, 0, 0],
    )
    payload = {
        "schema_version": "correctness-contract-v1",
        "input_schema": {"temperatures": "int[]"},
        "output_schema": "int[]",
        "postconditions": ["answer[i] is the wait until a warmer day, or 0 if none exists"],
        "oracle_strategy": "brute_force",
        "oracle_code": (
            "def brute_force(input_data):\n"
            "    temperatures = input_data['temperatures']\n"
            "    ans = []\n"
            "    for i, temp in enumerate(temperatures):\n"
            "        wait = 0\n"
            "        for j in range(i + 1, len(temperatures)):\n"
            "            if temperatures[j] > temp:\n"
            "                wait = j - i\n"
            "                break\n"
            "        ans.append(wait)\n"
            "    return ans\n"
        ),
        "test_cases": [{"input": request.input_data, "expected": request.expected_result}],
    }

    report = validate_contract(payload, request)

    assert report.errors == []
    assert report.release_gate.oracle_ready
    assert report.release_gate.contract_ready


def test_contract_validator_supports_expected_user_and_generated_oracles():
    request = ProblemInput(problem="identity", input_data={"x": 7}, expected_result=7)
    base = {
        "schema_version": "correctness-contract-v1",
        "input_schema": {"x": "int"},
        "output_schema": "int",
        "postconditions": ["return x"],
        "test_cases": [{"input": {"x": 7}, "expected": 7}],
    }

    expected_only = {**base, "oracle_strategy": "expected_only"}
    report = validate_contract(expected_only, request)
    assert report.errors == []
    assert report.release_gate.oracle_ready

    user_provided = {
        **base,
        "oracle_strategy": "user_provided",
        "oracle_code": "def oracle(input_data):\n    return input_data['x']",
    }
    report = validate_contract(user_provided, request)
    assert report.errors == []
    assert report.release_gate.oracle_ready

    generated = {
        **base,
        "oracle_strategy": "generated_verifier",
        "oracle_code": "def verify(input_data):\n    return input_data['x']",
    }
    report = validate_contract(generated, request)
    assert report.errors == []
    assert report.release_gate.oracle_ready


def test_contract_validator_blocks_oracle_expected_mismatch_and_timeout():
    request = ProblemInput(problem="Two Sum", input_data={"nums": [2, 7], "target": 9}, expected_result=[0, 1])
    mismatch = _two_sum_contract_payload()
    mismatch["oracle_code"] = "def brute_force(input_data):\n    return []"
    report = validate_contract(mismatch, request)
    assert any("oracle result" in error for error in report.errors), report.errors
    assert not report.release_gate.oracle_ready
    assert not report.release_gate.contract_ready

    timeout = _two_sum_contract_payload()
    timeout["oracle_code"] = "def brute_force(input_data):\n    while True:\n        pass"
    report = validate_contract(timeout, request, oracle_timeout_s=1)
    assert any("超时" in error for error in report.errors), report.errors
    assert not report.release_gate.oracle_ready
    assert not report.release_gate.contract_ready


def test_contract_prompt_states_json_expected_and_verifier_boundaries():
    prompt = Path("algolab/generation/prompts/contract_system.txt").read_text(encoding="utf-8")
    assert "只能输出 JSON" in prompt
    assert "schema_version" in prompt
    assert "input_schema" in prompt
    assert "postconditions" in prompt
    assert "oracle_strategy" in prompt
    assert "test_cases" in prompt
    assert "expected 优先" in prompt
    assert "不是形式化证明" in prompt
    assert "HTML" in prompt and "Three.js" in prompt


def test_tracker_prompt_requires_tracer_api():
    prompt = Path("algolab/generation/prompts/tracker_system.txt").read_text(encoding="utf-8")
    assert "Tracer" in prompt
    assert "tracer.set" in prompt
    assert "不要直接手写 events.append" in prompt


def test_repair_prompt_converts_sparse_trace_to_tracer_api():
    prompt = Path("algolab/generation/prompts/repair_system.txt").read_text(encoding="utf-8")
    assert "Tracer API" in prompt
    assert "events.append" in prompt
    assert "tracer.set" in prompt


def test_contract_prompt_examples_normalize_for_two_sum_dp_graph_stack():
    examples = [
        (
            "two_sum",
            {
                **_two_sum_contract_payload(),
                "test_cases": [{"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]}],
            },
            ProblemInput(problem="Two Sum", input_data={"nums": [2, 7, 11, 15], "target": 9}, expected_result=[0, 1]),
        ),
        (
            "dp",
            {
                "schema_version": "correctness-contract-v1",
                "input_schema": {"nums": "int[]"},
                "output_schema": "int",
                "postconditions": ["output is the maximum non-adjacent sum"],
                "oracle_strategy": "brute_force",
                "oracle_code": (
                    "def brute_force(input_data):\n"
                    "    nums = input_data['nums']\n"
                    "    def dfs(i):\n"
                    "        if i >= len(nums):\n"
                    "            return 0\n"
                    "        return max(dfs(i + 1), nums[i] + dfs(i + 2))\n"
                    "    return dfs(0)\n"
                ),
                "test_cases": [{"input": {"nums": [2, 7, 9, 3, 1]}, "expected": 12}],
            },
            ProblemInput(problem="House Robber", input_data={"nums": [2, 7, 9, 3, 1]}, expected_result=12),
        ),
        (
            "graph",
            {
                "schema_version": "correctness-contract-v1",
                "input_schema": {"graph": "object", "start": "str"},
                "output_schema": "object",
                "postconditions": ["output maps each reachable node to its BFS distance"],
                "oracle_strategy": "brute_force",
                "oracle_code": (
                    "def brute_force(input_data):\n"
                    "    graph = input_data['graph']\n"
                    "    start = input_data['start']\n"
                    "    dist = {start: 0}\n"
                    "    queue = [start]\n"
                    "    head = 0\n"
                    "    while head < len(queue):\n"
                    "        cur = queue[head]\n"
                    "        head += 1\n"
                    "        for nei in graph.get(cur, []):\n"
                    "            if nei not in dist:\n"
                    "                dist[nei] = dist[cur] + 1\n"
                    "                queue.append(nei)\n"
                    "    return dist\n"
                ),
                "test_cases": [{"input": {"graph": {"A": ["B"], "B": []}, "start": "A"}, "expected": {"A": 0, "B": 1}}],
            },
            ProblemInput(problem="BFS", input_data={"graph": {"A": ["B"], "B": []}, "start": "A"}, expected_result={"A": 0, "B": 1}),
        ),
        (
            "stack",
            {
                "schema_version": "correctness-contract-v1",
                "input_schema": {"temperatures": "int[]"},
                "output_schema": "int[]",
                "postconditions": ["answer[i] is wait until a warmer day"],
                "oracle_strategy": "brute_force",
                "oracle_code": (
                    "def brute_force(input_data):\n"
                    "    temperatures = input_data['temperatures']\n"
                    "    ans = []\n"
                    "    for i, temp in enumerate(temperatures):\n"
                    "        wait = 0\n"
                    "        for j in range(i + 1, len(temperatures)):\n"
                    "            if temperatures[j] > temp:\n"
                    "                wait = j - i\n"
                    "                break\n"
                    "        ans.append(wait)\n"
                    "    return ans\n"
                ),
                "test_cases": [{"input": {"temperatures": [30, 40, 50, 60]}, "expected": [1, 1, 1, 0]}],
            },
            ProblemInput(problem="Daily Temperatures", input_data={"temperatures": [30, 40, 50, 60]}, expected_result=[1, 1, 1, 0]),
        ),
    ]
    for name, raw, request in examples:
        contract = normalize_contract_spec(raw)
        report = validate_contract(contract, request)
        assert report.errors == [], (name, report.errors)
        assert report.release_gate.contract_ready, (name, report.release_gate)


def test_contract_repair_loop_fixes_truncated_json():
    request = ProblemInput(
        problem="Two Sum",
        input_data={"nums": [2, 7, 11, 15], "target": 9},
        expected_result=[0, 1],
    )
    responses = iter(
        [
            "{truncated",
            _two_sum_contract_payload(),
        ]
    )

    def fake_chat_json(_system_prompt, _user_prompt):
        item = next(responses)
        if isinstance(item, str):
            from llm_client import parse_json_content

            return parse_json_content(item)
        return item

    original = solution_generator.chat_json
    solution_generator.chat_json = fake_chat_json
    try:
        contract, repair_log = build_contract_with_repair(request, max_rounds=1)
    finally:
        solution_generator.chat_json = original

    assert contract.schema_version == "correctness-contract-v1"
    assert repair_log[0]["status"] == "failed"
    assert "LLMJsonError" in repair_log[0]["errors"][0]
    assert repair_log[-1]["status"] == "ok"


def test_contract_repair_loop_handles_validator_and_oracle_failures():
    request = ProblemInput(
        problem="Two Sum",
        input_data={"nums": [2, 7, 11, 15], "target": 9},
        expected_result=[0, 1],
    )
    bad_expected = _two_sum_contract_payload()
    bad_expected["test_cases"][0]["expected"] = [1, 2]
    fixed_expected = _two_sum_contract_payload()
    responses = iter([bad_expected, fixed_expected])

    original = solution_generator.chat_json
    solution_generator.chat_json = lambda _system_prompt, _user_prompt: next(responses)
    try:
        contract, repair_log = build_contract_with_repair(request, max_rounds=1)
    finally:
        solution_generator.chat_json = original

    assert contract.test_cases[0].expected == [0, 1]
    assert repair_log[0]["status"] == "failed"
    assert any("expected_result" in error for error in repair_log[0]["errors"])
    assert repair_log[-1]["status"] == "ok"

    bad_oracle = _two_sum_contract_payload()
    bad_oracle["oracle_code"] = "def brute_force(input_data):\n    return []"
    fixed_oracle = _two_sum_contract_payload()
    responses = iter([bad_oracle, fixed_oracle])
    solution_generator.chat_json = lambda _system_prompt, _user_prompt: next(responses)
    try:
        contract, repair_log = build_contract_with_repair(request, max_rounds=1)
    finally:
        solution_generator.chat_json = original

    assert contract.oracle_code == fixed_oracle["oracle_code"]
    assert repair_log[0]["status"] == "failed"
    assert any("oracle result" in error for error in repair_log[0]["errors"])
    assert repair_log[-1]["status"] == "ok"


def test_schema_rejects_non_contiguous_steps():
    bad = house_robber_trace().model_dump()
    bad["events"][1]["step"] = 7
    try:
        SemanticTrace.model_validate(bad)
    except ValidationError:
        return
    raise AssertionError("SemanticTrace 应拒绝不连续 step")


def test_trace_validator_rejects_unknown_index_target():
    trace_data = house_robber_trace().model_dump()
    trace_data["events"][1]["targets"] = [{"id": "dp[99]"}]
    trace = SemanticTrace.model_validate(trace_data)
    errors, _warnings = validate_trace(trace)
    assert any("不存在的索引" in e for e in errors), errors


def test_trace_validator_accepts_map_bracket_and_slice_targets():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "target 兼容",
            "input_data": {"text": "ababc"},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "text"}, {"id": "dist"}],
                    "state": {"text": "ababc", "dist": {"B": 1}},
                    "reason": "初始化字符串和 map。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "mark",
                    "targets": [{"id": "text[2:5]"}, {"id": "dist[B]"}],
                    "state": {"text": "ababc", "dist": {"B": 1}},
                    "role": "answer",
                    "reason": "高亮匹配片段和距离项。",
                    "code_line": 2,
                },
            ],
        }
    )
    errors, warnings = validate_trace(trace)
    assert errors == []
    assert not [w for w in warnings if "不存在" in w], warnings
    scene = compile_scene(trace)
    ids = {obj.id for frame in scene.frames for obj in frame.objects}
    assert "text[2:5]" in ids
    assert "dist[B]" in ids
    assert "dist:B" in ids


def test_trace_validator_accepts_input_tree_and_points_targets():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "input targets",
            "input_data": {
                "tree": {"nodes": [{"id": "3"}, {"id": "5"}], "edges": [["3", "5"]]},
                "points": [[0, 0], [1, 1]],
            },
            "result": None,
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "node:3"}, {"id": "points[0]"}, {"id": "point:1"}],
                    "state": {},
                    "reason": "高亮输入中的树节点和点。",
                    "code_line": 1,
                },
            ],
        }
    )
    errors, warnings = validate_trace(trace)
    assert errors == []
    assert not [w for w in warnings if "未在状态或输入图中出现" in w], warnings


def test_execute_variant_normalizes_quoted_map_targets():
    variant = SolutionVariant(
        id="quoted_map",
        name="quoted map",
        strategy="",
        code="def solve(input_data):\n    return 1",
        tracker_code=(
            "def trace(input_data):\n"
            "    return {\n"
            "      'schema_version': 'semantic-trace-v1',\n"
            "      'algorithm': 'map target',\n"
            "      'input_data': input_data,\n"
            "      'result': 1,\n"
            "      'events': [\n"
            "        {'step': 0, 'op': 'create', 'targets': [{'id': 'seen'}], 'state': {'seen': {'2': 0}}, 'reason': '初始化。', 'code_line': 1},\n"
            "        {'step': 1, 'op': 'mark', 'targets': [{'id': \"seen['2']\"}], 'state': {'seen': {'2': 0}}, 'reason': '高亮 map。', 'code_line': 2}\n"
            "      ]\n"
            "    }\n"
        ),
    )
    materialized = execute_variant(variant, {})
    assert materialized.trace is not None
    assert materialized.trace.events[1].targets[0].id == "seen[2]"
    errors, warnings = validate_trace(materialized.trace)
    assert errors == []
    assert warnings == []


def test_execute_variant_rejects_excessive_trace_events():
    variant = SolutionVariant(
        id="too_many_events",
        name="too many events",
        strategy="",
        code="def solve(input_data):\n    return 1",
        tracker_code=(
            "def trace(input_data):\n"
            "    return {\n"
            "      'schema_version': 'semantic-trace-v1',\n"
            "      'algorithm': 'too many',\n"
            "      'input_data': input_data,\n"
            "      'result': 1,\n"
            "      'events': [{'step': i, 'op': 'explain', 'targets': [], 'state': {}, 'reason': 'x', 'code_line': 1} for i in range(81)]\n"
            "    }\n"
        ),
    )
    try:
        execute_variant(variant, {})
    except ValueError as exc:
        assert "trace events 过多" in str(exc)
    else:
        raise AssertionError("过长 trace 应被拒绝")


def test_process_validator_accepts_map_container_dependency():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "map container dep",
            "input_data": {},
            "result": None,
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "seen"}],
                    "deps": [{"id": "map:seen"}],
                    "state": {"seen": {"2": 0}},
                    "reason": "引用哈希表容器。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, warnings = validate_process(trace)
    assert errors == []
    assert not [w for w in warnings if "deps 未出现在 state" in w], warnings


def test_semantic_event_normalizes_null_optional_text():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "空文本容错",
            "input_data": {},
            "result": None,
            "events": [
                {
                    "step": 0,
                    "op": "explain",
                    "targets": [],
                    "state": {},
                    "role": None,
                    "reason": None,
                    "code_line": 1,
                }
            ],
        }
    )
    assert trace.events[0].role == ""
    assert trace.events[0].reason == ""


def test_process_validator_rejects_bad_unique_paths_transition():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "不同路径",
            "input_data": {"m": 2, "n": 2},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "dp[1][1]"}],
                    "state": {"dp": [[1, 1], [1, 3]]},
                    "reason": "错误的 DP 表。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(trace)
    assert any("不同路径转移" in e for e in errors), errors


def test_process_validator_rejects_sparse_unique_paths_trace():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "不同路径",
            "input_data": {"m": 3, "n": 7},
            "result": 28,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "dp"}],
                    "state": {"dp": [[1] * 7 for _ in range(3)]},
                    "reason": "初始化 DP 表。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "set",
                    "targets": [{"id": "dp[1][1]"}],
                    "deps": [{"id": "dp[0][1]"}, {"id": "dp[1][0]"}],
                    "state": {"dp": [[1, 1, 1, 1, 1, 1, 1], [1, 2, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1]]},
                    "reason": "只展示了一个中间格。",
                    "code_line": 3,
                },
                {
                    "step": 2,
                    "op": "set",
                    "targets": [{"id": "dp[2][6]"}],
                    "deps": [{"id": "dp[1][6]"}, {"id": "dp[2][5]"}],
                    "state": {"dp": [[1, 1, 1, 1, 1, 1, 1], [1, 2, 3, 4, 5, 6, 7], [1, 3, 6, 10, 15, 21, 28]]},
                    "reason": "直接跳到最后一个格子。",
                    "code_line": 3,
                },
            ],
        }
    )
    errors, _warnings = validate_process(trace)
    assert any("缺少逐帧状态转移" in e for e in errors), errors


def test_process_validator_rejects_low_tracer_coverage_meta():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "覆盖率不足",
            "input_data": {"x": 1},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "answer"}],
                    "state": {
                        "answer": 1,
                        "_trace_meta": {
                            "policy": "full",
                            "max_events": 80,
                            "raw_event_count": 1,
                            "emitted_event_count": 1,
                            "sampled": False,
                            "expected_updates": {"dp": 12},
                            "recorded_updates": {"dp": 6},
                            "coverage": {"dp": 0.5},
                        },
                    },
                    "after": 1,
                    "reason": "覆盖率不足。",
                    "code_line": 1,
                }
            ],
        }
    )

    errors, _warnings = validate_process(trace)
    assert any("trace coverage dp 不足" in error for error in errors), errors


def test_process_validator_rejects_forged_tracer_coverage_meta():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "伪造覆盖率",
            "input_data": {"x": 1},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "dp[1][1]"}],
                    "state": {
                        "dp": [[1, 1], [1, 2]],
                        "_trace_meta": {
                            "policy": "full",
                            "max_events": 80,
                            "raw_event_count": 1,
                            "emitted_event_count": 1,
                            "sampled": False,
                            "expected_updates": {"dp": 12},
                            "recorded_updates": {"dp": 1},
                            "coverage": {"dp": 1.0},
                        },
                    },
                    "value": 2,
                    "reason": "只记录了一个更新，但覆盖率被伪造为完整。",
                    "code_line": 1,
                }
            ],
        }
    )

    errors, _warnings = validate_process(trace)
    assert any("trace coverage dp 不足" in error for error in errors), errors


def test_process_validator_rejects_bad_bfs_distance():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "BFS",
            "input_data": {"graph": {"A": ["B"], "B": []}, "start": "A"},
            "result": {"A": 0, "B": 1},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "dist[B]"}],
                    "state": {"graph": {"A": ["B"], "B": []}, "dist": {"A": 0, "B": 2}},
                    "reason": "错误距离。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(trace)
    assert any("dist[B]" in e for e in errors), errors


def test_process_validator_rejects_bad_subset_sum_transition():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "分割等和子集",
            "input_data": {"nums": [1, 5, 11, 5]},
            "result": True,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "dp[2]"}],
                    "state": {"nums": [1, 5, 11, 5], "target": 11, "i": 0, "num": 1, "dp": [True, True, True, False, False, False, False, False, False, False, False, False]},
                    "reason": "错误地认为只用数字 1 可以凑出 2。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(trace)
    assert any("0-1 背包可达性" in e for e in errors), errors


def test_process_validator_rejects_binary_search_mid_outside_window():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分",
            "input_data": {"nums": [1, 3, 5], "target": 3},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "compare",
                    "targets": [{"id": "nums[0]"}],
                    "state": {"nums": [1, 3, 5], "left": 0, "right": 1, "mid": 2, "target": 3},
                    "reason": "错误 mid。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(trace)
    assert any("mid 不在" in e for e in errors), errors


def test_process_validator_rejects_bad_heap_and_union_find():
    heap_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "坏堆",
            "input_data": {"heap": [3, 1]},
            "result": None,
            "events": [{"step": 0, "op": "create", "targets": [{"id": "heap"}], "state": {"heap": [3, 1]}, "reason": "坏小顶堆。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(heap_trace_bad)
    assert any("小顶堆" in e for e in errors), errors

    uf_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "坏并查集",
            "input_data": {},
            "result": None,
            "events": [{"step": 0, "op": "create", "targets": [{"id": "union_find"}], "state": {"union_find": {"parent": {"1": "2", "2": "1"}}}, "reason": "存在环。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(uf_trace_bad)
    assert any("非根环" in e for e in errors), errors


def test_process_validator_rejects_bad_monotonic_stack_and_topo():
    mono_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "坏单调栈",
            "input_data": {},
            "result": None,
            "events": [{"step": 0, "op": "push", "targets": [{"id": "stack"}], "state": {"stack": [3, 1], "stack_order": "increasing"}, "reason": "递增栈错误。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(mono_trace_bad)
    assert any("单调递增" in e for e in errors), errors

    topo_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "坏拓扑序",
            "input_data": {"graph": {"A": ["B"], "B": []}},
            "result": ["B", "A"],
            "events": [{"step": 0, "op": "set", "targets": [{"id": "order"}], "state": {"graph": {"A": ["B"], "B": []}, "topo_order": ["B", "A"]}, "reason": "拓扑序错误。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(topo_trace_bad)
    assert any("topo_order" in e for e in errors), errors


def test_process_validator_rejects_bad_dijkstra_lcs_and_edit_distance():
    dijkstra_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "坏 Dijkstra",
            "input_data": {"graph": {"A": [["B", 5]], "B": []}, "start": "A"},
            "result": {"A": 0, "B": 5},
            "events": [{"step": 0, "op": "set", "targets": [{"id": "dist[B]"}], "state": {"dist": {"A": 0, "B": 3}}, "reason": "距离过小。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(dijkstra_trace_bad)
    assert any("Dijkstra" in e for e in errors), errors

    lcs_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "坏 LCS",
            "input_data": {"text1": "a", "text2": "a"},
            "result": 1,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "dp[1][1]"}], "state": {"dp": [[0, 0], [0, 0]]}, "reason": "LCS 错误。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(lcs_trace_bad)
    assert any("LCS" in e for e in errors), errors

    edit_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "坏编辑距离",
            "input_data": {"word1": "a", "word2": "b"},
            "result": 1,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "dp[1][1]"}], "state": {"dp": [[0, 1], [1, 0]]}, "reason": "编辑距离错误。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(edit_trace_bad)
    assert any("编辑距离" in e for e in errors), errors


def test_process_validator_rejects_bad_kmp_complete_knapsack_interval_dp():
    kmp_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "KMP",
            "input_data": {"pattern": "ababaca"},
            "result": None,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "pi[5]"}], "state": {"pi": [0, 0, 1, 2, 3, 9, 0]}, "reason": "错误前缀函数。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(kmp_trace_bad)
    assert any("KMP" in e for e in errors), errors

    coin_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "零钱兑换",
            "input_data": {"coins": [1, 2], "amount": 3},
            "result": 2,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "dp[3]"}], "state": {"dp": [0, 1, 1, 3], "dp_mode": "complete_min"}, "reason": "错误完全背包。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(coin_trace_bad)
    assert any("完全背包" in e for e in errors), errors

    interval_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "石子合并",
            "input_data": {"stones": [1, 2]},
            "result": 3,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "dp[0][1]"}], "state": {"dp": [[0, 9], [0, 0]], "dp_mode": "merge_stones"}, "reason": "错误区间 DP。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(interval_trace_bad)
    assert any("区间 DP" in e for e in errors), errors


def test_process_validator_rejects_bad_bst_lca_tarjan_mst_geometry_backtracking():
    bst_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "BST",
            "input_data": {},
            "result": None,
            "events": [{"step": 0, "op": "create", "targets": [{"id": "tree"}], "state": {"tree": {"kind": "bst", "nodes": [{"id": "5", "value": 5}, {"id": "7", "value": 7}], "edges": [["5", "7"]]}}, "reason": "左孩子比根大。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(bst_trace_bad)
    assert any("BST" in e for e in errors), errors

    tree = {"nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}], "edges": [["1", "2"], ["1", "3"]]}
    lca_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "LCA",
            "input_data": {"tree": tree, "p": "2", "q": "3"},
            "result": "1",
            "events": [{"step": 0, "op": "set", "targets": [{"id": "answer"}], "state": {"tree": tree, "lca": "2"}, "reason": "错误 LCA。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(lca_trace_bad)
    assert any("LCA" in e for e in errors), errors

    tarjan_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Tarjan",
            "input_data": {},
            "result": None,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "low[A]"}], "state": {"dfn": {"A": 1}, "low": {"A": 2}}, "reason": "lowlink 错误。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(tarjan_trace_bad)
    assert any("low" in e for e in errors), errors

    mst_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "MST",
            "input_data": {"edges": [["A", "B", 1], ["B", "C", 1], ["A", "C", 1]]},
            "result": None,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "mst_edges"}], "state": {"mst_edges": [["A", "B", 1], ["B", "C", 1], ["A", "C", 1]]}, "reason": "MST 有环。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(mst_trace_bad)
    assert any("MST" in e for e in errors), errors

    geometry_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "凸包",
            "input_data": {},
            "result": None,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "geometry"}], "state": {"geometry": {"points": [{"id": "a", "x": 0, "y": 0}, {"id": "b", "x": 2, "y": 0}, {"id": "c", "x": 1, "y": 1}, {"id": "d", "x": 0, "y": 2}], "hull": ["a", "b", "d", "c"]}}, "reason": "非凸 hull。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(geometry_trace_bad)
    assert any("hull" in e for e in errors), errors

    backtracking_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "回溯",
            "input_data": {},
            "result": None,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "recursion_tree"}], "state": {"recursion_tree": {"nodes": [{"id": "root"}, {"id": "a"}], "edges": [["root", "a"], ["a", "root"]]}}, "reason": "搜索树有环。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(backtracking_trace_bad)
    assert any("回溯搜索树" in e for e in errors), errors


def test_process_validator_level_selection():
    core_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "层级测试 core",
            "input_data": {"nums": [1]},
            "result": None,
            "events": [
                {"step": 0, "op": "create", "targets": [{"id": "nums"}], "state": {"nums": [1]}, "reason": "初始化。", "code_line": 1},
                {"step": 1, "op": "set", "targets": [{"id": "nums[0]"}], "before": 9, "after": 2, "state": {"nums": [2]}, "reason": "更新。", "code_line": 2},
            ],
        }
    )
    errors, warnings = validate_process(core_trace_bad, levels="core")
    assert errors == []
    assert any("before 与上一状态不一致" in w for w in warnings), warnings
    errors, _warnings = validate_process(core_trace_bad, levels="algorithm")
    assert errors == []

    structure_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "层级测试 structure",
            "input_data": {},
            "result": None,
            "events": [{"step": 0, "op": "create", "targets": [{"id": "heap"}], "state": {"heap": [3, 1]}, "reason": "坏小顶堆。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(structure_trace_bad, levels=["structure"])
    assert any("小顶堆" in e for e in errors), errors
    errors, _warnings = validate_process(structure_trace_bad, levels=["algorithm"])
    assert errors == []

    algorithm_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "层级测试 algorithm",
            "input_data": {"pattern": "ababaca"},
            "result": None,
            "events": [{"step": 0, "op": "set", "targets": [{"id": "pi[5]"}], "state": {"pi": [0, 0, 1, 2, 3, 9, 0]}, "reason": "错误前缀函数。", "code_line": 1}],
        }
    )
    errors, _warnings = validate_process(algorithm_trace_bad, levels=["algorithm"])
    assert any("KMP" in e for e in errors), errors
    errors, _warnings = validate_process(algorithm_trace_bad, levels=["structure"])
    assert errors == []

    try:
        validate_process(algorithm_trace_bad, levels=["unknown"])  # type: ignore[list-item]
    except ValueError as exc:
        assert "未知 process invariant 层级" in str(exc)
    else:
        raise AssertionError("未知 invariant 层级应被拒绝")


def test_process_validator_rejects_unobservable_process_steps():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "空洞过程",
            "input_data": {"nums": [1]},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [1], "answer": 0},
                    "reason": "初始化。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "set",
                    "targets": [{"id": "answer"}],
                    "state": {"nums": [1], "answer": 0},
                    "reason": "声称写入答案，但状态没有变化，也没有 before/after/value/deps。",
                    "code_line": 2,
                },
            ],
        }
    )

    errors, warnings = validate_process(trace)

    assert warnings == []
    assert any("缺少可观测过程证据" in error for error in errors), errors


def test_scene_compiler_outputs_cells_and_arrows():
    scene = compile_scene(house_robber_trace())
    frame = scene.frames[2]
    object_types = {obj.type.value for obj in frame.objects}
    assert "cell" in object_types
    assert "arrow" in object_types
    assert any(mark.role == "dependency" for mark in frame.marks)


def test_scene_compiler_materializes_symbol_targets_as_labels():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "标量 target",
            "input_data": {"m": 3},
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "m"}],
                    "state": {"answer": 3},
                    "role": "current",
                    "reason": "标量 target 也应有可见 label。",
                    "code_line": 1,
                }
            ],
        }
    )
    scene = compile_scene(trace)
    errors, warnings = validate_scene(scene)
    assert errors == []
    assert warnings == []
    assert any(obj.id == "m" and obj.type.value == "label" for obj in scene.frames[0].objects)


def test_scene_compiler_binds_pointers_to_array_cells():
    trace_data = house_robber_trace().model_dump()
    trace_data["events"][1] = {
        "step": 1,
        "op": "set",
        "targets": [{"id": "pointer:left"}, {"id": "pointer:right"}],
        "value": [0, 4],
        "state": {"nums": [2, 7, 9, 3, 1], "left": 0, "right": 4},
        "role": "current",
        "reason": "初始化左右指针。",
        "code_line": 1,
    }
    trace = SemanticTrace.model_validate(trace_data)
    scene = compile_scene(trace)
    pointers = [obj for obj in scene.frames[1].objects if obj.type.value == "pointer"]
    assert {p.target for p in pointers} == {"nums[0]", "nums[4]"}
    assert all(p.parent == "nums" for p in pointers)


def test_scene_compiler_outputs_graph_nodes():
    scene = compile_scene(bfs_trace())
    frame = scene.frames[0]
    assert any(obj.id == "node:A" for obj in frame.objects)
    assert any(obj.type.value == "edge" for obj in frame.objects)


def test_classic_visual_layout_coverage():
    cases = [
        (tree_trace(), "tree"),
        (heap_trace(), "heap"),
        (trie_trace(), "trie"),
        (union_find_trace(), "union_find"),
        (recursion_trace(), "stack"),
        (string_trace(), "string"),
        (geometry_trace(), "geometry"),
    ]
    for trace, expected_layout in cases:
        scene = compile_scene(trace)
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expected_layout in layouts, (trace.algorithm, expected_layout, layouts)


def test_all_13_algorithm_families_have_fixture_and_layout():
    cases = algorithm_family_traces()
    assert len(cases) == 13
    seen_ids = {case[0] for case in cases}
    assert len(seen_ids) == 13
    for _variant_id, family_name, trace, expected_layout in cases:
        scene = compile_scene(trace)
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expected_layout in layouts, (family_name, expected_layout, layouts)


def test_classic_subfamilies_have_deterministic_visual_coverage():
    cases = algorithm_subfamily_traces()
    assert len(cases) >= 27
    seen_ids = {case[0] for case in cases}
    assert len(seen_ids) == len(cases)
    for variant_id, name, trace, expected_layouts, expected_objects in cases:
        scene = compile_scene(trace)
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
        for expected_layout in expected_layouts:
            assert expected_layout in layouts, (variant_id, name, expected_layout, layouts)
        for expected_object in expected_objects:
            assert expected_object in object_ids, (variant_id, name, expected_object)


def test_ml_primitives_cover_linear_and_logistic_regression(tmp_path: Path):
    linear = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "线性回归单步训练",
            "input_data": {"x": [[1.0], [2.0]], "y": [2.0, 4.0]},
            "result": {"prediction": [1.2, 2.4], "loss": 1.8},
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "training"}],
                    "state": {
                        "training": {
                            "features": [[1.0], [2.0]],
                            "batch": {"start": 0, "size": 2},
                            "parameters": {"w": 1.2, "b": 0.0},
                            "loss_curve": [3.2, 2.4, 1.8],
                            "gradient": {"w": -1.1, "b": -0.6},
                            "epoch": 1,
                            "prediction": [1.2, 2.4],
                        }
                    },
                    "reason": "展示线性回归的一次参数更新状态。",
                    "code_line": 1,
                }
            ],
        }
    )
    logistic = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "逻辑回归边界",
            "input_data": {"x": [[0, 0], [1, 1]], "y": [0, 1]},
            "result": {"prediction": [0, 1]},
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "model"}],
                    "state": {
                        "model": {
                            "tensor": [[0, 0], [1, 1]],
                            "parameters": {"w0": 1.0, "w1": 1.0, "b": -0.5},
                            "computational_graph": {
                                "nodes": [{"id": "x"}, {"id": "linear"}, {"id": "sigmoid"}, {"id": "loss"}],
                                "edges": [["x", "linear"], ["linear", "sigmoid"], ["sigmoid", "loss"]],
                            },
                            "decision_boundary": {"w": [1.0, 1.0], "b": -0.5},
                            "prediction": [0, 1],
                            "loss": 0.31,
                        }
                    },
                    "role": "current",
                    "reason": "展示逻辑回归的计算图和决策边界。",
                    "code_line": 1,
                }
            ],
        }
    )

    scenes = [compile_scene(linear), compile_scene(logistic)]
    for scene in scenes:
        errors, warnings = validate_scene(scene)
        assert errors == []
        assert warnings == []

    objects = [obj for scene in scenes for frame in scene.frames for obj in frame.objects]
    object_types = {obj.type.value for obj in objects}
    assert {
        "tensor",
        "batch",
        "parameter",
        "loss_curve",
        "gradient_vector",
        "decision_boundary",
        "training_epoch",
        "prediction",
    } <= object_types
    layouts = {obj.meta.get("layout") for obj in objects if obj.type.value == "container" or obj.meta}
    assert {"ml", "matrix", "computational_graph"} <= layouts
    assert any(obj.type.value == "edge" and obj.parent.endswith("computational_graph") for obj in objects)

    artifact = fixture_artifact().model_copy(deep=True)
    artifact.variants[0].id = "linear_ml"
    artifact.scenes = {"linear_ml": scenes[0], "logistic_ml": scenes[1]}
    out = save_html(artifact, tmp_path / "ml.html")
    html = out.read_text(encoding="utf-8")
    assert "renderML" in html
    assert "loss_curve" in html
    assert "decision_boundary" in html


def test_ml_correctness_accepts_linear_regression_gradient_and_loss_curve():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "线性回归单步梯度校验",
            "input_data": {"x": [[1.0], [2.0]], "y": [2.0, 4.0]},
            "result": {"loss": 1.0},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "training"}],
                    "state": {
                        "training": {
                            "features": [[1.0], [2.0]],
                            "labels": [2.0, 4.0],
                            "parameters": {"w": 1.0, "b": 0.0},
                            "prediction": [1.0, 2.0],
                            "gradient": {"w": -2.5, "b": -1.5},
                            "loss": 1.25,
                            "loss_curve": [3.0, 1.8, 1.25],
                            "loss_should_decrease": True,
                            "tolerance": 1e-9,
                        }
                    },
                    "reason": "校验线性回归的 MSE 单步梯度、loss 和 loss curve。",
                    "code_line": 1,
                }
            ],
        }
    )

    errors, warnings = validate_process(trace)

    assert errors == []
    assert warnings == []


def test_ml_correctness_rejects_bad_linear_regression_gradient_and_loss_curve():
    bad_gradient = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "线性回归错误梯度",
            "input_data": {"x": [[1.0], [2.0]], "y": [2.0, 4.0]},
            "result": None,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "training"}],
                    "state": {
                        "training": {
                            "features": [[1.0], [2.0]],
                            "labels": [2.0, 4.0],
                            "parameters": {"w": 1.0, "b": 0.0},
                            "prediction": [1.0, 2.0],
                            "gradient": {"w": -2.0, "b": -1.5},
                            "loss": 1.25,
                        }
                    },
                    "reason": "错误梯度应被 process invariant 拦截。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(bad_gradient)
    assert any("线性回归 grad_w" in error for error in errors), errors

    bad_curve = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "ML loss curve 错误",
            "input_data": {"x": [1, 2], "y": [2, 4]},
            "result": None,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "training"}],
                    "state": {
                        "training": {
                            "features": [1.0, 2.0],
                            "labels": [2.0, 4.0],
                            "parameters": {"w": 1.0, "b": 0.0},
                            "gradient": {"w": -2.5, "b": -1.5},
                            "loss_curve": [1.0, 1.3],
                            "loss_should_decrease": True,
                            "tolerance": 1e-9,
                        }
                    },
                    "reason": "loss curve 明显上升。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(bad_curve)
    assert any("loss_curve[1]" in error for error in errors), errors


def test_ml_correctness_checks_parameter_update_tolerance_and_random_seed():
    good_update = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "梯度下降训练动态",
            "input_data": {"x": [1.0, 2.0], "y": [2.0, 4.0]},
            "result": None,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "training"}],
                    "state": {
                        "training": {
                            "features": [1.0, 2.0],
                            "labels": [2.0, 4.0],
                            "parameters": {"w": 1.0, "b": 0.0},
                            "parameters_before": {"w": 1.0, "b": 0.0},
                            "parameters_after": {"w": 1.25, "b": 0.15},
                            "gradient": {"w": -2.5, "b": -1.5},
                            "learning_rate": 0.1,
                            "prediction": [1.0, 2.0],
                            "loss_curve": [2.0, 1.6],
                            "shuffle": True,
                            "seed": 42,
                        }
                    },
                    "reason": "校验单步参数更新和随机 seed。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(good_update)
    assert errors == []

    bad_update_and_seed = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "随机小批量梯度下降错误",
            "input_data": {"x": [1.0, 2.0], "y": [2.0, 4.0]},
            "result": None,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "training"}],
                    "state": {
                        "training": {
                            "features": [1.0, 2.0],
                            "labels": [2.0, 4.0],
                            "parameters_before": {"w": 1.0, "b": 0.0},
                            "parameters_after": {"w": 1.2, "b": 0.15},
                            "gradient": {"w": -2.5, "b": -1.5},
                            "learning_rate": 0.1,
                            "batch_sampling": "random",
                        }
                    },
                    "reason": "随机训练没有 seed，参数更新也错误。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(bad_update_and_seed)
    assert any("缺少固定 seed" in error for error in errors), errors
    assert any("参数 w 更新" in error for error in errors), errors


def test_sandbox_blocks_imports_and_times_out():
    assert run_function("def solve(input_data):\n    return input_data['x'] + 1", "solve", {"x": 2}) == 3

    try:
        run_function("import os\ndef solve(input_data):\n    return 1", "solve", {}, timeout_s=1)
    except SandboxError:
        pass
    else:
        raise AssertionError("sandbox 应禁止 os import")

    try:
        run_function("def solve(input_data):\n    while True:\n        pass", "solve", {}, timeout_s=1)
    except SandboxError as exc:
        assert "超时" in str(exc) or "无返回" in str(exc)
    else:
        raise AssertionError("sandbox 应终止死循环")


def test_sandbox_exposes_tracer_to_generated_tracker():
    code = """
def trace(input_data):
    tracer = Tracer(input_data, algorithm="常量")
    tracer.create("answer", state={"answer": 1}, reason="初始化答案。")
    tracer.result(1)
    return tracer.to_trace()
"""
    result = run_function(code, "trace", {"x": 1})
    assert result["algorithm"] == "常量"
    assert result["result"] == 1
    assert result["events"][0]["op"] == "create"


def test_sandbox_blocks_dunder_introspection_import_escape():
    attacks = [
        'def solve(input_data):\n    return Tracer.__init__.__globals__["__builtins__"]["__import__"]("os").getcwd()',
        'def solve(input_data):\n    return copy.deepcopy.__globals__["__builtins__"]["__import__"]("os").getcwd()',
        'def solve(input_data):\n    key = "_" * 2 + "import" + "_" * 2\n    return Tracer.__init__.__globals__["__builtins__"][key]("os").getcwd()',
    ]
    for code in attacks:
        try:
            run_function(code, "solve", {}, timeout_s=1)
        except SandboxError as exc:
            assert "禁止访问内部属性" in str(exc) or "禁止构造内部属性名" in str(exc)
        else:
            raise AssertionError("sandbox should reject dunder introspection import escape")


def test_renderer_writes_html(tmp_path: Path):
    out = save_html(fixture_artifact(), tmp_path / "fixture.html")
    html = out.read_text(encoding="utf-8")
    assert "离线打家劫舍" in html
    assert "SemanticTrace" not in html
    assert "RUNTIME_TARGET" in html
    assert "LAYOUT_RENDERERS" in html
    assert out.with_suffix(".json").exists()


def test_execute_variant_requires_trace_input_data():
    variant = SolutionVariant(
        id="bad",
        name="坏 trace",
        strategy="",
        code="def solve(input_data):\n    return 1",
        tracker_code=(
            "def trace(input_data):\n"
            "    return {'schema_version':'semantic-trace-v1','algorithm':'x','input_data':{},"
            "'result':1,'events':[{'step':0,'op':'explain','reason':'x','code_line':1}]}"
        ),
    )
    try:
        execute_variant(variant, {"x": 1})
    except Exception as exc:
        assert "input_data" in str(exc)
    else:
        raise AssertionError("execute_variant 应拒绝 trace.input_data 不一致")


def test_execute_variant_normalizes_event_steps():
    variant = SolutionVariant(
        id="step_normalize",
        name="step 归一化",
        strategy="",
        code="def solve(input_data):\n    return 1",
        tracker_code=(
            "def trace(input_data):\n"
            "    return {'schema_version':'semantic-trace-v1','algorithm':'x','input_data':input_data,"
            "'result':1,'events':["
            "{'step':0,'op':'create','targets':[{'id':'x'}],'state':{'x':1},'reason':'x','code_line':1},"
            "{'step':9,'op':'set','targets':[{'id':'x'}],'state':{'x':1},'reason':'x','code_line':2}"
            "]}"
        ),
    )
    materialized = execute_variant(variant, {"x": 1})
    assert materialized.trace is not None
    assert [event.step for event in materialized.trace.events] == [0, 1]


def test_scene_validator_rejects_empty_visual_frame():
    scene = SceneGraph(
        algorithm="x",
        input_data={},
        frames=[
            {
                "step": 0,
                "title": "空",
                "description": "",
                "operation": "explain",
                "objects": [],
            }
        ],
    )
    errors, _warnings = validate_scene(scene)
    assert errors


def _good_spec(verifier_code: str = ""):
    trace_literal = {
        "schema_version": "semantic-trace-v1",
        "algorithm": "常量",
        "input_data": {"x": 1},
        "result": 1,
        "events": [
            {
                "step": 0,
                "op": "create",
                "targets": [{"id": "x"}],
                "state": {"x": 1},
                "reason": "读取输入。",
                "code_line": 1,
            },
            {
                "step": 1,
                "op": "set",
                "targets": [{"id": "answer"}],
                "after": 1,
                "state": {"answer": 1},
                "reason": "返回答案。",
                "code_line": 2,
            },
        ],
    }
    return {
        "problem_title": "常量题",
        "input_contract": "读取 x。",
        "variants": [
            {
                "id": "const",
                "name": "常量解",
                "strategy": "返回 1。",
                "time_complexity": "O(1)",
                "space_complexity": "O(1)",
                "code": "def solve(input_data):\n    return 1",
                "tracker_code": f"def trace(input_data):\n    return {trace_literal!r}",
            }
        ],
        "verifier_code": verifier_code,
    }


def test_pipeline_requires_process_evidence():
    request = ProblemInput(problem="常量题", input_data={"x": 1})
    artifact, errors = _try_materialize(request, _good_spec())
    assert not artifact.validation.release_gate.release_ready
    assert "缺少独立 verifier" in " ".join(artifact.validation.release_gate.blocking_reasons)
    assert errors == []


def test_pipeline_expected_result_allows_single_solution_release():
    request = ProblemInput(problem="常量题", input_data={"x": 1}, expected_result=1)
    artifact, errors = _try_materialize(request, _good_spec())
    assert artifact.validation.release_gate.release_ready
    assert errors == []


def test_pipeline_blocks_unobservable_process_even_with_expected_result():
    request = ProblemInput(problem="常量题", input_data={"x": 1}, expected_result=1)
    trace_literal = {
        "schema_version": "semantic-trace-v1",
        "algorithm": "常量",
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
                "op": "set",
                "targets": [{"id": "answer"}],
                "state": {"answer": 1},
                "reason": "声称更新答案，但状态没有变化，也没有 before/after/value/deps。",
                "code_line": 2,
            },
        ],
    }
    spec = _good_spec()
    spec["variants"][0]["tracker_code"] = f"def trace(input_data):\n    return {trace_literal!r}"

    artifact, errors = _try_materialize(request, spec)

    assert not artifact.validation.release_gate.release_ready
    assert any("缺少可观测过程证据" in error for error in errors), errors


def test_pipeline_bad_verifier_blocks_release():
    request = ProblemInput(problem="常量题", input_data={"x": 1}, expected_result=1)
    artifact, errors = _try_materialize(request, _good_spec("def verify(input_data):\n    return 2"))
    assert not artifact.validation.release_gate.release_ready
    assert errors


def run_all():
    tests = [
        test_correctness_contract_accepts_minimal_two_sum,
        test_correctness_contract_rejects_invalid_contract,
        test_visual_plan_accepts_2d_3d_hybrid_and_rejects_invalid_target,
        test_visual_plan_prompt_and_validator_use_capabilities,
        test_app_benchmark_presets_cover_documented_benchmark_samples,
        test_layout_registry_declares_phase6_components,
        test_teaching_schema_rejects_unknown_fields,
        test_build_artifact_accepts_old_payload_without_new_optional_fields,
        test_build_artifact_dumps_optional_contract_visual_plan_and_render_report,
        test_render_report_schema_records_target_fallback_and_browser_smoke,
        test_contract_validator_rejects_bad_schema_and_expected_mismatch,
        test_contract_validator_accepts_expected_only_partial_contract,
        test_contract_validator_rejects_unusable_test_cases,
        test_contract_validator_executes_two_sum_brute_force_oracle,
        test_contract_validator_executes_daily_temperatures_brute_force_oracle,
        test_contract_validator_supports_expected_user_and_generated_oracles,
        test_contract_validator_blocks_oracle_expected_mismatch_and_timeout,
        test_contract_prompt_states_json_expected_and_verifier_boundaries,
        test_tracker_prompt_requires_tracer_api,
        test_repair_prompt_converts_sparse_trace_to_tracer_api,
        test_contract_prompt_examples_normalize_for_two_sum_dp_graph_stack,
        test_contract_repair_loop_fixes_truncated_json,
        test_contract_repair_loop_handles_validator_and_oracle_failures,
        test_schema_rejects_non_contiguous_steps,
        test_trace_validator_rejects_unknown_index_target,
        test_trace_validator_accepts_map_bracket_and_slice_targets,
        test_trace_validator_accepts_input_tree_and_points_targets,
        test_execute_variant_normalizes_quoted_map_targets,
        test_execute_variant_rejects_excessive_trace_events,
        test_process_validator_accepts_map_container_dependency,
        test_semantic_event_normalizes_null_optional_text,
        test_process_validator_rejects_bad_unique_paths_transition,
        test_process_validator_rejects_sparse_unique_paths_trace,
        test_process_validator_rejects_low_tracer_coverage_meta,
        test_process_validator_rejects_forged_tracer_coverage_meta,
        test_process_validator_rejects_bad_bfs_distance,
        test_process_validator_rejects_bad_subset_sum_transition,
        test_process_validator_rejects_binary_search_mid_outside_window,
        test_process_validator_rejects_bad_heap_and_union_find,
        test_process_validator_rejects_bad_monotonic_stack_and_topo,
        test_process_validator_rejects_bad_dijkstra_lcs_and_edit_distance,
        test_process_validator_rejects_bad_kmp_complete_knapsack_interval_dp,
        test_process_validator_rejects_bad_bst_lca_tarjan_mst_geometry_backtracking,
        test_process_validator_level_selection,
        test_process_validator_rejects_unobservable_process_steps,
        test_scene_compiler_outputs_cells_and_arrows,
        test_scene_compiler_materializes_symbol_targets_as_labels,
        test_scene_compiler_binds_pointers_to_array_cells,
        test_scene_compiler_outputs_graph_nodes,
        test_classic_visual_layout_coverage,
        test_all_13_algorithm_families_have_fixture_and_layout,
        test_classic_subfamilies_have_deterministic_visual_coverage,
        test_ml_correctness_accepts_linear_regression_gradient_and_loss_curve,
        test_ml_correctness_rejects_bad_linear_regression_gradient_and_loss_curve,
        test_ml_correctness_checks_parameter_update_tolerance_and_random_seed,
        test_sandbox_blocks_imports_and_times_out,
        test_sandbox_exposes_tracer_to_generated_tracker,
        test_sandbox_blocks_dunder_introspection_import_escape,
        test_execute_variant_requires_trace_input_data,
        test_execute_variant_normalizes_event_steps,
        test_scene_validator_rejects_empty_visual_frame,
        test_pipeline_requires_process_evidence,
        test_pipeline_expected_result_allows_single_solution_release,
        test_pipeline_blocks_unobservable_process_even_with_expected_result,
        test_pipeline_bad_verifier_blocks_release,
    ]
    for test in tests:
        test()
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        test_teaching_schema_compiles_explicit_fields_and_reason_fallback(Path(d))
        test_stable_renderer_exposes_correctness_and_step_evidence(Path(d))
        test_scene_compiler_hides_internal_trace_meta_from_rendered_state(Path(d))
        test_renderer_writes_html(Path(d))
        test_ml_primitives_cover_linear_and_logistic_regression(Path(d))


if __name__ == "__main__":
    run_all()
    print("offline_regression: PASS")
