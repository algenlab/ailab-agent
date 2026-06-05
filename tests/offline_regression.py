"""Offline regression suite.

This test suite does not call the LLM. It validates the stable architecture:
schema -> validator -> scene compiler -> renderer -> sandbox.
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path

from pydantic import ValidationError

from algolab.compiler.scene_compiler import compile_scene
from app import benchmark_preset_choices, load_benchmark_preset
import algolab.generation.solution_generator as solution_generator
import scripts.run_llm_benchmark as llm_benchmark
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
from algolab.schemas.validation import BuildArtifact, ValidationReport
from algolab.schemas.visual_plan import RenderTarget, VisualPlan
from algolab.verification.scene_validator import validate_scene
from algolab.verification.contract_validator import validate_contract
from algolab.verification.process_validator import (
    process_validation_profile_for_family,
    process_validation_registry,
    validate_process,
)
from algolab.verification.trace_validator import validate_trace
from algolab.verification.visual_plan_validator import validate_visual_plan
from tests.fixtures import (
    algorithm_subfamily_traces,
    algorithm_family_traces,
    bfs_trace,
    fixture_artifact,
    diff_prefix_trace,
    golden_visual_artifact,
    golden_visual_matrix,
    geometry_trace,
    hash_map_trace,
    heap_trace,
    house_robber_trace,
    monotonic_stack_trace,
    recursion_trace,
    recursion_tree_trace,
    phase17_visual_pattern_artifact,
    phase17_visual_pattern_matrix,
    string_trace,
    tree_trace,
    trie_trace,
    topk_heap_trace,
    two_pointer_trace,
    union_find_trace,
    unique_paths_trace,
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
        "linked_list": "linked_list",
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


def test_teaching_step_renders_structured_fields_without_algorithm_branches(tmp_path: Path):
    out = save_html(golden_visual_artifact(), tmp_path / "teaching_step.html")
    html = out.read_text(encoding="utf-8")

    assert "function renderTeachingField" in html
    assert "function teachingFieldRows" in html
    assert ".teach-row.formula" in html
    assert ".teach-row.invariant" in html
    assert ".teach-row.common_mistake" in html
    assert ".teach-row.hint" in html

    renderer = html.split("function teachingRows", 1)[1].split("function renderInteraction", 1)[0]
    assert "algorithm" not in renderer
    assert "problem_title" not in renderer
    assert "teaching.formula || ''" not in renderer
    assert "renderTeachingField" in renderer

    field_renderer = html.split("function renderTeachingField", 1)[1].split("function teachingRows", 1)[0]
    assert "row.key" in field_renderer


def test_teaching_step_covers_generic_algorithm_families_and_formula_fallback():
    artifact = golden_visual_artifact()
    expectations = {
        "unique_paths": ("dp[1][1] = 1 + 1 = 2", "处理当前格时"),
        "bfs": ("dist[v] = dist[A] + 1", "未访问节点第一次入队"),
        "binary_search": ("left = mid + 1", "新区间仍覆盖"),
        "monotonic_stack": ("answer[0] = 1 - 0 = 1", "被弹出的下标"),
    }

    for variant_id, (formula_part, invariant_part) in expectations.items():
        scene = artifact.scenes[variant_id]
        teaching_values = [frame.teaching or {} for frame in scene.frames]
        assert any(formula_part in str(teaching.get("formula", "")) for teaching in teaching_values), variant_id
        assert any(invariant_part in str(teaching.get("invariant", "")) for teaching in teaching_values), variant_id
        assert all(str(teaching.get("what", "")).strip() for teaching in teaching_values), variant_id
        assert all(str(teaching.get("why", "")).strip() for teaching in teaching_values), variant_id

    no_formula_trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "无公式教学",
            "input_data": {"items": ["A"]},
            "result": ["A"],
            "events": [
                {
                    "step": 0,
                    "op": "push",
                    "targets": [{"id": "queue"}],
                    "state": {"queue": ["A"]},
                    "reason": "元素入队。",
                    "code_line": 1,
                    "teaching": {
                        "what": "元素入队",
                        "why": "按到达顺序处理。",
                        "formula": "",
                        "invariant": "队列保持先进先出。",
                        "hint": "观察队尾变化。",
                    },
                }
            ],
        }
    )
    teaching = compile_scene(no_formula_trace).frames[0].teaching
    assert teaching is not None
    assert teaching["formula"] == ""
    assert teaching["invariant"] == "队列保持先进先出。"


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

    assert 'id="step-evidence"' in html
    assert 'id="debug-evidence"' in html
    assert "function renderEvidence" in html
    assert "function renderStepEvidence" in html
    assert "function stateDiff" in html
    assert "CorrectnessContract" in html
    assert "Contract tests" in html
    assert "目标写入核对" in html
    assert "seen only contains values from previous indices" in html


def test_renderer_uses_p1_information_architecture(tmp_path: Path):
    out = save_html(fixture_artifact(), tmp_path / "p1_layout.html")
    html = out.read_text(encoding="utf-8")

    assert 'id="top-result"' in html
    assert 'id="top-solution"' in html
    assert 'id="problem-description"' not in html
    assert 'id="input-editor"' not in html
    assert 'id="regeneration-panel"' not in html
    assert ">题目与输入<" not in html
    assert ">修改输入<" not in html
    assert ">输入重新生成<" not in html
    assert ">系统校验<" not in html
    assert 'id="teaching-panel"' in html
    assert 'id="code-panel"' in html
    code_panel_block = html.split('id="code-panel"', 1)[1].split('id="tabs"', 1)[0]
    assert '<h2>代码</h2>' in code_panel_block
    assert 'id="code"' in code_panel_block
    assert "<details" not in code_panel_block
    assert 'class="col task-col"' in html.split('id="code-panel"', 1)[0]
    assert html.index('<h2>代码</h2>') < html.index('<h2>解法</h2>')
    assert ".task-col .code {{" not in html
    assert ".code {{ max-height" not in html
    assert ".teaching-col {{ max-height" not in html
    teaching_col_block = html.split('class="col teaching-col"', 1)[1].split("</aside>", 1)[0]
    assert 'class="compact-details step-evidence-details"' in teaching_col_block
    assert 'class="compact-details step-evidence-details" open' not in teaching_col_block
    assert 'id="step-evidence"' in teaching_col_block
    assert 'id="debug-drawer"' in html
    assert 'id="debug-drawer" open' not in html
    assert html.index('id="teaching-panel"') < html.index('id="debug-drawer"')

    badge_renderer = html.split("function renderBadges()", 1)[1].split("function renderTabs()", 1)[0]
    assert "代码执行通过" in badge_renderer
    assert "轨迹覆盖完整" in badge_renderer
    assert "过程转移通过校验" in badge_renderer
    assert "可视化对象绑定正确" in badge_renderer
    assert "${k}：${v?'通过':'待检查'}" in badge_renderer
    assert "${k}：${v?'PASS':'NO'}" not in badge_renderer


def test_scene_compiler_emits_generic_timeline_evidence():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "通用阶段样例",
            "input_data": {"x": 1},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "dp"}],
                    "state": {"dp": [1, 0], "phase": "初始化"},
                    "reason": "创建 DP 容器。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "set",
                    "targets": [{"id": "dp[1]"}],
                    "deps": [{"id": "dp[0]"}],
                    "state": {"dp": [1, 2]},
                    "role": "answer",
                    "reason": "写入最终答案。",
                    "code_line": 2,
                },
            ],
        }
    )

    scene = compile_scene(trace)

    first_timeline = scene.frames[0].evidence["timeline"]
    second_timeline = scene.frames[1].evidence["timeline"]
    assert first_timeline["phase"] == "初始化"
    assert first_timeline["operation"] == "create"
    assert first_timeline["keyframe"] is True
    assert second_timeline["phase"] == "返回结果"
    assert second_timeline["operation"] == "set"
    assert second_timeline["keyframe"] is True
    assert second_timeline["keyframe_label"] == "写入最终答案。"


def test_scene_compiler_infers_timeline_phase_without_explicit_state_field():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "通用阶段降级",
            "input_data": {"nums": [1, 2]},
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}, {"id": "answer"}],
                    "state": {"nums": [1, 2], "answer": 0},
                    "reason": "准备输入和答案容器。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "nums[0]"}],
                    "state": {"nums": [1, 2], "answer": 0, "i": 0},
                    "role": "candidate",
                    "reason": "进入循环检查当前元素。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "set",
                    "targets": [{"id": "answer"}],
                    "deps": [{"id": "nums[0]"}, {"id": "nums[1]"}],
                    "after": 3,
                    "state": {"nums": [1, 2], "answer": 3, "i": 1},
                    "role": "answer",
                    "reason": "由两个数组元素推出答案。",
                    "code_line": 3,
                },
                {
                    "step": 3,
                    "op": "explain",
                    "targets": [{"id": "answer"}],
                    "state": {"nums": [1, 2], "answer": 3},
                    "role": "answer",
                    "reason": "返回最终答案。",
                    "code_line": 4,
                },
            ],
        }
    )

    phases = [frame.evidence["timeline"]["phase"] for frame in compile_scene(trace).frames]

    assert phases == ["初始化", "主循环", "关键转移", "返回结果"]


def test_renderer_uses_semantic_timeline_with_generic_fallback(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "通用时间线",
            "input_data": {"x": 1},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "dp"}],
                    "state": {"dp": [1, 0], "phase": "初始化"},
                    "reason": "创建 DP 容器。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "dp[0]"}],
                    "state": {"dp": [1, 0]},
                    "reason": "",
                    "code_line": 2,
                },
            ],
        }
    )
    artifact = fixture_artifact().model_copy(deep=True)
    artifact.problem_title = "通用时间线测试"
    artifact.input_data = trace.input_data
    artifact.expected_result = trace.result
    artifact.verifier_result = trace.result
    artifact.variants[0].trace = trace
    artifact.variants[0].result = trace.result
    artifact.scenes = {"dp": compile_scene(trace)}

    out = save_html(artifact, tmp_path / "semantic_timeline.html")
    html = out.read_text(encoding="utf-8")

    assert 'id="timeline" class="timeline" aria-label="语义时间线"' in html
    assert "function timelineMeta" in html
    assert "function fallbackTimelineLabel" in html
    assert "tick-label" in html
    assert "tick-op" in html
    assert "data-step" in html
    assert "data-phase" in html
    assert "aria-label=" in html
    assert "keyframe" in html

    timeline_renderer = html.split("function renderTimeline()", 1)[1].split("function renderState", 1)[0]
    assert "problem_title" not in timeline_renderer
    assert "algorithm" not in timeline_renderer
    assert "meta.phase" in timeline_renderer
    assert "fallbackTimelineLabel(f, i)" in timeline_renderer


def test_tracker_prompt_requests_phase_labels_without_stage_targets():
    prompt = Path("algolab/generation/prompts/tracker_system.txt").read_text(encoding="utf-8")

    assert 'state["phase"]' in prompt or '"phase"' in prompt
    assert "初始化" in prompt
    assert "主循环" in prompt
    assert "关键转移" in prompt
    assert "返回结果" in prompt
    assert "不要发明阶段 target" in prompt


def test_tracker_prompt_requires_accurate_code_lines_for_key_events():
    prompt = Path("algolab/generation/prompts/tracker_system.txt").read_text(encoding="utf-8")

    assert "关键事件" in prompt
    assert "准确 code_line" in prompt
    assert "solve" in prompt
    assert "pseudocode" in prompt
    assert "不要省略 code_line" in prompt
    assert "不要乱填" in prompt


def test_scene_frame_payload_flows_across_core_layouts():
    cases = [
        ("matrix", unique_paths_trace()),
        ("graph", bfs_trace()),
        ("array", two_pointer_trace()),
        ("stack", monotonic_stack_trace()),
        ("map", hash_map_trace()),
    ]

    for expected_layout, trace in cases:
        scene = compile_scene(trace)
        assert scene.frames, expected_layout
        assert any(
            obj.type.value == "container" and obj.meta.get("layout") == expected_layout
            for frame in scene.frames
            for obj in frame.objects
        ), (expected_layout, trace.algorithm)

        for event, frame in zip(trace.events, scene.frames, strict=True):
            assert frame.operation == event.op.value, (expected_layout, event.step)
            assert frame.code_line == event.code_line, (expected_layout, event.step)
            assert frame.description == event.reason, (expected_layout, event.step)
            assert frame.title.strip(), (expected_layout, event.step)
            assert frame.teaching is not None, (expected_layout, event.step)
            assert frame.teaching["what"].strip(), (expected_layout, event.step)
            assert frame.teaching["why"].strip(), (expected_layout, event.step)
            assert frame.evidence["operation"] == event.op.value, (expected_layout, event.step)
            assert frame.evidence["targets"] == [target.id for target in event.targets], (
                expected_layout,
                event.step,
            )
            assert frame.evidence["deps"] == [dep.id for dep in event.deps], (expected_layout, event.step)
            assert frame.evidence["code_line"] == event.code_line, (expected_layout, event.step)
            if event.interaction is not None:
                assert frame.interaction == event.interaction.model_dump(), (expected_layout, event.step)


def test_renderer_declares_scene_frame_payload_fallbacks(tmp_path: Path):
    out = save_html(fixture_artifact(), tmp_path / "payload_fallbacks.html")
    html = out.read_text(encoding="utf-8")

    assert "function frameTitle" in html
    assert "function frameDescription" in html
    assert "function frameOperation" in html
    assert "function frameCodeLine" in html

    render_step = html.split("function renderStep()", 1)[1].split("function markClass", 1)[0]
    assert "frameTitle(f)" in render_step
    assert "frameDescription(f)" in render_step
    assert "frameOperation(f)" in render_step
    assert "codeLineInfo(f, code)" in render_step

    render_step_evidence = html.split("function renderStepEvidence", 1)[1].split("function stateDiff", 1)[0]
    assert "frameOperation(f)" in render_step_evidence
    assert "frameCodeLine(f)" in render_step_evidence


def test_renderer_declares_code_sync_and_line_fallbacks(tmp_path: Path):
    artifact = fixture_artifact().model_copy(deep=True)
    artifact.variants[0].code = "def solve(input_data):\n    return 12"
    scene_id = artifact.variants[0].id
    artifact.scenes[scene_id].frames[0].code_line = 99

    out = save_html(artifact, tmp_path / "code_sync.html")
    html = out.read_text(encoding="utf-8")

    assert ".code-sync" in html
    assert ".line.fallback" in html
    assert "function codeLineInfo" in html
    assert "当前代码行" in html
    assert "code_line 越界" in html
    assert "data-active-line" in html
    assert "data-code-line-status" in html

    render_step = html.split("function renderStep()", 1)[1].split("function markClass", 1)[0]
    assert "const code = variant().code || '';" in render_step
    assert "renderCode(code, codeLineInfo(f, code));" in render_step

    code_info = html.split("function codeLineInfo", 1)[1].split("function markClass", 1)[0]
    assert "f && f.code_line" in code_info
    assert "algorithm" not in code_info
    assert "problem_title" not in code_info
    assert "Math.min(Math.max" in code_info

    render_code = html.split("function renderCode", 1)[1].split("function play", 1)[0]
    assert "info.label" in render_code
    assert "info.active" in render_code
    assert "data-active-line" in render_code
    assert "status === 'ok'" in render_code
    assert "lineActive" in render_code
    assert "fallback" in render_code


def _single_dependency_trace(layout: str) -> SemanticTrace:
    states = {
        "matrix": {
            "state": {"dp": [[1, 1], [1, 2]]},
            "targets": [{"id": "dp[1][1]"}],
            "deps": [{"id": "dp[0][1]"}, {"id": "dp[1][0]"}],
        },
        "graph": {
            "state": {"graph": {"A": ["B"], "B": []}, "dist": {"A": 0, "B": 1}},
            "targets": [{"id": "node:B"}],
            "deps": [{"id": "node:A"}, {"id": "edge:A->B"}],
        },
        "array": {
            "state": {"nums": [1, 3, 5], "answer": [1, 2]},
            "targets": [{"id": "answer[1]"}],
            "deps": [{"id": "nums[1]"}, {"id": "nums[2]"}],
        },
        "stack": {
            "state": {"temperatures": [73, 74], "stack": [0], "answer": [1, 0]},
            "targets": [{"id": "answer[0]"}],
            "deps": [{"id": "stack"}, {"id": "temperatures[1]"}],
        },
        "map": {
            "state": {"nums": [2, 7], "seen": {"2": 0}, "answer": [0, 1]},
            "targets": [{"id": "answer[1]"}],
            "deps": [{"id": "seen[2]"}, {"id": "nums[1]"}],
        },
    }
    case = states[layout]
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": f"{layout} 依赖测试",
            "input_data": {"layout": layout},
            "result": True,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": case["targets"],
                    "deps": case["deps"],
                    "state": case["state"],
                    "role": "answer",
                    "reason": "当前对象由依赖对象推出。",
                    "code_line": 1,
                }
            ],
        }
    )


def test_scene_compiler_compiles_deps_as_dependency_edges_across_core_layouts():
    for layout in ("matrix", "graph", "array", "stack", "map"):
        trace = _single_dependency_trace(layout)
        frame = compile_scene(trace).frames[0]
        deps = [dep.id for dep in trace.events[0].deps]
        targets = [target.id for target in trace.events[0].targets]
        arrows = [obj for obj in frame.objects if obj.type.value == "arrow"]

        assert arrows, layout
        assert {arrow.source for arrow in arrows} == set(deps), layout
        assert {arrow.target for arrow in arrows} == set(targets), layout
        assert all(arrow.role == "dependency" for arrow in arrows), layout
        assert all(any(mark.target == dep and mark.role == "dependency" for mark in frame.marks) for dep in deps), layout
        assert frame.evidence["deps"] == deps, layout
        assert frame.evidence["targets"] == targets, layout


def test_renderer_declares_structured_dependency_flow(tmp_path: Path):
    out = save_html(fixture_artifact(), tmp_path / "dependency_flow.html")
    html = out.read_text(encoding="utf-8")

    assert "function renderDependencyFlow" in html
    assert "function dependencyEdges" in html
    assert "function dependencyLabel" in html
    assert "function objectById" in html
    assert "dependency-flow" in html
    assert "dependency-edge" in html
    assert "data-source" in html
    assert "data-target" in html

    renderer = html.split("function renderDependencyFlow", 1)[1].split("function renderSpatialCanvas", 1)[0]
    assert "ARTIFACT" not in renderer
    assert "algorithm" not in renderer
    assert "problem_title" not in renderer
    assert "o.type === 'arrow'" in renderer
    assert "f.evidence" in renderer
    assert "→" in renderer


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


def test_tracker_prompt_requires_teaching_and_complete_key_set_events():
    prompt = Path("algolab/generation/prompts/tracker_system.txt").read_text(encoding="utf-8")

    assert "teaching" in prompt
    assert "每个关键事件" in prompt
    assert "what" in prompt and "why" in prompt
    assert "关键 set 事件" in prompt
    for field in ("deps", "value", "state", "reason", "code_line"):
        assert field in prompt
    assert "禁止旧字段" in prompt
    assert "type" in prompt and "target" in prompt
    assert "旧式 map target" in prompt
    assert "seen:2" in prompt and "dist:A" in prompt


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


def test_solution_repair_context_classifies_failure_types_and_step_targets():
    request = ProblemInput(problem="不同路径", input_data={"m": 2, "n": 2}, expected_result=2)
    previous = {"variants": [{"id": "dp", "name": "DP", "code": "", "tracker_code": ""}]}
    captured: dict[str, str] = {}

    def fake_chat_json(_system_prompt, user_prompt):
        captured["prompt"] = user_prompt
        return {
            "problem_title": "x",
            "input_contract": "",
            "variants": [{"id": "x", "name": "x", "code": "", "tracker_code": ""}],
            "verifier_code": "",
        }

    original = solution_generator.chat_json
    solution_generator.chat_json = fake_chat_json
    try:
        solution_generator.repair_solution_spec(
            request,
            previous,
            [
                "ValidationError: events[0].targets Field required",
                "第 3 步旧式 map target 已废弃，请使用方括号格式：seen:2",
                "第 4 步 dp[1][1] 不满足不同路径转移",
                "failure_type=coverage_error: BFS 小图缺少关键步骤覆盖：check_edge",
                "第 2 帧没有可见对象",
            ],
        )
    finally:
        solution_generator.chat_json = original

    prompt = captured["prompt"]
    assert "结构化错误上下文" in prompt
    assert "schema_error" in prompt
    assert "target_error" in prompt
    assert "process_error" in prompt
    assert "coverage_error" in prompt
    assert "scene_error" in prompt
    assert '"step": 3' in prompt
    assert '"target": "seen:2"' in prompt
    assert '"target": "dp[1][1]"' in prompt


def test_llm_benchmark_report_summarizes_repair_failure_type_transitions():
    import tempfile

    args = argparse.Namespace(
        case=["unique_paths"],
        sample=0,
        all_samples=False,
        solutions=1,
        max_rounds=2,
        timeout_s=1,
        strict_warnings=True,
        browser_smoke=False,
        write_each=True,
        concurrency=1,
    )
    with tempfile.TemporaryDirectory() as d:
        report_path = llm_benchmark.write_report(
            [
                {
                    "case_id": "unique_paths",
                    "title": "不同路径",
                    "family": "二维 DP",
                    "sample_index": 0,
                    "ok": True,
                    "errors": [],
                    "repair_failure_types": ["schema_error", "coverage_error"],
                    "duration_s": 1.0,
                },
                {
                    "case_id": "graph_bfs",
                    "title": "图 BFS",
                    "family": "BFS",
                    "sample_index": 0,
                    "ok": False,
                    "errors": ["第 2 帧没有可见对象"],
                    "repair_failure_types": ["target_error"],
                    "duration_s": 2.0,
                },
            ],
            Path(d),
            args=args,
            started_at="2026-01-01T00:00:00",
            ended_at="2026-01-01T00:00:03",
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["repair_failure_summary"] == {"schema_error": 1, "coverage_error": 1, "target_error": 1}
    assert report["results"][0]["repair_failure_types"] == ["schema_error", "coverage_error"]


def test_llm_benchmark_failed_run_preserves_repair_failure_types():
    args = argparse.Namespace(
        solutions=1,
        max_rounds=1,
        output_dir=Path("output/offline_regression"),
        strict_warnings=True,
    )
    case = benchmark_cases()[0]
    sample = case.samples[0]
    original = llm_benchmark.build_artifact_timed

    def fake_build_artifact_timed(_request, **kwargs):
        repair_types = kwargs["repair_failure_types_out"]
        repair_types.extend(["schema_error", "target_error"])
        raise RuntimeError("repair failed")

    llm_benchmark.build_artifact_timed = fake_build_artifact_timed
    try:
        result = llm_benchmark.run_one(case, sample, 0, args)
    finally:
        llm_benchmark.build_artifact_timed = original

    assert result["ok"] is False
    assert result["repair_failure_types"] == ["schema_error", "target_error"]


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
            "algorithm": "bracket target",
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
    assert "dist:B" not in ids


def test_trace_validator_rejects_legacy_map_colon_targets():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "legacy map target",
            "input_data": {},
            "result": None,
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "seen:2"}],
                    "deps": [{"id": "map:seen"}],
                    "state": {"seen": {"2": 0}},
                    "reason": "旧式 map target。",
                    "code_line": 1,
                }
            ],
        }
    )

    errors, _warnings = validate_trace(trace)

    assert any("旧式 map target" in error for error in errors), errors


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


def test_execute_variant_rejects_quoted_map_targets():
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
    try:
        materialized = execute_variant(variant, {})
        assert materialized.trace is not None
        errors, _warnings = validate_trace(materialized.trace)
    except Exception as exc:
        assert "seen['2']" in str(exc) or "map target" in str(exc)
    else:
        assert any("map target" in error for error in errors), errors


def test_execute_variant_preserves_long_trace_events():
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
            "      'events': [{'step': i, 'op': 'explain', 'targets': [], 'state': {'i': i}, 'reason': 'x', 'code_line': 1} for i in range(81)]\n"
            "    }\n"
        ),
    )
    materialized = execute_variant(variant, {})

    assert materialized.trace is not None
    assert len(materialized.trace.events) == 81


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
                    "deps": [{"id": "seen"}],
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


def test_process_validation_registry_declares_core_families():
    registry = {profile.family: profile for profile in process_validation_registry()}
    required = {"dp", "bfs", "binary_search", "monotonic_stack", "hash", "tree", "union_find"}

    assert required <= set(registry)
    for family in required:
        profile = registry[family]
        assert profile.coverage_rule
        assert profile.failure_type
        assert profile.status in {"strong", "fallback"}
        if profile.status == "strong":
            assert profile.checks, family
        else:
            assert profile.checks == ()
            assert profile.failure_type in {"process_fallback", "process_uncovered"}

    assert process_validation_profile_for_family("二维 DP").family == "dp"
    assert process_validation_profile_for_family("BFS/DFS 基础图").family == "bfs"
    assert process_validation_profile_for_family("栈 / 队列 / 单调栈").family == "monotonic_stack"
    hash_profile = process_validation_profile_for_family("哈希表 / map")
    assert hash_profile.family == "hash"
    assert hash_profile.status == "strong"
    assert "_validate_hash_map_process" in hash_profile.checks
    assert process_validation_profile_for_family("树 / BST / LCA").family == "tree"
    assert process_validation_profile_for_family("并查集").family == "union_find"


def test_process_validation_unknown_family_uses_fallback_not_strong_validation():
    profile = process_validation_profile_for_family("未注册算法族")

    assert profile.family == "uncovered"
    assert profile.status == "fallback"
    assert profile.checks == ()
    assert profile.coverage_rule == "基础 schema / scene / answer gate；不声明算法族强过程不变量"
    assert profile.failure_type == "process_uncovered"


def test_process_registry_does_not_replace_blocking_errors():
    profile = process_validation_profile_for_family("二维 DP")
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

    assert profile.status == "strong"
    assert any("不同路径转移" in e for e in errors), errors


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


def test_process_validator_rejects_bad_unique_paths_dependencies():
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
                    "deps": [{"id": "dp[0][0]"}, {"id": "dp[1][0]"}],
                    "state": {"dp": [[1, 1], [1, 2]]},
                    "reason": "值正确但依赖来源写错。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(trace)
    assert any("dp[1][1] 依赖应为" in e for e in errors), errors


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


def test_process_validator_rejects_bad_bfs_discovery_parent():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "BFS",
            "input_data": {"graph": {"A": ["B"], "B": []}, "start": "A"},
            "result": {"A": 0, "B": 1},
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "node:B"}],
                    "deps": [{"id": "node:C"}],
                    "state": {"graph": {"A": ["B"], "B": []}, "queue": ["B"], "dist": {"A": 0, "B": 1}, "parent": {"B": "C"}},
                    "role": "visited",
                    "reason": "距离正确但首次发现来源错误。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(trace)
    assert any("BFS 首次发现 node:B 来源" in e for e in errors), errors


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


def test_process_validator_rejects_binary_search_wrong_shrink_direction():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分",
            "input_data": {"nums": [1, 3, 5], "target": 5},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "compare",
                    "targets": [{"id": "nums[1]"}, {"id": "pointer:mid"}],
                    "state": {"nums": [1, 3, 5], "left": 0, "right": 2, "mid": 1, "target": 5},
                    "value": 1,
                    "reason": "mid 值小于 target。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "move",
                    "targets": [{"id": "pointer:left"}, {"id": "pointer:right"}],
                    "state": {"nums": [1, 3, 5], "left": 0, "right": 0, "target": 5},
                    "value": [0, 0],
                    "reason": "错误地向左收缩，丢掉目标所在半区。",
                    "code_line": 2,
                },
            ],
        }
    )
    errors, _warnings = validate_process(trace)
    assert any("二分收缩方向错误" in e for e in errors), errors


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


def test_process_validator_rejects_union_find_link_without_connected_roots():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "省份数量",
            "input_data": {"isConnected": [[1, 1], [1, 1]]},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "link",
                    "targets": [{"id": "node:0"}],
                    "deps": [{"id": "node:1"}],
                    "state": {"isConnected": [[1, 1], [1, 1]], "union_find": {"parent": {"0": "0", "1": "1"}}, "i": 0, "j": 1},
                    "reason": "声称 union，但 parent 没有把两个连通城市合并。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(trace)
    assert any("union 后 0 和 1 应连通" in e for e in errors), errors


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

    answer_trace_bad = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "每日温度",
            "input_data": {"temperatures": [73, 74]},
            "result": [1, 0],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "answer[0]"}],
                    "deps": [{"id": "temperatures[0]"}, {"id": "temperatures[0]"}],
                    "after": 0,
                    "state": {"temperatures": [73, 74], "stack": [], "answer": [0, 0], "stack_order": "decreasing", "i": 1},
                    "role": "answer",
                    "reason": "弹出后写入了错误等待天数。",
                    "code_line": 1,
                }
            ],
        }
    )
    errors, _warnings = validate_process(answer_trace_bad)
    assert any("answer[0] 应为 1" in e for e in errors), errors

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


def _tree_with_recursion_trace() -> SemanticTrace:
    tree = {
        "nodes": [{"id": "4"}, {"id": "2"}, {"id": "7"}],
        "edges": [["4", "2"], ["4", "7"]],
    }
    search_tree = {
        "nodes": [{"id": "dfs4", "label": "dfs(4)"}, {"id": "dfs2", "label": "dfs(2)"}],
        "edges": [["dfs4", "dfs2"]],
    }
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "树递归复合视图",
            "input_data": {"root": 4},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "enter",
                    "targets": [{"id": "node:2"}],
                    "deps": [{"id": "node:4"}],
                    "state": {
                        "tree": tree,
                        "recursion_tree": search_tree,
                        "stack": ["dfs(4)", "dfs(2)"],
                    },
                    "role": "current",
                    "reason": "在原树上进入左子节点，同时展示递归搜索树和调用栈。",
                    "code_line": 1,
                }
            ],
        }
    )


def test_scene_compiler_preserves_compound_visual_primitives_for_core_examples():
    cases = [
        ("bfs", bfs_trace(), ("graph", "queue", "map")),
        ("monotonic_stack", monotonic_stack_trace(), ("array", "stack")),
        ("tree_recursion", _tree_with_recursion_trace(), ("tree", "recursion_tree", "stack")),
        ("heap_array", topk_heap_trace(), ("array", "heap")),
    ]
    for case_id, trace, expected_layouts in cases:
        scene = compile_scene(trace)
        frame_layouts = [
            {
                obj.meta.get("layout")
                for obj in frame.objects
                if obj.type.value == "container"
            }
            for frame in scene.frames
        ]
        assert any(set(expected_layouts).issubset(layouts) for layouts in frame_layouts), (
            case_id,
            expected_layouts,
            frame_layouts,
        )


def test_renderer_declares_compound_primitive_layout(tmp_path: Path):
    out = save_html(fixture_artifact(), tmp_path / "compound_primitives.html")
    html = out.read_text(encoding="utf-8")

    assert "function renderPrimitivePanel" in html
    assert "function primitivePanelClass" in html
    assert "compound-scene" in html
    assert "primitive-panel" in html
    assert "data-layout" in html

    renderer = html.split("function renderTeachingCanvas", 1)[1].split("function renderDependencyFlow", 1)[0]
    render_canvas_block = html.split("function renderTeachingCanvas", 1)[1].split("function familyRendererForFrame", 1)[0]
    assert "algorithm" not in renderer
    assert "problem_title" not in renderer
    assert "function renderSemanticAnchorBand" in renderer
    assert "renderSemanticAnchorBand(f)" not in render_canvas_block
    assert "renderPrimitivePanel(c, groups[c.id] || [], marks, 'primary')" in renderer


def test_renderer_declares_phase1_primary_stage_fit_and_raw_state_policy(tmp_path: Path):
    out = save_html(phase17_visual_pattern_artifact(), tmp_path / "phase1_visual_policy.html")
    html = out.read_text(encoding="utf-8")

    for marker in (
        "function classifyStageContainers",
        "function stageRoleForContainer",
        "function renderPrimaryStage",
        "function renderSupportDock",
        "function renderRawStateDock",
        "function fitModeForFrame",
        "function measureVisualBounds",
        "function bindScenePanZoom",
        "function resetSceneView",
        "function syncSceneScrollSurface",
        "gcd-hero",
        "function scrollFocusedTarget",
        "function clampNumber",
        "primary-scene",
        "scene-scroll-surface",
        "scene-world",
        "support-dock",
        "raw-state-dock",
        "scroll-fit",
        "pan-scroll",
        "data-stage-role",
        "data-fit-mode",
        "raw_state_not_primary",
        "teaching_relation_visible",
    ):
        assert marker in html

    assert "height:clamp(460px,64vh,700px)" in html
    assert "grid-template-rows:minmax(340px,1fr) minmax(96px,168px)" in html
    assert "const minReadableScale = 1" in html
    assert "const maxUsefulScale = 1.85" in html
    assert "translate(" in html

    render_block = html.split("function renderTeachingCanvas", 1)[1].split("function fitSceneToCanvas", 1)[0]
    render_canvas_block = html.split("function renderTeachingCanvas", 1)[1].split("function familyRendererForFrame", 1)[0]
    assert "classifyStageContainers(f, containers)" in render_block
    assert "scene-scroll-surface" in render_block
    assert "scene-world" in render_block
    assert "renderPrimaryStage(classified.primary" in render_block
    assert "renderSupportDock(classified.support" in render_block
    assert "renderRawStateDock(classified.raw" in render_block
    assert "renderAnswerBadge(f)" not in render_canvas_block
    assert "renderSemanticAnchorBand(f)" not in render_canvas_block
    assert "containers.length > 1" not in render_block
    assert "algorithm" not in render_block
    assert "problem_title" not in render_block

    classifier_block = html.split("function classifyStageContainers", 1)[1].split("function renderPrimaryStage", 1)[0]
    assert "LAYOUT_RENDERERS" in classifier_block
    assert "capacity" in classifier_block
    assert "flow" in classifier_block
    assert "memo" in classifier_block
    assert "call_stack" in classifier_block
    assert "query_path" in classifier_block
    assert "raw" in classifier_block
    assert "support" in classifier_block
    assert "primary" in classifier_block
    assert "algorithm" not in classifier_block
    assert "problem_title" not in classifier_block

    fit_block = html.split("function fitSceneToCanvas", 1)[1].split("function renderPrimitivePanel", 1)[0]
    assert "rawScale" in fit_block
    assert "needsReadableFallback" in fit_block
    assert "effectiveFitMode" in fit_block
    assert "measureVisualBounds(scene)" in fit_block
    assert "bounds.left" in fit_block
    assert "bounds.top" in fit_block
    assert "const scrollFit = needsReadableFallback" in fit_block
    assert "scrollFit ? 'pan-scroll' : 'contain'" in fit_block
    assert "clampNumber(rawScale, minContainScale" in fit_block
    assert "fit.classList.toggle('scroll-fit'" in fit_block
    assert "fit.classList.toggle('pan-scroll'" in fit_block
    assert "scrollFocusedTarget(fit, scene)" in fit_block
    assert "translateX" in fit_block and "translateY" in fit_block
    assert "scene.dataset.fitMode" in fit_block
    assert "scene.dataset.cameraMode" in fit_block
    assert "scene.dataset.utilization" in fit_block
    assert "scene.dataset.visualBoundsWidth" in fit_block
    assert "const scale = Math.min(1, availableWidth / contentWidth" not in fit_block


def test_renderer_declares_linked_list_and_math_bit_primitives(tmp_path: Path):
    out = save_html(phase17_visual_pattern_artifact(), tmp_path / "family_primitives.html")
    html = out.read_text(encoding="utf-8")

    for marker in (
        "function renderLinkedList",
        "function linkedListPointers",
        "function renderMathBitPanel",
        "function mathBitItems",
        "function renderBitRows",
        "linked-list-view",
        "linked-node",
        "linked-arrow",
        "pointer-badge",
        "math-bit-panel",
        "bit-row",
        "gcd-chain",
        "fast-power-row",
        "sieve-grid",
    ):
        assert marker in html

    assert '"linked_list": "linked_list"' in html
    assert "if (renderer === 'linked_list') return renderLinkedList" in html
    assert "renderMathBitPanel(f)" in html

    linked_block = html.split("function renderLinkedList", 1)[1].split("function renderMathBitPanel", 1)[0]
    assert "prev" in linked_block
    assert "curr" in linked_block
    assert "next" in linked_block
    assert "old_direction" in linked_block
    assert "cycle" in linked_block
    assert "algorithm" not in linked_block
    assert "problem_title" not in linked_block

    math_block = html.split("function renderMathBitPanel", 1)[1].split("function renderTimeline", 1)[0]
    assert "gcd" in math_block
    assert "lowbit" in math_block
    assert "fast_power" in math_block
    assert "sieve" in math_block
    assert "state" in math_block
    assert "algorithm" not in math_block
    assert "problem_title" not in math_block


def test_renderer_declares_rich_object_detail_payload(tmp_path: Path):
    out = save_html(phase17_visual_pattern_artifact(), tmp_path / "object_detail.html")
    html = out.read_text(encoding="utf-8")

    detail_block = html.split("function showDependencyDetail", 1)[1].split("function unique", 1)[0]
    for marker in (
        "objectContainerInfo",
        "eventChangeRows",
        "before",
        "after",
        "所属容器",
        "layout",
        "值",
        "角色",
    ):
        assert marker in detail_block

    assert "function objectContainerInfo" in html


def test_renderer_declares_algorithm_family_semantic_primitives(tmp_path: Path):
    out = save_html(phase17_visual_pattern_artifact(), tmp_path / "family_semantic_primitives.html")
    html = out.read_text(encoding="utf-8")

    for marker in (
        "function renderBinaryPointerPattern",
        "function renderDigitDpPattern",
        "function renderMonotonicStackPattern",
        "function renderHeapSiftPattern",
        "function renderGraphMetricOverlay",
        "function renderTreeDpOverlay",
        "binary-pointer-panel",
        "search-interval-band",
        "marker-low",
        "marker-mid",
        "marker-high",
        "digit-dp-card",
        "digit-dp-state",
        "monotonic-stack-panel",
        "stack-pop-arrow",
        "heap-sift-panel",
        "heap-sift-path",
        "graph-metric-overlay",
        "graph-node-metric",
        "relax-formula",
        "frontier-dock",
        "tree-dp-overlay",
        "tree-dp-badge",
    ):
        assert marker in html

    visual_block = html.split("function renderVisualPatternPanel", 1)[1].split("function renderDependencyFlow", 1)[0]
    for helper in (
        "renderBinaryPointerPattern(f)",
        "renderDigitDpPattern(f)",
        "renderMonotonicStackPattern(f)",
        "renderHeapSiftPattern(f)",
        "renderGraphMetricOverlay(f)",
        "renderTreeDpOverlay(f)",
    ):
        assert helper in visual_block
    assert "problem_title" not in visual_block
    assert "algorithm" not in visual_block
    assert "ARTIFACT" not in visual_block


def test_renderer_declares_specialized_family_teaching_primitives(tmp_path: Path):
    out = save_html(phase17_visual_pattern_artifact(), tmp_path / "specialized_family_primitives.html")
    html = out.read_text(encoding="utf-8")

    for marker in (
        "function renderDpDependencyWindowPattern",
        "function renderStringSpecializedPattern",
        "function renderFenwickLowbitPattern",
        "function renderSparseTableBlocksPattern",
        "function renderDiffPrefixPattern",
        "function renderGeometryRelationPattern",
        "function renderNetworkFlowAugmentingPathPattern",
        "function renderVisualQualityTelemetry",
        "function updateVisualQualityTelemetry",
        "function familyRendererForFrame",
        "function graphNodeMetricText",
        "dp-dependency-window",
        "dp-current-cell",
        "dp-dependency-arrow",
        "string-specialized-card",
        "kmp-fallback-arc",
        "rolling-hash-track",
        "z-box-band",
        "manacher-radius-arc",
        "fenwick-lowbit-panel",
        "fenwick-hop-arrow",
        "sparse-table-blocks",
        "sparse-query-block",
        "diff-prefix-panel",
        "geometry-relation-card",
        "cross-turn-badge",
        "geo-cross-arrow",
        "geo-candidate-point",
        "geo-hull-ghost-svg",
        "hull-ghost-point",
        "network-augmenting-path-panel",
        "augmenting-path-chain",
        "bottleneck-badge",
        "bitmask-transition-panel",
        "kruskal-track-panel",
        "flow-bottleneck-label",
        "flow-delta-row",
        "graph-node-inline-metrics",
        "visual-quality-telemetry",
        "fit_mode=",
        "fit_scale=",
        "utilization=",
        "data-visual-quality",
        "data-family-renderer",
    ):
        assert marker in html

    render_block = html.split("function renderTeachingCanvas", 1)[1].split("function classifyStageContainers", 1)[0]
    assert "renderVisualQualityTelemetry(f, classified)" in render_block
    assert "data-family-renderer" in render_block

    visual_block = html.split("function renderVisualPatternPanel", 1)[1].split("function renderDependencyFlow", 1)[0]
    for helper in (
        "renderDpDependencyWindowPattern(f)",
        "renderStringSpecializedPattern(f)",
        "renderFenwickLowbitPattern(f)",
        "renderSparseTableBlocksPattern(f)",
        "renderDiffPrefixPattern(f)",
        "renderGeometryRelationPattern(f)",
        "renderNetworkFlowAugmentingPathPattern(f)",
        "renderBitmaskTransitionPattern(f)",
        "renderKruskalTrackPattern(f)",
    ):
        assert helper in visual_block
    assert "problem_title" not in visual_block
    assert "algorithm" not in visual_block
    assert "ARTIFACT" not in visual_block


def test_phase5_renderer_visual_audit_script_declares_current_renderer_quality_gate():
    script_path = Path("scripts/audit_renderer_visual_quality.py")
    assert script_path.exists()
    source = script_path.read_text(encoding="utf-8")

    for marker in (
        "BuildArtifact.model_validate_json",
        "save_html(artifact",
        "sample_frame_indices",
        "first",
        "middle",
        "last",
        "main_stage_utilization",
        "visual_bounds_left",
        "primary_visible_ratio",
        "primary_clip_detected",
        "multi_primary_fit_mode",
        "answer_primary_area_ratio",
        "graph_node_min_radius",
        "svg_occupied_ratio",
        "active_target_visible",
        "readable_scale",
        "dependency_visible",
        "code_line_status_visible",
        "no_major_overflow",
        "timeline_keyframes_visible",
        "raw_state_not_primary",
        "teaching_relation_visible",
        "fixed_overlay_blocks_primary",
        "aggregateRects",
        "primaryRects",
        "family_renderer_used",
        "multi_primary_focus",
        "answer_steals_primary",
        "graph_node_too_small",
        "fixed_overlay_blocks_primary",
        "quality_summary",
        "low_utilization_ratio",
        "failure_categories",
        "renderer_visual_quality_audit.json",
    ):
        assert marker in source
    assert "MIN_READABLE_SCALE = 1.0" in source
    assert "fitScale >= 1.0" in source


def test_phase5_renderer_visual_audit_collects_only_build_artifacts(tmp_path: Path):
    from scripts.audit_renderer_visual_quality import collect_artifact_paths

    artifact_path = tmp_path / "case.json"
    artifact_path.write_text('{"schema_version":"algolab-build-v1"}', encoding="utf-8")
    summary_path = tmp_path / "family_summary.json"
    summary_path.write_text('{"kind":"llm_family_summary"}', encoding="utf-8")
    broken_path = tmp_path / "broken.json"
    broken_path.write_text('{', encoding="utf-8")

    assert collect_artifact_paths(tmp_path, "*.json") == [artifact_path]


def test_phase5_renderer_visual_audit_rerenders_with_current_compiler(tmp_path: Path):
    from scripts.audit_renderer_visual_quality import rerender_artifacts

    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "图重编译",
            "input_data": {},
            "result": ["A", "B"],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "graph"}],
                    "state": {
                        "graph": {
                            "nodes": ["A", "B"],
                            "edges": [{"u": "A", "v": "B"}],
                            "directed": True,
                        }
                    },
                    "reason": "初始化 node/edge 图。",
                    "code_line": 1,
                }
            ],
        }
    )
    stale_scene = SceneGraph(
        algorithm="旧图",
        input_data={},
        frames=[
            {
                "step": 0,
                "title": "旧图",
                "description": "旧 compiler 把 nodes/edges 字段误当作普通图节点。",
                "operation": "create",
                "objects": [
                    {"id": "graph", "type": "container", "label": "graph", "meta": {"layout": "graph"}},
                    {"id": "node:nodes", "type": "node", "label": "nodes", "parent": "graph"},
                    {"id": "node:edges", "type": "node", "label": "edges", "parent": "graph"},
                    {
                        "id": "edge:nodes->A",
                        "type": "edge",
                        "source": "node:nodes",
                        "target": "node:A",
                        "parent": "graph",
                    },
                ],
            }
        ],
    )
    artifact = BuildArtifact(
        problem_title="图重编译审计",
        input_data={},
        variants=[
            {
                "id": "graph_variant",
                "name": "图解法",
                "strategy": "审计应使用当前 compiler。",
                "code": "def solve(input_data):\n    return ['A', 'B']",
                "tracker_code": "def trace(input_data):\n    return {}",
                "result": trace.result,
                "trace": trace.model_dump(),
            }
        ],
        scenes={"graph_variant": stale_scene},
        validation=ValidationReport(checks=["fixture"]),
    )
    artifact_path = tmp_path / "stale_graph.json"
    artifact_path.write_text(artifact.model_dump_json(), encoding="utf-8")

    records = rerender_artifacts([artifact_path], tmp_path / "html")
    html = Path(records[0]["html"]).read_text(encoding="utf-8")

    assert records[0]["rerendered_with_current_compiler"] is True
    assert "node:A" in html
    assert "edge:A-&gt;B" in html or "edge:A->B" in html
    assert "node:nodes" not in html
    assert "edge:nodes-&gt;A" not in html


def test_phase5_renderer_visual_audit_checks_primary_stability_within_timeline_phase():
    from scripts.audit_renderer_visual_quality import add_primary_container_stability

    rows = [
        {
            "case_id": "phase_switch_case",
            "variant_id": "v1",
            "timeline_phase": "初始化",
            "primary_rect": {"area": 100.0},
            "failure_categories": [],
        },
        {
            "case_id": "phase_switch_case",
            "variant_id": "v1",
            "timeline_phase": "主循环",
            "primary_rect": {"area": 1000.0},
            "failure_categories": [],
        },
    ]

    add_primary_container_stability(rows)

    assert all(row["primary_container_stable"] is True for row in rows)
    assert all("primary_container_unstable" not in row["failure_categories"] for row in rows)


def test_phase5_renderer_visual_audit_accepts_specialized_family_subrenderers():
    source = Path("scripts/audit_renderer_visual_quality.py").read_text(encoding="utf-8")

    family_block = source.split("function familyRendererMatches", 1)[1].split("function selectorForExpectedFamily", 1)[0]

    for marker in (
        "expected === 'string_specialized' && ['string_specialized','string_list','trie']",
        "expected === 'trie' && ['trie','tree','string_specialized']",
        "expected === 'graph' && ['graph','dp_matrix']",
        "expected === 'kruskal' && ['kruskal','graph']",
        "expected === 'bitmask_dp' && ['bitmask_dp','dp_matrix','math_bit']",
        "expected === 'digit_dp' && actual === 'digit_dp'",
        "expected === 'heap' && actual === 'heap'",
        "expected === 'monotonic_stack' && actual === 'monotonic_stack'",
    ):
        assert marker in family_block


def test_renderer_and_audit_use_semantic_target_proxy_for_focus(tmp_path: Path):
    out = save_html(phase17_visual_pattern_artifact(), tmp_path / "semantic_target_proxy.html")
    html = out.read_text(encoding="utf-8")
    audit_source = Path("scripts/audit_renderer_visual_quality.py").read_text(encoding="utf-8")

    for marker in (
        "function sceneObjectBySemanticId",
        "function semanticProxyIds",
        "semantic-anchor-band",
        "semantic-anchor-chip",
        "frameMatch",
        "node:${frameMatch[1]}",
        "answer' || String(id) === 'result",
        "semanticFallbackObject",
        "answerStateProxySelectors",
        "framePhaseMatch",
        "localStateCellProxy",
        "primaryLinearContainerId",
        ".answer-badge[data-object-id]",
    ):
        assert marker in html
    for marker in (
        "sceneObjectBySemanticIdInAudit",
        "semanticProxyIdsInAudit",
        "document.querySelector('#canvas .primary-scene')",
        "semantic-anchor-chip",
        "node:${frameMatch[1]}",
        "semanticFallbackObjectInAudit",
        "answerStateProxySelectorsInAudit",
        "framePhaseMatch",
        "localStateCellProxyInAudit",
        "primaryLinearContainerIdInAudit",
        ".answer-badge[data-object-id]",
    ):
        assert marker in audit_source
    answer_selector_block = html.split("function answerStateProxySelectors", 1)[1].split("function semanticProxyIds", 1)[0]
    audit_answer_selector_block = audit_source.split("function answerStateProxySelectorsInAudit", 1)[1].split("function aggregateRects", 1)[0]
    assert 'primary-scene [data-stage-role="primary"]' not in answer_selector_block
    assert 'primary-scene [data-stage-role="primary"]' not in audit_answer_selector_block


def test_scene_compiler_handles_node_edge_graph_dict_without_pseudo_nodes():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "图结构",
            "input_data": {},
            "result": {"A": 0, "B": 1},
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "graph"}],
                    "state": {
                        "graph": {
                            "nodes": ["A", "B"],
                            "edges": [{"u": "A", "v": "B", "weight": 3}],
                            "directed": True,
                        }
                    },
                    "reason": "初始化图。",
                    "code_line": 1,
                }
            ],
        }
    )
    scene = compile_scene(trace)
    frame = scene.frames[0]
    object_ids = {obj.id for obj in frame.objects}
    graph_edges = [obj for obj in frame.objects if obj.type.value == "edge"]

    assert {"graph", "node:A", "node:B", "edge:A->B"}.issubset(object_ids)
    assert "node:nodes" not in object_ids
    assert "node:edges" not in object_ids
    assert "edge:nodes->A" not in object_ids
    assert len(graph_edges) == 1
    assert graph_edges[0].label == "3"


def test_scene_compiler_converts_list_dict_to_linked_list_primitive():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "反转链表",
            "input_data": {},
            "result": [2, 1],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "list"}],
                    "state": {
                        "list": {
                            "head": 0,
                            "nodes": [
                                {"id": 0, "value": 1, "next": 1},
                                {"id": 1, "value": 2, "next": None},
                            ],
                        }
                    },
                    "reason": "初始化链表。",
                    "code_line": 1,
                }
            ],
        }
    )
    scene = compile_scene(trace)
    frame = scene.frames[0]
    by_id = {obj.id: obj for obj in frame.objects}

    assert by_id["list"].meta.get("layout") == "linked_list"
    assert by_id["node:0"].label == "1"
    assert by_id["node:1"].label == "2"
    assert by_id["edge:0->1"].source == "node:0"
    assert by_id["edge:0->1"].target == "node:1"


def test_scene_compiler_projects_graph_answer_to_primary_nodes_and_edges():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "图答案投影",
            "input_data": {},
            "result": {"articulation": ["B"], "bridges": [["A", "B"]]},
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "answer"}],
                    "state": {
                        "graph": {
                            "nodes": ["A", "B"],
                            "edges": [{"u": "A", "v": "B"}],
                        },
                        "answer": {"articulation": ["B"], "bridges": [["A", "B"]]},
                    },
                    "role": "answer",
                    "reason": "返回最终答案。",
                    "code_line": 1,
                }
            ],
        }
    )
    frame = compile_scene(trace).frames[0]
    by_id = {obj.id: obj for obj in frame.objects}

    assert "answer_projection" in by_id["node:B"].meta.get("visual_patterns", [])
    assert by_id["node:B"].meta.get("pattern_role") == "answer"
    assert "answer_projection" in by_id["edge:A->B"].meta.get("visual_patterns", [])
    assert by_id["edge:A->B"].meta.get("pattern_role") == "answer"
    assert {"node:B", "edge:A->B"}.issubset(set(frame.evidence["visual_patterns"][0]["objects"]) | {
        obj_id
        for pattern in frame.evidence["visual_patterns"]
        if pattern["pattern"] == "answer_projection"
        for obj_id in pattern["objects"]
    })


def test_scene_compiler_handles_localized_node_edge_graph_dict():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Kruskal 最小生成树",
            "input_data": {},
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "网络图"}],
                    "state": {
                        "网络图": {
                            "nodes": ["A", "B", "C"],
                            "edges": [
                                {"u": "A", "v": "B", "weight": 1},
                                {"u": "B", "v": "C", "weight": 2},
                            ],
                            "directed": False,
                        }
                    },
                    "reason": "初始化图。",
                    "code_line": 1,
                }
            ],
        }
    )
    frame = compile_scene(trace).frames[0]
    by_id = {obj.id: obj for obj in frame.objects}

    assert by_id["网络图"].meta.get("layout") == "graph"
    assert {"node:A", "node:B", "node:C", "edge:A->B", "edge:B->C"}.issubset(by_id)
    assert "node:nodes" not in by_id
    assert "edge:nodes->A" not in by_id


def test_scene_compiler_projects_adjacency_matrix_to_graph_for_province_style_state():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "省份数量",
            "input_data": {},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "isConnected"}],
                    "state": {"isConnected": [[1, 1, 0], [1, 1, 0], [0, 0, 1]]},
                    "reason": "初始化邻接矩阵。",
                    "code_line": 1,
                }
            ],
        }
    )
    frame = compile_scene(trace).frames[0]
    graph = next(obj for obj in frame.objects if obj.id == "isConnected:graph")
    edge_ids = {obj.id for obj in frame.objects if obj.type.value == "edge"}

    assert graph.meta.get("layout") == "graph"
    assert "adjacency_matrix_projection" in graph.meta.get("visual_patterns", [])
    assert "edge:0->1" in edge_ids or "edge:1->0" in edge_ids


def test_scene_compiler_converts_localized_point_sets_to_geometry_primitive():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "凸包",
            "input_data": {},
            "result": [[0, 0], [2, 0]],
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "当前凸壳"}],
                    "state": {
                        "点集": [[0, 0], [1, 1], [1, 2], [2, 0]],
                        "当前凸壳": [[0, 0], [2, 0]],
                    },
                    "reason": "维护当前凸壳。",
                    "code_line": 1,
                }
            ],
        }
    )
    frame = compile_scene(trace).frames[0]
    by_id = {obj.id: obj for obj in frame.objects}

    assert by_id["点集"].meta.get("layout") == "geometry"
    assert by_id["当前凸壳"].meta.get("layout") == "geometry"
    assert "point:0" in by_id
    assert "hull:0->1:0" in by_id
    assert by_id["hull:0->1:0"].source == "point:0"
    assert by_id["hull:0->1:0"].target == "point:1"


def test_scene_compiler_and_renderer_use_set_grid_for_ragged_subset_answers(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二进制掩码枚举子集",
            "input_data": {"nums": [1, 2, 3]},
            "result": [[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]],
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "answer"}],
                    "role": "answer",
                    "value": [[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]],
                    "state": {
                        "answer": [[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]],
                    },
                    "reason": "返回所有子集。",
                    "code_line": 1,
                }
            ],
        }
    )
    scene = compile_scene(trace)
    frame = scene.frames[0]
    by_id = {obj.id: obj for obj in frame.objects}

    assert by_id["answer"].meta.get("layout") == "set_grid"
    assert by_id["answer[0]"].value == "[]"
    assert by_id["answer[7][2]"].value == 3

    artifact = BuildArtifact(
        problem_title="二进制掩码枚举子集",
        input_contract="nums: int[]",
        input_data={"nums": [1, 2, 3]},
        expected_result=trace.result,
        verifier_result=trace.result,
        variants=[
            SolutionVariant(
                id="set_grid_variant",
                name="set grid answer",
                strategy="返回所有子集。",
                code="def solve(input_data):\n    return [[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]]",
                tracker_code="def trace(input_data):\n    return {}",
                result=trace.result,
                trace=trace,
            )
        ],
        scenes={"set_grid_variant": scene},
        validation=ValidationReport(checks=["set_grid_fixture"]),
    )
    html = save_html(artifact, tmp_path / "set_grid_answer.html").read_text(encoding="utf-8")
    assert "set_grid" in LAYOUT_RENDERERS
    assert "renderSetGrid" in html
    assert "set-grid" in html


def test_scene_compiler_emits_family_visual_hints_for_sparse_initial_frames():
    examples = [
        (
            "数位 DP",
            {"digits": [1, 2, 3]},
            "digit_dp",
            "digit_dp_state",
        ),
        (
            "数组环检测",
            {"nums": [1, 3, 1, 4, 2], "slow": 0, "fast": 0},
            "linked_list",
            "linked_list_pointer",
        ),
        (
            "每日温度",
            {"temperatures": [73, 74, 75], "stack": []},
            "monotonic_stack",
            "monotonic_stack",
        ),
        (
            "第 K 大元素",
            {"nums": [3, 2, 1], "k": 2},
            "heap",
            "heap_sift_path",
        ),
        (
            "树状数组",
            {"nums": [1, 2, 3]},
            "range_structure",
            "fenwick_lowbit",
        ),
        (
            "Lowbit 分解",
            {"remaining": 12},
            "math_bit",
            "lowbit_state",
        ),
        (
            "Dijkstra 最短路径",
            {"graph": {"A": {"B": 1}}, "priority_queue": [["A", 0]]},
            "graph",
            "graph_frontier",
        ),
        (
            "Manacher 算法",
            {"s_mod": "#a#b#a#"},
            "string_specialized",
            "manacher_radius",
        ),
        (
            "稀疏表 RMQ",
            {"nums": [1, 2, 3]},
            "range_structure",
            "sparse_table_blocks",
        ),
    ]

    for algorithm, state, expected_family, expected_pattern in examples:
        trace = SemanticTrace.model_validate(
            {
                "schema_version": "semantic-trace-v1",
                "algorithm": algorithm,
                "input_data": {},
                "result": None,
                "events": [
                    {
                        "step": 0,
                        "op": "create",
                        "targets": [{"id": next(iter(state.keys()))}],
                        "state": state,
                        "reason": "初始化。",
                        "code_line": 1,
                    }
                ],
            }
        )
        frame = compile_scene(trace).frames[0]

        assert frame.evidence["visual_family"] == expected_family
        patterns = {item["pattern"] for item in frame.evidence["visual_patterns"]}
        assert expected_pattern in patterns


def test_renderer_hides_semantic_target_badges_inside_primary_stage(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Dijkstra 最短路径",
            "input_data": {},
            "result": 0,
            "events": [
                {
                    "step": 0,
                    "op": "pop",
                    "targets": [{"id": "priority_queue"}],
                    "state": {
                        "graph": {"A": {"B": 1}},
                        "priority_queue": [["A", 0]],
                    },
                    "reason": "从优先队列弹出当前候选节点。",
                    "code_line": 1,
                }
            ],
        }
    )
    artifact = BuildArtifact(
        problem_title="Dijkstra 最短路径",
        input_data={},
        expected_result=trace.result,
        verifier_result=trace.result,
        variants=[
            SolutionVariant(
                id="v1",
                name="Dijkstra",
                strategy="优先队列驱动图搜索。",
                code="def solve(input_data):\n    return 0",
                tracker_code="def trace(input_data):\n    return {}",
                result=trace.result,
                trace=trace,
            )
        ],
        scenes={"v1": compile_scene(trace)},
        validation=ValidationReport(checks=["semantic_anchor_fixture"]),
    )

    out = save_html(artifact, tmp_path / "semantic_anchor.html")
    html = out.read_text(encoding="utf-8")

    assert "semantic-anchor-band" in html
    assert "semantic-anchor-chip" in html
    assert "target-kind=\"target\"" in html

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 790})
            page.goto(out.resolve().as_uri())
            page.wait_for_timeout(100)
            metrics = page.evaluate(
                """() => ({
                    sceneAnchorCount: document.querySelectorAll('#canvas .scene-fit > .semantic-anchor-band').length,
                    sceneAnchorChipCount: document.querySelectorAll('#canvas .scene-fit > .semantic-anchor-band .semantic-anchor-chip').length,
                    targetObjectCount: document.querySelectorAll('#canvas [data-object-id="priority_queue"], #canvas [data-object-id^="priority_queue["]').length,
                })"""
            )
            assert metrics["sceneAnchorCount"] == 0
            assert metrics["sceneAnchorChipCount"] == 0
            assert metrics["targetObjectCount"] >= 1
        finally:
            browser.close()


def test_renderer_hides_string_anchor_badge_without_geometry_relation(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Z Algorithm",
            "input_data": {"text": "aabcaabx"},
            "result": [0, 1, 0, 0, 3, 1, 0, 0],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "text"}],
                    "state": {"text": "aabcaabx"},
                    "reason": "初始化字符串 text。",
                    "code_line": 1,
                }
            ],
        }
    )
    artifact = BuildArtifact(
        problem_title="Z 算法",
        input_data=trace.input_data,
        expected_result=trace.result,
        verifier_result=trace.result,
        variants=[
            SolutionVariant(
                id="v1",
                name="Z Algorithm",
                strategy="维护 Z-box。",
                code="def solve(input_data):\n    return [0, 1, 0, 0, 3, 1, 0, 0]",
                tracker_code="def trace(input_data):\n    return {}",
                result=trace.result,
                trace=trace,
            )
        ],
        scenes={"v1": compile_scene(trace)},
        validation=ValidationReport(checks=["string_anchor_fixture"]),
    )

    out = save_html(artifact, tmp_path / "z_anchor.html")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 790})
            page.goto(out.resolve().as_uri())
            page.wait_for_timeout(120)

            metrics = page.evaluate(
                """() => {
                    const fit = document.querySelector('#canvas .scene-fit');
                    const textObject = document.querySelector('#canvas .primary-scene [data-object-id="text"], #canvas .primary-scene [data-object-id^="text["]');
                    const rect = node => {
                        const box = node && node.getBoundingClientRect();
                        return box ? { top: box.top, bottom: box.bottom, left: box.left, right: box.right, width: box.width, height: box.height } : null;
                    };
                    return {
                        fit: rect(fit),
                        anchorCount: document.querySelectorAll('#canvas .scene-fit > .semantic-anchor-band').length,
                        chipCount: document.querySelectorAll('#canvas .scene-fit > .semantic-anchor-band .semantic-anchor-chip').length,
                        textObject: rect(textObject),
                        geometryCards: document.querySelectorAll('#canvas .geometry-relation-card').length,
                    };
                }"""
            )

            assert metrics["fit"] is not None
            assert metrics["anchorCount"] == 0
            assert metrics["chipCount"] == 0
            assert metrics["textObject"] is not None
            assert metrics["geometryCards"] == 0
        finally:
            browser.close()


def test_renderer_renders_string_list_indices_without_null(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Rabin-Karp 字符串匹配",
            "input_data": {"text": "abcdef", "pattern": "cde"},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "answer"}],
                    "state": {
                        "text": ["a", "b", "c", "d", "e", "f"],
                        "pattern": ["c", "d", "e"],
                        "pattern_hash": 98340,
                        "window_hash": 98340,
                        "i": 2,
                        "answer": 2,
                    },
                    "reason": "返回最终答案。",
                    "code_line": 1,
                }
            ],
        }
    )
    artifact = BuildArtifact(
        problem_title="Rabin-Karp 字符串匹配",
        input_data=trace.input_data,
        expected_result=trace.result,
        verifier_result=trace.result,
        variants=[
            SolutionVariant(
                id="v1",
                name="Rabin-Karp",
                strategy="滚动哈希。",
                code="def solve(input_data):\n    return 2",
                tracker_code="def trace(input_data):\n    return {}",
                result=trace.result,
                trace=trace,
            )
        ],
        scenes={"v1": compile_scene(trace)},
        validation=ValidationReport(checks=["string_list_fixture"]),
    )

    out = save_html(artifact, tmp_path / "string_list_indices.html")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 790})
            page.goto(out.resolve().as_uri())
            page.wait_for_timeout(120)

            metrics = page.evaluate(
                """() => ({
                    nullIndexCount: Array.from(document.querySelectorAll('#canvas .primary-scene .cell .idx'))
                        .filter(node => node.textContent.trim() === 'null').length,
                    textCellCount: document.querySelectorAll('#canvas .primary-scene [data-object-id^="text["]').length,
                    patternCellCount: document.querySelectorAll('#canvas .primary-scene [data-object-id^="pattern["]').length,
                    utilization: Number(document.querySelector('#canvas .objects')?.dataset.utilization || 0),
                })"""
            )

            assert metrics["textCellCount"] >= 6
            assert metrics["patternCellCount"] >= 3
            assert metrics["nullIndexCount"] == 0
            assert metrics["utilization"] >= 0.2
        finally:
            browser.close()


def test_renderer_uses_pan_scroll_world_for_large_primary_canvas(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Large Matrix",
            "input_data": {},
            "result": 0,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "dp"}],
                    "state": {"dp": [list(range(80))]},
                    "reason": "展示大规模矩阵时保持格子可读，并允许用户移动主画布。",
                    "code_line": 1,
                }
            ],
        }
    )
    artifact = BuildArtifact(
        problem_title="Large Matrix",
        input_data={},
        expected_result=0,
        verifier_result=0,
        variants=[
            SolutionVariant(
                id="v1",
                name="Large Matrix",
                strategy="大画布展示。",
                code="def solve(input_data):\n    return 0",
                tracker_code="def trace(input_data):\n    return {}",
                result=0,
                trace=trace,
            )
        ],
        scenes={"v1": compile_scene(trace)},
        validation=ValidationReport(checks=["large_canvas_fixture"]),
    )

    out = save_html(artifact, tmp_path / "large_canvas.html")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 790})
            page.goto(out.resolve().as_uri())
            page.wait_for_timeout(120)
            metrics = page.evaluate(
                """() => {
                    const fit = document.querySelector('#canvas .scene-fit');
                    const surface = document.querySelector('#canvas .scene-scroll-surface');
                    const world = document.querySelector('#canvas .scene-world');
                    return {
                        hasFit: !!fit,
                        hasSurface: !!surface,
                        hasWorld: !!world,
                        fitMode: String(world?.dataset.fitMode || ''),
                        fitScale: Number(world?.dataset.fitScale || 0),
                        overflowX: fit ? getComputedStyle(fit).overflowX : '',
                        overflowY: fit ? getComputedStyle(fit).overflowY : '',
                        scrollWidth: fit ? fit.scrollWidth : 0,
                        clientWidth: fit ? fit.clientWidth : 0,
                        surfaceWidth: surface ? surface.getBoundingClientRect().width : 0,
                        worldTransform: world ? getComputedStyle(world).transform : '',
                    };
                }"""
            )
            assert metrics["hasFit"] is True
            assert metrics["hasSurface"] is True
            assert metrics["hasWorld"] is True
            assert metrics["fitMode"] == "pan-scroll"
            assert metrics["fitScale"] >= 1.0
            assert metrics["overflowX"] in {"auto", "scroll"}
            assert metrics["scrollWidth"] > metrics["clientWidth"]
            assert metrics["surfaceWidth"] > metrics["clientWidth"]
            assert metrics["worldTransform"] != "none"
        finally:
            browser.close()


def test_renderer_keeps_primary_nodes_clear_when_scene_badges_are_hidden(tmp_path: Path):
    graph = {
        "nodes": ["L1", "L2", "L3", "R1", "R2"],
        "edges": [
            {"u": "L1", "v": "R1"},
            {"u": "L1", "v": "R2"},
            {"u": "L2", "v": "R1"},
            {"u": "L3", "v": "R2"},
        ],
        "directed": False,
    }
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分图最大匹配",
            "input_data": {},
            "result": {"R1": "L1", "R2": "L3"},
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "edge:L1->R2"}],
                    "state": {"graph": graph, "match": {"R1": "L1", "R2": "L3"}},
                    "reason": "高亮一条跨分区边时，固定浮层不能遮挡顶部节点。",
                    "code_line": 1,
                }
            ],
        }
    )
    artifact = BuildArtifact(
        problem_title="二分图最大匹配",
        input_data={},
        expected_result=trace.result,
        verifier_result=trace.result,
        variants=[
            SolutionVariant(
                id="v1",
                name="bipartite",
                strategy="匈牙利算法。",
                code="def solve(input_data):\n    return {}",
                tracker_code="def trace(input_data):\n    return {}",
                result=trace.result,
                trace=trace,
            )
        ],
        scenes={"v1": compile_scene(trace)},
        validation=ValidationReport(checks=["overlay_clearance_fixture"]),
    )
    out = save_html(artifact, tmp_path / "overlay_clearance.html")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 790})
            page.goto(out.resolve().as_uri())
            page.wait_for_timeout(120)
            metrics = page.evaluate(
                """() => {
                    const overlay = document.querySelector('#canvas .semantic-anchor-band, #canvas .answer-badge');
                    const nodes = Array.from(document.querySelectorAll('#canvas .primary-scene svg .node'));
                    const rect = node => {
                        const r = node.getBoundingClientRect();
                        return { left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height };
                    };
                    const intersects = (a, b) => a && b && a.right > b.left + 1 && a.left < b.right - 1 && a.bottom > b.top + 1 && a.top < b.bottom - 1;
                    const overlayRect = overlay ? rect(overlay) : null;
                    const nodeRects = nodes.map(rect);
                    return {
                        overlayPresent: !!overlayRect,
                        nodeCount: nodeRects.length,
                        blockedNodeCount: nodeRects.filter(r => intersects(r, overlayRect)).length,
                        overlayBottom: overlayRect ? overlayRect.bottom : 0,
                        topNodeTop: nodeRects.length ? Math.min(...nodeRects.map(r => r.top)) : 0,
                    };
                }"""
            )
            assert metrics["overlayPresent"] is False
            assert metrics["nodeCount"] >= 5
            assert metrics["blockedNodeCount"] == 0
        finally:
            browser.close()


def test_renderer_keeps_support_dock_scrollable_when_answer_is_demoted(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "合并区间",
            "input_data": {},
            "result": [[i, i + 1] for i in range(12)],
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "answer"}],
                    "state": {
                        "intervals": [[i, i + 1] for i in range(4)],
                        "answer": [[i, i + 1] for i in range(12)],
                    },
                    "reason": "最终答案应作为辅助状态展示，但不能被静默截断。",
                    "code_line": 1,
                }
            ],
        }
    )
    artifact = BuildArtifact(
        problem_title="合并区间",
        input_data={},
        expected_result=trace.result,
        verifier_result=trace.result,
        variants=[
            SolutionVariant(
                id="v1",
                name="merge",
                strategy="排序后合并。",
                code="def solve(input_data):\n    return []",
                tracker_code="def trace(input_data):\n    return {}",
                result=trace.result,
                trace=trace,
            )
        ],
        scenes={"v1": compile_scene(trace)},
        validation=ValidationReport(checks=["support_scroll_fixture"]),
    )

    out = save_html(artifact, tmp_path / "support_scroll.html")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 790})
            page.goto(out.resolve().as_uri())
            page.wait_for_timeout(120)
            metrics = page.evaluate(
                """() => {
                    const dock = document.querySelector('#canvas .support-dock');
                    const sceneAnswerBadge = document.querySelectorAll('#canvas .scene-fit > .answer-badge');
                    return {
                        exists: !!dock,
                        clientHeight: dock ? dock.clientHeight : 0,
                        scrollHeight: dock ? dock.scrollHeight : 0,
                        overflowY: dock ? getComputedStyle(dock).overflowY : '',
                        sceneAnswerBadgeCount: sceneAnswerBadge.length,
                    };
                }"""
            )
            assert metrics["exists"] is True
            assert metrics["clientHeight"] >= 96
            assert metrics["scrollHeight"] > metrics["clientHeight"]
            assert metrics["overflowY"] in {"auto", "scroll"}
            assert metrics["sceneAnswerBadgeCount"] == 0
        finally:
            browser.close()


def test_renderer_keeps_graph_svg_nodes_inside_viewbox(tmp_path: Path):
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "无权图最短路径",
            "input_data": {},
            "result": {"A": 0, "B": 1, "C": 1, "D": 2},
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "answer"}],
                    "state": {
                        "graph": {"A": ["B", "C"], "B": ["A"], "C": ["A", "D"], "D": ["C"]},
                        "answer": {"A": 0, "B": 1, "C": 1, "D": 2},
                    },
                    "reason": "最终图节点仍应完整留在 SVG 可视区内。",
                    "code_line": 1,
                }
            ],
        }
    )
    artifact = BuildArtifact(
        problem_title="无权图最短路径",
        input_data={},
        expected_result=trace.result,
        verifier_result=trace.result,
        variants=[
            SolutionVariant(
                id="v1",
                name="BFS",
                strategy="广度优先搜索。",
                code="def solve(input_data):\n    return {}",
                tracker_code="def trace(input_data):\n    return {}",
                result=trace.result,
                trace=trace,
            )
        ],
        scenes={"v1": compile_scene(trace)},
        validation=ValidationReport(checks=["graph_bounds_fixture"]),
    )

    out = save_html(artifact, tmp_path / "graph_bounds.html")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 790})
            page.goto(out.resolve().as_uri())
            page.wait_for_timeout(120)
            metrics = page.evaluate(
                """() => {
                    const svg = document.querySelector('#canvas .primary-scene .graph-svg');
                    const svgRect = svg && svg.getBoundingClientRect();
                    const bad = Array.from(document.querySelectorAll('#canvas .primary-scene .graph-svg .node')).filter(node => {
                        const rect = node.getBoundingClientRect();
                        return rect.left < svgRect.left - 1 || rect.top < svgRect.top - 1 ||
                            rect.right > svgRect.right + 1 || rect.bottom > svgRect.bottom + 1;
                    });
                    return { svgExists: !!svg, clippedNodeCount: bad.length };
                }"""
            )
            assert metrics["svgExists"] is True
            assert metrics["clippedNodeCount"] == 0
        finally:
            browser.close()


def test_renderer_declares_digit_dp_state_extraction_from_recursion_stack(tmp_path: Path):
    out = save_html(phase17_visual_pattern_artifact(), tmp_path / "digit_dp_helpers.html")
    html = out.read_text(encoding="utf-8")

    for marker in (
        "digitDpStateForFrame",
        "digitDpStateFromStack",
        "递归栈",
        "digit-dp-card",
    ):
        assert marker in html


def _generic_state_change_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "通用状态变化",
            "input_data": {"nums": [1, 2]},
            "result": {"nums": [1, 5]},
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}, {"id": "seen"}, {"id": "queue"}, {"id": "stack"}],
                    "state": {"nums": [1, 2], "seen": {}, "left": 0, "queue": ["A"], "stack": [1, 2]},
                    "reason": "初始化多个通用容器。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "set",
                    "targets": [{"id": "nums[1]"}],
                    "value": 5,
                    "before": 2,
                    "after": 5,
                    "state": {"nums": [1, 5], "seen": {}, "left": 0, "queue": ["A"], "stack": [1, 2]},
                    "reason": "数组写入。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "set",
                    "targets": [{"id": "seen[5]"}],
                    "value": 1,
                    "before": None,
                    "after": 1,
                    "state": {"nums": [1, 5], "seen": {"5": 1}, "left": 0, "queue": ["A"], "stack": [1, 2]},
                    "reason": "map 更新。",
                    "code_line": 3,
                },
                {
                    "step": 3,
                    "op": "move",
                    "targets": [{"id": "pointer:left"}],
                    "before": 0,
                    "after": 1,
                    "state": {"nums": [1, 5], "seen": {"5": 1}, "left": 1, "queue": ["A"], "stack": [1, 2]},
                    "reason": "指针移动。",
                    "code_line": 4,
                },
                {
                    "step": 4,
                    "op": "push",
                    "targets": [{"id": "queue"}],
                    "state": {"nums": [1, 5], "seen": {"5": 1}, "left": 1, "queue": ["A", "B"], "stack": [1, 2]},
                    "reason": "queue 变化没有显式 before/after，应退化为 state diff。",
                    "code_line": 5,
                },
                {
                    "step": 5,
                    "op": "pop",
                    "targets": [{"id": "stack"}],
                    "state": {"nums": [1, 5], "seen": {"5": 1}, "left": 1, "queue": ["A", "B"], "stack": [1]},
                    "reason": "stack 变化没有显式 before/after，应退化为 state diff。",
                    "code_line": 6,
                },
            ],
        }
    )


def test_scene_compiler_emits_generic_change_evidence_for_core_state_transitions():
    scene = compile_scene(_generic_state_change_trace())

    array_change = scene.frames[1].evidence.get("changes", [])
    map_change = scene.frames[2].evidence.get("changes", [])
    pointer_change = scene.frames[3].evidence.get("changes", [])
    queue_change = scene.frames[4].evidence.get("changes", [])
    stack_change = scene.frames[5].evidence.get("changes", [])

    assert any(change["target"] == "nums[1]" and change["before"] == 2 and change["after"] == 5 for change in array_change)
    assert any(change["target"] == "seen[5]" and change["after"] == 1 for change in map_change)
    assert any(change["target"] == "pointer:left" and change["before"] == 0 and change["after"] == 1 for change in pointer_change)
    assert any(change["target"] == "queue" and change["source"] == "state_diff" for change in queue_change)
    assert any(change["target"] == "stack" and change["source"] == "state_diff" for change in stack_change)


def test_renderer_declares_generic_change_summary_in_teaching_panel(tmp_path: Path):
    out = save_html(fixture_artifact(), tmp_path / "change_summary.html")
    html = out.read_text(encoding="utf-8")

    assert "function renderChangeSummary" in html
    assert "function eventChangeRows" in html
    assert "function stateDiff" in html
    assert "change-summary" in html
    assert "状态变化摘要" in html

    teaching_renderer = html.split("function renderTeaching(f)", 1)[1].split("function renderInteraction", 1)[0]
    assert "renderChangeSummary(f)" in teaching_renderer
    assert "algorithm" not in teaching_renderer
    assert "problem_title" not in teaching_renderer


def test_golden_visual_matrix_declares_core_examples_and_contracts():
    examples = golden_visual_matrix()
    by_id = {example["id"]: example for example in examples}
    required = {"unique_paths", "bfs", "binary_search", "monotonic_stack"}

    assert required.issubset(by_id), by_id.keys()
    for example_id in required:
        example = by_id[example_id]
        doc_path = Path(example["doc"])
        assert doc_path.exists(), example_id
        assert example["primary_primitives"], example_id
        assert "key_deps" in example and example["key_deps"], example_id
        assert {"what", "why"}.issubset(set(example["key_teaching_fields"])), example_id
        assert example["key_objects"], example_id


def test_golden_visual_matrix_compiles_core_examples_without_renderer_branches():
    artifact = golden_visual_artifact()
    examples = golden_visual_matrix()

    assert {variant.id for variant in artifact.variants} == {example["id"] for example in examples}
    for example in examples:
        scene = artifact.scenes[example["id"]]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
        evidence_deps = {
            dep
            for frame in scene.frames
            for dep in (frame.evidence.get("deps") or [])
        }
        teaching_fields = {
            key
            for frame in scene.frames
            for key, value in (frame.teaching or {}).items()
            if str(value or "").strip()
        }

        assert set(example["primary_primitives"]).issubset(layouts), example["id"]
        assert set(example["support_primitives"]).issubset(layouts), example["id"]
        assert set(example["key_objects"]).issubset(object_ids), example["id"]
        assert set(example["key_deps"]).issubset(evidence_deps), example["id"]
        assert set(example["key_teaching_fields"]).issubset(teaching_fields), example["id"]


def test_golden_visual_matrix_declares_prediction_interactions_for_core_examples():
    artifact = golden_visual_artifact()
    expected_types = {
        "unique_paths": "input",
        "bfs": "choice",
        "binary_search": "choice",
        "monotonic_stack": "judge",
    }

    for variant_id, expected_type in expected_types.items():
        scene = artifact.scenes[variant_id]
        interactions = [frame.interaction for frame in scene.frames if frame.interaction]
        assert interactions, variant_id
        assert any(interaction["type"] == expected_type for interaction in interactions), (variant_id, interactions)
        for interaction in interactions:
            assert interaction["prompt"].strip(), (variant_id, interaction)
            assert interaction["answer"] is not None, (variant_id, interaction)
            assert interaction["explanation"].strip(), (variant_id, interaction)
            if interaction["type"] == "choice":
                assert interaction["options"], (variant_id, interaction)
                assert str(interaction["answer"]) in {str(option) for option in interaction["options"]}, (
                    variant_id,
                    interaction,
                )
                wrong_options = {str(option) for option in interaction["options"]} - {str(interaction["answer"])}
                assert wrong_options, (variant_id, interaction)
                option_explanations = interaction.get("option_explanations") or {}
                assert interaction.get("wrong_explanation") or any(
                    option in option_explanations and str(option_explanations[option]).strip()
                    for option in wrong_options
                ), (variant_id, interaction)


def test_renderer_declares_readonly_prediction_interactions(tmp_path: Path):
    out = save_html(golden_visual_artifact(), tmp_path / "prediction_interactions.html")
    html = out.read_text(encoding="utf-8")

    assert "function renderInteraction" in html
    assert "function checkChoice" in html
    assert "function checkInput" in html
    assert "function checkJudge" in html
    assert "function wrongFeedback" in html
    assert "option_explanations" in html
    assert "wrong_explanation" in html
    assert "data-interaction-type" in html
    assert "data-trace-step" in html

    render_interaction = html.split("function renderInteraction", 1)[1].split("function checkChoice", 1)[0]
    assert "interaction.type" in render_interaction
    assert "interaction.answer" not in render_interaction
    assert "algorithm" not in render_interaction
    assert "problem_title" not in render_interaction

    checker_block = html.split("function checkChoice", 1)[1].split("function renderCode", 1)[0]
    assert "frame().interaction.answer" in checker_block
    assert "ARTIFACT" not in checker_block
    assert "frames()[" not in checker_block
    assert "scene().frames" not in checker_block
    assert "stepIndex =" not in checker_block
    assert "algorithm" not in checker_block


def test_renderer_declares_phase17_formula_expand_and_structured_wrong_feedback(tmp_path: Path):
    out = save_html(golden_visual_artifact(), tmp_path / "phase17_interaction_learning.html")
    html = out.read_text(encoding="utf-8")

    assert "function renderFormulaExpansion" in html
    assert "function formulaSubstitutionForFrame" in html
    assert "class=\"teach-row formula formula-expander\"" in html
    assert "SceneGraph frame.teaching / frame.evidence / visual object meta" in html
    assert "错误选项解释：" in html
    assert "data-source" in html

    formula_block = html.split("function renderFormulaExpansion", 1)[1].split("function renderInteraction", 1)[0]
    assert "f && f.evidence" in formula_block
    assert "f && f.teaching" in formula_block
    assert "objectsWithPattern" in formula_block
    assert "ARTIFACT" not in formula_block
    assert "algorithm" not in formula_block

    feedback_block = html.split("function checkChoice", 1)[1].split("function renderCode", 1)[0]
    assert "option_explanations" in feedback_block
    assert "wrong_explanation" in feedback_block
    assert "teaching.common_mistake" in feedback_block
    assert "ARTIFACT" not in feedback_block
    assert "scene().frames" not in feedback_block


def test_renderer_removes_main_input_regeneration_and_validation_sections(tmp_path: Path):
    out = save_html(golden_visual_artifact(), tmp_path / "compact_main_view.html")
    html = out.read_text(encoding="utf-8")

    assert 'id="input-editor"' not in html
    assert 'id="regeneration-panel"' not in html
    assert 'id="problem-description"' not in html
    assert 'id="evidence"' not in html
    assert ">题目与输入<" not in html
    assert ">修改输入<" not in html
    assert ">输入重新生成<" not in html
    assert ">系统校验<" not in html
    assert "function buildProblemInputPayload" not in html
    assert "function updateRegeneratePayload" not in html
    assert "function requestRegenerate" not in html
    assert 'id="debug-evidence"' in html
    assert "function renderEvidence" in html

    select_block = html.split("function selectVariant", 1)[1].split("function go", 1)[0]
    assert "variantIndex = i" in select_block
    assert "stepIndex = 0" in select_block
    assert "ARTIFACT.scenes[variant().id]" in html


def test_renderer_declares_variant_comparison_without_scene_mixing(tmp_path: Path):
    out = save_html(golden_visual_artifact(), tmp_path / "variant_compare.html")
    html = out.read_text(encoding="utf-8")

    assert 'id="variant-compare-panel"' in html
    assert 'id="variant-compare"' in html
    assert "function renderVariantCompare" in html
    assert "function isKeyCompareFrame" in html
    assert "variant-compare-card" in html
    assert "复杂度" in html
    assert "关键步骤数" in html
    assert "结果一致" in html

    compare_block = html.split("function renderVariantCompare", 1)[1].split("function isKeyCompareFrame", 1)[0]
    assert "ARTIFACT.variants" in compare_block
    assert "ARTIFACT.scenes && ARTIFACT.scenes[v.id]" in compare_block
    assert "data-variant-id" in compare_block
    assert "data-scene-id" in compare_block
    assert "data-step-count" in compare_block
    assert "selectVariant(" in compare_block
    assert "algorithm" not in compare_block
    assert "unique_paths" not in compare_block
    assert "bfs" not in compare_block
    assert "ARTIFACT =" not in compare_block
    assert "scene().frames" not in compare_block
    assert "frames()[" not in compare_block

    keyframe_block = html.split("function isKeyCompareFrame", 1)[1].split("function selectVariant", 1)[0]
    assert "timeline.keyframe" in keyframe_block
    assert "evidence.operation" in keyframe_block
    assert "algorithm" not in keyframe_block
    assert "problem_title" not in keyframe_block

    select_block = html.split("function selectVariant", 1)[1].split("function go", 1)[0]
    assert "renderVariantCompare();" in select_block
    assert "stepIndex = 0" in select_block


def _process_evidence_text(scene_id: str) -> str:
    scene = golden_visual_artifact().scenes[scene_id]
    process_blocks = [frame.evidence.get("process") for frame in scene.frames]
    assert any(process_blocks), scene_id
    return json.dumps(process_blocks, ensure_ascii=False, sort_keys=True)


def test_scene_compiler_emits_user_readable_process_evidence_for_golden_examples():
    expectations = {
        "unique_paths": ("DP 转移", "依赖", "通过核对"),
        "bfs": ("首次访问", "距离", "dist"),
        "binary_search": ("区间收缩", "指针", "仍覆盖"),
        "monotonic_stack": ("弹出", "单调栈", "answer"),
    }

    for scene_id, keywords in expectations.items():
        text = _process_evidence_text(scene_id)
        for keyword in keywords:
            assert keyword in text, (scene_id, keyword, text)
        assert "raw validation" not in text.lower(), scene_id


def test_renderer_declares_process_evidence_and_preserves_raw_validation_report(tmp_path: Path):
    artifact = golden_visual_artifact().model_copy(deep=True)
    artifact.validation.errors.append("raw-process-error")
    artifact.validation.warnings.append("raw-process-warning")
    artifact.validation.release_gate.blocking_reasons.append("raw-blocking-reason")

    out = save_html(artifact, tmp_path / "process_evidence.html")
    html = out.read_text(encoding="utf-8")

    assert "function renderProcessEvidence" in html
    assert "过程校验证据" in html
    assert "本步过程核对" in html
    assert "debug-validation-json" in html
    assert "Warnings / errors" in html
    assert "raw-process-error" in html
    assert "raw-process-warning" in html
    assert "raw-blocking-reason" in html

    step_renderer = html.split("function renderStepEvidence", 1)[1].split("function renderChangeSummary", 1)[0]
    assert "renderProcessEvidence(f)" in step_renderer
    process_renderer = html.split("function renderProcessEvidence", 1)[1].split("function renderStepEvidence", 1)[0]
    assert "f.evidence" in process_renderer
    assert "algorithm" not in process_renderer
    assert "problem_title" not in process_renderer


def test_phase17_scene_compiler_emits_family_visual_pattern_meta():
    artifact = phase17_visual_pattern_artifact()
    expected = {str(item["id"]): set(item["patterns"]) for item in phase17_visual_pattern_matrix()}

    for variant_id, patterns in expected.items():
        scene = artifact.scenes[variant_id]
        object_patterns = {
            pattern
            for frame in scene.frames
            for obj in frame.objects
            for pattern in (obj.meta.get("visual_patterns") or [])
        }
        evidence_patterns = {
            item.get("pattern")
            for frame in scene.frames
            for item in frame.evidence.get("visual_patterns", [])
        }
        missing = patterns - object_patterns - evidence_patterns
        assert not missing, (variant_id, missing, object_patterns, evidence_patterns)

    dp_scene = artifact.scenes["dp_formula"]
    assert any(obj.type.value == "arrow" and "dp_dependency_arrow" in (obj.meta.get("visual_patterns") or []) for frame in dp_scene.frames for obj in frame.objects)

    flow_edges = [
        obj
        for frame in artifact.scenes["network_flow"].frames
        for obj in frame.objects
        if obj.type.value == "edge" and "network_flow_edge_label" in (obj.meta.get("visual_patterns") or [])
    ]
    assert flow_edges
    assert any(obj.meta.get("capacity") is not None and obj.meta.get("residual") is not None for obj in flow_edges)


def test_scene_compiler_marks_diff_prefix_only_when_endpoint_relation_exists():
    scene = compile_scene(diff_prefix_trace())

    assert scene.frames[0].evidence.get("visual_family") == "range_structure"
    assert scene.frames[0].evidence.get("visual_family_pattern") != "diff_prefix"
    assert scene.frames[1].evidence.get("visual_family") == "range_structure"
    assert scene.frames[1].evidence.get("visual_family_pattern") == "diff_prefix"
    assert any(
        item.get("pattern") == "diff_prefix"
        for item in scene.frames[1].evidence.get("visual_patterns", [])
    )


def test_scene_compiler_marks_geometry_relation_only_when_turn_relation_exists():
    scene = compile_scene(geometry_trace())

    assert scene.frames[0].evidence.get("visual_family") == "geometry"
    assert scene.frames[0].evidence.get("visual_family_pattern") != "geometry_relation"
    assert not any(
        item.get("pattern") == "geometry_relation"
        for item in scene.frames[0].evidence.get("visual_patterns", [])
    )
    assert scene.frames[1].evidence.get("visual_family") == "geometry"
    assert scene.frames[1].evidence.get("visual_family_pattern") == "geometry_relation"
    assert any(
        item.get("pattern") == "geometry_relation"
        for item in scene.frames[1].evidence.get("visual_patterns", [])
    )


def test_phase17_renderer_declares_generic_visual_pattern_runtime(tmp_path: Path):
    out = save_html(phase17_visual_pattern_artifact(), tmp_path / "phase17_visual_patterns.html")
    html = out.read_text(encoding="utf-8")

    for marker in (
        "function renderVisualPatternPanel",
        "function objectsWithPattern",
        "function objectMetaClass",
        "function edgeDisplayLabel",
        "dp-formula-substitution",
        "graph-visual-pattern",
        "string-alignment-card",
        "tree-return-pattern",
        "backtracking-pattern",
        "range-structure-pattern",
        "network-flow-pattern",
        "edge-label",
        "return-bubble",
    ):
        assert marker in html

    visual_block = html.split("function renderVisualPatternPanel", 1)[1].split("function renderDependencyFlow", 1)[0]
    assert "problem_title" not in visual_block
    assert "algorithm" not in visual_block
    assert "ARTIFACT" not in visual_block
    assert "objectsWithPattern" in visual_block
    assert "f.objects" in visual_block


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


def test_sandbox_allows_string_hash_character_codes():
    code = """
def solve(input_data):
    h = 0
    for ch in input_data["text"]:
        h = h * 257 + ord(ch)
    return h
"""
    assert run_function(code, "solve", {"text": "ab"}) == 97 * 257 + 98


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


def test_execute_variant_rejects_legacy_trace_event_fields():
    input_data = {
        "tree": {"nodes": [{"id": "2"}], "edges": []},
        "p": "2",
        "q": "2",
    }
    variant = SolutionVariant(
        id="legacy_lca_trace",
        name="旧 trace 字段 LCA",
        strategy="",
        code="def solve(input_data):\n    return '2'",
        tracker_code=(
            "def trace(input_data):\n"
            "    return {\n"
            "      'schema_version': 'semantic-trace-v1',\n"
            "      'algorithm': '二叉树最近公共祖先',\n"
            "      'result': '2',\n"
            "      'events': [\n"
            "        {'type': 'create', 'target': 'tree', 'state': {'tree': input_data['tree'], 'p': '2', 'q': '2'}, 'reason': '初始化树。', 'code_line': 1},\n"
            "        {'type': 'enter', 'target': 'node:2', 'state': {'tree': input_data['tree'], 'p': '2', 'q': '2', 'current': '2'}, 'role': 'current', 'reason': '进入节点。', 'code_line': 2},\n"
            "        {'type': 'mark', 'target': 'node:2', 'state': {'tree': input_data['tree'], 'p': '2', 'q': '2', 'lca': '2'}, 'role': 'answer', 'reason': '找到最近公共祖先。', 'code_line': 3}\n"
            "      ]\n"
            "    }\n"
        ),
    )

    try:
        execute_variant(variant, input_data)
    except Exception as exc:
        message = str(exc)
        assert "input_data" in message
        assert "op" in message
        assert "type" in message
        assert "target" in message
    else:
        raise AssertionError("execute_variant 应拒绝旧 trace 字段 type/target 和缺失 input_data")


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
        test_tracker_prompt_requires_teaching_and_complete_key_set_events,
        test_repair_prompt_converts_sparse_trace_to_tracer_api,
        test_contract_prompt_examples_normalize_for_two_sum_dp_graph_stack,
        test_contract_repair_loop_fixes_truncated_json,
        test_contract_repair_loop_handles_validator_and_oracle_failures,
        test_solution_repair_context_classifies_failure_types_and_step_targets,
        test_llm_benchmark_report_summarizes_repair_failure_type_transitions,
        test_llm_benchmark_failed_run_preserves_repair_failure_types,
        test_schema_rejects_non_contiguous_steps,
        test_trace_validator_rejects_unknown_index_target,
        test_trace_validator_accepts_map_bracket_and_slice_targets,
        test_trace_validator_rejects_legacy_map_colon_targets,
        test_trace_validator_accepts_input_tree_and_points_targets,
        test_execute_variant_rejects_quoted_map_targets,
        test_execute_variant_rejects_excessive_trace_events,
        test_process_validator_accepts_map_container_dependency,
        test_process_validation_registry_declares_core_families,
        test_process_validation_unknown_family_uses_fallback_not_strong_validation,
        test_process_registry_does_not_replace_blocking_errors,
        test_semantic_event_normalizes_null_optional_text,
        test_process_validator_rejects_bad_unique_paths_transition,
        test_process_validator_rejects_bad_unique_paths_dependencies,
        test_process_validator_rejects_sparse_unique_paths_trace,
        test_process_validator_rejects_low_tracer_coverage_meta,
        test_process_validator_rejects_forged_tracer_coverage_meta,
        test_process_validator_rejects_bad_bfs_distance,
        test_process_validator_rejects_bad_bfs_discovery_parent,
        test_process_validator_rejects_bad_subset_sum_transition,
        test_process_validator_rejects_binary_search_mid_outside_window,
        test_process_validator_rejects_binary_search_wrong_shrink_direction,
        test_process_validator_rejects_bad_heap_and_union_find,
        test_process_validator_rejects_union_find_link_without_connected_roots,
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
        test_scene_compiler_preserves_compound_visual_primitives_for_core_examples,
        test_scene_compiler_emits_generic_change_evidence_for_core_state_transitions,
        test_golden_visual_matrix_declares_core_examples_and_contracts,
        test_golden_visual_matrix_compiles_core_examples_without_renderer_branches,
        test_golden_visual_matrix_declares_prediction_interactions_for_core_examples,
        test_scene_compiler_emits_user_readable_process_evidence_for_golden_examples,
        test_phase17_scene_compiler_emits_family_visual_pattern_meta,
        test_ml_correctness_accepts_linear_regression_gradient_and_loss_curve,
        test_ml_correctness_rejects_bad_linear_regression_gradient_and_loss_curve,
        test_ml_correctness_checks_parameter_update_tolerance_and_random_seed,
        test_sandbox_blocks_imports_and_times_out,
        test_sandbox_exposes_tracer_to_generated_tracker,
        test_sandbox_allows_string_hash_character_codes,
        test_sandbox_blocks_dunder_introspection_import_escape,
        test_execute_variant_requires_trace_input_data,
        test_execute_variant_normalizes_event_steps,
        test_execute_variant_rejects_legacy_trace_event_fields,
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
        test_teaching_step_renders_structured_fields_without_algorithm_branches(Path(d))
        test_teaching_step_covers_generic_algorithm_families_and_formula_fallback()
        test_stable_renderer_exposes_correctness_and_step_evidence(Path(d))
        test_renderer_uses_p1_information_architecture(Path(d))
        test_scene_compiler_emits_generic_timeline_evidence()
        test_scene_compiler_infers_timeline_phase_without_explicit_state_field()
        test_renderer_uses_semantic_timeline_with_generic_fallback(Path(d))
        test_tracker_prompt_requests_phase_labels_without_stage_targets()
        test_tracker_prompt_requires_accurate_code_lines_for_key_events()
        test_scene_frame_payload_flows_across_core_layouts()
        test_renderer_declares_scene_frame_payload_fallbacks(Path(d))
        test_renderer_declares_code_sync_and_line_fallbacks(Path(d))
        test_scene_compiler_compiles_deps_as_dependency_edges_across_core_layouts()
        test_renderer_declares_structured_dependency_flow(Path(d))
        test_scene_compiler_hides_internal_trace_meta_from_rendered_state(Path(d))
        test_renderer_declares_process_evidence_and_preserves_raw_validation_report(Path(d))
        test_renderer_declares_compound_primitive_layout(Path(d))
        test_renderer_declares_phase1_primary_stage_fit_and_raw_state_policy(Path(d))
        test_renderer_declares_linked_list_and_math_bit_primitives(Path(d))
        test_renderer_declares_rich_object_detail_payload(Path(d))
        test_renderer_declares_algorithm_family_semantic_primitives(Path(d))
        test_renderer_declares_specialized_family_teaching_primitives(Path(d))
        test_renderer_hides_semantic_target_badges_inside_primary_stage(Path(d))
        test_renderer_hides_string_anchor_badge_without_geometry_relation(Path(d))
        test_renderer_renders_string_list_indices_without_null(Path(d))
        test_renderer_uses_pan_scroll_world_for_large_primary_canvas(Path(d))
        test_renderer_keeps_primary_nodes_clear_when_scene_badges_are_hidden(Path(d))
        test_renderer_keeps_support_dock_scrollable_when_answer_is_demoted(Path(d))
        test_renderer_keeps_graph_svg_nodes_inside_viewbox(Path(d))
        test_renderer_declares_generic_change_summary_in_teaching_panel(Path(d))
        test_renderer_declares_readonly_prediction_interactions(Path(d))
        test_renderer_declares_phase17_formula_expand_and_structured_wrong_feedback(Path(d))
        test_renderer_declares_regeneration_entry_without_trace_mutation(Path(d))
        test_renderer_declares_variant_comparison_without_scene_mixing(Path(d))
        test_phase17_renderer_declares_generic_visual_pattern_runtime(Path(d))
        test_renderer_writes_html(Path(d))
        test_ml_primitives_cover_linear_and_logistic_regression(Path(d))


if __name__ == "__main__":
    run_all()
    print("offline_regression: PASS")
