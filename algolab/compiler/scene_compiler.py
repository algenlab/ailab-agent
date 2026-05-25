"""Compile semantic traces into stable visual scene graphs."""

from __future__ import annotations

from typing import Any

from algolab.compiler.target_parser import parse_target
from algolab.schemas.scene_graph import SceneFrame, SceneGraph, SceneObject, SceneObjectType, VisualMark
from algolab.schemas.semantic_trace import SemanticEvent, SemanticOp, SemanticTrace


def compile_scene(trace: SemanticTrace) -> SceneGraph:
    frames = [compile_frame(trace, event) for event in trace.events]
    return SceneGraph(
        algorithm=trace.algorithm,
        input_data=trace.input_data,
        result=trace.result,
        pseudocode=trace.pseudocode,
        frames=frames,
    )


def compile_frame(trace: SemanticTrace, event: SemanticEvent) -> SceneFrame:
    state = event.state or {}
    objects: list[SceneObject] = []
    marks: list[VisualMark] = []

    objects.extend(_objects_from_state(state, trace.input_data))
    objects.extend(_objects_from_refs([*event.targets, *event.deps], event))
    objects.extend(_dependency_arrows(event))

    for target in event.targets:
        if event.role:
            marks.append(VisualMark(target=target.id, role=event.role))
    for dep in event.deps:
        marks.append(VisualMark(target=dep.id, role="dependency"))

    if event.reason:
        objects.append(
            SceneObject(
                id=f"callout:{event.step}",
                type=SceneObjectType.CALLOUT,
                value=event.reason,
                label="说明",
                role="reason",
            )
        )

    title = _title_for_event(event)
    return SceneFrame(
        step=event.step,
        title=title,
        description=event.reason,
        operation=event.op.value,
        code_line=event.code_line,
        objects=_dedupe_objects(objects),
        marks=marks,
        state=state,
        interaction=event.interaction.model_dump() if event.interaction else None,
        teaching=_teaching_for_event(event),
        evidence=_evidence_for_event(event),
    )


def _title_for_event(event: SemanticEvent) -> str:
    op_name = {
        SemanticOp.CREATE: "初始化结构",
        SemanticOp.SET: "更新状态",
        SemanticOp.MARK: "标记对象",
        SemanticOp.UNMARK: "取消标记",
        SemanticOp.MOVE: "移动指针",
        SemanticOp.COMPARE: "比较候选",
        SemanticOp.LINK: "建立关系",
        SemanticOp.UNLINK: "删除关系",
        SemanticOp.PUSH: "压入容器",
        SemanticOp.POP: "弹出容器",
        SemanticOp.ENTER: "进入阶段",
        SemanticOp.EXIT: "退出阶段",
        SemanticOp.EXPLAIN: "解释",
    }.get(event.op, event.op.value)
    if event.targets:
        return f"{op_name}: {', '.join(t.id for t in event.targets[:3])}"
    return op_name


def _teaching_for_event(event: SemanticEvent) -> dict[str, str]:
    if event.teaching is not None:
        return event.teaching.model_dump()

    target_text = ", ".join(target.id for target in event.targets[:3])
    dep_text = ", ".join(dep.id for dep in event.deps[:3])
    what = _title_for_event(event)
    why = event.reason or "根据当前状态推进算法步骤。"
    hint_parts = []
    if target_text:
        hint_parts.append(f"关注 {target_text}")
    if dep_text:
        hint_parts.append(f"依赖 {dep_text}")
    return {
        "what": what,
        "why": why,
        "formula": "",
        "invariant": "",
        "common_mistake": "",
        "hint": "；".join(hint_parts),
    }


def _evidence_for_event(event: SemanticEvent) -> dict[str, Any]:
    return {
        "operation": event.op.value,
        "targets": [target.id for target in event.targets],
        "deps": [dep.id for dep in event.deps],
        "role": event.role,
        "value": event.value,
        "before": event.before,
        "after": event.after,
        "reason": event.reason,
        "code_line": event.code_line,
    }


def _objects_from_state(state: dict[str, Any], input_data: Any) -> list[SceneObject]:
    objects: list[SceneObject] = []

    for key, value in state.items():
        if _is_ml_state_like(key, value):
            objects.extend(_ml_objects(key, value))
        elif _is_recursion_tree_like(key, value):
            objects.extend(_tree_objects(key, value, layout="recursion_tree"))
        elif _is_tree_like(key, value):
            objects.extend(_tree_objects(key, value))
        elif _is_trie_like(key, value):
            objects.extend(_trie_objects(key, value))
        elif _is_union_find_like(key, value):
            objects.extend(_union_find_objects(key, value))
        elif _is_geometry_like(key, value):
            objects.extend(_geometry_objects(key, value))
        elif _is_points_like(key, value):
            objects.extend(_points_objects(key, value))
        elif isinstance(value, str) and _is_string_view_key(key):
            objects.extend(_string_objects(key, value))
        elif _is_matrix(value):
            objects.append(SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "matrix"}))
            for r, row in enumerate(value):
                for c, cell in enumerate(row):
                    objects.append(
                        SceneObject(
                            id=f"{key}[{r}][{c}]",
                            type=SceneObjectType.CELL,
                            value=cell,
                            parent=key,
                            row=r,
                            col=c,
                        )
                    )
        elif _is_scalar_list(value):
            layout = key if key in {"heap", "stack", "queue", "deque"} else "array"
            objects.append(SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": layout}))
            for i, item in enumerate(value):
                objects.append(
                    SceneObject(
                        id=f"{key}[{i}]",
                        type=SceneObjectType.CELL,
                        value=item,
                        parent=key,
                        index=i,
                    )
                )
        elif isinstance(value, dict) and _looks_like_graph(key, value):
            objects.append(SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "graph"}))
            for node, neighbors in value.items():
                objects.append(SceneObject(id=f"node:{node}", type=SceneObjectType.NODE, label=str(node), parent=key))
                if isinstance(neighbors, list):
                    for nei in neighbors:
                        objects.append(
                            SceneObject(
                                id=f"edge:{node}->{nei}",
                                type=SceneObjectType.EDGE,
                                source=f"node:{node}",
                                target=f"node:{nei}",
                                parent=key,
                            )
                        )
        elif isinstance(value, dict):
            objects.append(SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "map"}))
            for mk, mv in value.items():
                objects.append(
                    SceneObject(
                        id=f"{key}:{mk}",
                        type=SceneObjectType.LABEL,
                        label=str(mk),
                        value=mv,
                        parent=key,
                    )
                )
                objects.append(
                    SceneObject(
                        id=f"{key}[{mk}]",
                        type=SceneObjectType.LABEL,
                        label=str(mk),
                        value=mv,
                        parent=key,
                    )
                )
        elif isinstance(value, (int, float, str, bool)) or value is None:
            objects.append(SceneObject(id=key, type=SceneObjectType.LABEL, label=key, value=value))

    if isinstance(input_data, dict):
        graph = input_data.get("graph") or input_data.get("adjacency")
        if isinstance(graph, dict) and not any(o.meta.get("layout") == "graph" for o in objects):
            objects.extend(_objects_from_state({"graph": graph}, {}))

    return objects


def _objects_from_refs(refs, event: SemanticEvent) -> list[SceneObject]:
    objects: list[SceneObject] = []
    for pos, target in enumerate(refs):
        parsed = parse_target(target.id)
        if parsed.kind == "node":
            objects.append(SceneObject(id=target.id, type=SceneObjectType.NODE, label=parsed.name))
        elif parsed.kind == "edge":
            objects.append(
                SceneObject(id=target.id, type=SceneObjectType.EDGE, source=f"node:{parsed.source}", target=f"node:{parsed.target}")
            )
        elif parsed.kind == "pointer":
            array_name, index = _pointer_location(event, parsed.name, pos)
            pointer_target = f"{array_name}[{index}]" if array_name and index is not None else ""
            objects.append(
                SceneObject(
                    id=target.id,
                    type=SceneObjectType.POINTER,
                    label=parsed.name,
                    parent=array_name,
                    target=pointer_target,
                    index=index,
                    meta={"array": array_name} if array_name else {},
                )
            )
        elif parsed.kind == "frame":
            objects.append(SceneObject(id=target.id, type=SceneObjectType.CONTAINER, label=parsed.name, meta={"layout": "frame"}))
        elif parsed.kind == "point":
            objects.append(SceneObject(id=target.id, type=SceneObjectType.NODE, label=parsed.name, meta={"layout": "point"}))
        elif parsed.kind == "char":
            objects.append(SceneObject(id=target.id, type=SceneObjectType.CELL, label=parsed.name, parent="string"))
        elif parsed.kind == "slice":
            objects.extend(_slice_target_objects(target.id, parsed.name, parsed.indices))
        elif parsed.kind == "map":
            key, _, item = parsed.name.partition(":")
            objects.append(SceneObject(id=target.id, type=SceneObjectType.LABEL, label=item or parsed.name, parent=key))
        elif parsed.kind == "container":
            objects.append(SceneObject(id=target.id, type=SceneObjectType.CONTAINER, label=parsed.name, meta={"layout": parsed.name}))
        elif parsed.kind == "symbol":
            value = (event.state or {}).get(parsed.name)
            objects.append(SceneObject(id=target.id, type=SceneObjectType.LABEL, label=parsed.name, value=value))
    return objects


def _pointer_location(event: SemanticEvent, pointer_name: str, target_pos: int) -> tuple[str, int | None]:
    state = event.state or {}
    array_name = _primary_array_name(state)
    index = None

    if isinstance(event.value, list) and target_pos < len(event.value):
        index = _as_int(event.value[target_pos])
    elif event.value is not None and not isinstance(event.value, (dict, list)):
        index = _as_int(event.value)
    if index is None:
        index = _as_int(state.get(pointer_name))

    return array_name, index


def _primary_array_name(state: dict[str, Any]) -> str:
    for key, value in state.items():
        if key not in {"stack", "queue", "deque", "heap"} and _is_scalar_list(value):
            return key
    return ""


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _dependency_arrows(event: SemanticEvent) -> list[SceneObject]:
    arrows: list[SceneObject] = []
    if not event.deps or not event.targets:
        return arrows
    for target in event.targets:
        for dep in event.deps:
            if dep.id.startswith("pointer:") or target.id.startswith("pointer:"):
                continue
            arrows.append(
                SceneObject(
                    id=f"arrow:{dep.id}->{target.id}:{event.step}",
                    type=SceneObjectType.ARROW,
                    source=dep.id,
                    target=target.id,
                    role="dependency",
                )
            )
    return arrows


def _slice_target_objects(raw_id: str, name: str, indices: tuple[int, ...]) -> list[SceneObject]:
    if len(indices) != 2:
        return []
    start, end = indices
    objects = [SceneObject(id=raw_id, type=SceneObjectType.HIGHLIGHT, label=f"{name}[{start}:{end}]", parent=name)]
    for i in range(start, max(start, end)):
        objects.append(SceneObject(id=f"{raw_id}#{i}", type=SceneObjectType.CELL, label=f"{name}[{i}]", parent=name, index=i))
    return objects


def _dedupe_objects(objects: list[SceneObject]) -> list[SceneObject]:
    result: dict[str, SceneObject] = {}
    for obj in objects:
        current = result.get(obj.id)
        if current is None or _object_score(obj) >= _object_score(current):
            result[obj.id] = obj
    return list(result.values())


def _object_score(obj: SceneObject) -> int:
    score = 0
    if obj.type == SceneObjectType.CONTAINER:
        score += 2
    elif obj.type != SceneObjectType.LABEL:
        score += 1
    for field in ("value", "label", "parent", "row", "col", "index", "source", "target", "role"):
        if getattr(obj, field) not in ("", None):
            score += 1
    score += len(obj.meta or {})
    return score


def _tree_objects(key: str, value: dict[str, Any], layout: str = "tree") -> list[SceneObject]:
    nodes = value.get("nodes") or []
    edges = value.get("edges") or []
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": layout})]
    for node in nodes:
        node_id = str(node.get("id") if isinstance(node, dict) else node)
        label = str(node.get("label", node_id) if isinstance(node, dict) else node_id)
        meta = dict(node.get("meta", {})) if isinstance(node, dict) and isinstance(node.get("meta"), dict) else {}
        objects.append(SceneObject(id=f"node:{node_id}", type=SceneObjectType.NODE, label=label, parent=key, meta=meta))
    for edge in edges:
        if isinstance(edge, dict):
            src, dst = str(edge.get("from")), str(edge.get("to"))
            label = str(edge.get("label", ""))
            meta = dict(edge.get("meta", {})) if isinstance(edge.get("meta"), dict) else {}
        else:
            if not isinstance(edge, (list, tuple)) or len(edge) < 2:
                continue
            src, dst = str(edge[0]), str(edge[1])
            label = ""
            meta = {}
        objects.append(
            SceneObject(
                id=f"edge:{src}->{dst}",
                type=SceneObjectType.EDGE,
                source=f"node:{src}",
                target=f"node:{dst}",
                parent=key,
                label=label,
                meta=meta,
            )
        )
    return objects


def _trie_objects(key: str, value: dict[str, Any]) -> list[SceneObject]:
    objects = _tree_objects(key, value)
    for obj in objects:
        if obj.type == SceneObjectType.CONTAINER:
            obj.meta["layout"] = "trie"
    return objects


def _union_find_objects(key: str, value: dict[str, Any]) -> list[SceneObject]:
    parent = value.get("parent") if isinstance(value, dict) else None
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "union_find"})]
    if not isinstance(parent, dict):
        return objects
    for node in sorted(parent, key=str):
        objects.append(SceneObject(id=f"node:{node}", type=SceneObjectType.NODE, label=str(node), parent=key))
    for node, par in parent.items():
        if node != par:
            objects.append(
                SceneObject(
                    id=f"edge:{node}->{par}",
                    type=SceneObjectType.EDGE,
                    source=f"node:{node}",
                    target=f"node:{par}",
                    parent=key,
                )
            )
    return objects


def _points_objects(key: str, value: list[Any]) -> list[SceneObject]:
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "geometry"})]
    for i, point in enumerate(value):
        if isinstance(point, dict):
            x, y = point.get("x"), point.get("y")
            point_id = str(point.get("id", i))
            label = str(point.get("label", point_id))
        else:
            x, y = point[0], point[1]
            point_id = str(i)
            label = str(i)
        objects.append(
            SceneObject(
                id=f"point:{point_id}",
                type=SceneObjectType.NODE,
                label=label,
                parent=key,
                meta={"x": x, "y": y},
            )
        )
    return objects


def _geometry_objects(key: str, value: dict[str, Any]) -> list[SceneObject]:
    points = value.get("points") or []
    objects = _points_objects(key, points)

    for i, segment in enumerate(value.get("segments") or []):
        src, dst = _segment_endpoints(segment)
        if src is None or dst is None:
            continue
        objects.append(
            SceneObject(
                id=f"segment:{src}->{dst}:{i}",
                type=SceneObjectType.EDGE,
                source=f"point:{src}",
                target=f"point:{dst}",
                parent=key,
                label=_segment_label(segment),
                meta={"shape": "segment"},
            )
        )

    hull = value.get("hull") or value.get("path") or []
    if isinstance(hull, list) and len(hull) >= 2:
        close = bool(value.get("closed", False))
        pairs = list(zip(hull, hull[1:]))
        if close and len(hull) > 2:
            pairs.append((hull[-1], hull[0]))
        for i, (src, dst) in enumerate(pairs):
            objects.append(
                SceneObject(
                    id=f"hull:{src}->{dst}:{i}",
                    type=SceneObjectType.EDGE,
                    source=f"point:{src}",
                    target=f"point:{dst}",
                    parent=key,
                    meta={"shape": "hull"},
                )
            )

    if "sweep_x" in value:
        objects.append(
            SceneObject(
                id=f"sweep:{key}:x",
                type=SceneObjectType.LABEL,
                label="扫描线",
                value=value.get("sweep_x"),
                parent=key,
                meta={"layout": "sweep_line", "axis": "x", "x": value.get("sweep_x")},
            )
        )
    if "sweep_y" in value:
        objects.append(
            SceneObject(
                id=f"sweep:{key}:y",
                type=SceneObjectType.LABEL,
                label="扫描线",
                value=value.get("sweep_y"),
                parent=key,
                meta={"layout": "sweep_line", "axis": "y", "y": value.get("sweep_y")},
            )
        )
    return objects


def _segment_endpoints(segment: Any) -> tuple[str | None, str | None]:
    if isinstance(segment, dict):
        if "from" in segment and "to" in segment:
            return str(segment.get("from")), str(segment.get("to"))
        if "source" in segment and "target" in segment:
            return str(segment.get("source")), str(segment.get("target"))
    if isinstance(segment, (list, tuple)) and len(segment) >= 2:
        return str(segment[0]), str(segment[1])
    return None, None


def _segment_label(segment: Any) -> str:
    if isinstance(segment, dict):
        return str(segment.get("label", ""))
    return ""


def _string_objects(key: str, value: str) -> list[SceneObject]:
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "string"})]
    for i, ch in enumerate(value):
        objects.append(SceneObject(id=f"{key}[{i}]", type=SceneObjectType.CELL, value=ch, parent=key, index=i))
    return objects


def _ml_objects(key: str, value: dict[str, Any]) -> list[SceneObject]:
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "ml"})]
    if "tensor" in value:
        objects.extend(_ml_tensor_objects("tensor", value.get("tensor"), parent=key, label="tensor"))
    for tensor_key in ("features", "weights", "matrix", "activations"):
        if tensor_key in value:
            objects.extend(_ml_tensor_objects(tensor_key, value.get(tensor_key), parent=key, label=tensor_key))
    if "batch" in value:
        objects.append(
            SceneObject(
                id=f"{key}:batch",
                type=SceneObjectType.BATCH,
                label="batch",
                value=value.get("batch"),
                parent=key,
                meta={"layout": "batch"},
            )
        )
    for name, val in (value.get("parameters") or {}).items() if isinstance(value.get("parameters"), dict) else []:
        objects.append(
            SceneObject(
                id=f"parameter:{name}",
                type=SceneObjectType.PARAMETER,
                label=str(name),
                value=val,
                parent=key,
                meta={"layout": "parameter"},
            )
        )
    if "loss" in value or "loss_curve" in value:
        history = value.get("loss_curve") or value.get("loss_history") or [value.get("loss")]
        objects.append(
            SceneObject(
                id=f"{key}:loss_curve",
                type=SceneObjectType.LOSS_CURVE,
                label="loss",
                value=history,
                parent=key,
                meta={"layout": "loss_curve"},
            )
        )
    gradient = value.get("gradient") or value.get("gradients")
    if gradient is not None:
        objects.append(
            SceneObject(
                id=f"{key}:gradient",
                type=SceneObjectType.GRADIENT_VECTOR,
                label="gradient",
                value=gradient,
                parent=key,
                meta={"layout": "gradient_vector"},
            )
        )
    graph = value.get("computational_graph")
    if isinstance(graph, dict):
        objects.extend(_ml_graph_objects(key, graph))
    boundary = value.get("decision_boundary")
    if boundary is not None:
        objects.append(
            SceneObject(
                id=f"{key}:decision_boundary",
                type=SceneObjectType.DECISION_BOUNDARY,
                label="decision boundary",
                value=boundary,
                parent=key,
                meta={"layout": "decision_boundary"},
            )
        )
    if "epoch" in value:
        objects.append(
            SceneObject(
                id=f"{key}:epoch",
                type=SceneObjectType.TRAINING_EPOCH,
                label="epoch",
                value=value.get("epoch"),
                parent=key,
                meta={"layout": "training_epoch"},
            )
        )
    if "prediction" in value:
        objects.append(
            SceneObject(
                id=f"{key}:prediction",
                type=SceneObjectType.PREDICTION,
                label="prediction",
                value=value.get("prediction"),
                parent=key,
                meta={"layout": "prediction"},
            )
        )
    return objects


def _ml_tensor_objects(name: str, value: Any, *, parent: str, label: str) -> list[SceneObject]:
    if value is None:
        return []
    shape = _shape_of(value)
    objects = [
        SceneObject(
            id=f"{parent}:{name}",
            type=SceneObjectType.TENSOR,
            label=label,
            value=value,
            parent=parent,
            meta={"layout": "tensor", "shape": shape},
        )
    ]
    if _is_matrix(value):
        matrix_parent = f"{parent}:{name}"
        objects.append(SceneObject(id=f"{matrix_parent}:matrix", type=SceneObjectType.CONTAINER, label=label, parent=parent, meta={"layout": "matrix"}))
        for r, row in enumerate(value):
            for c, cell in enumerate(row):
                objects.append(SceneObject(id=f"{matrix_parent}[{r}][{c}]", type=SceneObjectType.CELL, value=cell, parent=f"{matrix_parent}:matrix", row=r, col=c))
    return objects


def _ml_graph_objects(parent: str, graph: dict[str, Any]) -> list[SceneObject]:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    container_id = f"{parent}:computational_graph"
    objects = [SceneObject(id=container_id, type=SceneObjectType.CONTAINER, label="computational graph", parent=parent, meta={"layout": "computational_graph"})]
    for node in nodes:
        node_id = str(node.get("id") if isinstance(node, dict) else node)
        label = str(node.get("label", node_id) if isinstance(node, dict) else node_id)
        objects.append(SceneObject(id=f"ml_node:{node_id}", type=SceneObjectType.NODE, label=label, parent=container_id, meta={"layout": "computational_graph"}))
    for edge in edges:
        if isinstance(edge, dict):
            src = str(edge.get("from") or edge.get("source"))
            dst = str(edge.get("to") or edge.get("target"))
        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
            src, dst = str(edge[0]), str(edge[1])
        else:
            continue
        objects.append(SceneObject(id=f"ml_edge:{src}->{dst}", type=SceneObjectType.EDGE, source=f"ml_node:{src}", target=f"ml_node:{dst}", parent=container_id))
    return objects


def _shape_of(value: Any) -> list[int]:
    if isinstance(value, list):
        if value and all(isinstance(row, list) for row in value):
            return [len(value), max((len(row) for row in value), default=0)]
        return [len(value)]
    return []


def _is_scalar_list(value: Any) -> bool:
    return isinstance(value, list) and all(not isinstance(x, (list, dict)) for x in value)


def _is_matrix(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(row, list) for row in value)
        and len({len(row) for row in value}) <= 1
    )


def _looks_like_graph(key: str, value: dict[str, Any]) -> bool:
    if key in {"graph", "adjacency"}:
        return True
    return bool(value) and all(isinstance(v, list) for v in value.values())


def _is_tree_like(key: str, value: Any) -> bool:
    return isinstance(value, dict) and key in {"tree", "binary_tree", "segment_tree"} and "nodes" in value and "edges" in value


def _is_recursion_tree_like(key: str, value: Any) -> bool:
    return isinstance(value, dict) and key in {"recursion_tree", "call_tree", "search_tree"} and "nodes" in value and "edges" in value


def _is_trie_like(key: str, value: Any) -> bool:
    return isinstance(value, dict) and key == "trie" and "nodes" in value and "edges" in value


def _is_union_find_like(key: str, value: Any) -> bool:
    return isinstance(value, dict) and key in {"union_find", "dsu"} and isinstance(value.get("parent"), dict)


def _is_geometry_like(key: str, value: Any) -> bool:
    return isinstance(value, dict) and key in {"geometry", "plane", "sweep"} and isinstance(value.get("points"), list)


def _is_points_like(key: str, value: Any) -> bool:
    if key not in {"points", "geometry"} or not isinstance(value, list):
        return False
    return all(
        (isinstance(p, (list, tuple)) and len(p) >= 2)
        or (isinstance(p, dict) and "x" in p and "y" in p)
        for p in value
    )


def _is_string_view_key(key: str) -> bool:
    return key in {"s", "t", "pattern", "text", "string"}


def _is_ml_state_like(key: str, value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if key in {"ml", "model", "training", "linear_regression", "logistic_regression"}:
        return True
    ml_keys = {
        "tensor",
        "features",
        "weights",
        "batch",
        "parameters",
        "loss",
        "loss_curve",
        "loss_history",
        "gradient",
        "gradients",
        "computational_graph",
        "decision_boundary",
        "epoch",
        "prediction",
    }
    return bool(set(value) & ml_keys)
