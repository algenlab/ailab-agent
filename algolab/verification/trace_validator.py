"""Semantic trace validation beyond Pydantic shape checks."""

from __future__ import annotations

from algolab.compiler.object_resolver import basic_state_target_ids
from algolab.compiler.target_parser import parse_target
from algolab.schemas.semantic_trace import SemanticOp, SemanticTrace


def validate_trace(trace: SemanticTrace) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if trace.schema_version != "semantic-trace-v1":
        errors.append("trace schema_version 必须是 semantic-trace-v1")
    if len(trace.events) < 2:
        warnings.append("trace 步数很少，可能缺少关键过程")

    seen_explain = False
    known_targets = _known_targets_from_trace(trace)
    for i, event in enumerate(trace.events):
        if event.step != i:
            errors.append(f"第 {i} 个事件 step 不连续")
        if event.op != SemanticOp.EXPLAIN and not event.targets and event.op not in {SemanticOp.ENTER, SemanticOp.EXIT}:
            warnings.append(f"第 {i} 步没有 target，视觉定位可能不清晰")
        if event.reason:
            seen_explain = True
        for target in [*event.targets, *event.deps]:
            if " " in target.id and target.id not in known_targets:
                warnings.append(f"第 {i} 步 target 含空格：{target.id}")
            if _looks_like_legacy_map_target(target.id):
                errors.append(f"第 {i} 步旧式 map target 已废弃，请使用方括号格式：{target.id}")
            parsed = parse_target(target.id)
            if parsed.kind == "edge" and (not parsed.source or not parsed.target):
                errors.append(f"第 {i} 步 edge target 格式非法：{target.id}")
            if parsed.kind == "indexed" and target.id not in known_targets:
                errors.append(f"第 {i} 步引用了不存在的索引 target：{target.id}")
            if parsed.kind == "slice" and not _slice_in_known_targets(parsed.name, parsed.indices, known_targets):
                errors.append(f"第 {i} 步引用了不存在的切片 target：{target.id}")
            if (
                parsed.kind == "map"
                and target.id not in known_targets
                and parsed.name not in known_targets
                and _map_base_name(target.id) not in known_targets
            ):
                errors.append(f"第 {i} 步引用了不存在的 map target：{target.id}")
            if parsed.kind == "node" and known_targets and target.id not in known_targets:
                warnings.append(f"第 {i} 步引用的节点未在状态或输入图中出现：{target.id}")
        if event.interaction and event.interaction.type == "choice":
            if not event.interaction.options:
                errors.append(f"第 {i} 步 choice 交互缺少 options")
    if not seen_explain:
        warnings.append("trace 缺少 reason，教学解释不足")

    return errors, warnings


def _known_targets_from_trace(trace: SemanticTrace) -> set[str]:
    known: set[str] = set()
    for event in trace.events:
        for key, value in (event.state or {}).items():
            if isinstance(value, dict) and (
                _is_tree_like(key, value)
                or _is_union_find_like(key, value)
                or _is_geometry_like(key, value)
                or _looks_like_graph_dict(key, value)
            ):
                known.add(key)
            else:
                known.update(basic_state_target_ids({key: value}))
            if isinstance(value, str):
                for i, _ in enumerate(value):
                    known.add(f"{key}[{i}]")
            elif isinstance(value, dict):
                if _is_tree_like(key, value):
                    for node in value.get("nodes") or []:
                        node_id = str(node.get("id") if isinstance(node, dict) else node)
                        known.add(f"node:{node_id}")
                    for edge in value.get("edges") or []:
                        if isinstance(edge, dict):
                            src, dst = str(edge.get("from")), str(edge.get("to"))
                        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
                            src, dst = str(edge[0]), str(edge[1])
                        else:
                            continue
                        known.add(f"node:{src}")
                        known.add(f"node:{dst}")
                        known.add(f"edge:{src}->{dst}")
                elif _is_union_find_like(key, value):
                    parent = value.get("parent") or {}
                    for node, par in parent.items():
                        known.add(f"node:{node}")
                        known.add(f"node:{par}")
                        if node != par:
                            known.add(f"edge:{node}->{par}")
                elif _is_linked_list_like(value):
                    numeric_ids: list[int] = []
                    for node in value.get("nodes") or []:
                        if not isinstance(node, dict):
                            continue
                        node_id = node.get("id")
                        if node_id not in (None, ""):
                            known.add(f"node:{node_id}")
                            if isinstance(node_id, int):
                                numeric_ids.append(node_id)
                        next_id = node.get("next")
                        if node_id not in (None, "") and next_id not in (None, ""):
                            known.add(f"node:{next_id}")
                            known.add(f"edge:{node_id}->{next_id}")
                    if numeric_ids:
                        known.add(f"node:{max(numeric_ids) + 1}")
                elif _is_geometry_like(key, value):
                    for i, point in enumerate(value.get("points") or []):
                        point_id = str(point.get("id", i) if isinstance(point, dict) else i)
                        known.add(f"point:{point_id}")
                elif _looks_like_graph_dict(key, value):
                    _add_graph_targets(known, value)
                else:
                    for mk in value:
                        known.add(f"{key}[{mk}]")
    if isinstance(trace.input_data, dict):
        graph = trace.input_data.get("graph") or trace.input_data.get("adjacency") or trace.input_data.get("weighted_graph")
        if isinstance(graph, dict):
            _add_graph_targets(known, graph)
        edge_list = trace.input_data.get("edges") or trace.input_data.get("edge_list")
        if isinstance(edge_list, list):
            _add_edge_list_targets(known, edge_list)
        tree = trace.input_data.get("tree")
        if isinstance(tree, dict):
            _add_tree_targets(known, tree)
        points = trace.input_data.get("points")
        if isinstance(points, list):
            for i, _point in enumerate(points):
                known.add(f"points[{i}]")
                known.add(f"point:{i}")
    return known


def _looks_like_graph_dict(key: str, value: dict) -> bool:
    if key in {"graph", "adjacency", "weighted_graph"}:
        return True
    return bool(value) and all(isinstance(v, (dict, list)) for v in value.values())


def _add_graph_targets(known: set[str], graph: dict) -> None:
    for node, neighbors in graph.items():
        known.add(f"node:{node}")
        for neighbor in _graph_neighbor_items(neighbors):
            neighbor_id = _neighbor_id(neighbor)
            if not neighbor_id:
                continue
            known.add(f"node:{neighbor_id}")
            known.add(f"edge:{node}->{neighbor_id}")


def _graph_neighbor_items(neighbors) -> list:
    if isinstance(neighbors, dict):
        return list(neighbors.keys())
    if isinstance(neighbors, list):
        return neighbors
    return []


def _neighbor_id(value) -> str:
    if isinstance(value, dict):
        for key in ("to", "target", "id", "node"):
            if value.get(key) not in (None, ""):
                return str(value.get(key))
        return ""
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    return "" if value in (None, "") else str(value)


def _add_edge_list_targets(known: set[str], edges: list) -> None:
    for edge in edges:
        if isinstance(edge, dict):
            src = edge.get("from", edge.get("source", edge.get("u")))
            dst = edge.get("to", edge.get("target", edge.get("v")))
        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
            src, dst = edge[0], edge[1]
        else:
            continue
        if src in (None, "") or dst in (None, ""):
            continue
        src_text, dst_text = str(src), str(dst)
        known.add(f"node:{src_text}")
        known.add(f"node:{dst_text}")
        known.add(f"edge:{src_text}->{dst_text}")


def _add_tree_targets(known: set[str], tree: dict) -> None:
    for node in tree.get("nodes") or []:
        node_id = str(node.get("id") if isinstance(node, dict) else node)
        known.add(f"node:{node_id}")
    for edge in tree.get("edges") or []:
        if isinstance(edge, dict):
            src, dst = str(edge.get("from")), str(edge.get("to"))
        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
            src, dst = str(edge[0]), str(edge[1])
        else:
            continue
        known.add(f"node:{src}")
        known.add(f"node:{dst}")
        known.add(f"edge:{src}->{dst}")


def _looks_like_legacy_map_target(target_id: str) -> bool:
    if target_id.startswith("map:"):
        return True
    key, sep, item = target_id.partition(":")
    if not sep:
        return False
    if target_id.startswith(("node:", "edge:", "pointer:", "frame:", "point:", "char:")):
        return False
    if "[" in key or "]" in key:
        return False
    return bool(item) and key.isidentifier() and "->" not in item


def _map_base_name(target_id: str) -> str:
    return target_id.split("[", 1)[0] if "[" in target_id else ""


def _is_scalar_list(value) -> bool:
    return isinstance(value, list) and all(not isinstance(x, (list, dict)) for x in value)


def _is_string_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def _is_matrix(value) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(row, list) for row in value)
    )


def _slice_in_known_targets(name, indices, known_targets) -> bool:
    if len(indices) != 2:
        return False
    start, end = indices
    return start <= end and all(f"{name}[{i}]" in known_targets for i in range(start, end))


def _is_tree_like(key, value) -> bool:
    if key in {"tree", "binary_tree", "segment_tree", "recursion_tree", "call_tree", "search_tree"}:
        return "nodes" in value and "edges" in value
    if "trie" in str(key).lower():
        nodes = value.get("nodes")
        return isinstance(nodes, list) and (
            "edges" in value
            or any(isinstance(node, dict) and isinstance(node.get("children"), dict) for node in nodes)
        )
    return False


def _is_union_find_like(key, value) -> bool:
    return key in {"union_find", "dsu"} and isinstance(value.get("parent"), dict)


def _is_linked_list_like(value) -> bool:
    return isinstance(value.get("nodes"), list) and (
        "head" in value or any(isinstance(node, dict) and "next" in node for node in value.get("nodes") or [])
    )


def _is_geometry_like(key, value) -> bool:
    return key in {"geometry", "plane", "sweep"} and isinstance(value.get("points"), list)
