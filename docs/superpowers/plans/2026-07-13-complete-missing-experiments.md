# Complete Missing Experiments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the missing full-200 ablations, statistical analysis, gate-soundness evaluation, 646-sample replay, and judge-robustness experiments without overwriting frozen main-experiment artifacts.

**Architecture:** Reuse the frozen `algolab_full_final` artifacts and existing browser/LLM evaluation functions wherever possible. Deterministic derived conditions are written under `output/experiments/algotutorgen_completion_20260713`; browser work is shardable and resumable, while LLM judge work uses per-case cache files. A final machine-readable summary records input hashes, coverage, results, and claim boundaries.

**Tech Stack:** Python 3.10, Pydantic, Playwright container runner, SciPy/NumPy, OpenAI-compatible API, pytest, JSON/Markdown reports.

---

### Task 1: Freeze Experiment Inputs

**Files:**
- Create: `output/experiments/algotutorgen_completion_20260713/frozen_inputs.json`
- Create: `scripts/freeze_completion_experiment_inputs.py`
- Test: `tests/regression/experiment_completion.py`

- [ ] Add a test that verifies the freezer records SHA-256 hashes, 200 unique case IDs, 23 families, and all required source reports.
- [ ] Implement the freezer using the final Stage1, Direct, machine, external-review, Stage2, visual-baseline, and benchmark files.
- [ ] Run `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest tests/regression/experiment_completion.py -v` and require PASS.
- [ ] Generate `frozen_inputs.json` and verify every referenced path exists.

### Task 2: Build Paired Full-200 Ablation Conditions

**Files:**
- Create: `scripts/build_full200_ablation_conditions.py`
- Modify: `scripts/run_interaction_semantic_eval.py`
- Test: `tests/regression/experiment_completion.py`

- [ ] Add tests for `--algolab-only`, output condition relabeling, source-row preservation, and no-repair failure-row construction.
- [ ] Add `--algolab-only` and `--algolab-condition` to the browser evaluator without changing existing defaults.
- [ ] Build `full`, `no_teaching`, `no_interaction`, and `no_teaching_interaction` HTML/JSON from the same 200 final artifacts.
- [ ] Build a paired no-repair report from the 195 primary artifacts plus five explicit generation-failure rows, verifying the 195 retained artifact hashes match the final merged report.
- [ ] Build a paired no-SceneGraph trace-only report from the saved materialized traces, without new model calls.
- [ ] Run focused pytest and Python compilation checks.

### Task 3: Run Full-200 Browser Ablation Audits

**Files:**
- Create: `scripts/run_full200_ablation_audits.sh`
- Output: `output/experiments/algotutorgen_completion_20260713/ablation_audits/**`

- [ ] Run eight shards for each derived browser condition using the existing Playwright container.
- [ ] Merge shards with `scripts/merge_interaction_semantic_reports.py`.
- [ ] Verify exactly 200 unique records per condition and no duplicate case IDs.
- [ ] Reuse the frozen full-condition machine report and derived no-repair records rather than rerunning unchanged pages.

### Task 4: Expand Gate Fault Injection

**Files:**
- Modify: `scripts/run_gate_fault_injection.py`
- Test: `tests/regression/experiment_completion.py`
- Output: `output/experiments/algotutorgen_completion_20260713/fault_injection/**`

- [ ] Add clean controls and faults for event deletion, event reordering, state mutation, interaction-answer mutation, invalid target/reference, and stored SceneGraph corruption.
- [ ] Record both false-accept rate for injected artifacts and false-reject rate for clean controls.
- [ ] Run all supported faults across 200 final artifacts.
- [ ] Report rejection by fault type, family, and responsible validation layer.

### Task 5: Replay All 646 Benchmark Samples

**Files:**
- Create: `scripts/run_cross_input_replay.py`
- Modify: `scripts/replay_llm_specs.py`
- Test: `tests/regression/experiment_completion.py`
- Output: `output/experiments/algotutorgen_completion_20260713/cross_input_replay/**`

- [ ] Add an in-memory replay API with solve, trace, process, demo, and scene stage statuses.
- [ ] Map each final artifact to its benchmark case and replay its generated code/tracker on all 646 samples.
- [ ] Use bounded concurrency and deterministic row ordering.
- [ ] Report overall, sample-index, family, gate-layer, and boundary-category results.
- [ ] Verify 646 unique `(case_id, sample_index)` rows and 200 unique cases.

### Task 6: Compute Paired Statistics

**Files:**
- Create: `scripts/analyze_paired_experiments.py`
- Test: `tests/regression/experiment_completion.py`
- Output: `output/experiments/algotutorgen_completion_20260713/statistics/**`

- [ ] Add exact McNemar tests and seeded paired-bootstrap confidence intervals for all shared boolean metrics.
- [ ] Add paired Wilcoxon tests, Holm correction, and matched-pairs rank-biserial effect sizes for visual and LORI/MERLOT scores.
- [ ] Include pair completeness checks and fail on missing/duplicate IDs.
- [ ] Generate JSON, Markdown, and CSV tables.

### Task 7: Run Judge Robustness Matrix

**Files:**
- Modify: `scripts/run_external_eval_methods.py`
- Create: `scripts/analyze_judge_robustness.py`
- Test: `tests/regression/experiment_completion.py`
- Output: `output/experiments/algotutorgen_completion_20260713/judge_robustness/**`

- [ ] Add a blind-order mode that supports the frozen hash order and its exact A/B swap.
- [ ] Run full-200 DeepSeek-V4-Pro swapped-order review.
- [ ] Run full-200 Gemini-3-Flash-Preview reviews in frozen and swapped orders.
- [ ] Report winner agreement, Cohen's kappa, score Spearman correlations, order-flip rate, and model disagreement cases.
- [ ] Verify 200 valid cached responses for every matrix cell.

### Task 8: Final Verification and Paper Report

**Files:**
- Create: `docs/EXPERIMENT_RESULTS.md`
- Modify: `docs/EXPERIMENT_RESULTS.md`
- Modify: `docs/EXPERIMENT_RESULTS.md`
- Create: `output/experiments/algotutorgen_completion_20260713/completion_summary.json`

- [ ] Run Python compilation, focused pytest, shell syntax checks, and JSON completeness checks.
- [ ] Summarize every new experiment with exact numerator/denominator, cost, statistical test, and claim boundary.
- [ ] Update the paper report only where new evidence changes or strengthens an existing statement.
- [ ] Record failures and limitations explicitly; do not convert missing evidence into a positive claim.
