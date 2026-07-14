# AlgoTutorGen Paper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and verify a complete anonymous ACM `sigconf` paper that presents AlgoTutorGen as contract-guided compositional synthesis of verifiable interactive algorithm tutors.

**Architecture:** The paper is built from a frozen evidence ledger, a verified BibTeX library, three code-native analytical figures, and one Playwright-captured interface figure. The prose separates formal conditional statements from finite executable evidence, reports the negative recovery result prominently, and keeps all pending human studies outside completed claims.

**Tech Stack:** ACM `acmart`, pdfLaTeX, BibTeX, TikZ, PGFPlots, booktabs, graphicx, Playwright/Docker browser capture, shell-based consistency scans.

---

### Task 1: Freeze the evidence ledger

**Files:**
- Create: `latex/evidence-ledger.md`
- Read: `docs/36_THEORY_ALIGNED_EXPERIMENTS_REPORT.md`
- Read: `docs/21_ALGOTUTORGEN_PAPER_REPORT.md`
- Read: `docs/33_PLAN_MD_EXPERIMENT_COMPLETION_REPORT.md`
- Read: `docs/34_MULTIMODEL_FULL200_BASELINE_REPORT.md`
- Read: `docs/35_CANDIDATE_ROUND_BUDGET_ANALYSIS.md`

- [ ] **Step 1: Extract every number used by the required abstract, figures, and tables**

Record the source file, section, result path, numerator, denominator, percentage, statistical test, and allowed interpretation for each of: main reliability, nested survival, semantic preservation, semantic mutation, noninterference, determinism, Local/Global recovery, cross-model generation, held-out generation, ablations, browser repair, and long-trace scalability.

- [ ] **Step 2: Record conflict resolutions explicitly**

Use the newest report as authoritative. In particular, retain `39/40` for the original held-out generation result and describe the later `40/40` only as a targeted artifact completion used by the semantic-preservation audit.

- [ ] **Step 3: Scan the ledger for unsupported human-study results**

Run:

```bash
rg -n "expert result|student result|learning gain|calibration complete|trace audit complete" latex/evidence-ledger.md
```

Expected: no statement that pending labels or human studies are completed.

### Task 2: Verify related work and build BibTeX

**Files:**
- Create: `latex/references.bib`
- Create: `latex/reference-audit.md`

- [ ] **Step 1: Verify foundational sources**

Verify title, authors, year, venue, DOI or stable URL for SYNQUID, CompCert semantic preservation, assume-guarantee reasoning, Goguen--Meseguer noninterference, QuickCheck, metamorphic testing, TRAKLA2, Naps, Python Tutor, Algorithm Visualizer, Mayer multimedia learning, Munzner's nested model, and LORI/MERLOT-related educational-object evaluation.

- [ ] **Step 2: Verify directly comparable generated-page systems**

Use primary papers, publisher pages, author PDFs, or official repositories for WebGen-Agent, HTMLCure, EduVisAgent, and any retained interactive webpage generation work. Omit candidates whose bibliographic metadata cannot be confirmed.

- [ ] **Step 3: Write complete BibTeX entries**

Use stable keys, ASCII-safe LaTeX accents, full author lists when available, venue, year, DOI, and URL. Do not use `note={arXiv}` when a formal venue is verified.

- [ ] **Step 4: Create a reference audit table**

For every BibTeX key, record the verification URL and the paper section that will cite it.

### Task 3: Capture a grounded system interface figure

**Files:**
- Create: `latex/figures/system-ui.png`
- Read: `scripts/run_browser_smoke_container.sh`
- Read: representative HTML artifacts under `output/experiments/`

- [ ] **Step 1: Select a representative verified artifact**

Choose a Stage1 page with visible algorithm state, timeline, teaching explanation, interaction controls, and validation evidence. Prefer binary search, unique paths, or Dijkstra because their state transitions are visually legible in a two-column paper figure.

- [ ] **Step 2: Capture the page with Playwright**

Use the repository's Playwright-compatible Docker path because the host glibc cannot run the bundled Playwright Node binary. Set a publication-friendly viewport, navigate to a representative key frame, expose the teaching/interaction panel, and save a PNG under `latex/figures/`.

- [ ] **Step 3: Inspect the image**

Verify that text is legible at column or page width, no personal data or API credentials appear, the screenshot is not clipped, and it reflects the real generated artifact rather than a mockup.

### Task 4: Create the ACM paper skeleton and analytical figures

**Files:**
- Create: `latex/main.tex`

- [ ] **Step 1: Add the required preamble**

Use:

```latex
% Compile with:
% pdflatex main.tex
% bibtex main
% pdflatex main.tex
% pdflatex main.tex
\documentclass[sigconf,review,anonymous]{acmart}
```

Load only pdfLaTeX-compatible packages required by the paper, define theorem environments, configure PGFPlots compatibility, and define compact reusable table/figure styles.

- [ ] **Step 2: Add anonymous metadata and complete section structure**

Include title, anonymous author, abstract, CCS concepts, keywords, all required body sections, acknowledgments suppression appropriate for anonymous review, bibliography commands, and appendices.

- [ ] **Step 3: Implement Figure 1 in TikZ**

Draw open-ended LLM stages with rounded boxes, deterministic stages with rectangular boxes, contract checks with diamond or narrow gate nodes, algorithmic state with solid lines, and pedagogical-state flow with dashed lines. Include a legend that remains interpretable in grayscale.

- [ ] **Step 4: Implement Figure 2 in PGFPlots**

Plot cumulative survival at C1--C6:

```text
AlgoTutorGen: 100, 100, 100, 99, 99, 99
Direct HTML: 100, 94, 74.5, 54, 49, 49
```

The caption must define C1 answer, C2 load, C3 interaction, C4 bidirectional feedback, C5 teaching support, and C6 noninterference.

- [ ] **Step 5: Implement Figure 3 in TikZ**

Map compositional preservation to `55,108` frames, contract discrimination to `2,198 + 392` mutations, noninterference to `1,561,298` actions, and conditional recovery to the negative Local/Global experiment. Each branch must state its evidence boundary.

- [ ] **Step 6: Insert the real UI screenshot**

Use `\includegraphics` with a factual caption explaining that the screenshot illustrates the fixed runtime and is not itself correctness evidence.

### Task 5: Write the formal problem and method sections

**Files:**
- Modify: `latex/main.tex`

- [ ] **Step 1: Write the 180--230 word abstract**

Include 200 tasks and 23 families, 198/200 versus 98/200 Machine OK, 55,108 preserved frames, 2,198 rejected violations, 392 accepted preserving transformations, 1,561,298 actions with no observed violation, and the explicit negative recovery result. Do not claim learning gains.

- [ ] **Step 2: Write the introduction and contributions**

Follow the observation--diagnosis--factorization--theory--results sequence. Define constraint entanglement and state four contributions without marketing language.

- [ ] **Step 3: Write the problem formulation**

Define input $x=(q,i,e,c)$, artifact $W=(S,T,G,P,R)$, and the global contract conjunction. Explain why explicit contracts, early rejection, semantic reuse, and deterministic compilation--not modularity alone--create the benefit.

- [ ] **Step 4: Write the system design**

Describe solver/spec generation, TraceSession DSL, sandbox execution, result/trace/process/scene validation, deterministic compilation, runtime, teaching overlay, browser audit, and actual repair boundaries. Accurately characterize the current process validator as a DSL-era sanity layer rather than per-family formal verification.

- [ ] **Step 5: Write the theoretical analysis**

Define canonical projections and state/prove compositional semantic preservation, pedagogical noninterference, nested contract survival, and conditional ideal stage-local recovery. For every theorem, immediately state which premise is checked empirically and which premise remains assumed.

### Task 6: Write setup, results, and negative findings

**Files:**
- Modify: `latex/main.tex`

- [ ] **Step 1: Write experimental setup and metrics**

Document 200 tasks, 23 families, 646 samples, sample-0 main comparison, models, expected visibility, repair budgets, nine Machine OK checks, paired statistics, external baselines, and theory-aligned audits.

- [ ] **Step 2: Write Table 1 and main reliability analysis**

Report AlgoTutorGen `198/200`, Direct `98/200`, WebGen-Agent `45/200`, and strict HTMLCure `40/200`, plus the paired bootstrap interval and McNemar result for AlgoTutorGen versus Direct.

- [ ] **Step 3: Write Table 2 and theory-aligned evidence**

Report projection preservation, determinism, semantic mutation discrimination, overlay isolation, and browser noninterference with exact denominators.

- [ ] **Step 4: Write Table 3 for cross-model and held-out evidence**

Report Flash `196/200` versus `118/200`, GLM `170/200` versus `35/200`, Kimi `160/200` versus `87/200`, and held-out `39/40` versus `18/40` with its paired test. Keep targeted completion separate.

- [ ] **Step 5: Write Table 4 and the recovery section**

Report Flash Local `38/50` versus Global `42/50`, GLM Local `42/50` versus Global `43/50`, token cost per successful page, and McNemar values. Explain teaching recomputation and avoid equivalence claims from nonsignificant tests.

- [ ] **Step 6: Write ablations and scalability**

Include Direct-to-SceneGraph, VerifiedTrace-to-LLM-HTML, browser-repair budget collapse, and long-trace storage/load costs. Put secondary visual results in the appendix unless page space permits.

### Task 7: Write related work, discussion, limitations, and appendix

**Files:**
- Modify: `latex/main.tex`

- [ ] **Step 1: Write related work from the audited bibliography**

Organize by generated webpages/browser agents, algorithm visualization/tutoring, synthesis/refinement, compositional verification/semantic preservation, and noninterference/property-based testing. State differences narrowly and avoid unsupported priority claims.

- [ ] **Step 2: Write discussion**

Answer why the approach works, what is mathematically established, what is checked only on finite artifacts, what is not established, and why the negative recovery result matters.

- [ ] **Step 3: Write threats and limitations**

Cover metric construct validity, runtime evaluator bias, pending human calibration and trace review, finite mutation suites, stress testing versus proof, sample-0 weighting, 646-sample failures, unequal compute, remote model drift, long-trace size, single-VLM visual evaluation, and absent student outcomes.

- [ ] **Step 4: Write conclusion and appendices**

Conclude with contract-guided semantic factorization, executable interaction reliability, compositional evidence, pedagogical isolation, and missing computational checkpointing. Add metric, robustness, scalability, and reproducibility appendices without introducing new unsupported claims.

### Task 8: Compile and audit the final paper

**Files:**
- Verify: `latex/main.tex`
- Verify: `latex/references.bib`
- Generate: `latex/main.pdf`

- [ ] **Step 1: Run static source checks**

Check forbidden packages, placeholder text, Unicode math, unescaped percent/underscore risks, duplicate labels, missing BibTeX keys, and claims about pending human studies.

- [ ] **Step 2: Run the required build**

From `latex/`:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Expected: all commands exit `0` and produce `main.pdf`.

- [ ] **Step 3: Inspect the log**

Run:

```bash
rg -n "Undefined control sequence|LaTeX Error|Citation .* undefined|Reference .* undefined|There were undefined references|multiply defined" main.log
```

Expected: no matches.

- [ ] **Step 4: Inspect the rendered PDF**

Render representative pages to images and visually inspect the title/abstract, theory pages, all figures, wide tables, references, and appendix for clipping, illegible text, or severe overfull boxes.

- [ ] **Step 5: Reconcile every numerical claim**

Compare all numerals in the abstract, main tables, captions, and conclusion against `latex/evidence-ledger.md`. Resolve any discrepancy before completion.

- [ ] **Step 6: Report deliverables and verification evidence**

Report absolute paths for `main.tex`, `references.bib`, `main.pdf`, and `figures/system-ui.png`, the final page count, build status, remaining nonfatal warnings, and the explicit boundary that pending human studies remain unreported as results.
