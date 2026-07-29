"""Validate runtime-owned single-execution evidence against its public trace."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from algolab.schemas.execution_record import ExecutionRecord, state_digest
from algolab.schemas.semantic_trace import SemanticTrace


class ExecutionRecordValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    same_execution_binding: bool
    prefix_replay_ok: bool
    final_state_ok: bool
    result_binding_ok: bool
    unlogged_mutation_count: int = Field(ge=0)
    state_event_mismatch_count: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)


def validate_execution_record(
    record: ExecutionRecord,
    trace: SemanticTrace,
) -> ExecutionRecordValidation:
    errors: list[str] = []
    transitions = record.transitions

    mixed_run_ids = [row.index for row in transitions if row.run_id != record.run_id]
    same_execution_binding = bool(record.run_id) and not mixed_run_ids
    if mixed_run_ids:
        errors.append(f"execution run_id mismatch at transitions {mixed_run_ids}")

    prefix_replay_ok = True
    previous_hash = record.initial_state_hash
    for expected_index, transition in enumerate(transitions):
        if transition.index != expected_index:
            prefix_replay_ok = False
            errors.append(
                f"transition index mismatch: expected {expected_index}, found {transition.index}"
            )
        if transition.before_state_hash != previous_hash:
            prefix_replay_ok = False
            errors.append(f"state chain mismatch at transition {transition.index}")
        previous_hash = transition.after_state_hash

    unlogged = [row for row in transitions if not row.committed or row.event_index is None]
    if unlogged:
        prefix_replay_ok = False
        errors.append(
            "unlogged transitions: " + ", ".join(str(row.index) for row in unlogged)
        )

    claim_mismatch_count = sum(len(row.claim_mismatches) for row in transitions)
    if claim_mismatch_count:
        errors.append(
            "decoupled claim mismatch: "
            + "; ".join(
                f"{row.index}={','.join(row.claim_mismatches)}"
                for row in transitions
                if row.claim_mismatches
            )
        )

    trace_state_mismatches = 0
    committed = [row for row in transitions if row.committed and row.event_index is not None]
    seen_event_indexes: set[int] = set()
    for transition in committed:
        assert transition.event_index is not None
        event_index = transition.event_index
        if event_index in seen_event_indexes or event_index >= len(trace.events):
            trace_state_mismatches += 1
            prefix_replay_ok = False
            errors.append(
                f"transition {transition.index} has invalid event_index {event_index}"
            )
            continue
        seen_event_indexes.add(event_index)
        event = trace.events[event_index]
        mismatch_fields: list[str] = []
        if state_digest(event.state) != transition.after_state_hash:
            mismatch_fields.append("state")
        if event.op.value != transition.op:
            mismatch_fields.append("op")
        if [target.id for target in event.targets] != transition.targets:
            mismatch_fields.append("targets")
        if mismatch_fields:
            trace_state_mismatches += len(mismatch_fields)
            prefix_replay_ok = False
            errors.append(
                f"event mismatch at transition {transition.index}: {','.join(mismatch_fields)}"
            )
    if len(seen_event_indexes) != len(trace.events):
        prefix_replay_ok = False
        missing = sorted(set(range(len(trace.events))) - seen_event_indexes)
        trace_state_mismatches += len(missing)
        errors.append(f"trace events without runtime transition: {missing}")

    final_state_ok = bool(transitions) and previous_hash == record.final_state_hash
    if not final_state_ok:
        errors.append("final state hash does not match the transition chain")

    result_binding_ok = (
        state_digest(record.result) == record.result_hash
        and state_digest(trace.result) == record.result_hash
    )
    if not result_binding_ok:
        errors.append("trace result is not bound to the runtime execution result")

    state_event_mismatch_count = claim_mismatch_count + trace_state_mismatches
    ok = (
        same_execution_binding
        and prefix_replay_ok
        and final_state_ok
        and result_binding_ok
        and not unlogged
        and state_event_mismatch_count == 0
    )
    return ExecutionRecordValidation(
        ok=ok,
        same_execution_binding=same_execution_binding,
        prefix_replay_ok=prefix_replay_ok,
        final_state_ok=final_state_ok,
        result_binding_ok=result_binding_ok,
        unlogged_mutation_count=len(unlogged),
        state_event_mismatch_count=state_event_mismatch_count,
        errors=errors,
    )
