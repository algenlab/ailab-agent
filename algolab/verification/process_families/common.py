"""Shared process validator helpers."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from typing import Any

from algolab.compiler.target_parser import parse_target
from algolab.schemas.semantic_trace import SemanticOp, SemanticTrace

FULL_DP_TRACE_CELL_LIMIT = 80
SMALL_BFS_NODE_LIMIT = 20
SMALL_BFS_EDGE_LIMIT = 80
SMALL_BINARY_SEARCH_INPUT_LIMIT = 64
SMALL_MONOTONIC_STACK_INPUT_LIMIT = 64
DP_CONTRACT_LOOP_KEYS = ("i", "j", "k", "capacity_index", "capacity", "mask", "digit", "current")
ARRAY_POINTER_SUBMODES = {
    "binary_answer",
    "two_pointer",
    "sliding_window",
    "prefix_sum",
    "difference_array",
    "fast_slow",
}
GRAPH_CONTRACT_SUBMODES = {
    "bfs",
    "dfs",
    "connected_components",
    "bipartite_coloring",
    "dijkstra",
    "bellman_ford",
    "floyd_warshall",
    "zero_one_bfs",
    "topological_sort",
    "mst",
    "tarjan",
    "network_flow",
}
FAMILY_CONTRACT_FAMILIES = {
    "string",
    "tree",
    "backtracking",
    "heap",
    "trie",
    "linked_list",
}

def _validate_core_invariants(trace: SemanticTrace) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(_validate_trace_meta_coverage(trace))
    errors.extend(_validate_observable_process_evidence(trace))
    replay_errors, replay_warnings = _validate_set_replay(trace)
    errors.extend(replay_errors)
    warnings.extend(replay_warnings)
    warnings.extend(_validate_dependency_presence(trace))
    warnings.extend(_validate_reason_grounding(trace))
    return errors, warnings


def _validate_trace_meta_coverage(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        meta = (event.state or {}).get("_trace_meta")
        if not isinstance(meta, dict):
            continue
        sampled = meta.get("sampled") is True
        if sampled:
            continue
        coverage = _recompute_trace_meta_coverage(trace, meta)
        for name, value in coverage.items():
            if value < 1.0:
                errors.append(f"第 {event.step} 步 trace coverage {name} 不足：{value}")
    return errors


def _recompute_trace_meta_coverage(trace: SemanticTrace, meta: dict[str, Any]) -> dict[str, float]:
    expected_updates = meta.get("expected_updates")
    if not isinstance(expected_updates, dict):
        return {}
    recorded_updates = _count_recorded_updates(trace)
    coverage: dict[str, float] = {}
    for raw_name, raw_expected in expected_updates.items():
        if not isinstance(raw_expected, int):
            continue
        name = str(raw_name)
        recorded = recorded_updates.get(name, 0)
        coverage[name] = 1.0 if raw_expected == 0 else round(recorded / raw_expected, 6)
    return coverage


def _count_recorded_updates(trace: SemanticTrace) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in trace.events:
        if event.op not in {SemanticOp.SET, SemanticOp.MARK, SemanticOp.MOVE, SemanticOp.PUSH, SemanticOp.POP}:
            continue
        for target in event.targets:
            name = _coverage_name_for_target(target.id)
            counts[name] = counts.get(name, 0) + 1
    return counts


def _coverage_name_for_target(target_id: str) -> str:
    if target_id.startswith("pointer:"):
        return target_id
    return target_id.split("[", 1)[0]


def _validate_observable_process_evidence(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    previous_state: dict[str, Any] | None = None
    for event in trace.events:
        state = event.state or {}
        if event.op in {SemanticOp.SET, SemanticOp.MOVE, SemanticOp.PUSH, SemanticOp.POP, SemanticOp.MARK, SemanticOp.LINK, SemanticOp.UNLINK}:
            if not event.targets:
                errors.append(f"第 {event.step} 步 {event.op.value} 缺少 targets，无法核对过程动作")
            if not _event_has_observable_evidence(event, previous_state, state):
                errors.append(f"第 {event.step} 步 {event.op.value} 缺少可观测过程证据：需要 deps、before/after/value 或可解析的状态变化")
        if event.op == SemanticOp.COMPARE and len(event.targets) < 2 and not event.deps and not _has_explicit_aux_value(event.value):
            errors.append(f"第 {event.step} 步 compare 缺少 deps/value，无法说明比较依据")
        previous_state = state
    return errors


def _event_has_observable_evidence(event, previous_state: dict[str, Any] | None, state: dict[str, Any]) -> bool:
    if event.op in {SemanticOp.MARK, SemanticOp.UNMARK} and event.role:
        return True
    if event.deps or _has_explicit_aux_value(event.value) or _has_explicit_aux_value(event.before) or _has_explicit_aux_value(event.after):
        return True
    if previous_state is None:
        return bool(state)
    if _state_changed(previous_state, state):
        return True
    return any(_target_changed(target.id, previous_state, state) for target in event.targets)


def _event_ref_ids(refs: Iterable[Any]) -> set[str]:
    return {ref.id for ref in refs if getattr(ref, "id", "")}


def _state_changed(previous_state: dict[str, Any], state: dict[str, Any]) -> bool:
    keys = set(previous_state) | set(state)
    return any(not _same_value(previous_state.get(key), state.get(key)) for key in keys)


def _target_changed(target_id: str, previous_state: dict[str, Any], state: dict[str, Any]) -> bool:
    before = _resolve_target(previous_state, target_id)
    after = _resolve_target(state, target_id)
    if not before.exists and not after.exists:
        return False
    return not _same_value(before.value, after.value)


def _state_has_any(state: dict[str, Any], keys: Iterable[str]) -> bool:
    return any(key in state for key in keys)


def _event_refs_include_prefix(event, prefixes: tuple[str, ...]) -> bool:
    refs = _event_target_ids(event) | _event_dep_ids(event)
    return any(ref.startswith(prefixes) for ref in refs)


def _run_error_only_checks(
    trace: SemanticTrace,
    checks: Iterable[Callable[[SemanticTrace], list[str]]],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    for check in checks:
        errors.extend(check(trace))
    return errors, []


def _validate_set_replay(trace: SemanticTrace) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    previous_state: dict[str, Any] | None = None
    for event in trace.events:
        state = event.state or {}
        if event.op != SemanticOp.SET or not event.targets:
            previous_state = state
            continue

        target_values = [_single_target_aux_value(event.before, event.targets, index) for index, _target in enumerate(event.targets)]
        after_values = [_single_target_aux_value(event.after, event.targets, index) for index, _target in enumerate(event.targets)]
        for index, target in enumerate(event.targets):
            if _has_explicit_aux_value(event.after):
                resolved_after = _resolve_target(state, target.id)
                expected_after = after_values[index]
                if resolved_after.exists and _has_explicit_aux_value(expected_after) and not _same_value(resolved_after.value, expected_after):
                    warnings.append(f"第 {event.step} 步 after 与 state 不一致：{target.id}")
            if previous_state is not None and _has_explicit_aux_value(event.before):
                resolved_before = _resolve_target(previous_state, target.id)
                expected_before = target_values[index]
                if resolved_before.exists and _has_explicit_aux_value(expected_before) and not _same_value(resolved_before.value, expected_before):
                    warnings.append(f"第 {event.step} 步 before 与上一状态不一致：{target.id}")
        previous_state = state
    return errors, warnings


def _single_target_aux_value(value: Any, targets: list[Any], index: int) -> Any:
    if isinstance(value, list) and len(value) == len(targets):
        return value[index]
    if len(targets) == 1:
        return value
    return None


def _has_explicit_aux_value(value: Any) -> bool:
    return value is not None and value != ""


def _same_value(left: Any, right: Any) -> bool:
    import json

    try:
        return json.dumps(left, ensure_ascii=False, sort_keys=True) == json.dumps(right, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return left == right


def _validate_dependency_presence(trace: SemanticTrace) -> list[str]:
    warnings: list[str] = []
    for event in trace.events:
        state = event.state or {}
        for dep in event.deps:
            resolved = _resolve_target(state, dep.id)
            parsed = parse_target(dep.id)
            if not resolved.exists and parsed.kind not in {"node", "edge", "pointer"} and not _is_map_container_ref(parsed, state):
                warnings.append(f"第 {event.step} 步 deps 未出现在 state 中：{dep.id}")
    return warnings


def _is_map_container_ref(parsed, state: dict[str, Any]) -> bool:
    if parsed.kind != "map":
        return False
    key, _, item = parsed.name.partition(":")
    if key == "map" and item in state and isinstance(state.get(item), dict):
        return True
    return parsed.name in state and isinstance(state.get(parsed.name), dict)


def _validate_reason_grounding(trace: SemanticTrace) -> list[str]:
    warnings: list[str] = []
    for event in trace.events:
        reason = event.reason or ""
        if not reason:
            continue
        refs = {ref.id for ref in [*event.targets, *event.deps]}
        refs.update((event.state or {}).keys())
        for key in ("dp", "nums", "queue", "stack", "graph", "text", "pattern", "heap"):
            if key in reason and not any(ref == key or ref.startswith(f"{key}[") for ref in refs):
                warnings.append(f"第 {event.step} 步 reason 提到 {key}，但 targets/deps/state 缺少对应依据")
    return warnings


class Resolved:
    def __init__(self, exists: bool, value: Any = None):
        self.exists = exists
        self.value = value


def _resolve_target(state: dict[str, Any], target_id: str) -> Resolved:
    parsed = parse_target(target_id)
    if parsed.kind == "indexed":
        value = state.get(parsed.name)
        try:
            for idx in parsed.indices:
                value = value[idx]
            return Resolved(True, value)
        except Exception:
            return Resolved(False)
    if parsed.kind == "slice":
        value = state.get(parsed.name)
        start, end = parsed.indices
        if isinstance(value, (list, str)) and 0 <= start <= end <= len(value):
            return Resolved(True, value[start:end])
        return Resolved(False)
    if parsed.kind == "map":
        name = parsed.name
        key, _, item = name.partition(":")
        data = state.get(key)
        if isinstance(data, dict) and item in data:
            return Resolved(True, data[item])
        if isinstance(data, dict):
            for existing_key, existing_value in data.items():
                if str(existing_key) == item:
                    return Resolved(True, existing_value)
        if target_id in state:
            return Resolved(True, state[target_id])
        return Resolved(False)
    if target_id in state:
        return Resolved(True, state[target_id])
    return Resolved(False)


def _dict_lookup(data: dict[Any, Any], key: Any) -> Any:
    if key in data:
        return data[key]
    key_text = str(key)
    for existing_key, value in data.items():
        if str(existing_key) == key_text:
            return value
    return None


def _same_node(left: Any, right: Any) -> bool:
    return str(left) == str(right)


def _node_display(node: Any) -> str:
    return str(node)


def _event_target_ids(event) -> set[str]:
    return _event_ref_ids(event.targets)


def _event_dep_ids(event) -> set[str]:
    return _event_ref_ids(event.deps)


def _close(left: float, right: float, tolerance: float) -> bool:
    return math.isclose(left, right, rel_tol=tolerance, abs_tol=tolerance)


def _is_matrix(value: Any) -> bool:
    return isinstance(value, list) and value and all(isinstance(row, list) for row in value)


def _matrix_get(matrix: list[Any], row: int, col: int) -> Any:
    try:
        return matrix[row][col]
    except (TypeError, IndexError):
        return None


def _as_number(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return value


def _is_numeric_sequence(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _dict_int(data: dict[Any, Any], key: Any, *, default: int | None = None) -> int | None:
    value = _dict_lookup(data, key)
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return default


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _flow_edge_uv(edge: Any) -> tuple[Any, Any]:
    if isinstance(edge, str) and "->" in edge:
        return tuple(edge.split("->", 1))
    return _edge_uv(edge)


def _edge_uv(edge: Any) -> tuple[Any, Any]:
    if isinstance(edge, dict):
        return edge.get("u", edge.get("from")), edge.get("v", edge.get("to"))
    if isinstance(edge, (list, tuple)) and len(edge) >= 2:
        return edge[0], edge[1]
    return None, None


def _find(parent: dict[Any, Any], node: Any) -> Any:
    while parent[node] != node:
        parent[node] = parent[parent[node]]
        node = parent[node]
    return node

__all__ = [name for name in globals() if not name.startswith("__")]
