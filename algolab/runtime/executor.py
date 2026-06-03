"""Execute generated variants and materialize semantic traces."""

from __future__ import annotations

from typing import Any

from algolab.runtime.sandbox import run_function
from algolab.schemas.semantic_trace import SemanticTrace, SolutionVariant


def to_jsonable(value: Any) -> Any:
    import json

    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        if isinstance(value, set):
            return sorted(to_jsonable(v) for v in value)
        if isinstance(value, tuple):
            return [to_jsonable(v) for v in value]
        if isinstance(value, dict):
            return {str(k): to_jsonable(v) for k, v in value.items()}
        return str(value)


def canonical(value: Any) -> str:
    import json

    return json.dumps(to_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def results_equivalent(left: Any, right: Any) -> bool:
    if canonical(left) == canonical(right):
        return True
    left_graph = _canonical_graph_set_result(left)
    right_graph = _canonical_graph_set_result(right)
    return left_graph is not None and left_graph == right_graph


def _canonical_graph_set_result(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or "articulation" not in value or "bridges" not in value:
        return None
    bridges = []
    for edge in value.get("bridges") or []:
        if not isinstance(edge, (list, tuple)) or len(edge) < 2:
            return None
        bridges.append(tuple(sorted((str(edge[0]), str(edge[1])))))
    return {
        "articulation": sorted(str(item) for item in (value.get("articulation") or [])),
        "bridges": sorted(bridges),
    }


def execute_variant(variant: SolutionVariant, input_data: Any) -> SolutionVariant:
    """Run solve and trace code for one variant."""

    solve_result = to_jsonable(run_function(variant.code, "solve", input_data))
    raw_trace = run_function(variant.tracker_code, "trace", input_data)
    if not isinstance(raw_trace, dict):
        raise ValueError("trace(input_data) 必须返回 dict")
    raw_trace["result"] = to_jsonable(raw_trace.get("result"))
    _normalize_event_steps(raw_trace)
    _validate_trace_budget(raw_trace)
    trace = SemanticTrace.model_validate(raw_trace)
    if canonical(trace.input_data) != canonical(input_data):
        raise ValueError("trace.input_data 必须与本次输入完全一致")
    if not results_equivalent(solve_result, trace.result):
        raise ValueError(f"solve 结果 {solve_result!r} 与 trace 结果 {trace.result!r} 不一致")
    variant.result = solve_result
    variant.trace = trace
    return variant


def run_verifier(verifier_code: str, input_data: Any) -> Any:
    return to_jsonable(run_function(verifier_code, "verify", input_data))


def _normalize_event_steps(raw_trace: dict[str, Any]) -> None:
    events = raw_trace.get("events")
    if not isinstance(events, list):
        return
    for index, event in enumerate(events):
        if isinstance(event, dict):
            event["step"] = index


def _validate_trace_budget(raw_trace: dict[str, Any]) -> None:
    events = raw_trace.get("events")
    if not isinstance(events, list):
        return
    max_events = _trace_max_events(raw_trace)
    if len(events) > max_events and not _has_tracer_full_semantic_budget(raw_trace, max_events):
        raise ValueError(f"trace events 过多：{len(events)}，请压缩到 {max_events} 步以内")
    for event in events:
        if not isinstance(event, dict):
            continue
        state = event.get("state")
        if isinstance(state, dict) and len(str(state)) > 20000:
            raise ValueError("单步 state 过大，请只保留可视化必要变量")


def _trace_max_events(raw_trace: dict[str, Any]) -> int:
    events = raw_trace.get("events")
    if not isinstance(events, list):
        return 80
    meta = _trace_meta_from_events(events)
    if isinstance(meta, dict) and isinstance(meta.get("max_events"), int) and meta["max_events"] > 0:
        return meta["max_events"]
    return 80


def _has_tracer_full_semantic_budget(raw_trace: dict[str, Any], max_events: int) -> bool:
    events = raw_trace.get("events")
    if not isinstance(events, list):
        return False
    meta = _trace_meta_from_events(events)
    if not isinstance(meta, dict) or meta.get("sampled") is True:
        return False
    expected_updates = meta.get("expected_updates")
    if not isinstance(expected_updates, dict) or not expected_updates:
        return False
    expected_total = 0
    for value in expected_updates.values():
        if not isinstance(value, int) or value < 0:
            return False
        expected_total += value
    return expected_total <= max_events


def _trace_meta_from_events(events: list[Any]) -> dict[str, Any] | None:
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        state = event.get("state")
        if not isinstance(state, dict):
            continue
        meta = state.get("_trace_meta")
        if isinstance(meta, dict):
            return meta
    return None
