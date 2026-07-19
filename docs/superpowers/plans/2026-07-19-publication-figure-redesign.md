# Publication Figure Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce three visually rich, scientifically exact, editable SVG figures and paper-ready PNG exports.

**Architecture:** Use AutoFigure-Edit's GPTImage2 path for visual reference generation, then create deterministic SVGs with reusable semantic icon groups and live text. Validate and rasterize through AutoFigure-Edit's own SVG helpers so exact labels and topology do not depend on image-model typography.

**Tech Stack:** Python 3.10, SVG/XML, AutoFigure-Edit `autofigure2.py`, CairoSVG, Pillow, LaTeX.

---

### Task 1: Strengthen the three visual prompts

**Files:**
- Modify: `latex/figure-generation/prompts/method-paradigm-comparison.txt`
- Modify: `latex/figure-generation/prompts/system-detailed-architecture.txt`
- Modify: `latex/figure-generation/prompts/dataset-overview.txt`

- [ ] Add functional robot roles, richer semantic icons, and dense AutoFigure-style visual storytelling.
- [ ] Preserve every exact label, number, evidence boundary, and forbidden-quality-symbol constraint.
- [ ] Run a prompt scan to ensure required labels remain present exactly once in the specification.

### Task 2: Generate richer GPTImage2 visual references

**Files:**
- Create: `latex/figure-generation/work/method-paradigm-comparison-rich-reference.png`
- Create: `latex/figure-generation/work/system-detailed-architecture-rich-reference.png`
- Create: `latex/figure-generation/work/dataset-overview-rich-reference.png`

- [ ] Invoke AutoFigure-Edit's native OpenAI Images implementation with the project API settings and `gpt-image-2`.
- [ ] Generate at 2:1 or 2.1:1 landscape dimensions without overwriting existing figures.
- [ ] Inspect each reference for robot semantics, icon richness, topology, and scientific content.

### Task 3: Build reusable deterministic SVG primitives

**Files:**
- Create: `latex/figure-generation/build_publication_figures.py`

- [ ] Implement SVG helpers for cards, text, arrows, dashed paths, browser windows, document stacks, robots, shields, contract diamonds, traces, scene graphs, and task folders.
- [ ] Keep all text as SVG `<text>` and all icons as editable vector groups with stable IDs.
- [ ] Add assertions for viewBox dimensions, unique IDs, and required labels.

### Task 4: Construct the method comparison SVG

**Files:**
- Create: `latex/figures/method-paradigm-comparison-v2.svg`
- Create: `latex/figures/method-paradigm-comparison-v2.png`

- [ ] Implement the three aligned islands with functional robots and richer semantic artifacts.
- [ ] Ensure the red audit loop targets the whole Direct HTML browser and the AlgoTutorGen loop targets only `Spec`.
- [ ] Validate and rasterize through AutoFigure-Edit.

### Task 5: Construct the detailed architecture SVG

**Files:**
- Create: `latex/figures/system-detailed-architecture-v2.svg`
- Create: `latex/figures/system-detailed-architecture-v2.png`

- [ ] Implement the exact canonical pipeline, validation rail, pedagogical lane, and repair arc.
- [ ] Assert that the pedagogical path starts at `Validated SceneGraph`, enters `Read-only facts`, then `Overlay sanitizer`, then `Teaching enrichment`, and reconnects only to `Browser Artifact`.
- [ ] Validate and rasterize through AutoFigure-Edit.

### Task 6: Construct the dataset overview SVG

**Files:**
- Create: `latex/figures/dataset-overview-v1.svg`
- Create: `latex/figures/dataset-overview-v1.png`

- [ ] Implement the scale, coverage, and task-bundle sections with one functional curator robot.
- [ ] Assert all eleven numeric values against `benchmark/algo_learn_env_benchmark.json` and `benchmark/heldout_cases_v1.json`.
- [ ] Validate and rasterize through AutoFigure-Edit.

### Task 7: Verify visual and LaTeX integration

**Files:**
- Modify: `latex/main.tex`

- [ ] Add or replace figure environments using the selected versioned PNGs without deleting the source SVGs.
- [ ] Compile `main.tex` with the repository's existing build command.
- [ ] Inspect the PDF for clipping, unreadable text, incorrect labels, connector crossings, and excessive figure height.
- [ ] Record exact generated paths and verification results.
