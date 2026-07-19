# English Prompt Templates for the Paper Appendix

This file gives faithful English structural renderings of the prompt modules
used by AlgoTutorGen and the Direct HTML baseline. The production prompt files
listed under each module remain the token-exact source of record. Some
production prompts are written in Chinese; therefore the text below must be
cited as an English rendering, not as a byte-identical transcript.

## P1. Executable Solution and SemanticTrace Generation

Source of record:

- `algolab/generation/prompts/tracker_system.txt`
- dynamic input builder: `algolab/generation/solution_generator.py::_build_user_prompt`

```text
ROLE
You generate an executable algorithm solution and a visualization trace.

INPUT
- problem statement
- concrete input JSON
- optional expected output
- optional strategy hint or user code
- required number of solution variants
- required output language

RETURN
One JSON object with exactly these top-level fields:
problem_title, input_contract, verifier_code, variants.

Each variant contains exactly:
id, name, strategy, time_complexity, space_complexity, code, tracker_code.

HARD CONSTRAINTS
- code defines solve(input_data).
- tracker_code defines trace(input_data).
- trace uses the injected TraceSession DSL and returns sess.to_trace().
- solve and trace must return equivalent JSON-serializable answers.
- every important trace event receives a code_line referring to solve code.
- use only documented DSL objects and methods.
- do not emit HTML, CSS, JavaScript, rendering code, extra fields, or Markdown.
- keep the trace instructionally meaningful and each per-frame state compact.

SELF-CHECK
Verify the JSON schema, function signatures, DSL method names, result
agreement, code-line mapping, and complete JSON closure before returning.
```

## P2. Optional Correctness-Contract Drafting

Source of record:

- `algolab/generation/prompts/contract_system.txt`
- `algolab/generation/prompts/contract_repair_system.txt`

This is an optional code path and is not described as a uniformly used
component of the main experiment.

```text
ROLE
Draft a correctness-contract-v1 JSON object.

INPUT
Problem, concrete input JSON, optional expected output, optional strategy.

RETURN
input_schema, output_schema, preconditions, postconditions, oracle_strategy,
oracle_code, test_cases, optional metamorphic relations and process invariants.

HARD CONSTRAINTS
- expected output has priority and must not be rewritten.
- an oracle is executable evidence, not a formal proof.
- oracle code returns the task answer, not a pass/fail judgment.
- use only the permitted standard-library modules.
- do not generate webpage, animation, or layout instructions.
```

## P3. Error-Guided Solution Repair

Source of record:

- `algolab/generation/prompts/repair_system.txt`
- repair context builder: `algolab/generation/repair.py`

```text
ROLE
Repair the previous solution specification after a schema, sandbox, result,
DSL-method, trace-size, or release-gate failure.

INPUT
- original problem and input
- complete previous JSON
- structured failure messages and generated-code traceback

RETURN
A complete replacement JSON object with the same allowed fields and function
signatures as P1.

HARD CONSTRAINTS
- make the smallest relevant change.
- preserve the TraceSession DSL style.
- never fall back to the deprecated Tracer API.
- never invent a DSL object method.
- keep unrelated variants and fields stable.
- preserve solve/trace result agreement.
- if output was truncated, shorten it enough to guarantee valid JSON.
```

## P4. Teaching-Overlay Enrichment

Source of record:

- `algolab/generation/teaching_enricher.py::TEACHING_SYSTEM_PROMPT`
- schema: `TeachingOverlay` and `TeachingOverlayFrame`

```text
ROLE
Add teaching explanations and learner checkpoints to a digest of a validated
SemanticTrace. The trace is the source of truth.

INPUT
- problem, algorithm, input, result, pseudocode, and solve code
- up to 30 selected trace frames with operation, targets, dependencies,
  before/after values, compact state, state difference, and neighboring events

RETURN
{"frames": [{"step": ..., "teaching": ..., "interaction": ...}]}

ALLOWED TEACHING FIELDS
what, why, formula, invariant, common_mistake, hint.

ALLOWED INTERACTION FIELDS
type, prompt, options, answer, explanation, wrong_explanation,
option_explanations.

HARD CONSTRAINTS
- do not alter or restate operation, targets, dependencies, state, result, or
  code_line.
- every checkpoint answer must follow from the supplied verified facts.
- prioritize key transitions, dependency-bearing frames, and the answer frame.
- if the primary call fails, retry with a three-frame digest.
```

## P5. Creative Stage Generation and Layout Repair

Source of record:

- `algolab/generation/prompts/direct_visual_stage_system.txt`
- `algolab/generation/prompts/direct_visual_stage_repair_system.txt`

The block below records the prompt-level contract. The implementation checks
the required script entry point and stable shell IDs, but the nested context
objects are not deep-frozen; therefore “read-only” is a requested protocol, not
an OS-level or language-enforced security guarantee.

```text
ROLE
Draw only the problem-specific main stage inside the fixed Creative Shell.

INPUT
Read-only verified artifact, current frame, all frames, state, evidence, input,
result, and the host element.

RETURN
Only a scoped style block, an optional stage template, and
window.renderCreativeStage(ctx).

HARD CONSTRAINTS
- do not output a complete webpage or duplicate shell panels and controls.
- do not recompute the algorithm or modify result, trace, state, or frames.
- derive all displayed state from ctx.frame/ctx.state/ctx.evidence.
- do not use network, storage, external libraries, eval, or dynamic import.
- use stable layouts, reserved label lanes, and non-occluding highlights.
- layout repair may change only stage presentation, never verified facts.
```

## P6. Direct HTML Baseline

Source of record:

- `scripts/run_direct_html_baseline.py::_system_prompt`
- `scripts/run_direct_html_baseline.py::_user_prompt`
- `scripts/run_direct_html_baseline.py::_repair_prompt`

```text
ROLE
Generate one complete, self-contained algorithm-tutoring HTML page.

INPUT
Title, problem, algorithm family, strategy hint, concrete input JSON, expected
output JSON, and the same teaching requirements used in browser evaluation.

REQUIRED PAGE BEHAVIOR
- readable algorithm code and active-line highlighting
- current-step state and a synchronized timeline
- working previous, next, play, and range controls
- problem-specific algorithm objects
- a learner checkpoint with distinct correct and incorrect feedback
- hint, show-answer, visible learning log, and final answer
- no external resources and no private validation claim

REPAIR
If generation fails, return a complete replacement HTML document using the
structured failure message. The baseline has no SemanticTrace or SceneGraph
checkpoint and repairs the whole page.
```

## P7. Screenshot-Only Teaching-Quality Judge

Source of record:

- `algolab/generation/prompts/vlm_screenshot_judge_system.txt`
- `algolab/generation/prompts/vlm_screenshot_judge_user.txt`

```text
ROLE
Score only visible teaching and visual quality in a screenshot.

DIMENSIONS
layout_readability, algorithm_state_visibility, teaching_explanation,
interaction_affordance, evidence_alignment, overall_teaching_quality.

BOUNDARY
Do not execute the page, infer hidden state, judge answer correctness, or make
a release decision. Return strict JSON with 1--5 integer scores, confidence,
visible issues, and a short caption.
```
