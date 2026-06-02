"""Regression tests for SceneGraph edge/node binding."""

from __future__ import annotations

from algolab.compiler.scene_compiler import compile_scene
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.verification.scene_validator import validate_scene
from algolab.verification.trace_validator import validate_trace


def _trace_with_event(
    *,
    state: dict,
    targets: list[str],
    deps: list[str] | None = None,
    input_data: dict | None = None,
) -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Scene edge binding regression",
            "input_data": input_data or {},
            "result": None,
            "pseudocode": ["compile scene"],
            "events": [
                {
                    "step": 0,
                    "op": "compare",
                    "targets": [{"id": target} for target in targets],
                    "deps": [{"id": dep} for dep in (deps or [])],
                    "state": state,
                    "reason": "检查 SceneGraph edge/node 绑定。",
                    "code_line": 1,
                }
            ],
        }
    )


def _scene_warnings(*, state: dict, targets: list[str], deps: list[str] | None = None) -> list[str]:
    scene = compile_scene(_trace_with_event(state=state, targets=targets, deps=deps))
    errors, warnings = validate_scene(scene)
    assert errors == [], errors
    return warnings


def _binding_warnings(warnings: list[str]) -> list[str]:
    return [warning for warning in warnings if "不在对象集合" in warning or "不存在" in warning]


def test_graph_state_edge_generates_neighbor_node_for_binding():
    warnings = _scene_warnings(state={"graph": {"A": ["B"]}}, targets=["edge:A->B", "edge:A-B"])

    assert not _binding_warnings(warnings), warnings


def test_edge_list_state_generates_endpoint_nodes_for_binding():
    warnings = _scene_warnings(
        state={"edges": [["A", "B", 4], ["A", "C", 2], ["B", "C", -1]], "dist": {"A": 0, "B": 4, "C": 2}},
        targets=["edge:A->B", "edge:A->C", "edge:B->C"],
    )

    assert not _binding_warnings(warnings), warnings


def test_weighted_graph_input_generates_endpoint_nodes_for_binding():
    trace = _trace_with_event(
        input_data={"weighted_graph": {"A": [["B", 1]], "B": []}, "start": "A"},
        state={"dist": {"A": 0}, "current": "A"},
        targets=["edge:A->B"],
        deps=["node:A", "node:B"],
    )
    trace_errors, trace_warnings = validate_trace(trace)
    scene = compile_scene(trace)
    scene_errors, scene_warnings = validate_scene(scene)

    assert trace_errors == [], trace_errors
    assert not any("节点未在状态或输入图中出现" in warning for warning in trace_warnings), trace_warnings
    assert scene_errors == [], scene_errors
    assert not _binding_warnings(scene_warnings), scene_warnings


def test_linked_list_state_edge_generates_endpoint_nodes_for_binding():
    warnings = _scene_warnings(
        state={"linked_list": {"nodes": [{"id": "1"}, {"id": "2"}], "edges": [["1", "2"]]}},
        targets=["edge:1->2"],
    )

    assert not _binding_warnings(warnings), warnings


def test_segment_tree_state_accepts_source_target_edge_keys_for_binding():
    warnings = _scene_warnings(
        state={
            "segment_tree": {
                "nodes": [{"id": "root"}, {"id": "left"}],
                "edges": [{"source": "root", "target": "left"}],
            }
        },
        targets=["node:root"],
        deps=["node:left"],
    )

    assert not any("node:None" in warning for warning in warnings), warnings
    assert not _binding_warnings(warnings), warnings


def test_bipartite_graph_state_edge_generates_right_side_node_for_binding():
    warnings = _scene_warnings(
        state={"graph": {"L1": ["R1"]}, "left_nodes": ["L1"], "right_nodes": ["R1"]},
        targets=["edge:L1->R1"],
    )

    assert not _binding_warnings(warnings), warnings


def test_points_state_generates_indexed_point_objects_for_binding():
    warnings = _scene_warnings(state={"points": [[0, 0], [1, 1]]}, targets=["points[0]"], deps=["points[1]"])

    assert not _binding_warnings(warnings), warnings


def test_missing_state_node_reference_still_warns():
    warnings = _scene_warnings(state={"graph": {"A": ["B"]}}, targets=["node:Z"])

    assert any("node:Z" in warning and "不存在" in warning for warning in warnings), warnings


def run_all() -> None:
    test_graph_state_edge_generates_neighbor_node_for_binding()
    test_edge_list_state_generates_endpoint_nodes_for_binding()
    test_weighted_graph_input_generates_endpoint_nodes_for_binding()
    test_linked_list_state_edge_generates_endpoint_nodes_for_binding()
    test_segment_tree_state_accepts_source_target_edge_keys_for_binding()
    test_bipartite_graph_state_edge_generates_right_side_node_for_binding()
    test_points_state_generates_indexed_point_objects_for_binding()
    test_missing_state_node_reference_still_warns()


if __name__ == "__main__":
    run_all()
    print("scene_edge_binding: PASS")
