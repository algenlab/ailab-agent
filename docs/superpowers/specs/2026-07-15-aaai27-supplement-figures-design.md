# AAAI-27 Supplement Figure Design

## Objective

Add two publication-ready raster infographics to the anonymous AAAI-27 supplement: (1) a system-level comparison of generation paradigms and (2) a detailed implementation architecture for AlgoTutorGen. The figures must complement, rather than duplicate, the compact TikZ architecture already present in `latex/main.tex`.

## Chosen Production Approach

Use the built-in image2 generation path to create the visual foundation for each infographic, then apply deterministic local text correction or overlay when needed. This hybrid approach preserves the requested image2 visual treatment while ensuring that technical labels, contract names, and claim boundaries are exact.

Rejected alternatives:

1. A single fully generated image2 pass with all dense text is faster but risks misspelled labels and incorrect mathematical notation.
2. Pure TikZ or SVG would maximize textual precision but would not satisfy the explicit request to use image2.

## Figure 1: Generation-Paradigm Overview

### Purpose

Explain why AlgoTutorGen differs structurally from monolithic HTML generation and final-artifact browser repair. The figure compares synthesis and validation mechanisms, not universal system quality.

### Composition

Use a wide three-lane landscape composition with one lane per paradigm:

1. **Direct HTML**
   - Flow: `Problem + Input + Expected Answer` -> `One-shot Free-Form HTML` -> `Final Browser Audit`.
   - Show answer, trace, scene, runtime, feedback, and state isolation as intertwined obligations inside one red artifact.
   - Repair label: `Whole-page rewrite`.

2. **Iterative Final-Artifact Repair**
   - Subtitle: `WebGen-Agent / HTMLCure-style`.
   - Flow: `Generate HTML` -> `Browser Feedback` -> `Rewrite HTML`, with an orange feedback loop.
   - Show that evaluation is richer than one-shot generation while the repaired object remains free-form HTML.
   - Repair label: `Whole-artifact repair`.

3. **AlgoTutorGen**
   - Flow: `Executable Spec` -> `SemanticTrace` -> `Validated SceneGraph` -> `Fixed Runtime` -> `Browser Artifact`.
   - Add a separate `Teaching Overlay` branch from sanitized read-only facts.
   - Show contract gates `C_S`, `C_T`, `C_G`, `C_P`, and `C_B` between representations.
   - Repair label: `Specification-level repair in the current system`.

A compact comparison band at the bottom uses these exact row labels:

- `Output space`
- `Validation granularity`
- `Repair scope`
- `Algorithm / teaching state`

The figure contains no experimental success counts. Exact counts remain in the result tables and caption.

### Evidence Boundary

The caption states that WebGen-Agent and HTMLCure are grouped only as evaluated final-artifact generation/repair paths under this paper's protocol. The image is not a universal ranking of webpage-generation systems.

## Figure 2: Detailed AlgoTutorGen Architecture

### Purpose

Expand the compact main-paper TikZ figure into an implementation-level map of components, validators, state flows, and the actual repair boundary.

### Components and Exact Labels

Inputs:

- `Problem q`
- `Concrete Input i`
- `Expected / Oracle e`
- `Optional Code / Strategy c`

Generated or open-ended stages:

- `LLM Solver / Specification`
- `LLM Teaching Enrichment`

Deterministic stages:

- `Sandboxed Materialization`
- `TraceSession DSL`
- `SemanticTrace`
- `SceneGraph Compiler`
- `Validated SceneGraph`
- `Fixed Web Runtime`
- `Self-contained Browser Artifact`

Validation and contract labels:

- `Result / Oracle Check`
- `Trace Schema Check`
- `Process Continuity Check`
- `Scene Reference Check`
- `Projection Agreement Check`
- `Overlay Sanitizer`
- `9-check Browser Release Audit`

State and repair annotations:

- `Canonical algorithmic state` on a solid blue path.
- `Mutable pedagogical state` on a dashed purple path.
- `Sanitized read-only facts` entering teaching enrichment.
- A red `Browser failure signal` loop returning to `Repair Current Specification`.
- Boundary note: `Materialization and teaching are recomputed after repair.`
- Footer note: `Implemented: specification-level repair; not fully checkpointed stage-local recovery.`

### Data Flow

The primary left-to-right path carries canonical algorithmic state through the specification, trace, scene, runtime, and released page. Teaching enrichment receives only sanitized verified facts and mutates pedagogical state. Browser audit failures may trigger specification repair, but downstream materialization and teaching are rerun.

## Visual System

Both figures use:

- a clean white background;
- flat academic infographic styling without photorealism, 3D effects, gradients, shadows, logos, or watermarks;
- a color-blind-friendly palette: navy/blue for algorithmic flow, teal for validated deterministic stages, purple for pedagogy, orange for iterative repair, and muted red for entanglement or failure signals;
- consistent rounded cards, restrained line weights, generous whitespace, and legible arrowheads;
- English labels only;
- a 16:9 landscape composition suitable for `figure*` at full text width.

The final assets should be high-resolution PNG files with no transparent background requirement.

## File and Integration Plan

Create new files without overwriting the existing UI screenshot:

- `latex/figures/method-paradigm-comparison.png`
- `latex/figures/system-detailed-architecture.png`

Insert the overview figure after `Supplement Scope and Reading Guide`. Insert the detailed architecture after `Machine OK Protocol and Artifact Provenance`. Keep the current Playwright UI screenshot.

Use full-width `figure*` environments. A supplement length of roughly six to eight pages is acceptable; preserving readability is more important than retaining the previous five-page layout.

## Captions

The overview caption must explain that the diagram compares output structure, validation granularity, repair scope, and state separation. It must state that protocol-specific reliability numbers remain in the tables and that the grouping is not a universal ranking.

The detailed architecture caption must explain the solid algorithmic flow, dashed pedagogical flow, contract gates, and red repair loop. It must explicitly state that the current implementation repairs the specification and recomputes materialization and teaching rather than providing fully checkpointed stage-local recovery.

## Validation

Before acceptance:

1. Compare every visible label against this specification.
2. Inspect each image at full resolution and at final two-column PDF size.
3. Reject or correct misspelled, duplicated, invented, or unreadable text.
4. Confirm that no generated visual implies formal proof, universal superiority, completed human studies, or fully checkpointed recovery.
5. Compile the supplement twice with the existing TinyTeX toolchain.
6. Check page size, overflow, cropping, table/figure separation, fonts, metadata, links, attachments, and text extraction.
7. Visually inspect every final PDF page.

## Non-Goals

- Do not alter `main.tex` or `main.pdf`.
- Do not replace the real Playwright UI screenshot.
- Do not place experimental denominators or p-values inside generated images.
- Do not claim that WebGen-Agent or HTMLCure share identical internal architectures.
- Do not claim that the current system has fully independent per-stage retry.
