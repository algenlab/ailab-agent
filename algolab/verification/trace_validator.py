"""Semantic trace validation beyond Pydantic shape checks."""

from __future__ import annotations

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
            if " " in target.id:
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
            if parsed.kind == "map" and target.id not in known_targets and parsed.name not in known_targets:
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
            known.add(key)
            if _is_matrix(value):
                for r, row in enumerate(value):
                    known.add(f"{key}[{r}]")
                    for c, _ in enumerate(row):
                        known.add(f"{key}[{r}][{c}]")
            elif _is_scalar_list(value):
                for i, _ in enumerate(value):
                    known.add(f"{key}[{i}]")
            elif isinstance(value, str):
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
                elif _is_geometry_like(key, value):
                    for i, point in enumerate(value.get("points") or []):
                        point_id = str(point.get("id", i) if isinstance(point, dict) else i)
                        known.add(f"point:{point_id}")
                elif key in {"graph", "adjacency"} or all(isinstance(v, list) for v in value.values()):
                    for node, neighbors in value.items():
                        known.add(f"node:{node}")
                        for nei in neighbors if isinstance(neighbors, list) else []:
                            known.add(f"node:{nei}")
                            known.add(f"edge:{node}->{nei}")
                else:
                    for mk in value:
                        known.add(f"{key}[{mk}]")
    if isinstance(trace.input_data, dict):
        graph = trace.input_data.get("graph") or trace.input_data.get("adjacency")
        if isinstance(graph, dict):
            for node, neighbors in graph.items():
                known.add(f"node:{node}")
                for nei in neighbors if isinstance(neighbors, list) else []:
                    known.add(f"node:{nei}")
                    known.add(f"edge:{node}->{nei}")
        tree = trace.input_data.get("tree")
        if isinstance(tree, dict):
            _add_tree_targets(known, tree)
        points = trace.input_data.get("points")
        if isinstance(points, list):
            for i, _point in enumerate(points):
                known.add(f"points[{i}]")
                known.add(f"point:{i}")
    return known


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


def _is_scalar_list(value) -> bool:
    return isinstance(value, list) and all(not isinstance(x, (list, dict)) for x in value)


def _is_matrix(value) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(row, list) for row in value)
        and len({len(row) for row in value}) <= 1
    )


def _slice_in_known_targets(name, indices, known_targets) -> bool:
    if len(indices) != 2:
        return False
    start, end = indices
    return start <= end and all(f"{name}[{i}]" in known_targets for i in range(start, end))


def _is_tree_like(key, value) -> bool:
    return key in {"tree", "binary_tree", "segment_tree", "trie", "recursion_tree", "call_tree", "search_tree"} and "nodes" in value and "edges" in value


def _is_union_find_like(key, value) -> bool:
    return key in {"union_find", "dsu"} and isinstance(value.get("parent"), dict)


def _is_geometry_like(key, value) -> bool:
    return key in {"geometry", "plane", "sweep"} and isinstance(value.get("points"), list)
