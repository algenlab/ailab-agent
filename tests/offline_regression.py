"""Offline regression suite.

This test suite does not call the LLM. It validates the stable architecture:
schema -> validator -> scene compiler -> renderer -> sandbox.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from algolab.compiler.scene_compiler import compile_scene
from algolab.pipeline import _try_materialize
from algolab.renderer.export import save_html
from algolab.runtime.sandbox import SandboxError, run_function
from algolab.runtime.executor import execute_variant
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.schemas.input import ProblemInput
from algolab.schemas.scene_graph import SceneGraph
from algolab.verification.scene_validator import validate_scene
from algolab.verification.process_validator import validate_process
from algolab.verification.trace_validator import validate_trace
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


def test_renderer_writes_html(tmp_path: Path):
    out = save_html(fixture_artifact(), tmp_path / "fixture.html")
    html = out.read_text(encoding="utf-8")
    assert "离线打家劫舍" in html
    assert "SemanticTrace" not in html
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


def test_pipeline_bad_verifier_blocks_release():
    request = ProblemInput(problem="常量题", input_data={"x": 1}, expected_result=1)
    artifact, errors = _try_materialize(request, _good_spec("def verify(input_data):\n    return 2"))
    assert not artifact.validation.release_gate.release_ready
    assert errors


def run_all():
    tests = [
        test_schema_rejects_non_contiguous_steps,
        test_trace_validator_rejects_unknown_index_target,
        test_trace_validator_accepts_map_bracket_and_slice_targets,
        test_trace_validator_accepts_input_tree_and_points_targets,
        test_execute_variant_normalizes_quoted_map_targets,
        test_execute_variant_rejects_excessive_trace_events,
        test_process_validator_accepts_map_container_dependency,
        test_semantic_event_normalizes_null_optional_text,
        test_process_validator_rejects_bad_unique_paths_transition,
        test_process_validator_rejects_bad_bfs_distance,
        test_process_validator_rejects_bad_subset_sum_transition,
        test_process_validator_rejects_binary_search_mid_outside_window,
        test_process_validator_rejects_bad_heap_and_union_find,
        test_process_validator_rejects_bad_monotonic_stack_and_topo,
        test_process_validator_rejects_bad_dijkstra_lcs_and_edit_distance,
        test_process_validator_rejects_bad_kmp_complete_knapsack_interval_dp,
        test_process_validator_rejects_bad_bst_lca_tarjan_mst_geometry_backtracking,
        test_process_validator_level_selection,
        test_scene_compiler_outputs_cells_and_arrows,
        test_scene_compiler_materializes_symbol_targets_as_labels,
        test_scene_compiler_binds_pointers_to_array_cells,
        test_scene_compiler_outputs_graph_nodes,
        test_classic_visual_layout_coverage,
        test_all_13_algorithm_families_have_fixture_and_layout,
        test_classic_subfamilies_have_deterministic_visual_coverage,
        test_sandbox_blocks_imports_and_times_out,
        test_execute_variant_requires_trace_input_data,
        test_execute_variant_normalizes_event_steps,
        test_scene_validator_rejects_empty_visual_frame,
        test_pipeline_requires_process_evidence,
        test_pipeline_expected_result_allows_single_solution_release,
        test_pipeline_bad_verifier_blocks_release,
    ]
    for test in tests:
        test()
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        test_renderer_writes_html(Path(d))


if __name__ == "__main__":
    run_all()
    print("offline_regression: PASS")
