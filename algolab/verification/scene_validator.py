"""Scene graph validation."""

from __future__ import annotations

from typing import Any

from algolab.schemas.scene_graph import SceneGraph


VISIBLE_TYPES = {
    "cell",
    "node",
    "edge",
    "label",
    "pointer",
    "callout",
    "tensor",
    "batch",
    "parameter",
    "loss_curve",
    "gradient_vector",
    "decision_boundary",
    "training_epoch",
    "prediction",
}


def validate_scene(scene: SceneGraph) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if scene.schema_version != "scene-graph-v1":
        errors.append("scene schema_version 必须是 scene-graph-v1")
    if not scene.frames:
        errors.append("scene 必须包含至少一个 frame")
        return errors, warnings

    for frame in scene.frames:
        if not frame.objects:
            errors.append(f"第 {frame.step} 帧没有任何 scene object")
            continue
        object_ids = {obj.id for obj in frame.objects}
        if len(object_ids) != len(frame.objects):
            errors.append(f"第 {frame.step} 帧存在重复 scene object id")
        visible = [obj for obj in frame.objects if obj.type.value in VISIBLE_TYPES]
        if not visible:
            errors.append(f"第 {frame.step} 帧没有可见对象")
        for mark in frame.marks:
            if mark.target not in object_ids:
                errors.append(f"第 {frame.step} 帧 mark 指向不存在对象：{mark.target}")
        for obj in frame.objects:
            if obj.parent and obj.parent not in object_ids:
                errors.append(
                    f"第 {frame.step} 帧对象 {obj.id} parent 指向不存在对象：{obj.parent}"
                )
            if obj.source and obj.source not in object_ids:
                errors.append(
                    f"第 {frame.step} 帧对象 {obj.id} source 指向不存在对象：{obj.source}"
                )
            if obj.target and obj.target not in object_ids:
                errors.append(
                    f"第 {frame.step} 帧对象 {obj.id} target 指向不存在对象：{obj.target}"
                )
    return errors, warnings


def _state_node_ids(state: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    if "nodes" in state:
        result.update(_node_ids_from_node_edge_struct({"nodes": state.get("nodes"), "edges": state.get("edges")}))
        result.add("node:nodes")
    for key in ("graph", "adjacency", "weighted_graph"):
        graph = state.get(key)
        if isinstance(graph, dict):
            result.update(_graph_node_ids(graph))
    for key in ("edges", "weighted_edges", "edge_list", "mst_edges", "tree_edges"):
        result.update(_edge_list_node_ids(state.get(key)))
    for key in ("left_nodes", "right_nodes"):
        result.update(f"node:{item}" for item in _as_string_list(state.get(key)))
    for key in ("tree", "binary_tree", "segment_tree", "trie", "linked_list", "recursion_tree", "search_tree", "call_tree"):
        struct = state.get(key)
        if isinstance(struct, dict):
            result.update(_node_ids_from_node_edge_struct(_normalize_trie_struct(struct) if key == "trie" else struct))
    for key, struct in state.items():
        if _is_trie_state(key, struct):
            result.update(_node_ids_from_node_edge_struct(_normalize_trie_struct(struct)))
    for key in ("union_find", "dsu"):
        union_find = state.get(key)
        parent = union_find.get("parent") if isinstance(union_find, dict) else None
        if isinstance(parent, dict):
            for node, par in parent.items():
                result.add(f"node:{node}")
                result.add(f"node:{par}")
    return result


def _graph_node_ids(graph: dict[Any, Any]) -> set[str]:
    result: set[str] = set()
    for node, neighbors in graph.items():
        result.add(f"node:{node}")
        for neighbor in _graph_neighbor_items(neighbors):
            neighbor_id = _neighbor_id(neighbor)
            if neighbor_id:
                result.add(f"node:{neighbor_id}")
    return result


def _graph_neighbor_items(neighbors: Any) -> list[Any]:
    if isinstance(neighbors, dict):
        return list(neighbors.keys())
    if isinstance(neighbors, list):
        return neighbors
    return []


def _edge_list_node_ids(edges: Any) -> set[str]:
    result: set[str] = set()
    if not isinstance(edges, list):
        return result
    for edge in edges:
        src, dst = _edge_endpoints(edge)
        if src:
            result.add(f"node:{src}")
        if dst:
            result.add(f"node:{dst}")
    return result


def _node_ids_from_node_edge_struct(struct: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for node_key, node in _node_entries(struct.get("nodes")):
        node_id = _node_id(node, fallback=node_key)
        if node_id:
            result.add(f"node:{node_id}")
    for edge in struct.get("edges") or []:
        src, dst = _edge_endpoints(edge)
        if src:
            result.add(f"node:{src}")
        if dst:
            result.add(f"node:{dst}")
    return result


def _normalize_trie_struct(struct: dict[str, Any]) -> dict[str, Any]:
    nodes = struct.get("nodes") or []
    edges = list(struct.get("edges") or [])
    if not edges and isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            src = node.get("id")
            children = node.get("children")
            if src is None or not isinstance(children, dict):
                continue
            for dst in children.values():
                edges.append([src, dst])
    return {"nodes": nodes, "edges": edges}


def _is_trie_state(key: str, value: Any) -> bool:
    if not isinstance(value, dict) or "trie" not in str(key).lower():
        return False
    nodes = value.get("nodes")
    return isinstance(nodes, list) and any(isinstance(node, dict) and isinstance(node.get("children"), dict) for node in nodes)


def _node_entries(nodes: Any) -> list[tuple[Any, Any]]:
    if isinstance(nodes, dict):
        return list(nodes.items())
    if isinstance(nodes, list):
        return [
            (node.get("id", index) if isinstance(node, dict) else node, node)
            for index, node in enumerate(nodes)
        ]
    return []


def _neighbor_id(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("to", "target", "id", "node"):
            if value.get(key) not in (None, ""):
                return str(value.get(key))
        return ""
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    return str(value)


def _node_id(value: Any, *, fallback: Any = None) -> str:
    if isinstance(value, dict):
        raw = value.get("id", fallback)
        return "" if raw in (None, "") else str(raw)
    raw = fallback if value in (None, "") else value
    return "" if raw in (None, "") else str(raw)


def _edge_endpoints(edge: Any) -> tuple[str, str]:
    if isinstance(edge, dict):
        src = edge.get("from", edge.get("source"))
        dst = edge.get("to", edge.get("target"))
        return ("" if src in (None, "") else str(src), "" if dst in (None, "") else str(dst))
    if isinstance(edge, (list, tuple)) and len(edge) >= 2:
        return str(edge[0]), str(edge[1])
    return "", ""


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]
