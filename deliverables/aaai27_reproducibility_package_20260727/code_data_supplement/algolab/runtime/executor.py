"""Execute generated variants and materialize semantic traces."""

from __future__ import annotations

from typing import Any

from algolab.runtime.dsl_guard import validate_dsl_method_usage
from algolab.runtime.sandbox import run_function, run_instrumented_trace
from algolab.schemas.execution_record import ExecutionRecord
from algolab.schemas.semantic_trace import SemanticTrace, SolutionVariant
from algolab.verification.execution_record_validator import validate_execution_record
from algolab.verification.result_normalizer import canonical, results_equivalent, to_jsonable


def execute_variant(
    variant: SolutionVariant,
    input_data: Any,
    *,
    case_id: str | None = None,
    family_id: str | None = None,
    subfamily_id: str | None = None,
    execution_mode: str = "atomic",
) -> SolutionVariant:
    """Run the authoritative instrumented trace once for one variant."""

    validate_dsl_method_usage(variant.tracker_code, "trace")
    if execution_mode == "separate":
        execution_mode = "atomic"
    execution_record = None
    execution_validation: dict[str, Any] = {}
    if execution_mode in {"atomic", "decoupled"}:
        bundle = run_instrumented_trace(
            variant.tracker_code,
            input_data,
            mode=execution_mode,
        )
        raw_trace = bundle["trace"]
        execution_record = ExecutionRecord.model_validate(bundle["execution_record"])
        execution_result = to_jsonable(execution_record.result)
    else:
        raise ValueError(f"unsupported execution_mode: {execution_mode}")
    raw_trace = to_jsonable(raw_trace)
    if not isinstance(raw_trace, dict):
        raise ValueError("trace(input_data) 必须返回 dict")
    if raw_trace.get("input_data") is None:
        raw_trace["input_data"] = to_jsonable(input_data)
    raw_trace["result"] = to_jsonable(raw_trace.get("result"))
    equivalence_context = {"case_id": case_id, "family_id": family_id, "subfamily_id": subfamily_id}
    _normalize_event_steps(raw_trace)
    _validate_trace_budget(raw_trace)
    trace = SemanticTrace.model_validate(raw_trace)
    if canonical(trace.input_data) != canonical(input_data):
        raise ValueError("trace.input_data 必须与本次输入完全一致")
    if not results_equivalent(execution_result, trace.result, **equivalence_context):
        raise ValueError(f"单执行结果 {execution_result!r} 与 trace 结果 {trace.result!r} 不一致")
    if execution_record is not None:
        validation = validate_execution_record(execution_record, trace)
        execution_validation = validation.model_dump(mode="json")
        if not validation.ok:
            raise ValueError(
                "single-execution validation failed: " + "; ".join(validation.errors)
            )
    variant.result = execution_result
    variant.trace = trace
    variant.execution_record = execution_record
    variant.execution_validation = execution_validation
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
    for event in events:
        if not isinstance(event, dict):
            continue
        state = event.get("state")
        if isinstance(state, dict) and len(str(state)) > 20000:
            raise ValueError("单步 state 过大，请只保留可视化必要变量")
