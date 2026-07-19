# AlgoTutorGen AAAI-27 Paper Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. The user has explicitly selected inline execution and prohibited subagent delegation.

**Goal:** Convert the existing grounded AlgoTutorGen manuscript into an anonymous, submission-ready AAAI-27 main-track paper with at most seven pages of technical content and at most two additional reference-only pages.

**Architecture:** Preserve the approved contract-centered research narrative and frozen evidence while replacing ACM-specific formatting with the official 2027 AAAI author kit. Compress by removing ACM metadata and the in-paper appendix, merging redundant exposition, and prioritizing four core evidence objects: system architecture, nested contract survival, theory-aligned evidence, and the Local-vs-Global negative result.

**Tech Stack:** PDFLaTeX, BibTeX, official `aaai2027.sty`, official `aaai2027.bst`, TikZ, PGFPlots, booktabs, natbib, Poppler PDF inspection tools.

---

### Task 1: Freeze AAAI-27 submission constraints

**Files:**
- Read: official `AnonymousSubmission2027.tex`
- Add: `latex/aaai2027.sty`
- Add: `latex/aaai2027.bst`

- [ ] Copy the unmodified official 2027 style and bibliography files from the AAAI Author Kit.
- [ ] Record the hard limits: seven technical-content pages, pages eight and nine reserved only for references, US Letter, PDFLaTeX, anonymous submission, no embedded links or bookmarks.
- [ ] Record forbidden packages and commands, including `hyperref`, `cleveref` when it induces forbidden dependencies, `balance`, `geometry`, `flushend`, `stfloats`, `titlesec`, `wrapfig`, manual page breaks, and spacing hacks.

### Task 2: Replace ACM metadata and preamble

**Files:**
- Modify: `latex/main.tex`

- [ ] Replace `acmart` with `\documentclass[letterpaper]{article}` and `\usepackage[submission]{aaai2027}`.
- [ ] Add the official `url`, `graphicx`, `natbib`, `caption`, `booktabs`, and `\pdfinfo{/TemplateVersion (2027.1)}` lines.
- [ ] Remove ACM copyright, conference, CCS, keyword, affiliation, description, and reference-style commands.
- [ ] Use `Anonymous Submission` with empty affiliations and preserve title-case capitalization.
- [ ] Remove unused or AAAI-incompatible packages and replace `\cref` references with explicit typed references.

### Task 3: Recompose the seven-page technical paper

**Files:**
- Modify: `latex/main.tex`

- [ ] Preserve the 180--230 word abstract and the approved constraint-entanglement narrative.
- [ ] Keep all required main sections: Introduction, Problem Formulation, System Design, Theoretical Analysis, Experimental Setup, Results, Negative Recovery Result, Related Work, Discussion and Limitations, and Conclusion.
- [ ] Retain the conditional semantic-preservation and noninterference theorems with concise proofs; compress the chain-rule proposition and ideal-recovery theorem without overstating implementation guarantees.
- [ ] Retain exact main reliability, semantic projection, mutation, noninterference, cross-model/held-out, and Local-vs-Global facts from `evidence-ledger.md`.
- [ ] Remove the main-PDF appendix. Fold only critical protocol definitions, ablation evidence, and scalability limitations into the seven technical pages.
- [ ] Keep the real UI screenshot only if it fits without displacing core technical evidence; otherwise prioritize the code-native analytical figures.

### Task 4: Adapt figures and tables to AAAI columns

**Files:**
- Modify: `latex/main.tex`
- Reuse: `latex/figures/system-ui.png`

- [ ] Resize the architecture diagram for AAAI's 7-inch text width without clipping or margin overflow.
- [ ] Keep the C1--C6 survival plot legible at one-column width.
- [ ] Merge theory-to-evidence facts into a compact table or figure, choosing the smaller rendered result.
- [ ] Keep the Local-vs-Global table in the main paper.
- [ ] Ensure every caption is self-contained and uses no font smaller than AAAI permits.

### Task 5: Adapt the bibliography

**Files:**
- Modify: `latex/references.bib`
- Use: `latex/aaai2027.bst`

- [ ] Preserve only cited, audited entries and retain stable DOI or official repository metadata.
- [ ] Convert arXiv-only entries to AAAI's recommended `@misc` form where needed.
- [ ] Use `\bibliography{references}` and allow `aaai2027.sty` to select the bibliography style.
- [ ] Verify that all citation keys resolve and that references begin no earlier than necessary while remaining within pages eight and nine.

### Task 6: Build and repair layout

**Files:**
- Generate: `latex/main.pdf`
- Inspect: `latex/main.log`, `latex/main.blg`

- [ ] Run `pdflatex main.tex`, `bibtex main`, `pdflatex main.tex`, and `pdflatex main.tex` with the configured TinyTeX/PDFLaTeX toolchain.
- [ ] Confirm page count is at most nine and use extracted page text to verify that technical content ends on or before page seven.
- [ ] Fix only prose, figure composition, and table layout; do not use forbidden spacing, font, margin, or page-break manipulation.
- [ ] Remove undefined citations/references, overfull boxes that cross margins, duplicate labels, and fatal BibTeX warnings.

### Task 7: Perform final AAAI compliance audit

**Files:**
- Verify: `latex/main.tex`
- Verify: `latex/references.bib`
- Verify: `latex/main.pdf`

- [ ] Scan for disallowed packages and commands from the official author kit.
- [ ] Scan for unsupported claims, completed-human-study language, Local-Resume superiority, and formal-verification overclaims.
- [ ] Confirm the PDF is US Letter, version 1.5 or higher, unencrypted, without page numbers, embedded links, or bookmarks, and with all fonts embedded and no Type 3 fonts.
- [ ] Render every PDF page and visually inspect title anonymity, figure legibility, table fit, reference placement, and accidental blank pages.
- [ ] Report exact build commands, page count, warnings that remain, and all files changed.
