# AAAI-27 Supplement Figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execute inline in the current workspace; do not delegate, commit, push, or modify the main paper.

**Goal:** Generate two image2-based publication infographics, integrate them into the anonymous supplement, and verify the resulting PDF end to end.

**Architecture:** Use the built-in image generation tool once per distinct figure, validate the resulting raster assets, and correct any text defects before integration. Add each asset as a full-width `figure*` in `latex/supplement.tex`, preserving the existing UI screenshot and all evidence boundaries.

**Tech Stack:** Built-in image2/image generation, PNG, PDFLaTeX/TinyTeX, Poppler PDF inspection tools, local image inspection, optional Pillow post-processing with `/ssd1/liaokunpeng/agent-py310-cu/bin/python3`.

---

### Task 1: Establish the failing acceptance check and workspace boundary

**Files:**
- Read: `latex/supplement.tex`
- Read: `latex/main.tex`
- Read: `docs/superpowers/specs/2026-07-15-aaai27-supplement-figures-design.md`

- [ ] **Step 1: Verify that the current workspace must be used in place**

Run:

```bash
git status --short -- latex docs/superpowers/specs/2026-07-15-aaai27-supplement-figures-design.md
```

Expected: `latex/` is untracked and contains the user's current paper sources, so a clean worktree would omit required assets. Work in place and preserve unrelated changes.

- [ ] **Step 2: Run the feature acceptance assertion before implementation**

Run:

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -c 'from pathlib import Path; root=Path("/ssd1/liaokunpeng/paper/ailab-agent/latex"); tex=(root/"supplement.tex").read_text(); assets=[root/"figures/method-paradigm-comparison.png",root/"figures/system-detailed-architecture.png"]; assert all(p.is_file() and p.stat().st_size>0 for p in assets), "missing generated figure assets"; assert "fig:method-paradigms" in tex and "fig:detailed-architecture" in tex, "missing LaTeX figure references"'
```

Expected: FAIL with `AssertionError: missing generated figure assets`.

- [ ] **Step 3: Record the main-paper boundary**

Run:

```bash
stat -c '%n | %s bytes | %y' latex/main.tex latex/main.pdf
```

Expected: record the existing timestamps and sizes; they must remain unchanged.

### Task 2: Generate and validate the method-paradigm comparison

**Files:**
- Create: `latex/figures/method-paradigm-comparison.png`

- [ ] **Step 1: Generate the image with the built-in image2 path**

Use one built-in image-generation call with this prompt:

```text
Use case: infographic-diagram
Asset type: full-width academic paper figure
Primary request: Create a publication-quality landscape infographic titled "Three Generation Paradigms for Interactive Algorithm Tutors". Compare three horizontal lanes.
Lane 1 header: "Direct HTML". Show "Problem + Input + Expected Answer" flowing into "One-shot Free-Form HTML", containing intertwined obligations labeled "answer", "trace", "scene", "runtime", "feedback", and "state isolation", followed by "Final Browser Audit" and a muted-red loop labeled "Whole-page rewrite".
Lane 2 header: "Iterative Final-Artifact Repair" with subtitle "WebGen-Agent / HTMLCure-style". Show "Generate HTML" -> "Browser Feedback" -> "Rewrite HTML" as an orange loop. Add "Whole-artifact repair" and make clear that the repaired object remains free-form HTML.
Lane 3 header: "AlgoTutorGen". Show "Executable Spec" -> "C_S" -> "SemanticTrace" -> "C_T" -> "Validated SceneGraph" -> "C_G" -> "Fixed Runtime" -> "C_B" -> "Browser Artifact". Add a purple branch "Sanitized Read-only Facts" -> "C_P" -> "Teaching Overlay" -> browser artifact. Add "Specification-level repair in the current system".
At the bottom add a compact comparison band with exact row labels: "Output space", "Validation granularity", "Repair scope", "Algorithm / teaching state".
Style/medium: flat vector-like scientific infographic rendered as a crisp raster image, white background, restrained academic styling.
Composition/framing: 16:9 landscape, three clearly separated horizontal lanes, generous margins, readable at full paper width.
Color palette: muted red for entanglement, orange for final-artifact repair, navy and teal for algorithmic and validated stages, purple for pedagogy.
Text: render every quoted label verbatim in clear sans-serif typography.
Constraints: no performance numbers, no p-values, no logos, no watermark, no 3D, no gradients, no decorative people, no claim of universal superiority.
Avoid: misspellings, duplicated nodes, invented method names, tiny text, crossed arrows, clipped text.
```

Expected: a wide raster infographic with all three paradigms and no experimental counts.

- [ ] **Step 2: Move the generated asset into the workspace**

Copy the exact output path returned by the image-generation tool to:

```text
/ssd1/liaokunpeng/paper/ailab-agent/latex/figures/method-paradigm-comparison.png
```

Do not overwrite any pre-existing file; the target is new.

- [ ] **Step 3: Inspect the image at original resolution**

Use the local image viewer and compare every visible label against the prompt and design spec.

Expected: no spelling errors, no duplicated/invented labels, no counts, and no universal-ranking implication. If a label is wrong, issue one targeted image edit or apply a deterministic local text correction, then inspect again.

- [ ] **Step 4: Verify the asset is a readable landscape PNG**

Run:

```bash
file latex/figures/method-paradigm-comparison.png
```

and:

```bash
identify latex/figures/method-paradigm-comparison.png
```

If `identify` is unavailable, use Pillow with the required Python interpreter to print format, dimensions, and mode. Expected: PNG, landscape orientation, nonzero dimensions, RGB/RGBA.

### Task 3: Generate and validate the detailed architecture

**Files:**
- Create: `latex/figures/system-detailed-architecture.png`

- [ ] **Step 1: Generate the image with the built-in image2 path**

Use one built-in image-generation call with this prompt:

```text
Use case: scientific-educational
Asset type: full-width detailed system architecture figure for an academic paper
Primary request: Create a publication-quality architecture diagram titled "AlgoTutorGen: Detailed Contract and State Flow".
Inputs at the left: "Problem q", "Concrete Input i", "Expected / Oracle e", "Optional Code / Strategy c".
Main generated stage: "LLM Solver / Specification".
Deterministic main flow: "Sandboxed Materialization" -> "TraceSession DSL" -> "SemanticTrace" -> "SceneGraph Compiler" -> "Validated SceneGraph" -> "Fixed Web Runtime" -> "Self-contained Browser Artifact".
Place validation gates beside the appropriate boundaries with exact labels: "Result / Oracle Check", "Trace Schema Check", "Process Continuity Check", "Scene Reference Check", "Projection Agreement Check", and "9-check Browser Release Audit".
Teaching branch: from "Sanitized Read-only Facts" through "Overlay Sanitizer" to "LLM Teaching Enrichment", then into the browser artifact. Label the branch "Mutable pedagogical state".
Main solid blue flow label: "Canonical algorithmic state".
Repair path: a red "Browser failure signal" returns to "Repair Current Specification" and then to "LLM Solver / Specification".
Add exact boundary notes: "Materialization and teaching are recomputed after repair." and "Implemented: specification-level repair; not fully checkpointed stage-local recovery."
Style/medium: flat vector-like scientific architecture infographic rendered as a crisp raster image, white background, clean cards and contract badges.
Composition/framing: 16:9 landscape, left-to-right primary pipeline with a clearly separated lower teaching lane and a visible red repair loop.
Color palette: navy/blue for canonical algorithmic state, teal for deterministic validated components, purple dashed flow for pedagogy, muted red for failure/repair.
Text: render every quoted label verbatim in clear sans-serif typography.
Constraints: no performance numbers, no theorem/proof badges, no human-study claims, no logos, no watermark, no 3D, no gradients.
Avoid: misspelled technical terms, implying independent per-stage retry, crossed connectors, clipped labels, tiny text.
```

Expected: a detailed architecture diagram that accurately shows components, validators, two state flows, and the real specification-level repair boundary.

- [ ] **Step 2: Move the generated asset into the workspace**

Copy the exact output path returned by the image-generation tool to:

```text
/ssd1/liaokunpeng/paper/ailab-agent/latex/figures/system-detailed-architecture.png
```

- [ ] **Step 3: Inspect and correct exact labels**

Use the local image viewer at original resolution. Compare all labels against the design spec. Correct any image-generation text error before integration.

- [ ] **Step 4: Verify format and dimensions**

Run the same PNG/landscape checks as Task 2. Expected: readable high-resolution landscape PNG.

### Task 4: Integrate both figures into the supplement

**Files:**
- Modify: `latex/supplement.tex`

- [ ] **Step 1: Add the method-paradigm overview after the reading guide**

Insert:

```latex
\begin{figure*}[t]
\centering
\includegraphics[width=\textwidth]{figures/method-paradigm-comparison.png}
\caption{Comparison of three synthesis-and-repair paradigms for interactive algorithm tutors. Direct HTML places heterogeneous obligations in one free-form artifact; task-adapted final-artifact generation and repair paths, including the evaluated WebGen-Agent and HTMLCure configurations, add browser feedback but still rewrite free-form HTML; \system{} instead validates explicit representations and separates algorithmic from pedagogical state. The diagram compares output structure, validation granularity, repair scope, and state separation, not universal system quality; exact protocol-specific reliability counts remain in the tables.}
\label{fig:method-paradigms}
\end{figure*}
\FloatBarrier
```

- [ ] **Step 2: Add the detailed architecture after the protocol section**

Insert:

```latex
\begin{figure*}[t]
\centering
\includegraphics[width=\textwidth]{figures/system-detailed-architecture.png}
\caption{Detailed \system{} implementation architecture. Solid blue flow carries canonical algorithmic state through sandboxed materialization, typed trace construction, scene compilation, the fixed runtime, and the browser audit. Dashed purple flow carries sanitized read-only facts into mutable pedagogical state. Contract checks reject invalid representations at explicit boundaries. The red loop is the implemented recovery boundary: the current specification is repaired, after which materialization and teaching are recomputed; it is not fully checkpointed stage-local recovery.}
\label{fig:detailed-architecture}
\end{figure*}
\FloatBarrier
```

- [ ] **Step 3: Run the acceptance assertion again**

Run the Task 1 assertion.

Expected: PASS with exit code 0.

- [ ] **Step 4: Confirm no main-paper changes**

Run the Task 1 `stat` command and compare with the recorded values.

Expected: `main.tex` and `main.pdf` timestamps and sizes are unchanged.

### Task 5: Build, audit, and visually inspect the expanded supplement

**Files:**
- Generate: `latex/supplement.pdf`
- Inspect then remove: `latex/supplement.aux`, `latex/supplement.log`

- [ ] **Step 1: Remove supplement auxiliaries**

Run:

```bash
rm -f supplement.aux supplement.log supplement.out supplement.toc supplement.fdb_latexmk supplement.fls supplement.synctex.gz
```

- [ ] **Step 2: Compile twice with TinyTeX**

Run twice:

```bash
/ssd1/liaokunpeng/.TinyTeX/bin/x86_64-linux/pdflatex -interaction=nonstopmode -halt-on-error supplement.tex
```

Expected: both runs exit 0; second run has no undefined references.

- [ ] **Step 3: Audit the second-pass log and PDF**

Check for LaTeX/package warnings, overfull boxes, undefined references, Letter page size, embedded non-Type-3 fonts, anonymous metadata, JavaScript, links, bookmarks, attachments, and extractable text.

Expected: no critical warning or overflow; all pages Letter; all fonts embedded; no Type 3, identity metadata, JavaScript, links, bookmarks, or attachments.

- [ ] **Step 4: Render and inspect every PDF page**

Render all pages to temporary PNG files with `pdftoppm`, inspect each page at original resolution, and verify figure legibility, no cropping, no caption separation, and preserved reading order.

Expected: both new figures are readable at paper width; the existing UI screenshot remains intact; the final reproducibility/human-protocol split remains clear.

- [ ] **Step 5: Clean diagnostics and record final artifacts**

Remove temporary rendered pages and supplement auxiliary files. Keep only the formal source and PDF plus the two project figure assets. Record sizes, timestamps, page count, and SHA-256 hashes.

### Task 6: Close the written plan

**Files:**
- Modify: `docs/superpowers/plans/2026-07-15-aaai27-supplement-figures.md`

- [ ] **Step 1: Mark every completed checkbox**

Change each plan checkbox from `[ ]` to `[x]` only after its verification has passed.

- [ ] **Step 2: Verify no unchecked steps remain**

Run:

```bash
awk '/- \[x\]/{done++} /- \[ \]/{todo++} END{print "completed=" done+0; print "unchecked=" todo+0}' docs/superpowers/plans/2026-07-15-aaai27-supplement-figures.md
```

Expected: `unchecked=0`.
