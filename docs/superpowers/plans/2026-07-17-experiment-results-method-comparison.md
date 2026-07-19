# Experiment Results Method Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `docs/EXPERIMENT_RESULTS.md` around a clear five-method comparison with unified metrics, while retaining cost, robustness, mechanism, teaching/visual, limitation, and evidence sections without duplicated headline numbers.

**Architecture:** The document becomes a method-first results ledger. Frozen JSON reports remain the source of truth; the Markdown presents one method catalog, two full-200 scoreboards, concise method-level interpretation, and progressively deeper evidence sections. Ablations and sensitivity analyses remain separate from the five complete methods.

**Tech Stack:** Markdown, frozen JSON experiment reports, Python 3.10 JSON inspection, ripgrep, Git diff validation.

---

### Task 1: Freeze the five-method metric matrix

**Files:**
- Read: `docs/EXPERIMENT_RESULTS.md`
- Read: `latex/evidence-ledger.md`
- Read: `output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine/interaction_semantic_eval_report.json`
- Read: `output/external_baselines/webgen/audit_all200_sample0/report.json`
- Read: `output/external_baselines/htmlcure_all200_sample0/behavior_audit/interaction_semantic_eval_report.json`
- Read: `output/experiments/algotutorgen_plan_completion_20260713/direct_browser_repair_5/budget_curve_report.json`

- [ ] **Step 1: Inspect each report schema and locate the nine Machine OK component counts**

Run a Python JSON inspection over the four report files. Expected: every file parses and exposes either a summary or per-case rows from which fixed 200-task counts can be derived.

- [ ] **Step 2: Recompute the BrowserRepair 1-call row**

Use only the fixed 1-call condition and the exact booleans `page_load_ok`, `visible_answer_match`, `interaction_reachable`, `correct_feedback_ok`, `wrong_feedback_ok`, `hint_ok`, `show_answer_ok`, `learning_log_ok`, `mutation_free`, and `machine_ok`. Never select a different repair call per case.

- [ ] **Step 3: Cross-check the four frozen rows**

Expected values:

```text
AlgoTutorGen: Load 200, Answer 200, Interaction 200, Correct 199, Wrong 198,
Hint 200, Show 200, Log 200, Mutation-free 200, Machine OK 198.
Direct HTML: Load 188, Answer 200, Interaction 149, Correct 120, Wrong 125,
Hint 132, Show 133, Log 135, Mutation-free 149, Machine OK 98.
WebGen-Agent: Load 194, Answer 169, Interaction 154, Correct 74, Wrong 89,
Hint 136, Show 148, Log 109, Mutation-free 154, Machine OK 45.
HTMLCure strict: Load 75, Answer 75, Interaction 62, Correct 52, Wrong 51,
Hint 53, Show 53, Log 59, Mutation-free 62, Machine OK 40.
```

Resolve any conflict in favor of the newest machine-readable report and record the discrepancy in the Markdown.

### Task 2: Replace the opening with method-first scoreboards

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md:1-70`

- [ ] **Step 1: Write the reading guide and metric contract**

State that the main comparison uses 200 tasks, 23 families, sample index 0; Machine OK is the conjunction of nine browser checks; teaching quality, visual preference, and learning gains are outside Machine OK.

- [ ] **Step 2: Add the method catalog**

Create this schema:

```text
Method | Generation path | Browser/agent feedback | Runtime strategy | Main comparison role
```

Rows: AlgoTutorGen, Direct HTML, WebGen-Agent, Direct + HTMLCure, Direct + BrowserRepair (1-call).

- [ ] **Step 3: Add two scoreboards**

Table A:

```text
Method | Load | Answer | Interaction | Machine OK
```

Table B:

```text
Method | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free
```

Format every value as `count/200 (percentage)` and bold only the best complete-method value in each column.

- [ ] **Step 4: Add one concise interpretation bullet per method**

Each bullet identifies the main contract-loss location without repeating every table cell.

### Task 3: Reorder the remaining evidence and remove duplication

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] **Step 1: Put repair and cost evidence after the main comparison**

Keep Stage1 versus Direct call/token cost, the BrowserRepair fixed-budget curve, HTMLCure strict versus blocked-external sensitivity, and the Local Resume versus Global Restart negative result. Treat BrowserRepair 2/3/5-call rows as a budget study, not separate methods.

- [ ] **Step 2: Group robustness evidence**

Place the 646-input replay, cross-model fixed-budget comparison, held-out 40-task comparison, and long-trace scalability in one section.

- [ ] **Step 3: Group mechanism evidence**

Place nested contract survival, the two non-degenerate ablations, 55,108-frame semantic preservation, mutation discrimination, and noninterference stress testing in one section.

- [ ] **Step 4: Keep teaching and visual evidence secondary**

Retain Naps, TRAKLA2-style, LORI/MERLOT, judge robustness, and Stage2 VLM under a heading that explicitly excludes correctness and student-learning claims.

- [ ] **Step 5: Delete repeated headline tables and prose**

Remove the duplicate nine-metric lookup table. Replace it with a pointer to the two main scoreboards while preserving unique family splits, statistical tests, caveats, and artifact paths.

### Task 4: Verify the rewritten results ledger

**Files:**
- Verify: `docs/EXPERIMENT_RESULTS.md`
- Verify: `latex/evidence-ledger.md`

- [ ] **Step 1: Check section order and method coverage**

Run `rg -n '^## |^### |AlgoTutorGen|Direct HTML|WebGen-Agent|HTMLCure|BrowserRepair' docs/EXPERIMENT_RESULTS.md`.

Expected: all five methods appear in the catalog and both scoreboards; ablations appear only in the mechanism section.

- [ ] **Step 2: Check frozen headline numbers**

Use Python assertions to verify that the Markdown main scoreboard contains Machine OK values `198/200`, `98/200`, `45/200`, `40/200`, and the recomputed BrowserRepair 1-call value.

- [ ] **Step 3: Check evidence paths**

Extract inline paths beginning with `output/`, `benchmark/`, or `latex/` and assert that every referenced path exists.

- [ ] **Step 4: Run repository checks**

```bash
git diff --check
python3 scripts/run_quality_checks.py
python3 -m pytest tests/regression/*.py -q
```

Expected: diff check exits 0, quality checks print `PASS`, and the explicit regression suite reports 107 passed.

- [ ] **Step 5: Review the final diff**

Review only `docs/EXPERIMENT_RESULTS.md` and this plan. Expected: organization and wording change while frozen claims remain numerically consistent.
