# AlgoTutorGen AAAI-27 Supplement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. The user selected inline execution and no subagent delegation.

**Goal:** Produce a complete anonymous AAAI-27 supplementary appendix containing protocol details, secondary experiments, the real UI figure, and reproducibility boundaries.

**Architecture:** Build a standalone `supplement.tex` using the same official AAAI style as the main paper. Keep the supplement fact-locked to `evidence-ledger.md`, organize it around auditable tables, and avoid cross-document references or claims that are absent from the main paper.

**Tech Stack:** PDFLaTeX, official `aaai2027.sty`, TikZ-compatible AAAI preamble, booktabs, multirow, graphicx, Poppler PDF inspection tools.

---

### Task 1: Build the standalone anonymous skeleton

**Files:**
- Create: `latex/supplement.tex`
- Reuse: `latex/aaai2027.sty`
- Reuse: `latex/figures/system-ui.png`

- [x] Add the official anonymous AAAI-27 preamble, title, empty affiliations, and supplement scope statement.
- [x] Define only the macros and theorem/table helpers used by the supplement.
- [x] Avoid bibliography and external links unless required by final content.

### Task 2: Write protocol and artifact provenance

**Files:**
- Modify: `latex/supplement.tex`
- Read: `latex/evidence-ledger.md`

- [x] Define the nine Machine OK checks and browser isolation rules.
- [x] Tabulate main, held-out, long-trace, and noninterference artifact sets.
- [x] Explain selected-final retry provenance and paired statistical interpretation.

### Task 3: Add theory-aligned detail

**Files:**
- Modify: `latex/supplement.tex`

- [x] Add full nested C1--C6 survival results for the original and three cross-model conditions.
- [x] Add semantic-preservation subsets, determinism reruns, semantic mutation categories, overlay sanitization, and noninterference action counts.
- [x] State the evidence boundary immediately below each table.

### Task 4: Add recovery and additional evaluation

**Files:**
- Modify: `latex/supplement.tex`

- [x] Add Local-vs-Global success, calls, tokens, time, paired counts, and token decomposition.
- [x] Add 646-sample replay, held-out provenance, two non-degenerate ablations, and Direct browser-repair budget.
- [x] Preserve the negative conclusion and avoid interpreting nonsignificant tests as equivalence.

### Task 5: Add scalability, visual results, UI figure, and reproducibility

**Files:**
- Modify: `latex/supplement.tex`
- Reuse: `latex/figures/system-ui.png`

- [x] Add small/medium/large long-trace browser costs and extreme-page limits.
- [x] Add Stage2-versus-Direct visual dimensions and Holm results.
- [x] Include the real Playwright screenshot with a caption separating interface evidence from correctness evidence.
- [x] List frozen result paths and pending human-label boundaries.

### Task 6: Build and audit

**Files:**
- Generate: `latex/supplement.pdf`
- Inspect: `latex/supplement.log`

- [x] Run PDFLaTeX twice with the existing TinyTeX toolchain.
- [x] Remove undefined references, overflow, forbidden packages, placeholders, and unsupported claims.
- [x] Verify US Letter, anonymous metadata, embedded non-Type-3 fonts, no links/bookmarks, and readable tables/figure on every page.
