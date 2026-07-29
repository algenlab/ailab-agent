# Plan2 Experiments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. This repository already contains in-progress uncommitted RED tests, so execution continues in place and does not commit or push.

**Goal:** Complete every automatable experiment in `plan/plan2.md`, preserve human-label boundaries, and produce protocol-audited final results and documentation.

**Architecture:** Treat each experiment as a frozen, restart-safe pipeline with explicit inputs, protocol metadata, release gates, raw outputs, and a deterministic analyzer. P0-2 pairs two prompt profiles on identical frozen payloads; P0-3 uses Docker Playwright for browser evidence; P0-4 and P1 prepare non-destructive human annotation packages and only compute human statistics when real labels exist.

**Tech Stack:** Python 3.10 (`/ssd1/liaokunpeng/agent-py310-cu/bin/python3`), pytest, Bash, Docker Playwright, JSON/CSV, OpenAI-compatible API.

---

### Task 1: Freeze and enforce the P0-2 paired protocol

**Files:**
- Modify: `llm_client.py`
- Modify: `algolab/generation/repair.py`
- Modify: `algolab/generation/solution_generator.py`
- Modify: `algolab/generation/prompt_profiles.py`
- Modify: `algolab/pipeline.py`
- Modify: `scripts/run_llm_benchmark.py`
- Modify: `scripts/run_plan2_prompt_ablation.sh`
- Test: `tests/regression/test_llm_client_retry_budget.py`
- Test: `tests/regression/test_plan2_prompt_profiles.py`

- [ ] Record every JSON attempt with `json_attempt` and `json_valid`, retain the requested variant budget in retry prompts, and expose initial specification validity independently of candidate selection.
- [ ] Remove `strategy_hint` only for `service_only`, bump prompt metadata to v2, and record the policy in the frozen profile metadata.
- [ ] Require exactly two valid variants at the generation/release boundary and in report protocol validation.
- [ ] Classify 401/403 as configuration failures and keep infrastructure failures separate from method failures.
- [ ] Inject `benchmark/algo_learn_env_benchmark.json` through `--case-overrides` for both pilot and Full-200, and validate problem/input/expected payload equality before accepting a report.
- [ ] Run:

```bash
export TMPDIR=/ssd1/liaokunpeng/.tmp
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest -q \
  tests/regression/test_llm_client_retry_budget.py \
  tests/regression/test_plan2_prompt_profiles.py
```

Expected: all tests pass with zero failures.

### Task 2: Make P0-2 paired statistics fail closed

**Files:**
- Modify: `scripts/analyze_plan2_prompt_ablation.py`
- Test: `tests/regression/test_plan2_prompt_statistics.py`

- [ ] Reject controlled-configuration, paired-payload, case-set, machine-record, or infrastructure contamination before computing statistics.
- [ ] Hash the canonical paired payload and report `paired_payload_sha256`.
- [ ] Use explicit `first_pass_specification_valid` rather than the final selection label.
- [ ] Count unknown DSL calls across all candidate attempts, including repaired and failed candidates.
- [ ] Preserve paired bootstrap, exact McNemar, Holm correction, and the −3 percentage-point non-inferiority rule.
- [ ] Run:

```bash
export TMPDIR=/ssd1/liaokunpeng/.tmp
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest -q \
  tests/regression/test_plan2_prompt_statistics.py
```

Expected: all tests pass with zero failures.

### Task 3: Audit P0-3 across every frame and content dimension

**Files:**
- Modify: `tests/regression/test_plan2_shell_ownership.py`
- Modify: `scripts/audit_plan2_shell_ownership.py`
- Modify: `scripts/run_plan2_prompt_machine_audits.sh` if shared Docker invocation needs alignment

- [ ] Add failing tests proving all frames are traversed, content hashes are compared, creative-stage parsing cannot hide shell differences, and dimension totals are counted once.
- [ ] Parse DOM using `html5lib`, exclude only the `creative-stage-host` subtree, and compare text/content for code panel, timeline, explanation, interaction, feedback, answer, learning log, and canonical artifact state.
- [ ] Execute all five fault-injection categories on 20 selected artifacts and report reject-or-safe-fallback outcomes.
- [ ] Run:

```bash
export TMPDIR=/ssd1/liaokunpeng/.tmp
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest -q \
  tests/regression/test_plan2_shell_ownership.py
bash scripts/run_browser_smoke_container.sh
```

Expected: regression tests and Docker browser verification pass.

### Task 4: Preserve and analyze real P0-4/P1 human labels

**Files:**
- Modify: `tests/regression/test_plan2_source_trace_audit.py`
- Modify: `scripts/audit_plan2_source_trace.py`
- Modify: `tests/regression/test_plan2_visual_human_calibration.py`
- Modify: `scripts/plan2_visual_human_calibration.py`

- [ ] Add failing tests for non-destructive reruns: existing non-empty labels and blinding keys must be preserved or preparation must refuse to overwrite them.
- [ ] Compute P0-4 human exact+adjacent accuracy with 95% CI, critical-error rate, and inter-rater agreement only when complete real labels are present.
- [ ] Keep P1 at `pending_human_labels` unless real reviewer scores exist; when complete, compute human–VLM correlation, All≥3 agreement, paired preferences, and inter-rater agreement.
- [ ] Run:

```bash
export TMPDIR=/ssd1/liaokunpeng/.tmp
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest -q \
  tests/regression/test_plan2_source_trace_audit.py \
  tests/regression/test_plan2_visual_human_calibration.py
```

Expected: tests pass; preparation is idempotent and no label is synthesized.

### Task 5: Verify all deterministic Plan2 tooling

**Files:**
- Test: `tests/regression/test_plan2_*.py`
- Test: `tests/regression/test_llm_client_retry_budget.py`

- [ ] Run all Plan2 regression tests, Python compilation, and the repository quality checks.
- [ ] Run Docker Playwright rather than host Playwright.
- [ ] Inspect generated schemas and counts before any paid API run.

```bash
export TMPDIR=/ssd1/liaokunpeng/.tmp
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest -q \
  tests/regression/test_plan2_*.py \
  tests/regression/test_llm_client_retry_budget.py
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

Expected: zero regression failures and zero quality-check failures.

### Task 6: Run the paired P0-2 API experiment

**Files:**
- Output: `output/experiments/plan2_20260722/p0_2_prompt_ablation/pilot/`
- Output: `output/experiments/plan2_20260722/p0_2_prompt_ablation/full200/`

- [ ] Start a fresh 60-case stratified pilot for `hybrid_current` and `service_only`, eight workers per profile, total API concurrency 16.
- [ ] Audit profile hashes, exact frozen payloads, exactly two variants, failure taxonomy, case completeness, and paired machine outputs.
- [ ] If the pilot protocol passes, run Full-200 under the identical locked protocol.
- [ ] Generate service-composition audits, Docker machine audits, and paired statistics for both modes.

```bash
bash scripts/run_plan2_prompt_ablation.sh pilot
bash scripts/run_plan2_prompt_machine_audits.sh pilot
bash scripts/run_plan2_prompt_ablation.sh full200
bash scripts/run_plan2_prompt_machine_audits.sh full200
```

Expected: both profiles contain the same 60/200 case IDs and payload hashes; no infrastructure contamination is accepted.

### Task 7: Regenerate P0-1, P0-3, P0-4, and P1 outputs

**Files:**
- Output: `output/experiments/plan2_20260722/p0_1_service_composition/`
- Output: `output/experiments/plan2_20260722/p0_3_shell_ownership/`
- Output: `output/experiments/plan2_20260722/p0_4_source_trace/`
- Output: `output/experiments/plan2_20260722/p1_visual_human_calibration/`

- [ ] Re-run P0-1 against the final frozen 200 selected artifacts.
- [ ] Run the corrected P0-3 browser audit in Docker over all frame/state pairs and the 20×5 fault injections.
- [ ] Re-run P0-4 automatic analysis and non-destructive 40-case/80-variant human package preparation.
- [ ] Re-run P1 non-destructive 30×5 blinded-page preparation; retain `pending_human_labels` if labels are absent.
- [ ] Validate required JSON/CSV files and all denominators against Plan2.

### Task 8: Document final evidence and limits

**Files:**
- Create: `docs/PLAN2_EXPERIMENT_RESULTS.md`
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] Put direct result tables first, define unclear metrics at first use, and separate automated results from pending human calibration.
- [ ] Record final protocol, sample sizes, exact result paths, statistical decisions, and claim boundaries without narrating obsolete experimental evolution.
- [ ] Add only a concise link/summary to the main experiment document.
- [ ] Re-run the full verification command and inspect `git diff` without committing or pushing.
