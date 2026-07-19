# Method Artifact Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a deterministic GitHub-browsable gallery containing one representative case from each of the 23 benchmark families for all five evaluated methods.

**Architecture:** A standalone Python builder reads the frozen benchmark, five-method machine-audit records, multimodal review summaries, HTML artifacts, screenshots, and WebGen workspaces. It copies a sanitized subset into a case-centric generated directory and emits JSON/Markdown indexes. A regression test validates both the builder contract and the generated tree.

**Tech Stack:** Python 3.10 standard library, existing benchmark JSON, existing `scripts.run_all_method_auxiliary_eval` record loader, pytest-style regression functions, Markdown, JSON.

---

### Task 1: Define the gallery contract with a failing test

**Files:**
- Create: `tests/regression/method_artifact_gallery.py`
- Test: `tests/regression/method_artifact_gallery.py`

- [ ] **Step 1: Write the failing test**

Add tests that import `SELECTED_CASES`, `METHOD_ORDER`, `build_gallery`, and `validate_gallery` from `scripts.build_method_artifact_gallery`. Assert 23 unique families, five methods per case, complete nine-item metrics, sanitized paths, and method-specific file requirements.

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
TMPDIR=/ssd1/liaokunpeng/.tmp /ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest -q tests/regression/method_artifact_gallery.py
```

Expected: collection failure because `scripts.build_method_artifact_gallery` does not exist.

### Task 2: Implement the deterministic builder

**Files:**
- Create: `scripts/build_method_artifact_gallery.py`
- Test: `tests/regression/method_artifact_gallery.py`

- [ ] **Step 1: Implement selection and record loading**

Define the explicit 23-case selection, load existing method records through `build_method_records`, load one multimodal review JSON per method/case, and reject missing or duplicate families.

- [ ] **Step 2: Implement safe copying**

Copy standalone HTML and screenshots with `shutil.copy2`. Copy WebGen workspaces with `shutil.copytree`, excluding `node_modules`, `dist`, `.git`, `.vite`, coverage, and cache directories.

- [ ] **Step 3: Implement sanitized metadata**

Emit `case.json`, method-level `audit.json`, and `manifest.json`. Convert all provenance paths to repository-relative POSIX paths and omit raw model responses and credentials.

- [ ] **Step 4: Implement Markdown indexes**

Generate a root reading guide and one case README with screenshot embeds, artifact links, and a complete nine-metric comparison table.

- [ ] **Step 5: Run the focused test**

Run the same pytest command. Expected: all gallery tests pass.

### Task 3: Generate and inspect the public artifact tree

**Files:**
- Create: `artifacts/method_comparison_samples/**`

- [ ] **Step 1: Generate the gallery**

Run:

```bash
TMPDIR=/ssd1/liaokunpeng/.tmp /ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_method_artifact_gallery.py
```

Expected: a summary reporting 23 cases, 115 method artifacts, and zero validation errors.

- [ ] **Step 2: Inspect size and large-file safety**

Run `du -sh artifacts/method_comparison_samples` and confirm no file is 100 MB or larger.

- [ ] **Step 3: Re-run validation without rebuilding**

Run the builder with `--validate-only`. Expected: PASS with the same counts.

### Task 4: Run project verification and publish

**Files:**
- Modify: `tests/benchmark_regression.py` only if needed to include the new focused test in the lightweight entrypoint.

- [ ] **Step 1: Run gallery and project checks**

Run the focused gallery test, `scripts/run_quality_checks.py`, shell syntax checks, JSON parsing checks, and the explicit active regression suite including the new test.

- [ ] **Step 2: Review Git scope and secrets**

Confirm only the builder, test, design/plan, and generated artifact directory are changed. Scan staged text for credential-shaped values and ensure no ignored API settings are staged.

- [ ] **Step 3: Commit and push**

Commit with `feat: add five-method artifact sample gallery` and push the existing `codex/publish-current-project-20260719` branch.

