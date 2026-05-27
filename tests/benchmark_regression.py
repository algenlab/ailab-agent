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
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport
from algolab.verification.process_validator import validate_process
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
from scripts.check_benchmark_html import html_paths_from_report, resolve_required_case_htmls
from scripts.build_evaluation_manifest import build_manifest, write_manifest
from scripts.build_evaluation_report import build_evaluation_report, comparison_protocols, compute_metrics, condition_summary
from scripts.build_reproducibility_package import build_reproducibility_package, write_reproducibility_package
from scripts.check_v1_release_gate import build_v1_release_gate_report, write_v1_release_gate_report
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


def _process_errors_for(raw_trace: dict) -> list[str]:
    trace = SemanticTrace.model_validate(raw_trace)
    errors, _warnings = validate_process(trace)
    return errors


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


def test_process_validator_rejects_missing_key_step_coverage_for_small_traces():
    dp_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "不同路径",
            "input_data": {"m": 2, "n": 2},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "dp"}],
                    "state": {"dp": [[1, 1], [1, 2]]},
                    "reason": "只展示最终 DP 表。",
                    "code_line": 1,
                }
            ],
        }
    )
    bfs_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "BFS 最短层数",
            "input_data": {"graph": {"A": ["B"], "B": []}, "start": "A"},
            "result": {"A": 0, "B": 1},
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "queue"}, {"id": "node:A"}],
                    "state": {"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0, "B": 1}},
                    "reason": "只展示 BFS 最终距离。",
                    "code_line": 1,
                }
            ],
        }
    )
    binary_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分查找",
            "input_data": {"nums": [1, 3, 5], "target": 5},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [1, 3, 5], "left": 2, "right": 2, "target": 5},
                    "reason": "只展示最终搜索区间。",
                    "code_line": 1,
                }
            ],
        }
    )
    stack_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "每日温度",
            "input_data": {"temperatures": [30, 40]},
            "result": [1, 0],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "temperatures"}, {"id": "stack"}, {"id": "answer"}],
                    "state": {
                        "temperatures": [30, 40],
                        "stack": [],
                        "answer": [1, 0],
                        "stack_order": "decreasing",
                    },
                    "reason": "只展示最终答案。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("不同路径小 DP 表缺少逐帧状态转移" in error for error in dp_errors)
    assert any("BFS 小图缺少关键步骤覆盖" in error for error in bfs_errors)
    assert any("二分缺少关键步骤覆盖" in error for error in binary_errors)
    assert any("单调栈缺少关键步骤覆盖" in error for error in stack_errors)
    assert classify_failure("failure_type=coverage_error: BFS 小图缺少关键步骤覆盖：check_edge") == "coverage_error"


def test_process_validator_rejects_bad_string_algorithm_tables():
    rabin_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Rabin-Karp 滚动哈希",
            "input_data": {"text": "abcd", "pattern": "bc"},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "window_hashes[1]"}],
                    "state": {
                        "text": "abcd",
                        "pattern": "bc",
                        "pattern_hash": 99,
                        "window_hashes": [10, 999, 30],
                    },
                    "reason": "错误滚动哈希。",
                    "code_line": 1,
                }
            ],
        }
    )
    z_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Z Algorithm",
            "input_data": {"text": "aabcaabx"},
            "result": [0, 1, 0, 0, 3, 1, 0, 0],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "z[4]"}],
                    "state": {"text": "aabcaabx", "z": [0, 1, 0, 0, 9, 1, 0, 0]},
                    "reason": "错误 Z 值。",
                    "code_line": 1,
                }
            ],
        }
    )
    manacher_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Manacher 回文半径",
            "input_data": {"text": "ababa"},
            "result": 5,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "radius[5]"}],
                    "state": {"text": "#a#b#a#b#a#", "radius": [0, 1, 0, 3, 0, 4, 0, 3, 0, 1, 0]},
                    "reason": "错误回文半径。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("Rabin-Karp" in error for error in rabin_errors), rabin_errors
    assert any("Z Algorithm" in error for error in z_errors), z_errors
    assert any("Manacher" in error for error in manacher_errors), manacher_errors


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


def test_phase7_string_algorithms_have_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "kmp": {"state_keys": {"text", "pattern", "pi"}, "target_prefix": "pi[", "reason_token": "回退"},
        "rabin_karp": {"state_keys": {"text", "pattern", "pattern_hash"}, "target_prefix": "window_hashes[", "reason_token": "哈希"},
        "z_algorithm": {"state_keys": {"text", "z"}, "target_prefix": "z[", "reason_token": "Z"},
        "manacher": {"state_keys": {"text", "radius"}, "target_prefix": "radius[", "reason_token": "半径"},
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert "string" in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
        for key in expectation["state_keys"]:
            assert key in object_ids, (case_id, key, sorted(object_ids)[:20])
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        assert any(target.startswith(expectation["target_prefix"]) for target in target_ids), (case_id, target_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        assert expectation["reason_token"] in reasons, (case_id, reasons)

    example_names = {
        "string_kmp.md": ["string", "pi", "失配回退"],
        "string_rabin_karp.md": ["string", "pattern_hash", "滚动哈希"],
        "string_z_algorithm.md": ["string", "z", "Z-box"],
        "string_manacher.md": ["string", "radius", "半径扩展"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_tree_recursion_aggregates():
    diameter_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二叉树直径",
            "input_data": {
                "tree": {
                    "nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                    "edges": [["1", "2"], ["1", "3"]],
                }
            },
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "diameter[1]"}],
                    "state": {
                        "tree": {
                            "nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                            "edges": [["1", "2"], ["1", "3"]],
                        },
                        "current": "1",
                        "height": {"1": 2, "2": 1, "3": 1},
                        "diameter": {"1": 9, "2": 0, "3": 0},
                    },
                    "reason": "错误树直径聚合。",
                    "code_line": 1,
                }
            ],
        }
    )
    tree_dp_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "树形 DP 最大独立集",
            "input_data": {
                "tree": {
                    "nodes": [{"id": "1", "value": 3}, {"id": "2", "value": 2}, {"id": "3", "value": 1}],
                    "edges": [["1", "2"], ["1", "3"]],
                }
            },
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "dp_take[1]"}],
                    "state": {
                        "tree": {
                            "nodes": [{"id": "1", "value": 3}, {"id": "2", "value": 2}, {"id": "3", "value": 1}],
                            "edges": [["1", "2"], ["1", "3"]],
                        },
                        "current": "1",
                        "dp_take": {"1": 99, "2": 2, "3": 1},
                        "dp_skip": {"1": 3, "2": 0, "3": 0},
                    },
                    "reason": "错误树形 DP 聚合。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("树直径" in error for error in diameter_errors), diameter_errors
    assert any("树形 DP" in error for error in tree_dp_errors), tree_dp_errors


def test_phase7_tree_recursion_group_has_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "binary_tree_inorder": {"layout": "tree", "state_keys": {"current", "call_stack", "return_values"}, "reason_token": "中序"},
        "lca": {"layout": "tree", "state_keys": {"current", "call_stack", "return_values"}, "reason_token": "最近公共祖先"},
        "tree_diameter": {"layout": "tree", "state_keys": {"current", "call_stack", "height", "diameter"}, "reason_token": "子树高度"},
        "tree_max_independent_set": {"layout": "tree", "state_keys": {"current", "call_stack", "dp_take", "dp_skip"}, "reason_token": "子树聚合"},
        "permutations": {"layout": "recursion_tree", "state_keys": {"path", "call_stack", "return_values"}, "reason_token": "撤销选择"},
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert expectation["layout"] in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expectation["layout"] in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        target_ids = {target.id for event in artifact.variants[0].trace.events for target in event.targets}
        dep_ids = {dep.id for event in artifact.variants[0].trace.events for dep in event.deps}
        assert any(target.startswith("frame:") for target in target_ids), (case_id, target_ids)
        assert any(target.startswith("node:") for target in target_ids), (case_id, target_ids)
        assert any(dep.startswith("frame:") for dep in dep_ids), (case_id, dep_ids)
        assert any(dep.startswith("node:") for dep in dep_ids), (case_id, dep_ids)
        arrow_pairs = {(obj.source, obj.target) for frame in scene.frames for obj in frame.objects if obj.type.value == "arrow"}
        assert any(source.startswith("frame:") and target.startswith("node:") for source, target in arrow_pairs) or any(
            source.startswith("node:") and target.startswith("frame:") for source, target in arrow_pairs
        ), (case_id, arrow_pairs)
        reasons = "\n".join(event.reason or "" for event in artifact.variants[0].trace.events)
        assert expectation["reason_token"] in reasons, (case_id, reasons)

    example_names = {
        "tree_inorder.md": ["tree", "call_stack", "返回值"],
        "tree_lca.md": ["tree", "frame:", "最近公共祖先"],
        "tree_diameter.md": ["tree", "height", "diameter"],
        "tree_dp.md": ["tree", "dp_take", "子树聚合"],
        "recursion_permutations.md": ["recursion_tree", "path", "撤销选择"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_range_structure_tables():
    segment_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "线段树区间和",
            "input_data": {"nums": [2, 1, 4], "query": [0, 2], "update": [1, 3]},
            "result": {"before": 7, "after": 9},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "node:seg_1_0_2"}],
                    "state": {
                        "nums": [2, 1, 4],
                        "query": [0, 2],
                        "segment_tree": {
                            "nodes": [
                                {"id": "seg_1_0_2", "label": "[0,2]=99", "meta": {"l": 0, "r": 2, "sum": 99}},
                                {"id": "seg_2_0_1", "label": "[0,1]=3", "meta": {"l": 0, "r": 1, "sum": 3}},
                                {"id": "seg_3_2_2", "label": "[2,2]=4", "meta": {"l": 2, "r": 2, "sum": 4}},
                            ],
                            "edges": [["seg_1_0_2", "seg_2_0_1"], ["seg_1_0_2", "seg_3_2_2"]],
                        },
                    },
                    "reason": "错误线段树聚合。",
                    "code_line": 1,
                }
            ],
        }
    )
    fenwick_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "树状数组前缀和",
            "input_data": {"nums": [1, 2, 3, 4], "query": [1, 3], "update": [2, 1]},
            "result": {"before": 9, "after": 10},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "bit[2]"}],
                    "state": {"nums": [1, 2, 3, 4], "bit": [0, 1, 99, 3, 10], "query": [1, 3]},
                    "reason": "错误树状数组节点。",
                    "code_line": 1,
                }
            ],
        }
    )
    sparse_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "稀疏表区间最小值",
            "input_data": {"nums": [5, 2, 7, 3], "query": [1, 3]},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "st[1][1]"}],
                    "state": {"nums": [5, 2, 7, 3], "st": [[5, 2, 7, 3], [2, 9, 3], [2]], "log": [0, 0, 1, 1, 2], "query": [1, 3]},
                    "reason": "错误稀疏表单元。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("线段树" in error for error in segment_errors), segment_errors
    assert any("树状数组" in error for error in fenwick_errors), fenwick_errors
    assert any("稀疏表" in error for error in sparse_errors), sparse_errors


def test_phase7_range_structures_have_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "segment_tree_range_sum": {
            "layout": "tree",
            "state_keys": {"segment_tree", "nums", "query", "update", "answer"},
            "target_prefix": "node:seg_",
            "reason_tokens": ("查询区间", "更新路径"),
        },
        "fenwick_tree_prefix_sum": {
            "layout": "array",
            "state_keys": {"nums", "bit", "query", "update", "answer"},
            "target_prefix": "bit[",
            "reason_tokens": ("lowbit", "前缀", "更新路径"),
        },
        "sparse_table_range_min": {
            "layout": "matrix",
            "state_keys": {"nums", "st", "log", "query", "answer"},
            "target_prefix": "st[",
            "reason_tokens": ("稀疏表", "重叠区间"),
        },
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert expectation["layout"] in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expectation["layout"] in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        dep_ids = {dep.id for event in trace.events for dep in event.deps}
        assert not any(item.startswith("range:") for item in target_ids | dep_ids), (case_id, target_ids | dep_ids)
        assert any(target.startswith(expectation["target_prefix"]) for target in target_ids | dep_ids), (case_id, target_ids, dep_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        for token in expectation["reason_tokens"]:
            assert token in reasons, (case_id, token, reasons)

    example_names = {
        "range_segment_tree.md": ["segment_tree", "node:seg_", "查询区间", "更新路径"],
        "range_fenwick_tree.md": ["bit[", "lowbit", "前缀"],
        "range_sparse_table.md": ["st[", "稀疏表", "重叠区间"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_math_bit_invariants():
    gcd_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "最大公约数 Euclid",
            "input_data": {"a": 48, "b": 18},
            "result": 6,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "remainders[0]"}],
                    "state": {"a": 48, "b": 18, "remainders": [99]},
                    "reason": "错误余数。",
                    "code_line": 1,
                }
            ],
        }
    )
    fast_power_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "快速幂",
            "input_data": {"base": 3, "exponent": 5, "mod": 13},
            "result": 9,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "powers[2]"}],
                    "state": {"base": 3, "exponent": 5, "mod": 13, "bits": [1, 0, 1], "powers": [3, 9, 99]},
                    "reason": "错误快速幂平方表。",
                    "code_line": 1,
                }
            ],
        }
    )
    sieve_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "埃氏筛",
            "input_data": {"n": 10},
            "result": [2, 3, 5, 7],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "is_prime[9]"}],
                    "state": {"n": 10, "is_prime": [False, False, True, True, False, True, False, True, False, True, False]},
                    "reason": "错误筛法倍数标记。",
                    "code_line": 1,
                }
            ],
        }
    )
    combination_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "组合数 Pascal",
            "input_data": {"n": 5, "k": 2},
            "result": 10,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "table[5][2]"}],
                    "state": {"n": 5, "k": 2, "table": [[1, 0, 0], [1, 1, 0], [1, 2, 1], [1, 3, 3], [1, 4, 6], [1, 99, 99]]},
                    "reason": "错误组合数表。",
                    "code_line": 1,
                }
            ],
        }
    )
    bitmask_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "位掩码枚举子集",
            "input_data": {"nums": [1, 2, 3]},
            "result": [[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "bits[1]"}],
                    "state": {"nums": [1, 2, 3], "mask": 5, "bits": [1, 1, 1], "subset": [1, 2, 3]},
                    "reason": "错误位掩码位图。",
                    "code_line": 1,
                }
            ],
        }
    )
    lowbit_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "lowbit 分解",
            "input_data": {"n": 12},
            "result": [4, 8],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "lowbits[0]"}],
                    "state": {"n": 12, "remaining": 12, "lowbit": 99, "bits": [0, 0, 1, 1], "lowbits": [99]},
                    "reason": "错误 lowbit。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("最大公约数" in error or "GCD" in error for error in gcd_errors), gcd_errors
    assert any("快速幂" in error for error in fast_power_errors), fast_power_errors
    assert any("筛法" in error for error in sieve_errors), sieve_errors
    assert any("组合数" in error for error in combination_errors), combination_errors
    assert any("位掩码" in error for error in bitmask_errors), bitmask_errors
    assert any("lowbit" in error for error in lowbit_errors), lowbit_errors


def test_phase7_math_bit_group_has_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "gcd_euclid": {
            "layout": "array",
            "state_keys": {"a", "b", "remainders", "answer"},
            "target_prefix": "remainders[",
            "reason_tokens": ("最大公约数", "不变量"),
        },
        "fast_power_mod": {
            "layout": "array",
            "state_keys": {"base", "exponent", "mod", "bits", "powers", "answer"},
            "target_prefix": "powers[",
            "reason_tokens": ("快速幂", "指数"),
        },
        "sieve_primes": {
            "layout": "array",
            "state_keys": {"n", "is_prime", "current", "multiples", "answer"},
            "target_prefix": "is_prime[",
            "reason_tokens": ("筛法", "倍数"),
        },
        "combinations_pascal": {
            "layout": "matrix",
            "state_keys": {"n", "k", "table", "answer"},
            "target_prefix": "table[",
            "reason_tokens": ("组合数", "帕斯卡"),
        },
        "bitmask_subsets": {
            "layout": "array",
            "state_keys": {"nums", "mask", "bits", "subset", "answer"},
            "target_prefix": "bits[",
            "reason_tokens": ("位掩码", "子集"),
        },
        "lowbit_decomposition": {
            "layout": "array",
            "state_keys": {"n", "remaining", "bits", "lowbits", "answer"},
            "target_prefix": "lowbits[",
            "reason_tokens": ("lowbit", "最低位"),
        },
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert expectation["layout"] in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expectation["layout"] in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        dep_ids = {dep.id for event in trace.events for dep in event.deps}
        assert not any(item.startswith("number:") for item in target_ids | dep_ids), (case_id, target_ids | dep_ids)
        assert any(target.startswith(expectation["target_prefix"]) for target in target_ids | dep_ids), (case_id, target_ids, dep_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        for token in expectation["reason_tokens"]:
            assert token in reasons, (case_id, token, reasons)

    example_names = {
        "math_gcd.md": ["remainders", "最大公约数", "不变量"],
        "math_fast_power.md": ["powers", "bits", "快速幂"],
        "math_sieve.md": ["is_prime", "筛法", "倍数"],
        "math_combinations.md": ["table", "组合数", "帕斯卡"],
        "bitmask_subsets.md": ["bits", "mask", "子集"],
        "bit_lowbit.md": ["lowbits", "lowbit", "最低位"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_advanced_graph_invariants():
    tarjan_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Tarjan 强连通分量",
            "input_data": {"graph": {"A": ["B"], "B": ["A"]}},
            "result": [["A", "B"]],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "low[A]"}],
                    "state": {
                        "graph": {"A": ["B"], "B": ["A"]},
                        "dfn": {"A": 1, "B": 2},
                        "low": {"A": 3, "B": 1},
                        "stack": ["A", "B"],
                        "on_stack": {"A": True, "B": True},
                    },
                    "reason": "错误 lowlink。",
                    "code_line": 1,
                }
            ],
        }
    )
    bridge_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "割点和桥 Tarjan",
            "input_data": {"graph": {"A": ["B"], "B": ["A", "C"], "C": ["B"]}},
            "result": {"articulation": ["B"], "bridges": [["A", "B"], ["B", "C"]]},
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "edge:A->B"}],
                    "state": {
                        "graph": {"A": ["B"], "B": ["A", "C"], "C": ["B"]},
                        "dfn": {"A": 1, "B": 2, "C": 3},
                        "low": {"A": 1, "B": 1, "C": 3},
                        "parent": {"A": None, "B": "A", "C": "B"},
                        "bridges": [["A", "B"]],
                        "articulation": [],
                    },
                    "role": "bridge",
                    "reason": "错误桥判定。",
                    "code_line": 1,
                }
            ],
        }
    )
    matching_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分图匹配",
            "input_data": {"graph": {"L1": ["R1"], "L2": ["R1"]}, "left": ["L1", "L2"], "right": ["R1"]},
            "result": {"L1": "R1", "L2": "R1"},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "match[L2]"}],
                    "state": {
                        "graph": {"L1": ["R1"], "L2": ["R1"]},
                        "left_nodes": ["L1", "L2"],
                        "right_nodes": ["R1"],
                        "match": {"L1": "R1", "L2": "R1", "R1": "L2"},
                        "visited": {"R1": True},
                    },
                    "reason": "错误匹配：两个左侧点匹配同一个右侧点。",
                    "code_line": 1,
                }
            ],
        }
    )
    flow_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Edmonds-Karp 最大流",
            "input_data": {"graph": {"S": ["A"], "A": ["T"], "T": []}, "source": "S", "sink": "T"},
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "flow[S->A]"}],
                    "state": {
                        "graph": {"S": ["A"], "A": ["T"], "T": []},
                        "capacity": {"S->A": 2, "A->T": 2},
                        "flow": {"S->A": 3, "A->T": 1},
                        "queue": ["S"],
                        "parent": {"A": "S", "T": "A"},
                        "bottleneck": 3,
                    },
                    "reason": "错误 flow 超过容量。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("Tarjan" in error or "low" in error for error in tarjan_errors), tarjan_errors
    assert any("桥" in error or "bridge" in error.lower() for error in bridge_errors), bridge_errors
    assert any("匹配" in error or "match" in error.lower() for error in matching_errors), matching_errors
    assert any("flow" in error.lower() or "容量" in error for error in flow_errors), flow_errors


def test_phase7_advanced_graph_group_has_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "tarjan_scc": {
            "state_keys": {"graph", "dfn", "low", "stack", "on_stack", "component"},
            "target_prefixes": ("dfn[", "low[", "node:", "edge:"),
            "reason_tokens": ("Tarjan", "low"),
        },
        "articulation_bridges": {
            "state_keys": {"graph", "dfn", "low", "parent", "bridges", "articulation"},
            "target_prefixes": ("dfn[", "low[", "node:", "edge:"),
            "reason_tokens": ("割点", "桥"),
        },
        "bipartite_matching": {
            "state_keys": {"graph", "match", "visited", "left_nodes", "right_nodes"},
            "target_prefixes": ("match[", "node:", "edge:"),
            "reason_tokens": ("匹配", "增广"),
        },
        "edmonds_karp": {
            "state_keys": {"graph", "capacity", "flow", "queue", "parent", "bottleneck"},
            "target_prefixes": ("cap[", "flow[", "node:", "edge:"),
            "reason_tokens": ("Edmonds-Karp", "残量"),
        },
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert "graph" in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert "graph" in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        dep_ids = {dep.id for event in trace.events for dep in event.deps}
        assert not any(item.startswith("flow:") for item in target_ids | dep_ids), (case_id, target_ids | dep_ids)
        for prefix in expectation["target_prefixes"]:
            assert any(item.startswith(prefix) for item in target_ids | dep_ids), (case_id, prefix, target_ids, dep_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        for token in expectation["reason_tokens"]:
            assert token in reasons, (case_id, token, reasons)

    example_names = {
        "graph_tarjan_scc.md": ["dfn", "low", "stack", "Tarjan"],
        "graph_articulation_bridges.md": ["dfn", "low", "桥", "割点"],
        "graph_bipartite_matching.md": ["match[", "增广", "匹配"],
        "graph_edmonds_karp.md": ["capacity", "flow[", "残量"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


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
    assert classify_failure("严格模式拒绝 warning：failure_type=coverage_error: BFS 小图缺少关键步骤覆盖：check_edge") == "coverage_error"
    assert classify_failure("第 3 步 dp[2] 不满足 0-1 背包可达性") == "process_invariant"
    assert classify_failure("failure_type=coverage_error: 小 DP 表缺少逐帧状态转移") == "coverage_error"
    assert classify_failure("failure_type=process_uncovered: 未注册算法族只执行基础门禁") == "process_uncovered"
    assert classify_failure("第 1 步 union_find 存在非根环") == "process_invariant"
    assert classify_failure("第 2 步 二分收缩方向错误：nums[1] < target") == "process_invariant"
    assert classify_failure("第 4 步 BFS 首次发现 node:B 来源应为上一层相邻节点") == "process_invariant"
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
    assert report["model_config"]["model"] == "demo-model"
    assert report["model_config"]["llm"]["base_url"] == "http://example.invalid/v1"
    assert report["repair_summary"]["max_rounds_configured"] == 2
    assert report["repair_summary"]["cases_with_repair"] == 1
    assert report["repair_summary"]["repair_rounds_attempted"] == 1
    assert report["repair_summary"]["repair_successes"] == 1
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
        "/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py"
    )
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
    assert "scripts/run_quality_checks.py" in commands_text
    assert "scripts/run_llm_benchmark.py" in commands_text


def test_v1_release_gate_report_records_release_requirements(tmp_path: Path):
    report = build_v1_release_gate_report()

    assert report["schema_version"] == "v1-release-gate-v1"
    assert report["overall_ready"] is True
    assert report["commands"]["quality_checks"] == (
        "/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py"
    )
    deterministic = report["checks"]["deterministic_benchmark"]
    assert 80 <= deterministic["benchmark_sample_count"] <= 120
    assert deterministic["benchmark_sample_count"] == sum(len(case.samples) for case in benchmark_cases())
    assert deterministic["status"] == "pass"

    golden = report["checks"]["golden_browser_smoke"]
    assert golden["status"] == "pass"
    assert {"unique_paths", "graph_bfs", "binary_search", "daily_temperatures"} <= set(golden["required_cases"])
    assert golden["covered_by"] == "scripts/run_quality_checks.py -> tests.browser_smoke.run_all"

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
    test_process_validator_rejects_missing_key_step_coverage_for_small_traces()
    test_process_validator_rejects_bad_string_algorithm_tables()
    test_convex_hull_trace_exposes_scan_phases_and_pop_steps()
    test_phase7_string_algorithms_have_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_tree_recursion_aggregates()
    test_phase7_tree_recursion_group_has_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_range_structure_tables()
    test_phase7_range_structures_have_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_math_bit_invariants()
    test_phase7_math_bit_group_has_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_advanced_graph_invariants()
    test_phase7_advanced_graph_group_has_benchmarks_visual_state_and_examples()
    test_contract_tests_block_bad_solve()
    test_llm_benchmark_request_uses_problem_and_expected()
    test_llm_benchmark_sample_selection_and_failure_classification(Path(tempfile.gettempdir()))
    test_benchmark_report_summarizes_process_registry_failure_types(Path(tempfile.gettempdir()))
    test_llm_benchmark_phase_timing_helpers()
    test_llm_json_and_spec_normalization_helpers()
    test_existing_benchmark_html_report_helper(Path(tempfile.gettempdir()))
    test_benchmark_html_checker_resolves_required_phase8_cases(Path(tempfile.gettempdir()))
    test_demo_dashboard_selection_defaults_to_curated_showcase()
    test_runtime_capabilities_prompt_context_is_json()

    with tempfile.TemporaryDirectory() as d:
        test_llm_client_reads_local_api_settings_without_committing_key(Path(d))
        test_benchmark_aggregate_artifact(Path(d))
        test_demo_dashboard_writes_bundle_and_index(Path(d))
        test_evaluation_manifest_covers_phase10_datasets(Path(d))
        test_evaluation_report_exports_phase10_metrics_and_core_tables(Path(d))
        test_evaluation_report_summarizes_baseline_ablation_conditions(Path(d))
        test_reproducibility_package_records_environment_commands_samples_and_modes(Path(d))
        test_v1_release_gate_report_records_release_requirements(Path(d))
    test_creative_renderer_contains_theme_controls_and_stage()


if __name__ == "__main__":
    run_all()
    print("benchmark_regression: PASS")
