# AlgoTutorGen AAAI-27 Reproducibility Package

This anonymous archive contains the current executable implementation, frozen
benchmark definitions, exact prompt files, representative 23-case method
artifacts, paper-supporting reports, and current LaTeX sources. It does not
contain API credentials.

## Contents

- `code_data_supplement/algolab/`: implementation, runtime, validators, and renderers.
- `code_data_supplement/benchmark/`: 200-task/646-input and held-out definitions.
- `code_data_supplement/scripts/`: generation, audit, and analysis entry points.
- `code_data_supplement/artifacts/method_comparison_samples_en/`: 23 representative cases with artifacts, pages, screenshots, audits, and baseline source.
- `code_data_supplement/output/`: selected frozen reports at the paths used by the paper.
- `code_data_supplement/paper/latex/`: paper, supplement, figures, style, and bibliography sources.
- `supplementary_document.pdf`: current supplement compiled with pdfLaTeX.
- `reproducibility_checklist.pdf`: current checklist compiled with pdfLaTeX.
- `SHA256SUMS`: SHA-256 manifest for this directory.

## Deterministic checks

Run from `code_data_supplement/` with Python 3.10+:

```bash
python3 scripts/run_quality_checks.py
python3 -m pytest tests/regression -q
```

Install the pinned packages in `requirements-browser-smoke.txt`. Live LLM runs
require an externally configured `ALGOLAB_LLM_API_KEY`; credentials are not
part of the archive.

## Scope

The archive includes the reports needed to inspect the paper's final numbers
and the 23-case qualitative evidence, rather than the 24GB historical output
tree. Missing cited materials are listed in `MISSING_MATERIALS.md`. Remote model
versions, provider responses, browser binaries, and API latency can drift.
