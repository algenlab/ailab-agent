# Single-Execution Pilot and Mutant Audit Design

## Scope

Implement the smallest compatible execution path needed for Plan-3 experiments one and three. Preserve the existing `SolutionVariant`, SceneGraph, renderer, and historical `separate` execution mode. Add two opt-in experiment modes:

- `atomic`: execute `tracker_code/trace(input_data)` once; its runtime-owned `TraceSession` record supplies both result and trace.
- `decoupled`: execute the same shape of tracker once, but state-changing service operations require a separate explicit event-record call.

The first run is a paired 23-family pilot. Full-200 remains gated on pilot review. The wrong-but-self-consistent audit uses frozen generated tracker sources and does not call an LLM.

## Runtime Record

Each sandbox execution creates one runtime-issued run ID. `TraceSession` records every service transition outside the model-returned trace with:

- transition index and runtime-captured generated-source line;
- operation and targets;
- before-state and after-state hashes;
- committed event index, or an unlogged marker;
- claim mismatch fields for decoupled mode.

The sandbox exports the trace from the live session after the generated function returns. It does not trust a model-mutated returned trace. The execution result is the same session's `result` value.

## Atomic and Decoupled Semantics

Atomic mode preserves current DSL calls: every service operation updates canonical state and commits its event in one method call. `sess.result(value)` is also a service operation and commits the answer event immediately.

Decoupled mode performs the same state transition but leaves it pending. Generated code must call `sess.record(...)` before another service transition and before returning. The explicit record supplies the claimed operation, targets, before and after values. Runtime truth remains private. Missing records become unlogged transitions; conflicting claims become state/event mismatches.

Both modes run in the same sandbox, use the same service objects, emit the same public `SemanticTrace`, and feed the unchanged compiler and renderer.

### Frozen Manual-Claim Contract

The confirmatory Decoupled condition does not accept an empty `sess.record()` acknowledgement. Every record must provide `op`, `targets`, `before`, and `after`; optional presentation fields such as `reason`, `value`, `role`, and `deps` do not replace those four required facts. A public DSL call with one pending transition uses the keyword form. A public DSL call that creates multiple internal transitions uses `sess.record(events=[...])`, with one complete claim per pending transition in runtime order. The runtime compares claims with private pending facts and never fills omitted required fields for the model.

The earlier explicit-commit pilot remains an exploratory result. The confirmatory 23-family pilot is written to a new output directory, carries prompt profile version `single-execution-pilot-v2`, and reruns both conditions rather than reusing the earlier Atomic outputs. Pilot interpretation remains frozen: a higher Atomic Machine OK rate together with fewer mismatch/unlogged failures supports the reliability hypothesis; non-inferior reliability with lower cost supports only efficiency; otherwise the result does not support atomic coupling as the primary contribution.

## Validation

The execution-record validator checks:

1. one runtime-issued run ID binds result, transitions and events;
2. every service transition has exactly one committed event;
3. runtime before/after hashes form a contiguous chain;
4. each event state hash equals its runtime after-state hash;
5. decoupled explicit claims agree with the pending runtime transition;
6. no pending or unlogged mutation remains at return;
7. final trace result equals the same execution record's result.

Expected result and independent verifier checks remain outside this validator and continue to determine algorithm correctness at the release gate.

## Pilot

Select one deterministic case per family from the frozen Full-200 report using the existing stratified manifest builder with `total=23`. Run Atomic and Decoupled with the same model, case order, temperature, solution count, two candidates, two repairs, teaching enrichment, browser audit, and fixed shell.

Primary outcome is Machine OK. Mechanism outcomes are final generation pass, execution binding, prefix replay, state/event mismatch, unlogged mutation, model calls, repair calls, total tokens, API latency and time-to-valid. Analyze paired binary outcomes with exact McNemar and 10,000 paired bootstrap draws. Pilot results are diagnostic and do not replace Full-200.

## Wrong-but-Self-Consistent Audit

Select about 30 frozen successful cases covering all 23 families. Mutate tracker source before its single execution. Prefer comparison/boundary changes and omitted updates; use a wrong-return mutation as a deterministic applicable fallback. Retain only mutants that execute normally and disagree with the trusted expected result.

For every applicable mutant report execution binding, prefix/final replay, deterministic replay, oracle mismatch and final release rejection. Report Wilson 95% intervals. A mutant that disagrees with the oracle but passes release is a blocking defect.

## Compatibility

Existing callers default to `separate`. New experiment runners explicitly select `atomic` or `decoupled`. No historical result is silently reinterpreted. Public experiment reports contain only protocol, results, statistics and limitations, not implementation-change narration.
