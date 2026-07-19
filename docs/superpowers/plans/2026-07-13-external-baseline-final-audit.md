# External Baseline Final Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete a final literature and reproducibility audit of external baselines, run every fair and locally reproducible missing comparison, and document why excluded systems cannot enter the full-200 table.

**Architecture:** Preserve the frozen 200-case generative main table and evaluate human-authored or general-purpose visualization systems only on explicitly matched scopes. Freeze upstream commits and licenses, keep raw smoke-test evidence under a separate external-baseline output tree, and classify every candidate by task alignment, artifact generation, input controllability, batchability, and tutoring-contract coverage.

**Tech Stack:** Git, Node.js/npm, Python 3.10, Playwright/browser automation, JSON/Markdown reports, Crossref/arXiv metadata APIs.

---

### Task 1: Freeze Candidate Systems and Comparison Rules

**Files:**
- Create: `output/external_baselines/traditional_systems/candidate_registry.json`
- Create: `docs/EXPERIMENT_RESULTS.md`

- [ ] Record repository URL, inspected commit, license, release state, accepted input, generated artifact, browser availability, and batchability for Algorithm Visualizer, Python Tutor, OpenDSA/JSAV, VisualCodeMOOC, VisuAlgo, EduVisAgent, WebGen-Agent, and HTMLCure.
- [ ] State the inclusion rule for the 200-case table: the system must accept arbitrary unseen benchmark tasks and emit a browser-auditable teaching artifact without human-authored per-algorithm adapters.
- [ ] State the exact-overlap rule: fixed-template systems may be compared only on algorithms and inputs their official artifacts actually support, using common visualization metrics rather than tutoring-specific Machine OK.
- [ ] Store raw Git and repository evidence paths so every registry field is traceable.

### Task 2: Search Recent Literature and Public Implementations

**Files:**
- Create: `output/external_baselines/traditional_systems/literature_search.json`
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] Query arXiv and Crossref for 2024-2026 work on automatic algorithm visualization generation, LLM algorithm tutoring visualization, code visualization agents, and interactive algorithm-learning environment generation.
- [ ] Resolve each potentially relevant result to an official paper and public implementation when available.
- [ ] Classify each result as full-task executable baseline, overlap-only system, related work with non-browser output, or unavailable/non-reproducible system.
- [ ] Preserve query strings, retrieval date, identifiers, URLs, and exclusion reasons in machine-readable form.

### Task 3: Reproduce Algorithm Visualizer

**Files:**
- Create: `output/external_baselines/traditional_systems/algorithm_visualizer/reproducibility.json`
- Create: `output/external_baselines/traditional_systems/algorithm_visualizer/smoke_report.json`
- Create: `output/external_baselines/traditional_systems/algorithm_visualizer/exact_overlap_manifest.json`
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] Inspect the official web, algorithms, tracer, and server contracts and freeze all required commits and licenses.
- [ ] Build or run the official stack with a compatible Node version without modifying algorithm semantics.
- [ ] Smoke-test at least one sorting case and one graph/string case, verifying page load, play/step/reset controls, visible algorithm state, code synchronization, and completion.
- [ ] Map benchmark cases only where the official algorithm implementation is an exact semantic match; record whether the benchmark sample input can be injected into the unmodified official implementation.
- [ ] If the stack or input injection is not reproducible, capture the exact failure and stop before producing an invalid numeric comparison.

### Task 4: Reproduce Current Python Tutor

**Files:**
- Create: `output/external_baselines/traditional_systems/python_tutor/reproducibility.json`
- Create: `output/external_baselines/traditional_systems/python_tutor/smoke_report.json`
- Create: `output/external_baselines/traditional_systems/python_tutor/exact_overlap_manifest.json`
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] Clone the current official `pgbovine/OnlinePythonTutor` repository and freeze its commit and license.
- [ ] Verify Python 3 trace generation using a benchmark solver and sample input, including deterministic final output and a non-empty execution trace.
- [ ] Run the official embeddable or local browser frontend when available and verify page load, forward/back stepping, variable/state visibility, code-line synchronization, and final output.
- [ ] Build an exact-overlap manifest only for benchmark solvers supported by the frozen trace generator and bounded trace length.
- [ ] If the current browser frontend is not independently deployable from the public repository, retain trace-level evidence and report the frontend reproducibility boundary instead of inventing a replacement UI.

### Task 5: Run the Fair Overlap Study or Establish Boundaries

**Files:**
- Create: `output/external_baselines/traditional_systems/overlap_study_summary.json`
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] Run common browser metrics on every system that passed Tasks 3-4: load, step/play availability, reset/back navigation, visible execution state, code synchronization, final-result visibility, input controllability, and external-resource dependence.
- [ ] Report denominators separately for each system and never impute unsupported algorithms as failures.
- [ ] Keep hint, answer submission, bidirectional feedback, show-answer, and learning-log metrics descriptive because traditional visualizers do not claim the full tutoring contract.
- [ ] If neither system supports a stable official browser run with paired benchmark inputs, publish a reproducibility-boundary table and omit numeric quality rankings.

### Task 6: Update Paper-Facing External Baseline Summary

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] Add the final candidate census and explain why no additional system qualifies for the 200-case generative main table unless Task 2 identifies one.
- [ ] Add any valid overlap-study results in a separate table with its own denominator and capability scope.
- [ ] Preserve AlgoTutorGen, Direct HTML, WebGen-Agent, and HTMLCure numbers exactly as frozen.
- [ ] State remaining limitations, including template/manual-authoring advantage, differing inputs, unavailable services, and frontend deployment boundaries.

### Task 7: Verify Evidence and Report Consistency

**Files:**
- Verify: `output/external_baselines/traditional_systems/**/*.json`
- Verify: `docs/EXPERIMENT_RESULTS.md`
- Verify: `docs/EXPERIMENT_RESULTS.md`

- [ ] Parse every new JSON artifact and reject duplicate candidate IDs or case IDs.
- [ ] Check all recorded local evidence paths and inspected commit hashes.
- [ ] Run syntax/build/smoke commands used by reproducible systems again and record exit status.
- [ ] Cross-check every numerator, denominator, commit, license, and exclusion claim against primary evidence before reporting completion.
