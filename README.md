# AlgoTutorGen

AlgoTutorGen turns a concrete algorithm problem into a verifiable, interactive
teaching page. It separates generated algorithm semantics from deterministic
visual compilation and browser execution.

## Inputs and outputs

Inputs:

- an algorithm problem;
- a concrete JSON input;
- an optional strategy hint or reference implementation;
- an optional expected result.

Outputs:

- an executable solution specification;
- a typed `SemanticTrace`;
- a compiled `SceneGraph`;
- a self-contained interactive HTML tutor;
- a machine-readable build artifact.

## Pipeline

```text
Problem + concrete input
        |
        v
LLM-generated solve/trace specification
        |
        v
Sandboxed materialization + contract gates
        |
        v
SemanticTrace
        |
        v
Deterministic Scene Compiler
        |
        v
SceneGraph + fixed Web Runtime
        |
        v
Teaching overlay + browser audit
```

The main design boundaries are:

- the model does not generate the fixed page shell, global layout, or browser
  controls;
- traces use a small typed operation vocabulary;
- the scene compiler projects verified trace objects into visual objects;
- teaching content is generated from verified facts and is checked separately;
- browser release requires all nine recorded interaction checks.

The trace operation vocabulary is:

`create`, `set`, `mark`, `unmark`, `move`, `compare`, `link`, `unlink`, `push`,
`pop`, `enter`, `exit`, and `explain`.

## Quick start

Configure an OpenAI-compatible endpoint through environment variables described
in [`.env.example`](.env.example), then run:

```bash
python3 cli.py \
  --problem "Count the number of unique paths in an m by n grid." \
  --input '{"m":3,"n":7}' \
  --expected '28' \
  --strategy "Dynamic programming and combinatorics" \
  --solutions 2 \
  --output output/unique_paths.html
```

Start the local Web UI with:

```bash
python3 app.py
```

The default local port is `7861`.

## Quality checks

Run the lightweight checks that do not call a remote model:

```bash
python3 scripts/run_quality_checks.py
```

Run the explicit browser smoke path with:

```bash
bash scripts/run_browser_smoke_container.sh
```

The container image defaults to the public Playwright image
`mcr.microsoft.com/playwright/python:v1.59.0-noble` and can be overridden with
`ALGOLAB_PLAYWRIGHT_IMAGE`.

These checks cover schema validation, trace references, process continuity,
scene compilation, sandbox timeouts, HTML export, and browser loading. They do
not prove that every generated trace is a correct implementation for every
possible input.

## Released English artifacts

- [English five-method artifact gallery](artifacts/method_comparison_samples_en/README.md):
  23 cases, five methods, 115 frozen pages/screenshots, and their nine-field
  browser audits.

The gallery distinguishes static visual evidence from executable
browser outcomes. A screenshot alone is not used as proof of hidden interaction
behavior.

## Repository layout

```text
algolab/
  schemas/              # ProblemInput, SemanticTrace, SceneGraph, validation
  generation/           # Model prompts and structured generation
  runtime/              # Sandboxed solve/trace execution
  verification/         # Contract validators and release gate
  compiler/             # SemanticTrace -> SceneGraph
  renderer/             # SceneGraph -> self-contained HTML

scripts/                # Experiment, audit, and artifact builders
benchmark/              # Frozen benchmark definitions
artifacts/              # Public English project demonstrations
tests/                  # Offline and regression tests
cli.py                  # Command-line entry point
app.py                  # Local Web UI entry point
llm_client.py           # OpenAI-compatible model client
```

The historical `modules/`, `renderers/`, and `simulators/` paths are not the
active pipeline. The current entry points are `cli.py` and `app.py`.
