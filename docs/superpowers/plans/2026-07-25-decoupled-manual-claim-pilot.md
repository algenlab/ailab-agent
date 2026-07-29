# Decoupled Manual-Claim Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the Plan-3 Decoupled condition so the model explicitly maintains event facts, then rerun the frozen paired 23-family pilot without reusing the exploratory outputs.

**Architecture:** Keep Atomic and historical separate execution unchanged. In Decoupled mode, retain runtime-owned pending transitions but require complete model claims before committing public events; compare those claims with private runtime truth and preserve mismatch evidence. Version and freeze the prompt contract, then write the new pilot to an isolated output directory.

**Tech Stack:** Python 3.10, Pydantic, existing TraceSession sandbox, pytest, Bash, jq, existing paired analysis and browser machine-audit scripts.

---

### Task 1: Strict manual claims

**Files:**
- Modify: `tests/regression/test_single_execution_record.py`
- Modify: `algolab/runtime/dsl.py`

- [ ] Add tests proving empty or incomplete records fail, a complete single claim commits, mismatched claims remain observable, and `events=[...]` commits one claim per pending internal transition.
- [ ] Run `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest -q tests/regression/test_single_execution_record.py` and verify the new tests fail for the missing strict behavior.
- [ ] Remove the runtime-truth acknowledgement path from `TraceSession.record`, validate the four required fields, and implement ordered multi-claim handling without changing Atomic behavior.
- [ ] Rerun the focused runtime tests and verify they pass.

### Task 2: Frozen generation contract

**Files:**
- Modify: `tests/regression/test_single_execution_prompt_profiles.py`
- Modify: `algolab/generation/execution_modes.py`
- Modify: `algolab/generation/repair.py`
- Modify: `algolab/generation/solution_generator.py`

- [ ] Add prompt tests rejecting empty acknowledgement examples and requiring full `op/targets/before/after` examples plus profile version `single-execution-pilot-v2`.
- [ ] Run the prompt tests and verify failure against the v1 appendix.
- [ ] Replace the Decoupled appendix with the strict single/multi claim contract and make Decoupled repair guidance explicitly allow only `sess.record(...)` claims to name event fields.
- [ ] Rerun prompt and repair regression tests.

### Task 3: Isolated confirmatory runner

**Files:**
- Modify: `scripts/run_atomic_service_pilot.sh`
- Modify: `tests/regression/test_atomic_service_pilot.py`

- [ ] Add a test or shell assertion that completion requires execution profile v2 and the expected prompt hash.
- [ ] Change the default output directory to `output/experiments/plan3_20260725/atomic_service_manual_claim_pilot` while retaining the frozen 23-case manifest and existing condition names used by the analyzer.
- [ ] Verify runner syntax, manifest cardinality, controlled configuration parity, and the paired analyzer tests.

### Task 4: Verification and interface pretest

**Files:**
- Output only: `output/experiments/plan3_20260725/decoupled_manual_claim_interface_pretest/`

- [ ] Run focused runtime, pipeline, prompt, and pilot-analysis tests.
- [ ] Run the complete `tests/regression` suite and Python syntax checks.
- [ ] Run a small Decoupled LLM pretest only to detect interface defects; do not change hypotheses, case selection, outcomes, or statistical criteria.
- [ ] Freeze the prompt hashes after any interface-only correction and rerun the focused tests.

### Task 5: Formal paired pilot and report

**Files:**
- Output: `output/experiments/plan3_20260725/atomic_service_manual_claim_pilot/`
- Modify: `docs/35_ATOMIC_SERVICE_PILOT_EXPERIMENT.md`
- Output: `deliverables/plan3_experiments_1_3_pilot_20260725.tar.gz`

- [ ] Generate both 23-case conditions concurrently in the new directory.
- [ ] Run both browser machine audits and the frozen paired analysis.
- [ ] Verify 23 complete pairs, config parity, token accounting, mechanism observability, Holm adjustment, and artifact checksums.
- [ ] Report the observed direction without relabeling failures or changing the primary metric; start no Full-200 unless the frozen positive criterion is met.
- [ ] Update the concise result report and rebuild the formal artifact archive, excluding all pretests.
