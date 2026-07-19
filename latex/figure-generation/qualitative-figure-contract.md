# Qualitative Figure Contract

## Scope

These figures document real, frozen English artifacts from
`artifacts/method_comparison_samples_en/`. They do not regenerate interfaces,
infer hidden behavior from pixels, or replace the browser audit.

## Core conclusions

1. **Aligned method comparison.** Visually plausible pages can still fail the
   executable tutoring contract. The Dijkstra comparison therefore pairs each
   static screenshot with its nine recorded browser checks.
2. **Single-case walkthrough.** The complete-knapsack example shows how a
   concrete input, an algorithm-state view, navigation, and a verified answer
   are presented in one selected AlgoTutorGen artifact.
3. **Cross-family coverage.** Four AlgoTutorGen examples show that the fixed
   shell supports distinct visual structures rather than one repeated layout.

## Evidence rules

- Screenshot pixels come from the released `screenshot.png` files.
- Pass/fail badges come only from the corresponding `audit.json`.
- A static screenshot is never described as proving an interaction failure.
- Direct HTML and HTMLCure are not shown as separate visual outputs when their
  screenshot hashes are identical.
- The qualitative 23-case package is reported separately from the Full-200
  main experiment.

## Layout and export

- Final width: 7.2 inches (AAAI double-column width).
- Minimum figure text: 7.2 pt; panel/method labels: 8.5--10 pt.
- White figure page; screenshots retain their original light or dark theme.
- Green denotes a passed recorded check; red denotes a failed recorded check.
- Primary editable output: SVG with text preserved as text.
- Companion outputs: vector PDF and 300-dpi PNG.

