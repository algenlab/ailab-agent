# AlgoTutorGen Paper Figures Redesign

## Objective

Produce three publication-ready figures from the current AlgoTutorGen paper and benchmark artifacts:

1. a comparison between Direct HTML, final-artifact browser repair, and AlgoTutorGen;
2. a detailed AlgoTutorGen system architecture;
3. an AlgoLearnEnv-Bench dataset overview.

The two existing PNGs are visual references rather than immutable edit targets. New outputs preserve their scientifically useful structure while improving hierarchy, density, typography, and readability at paper scale.

## Selected Production Route

Use the project-configured OpenAI-compatible API and the best available GPTImage2 model to generate strong raster foundations. Use AutoFigure-Edit for structure-aware refinement and text/layout correction where its supported workflow is applicable. Apply deterministic local post-processing only for publication requirements such as exact cropping, padding, resolution, or compositing; do not use local edits to change scientific meaning.

This hybrid route was selected over:

- a single fully generated pass, which is fast but unreliable for dense technical labels and exact arrows;
- pure TikZ/SVG reconstruction, which is deterministic but does not satisfy the requested GPTImage2 and AutoFigure-Edit workflow.

## Shared Visual System

- Wide landscape composition, approximately 2:1, designed for full-width AAAI `figure*` placement.
- Clean white or near-white background, flat 2D scientific illustration, restrained line weight, generous but efficient whitespace.
- Navy/blue: canonical algorithmic state and primary structure.
- Teal/mint: deterministic validated stages.
- Purple/lavender: pedagogical state and teaching flow.
- Muted red: entanglement, failure, and repair.
- Orange: iterative final-artifact browser repair.
- English labels only, high-contrast sans-serif type, no gradients, 3D effects, decorative people, logos, watermarks, or invented performance claims.
- Prefer compact semantic symbols and aligned cards over oversized decorative icons.

## Figure 1: Generation-Paradigm Comparison

### Purpose

Explain structural differences in output space, validation granularity, repair scope, and algorithm/teaching-state separation. The figure is not a universal quality ranking and contains no reliability counts or p-values.

### Composition

Use three aligned vertical method islands:

1. **Direct HTML**
   - `Problem`, `Input`, and `Expected Answer` enter one free-form browser artifact.
   - Inside the artifact, answer, trace, scene, runtime, feedback, and state isolation are visibly entangled.
   - A final-only audit returns to a whole-page rewrite loop.

2. **Final-artifact repair**
   - Header: `Final-artifact repair`.
   - Subtitle: `WebGen-Agent / HTMLCure-style` or a wording consistent with the evaluated protocol.
   - A single monolithic HTML artifact cycles through browser feedback and whole-artifact rewrite.

3. **AlgoTutorGen**
   - `Spec -> Trace -> Scene -> Runtime -> Browser Artifact` with contract diamonds between representations.
   - Sanitized read-only facts branch to a separate teaching overlay through a dashed purple path.
   - The browser release audit returns only to specification-level repair.

### Evidence Boundary

The grouping of WebGen-Agent and HTMLCure is specific to the paper's evaluated final-artifact paths. Do not imply identical internal architectures or universal inferiority.

## Figure 2: Detailed System Architecture

### Purpose

Show implementation components, validation boundaries, canonical and pedagogical state flows, and the actual recovery boundary more clearly than the compact main-paper TikZ figure.

### Composition

- Left input dock: `Problem q`, `Concrete Input i`, `Expected / Oracle e`, `Optional Code / Strategy c`.
- Main solid path: `LLM Solver / Specification`, `Sandboxed Materialization`, `TraceSession DSL`, `SemanticTrace`, `SceneGraph Compiler`, `Validated SceneGraph`, `Fixed Web Runtime`, and `Self-contained Browser Artifact`.
- Validation rail: result/oracle, trace schema, process continuity, scene reference, projection agreement, and nine-check browser release audit.
- Lower dashed purple teaching path: sanitized read-only facts, overlay sanitizer, LLM teaching enrichment, and pedagogical state entering the browser artifact.
- Red repair path: browser failure signal returns to repair the current specification.
- Explicit boundary: materialization and teaching are recomputed after repair; the implementation is not fully checkpointed stage-local recovery.

### Scientific Invariants

- Solid primary arrows carry canonical algorithmic state.
- Dashed purple arrows carry mutable pedagogical state derived from sanitized read-only facts.
- Contract gates must sit between the correct representations.
- No arrow may imply that teaching enrichment rewrites canonical algorithmic state.
- No visual may claim formal proof of arbitrary source traces.

## Figure 3: AlgoLearnEnv-Bench Dataset Overview

### Purpose

Communicate benchmark scale, coverage, task-bundle richness, and evaluation strata without presenting 646 samples as independent tasks.

### Exact Facts

- `200 tasks`
- `646 concrete samples`
- `23 algorithm families`
- `40 held-out tasks across 15 supported families`
- `62 family-core tasks / 222 samples`
- `138 expansion tasks / 424 samples`
- `71 deterministic-synthetic tasks`
- `129 public-synthetic tasks`
- Difficulty: `43 easy`, `157 medium`

### Composition

Use a three-part horizontal story:

1. **Scale cards** with the four headline numbers: 200, 646, 23, and held-out 40/15.
2. **Coverage field** using compact family glyphs/cards grouped into readable super-families rather than a dense 23-bar chart. Representative groups include arrays/search, graphs, dynamic programming, strings, trees, data structures, and mathematical/advanced families.
3. **Task-bundle anatomy** showing that each case contains a problem and concrete inputs, oracle/verifier, executable solver, typed semantic trace, required views, learning objectives, interaction tasks, and assessment metadata.

Include a restrained lower split for `family-core 62` and `expansion 138`. State visually or in the caption that the 646 samples are multiple concrete inputs from the same 200 tasks.

### Evidence Boundary

Held-out tasks are new tasks within supported families, not previously unseen algorithm families. The dataset figure must not imply balanced family counts, student learning outcomes, or 646 independent task-level observations.

## Files and Preservation

Preserve the existing source figures. Save redesigned assets as siblings before any optional replacement decision:

- `latex/figures/method-paradigm-comparison-v2.png`
- `latex/figures/system-detailed-architecture-v2.png`
- `latex/figures/dataset-overview.png`

Also save final prompts and generation metadata under a dedicated project-local work directory so the figures are reproducible without exposing API credentials.

## Tool and API Workflow

1. Clone `https://github.com/ResearAI/AutoFigure-Edit` into `$AUTOFIGURE_ROOT`.
2. Inspect its README, examples, dependencies, supported providers/models, input/output conventions, and editing commands.
3. Read the existing project's ignored API settings without printing the credential.
4. Query the configured `/models` endpoint and select the highest-quality available GPTImage2 identifier.
5. Generate one or more candidates per distinct figure.
6. Use the existing two PNGs as composition/content references for Figures 1 and 2.
7. Use AutoFigure-Edit for targeted corrections supported by the cloned tool; do not force it into a path its documentation does not support.
8. Inspect every candidate at original resolution and iterate on one defect at a time.

## Acceptance Checks

For every final figure:

- PNG, landscape, nonzero dimensions, publication-scale resolution.
- No cropped labels, misspellings, duplicated/invented nodes, crossed arrows, logos, watermarks, or unsupported claims.
- Scientific relationships match the paper and benchmark JSON.
- Readable both at original resolution and at approximate full-width paper scale.
- Existing figures remain recoverable.
- Prompts, model identifier, tool path, and output paths are recorded without API secrets.

For the complete delivery:

- Verify all three assets with file/image metadata checks.
- Produce a contact sheet for side-by-side review.
- If LaTeX integration is changed, compile and visually inspect the relevant PDF; otherwise leave the paper source untouched and report the ready-to-integrate files.
