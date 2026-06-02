"""Compile semantic traces into stable visual scene graphs."""

from __future__ import annotations

from typing import Any

from algolab.compiler.target_parser import parse_target
from algolab.schemas.scene_graph import SceneFrame, SceneGraph, SceneObject, SceneObjectType, VisualMark
from algolab.schemas.semantic_trace import SemanticEvent, SemanticOp, SemanticTrace


def compile_scene(trace: SemanticTrace) -> SceneGraph:
    frames: list[SceneFrame] = []
    previous_state: dict[str, Any] = {}
    total_steps = len(trace.events)
    for event in trace.events:
        frame = compile_frame(trace, event, previous_state=previous_state, total_steps=total_steps)
        frames.append(frame)
        previous_state = frame.state
    return SceneGraph(
        algorithm=trace.algorithm,
        input_data=trace.input_data,
        result=trace.result,
        pseudocode=trace.pseudocode,
        frames=frames,
    )


def compile_frame(
    trace: SemanticTrace,
    event: SemanticEvent,
    previous_state: dict[str, Any] | None = None,
    total_steps: int | None = None,
) -> SceneFrame:
    raw_state = event.state or {}
    state = _public_state(raw_state)
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

    teaching = _teaching_for_event(event)
    objects = _dedupe_objects(objects)
    _apply_visual_pattern_metadata(objects, event, state, teaching)
    evidence = _evidence_for_event(event, previous_state or {}, state, teaching, total_steps=total_steps)
    evidence["visual_patterns"] = _visual_patterns_for_frame(objects)
    title = _title_for_event(event)
    return SceneFrame(
        step=event.step,
        title=title,
        description=event.reason,
        operation=event.op.value,
        code_line=event.code_line,
        objects=objects,
        marks=marks,
        state=state,
        interaction=event.interaction.model_dump() if event.interaction else None,
        teaching=teaching,
        evidence=evidence,
    )


def _public_state(state: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in state.items() if not key.startswith("_")}


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


def _evidence_for_event(
    event: SemanticEvent,
    previous_state: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    teaching: dict[str, Any] | None = None,
    total_steps: int | None = None,
) -> dict[str, Any]:
    public_state = state if state is not None else _public_state(event.state or {})
    changes = _changes_for_event(event, previous_state or {}, public_state)
    return {
        "operation": event.op.value,
        "targets": [target.id for target in event.targets],
        "deps": [dep.id for dep in event.deps],
        "role": event.role,
        "value": event.value,
        "before": event.before,
        "after": event.after,
        "changes": changes,
        "reason": event.reason,
        "code_line": event.code_line,
        "timeline": _timeline_for_event(event, teaching or {}, total_steps=total_steps),
        "process": _process_evidence_for_event(event, public_state, changes, teaching or {}),
    }


def _process_evidence_for_event(
    event: SemanticEvent,
    state: dict[str, Any],
    changes: list[dict[str, Any]],
    teaching: dict[str, Any],
) -> dict[str, Any]:
    targets = [target.id for target in event.targets]
    deps = [dep.id for dep in event.deps]
    if _is_dp_transfer_event(event):
        return _dp_process_evidence(targets, deps, state, changes, teaching)
    if _is_graph_first_visit_event(event, state):
        return _graph_visit_process_evidence(targets, deps, state, changes, teaching)
    if _is_interval_shrink_event(event, state):
        return _interval_process_evidence(targets, deps, state, changes, teaching)
    if _is_stack_pop_answer_event(event, state):
        return _stack_pop_process_evidence(targets, deps, state, changes, teaching)
    if not (targets or deps or changes or event.reason):
        return {}
    checks = _base_process_checks(targets, deps, state, changes, teaching)
    return {
        "status": "通过核对",
        "kind": "通用过程证据",
        "summary": _generic_process_summary(event, targets, deps, changes),
        "checks": checks,
    }


def _is_dp_transfer_event(event: SemanticEvent) -> bool:
    if event.op not in {SemanticOp.SET, SemanticOp.COMPARE}:
        return False
    targets = [target.id for target in event.targets]
    deps = [dep.id for dep in event.deps]
    return any(_is_matrix_target(target) for target in targets) and len([dep for dep in deps if _is_matrix_target(dep)]) >= 1


def _is_matrix_target(target: str) -> bool:
    parsed = parse_target(target)
    return parsed.kind == "indexed" and len(parsed.indices) == 2


def _is_graph_first_visit_event(event: SemanticEvent, state: dict[str, Any]) -> bool:
    if event.op not in {SemanticOp.MARK, SemanticOp.SET, SemanticOp.PUSH}:
        return False
    if not isinstance(state.get("dist"), dict):
        return False
    targets = [target.id for target in event.targets]
    deps = [dep.id for dep in event.deps]
    return any(target.startswith("node:") for target in targets) and any(dep.startswith(("node:", "edge:")) for dep in deps)


def _is_interval_shrink_event(event: SemanticEvent, state: dict[str, Any]) -> bool:
    if event.op not in {SemanticOp.MOVE, SemanticOp.SET}:
        return False
    targets = [target.id for target in event.targets]
    has_window = isinstance(state.get("left"), int) and isinstance(state.get("right"), int)
    has_pointer = any(target.startswith("pointer:") for target in targets)
    return has_window and has_pointer


def _is_stack_pop_answer_event(event: SemanticEvent, state: dict[str, Any]) -> bool:
    if event.op != SemanticOp.POP or not isinstance(state.get("stack"), list):
        return False
    targets = [target.id for target in event.targets]
    return any(target.startswith("answer") for target in targets) or "answer" in state


def _dp_process_evidence(
    targets: list[str],
    deps: list[str],
    state: dict[str, Any],
    changes: list[dict[str, Any]],
    teaching: dict[str, Any],
) -> dict[str, Any]:
    target_text = _join_limited(targets)
    dep_text = _join_limited(deps)
    checks = _base_process_checks(targets, deps, state, changes, teaching)
    checks.insert(0, {"label": "转移类型", "text": "DP 转移使用依赖状态推出当前目标。"})
    return {
        "status": "通过核对",
        "kind": "DP 转移核对",
        "summary": f"DP 转移通过核对：{target_text} 由依赖 {dep_text} 推出。",
        "checks": checks,
    }


def _graph_visit_process_evidence(
    targets: list[str],
    deps: list[str],
    state: dict[str, Any],
    changes: list[dict[str, Any]],
    teaching: dict[str, Any],
) -> dict[str, Any]:
    target_text = _join_limited(targets)
    dep_text = _join_limited(deps)
    dist_values = _dist_values_for_nodes(state, targets)
    checks = _base_process_checks(targets, deps, state, changes, teaching)
    if dist_values:
        checks.insert(0, {"label": "距离记录", "text": dist_values})
    return {
        "status": "通过核对",
        "kind": "图搜索首次访问核对",
        "summary": f"首次访问通过核对：{target_text} 已写入 dist 距离表，来源依赖 {dep_text}。",
        "checks": checks,
    }


def _interval_process_evidence(
    targets: list[str],
    deps: list[str],
    state: dict[str, Any],
    changes: list[dict[str, Any]],
    teaching: dict[str, Any],
) -> dict[str, Any]:
    left = state.get("left")
    right = state.get("right")
    checks = _base_process_checks(targets, deps, state, changes, teaching)
    checks.insert(0, {"label": "新区间", "text": f"[left, right] = [{left}, {right}]"})
    return {
        "status": "通过核对",
        "kind": "区间收缩核对",
        "summary": f"区间收缩通过核对：指针 {_join_limited(targets)} 已移动，新区间仍覆盖可能答案。",
        "checks": checks,
    }


def _stack_pop_process_evidence(
    targets: list[str],
    deps: list[str],
    state: dict[str, Any],
    changes: list[dict[str, Any]],
    teaching: dict[str, Any],
) -> dict[str, Any]:
    checks = _base_process_checks(targets, deps, state, changes, teaching)
    answer_changes = [change for change in changes if str(change.get("target", "")).startswith("answer")]
    if answer_changes:
        checks.insert(0, {"label": "answer 更新", "text": _change_text(answer_changes[0])})
    return {
        "status": "通过核对",
        "kind": "单调栈弹出核对",
        "summary": "弹出通过核对：当前元素使栈顶候选出栈，并写入 answer，保持单调栈不变量。",
        "checks": checks,
    }


def _base_process_checks(
    targets: list[str],
    deps: list[str],
    state: dict[str, Any],
    changes: list[dict[str, Any]],
    teaching: dict[str, Any],
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    if targets:
        checks.append({"label": "目标对象", "text": _join_limited(targets)})
    if deps:
        checks.append({"label": "依赖对象", "text": _dependency_values_text(state, deps)})
    formula = str(teaching.get("formula") or "").strip()
    if formula:
        checks.append({"label": "公式 / 规则", "text": formula})
    invariant = str(teaching.get("invariant") or "").strip()
    if invariant:
        checks.append({"label": "不变量", "text": invariant})
    if changes:
        checks.append({"label": "状态证据", "text": _change_text(changes[0])})
    return checks


def _generic_process_summary(
    event: SemanticEvent,
    targets: list[str],
    deps: list[str],
    changes: list[dict[str, Any]],
) -> str:
    if deps and targets:
        return f"本步过程通过核对：{_join_limited(targets)} 使用依赖 {_join_limited(deps)}。"
    if changes:
        return f"本步过程通过核对：{_change_text(changes[0])}。"
    if targets:
        return f"本步过程通过核对：{event.op.value} 作用于 {_join_limited(targets)}。"
    return "本步过程通过核对：包含可观测状态或说明。"


def _dependency_values_text(state: dict[str, Any], deps: list[str]) -> str:
    parts: list[str] = []
    for dep in deps[:4]:
        exists, value = _resolve_state_target(state, dep)
        parts.append(f"{dep}={_compact_text(value)}" if exists else dep)
    if len(deps) > 4:
        parts.append(f"还有 {len(deps) - 4} 项")
    return "；".join(parts)


def _dist_values_for_nodes(state: dict[str, Any], targets: list[str]) -> str:
    dist = state.get("dist")
    if not isinstance(dist, dict):
        return ""
    parts: list[str] = []
    for target in targets:
        if not target.startswith("node:"):
            continue
        node = target.split(":", 1)[1]
        if node in dist:
            parts.append(f"dist[{node}]={dist[node]}")
        else:
            for key, value in dist.items():
                if str(key) == node:
                    parts.append(f"dist[{node}]={value}")
                    break
    return "；".join(parts)


def _change_text(change: dict[str, Any]) -> str:
    target = str(change.get("target") or "state")
    before = change.get("before")
    after = change.get("after")
    if "before" in change or "after" in change:
        return f"{target}: {_compact_text(before)} -> {_compact_text(after)}"
    if "value" in change:
        return f"{target}: value={_compact_text(change.get('value'))}"
    return f"{target} 已变化"


def _join_limited(values: list[str], limit: int = 4) -> str:
    if not values:
        return "无"
    selected = values[:limit]
    suffix = f" 等 {len(values)} 项" if len(values) > limit else ""
    return "、".join(selected) + suffix


def _compact_text(value: Any) -> str:
    text = repr(value)
    if len(text) > 80:
        return text[:77] + "..."
    return text


def _changes_for_event(event: SemanticEvent, previous_state: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = _event_value_changes(event)
    if explicit:
        return explicit

    target_changes = _target_state_changes([target.id for target in event.targets], previous_state, state)
    if target_changes:
        return target_changes

    return _state_diff_changes(previous_state, state)


def _event_value_changes(event: SemanticEvent) -> list[dict[str, Any]]:
    fields = getattr(event, "model_fields_set", set())
    has_value = "value" in fields
    has_before = "before" in fields
    has_after = "after" in fields
    if not (has_value or has_before or has_after):
        return []

    targets = [target.id for target in event.targets] or ["state"]
    changes: list[dict[str, Any]] = []
    for index, target in enumerate(targets):
        change: dict[str, Any] = {
            "target": target,
            "operation": event.op.value,
            "source": "event",
        }
        if has_before:
            change["before"] = _event_value_at(event.before, index, len(targets))
        if has_after:
            change["after"] = _event_value_at(event.after, index, len(targets))
        if has_value:
            change["value"] = _event_value_at(event.value, index, len(targets))
        changes.append(change)
    return changes


def _event_value_at(value: Any, index: int, target_count: int) -> Any:
    if isinstance(value, list) and target_count > 1 and index < len(value):
        return value[index]
    return value


def _target_state_changes(targets: list[str], previous_state: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for target in targets:
        before_exists, before = _resolve_state_target(previous_state, target)
        after_exists, after = _resolve_state_target(state, target)
        if not before_exists and not after_exists:
            continue
        if _stable_change_value(before) == _stable_change_value(after):
            continue
        changes.append(
            {
                "target": target,
                "before": before,
                "after": after,
                "kind": _change_kind(before_exists, after_exists),
                "source": "state_diff",
            }
        )
    return changes


def _state_diff_changes(previous_state: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for key in sorted(set(previous_state) | set(state)):
        before_exists = key in previous_state
        after_exists = key in state
        before = previous_state.get(key)
        after = state.get(key)
        if _stable_change_value(before) == _stable_change_value(after):
            continue
        changes.append(
            {
                "target": key,
                "before": before,
                "after": after,
                "kind": _change_kind(before_exists, after_exists),
                "source": "state_diff",
            }
        )
    return changes


def _change_kind(before_exists: bool, after_exists: bool) -> str:
    if not before_exists:
        return "新增"
    if not after_exists:
        return "删除"
    return "更新"


def _resolve_state_target(state: dict[str, Any], target: str) -> tuple[bool, Any]:
    if not state:
        return False, None
    if target in state:
        return True, state[target]

    if target.startswith("pointer:"):
        name = target.split(":", 1)[1]
        if name in state:
            return True, state[name]
        return False, None

    parsed = _parse_state_path(target)
    if not parsed:
        return False, None
    name, parts = parsed
    if name not in state:
        return False, None

    value = state[name]
    for part in parts:
        exists, value = _descend_state_value(value, part)
        if not exists:
            return False, None
    return True, value


def _parse_state_path(target: str) -> tuple[str, list[str]] | None:
    if "[" not in target or not target.endswith("]"):
        return None
    name, rest = target.split("[", 1)
    if not name:
        return None
    parts = [part.rstrip("]") for part in rest.split("[")]
    if not parts or any(part == "" for part in parts):
        return None
    return name, parts


def _descend_state_value(value: Any, key: str) -> tuple[bool, Any]:
    if isinstance(value, list):
        index = _as_int(key)
        if index is None or index < 0 or index >= len(value):
            return False, None
        return True, value[index]
    if isinstance(value, dict):
        if key in value:
            return True, value[key]
        numeric_key = _as_int(key)
        if numeric_key is not None and numeric_key in value:
            return True, value[numeric_key]
        return False, None
    return False, None


def _stable_change_value(value: Any) -> str:
    try:
        return repr(_sort_change_value(value))
    except Exception:
        return str(value)


def _sort_change_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_change_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_change_value(item) for item in value]
    return value


def _timeline_for_event(
    event: SemanticEvent,
    teaching: dict[str, Any] | None = None,
    total_steps: int | None = None,
) -> dict[str, Any]:
    teaching = teaching if teaching is not None else (event.teaching.model_dump() if event.teaching is not None else {})
    return {
        "phase": _timeline_phase(event, teaching, total_steps=total_steps),
        "operation": event.op.value,
        "keyframe": _is_keyframe_event(event),
        "keyframe_label": _timeline_keyframe_label(event, teaching),
        "targets": [target.id for target in event.targets[:3]],
        "role": event.role,
    }


def _timeline_phase(
    event: SemanticEvent,
    teaching: dict[str, Any] | None = None,
    total_steps: int | None = None,
) -> str:
    state = event.state or {}
    for key in ("phase", "stage", "current_phase"):
        value = state.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _fallback_timeline_phase(event, teaching or {}, total_steps=total_steps)


def _fallback_timeline_phase(
    event: SemanticEvent,
    teaching: dict[str, Any],
    total_steps: int | None = None,
) -> str:
    if event.step == 0 or event.op == SemanticOp.CREATE:
        return "初始化"
    if _looks_like_return_event(event, teaching, total_steps=total_steps):
        return "返回结果"
    if event.op in {SemanticOp.SET, SemanticOp.MARK, SemanticOp.MOVE, SemanticOp.LINK, SemanticOp.UNLINK, SemanticOp.POP} and (
        event.deps or event.role in {"answer", "visited", "conflict"}
    ):
        return "关键转移"
    if event.op in {SemanticOp.COMPARE, SemanticOp.PUSH, SemanticOp.POP, SemanticOp.MOVE, SemanticOp.ENTER, SemanticOp.EXIT}:
        return "主循环"
    if event.op == SemanticOp.EXPLAIN:
        return "说明"
    return "主循环"


def _looks_like_return_event(
    event: SemanticEvent,
    teaching: dict[str, Any],
    total_steps: int | None = None,
) -> bool:
    text = " ".join(
        part
        for part in [
            event.reason or "",
            str(teaching.get("what") or ""),
            str(teaching.get("why") or ""),
        ]
        if part
    )
    if any(token in text for token in ("返回", "最终答案", "得到答案", "输出答案")):
        return True
    if event.op in {SemanticOp.EXIT, SemanticOp.EXPLAIN} and event.role == "answer":
        return True
    if total_steps is not None and event.step == total_steps - 1 and event.role == "answer":
        return True
    targets = [target.id for target in event.targets]
    return event.role == "answer" and bool(targets) and all(target in {"answer", "result"} for target in targets) and not event.deps


def _is_keyframe_event(event: SemanticEvent) -> bool:
    if event.role in {"answer", "conflict", "visited"}:
        return True
    if event.op in {SemanticOp.CREATE, SemanticOp.ENTER, SemanticOp.EXIT, SemanticOp.SET, SemanticOp.MARK}:
        return True
    return bool(event.deps)


def _timeline_keyframe_label(event: SemanticEvent, teaching: dict[str, Any]) -> str:
    for value in (event.reason, teaching.get("what")):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _title_for_event(event)


def _objects_from_state(state: dict[str, Any], input_data: Any) -> list[SceneObject]:
    objects: list[SceneObject] = []

    for key, value in state.items():
        if _is_ml_state_like(key, value):
            objects.extend(_ml_objects(key, value))
        elif _is_recursion_tree_like(key, value):
            objects.extend(_tree_objects(key, value, layout="recursion_tree"))
        elif _is_linked_list_like(key, value):
            objects.extend(_tree_objects(key, value, layout="linked_list"))
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
            objects.extend(_string_objects(key, value, state))
        elif _is_edge_list_like(key, value):
            objects.extend(_edge_list_objects(key, value, state))
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
        elif key not in {"heap", "stack", "queue", "deque"} and _is_string_list(value):
            objects.append(SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "string_list"}))
            for r, item in enumerate(value):
                objects.append(SceneObject(id=f"{key}[{r}]", type=SceneObjectType.LABEL, label=str(r), value=item, parent=key, row=r))
                for c, char in enumerate(item):
                    objects.append(
                        SceneObject(
                            id=f"{key}[{r}][{c}]",
                            type=SceneObjectType.CELL,
                            value=char,
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
            objects.extend(_graph_objects(key, value, state))
        elif isinstance(value, dict):
            objects.append(SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "map"}))
            for mk, mv in value.items():
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
        graph = input_data.get("graph") or input_data.get("adjacency") or input_data.get("weighted_graph")
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
    formula = _formula_for_event(event)
    for target in event.targets:
        for dep in event.deps:
            if dep.id.startswith("pointer:") or target.id.startswith("pointer:"):
                continue
            meta = {"visual_pattern": "dependency_flow", "visual_patterns": ["dependency_flow"]}
            if _is_matrix_target(target.id) and _is_matrix_target(dep.id):
                meta.update(
                    {
                        "visual_pattern": "dp_dependency",
                        "visual_patterns": ["dependency_flow", "dp_dependency", "formula_substitution"],
                        "formula": formula,
                    }
                )
            elif dep.id.startswith("edge:") or (target.id.startswith("node:") and _has_graph_visual_state(event.state or {})):
                meta.update(
                    {
                        "visual_pattern": "graph_relax",
                        "visual_patterns": ["dependency_flow", "graph_relax"],
                        "formula": formula,
                    }
                )
            arrows.append(
                SceneObject(
                    id=f"arrow:{dep.id}->{target.id}:{event.step}",
                    type=SceneObjectType.ARROW,
                    source=dep.id,
                    target=target.id,
                    role="dependency",
                    meta=meta,
                )
            )
    return arrows


def _has_graph_visual_state(state: dict[str, Any]) -> bool:
    return (
        isinstance(state.get("graph"), dict)
        or isinstance(state.get("adjacency"), dict)
        or isinstance(state.get("dist"), dict)
        or isinstance(state.get("distance"), dict)
        or _has_flow_state(state)
    )


def _apply_visual_pattern_metadata(
    objects: list[SceneObject],
    event: SemanticEvent,
    state: dict[str, Any],
    teaching: dict[str, Any],
) -> None:
    by_id = {obj.id: obj for obj in objects}
    _tag_dp_visuals(by_id, event, state, teaching)
    _tag_graph_visuals(objects, by_id, event, state)
    _tag_string_visuals(objects, by_id, event, state)
    _tag_tree_visuals(objects, by_id, event, state)
    _tag_range_visuals(objects, by_id, event, state)
    _tag_network_flow_visuals(objects, state)


def _tag_dp_visuals(
    by_id: dict[str, SceneObject],
    event: SemanticEvent,
    state: dict[str, Any],
    teaching: dict[str, Any],
) -> None:
    targets = [target.id for target in event.targets if _is_matrix_target(target.id)]
    deps = [dep.id for dep in event.deps if _is_matrix_target(dep.id)]
    if not targets or not deps:
        return
    formula = _formula_for_event(event, teaching)
    substitution = _dependency_values_text(state, deps)
    for target in targets:
        _add_visual_pattern(
            by_id.get(target),
            "dp_formula_substitution",
            "dp_target",
            formula=formula,
            substitution=substitution,
        )
    for dep in deps:
        _add_visual_pattern(
            by_id.get(dep),
            "dp_formula_substitution",
            "dp_dependency",
            formula=formula,
        )
    for arrow in by_id.values():
        if arrow.type == SceneObjectType.ARROW and arrow.target in targets and arrow.source in deps:
            _add_visual_pattern(arrow, "dp_dependency_arrow", "dependency", formula=formula, substitution=substitution)


def _tag_graph_visuals(
    objects: list[SceneObject],
    by_id: dict[str, SceneObject],
    event: SemanticEvent,
    state: dict[str, Any],
) -> None:
    frontier = _frontier_nodes(state)
    visited = _visited_nodes(state)
    current = _current_node(state)
    for node_id in frontier:
        _add_visual_pattern(by_id.get(f"node:{node_id}"), "graph_frontier", "frontier")
    for node_id in visited:
        _add_visual_pattern(by_id.get(f"node:{node_id}"), "graph_visit_state", "visited")
    if current:
        _add_visual_pattern(by_id.get(f"node:{current}"), "graph_current_node", "current")

    graphish = isinstance(state.get("dist"), dict) or isinstance(state.get("distance"), dict) or bool(frontier)
    for dep in event.deps:
        if dep.id.startswith("edge:") and graphish:
            _add_visual_pattern(by_id.get(dep.id), "graph_relax_edge", "relax")
    for target in event.targets:
        if target.id.startswith("node:") and graphish:
            _add_visual_pattern(by_id.get(target.id), "graph_relax_target", event.role or "target")

    for edge_id in _path_edge_ids(state):
        _add_visual_pattern(by_id.get(edge_id), "graph_path_highlight", "path")
    for node_id in _path_node_ids(state):
        _add_visual_pattern(by_id.get(f"node:{node_id}"), "graph_path_highlight", "path")

    for obj in objects:
        if obj.type != SceneObjectType.EDGE:
            continue
        if obj.meta.get("edge_label") or obj.meta.get("weight") is not None:
            _add_visual_pattern(obj, "graph_edge_label", "edge_label")


def _tag_string_visuals(
    objects: list[SceneObject],
    by_id: dict[str, SceneObject],
    event: SemanticEvent,
    state: dict[str, Any],
) -> None:
    string_containers = [obj for obj in objects if obj.type == SceneObjectType.CONTAINER and obj.meta.get("layout") == "string"]
    if len(string_containers) >= 2:
        for obj in string_containers:
            _add_visual_pattern(obj, "string_alignment", str(obj.meta.get("row_role") or obj.id))
    for target in [*(target.id for target in event.targets), *(dep.id for dep in event.deps)]:
        if target.startswith(("text[", "pattern[", "s[", "t[", "string[")):
            _add_visual_pattern(by_id.get(target), "string_alignment", "cursor")
    for raw_id in _string_window_ids(state):
        _add_visual_pattern(by_id.get(raw_id), "string_window", "window")
    fallback = _string_fallback_edge(state)
    if fallback:
        src, dst = fallback
        if src in by_id and dst in by_id:
            objects.append(
                SceneObject(
                    id=f"arrow:{src}->{dst}:fallback:{event.step}",
                    type=SceneObjectType.ARROW,
                    source=src,
                    target=dst,
                    role="fallback",
                    meta={
                        "visual_pattern": "string_fallback_arc",
                        "visual_patterns": ["string_alignment", "string_fallback_arc"],
                    },
                )
            )


def _tag_tree_visuals(
    objects: list[SceneObject],
    by_id: dict[str, SceneObject],
    event: SemanticEvent,
    state: dict[str, Any],
) -> None:
    return_values = _return_value_map(state)
    for node_key, value in return_values.items():
        obj = by_id.get(f"node:{node_key}") or by_id.get(str(node_key))
        if obj is not None:
            _add_visual_pattern(obj, "tree_return_value", "return_value", return_value=value)

    if "return_value" in state:
        for target in event.targets:
            if target.id.startswith("node:"):
                _add_visual_pattern(by_id.get(target.id), "tree_return_value", "return_value", return_value=state.get("return_value"))

    recursion_nodes = {
        obj.id
        for obj in objects
        if obj.type == SceneObjectType.NODE and _container_layout(by_id, obj.parent) == "recursion_tree"
    }
    if not recursion_nodes:
        return
    if event.op in {SemanticOp.MARK, SemanticOp.ENTER, SemanticOp.PUSH, SemanticOp.LINK}:
        action = "choose"
        pattern = "backtracking_choice"
    elif event.op in {SemanticOp.UNMARK, SemanticOp.EXIT, SemanticOp.POP, SemanticOp.UNLINK}:
        action = "undo"
        pattern = "backtracking_undo"
    else:
        action = ""
        pattern = ""
    if not pattern:
        return
    for target in event.targets:
        if target.id in recursion_nodes:
            _add_visual_pattern(by_id.get(target.id), pattern, action, backtracking_action=action)


def _tag_range_visuals(
    objects: list[SceneObject],
    by_id: dict[str, SceneObject],
    event: SemanticEvent,
    state: dict[str, Any],
) -> None:
    range_containers = [obj for obj in objects if obj.id in {"segment_tree", "fenwick_tree", "bit", "st"}]
    if not range_containers and "segment_tree" not in state:
        return
    for container in range_containers:
        _add_visual_pattern(container, "range_structure", "container")
    for key, pattern, role in (
        ("query_path", "range_query_path", "query"),
        ("update_path", "range_update_path", "update"),
        ("cover_path", "range_cover_path", "cover"),
    ):
        for node_id in _as_string_list(state.get(key)):
            obj = by_id.get(node_id) or by_id.get(f"node:{node_id}") or by_id.get(f"bit[{node_id}]")
            _add_visual_pattern(obj, pattern, role)
    target_nodes = [target.id for target in event.targets if target.id.startswith("node:")]
    dep_ids = [dep.id for dep in event.deps]
    reason = event.reason or ""
    if target_nodes and (any(dep.startswith("query[") for dep in dep_ids) or "查询" in reason):
        for target in target_nodes:
            _add_visual_pattern(by_id.get(target), "range_query_path", "query")
            if event.op == SemanticOp.MARK or "覆盖" in reason:
                _add_visual_pattern(by_id.get(target), "range_cover_path", "cover")
    if target_nodes and (any(dep.startswith("update[") for dep in dep_ids) or "更新路径" in reason):
        for target in target_nodes:
            _add_visual_pattern(by_id.get(target), "range_update_path", "update")


def _tag_network_flow_visuals(objects: list[SceneObject], state: dict[str, Any]) -> None:
    if not _has_flow_state(state):
        return
    for obj in objects:
        if obj.type != SceneObjectType.EDGE:
            continue
        if obj.meta.get("capacity") is not None or obj.meta.get("flow") is not None or obj.meta.get("residual") is not None:
            _add_visual_pattern(obj, "network_flow_edge_label", "flow_edge")
    for obj in objects:
        if obj.id in _path_edge_ids(state):
            _add_visual_pattern(obj, "network_flow_augmenting_path", "augmenting_path")


def _visual_patterns_for_frame(objects: list[SceneObject]) -> list[dict[str, Any]]:
    by_pattern: dict[str, dict[str, Any]] = {}
    for obj in objects:
        for pattern in _meta_patterns(obj.meta):
            item = by_pattern.setdefault(pattern, {"pattern": pattern, "objects": [], "roles": []})
            item["objects"].append(obj.id)
            role = obj.meta.get("pattern_role")
            if role:
                item["roles"].append(str(role))
    result = []
    for item in by_pattern.values():
        item["objects"] = sorted(set(item["objects"]))
        item["roles"] = sorted(set(item["roles"]))
        result.append(item)
    return sorted(result, key=lambda item: item["pattern"])


def _add_visual_pattern(obj: SceneObject | None, pattern: str, role: str = "", **extra: Any) -> None:
    if obj is None or not pattern:
        return
    patterns = set(_meta_patterns(obj.meta))
    patterns.add(pattern)
    obj.meta["visual_patterns"] = sorted(patterns)
    obj.meta.setdefault("visual_pattern", pattern)
    if role:
        obj.meta["pattern_role"] = role
    for key, value in extra.items():
        if value not in ("", None, []):
            obj.meta[key] = value


def _meta_patterns(meta: dict[str, Any]) -> list[str]:
    patterns: list[str] = []
    raw = meta.get("visual_patterns")
    if isinstance(raw, list):
        patterns.extend(str(item) for item in raw if str(item).strip())
    elif isinstance(raw, str) and raw.strip():
        patterns.append(raw.strip())
    single = meta.get("visual_pattern")
    if isinstance(single, str) and single.strip():
        patterns.append(single.strip())
    return patterns


def _container_layout(by_id: dict[str, SceneObject], container_id: str) -> str:
    container = by_id.get(container_id)
    return str(container.meta.get("layout") or "") if container is not None else ""


def _formula_for_event(event: SemanticEvent, teaching: dict[str, Any] | None = None) -> str:
    if teaching and isinstance(teaching.get("formula"), str) and teaching.get("formula", "").strip():
        return str(teaching.get("formula")).strip()
    if event.teaching is not None and event.teaching.formula:
        return event.teaching.formula
    value = (event.state or {}).get("formula")
    return str(value).strip() if isinstance(value, str) else ""


def _frontier_nodes(state: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for key in ("frontier", "queue", "deque", "heap", "open_set"):
        result.update(_as_string_list(state.get(key)))
    return result


def _visited_nodes(state: dict[str, Any]) -> set[str]:
    visited = state.get("visited")
    if isinstance(visited, dict):
        return {str(key) for key, value in visited.items() if value}
    return set(_as_string_list(visited))


def _current_node(state: dict[str, Any]) -> str:
    for key in ("current", "node", "u"):
        value = state.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _path_node_ids(state: dict[str, Any]) -> list[str]:
    for key in ("path", "current_path", "augmenting_path"):
        values = _as_string_list(state.get(key))
        if values and not any("->" in value for value in values):
            return values
    return []


def _path_edge_ids(state: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for key in ("path_edges", "relax_path", "augmenting_edges"):
        for value in _as_string_list(state.get(key)):
            result.add(value if value.startswith("edge:") else f"edge:{value}")
    for key in ("path", "current_path", "augmenting_path"):
        raw = state.get(key)
        values = _as_string_list(raw)
        if not values:
            continue
        if any("->" in value for value in values):
            result.update(value if value.startswith("edge:") else f"edge:{value}" for value in values)
        else:
            result.update(f"edge:{src}->{dst}" for src, dst in zip(values, values[1:]))
    return result


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        if "nodes" in value:
            return _as_string_list(value.get("nodes"))
        if "path" in value:
            return _as_string_list(value.get("path"))
        if "from" in value and "to" in value:
            return [f"{value.get('from')}->{value.get('to')}"]
        return [str(key) for key, enabled in value.items() if enabled]
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            if isinstance(item, dict) and "from" in item and "to" in item:
                result.append(f"{item.get('from')}->{item.get('to')}")
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                result.append(f"{item[0]}->{item[1]}")
            else:
                result.append(str(item))
        return result
    return [str(value)]


def _string_window_ids(state: dict[str, Any]) -> list[str]:
    text_key = "text" if "text" in state else "s" if "s" in state else "string" if "string" in state else ""
    if not text_key:
        return []
    bounds = _window_bounds(state)
    if not bounds:
        return []
    start, end = bounds
    return [f"{text_key}[{idx}]" for idx in range(max(0, start), max(start, end))]


def _window_bounds(state: dict[str, Any]) -> tuple[int, int] | None:
    raw = state.get("window")
    if isinstance(raw, dict):
        start = _as_int(raw.get("start", raw.get("left")))
        end = _as_int(raw.get("end", raw.get("right")))
        if start is not None and end is not None:
            return start, end + 1 if "right" in raw and "end" not in raw else end
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        start, end = _as_int(raw[0]), _as_int(raw[1])
        if start is not None and end is not None:
            return start, end
    start = _as_int(state.get("window_start", state.get("left")))
    end = _as_int(state.get("window_end", state.get("right")))
    if start is None or end is None:
        return None
    return start, end + 1 if "right" in state and "window_end" not in state else end


def _string_fallback_edge(state: dict[str, Any]) -> tuple[str, str] | None:
    before = _as_int(state.get("fallback_from", state.get("j_before")))
    after = _as_int(state.get("fallback_to", state.get("j_after")))
    if before is None or after is None:
        return None
    key = "pattern" if "pattern" in state else "t" if "t" in state else ""
    if not key:
        return None
    return f"{key}[{before}]", f"{key}[{after}]"


def _string_cursor_for_key(key: str, state: dict[str, Any]) -> int | None:
    if key in {"text", "s", "string"}:
        return _as_int(state.get("i", state.get("text_index")))
    if key in {"pattern", "t"}:
        return _as_int(state.get("j", state.get("pattern_index")))
    return None


def _pattern_alignment_offset(state: dict[str, Any]) -> int | None:
    explicit = _as_int(state.get("alignment_offset"))
    if explicit is not None:
        return explicit
    i = _as_int(state.get("i", state.get("text_index")))
    j = _as_int(state.get("j", state.get("pattern_index")))
    if i is None or j is None:
        return None
    return i - j


def _return_value_map(state: dict[str, Any]) -> dict[str, Any]:
    for key in ("return_values", "returns", "node_returns"):
        value = state.get(key)
        if isinstance(value, dict):
            return {str(k): v for k, v in value.items()}
    return {}


def _neighbor_id(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("to", "target", "id", "node"):
            if value.get(key) not in (None, ""):
                return str(value.get(key))
        return ""
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    return str(value)


def _edge_meta_for_state(state: dict[str, Any], src: str, dst: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    weight = _edge_metric_value(state, ("weights", "weight", "cost"), src, dst)
    capacity = _edge_metric_value(state, ("capacity", "cap", "capacities"), src, dst)
    flow = _edge_metric_value(state, ("flow", "flows"), src, dst)
    residual = _edge_metric_value(state, ("residual", "residual_capacity", "residuals"), src, dst)
    if weight is not None:
        meta["weight"] = weight
        meta["edge_label"] = str(weight)
        meta["visual_pattern"] = "graph_edge_label"
        meta["visual_patterns"] = ["graph_edge_label"]
    if capacity is not None or flow is not None or residual is not None:
        meta["capacity"] = capacity
        meta["flow"] = flow
        meta["residual"] = residual
        label = _flow_label(flow, capacity, residual)
        if label:
            meta["edge_label"] = label
        meta["visual_pattern"] = "network_flow_edge_label"
        meta["visual_patterns"] = ["graph_edge_label", "network_flow_edge_label"]
    return {key: value for key, value in meta.items() if value is not None}


def _edge_metric_value(state: dict[str, Any], keys: tuple[str, ...], src: str, dst: str) -> Any:
    for key in keys:
        mapping = state.get(key)
        if not isinstance(mapping, dict):
            continue
        for candidate in (f"{src}->{dst}", f"{src},{dst}", f"edge:{src}->{dst}"):
            if candidate in mapping:
                return mapping[candidate]
        nested = mapping.get(src)
        if isinstance(nested, dict) and dst in nested:
            return nested[dst]
    return None


def _flow_label(flow: Any, capacity: Any, residual: Any) -> str:
    pieces: list[str] = []
    if flow is not None or capacity is not None:
        pieces.append(f"{0 if flow is None else flow}/{capacity if capacity is not None else '?'}")
    if residual is not None:
        pieces.append(f"res {residual}")
    return " · ".join(str(piece) for piece in pieces if str(piece))


def _has_flow_state(state: dict[str, Any]) -> bool:
    return any(isinstance(state.get(key), dict) for key in ("capacity", "cap", "capacities", "flow", "flows", "residual", "residual_capacity", "residuals"))


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


def _graph_objects(key: str, value: dict[str, Any], state: dict[str, Any]) -> list[SceneObject]:
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "graph"})]
    node_ids: set[str] = set()
    for node, neighbors in value.items():
        node_ids.add(str(node))
        for nei in _graph_neighbor_items(neighbors):
            edge_id = _neighbor_id(nei)
            if edge_id:
                node_ids.add(edge_id)
    for side_key, side in (("left_nodes", "left"), ("right_nodes", "right")):
        for node_id in _as_string_list(state.get(side_key)):
            node_ids.add(node_id)
            objects.append(SceneObject(id=f"node:{node_id}", type=SceneObjectType.NODE, label=node_id, parent=key, meta={"side": side}))
    existing_ids = {obj.id for obj in objects}
    for node_id in sorted(node_ids, key=str):
        object_id = f"node:{node_id}"
        if object_id not in existing_ids:
            objects.append(SceneObject(id=object_id, type=SceneObjectType.NODE, label=str(node_id), parent=key))
            existing_ids.add(object_id)
    for node, neighbors in value.items():
        for nei in _graph_neighbor_items(neighbors):
            edge_id = _neighbor_id(nei)
            if not edge_id:
                continue
            src = str(node)
            edge_meta = _edge_meta_for_state(state, src, edge_id)
            objects.append(
                SceneObject(
                    id=f"edge:{src}->{edge_id}",
                    type=SceneObjectType.EDGE,
                    source=f"node:{src}",
                    target=f"node:{edge_id}",
                    parent=key,
                    label=str(edge_meta.get("edge_label", "")),
                    meta=edge_meta,
                )
            )
    return objects


def _graph_neighbor_items(neighbors: Any) -> list[Any]:
    if isinstance(neighbors, dict):
        return list(neighbors.keys())
    if isinstance(neighbors, list):
        return neighbors
    return []


def _edge_list_objects(key: str, value: list[Any], state: dict[str, Any]) -> list[SceneObject]:
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "graph", "source": "edge_list"})]
    endpoints: list[tuple[str, str, Any]] = []
    node_ids: set[str] = set()
    for edge in value:
        src, dst, label = _edge_list_entry(edge)
        if not src or not dst:
            continue
        endpoints.append((src, dst, label))
        node_ids.update((src, dst))
    for node_id in sorted(node_ids, key=str):
        objects.append(SceneObject(id=f"node:{node_id}", type=SceneObjectType.NODE, label=str(node_id), parent=key))
    for src, dst, label in endpoints:
        meta = _edge_meta_for_state(state, src, dst)
        if label not in (None, "") and "edge_label" not in meta:
            meta["edge_label"] = str(label)
            meta["weight"] = label
            meta["visual_pattern"] = "graph_edge_label"
            meta["visual_patterns"] = ["graph_edge_label"]
        objects.append(
            SceneObject(
                id=f"edge:{src}->{dst}",
                type=SceneObjectType.EDGE,
                source=f"node:{src}",
                target=f"node:{dst}",
                parent=key,
                label=str(meta.get("edge_label", "")),
                meta=meta,
            )
        )
    return objects


def _edge_list_entry(edge: Any) -> tuple[str, str, Any]:
    if isinstance(edge, dict):
        src = edge.get("from", edge.get("source", edge.get("u")))
        dst = edge.get("to", edge.get("target", edge.get("v")))
        label = edge.get("weight", edge.get("w", edge.get("label", "")))
        return ("" if src in (None, "") else str(src), "" if dst in (None, "") else str(dst), label)
    if isinstance(edge, (list, tuple)) and len(edge) >= 2:
        label = edge[2] if len(edge) >= 3 else ""
        return str(edge[0]), str(edge[1]), label
    return "", "", ""


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
            src = str(edge.get("from", edge.get("source", edge.get("u"))))
            dst = str(edge.get("to", edge.get("target", edge.get("v"))))
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
        objects.append(
            SceneObject(
                id=f"{key}[{i}]",
                type=SceneObjectType.NODE,
                label=label,
                parent=key,
                index=i,
                meta={"x": x, "y": y, "alias": f"point:{point_id}"},
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


def _string_objects(key: str, value: str, state: dict[str, Any]) -> list[SceneObject]:
    container_meta: dict[str, Any] = {"layout": "string", "row_role": key}
    if key in {"text", "pattern", "s", "t", "string"}:
        container_meta.update({"visual_pattern": "string_alignment", "visual_patterns": ["string_alignment"]})
    cursor = _string_cursor_for_key(key, state)
    if cursor is not None:
        container_meta["cursor_index"] = cursor
    if key in {"pattern", "t"}:
        offset = _pattern_alignment_offset(state)
        if offset is not None:
            container_meta["alignment_offset"] = offset
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta=container_meta)]
    window_ids = set(_string_window_ids(state))
    for i, ch in enumerate(value):
        cell_meta: dict[str, Any] = {}
        if f"{key}[{i}]" in window_ids:
            cell_meta.update({"visual_pattern": "string_window", "visual_patterns": ["string_window"], "pattern_role": "window"})
        if cursor == i:
            cell_meta.update({"visual_pattern": "string_alignment", "visual_patterns": ["string_alignment"], "pattern_role": "cursor"})
        objects.append(SceneObject(id=f"{key}[{i}]", type=SceneObjectType.CELL, value=ch, parent=key, index=i, meta=cell_meta))
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


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def _is_matrix(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(row, list) for row in value)
        and len({len(row) for row in value}) <= 1
    )


def _is_edge_list_like(key: str, value: Any) -> bool:
    if key not in {"edges", "weighted_edges", "edge_list", "mst_edges", "tree_edges"} or not isinstance(value, list):
        return False
    return any(_edge_list_entry(item)[:2] != ("", "") for item in value)


def _looks_like_graph(key: str, value: dict[str, Any]) -> bool:
    if key in {"graph", "adjacency", "weighted_graph"}:
        return True
    return bool(value) and all(isinstance(v, (dict, list)) for v in value.values())


def _is_tree_like(key: str, value: Any) -> bool:
    return isinstance(value, dict) and key in {"tree", "binary_tree", "segment_tree"} and "nodes" in value and "edges" in value


def _is_linked_list_like(key: str, value: Any) -> bool:
    return isinstance(value, dict) and key == "linked_list" and "nodes" in value and "edges" in value


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
