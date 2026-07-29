# Single-Execution Pilot and Mutant Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimally invasive single-execution evidence path, run the paired 23-family Atomic/Decoupled pilot, and complete the wrong-but-self-consistent solver audit.

**Architecture:** Keep historical separate execution intact. Capture a private `TraceSession` execution record inside the sandbox for opt-in Atomic and Decoupled modes, validate it before the existing trace/compiler pipeline, and expose only compact evidence summaries to experiment scripts.

**Tech Stack:** Python 3.10, Pydantic, multiprocessing sandbox, pytest, NumPy/SciPy, existing AlgoLab benchmark and browser-audit scripts.

---

### Task 1: Execution-record contract

**Files:**
- Create: `algolab/schemas/execution_record.py`
- Create: `algolab/verification/execution_record_validator.py`
- Create: `tests/regression/test_single_execution_record.py`

- [ ] Write failing tests for run binding, contiguous state hashes, event/state equality, unlogged mutations and decoupled claim mismatch.
- [ ] Run the focused test and confirm failure because the schema/validator does not exist.
- [ ] Add the minimal Pydantic record models and pure validator.
- [ ] Run the focused test and confirm all contract tests pass.

### Task 2: Runtime capture

**Files:**
- Modify: `algolab/runtime/dsl.py`
- Modify: `algolab/runtime/dsl_guard.py`
- Modify: `algolab/runtime/sandbox.py`
- Test: `tests/regression/test_single_execution_record.py`

- [ ] Add failing tests proving Atomic emits one transition/event pair per state change and result, with a runtime run ID and captured callsite.
- [ ] Add failing tests proving Decoupled requires `sess.record(...)`, detects missing/mismatched records and cannot use private DSL attributes.
- [ ] Implement per-process capture lifecycle and runtime-owned trace export.
- [ ] Implement pending Decoupled transitions and explicit record commit.
- [ ] Run focused runtime and existing sandbox/DSL tests.

### Task 3: Pipeline integration

**Files:**
- Modify: `algolab/schemas/input.py`
- Modify: `algolab/schemas/semantic_trace.py`
- Modify: `algolab/runtime/executor.py`
- Modify: `algolab/pipeline.py`
- Test: `tests/regression/test_single_execution_pipeline.py`

- [ ] Add failing tests showing Atomic and Decoupled call tracker exactly once, never call solve, bind result to trace and reject oracle disagreement.
- [ ] Add `execution_mode` request/variant evidence fields without changing historical defaults.
- [ ] Route new modes through the instrumented sandbox and execution validator.
- [ ] Preserve `separate` behavior and run existing executor/pipeline regressions.

### Task 4: Generation profiles and benchmark metadata

**Files:**
- Create: `algolab/generation/execution_modes.py`
- Modify: `algolab/generation/solution_generator.py`
- Modify: `algolab/generation/repair.py`
- Modify: `scripts/run_llm_benchmark.py`
- Test: `tests/regression/test_single_execution_prompt_profiles.py`

- [ ] Add failing tests for Atomic and Decoupled prompt differences and frozen metadata hashes.
- [ ] Add mode-specific prompt appendices, including explicit Decoupled record examples.
- [ ] Add CLI/config/result metadata for execution mode and evidence metrics.
- [ ] Verify controlled fields remain equal apart from the declared mode/prompt difference.

### Task 5: Pilot manifest, runner and statistics

**Files:**
- Create: `scripts/run_atomic_service_pilot.sh`
- Create: `scripts/analyze_atomic_service_pilot.py`
- Create: `tests/regression/test_atomic_service_pilot.py`

- [ ] Generate a deterministic 23-case, 23-family manifest from the frozen Full-200 report.
- [ ] Test paired-ID/config validation and mechanism-metric aggregation.
- [ ] Implement interleaved Atomic/Decoupled generation and browser-audit orchestration.
- [ ] Implement McNemar, paired bootstrap, cost and mechanism summaries.
- [ ] Run the pilot and freeze all raw and analyzed outputs.

### Task 6: Self-consistent mutant audit

**Files:**
- Create: `scripts/run_wrong_self_consistent_solver_audit.py`
- Create: `tests/regression/test_wrong_self_consistent_solver_audit.py`

- [ ] Add failing tests for deterministic AST mutations, applicable filtering and rejection accounting.
- [ ] Implement comparison/boundary, omitted-update and wrong-return mutation candidates.
- [ ] Execute mutants through Atomic runtime twice, require deterministic replay, and compare with trusted expected results.
- [ ] Compute execution consistency, oracle mismatch, release rejection and Wilson intervals.
- [ ] Freeze the manifest, every mutation attempt and the final report.

### Task 7: Reports and verification

**Files:**
- Create: `docs/35_ATOMIC_SERVICE_PILOT_EXPERIMENT.md`
- Create: `docs/36_WRONG_SELF_CONSISTENT_SOLVER_AUDIT.md`

- [ ] Write reports containing only experimental protocol, metrics, results, statistics, limitations and artifact locations.
- [ ] Run focused tests, related regression suites, syntax checks and output consistency assertions.
- [ ] Confirm every required raw artifact and source hash is present.
- [ ] Package the two experiment result directories and reports.

