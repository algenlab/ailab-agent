# AlgoTutorGen AAAI-27 Supplement Design

## Objective

Create a separate anonymous supplementary appendix for the AAAI-27 paper. The supplement must preserve the seven-page main-paper limit, add no new unsupported claims, and make the experimental protocol and secondary evidence easier to audit.

## Chosen Format

The supplement uses the official `aaai2027` anonymous submission style in a standalone `latex/supplement.tex` and compiles to `latex/supplement.pdf`. It does not use `\appendix` inside `main.tex`, does not alter `main.pdf`, and does not rely on cross-document LaTeX references.

## Content Structure

1. **Scope and reading guide:** distinguish main-paper claims from supplementary detail.
2. **Machine OK protocol:** define all nine checks, browser isolation, retry provenance, artifact sets, and paired statistics.
3. **Nested contract survival:** provide full cross-model C1--C6 results and explain cumulative versus conditional interpretation.
4. **Theory-aligned audits:** break down semantic preservation, determinism, mutation discrimination, overlay sanitization, and noninterference action counts.
5. **Recovery experiment:** report success, paired counts, calls, token/time costs, cost decomposition, and why the ideal checkpoint theorem does not apply directly.
6. **Additional reliability evidence:** include the 646-sample replay, held-out provenance, non-degenerate ablations, and Direct browser-repair budget.
7. **Scalability and visual evidence:** report long-trace costs, secondary visual ratings, and include the real Playwright-captured system interface.
8. **Reproducibility boundaries:** list frozen reports/result files and all pending human-data protocols.

## Evidence Policy

All numerical values come from `latex/evidence-ledger.md`, whose source priority is `docs/EXPERIMENT_RESULTS.md`, then the latest paper report and dedicated machine-result reports. The original held-out generation result remains 39/40; the targeted 40th artifact is identified only as audit completion. Zero stress-test violations are described as absence of a found counterexample, never as a universal proof.

## Presentation Policy

- Use self-contained tables with exact denominators and concise evidence boundaries.
- Use the existing bitmap `figures/system-ui.png`; the screenshot is interface evidence, not correctness evidence.
- Keep anonymous metadata and omit acknowledgments, links, author identities, and project URLs that could deanonymize the submission.
- Reuse official `aaai2027.sty` and avoid all prohibited packages, spacing changes, and page-layout commands.
- Use no external bibliography unless a supplementary statement requires a citation; the current design requires none.

## Verification

Compile twice with PDFLaTeX, then check undefined references, overflow, page size, anonymity, embedded fonts, Type 3 fonts, links/bookmarks, claim boundaries, and visual legibility of every page.

