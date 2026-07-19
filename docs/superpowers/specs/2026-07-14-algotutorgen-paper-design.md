# AlgoTutorGen Paper Design

## Objective

Produce a complete anonymous ACM `sigconf` research paper in English, compiled with `pdflatex` and BibTeX, under `latex/`. The paper must present AlgoTutorGen as contract-guided compositional synthesis for verifiable interactive algorithm tutors, not as a collection of engineering modules.

The deliverables are:

- `latex/main.tex`
- `latex/references.bib`
- `latex/figures/system-ui.png`, captured from a real generated AlgoTutorGen page with Playwright
- a successfully compiled `latex/main.pdf`

## Chosen Positioning

The paper will use a systems/software-engineering framing strengthened by formal contract analysis and educational-interaction evaluation.

Three candidate framings were considered:

1. **Contract-centered systems paper (selected).** This framing best matches the strongest evidence: executable interaction reliability, cross-representation semantic preservation, contract mutation discrimination, and pedagogical noninterference. It can report the recovery experiment honestly without requiring missing human-learning data.
2. **Education-technology effectiveness paper.** Rejected as the primary framing because evaluator calibration, expert review, and student studies remain pending; the repository does not support a learning-gain claim.
3. **Formal-verification paper.** Rejected as the primary framing because the theorems are conditional paper proofs and the implementation evidence is finite executable checking rather than machine-assisted verification of arbitrary source traces.

The working title is:

> AlgoTutorGen: Contract-Guided Compositional Synthesis of Verifiable Interactive Algorithm Tutors

## Central Argument

Monolithic HTML generation entangles heterogeneous obligations: answer correctness, trace consistency, visual-state binding, browser execution, bidirectional feedback, teaching support, and noninterference. AlgoTutorGen factors these obligations through executable semantic representations and explicit contracts. The factorization supports early rejection, deterministic downstream compilation, compositional semantic reasoning, and stable teaching interactions.

The paper will distinguish:

- **semantic decoupling**, which separates solver facts, trace state, scene state, and pedagogical state;
- **verification decoupling**, which checks obligations at the solver, trace, scene, runtime, and interaction boundaries;
- **computational recovery decoupling**, which would cache verified stages and retry only a failed stage.

The current implementation realizes the first two substantially but not the third. Local Resume retains a solution specification, then reruns materialization and teaching. The negative recovery result is therefore a core design finding: semantic factorization does not automatically provide computational checkpointing.

## Claim Hierarchy

### Primary claims

- Under the evaluated 200-task protocol, AlgoTutorGen improves complete executable interaction reliability from Direct HTML's 98/200 to 198/200 Machine OK while both methods display the expected answer on 200/200 pages.
- All evaluated Trace--SceneGraph--Runtime projections are preserved for 294/294 artifacts and 55,108/55,108 frames.
- The evaluated contracts reject 2,198/2,198 tested semantic violations and accept 392/392 tested semantics-preserving transformations.
- No pedagogical noninterference counterexample is found across 240 pages, 24,000 random sequences, and 1,561,298 browser actions.
- The reliability pattern persists across several generation models and held-out tasks.

### Explicit non-claims

- arbitrary source traces are not formally verified;
- the validators are not universally sound and complete;
- student learning gains have not been established;
- the browser implementation is not formally proved noninterfering;
- Local Resume is not superior to Global Restart in the current implementation;
- Stage2 is not visually superior in every dimension.

## Paper Structure

1. **Abstract:** constraint entanglement, semantic factorization, two theoretical properties, main reliability results, semantic evidence, noninterference evidence, and the negative recovery result.
2. **Introduction:** observation, diagnosis, method, theory, evidence, and four contributions.
3. **Problem Formulation:** artifact tuple, contract conjunction, free HTML space versus factored refinement obligations, and the precise source of benefit.
4. **System Design:** generated stages, deterministic stages, validation boundaries, immutable algorithmic state, mutable pedagogical state, and the true repair boundary.
5. **Theoretical Analysis:** canonical projection, compositional semantic preservation, pedagogical noninterference, nested contract survival, and conditional ideal stage-local recovery.
6. **Experimental Setup:** datasets, models, baseline fairness, Machine OK, statistics, theory-aligned protocols, and artifact provenance.
7. **Results:** main reliability, nested contract survival, semantic preservation, contract discrimination, noninterference, determinism, cross-model and held-out evidence, and non-degenerate ablations.
8. **Negative Recovery Result:** Local versus Global with success, token, and time trade-offs plus an explanation of recomputed teaching.
9. **Related Work:** webpage generation and browser agents; algorithm visualization and tutoring; program synthesis and refinement; compositional verification and compilation; noninterference and property-based testing.
10. **Discussion:** why factorization works, what is proved, what is only tested, and what the recovery result teaches.
11. **Threats and Limitations:** construct, internal, external, statistical, reproducibility, scalability, and missing human studies.
12. **Conclusion:** concise restatement of the factorization result and the missing checkpointing boundary.
13. **Appendix:** metric definitions, additional cross-model/held-out tables, ablations, scalability, and reproducibility details as space permits.

## Figures and Tables

### Figures

1. **System architecture (TikZ):** problem/input to solver/spec, SemanticTrace, SceneGraph, runtime, teaching overlay, and browser artifact. Shape, borders, and line styles distinguish generated, deterministic, validation, algorithmic, and pedagogical elements without relying only on color.
2. **Nested contract survival (PGFPlots):** C1--C6 curves for AlgoTutorGen and Direct HTML.
3. **Theory-to-evidence map (TikZ):** each formal property connected to its executable evidence and limitations.
4. **Real system interface (Playwright PNG):** a newly captured representative teaching page showing algorithm state, timeline, teaching explanation, interaction, and evidence panels.

### Tables

1. Main reliability across AlgoTutorGen, Direct HTML, WebGen-Agent, and strict HTMLCure.
2. Theory-aligned evidence for preservation, mutation discrimination, determinism, and noninterference.
3. Cross-model and held-out results.
4. Local Resume versus Global Restart, including success and tokens per successful page.
5. Optional appendix tables for ablations, browser repair, long-trace scaling, and visual evaluation.

## Evidence and Fact Policy

Numerical facts follow this order:

1. `docs/EXPERIMENT_RESULTS.md`
2. `latex/evidence-ledger.md`
3. frozen machine-result paths
4. older plans and summaries

Conflicts will be resolved in favor of the newer report and recorded as LaTeX comments near the relevant table or statement. No human label, expert result, student result, significance test, or bibliography entry will be invented.

## Bibliography Policy

Every cited item must be verified against an original paper, publisher page, author page, or official repository. The bibliography will prioritize foundational and directly relevant sources: SYNQUID, CompCert, assume-guarantee reasoning, noninterference, QuickCheck, metamorphic testing, TRAKLA2, Naps, Python Tutor, algorithm visualization systems, multimedia learning, visualization validation, WebGen-Agent, HTMLCure, and related interactive-page generation work. Unverifiable candidates will be omitted.

## Build and Verification

The paper will use `acmart` with `sigconf,review,anonymous`, BibTeX, TikZ, PGFPlots, tables, and `graphicx`. It will avoid XeLaTeX-only packages, `minted`, Unicode mathematics, shell escape, placeholder prose, and missing references.

Verification will include:

- citation-key completeness;
- label/reference completeness;
- ASCII and forbidden-package scans;
- consistency checks against the source reports;
- a fresh Playwright screenshot and visual inspection;
- `pdflatex main.tex`, `bibtex main`, and two final `pdflatex` runs;
- log inspection for undefined citations/references and fatal overfull layout issues;
- final PDF page count and rendered-page inspection.

## Scope Boundary

This task produces the submission-ready paper artifact and its grounded figures. It does not modify the AlgoTutorGen implementation, rerun costly LLM generation experiments, fabricate pending human studies, or silently rewrite existing experimental outputs.
