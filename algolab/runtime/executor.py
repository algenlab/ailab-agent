"""Execute generated variants and materialize semantic traces."""

from __future__ import annotations

from typing import Any

from algolab.runtime.dsl_guard import validate_dsl_method_usage
from algolab.runtime.sandbox import run_function
from algolab.schemas.semantic_trace import SemanticTrace, SolutionVariant
from algolab.verification.result_normalizer import canonical, results_equivalent, to_jsonable


def execute_variant(
    variant: SolutionVariant,
    input_data: Any,
    *,
    case_id: str | None = None,
    family_id: str | None = None,
    subfamily_id: str | None = None,
) -> SolutionVariant:
    """Run solve and trace code for one variant."""

    solve_result = to_jsonable(run_function(variant.code, "solve", input_data))
    validate_dsl_method_usage(variant.tracker_code, "trace")
    raw_trace = run_function(variant.tracker_code, "trace", input_data)
    raw_trace = to_jsonable(raw_trace)
    if not isinstance(raw_trace, dict):
        raise ValueError("trace(input_data) 必须返回 dict")
    if raw_trace.get("input_data") is None:
        raw_trace["input_data"] = to_jsonable(input_data)
    raw_trace["result"] = to_jsonable(raw_trace.get("result"))
    equivalence_context = {"case_id": case_id, "family_id": family_id, "subfamily_id": subfamily_id}
    if canonical(solve_result) != canonical(raw_trace["result"]) and results_equivalent(
        solve_result,
        raw_trace["result"],
        **equivalence_context,
    ):
        _rewrite_trace_answer(raw_trace, solve_result)
    _normalize_event_steps(raw_trace)
    _validate_trace_budget(raw_trace)
    trace = SemanticTrace.model_validate(raw_trace)
    if canonical(trace.input_data) != canonical(input_data):
        raise ValueError("trace.input_data 必须与本次输入完全一致")
    if not results_equivalent(solve_result, trace.result, **equivalence_context):
        raise ValueError(f"solve 结果 {solve_result!r} 与 trace 结果 {trace.result!r} 不一致")
    variant.result = solve_result
    variant.trace = trace
    return variant


def _rewrite_trace_answer(raw_trace: dict[str, Any], answer: Any) -> None:
    raw_trace["result"] = to_jsonable(answer)
    for event in raw_trace.get("events") or []:
        if not isinstance(event, dict):
            continue
        state = event.get("state")
        if isinstance(state, dict):
            if "answer" in state:
                state["answer"] = to_jsonable(answer)
            if "result" in state:
                state["result"] = to_jsonable(answer)
        targets = event.get("targets") or []
        target_ids = {str(target.get("id")) for target in targets if isinstance(target, dict)}
        if event.get("role") == "answer" or target_ids & {"answer", "result"}:
            event["value"] = to_jsonable(answer)


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
