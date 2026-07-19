# Paper Case Studies (English)

This directory contains publication-ready qualitative figures derived from the
frozen English method-comparison artifacts in
`../method_comparison_samples_en/`.

## Figures

- `figures/qualitative_dijkstra_comparison.*` compares four distinct methods
  on the same Dijkstra task and displays the nine recorded browser checks.
- `figures/complete_knapsack_walkthrough.*` presents an annotated walkthrough
  of one complete-knapsack AlgoTutorGen artifact.
- `figures/cross_family_gallery.*` shows four AlgoTutorGen examples from
  dynamic programming, shortest paths, backtracking, and union-find.

Each figure is exported as editable SVG, vector PDF, and 300-dpi PNG. Raster
screenshots remain embedded images; all figure labels, audit strips, panel
letters, and annotations remain vector text.

## Interpretation boundary

The screenshots document visible interfaces. Functional pass/fail labels are
copied from each method's `audit.json`; they are not inferred from the
screenshot. The 23-case qualitative package is separate from the Full-200
main experiment.

## Regeneration

From the repository root:

```bash
python3 artifacts/paper_case_studies_en/generate_qualitative_figures.py
```

The script validates the selected audit records, regenerates all formats, and
copies publication assets to `latex/figures/`.

