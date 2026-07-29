from __future__ import annotations

from copy import deepcopy

import pytest

from algolab.schemas.execution_record import ExecutionRecord, ExecutionTransition, state_digest
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.runtime.dsl_guard import DSLMethodError, validate_dsl_method_usage
from algolab.runtime.sandbox import SandboxError, run_instrumented_trace
from algolab.verification.execution_record_validator import validate_execution_record


def _trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "algorithm": "demo",
            "input_data": {"value": 1},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "value"}],
                    "reason": "create value",
                    "state": {"value": 1},
                    "code_line": 2,
                },
                {
                    "step": 1,
                    "op": "set",
                    "targets": [{"id": "value"}],
                    "before": 1,
                    "after": 2,
                    "reason": "update value",
                    "state": {"value": 2},
                    "code_line": 3,
                },
                {
                    "step": 2,
                    "op": "mark",
                    "targets": [{"id": "answer"}],
                    "value": 2,
                    "role": "answer",
                    "reason": "return answer",
                    "state": {"value": 2, "answer": 2},
                    "code_line": 4,
                },
            ],
        }
    )


def _record(mode: str = "atomic") -> ExecutionRecord:
    states = [{}, {"value": 1}, {"value": 2}, {"value": 2, "answer": 2}]
    return ExecutionRecord(
        run_id="runtime-0123456789abcdef",
        mode=mode,
        result=2,
        result_hash=state_digest(2),
        initial_state_hash=state_digest(states[0]),
        final_state_hash=state_digest(states[-1]),
        transitions=[
            ExecutionTransition(
                run_id="runtime-0123456789abcdef",
                index=index,
                op=op,
                targets=targets,
                before_state_hash=state_digest(states[index]),
                after_state_hash=state_digest(states[index + 1]),
                event_index=index,
                callsite_line=index + 2,
                committed=True,
            )
            for index, (op, targets) in enumerate(
                [("create", ["value"]), ("set", ["value"]), ("mark", ["answer"])]
            )
        ],
    )


def test_valid_atomic_record_binds_result_transitions_and_every_trace_prefix() -> None:
    report = validate_execution_record(_record(), _trace())

    assert report.ok is True
    assert report.same_execution_binding is True
    assert report.prefix_replay_ok is True
    assert report.final_state_ok is True
    assert report.unlogged_mutation_count == 0
    assert report.state_event_mismatch_count == 0
    assert report.errors == []


def test_validator_rejects_mixed_run_ids_and_broken_state_chain() -> None:
    record = _record()
    record.transitions[1].run_id = "runtime-other"
    record.transitions[2].before_state_hash = state_digest({"value": 999})

    report = validate_execution_record(record, _trace())

    assert report.ok is False
    assert report.same_execution_binding is False
    assert report.prefix_replay_ok is False
    assert any("run_id" in error for error in report.errors)
    assert any("state chain" in error for error in report.errors)


def test_validator_rejects_unlogged_transition_and_decoupled_claim_mismatch() -> None:
    record = _record(mode="decoupled")
    record.transitions[1].committed = False
    record.transitions[1].event_index = None
    record.transitions[2].event_index = 1
    record.transitions[2].claim_mismatches = ["targets", "after"]
    trace_data = _trace().model_dump(mode="json")
    trace_data["events"].pop(1)
    trace_data["events"][1]["step"] = 1

    report = validate_execution_record(record, SemanticTrace.model_validate(trace_data))

    assert report.ok is False
    assert report.unlogged_mutation_count == 1
    assert report.state_event_mismatch_count == 2
    assert any("unlogged" in error for error in report.errors)
    assert any("claim mismatch" in error for error in report.errors)


def test_validator_rejects_trace_state_or_result_not_owned_by_record() -> None:
    trace_data = _trace().model_dump(mode="json")
    trace_data["events"][1]["state"] = {"value": 7}
    trace_data["result"] = 7
    trace = SemanticTrace.model_validate(trace_data)

    report = validate_execution_record(_record(), trace)

    assert report.ok is False
    assert report.prefix_replay_ok is False
    assert report.result_binding_ok is False
    assert report.state_event_mismatch_count >= 1


def test_execution_record_round_trip_preserves_runtime_evidence() -> None:
    original = _record(mode="decoupled")

    restored = ExecutionRecord.model_validate(deepcopy(original.model_dump(mode="json")))

    assert restored == original


ATOMIC_SOURCE = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    value = sess.scalar("value", input_data["value"])
    value.set(int(value) + 1, reason="increment")
    sess.result(int(value))
    return sess.to_trace()
'''


DECOUPLED_SOURCE = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    value = sess.scalar("value", input_data["value"])
    sess.record(op="create", targets=["value"], before=None, after=None)
    before = int(value)
    value.set(int(value) + 1, reason="increment")
    sess.record(op="set", targets=["value"], before=before, after=int(value))
    sess.result(int(value))
    sess.record(op="mark", targets=["answer"], before=None, after=int(value))
    return sess.to_trace()
'''


def test_atomic_runtime_owns_result_trace_run_id_and_callsites() -> None:
    bundle = run_instrumented_trace(ATOMIC_SOURCE, {"value": 1}, mode="atomic")
    trace = SemanticTrace.model_validate(bundle["trace"])
    record = ExecutionRecord.model_validate(bundle["execution_record"])

    assert bundle["function_return_ignored"] is True
    assert trace.result == 2
    assert record.result == 2
    assert record.run_id.startswith("runtime-")
    assert [row.op for row in record.transitions] == ["create", "create", "set", "mark"]
    assert [row.callsite_line for row in record.transitions] == [2, 3, 4, 5]
    assert all(row.committed for row in record.transitions)
    assert validate_execution_record(record, trace).ok is True


def test_decoupled_runtime_accepts_matching_explicit_records() -> None:
    bundle = run_instrumented_trace(DECOUPLED_SOURCE, {"value": 1}, mode="decoupled")
    trace = SemanticTrace.model_validate(bundle["trace"])
    record = ExecutionRecord.model_validate(bundle["execution_record"])

    assert [row.op for row in record.transitions] == ["create", "create", "set", "mark"]
    assert all(row.committed for row in record.transitions)
    assert all(not row.claim_mismatches for row in record.transitions)
    assert validate_execution_record(record, trace).ok is True


def test_decoupled_runtime_rejects_empty_record_acknowledgement() -> None:
    source = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    value = sess.scalar("value", 1)
    sess.record()
    sess.result(int(value))
    return sess.to_trace()
'''

    with pytest.raises(SandboxError, match="requires op, targets, before, and after"):
        run_instrumented_trace(source, {}, mode="decoupled")


def test_decoupled_runtime_rejects_incomplete_manual_claim() -> None:
    source = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    value = sess.scalar("value", 1)
    sess.record(op="create", targets=["value"])
    sess.result(int(value))
    return sess.to_trace()
'''

    with pytest.raises(SandboxError, match="requires op, targets, before, and after"):
        run_instrumented_trace(source, {}, mode="decoupled")


def test_decoupled_record_commits_claims_for_all_internal_events_from_one_service_call() -> None:
    source = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    trie = sess.trie("trie")
    sess.record(op="create", targets=["trie"], before=None, after=None)
    trie.insert("ab")
    sess.record(events=[
        {"op": "create", "targets": ["node:1"], "before": None, "after": None},
        {"op": "create", "targets": ["node:2"], "before": None, "after": None},
        {"op": "set", "targets": ["node:2"], "before": None, "after": None},
    ])
    answer = trie.prefix_count("a")
    sess.result(answer)
    sess.record(op="mark", targets=["answer"], before=None, after=answer)
    return sess.to_trace()
'''

    bundle = run_instrumented_trace(source, {}, mode="decoupled")
    trace = SemanticTrace.model_validate(bundle["trace"])
    record = ExecutionRecord.model_validate(bundle["execution_record"])
    report = validate_execution_record(record, trace)

    insert_rows = [row for row in record.transitions if row.callsite_line == 5]
    assert len(insert_rows) == 3
    assert all(row.committed for row in insert_rows)
    assert report.ok is True


def test_decoupled_redundant_record_without_pending_transition_is_rejected() -> None:
    source = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    value = sess.scalar("value", 1)
    sess.record(op="create", targets=["value"], before=None, after=None)
    sess.note("read only")
    sess.record(op="explain", targets=[], before=None, after=None)
    sess.result(int(value))
    return sess.to_trace()
'''

    with pytest.raises(SandboxError, match="has no pending state transition"):
        run_instrumented_trace(source, {}, mode="decoupled")


def test_decoupled_repeated_calls_on_the_same_source_line_need_separate_records() -> None:
    source = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    values = sess.array("values", [])
    sess.record(op="create", targets=["values"], before=None, after=None)
    for item in [1, 2]:
        values.append(item)
    sess.record(op="set", targets=["values[1]"], before=None, after=2)
    sess.result(list(values))
    sess.record(op="mark", targets=["answer"], before=None, after=list(values))
    return sess.to_trace()
'''

    bundle = run_instrumented_trace(source, {}, mode="decoupled")
    trace = SemanticTrace.model_validate(bundle["trace"])
    record = ExecutionRecord.model_validate(bundle["execution_record"])
    report = validate_execution_record(record, trace)

    append_rows = [row for row in record.transitions if row.callsite_line == 6]
    assert len(append_rows) == 2
    assert [row.committed for row in append_rows] == [False, True]
    assert report.ok is False
    assert report.unlogged_mutation_count == 1


def test_decoupled_runtime_preserves_unlogged_and_mismatched_transition_evidence() -> None:
    source = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    value = sess.scalar("value", input_data["value"])
    value.set(2, reason="unlogged create")
    sess.record(op="move", targets=["wrong"], before=9, after=8, reason="wrong claim")
    sess.result(int(value))
    return sess.to_trace()
'''

    bundle = run_instrumented_trace(source, {"value": 1}, mode="decoupled")
    trace = SemanticTrace.model_validate(bundle["trace"])
    record = ExecutionRecord.model_validate(bundle["execution_record"])
    report = validate_execution_record(record, trace)

    assert len(record.transitions) == 4
    assert record.transitions[0].committed is True
    assert record.transitions[1].committed is False
    assert set(record.transitions[2].claim_mismatches) >= {"op", "targets", "before", "after"}
    assert record.transitions[3].committed is False
    assert report.ok is False
    assert report.unlogged_mutation_count == 2
    assert report.state_event_mismatch_count >= 4


def test_dsl_guard_rejects_private_state_access_but_allows_decoupled_record() -> None:
    validate_dsl_method_usage(DECOUPLED_SOURCE, "trace")
    private_source = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    sess._snapshot = {"answer": 7}
    return sess.to_trace()
'''

    try:
        validate_dsl_method_usage(private_source, "trace")
    except DSLMethodError as exc:
        assert "_snapshot" in str(exc)
    else:
        raise AssertionError("private TraceSession state access was not rejected")
