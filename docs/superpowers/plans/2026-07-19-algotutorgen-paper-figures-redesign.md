# AlgoTutorGen Paper Figures Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clone and exercise AutoFigure-Edit, then use the project API with `gpt-image-2` to create and verify three publication-ready AlgoTutorGen paper figures.

**Architecture:** Keep the paper repository in place because the required LaTeX sources, ignored API settings, benchmark JSON, and existing figure references are not present in a clean checkout. Clone AutoFigure-Edit beside it, call its native stage-1 `generate_figure_from_method` function with the project OpenAI-compatible endpoint, use reference-image edits for consistent styling, and preserve every existing source figure by writing versioned outputs.

**Tech Stack:** AutoFigure-Edit v1.1+, OpenAI-compatible Images API, `gpt-image-2`, Pillow/ImageMagick, project benchmark JSON, local visual inspection, optional AutoFigure SAM/SVG stages when their dependencies are already available.

---

### Task 1: Establish Workspace Boundaries and Clone AutoFigure-Edit

**Files:**
- Read: `./latex/main.tex`
- Read: `./benchmark/algo_learn_env_benchmark.json`
- Create: `$AUTOFIGURE_ROOT/`

- [ ] **Step 1: Confirm the required target is absent**

Run:

```bash
test ! -e $AUTOFIGURE_ROOT
```

Expected: exit code 0. If the directory exists, inspect it and reuse it only if its remote is `https://github.com/ResearAI/AutoFigure-Edit` and it has no unrelated local changes.

- [ ] **Step 2: Clone the requested repository at the exact location**

Run:

```bash
git clone https://github.com/ResearAI/AutoFigure-Edit $AUTOFIGURE_ROOT
```

Expected: clone completes and `$AUTOFIGURE_ROOT/autofigure2.py` exists.

- [ ] **Step 3: Record the cloned revision and supported route**

Run from `$AUTOFIGURE_ROOT`:

```bash
git rev-parse HEAD
git remote -v
rg -n 'gpt-image-2|input_figure_path|image_provider openai|Custom Provider' README.md autofigure2.py
```

Expected: the README documents v1.1 support for `gpt-image-2`, user-supplied stage-1 figures, the OpenAI Images route, and custom OpenAI-compatible `/v1` endpoints.

### Task 2: Verify Tool Dependencies Without Polluting the Paper Environment

**Files:**
- Read: `$AUTOFIGURE_ROOT/requirements.txt`
- Create: `./latex/figure-generation/autofigure-usage.md`

- [ ] **Step 1: Check the existing mandated Python environment**

Run:

```bash
python3 -c 'import PIL, openai, requests; print("stage1_dependencies=ok")'
```

Expected: `stage1_dependencies=ok`.

- [ ] **Step 2: Check optional full SVG-pipeline dependencies**

Run:

```bash
python3 -c 'import importlib.util, os; print("sam3="+str(bool(importlib.util.find_spec("sam3")))); print("torch="+str(bool(importlib.util.find_spec("torch")))); print("roboflow_key="+str(bool(os.environ.get("ROBOFLOW_API_KEY")))); print("fal_key="+str(bool(os.environ.get("FAL_KEY")))); print("hf_token="+str(bool(os.environ.get("HF_TOKEN"))))'
```

Expected: a capability report only; no secret values are printed. Stage-1 generation remains usable even if SAM3/RMBG credentials are unavailable.

- [ ] **Step 3: Write a concise usage note**

Create `latex/figure-generation/autofigure-usage.md` with:

- cloned revision and repository URL;
- documented CLI examples for method text, existing stage-1 import, `--image_provider openai`, `--image_model gpt-image-2`, and custom base URLs;
- the exact local strategy: invoke `generate_figure_from_method` directly for stage 1 so a missing optional SAM3 backend does not prevent producing the requested raster figures;
- the optional full pipeline command only when SAM3 plus RMBG are actually available.

### Task 3: Freeze Exact Prompts and Dataset Facts

**Files:**
- Create: `latex/figure-generation/prompts/method-paradigm-comparison.txt`
- Create: `latex/figure-generation/prompts/system-detailed-architecture.txt`
- Create: `latex/figure-generation/prompts/dataset-overview.txt`
- Read: `docs/superpowers/specs/2026-07-19-algotutorgen-paper-figures-redesign.md`

- [ ] **Step 1: Create the method-comparison prompt**

The prompt must specify three aligned vertical islands, exact headers `Direct HTML`, `Final-artifact repair`, and `AlgoTutorGen`, the monolithic repair loops, the contract-separated `Spec -> Trace -> Scene -> Runtime -> Browser` path, the separate teaching overlay, no result counts, and the shared navy/teal/purple/orange/red palette.

- [ ] **Step 2: Create the detailed-architecture prompt**

The prompt must specify the four inputs, main solid algorithmic pipeline, six validation checkpoints, lower dashed teaching lane, browser failure loop, and the exact recovery boundary that materialization and teaching are recomputed and recovery is not fully checkpointed.

- [ ] **Step 3: Create the dataset-overview prompt**

The prompt must include exact figures `200 tasks`, `646 concrete samples`, `23 algorithm families`, `40 held-out tasks / 15 supported families`, `62 family-core / 138 expansion`, and task-bundle anatomy. It must explicitly avoid implying 646 independent tasks or entirely unseen held-out families.

- [ ] **Step 4: Verify the prompt facts against source JSON**

Run:

```bash
jq '.summary' benchmark/algo_learn_env_benchmark.json
jq '.cases | length' benchmark/heldout_cases_v1.json
jq '.cases | map(.family_id) | unique | length' benchmark/heldout_cases_v1.json
```

Expected: main summary reports 200 cases, 646 samples, and 23 family IDs; held-out reports 40 cases across 15 family IDs.

### Task 4: Discover Models and Probe the Hidden Images Route

**Files:**
- Read: `api_settings.json`
- Read: `api_settings.yaml`
- Create: `latex/figure-generation/work/model-probe.png` only if the probe succeeds

- [ ] **Step 1: Query the active project model list without printing the API key**

Use `python3` and `OpenAI(...).models.list()` with `api_settings.json`.

Expected: record the base URL, count, and model IDs. The current list may omit image-only models; omission does not prove the Images route is unavailable.

- [ ] **Step 2: Probe `gpt-image-2` through AutoFigure-Edit's official OpenAI Images implementation**

Run a short Python `-c` command from `$AUTOFIGURE_ROOT` that:

- loads `../ailab-agent/api_settings.json` internally;
- imports `generate_figure_from_method` from `autofigure2.py`;
- uses `provider="openai"`, `model="gpt-image-2"`, the configured base URL, `image_size="1536x1024"`, and `enable_upscale=False`;
- writes `../ailab-agent/latex/figure-generation/work/model-probe.png`;
- never prints the credential.

Expected: a valid PNG proves the hidden image route is usable. If the Images route returns a model/endpoint error, run the same probe with `provider="custom"` so AutoFigure uses the project's `/chat/completions` image-return convention. Record the exact error if both routes fail before choosing any fallback.

### Task 5: Generate and Refine the Method-Paradigm Comparison

**Files:**
- Read: `latex/figures/method-paradigm-comparison.png`
- Read: `latex/figure-generation/prompts/method-paradigm-comparison.txt`
- Create: `latex/figure-generation/work/method-paradigm-comparison-candidate-01.png`
- Create: `latex/figures/method-paradigm-comparison-v2.png`

- [ ] **Step 1: Generate candidate 01 with the existing image as reference**

Call AutoFigure-Edit's `generate_figure_from_method` with `provider="openai"`, `model="gpt-image-2"`, `reference_image_path` pointing to the existing PNG, `image_size="1536x1024"`, and 4K upscale enabled.

Expected: a 3840-pixel-long-edge PNG preserving the useful three-way logic while reducing oversized icons and empty space.

- [ ] **Step 2: Inspect at original resolution**

Check headings, lane ordering, arrow direction, state separation, and absence of invented counts or claims. Reject any candidate with misspellings, duplicated modules, crossed arrows, clipped text, or a universal-ranking implication.

- [ ] **Step 3: Perform one targeted reference-image edit if needed**

Feed candidate 01 back through the same AutoFigure stage-1 function as the reference and use a prompt that names only the observed defects while requiring every correct region to remain unchanged.

Expected: one focused revision, not a complete random redraw.

- [ ] **Step 4: Save the selected final non-destructively**

Copy the selected candidate to `latex/figures/method-paradigm-comparison-v2.png`; preserve the original `method-paradigm-comparison.png`.

### Task 6: Generate and Refine the Detailed Architecture

**Files:**
- Read: `latex/figures/system-detailed-architecture.png`
- Read: `latex/figure-generation/prompts/system-detailed-architecture.txt`
- Create: `latex/figure-generation/work/system-detailed-architecture-candidate-01.png`
- Create: `latex/figures/system-detailed-architecture-v2.png`

- [ ] **Step 1: Generate candidate 01 from the existing architecture reference**

Use the same AutoFigure/OpenAI route and size settings as Task 5 with the detailed architecture prompt.

- [ ] **Step 2: Inspect scientific invariants**

Verify the solid canonical path, dashed teaching path, contract placement, validation rail, browser release audit, specification-only repair return, and the `not fully checkpointed` boundary.

- [ ] **Step 3: Apply one targeted edit if necessary**

Edit only detected label, spacing, or connector defects while preserving correct nodes and flows.

- [ ] **Step 4: Save the selected final non-destructively**

Copy the selected candidate to `latex/figures/system-detailed-architecture-v2.png`; preserve the original PNG.

### Task 7: Generate the Dataset Overview in the Same Visual Language

**Files:**
- Read: `benchmark/algo_learn_env_benchmark.json`
- Read: `benchmark/heldout_cases_v1.json`
- Read: `latex/figure-generation/prompts/dataset-overview.txt`
- Create: `latex/figure-generation/work/dataset-overview-candidate-01.png`
- Create: `latex/figures/dataset-overview.png`

- [ ] **Step 1: Use the best redesigned system figure as a style reference**

Generate candidate 01 through AutoFigure-Edit with `gpt-image-2`, using the selected Figure 1 or Figure 2 output only as a style reference.

- [ ] **Step 2: Inspect every number and evidence boundary**

Verify 200, 646, 23, 40/15, 62/138, task-bundle anatomy, and the wording that samples are concrete inputs from the same 200 tasks.

- [ ] **Step 3: Apply one targeted edit if needed**

Correct only erroneous numbers, labels, or family/task-bundle relationships and retain the shared palette and visual hierarchy.

- [ ] **Step 4: Save the selected final**

Copy the selected candidate to `latex/figures/dataset-overview.png`.

### Task 8: Exercise the Optional Editable-SVG Path When Available

**Files:**
- Read: `$AUTOFIGURE_ROOT/autofigure2.py`
- Create conditionally: `latex/figure-generation/autofigure-svg-smoke/`

- [ ] **Step 1: Evaluate the capability report from Task 2**

If local SAM3 and RMBG requirements are already usable, run one import-mode smoke test on the dataset figure with `--input_figure_path`, `--provider custom`, the project base URL, `--svg_model gpt-5.5`, `--optimize_iterations 0`, and a suitable `--sam_prompt`.

If the environment lacks SAM3/HF or an API SAM credential, do not install a multi-gigabyte optional stack or use unrelated credentials merely for this raster deliverable. Record that AutoFigure's stage-1 generator was exercised successfully and that its optional SVG reconstruction path was inspected but unavailable in the current configured environment.

- [ ] **Step 2: Validate the optional output if produced**

Expected when available: `figure.png`, `samed.png`, `boxlib.json`, `template.svg`, and `final.svg` are nonempty and openable.

### Task 9: Build Review Artifacts and Validate Publication Readability

**Files:**
- Create: `latex/figures/algotutorgen-paper-figures-contact-sheet.png`
- Create: `latex/figure-generation/generation-report.md`

- [ ] **Step 1: Check format, size, and orientation**

Run:

```bash
file latex/figures/method-paradigm-comparison-v2.png latex/figures/system-detailed-architecture-v2.png latex/figures/dataset-overview.png
identify latex/figures/method-paradigm-comparison-v2.png latex/figures/system-detailed-architecture-v2.png latex/figures/dataset-overview.png
```

Expected: three valid landscape PNGs, each with a long edge near 3840 pixels.

- [ ] **Step 2: Inspect original and paper-scale previews**

Use the local image viewer for each original. Create temporary 1200-pixel-wide previews with ImageMagick and verify headings, major labels, arrows, and key numbers remain readable.

- [ ] **Step 3: Create a side-by-side contact sheet**

Use ImageMagick `montage` to place the three final figures in a labeled vertical review sheet without changing the final assets.

- [ ] **Step 4: Write the generation report**

Record:

- AutoFigure-Edit repository revision and relevant usage path;
- active base URL but no credential;
- `/models` discovery result and whether `gpt-image-2` was hidden or listed;
- selected model and provider route;
- exact prompt paths, reference-image roles, candidate/final paths, dimensions, and SHA-256 hashes;
- optional SVG-path capability result;
- scientific and visual checks performed.

### Task 10: Final Verification and Plan Closure

**Files:**
- Modify: `docs/superpowers/plans/2026-07-19-algotutorgen-paper-figures-redesign.md`

- [ ] **Step 1: Run the complete acceptance assertion**

Use the mandated Python interpreter to assert that all three final assets exist, are PNG, are landscape, have nonzero dimensions, and have a long edge of at least 3000 pixels.

- [ ] **Step 2: Confirm original source figures remain unchanged**

Compare their pre-work and post-work hashes or record that only versioned sibling outputs were created.

- [ ] **Step 3: Inspect git scope**

Run:

```bash
git status --short -- latex/figures latex/figure-generation docs/superpowers/plans/2026-07-19-algotutorgen-paper-figures-redesign.md
```

Expected: only the planned prompts, report, review artifact, versioned final images, and plan bookkeeping appear in task scope; unrelated existing changes remain untouched.

- [ ] **Step 4: Mark this plan complete only after every check passes**

Change each completed checkbox to `[x]`, then run:

```bash
awk '/- \[x\]/{done++} /- \[ \]/{todo++} END{print "completed=" done+0; print "unchecked=" todo+0}' docs/superpowers/plans/2026-07-19-algotutorgen-paper-figures-redesign.md
```

Expected: `unchecked=0`.
