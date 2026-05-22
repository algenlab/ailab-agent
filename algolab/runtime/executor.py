"""Execute generated variants and materialize semantic traces."""

from __future__ import annotations

from typing import Any

from algolab.compiler.target_parser import parse_target
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


def execute_variant(variant: SolutionVariant, input_data: Any) -> SolutionVariant:
    """Run solve and trace code for one variant."""

    solve_result = to_jsonable(run_function(variant.code, "solve", input_data))
    raw_trace = run_function(variant.tracker_code, "trace", input_data)
    if not isinstance(raw_trace, dict):
        raise ValueError("trace(input_data) 必须返回 dict")
    raw_trace["result"] = to_jsonable(raw_trace.get("result"))
    _normalize_event_steps(raw_trace)
    _normalize_event_refs(raw_trace)
    _validate_trace_budget(raw_trace)
    trace = SemanticTrace.model_validate(raw_trace)
    if canonical(trace.input_data) != canonical(input_data):
        raise ValueError("trace.input_data 必须与本次输入完全一致")
    if canonical(solve_result) != canonical(trace.result):
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


def _normalize_event_refs(raw_trace: dict[str, Any]) -> None:
    events = raw_trace.get("events")
    if not isinstance(events, list):
        return
    for event in events:
        if not isinstance(event, dict):
            continue
        for field in ("targets", "deps"):
            refs = event.get(field)
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if isinstance(ref, dict) and "id" in ref:
                    ref["id"] = _normalize_ref_id(ref["id"])


def _normalize_ref_id(raw: Any) -> str:
    text = str(raw).strip()
    parsed = parse_target(text)
    if parsed.kind == "map":
        key, _, item = parsed.name.partition(":")
        if key and item:
            return f"{key}[{item}]"
    return text


def _validate_trace_budget(raw_trace: dict[str, Any]) -> None:
    events = raw_trace.get("events")
    if not isinstance(events, list):
        return
    if len(events) > 80:
        raise ValueError(f"trace events 过多：{len(events)}，请压缩到 80 步以内")
    for event in events:
        if not isinstance(event, dict):
            continue
        state = event.get("state")
        if isinstance(state, dict) and len(str(state)) > 20000:
            raise ValueError("单步 state 过大，请只保留可视化必要变量")
