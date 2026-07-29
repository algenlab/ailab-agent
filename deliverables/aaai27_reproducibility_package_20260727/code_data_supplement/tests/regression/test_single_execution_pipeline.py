from __future__ import annotations

import pytest

from algolab.pipeline import _try_materialize
from algolab.runtime.executor import execute_variant
from algolab.schemas.input import ProblemInput
from algolab.schemas.semantic_trace import SolutionVariant


ATOMIC_TRACKER = '''def trace(input_data):
    sess = TraceSession("increment", input_data)
    value = sess.scalar("value", input_data["value"])
    value.set(int(value) + 1, reason="increment")
    sess.result(int(value))
    return {"forged": "return value is ignored"}
'''


DECOUPLED_TRACKER = '''def trace(input_data):
    sess = TraceSession("increment", input_data)
    value = sess.scalar("value", input_data["value"])
    sess.record(op="create", targets=["value"], before=None, after=None)
    before = int(value)
    value.set(int(value) + 1, reason="increment")
    sess.record(op="set", targets=["value"], before=before, after=int(value))
    sess.result(int(value))
    sess.record(op="mark", targets=["answer"], before=None, after=int(value))
    return sess.to_trace()
'''


def _variant(tracker_code: str) -> SolutionVariant:
    return SolutionVariant(
        id="v1",
        name="increment",
        strategy="increment once",
        code='def solve(input_data):\n    raise ValueError("solve must not execute")',
        tracker_code=tracker_code,
    )


@pytest.mark.parametrize(
    ("mode", "tracker_code"),
    [("atomic", ATOMIC_TRACKER), ("decoupled", DECOUPLED_TRACKER)],
)
def test_single_execution_modes_never_run_solve_and_bind_tracker_result(mode: str, tracker_code: str) -> None:
    materialized = execute_variant(
        _variant(tracker_code),
        {"value": 1},
        execution_mode=mode,
    )

    assert materialized.result == 2
    assert materialized.trace is not None
    assert materialized.trace.result == 2
    assert materialized.execution_record is not None
    assert materialized.execution_record.mode == mode
    assert materialized.execution_validation["ok"] is True


def test_decoupled_pipeline_rejects_an_unlogged_state_change() -> None:
    tracker = '''def trace(input_data):
    sess = TraceSession("increment", input_data)
    value = sess.scalar("value", input_data["value"])
    value.set(2)
    sess.result(2)
    return sess.to_trace()
'''

    with pytest.raises(ValueError, match="single-execution validation failed.*unlogged"):
        execute_variant(_variant(tracker), {"value": 1}, execution_mode="decoupled")


def test_historical_separate_mode_retains_solve_trace_consistency_check() -> None:
    tracker = ATOMIC_TRACKER.replace('return {"forged": "return value is ignored"}', "return sess.to_trace()")
    variant = _variant(tracker).model_copy(
        update={"code": 'def solve(input_data):\n    return 99'}
    )

    with pytest.raises(ValueError, match="solve 结果 99 与 trace 结果 2 不一致"):
        execute_variant(variant, {"value": 1}, execution_mode="separate")


def test_release_gate_rejects_self_consistent_single_execution_when_oracle_disagrees() -> None:
    request = ProblemInput(
        problem="increment once",
        input_data={"value": 1},
        expected_result=3,
        solution_count=1,
        teaching_enrichment=False,
        execution_mode="atomic",
    )
    spec = {
        "problem_title": "increment once",
        "input_contract": "value is int",
        "variants": [_variant(ATOMIC_TRACKER).model_dump(exclude={"trace", "result"})],
    }

    artifact, errors = _try_materialize(request, spec)

    assert artifact.validation.release_gate.release_ready is False
    assert artifact.variants == []
    assert any("结果 2 与 expected 3 不一致" in error for error in errors)
