# Publication Figure Redesign

## Goal

Redesign the method comparison, system architecture, and dataset overview as a coherent family of publication figures that are visually rich, scientifically exact, and delivered as editable SVG plus paper-ready PNG.

## Decision

Use a hybrid AutoFigure workflow:

1. Use AutoFigure-Edit's GPTImage2 route to create rich visual references with functional research robots, browser artifacts, code documents, traces, scene graphs, validation shields, and teaching overlays.
2. Reconstruct the selected composition as deterministic SVG rather than accepting model-rendered text.
3. Validate and rasterize the SVG with AutoFigure-Edit's `validate_svg_syntax` and `svg_to_png` helpers.

This is preferred over the full SAM reconstruction path because the current machine lacks a configured SAM backend and because the paper requires exact text and connector topology. Pure raster generation is rejected because it produced overly sparse diagrams and cannot guarantee editable elements or exact labels.

## Shared Visual Language

- Flat academic vector illustration on white, with no gradients, shadows, or 3D effects.
- Dense but orderly compositions inspired by AutoFigure-Edit's robot-rich gallery examples.
- One compact white/navy research robot denotes an open-ended LLM or agent role. Robots must perform a semantic action; none may be decorative.
- Deterministic processing uses machines, gears, timelines, graph compilers, and shields rather than robots.
- Browser artifacts, documents, data structures, and audit instruments use reusable SVG groups with stable IDs.
- Palette remains navy/azure, teal/mint, purple/lavender, coral/orange, muted red, charcoal.
- Text remains live SVG `<text>` elements. Connectors remain SVG paths with marker arrows.
- Method comparison: 2400 x 1200 viewBox (2:1).
- System architecture: 2520 x 1200 viewBox (2.1:1).
- Dataset overview: 2400 x 1200 viewBox (2:1).

## Figure 1: Method Paradigm Comparison

- Direct HTML: a red agent robot receives the three input documents and emits one browser containing six visibly tangled obligations. A magnifying-glass audit returns to the whole browser.
- Final-artifact repair: an orange repair robot works around one large browser, with generate, browser-feedback, and rewrite stations on one continuous loop.
- AlgoTutorGen: a navy orchestration robot stands beside separate specification, trace, scene, runtime, and browser cards. Contract diamonds and shields remain explicit. A smaller purple tutor robot appears only on the sanitized teaching branch.
- The right island is slightly wider and visually more structured, but no trophy, ranking, or winner symbol is allowed.

## Figure 2: Detailed System Architecture

- Each canonical representation is a separate illustrated module.
- `LLM Spec` is represented by a research robot writing a specification card.
- Sandboxing, trace materialization, compilation, runtime, and release use deterministic machine imagery.
- The validation rail contains exactly six shield badges aligned under their relevant boundaries.
- The pedagogical lane must connect `Validated SceneGraph` to `Read-only facts`, then `Overlay sanitizer`, then `Teaching enrichment`, and only then to `Browser Artifact`.
- A repair robot with a wrench may appear inside `Repair spec`; the red failure path returns only to `LLM Spec`.

## Figure 3: AlgoLearnEnv-Bench Overview

- Scale uses four large metric cards plus the required clarification about 646 inputs.
- Coverage uses seven family cards with distinct algorithmic glyphs: array/search, graph, DP grid, string, tree, data-structure stack, and math symbol.
- The task bundle is a layered folder containing the eight exact fields and feeds a compact interactive browser artifact.
- One curator robot may organize the task bundle; it is functional, not decorative.
- The held-out boundary is shown as a sealed split card and must state that tasks are new within supported families.

## Deliverables

- `latex/figures/method-paradigm-comparison-v2.svg` and `.png`
- `latex/figures/system-detailed-architecture-v2.svg` and `.png`
- `latex/figures/dataset-overview-v1.svg` and `.png`
- Reproducible SVG generator and validation script under `latex/figure-generation/`
- Updated prompts preserving exact scientific constraints while requiring functional robots and richer visual storytelling

## Verification

- XML/SVG syntax validation through AutoFigure-Edit.
- Rasterization of all SVGs at publication resolution.
- Automated scan for every required label and number.
- Automated rejection of forbidden extra labels where feasible.
- Visual inspection at full resolution and at paper-width reduction.
- LaTeX build verification after the final figures are integrated.
