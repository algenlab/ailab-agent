# AlgoTutorGen Evidence Ledger

This ledger freezes the numerical facts allowed in `main.tex` and `supplement.tex`. Newer sources override older summaries. Machine-readable reports were checked where available.

## Dataset and protocol

| Fact | Value | Source | Allowed interpretation |
|---|---:|---|---|
| Main benchmark | 200 tasks, 23 algorithm families | `benchmark/README.md`; `docs/EXPERIMENT_RESULTS.md` Sec. 1 | One paired observation per task, using sample index 0. |
| Full deterministic benchmark | 646 samples across the same 200 tasks | `benchmark/README.md`; `docs/EXPERIMENT_RESULTS.md` Sec. 1 | Robustness set; the 646 rows are not independent balanced main-table tasks. |
| Frozen full-sample replay | 626/646 passed (96.90%): sample 0 was 200/200 and additional inputs were 426/446 | `docs/EXPERIMENT_RESULTS.md` Sec. 6.1 | Input-robustness limitation for frozen solvers/trackers; do not merge this denominator with the paired 200-task main comparison or claim 100% input generalization. |
| Core/expansion split | 62 cases/222 samples and 138 cases/424 samples | `benchmark/README.md` | Dataset description only. |
| Held-out set | 40 new cases, 15 families | `docs/EXPERIMENT_RESULTS.md` Sec. 1 | Evidence on a finite frozen held-out set, not open-domain generalization. |

## Main full-200 reliability

| Metric | AlgoTutorGen | Direct HTML | WebGen-Agent | HTMLCure strict | Source |
|---|---:|---:|---:|---:|---|
| Machine OK | 198/200 (99.0%) | 98/200 (49.0%) | 45/200 (22.5%) | 40/200 (20.0%) | `docs/EXPERIMENT_RESULTS.md` Sec. 2 |
| Page load | 200/200 | 188/200 | 194/200 | 75/200 | same |
| Visible answer match | 200/200 | 200/200 | 169/200 | 75/200 | same |
| Interaction reachable | 200/200 | 149/200 | 154/200 | 62/200 | same |
| Correct feedback | 199/200 | 120/200 | 74/200 | 52/200 | same |
| Wrong feedback | 198/200 | 125/200 | 89/200 | 51/200 | same |

Machine OK is the conjunction of page load, visible answer match, interaction reachable, correct feedback, wrong feedback, hint, show answer, learning log, and protected-answer stability. The ninth check compares the protected visible-answer summary, not the full algorithm state; full-state noninterference is evaluated separately. Machine OK measures executable behavior completeness, not student learning.

AlgoTutorGen versus Direct HTML:

- paired difference: +50.0 percentage points;
- 95% paired-bootstrap confidence interval: [43.0, 57.0] points;
- discordant pairs: 101 AlgoTutorGen-only, 1 Direct-only;
- exact two-sided McNemar p-value: 4.06e-29;
- Holm-adjusted p-value: 4.06e-28.

Source: `docs/EXPERIMENT_RESULTS.md` Sec. 2 and `output/experiments/algotutorgen_completion_20260713/statistics/paired_statistics.json`.

Generation boundary: selected-final Stage1 and Direct both reached 200/200 generated pages after allowed retries. Stage1 primary generation was 195/200; five failed tasks were replaced by targeted retries. Do not describe selected-final 200/200 as first-pass success.

## Nested contract survival

Contract levels:

- C1: visible answer match;
- C2: page load;
- C3: interaction reachable;
- C4: correct and wrong feedback;
- C5: hint, show answer, and learning log;
- C6: protected-answer stability.

| Method | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---:|---:|---:|---:|---:|---:|
| AlgoTutorGen main | 100.0 | 100.0 | 100.0 | 99.0 | 99.0 | 99.0 |
| Direct HTML main | 100.0 | 94.0 | 74.5 | 54.0 | 49.0 | 49.0 |
| AlgoTutorGen Flash final | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| Direct Flash | 99.0 | 95.0 | 81.0 | 65.5 | 59.0 | 59.0 |
| AlgoTutorGen GLM final | 99.0 | 99.0 | 99.0 | 98.0 | 98.0 | 98.0 |
| Direct GLM | 100.0 | 91.0 | 53.0 | 38.0 | 17.5 | 17.5 |
| AlgoTutorGen Kimi final | 97.5 | 97.5 | 97.5 | 97.0 | 97.0 | 97.0 |
| Direct Kimi | 99.5 | 95.0 | 68.0 | 52.5 | 43.5 | 43.5 |

Machine source: `output/experiments/theory_aligned_20260714/nested_contract_survival_report.json`. The product identity is the probability chain rule, not a new theorem. The empirical finding is the different conditional survival pattern.

## Semantic preservation and determinism

| Dataset | Artifacts all-frame pass | Equivalent frames | Rate |
|---|---:|---:|---:|
| Main 200 | 200/200 | 9,421/9,421 | 100.0% |
| Held-out completed set | 40/40 | 4,568/4,568 | 100.0% |
| Long-trace 54 | 54/54 | 41,119/41,119 | 100.0% |
| Total | 294/294 | 55,108/55,108 | 100.0% |

Projection boundary: `trace.state -> scene.frame.state -> runtime frame state`.

Twenty stratified ordinary artifacts were recompiled and rerendered ten times each. Every artifact produced one render hash, and every compiled variant produced one projection hash.

Source: `output/experiments/theory_aligned_20260714/semantic_preservation_report.json` and `docs/EXPERIMENT_RESULTS.md` Sec. 5.1.

Allowed interpretation: executable evidence of representation-level semantic preservation on evaluated artifacts. It does not establish that every source trace is an independently correct algorithm execution or that pixel output is formally verified.

Conflict note: the original held-out generation result remains 39/40. The 40th artifact was obtained by an explicitly recorded targeted retry for the semantic-preservation and noninterference suites. Do not replace the original held-out generation result with 40/40.

## Contract discrimination by semantic mutation

| Mutation class | Expected outcome | Result |
|---|---|---:|
| Tested semantic violations | reject | 2,198/2,198 rejected |
| Tested semantics-preserving transformations | accept | 392/392 accepted |

The 392 accepted transformations comprise 195 teaching-text rewrites, 195 visual-metadata modifications, and 2 equivalent unordered-result reorderings. Ambiguous event deletions and equivalent expected-result reorderings were reclassified before this analysis.

Source: `output/experiments/theory_aligned_20260714/semantic_mutation_report.json`; `docs/EXPERIMENT_RESULTS.md` Sec. 5.2.

Allowed interpretation: complete discrimination on the defined mutation suite. Do not claim universal validator soundness or completeness.

## Teaching-overlay isolation and cross-model reuse

The Flash main set contains 372 SceneGraph variants across 200 pages.

| Condition | Result |
|---|---:|
| Original overlay reapplied | 372/372 state hashes preserved |
| Concise legal overlay | 372/372 state hashes preserved |
| Detailed legal overlay | 372/372 state hashes preserved |
| Schema-valid random-text overlay | 372/372 state hashes preserved |
| Illegal `final_answer`/`state` writes | 372/372 sanitized with state hashes preserved |
| Negative step | 372/372 schema-rejected |
| Nonexistent step | 372/372 contract-warned/rejected |
| Cross-model GLM overlay | 369/369 mapped scenes preserved state hashes |

Of the 369 cross-model scenes, 169 applied without warnings and 200 applied partially with `step not found` warnings because the Flash and GLM traces expose different step sets.

Source: `output/experiments/theory_aligned_20260714/cross_model_overlay_report.json`; `docs/EXPERIMENT_RESULTS.md` Sec. 5.3.

Allowed interpretation: the tested overlays did not redefine canonical algorithm state. The illegal-field result is sanitization, not evidence that every unknown field is rejected by schema-level `extra=forbid`; complete isolation is claimed only for the defined finite suite.

## Pedagogical noninterference stress test

| Quantity | Value |
|---|---:|
| Unique pages | 240 (main 200 + held-out 40) |
| Random action sequences | 24,000 |
| Total actions | 1,561,298 |
| Pure pedagogical actions | 435,859 |
| Navigation/variant-selection actions | 1,125,439 |
| Pages passed | 240/240 |
| Observed violations | 0 |
| Overlay artifacts passed | 240/240 |

Pure pedagogical actions: submit correct, submit wrong, hint, show answer, and clear learning log. Navigation actions: next, previous, timeline, reset, and select variant.

Source: `output/experiments/theory_aligned_20260714/noninterference_stress_report.json`; `docs/EXPERIMENT_RESULTS.md` Sec. 5.3.

Allowed interpretation: no counterexample was found in this property-based browser stress suite. Do not claim the implementation is formally proved noninterfering for all future actions.

## Local Resume versus Global Restart

| Model | Strategy | Success | Tokens per successful page | Calls per successful page | Mean time to valid | McNemar comparison |
|---|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash | Local Resume | 38/50 (76.0%) | 71,369 | 6.63 | 172.9 s | p=0.4545 |
| DeepSeek-V4-Flash | Global Restart | 42/50 (84.0%) | 62,256 | 5.50 | 194.2 s | p=0.4545 |
| GLM-5.2 | Local Resume | 42/50 (84.0%) | 92,385 | 6.69 | 533.8 s | p=1.0000 |
| GLM-5.2 | Global Restart | 43/50 (86.0%) | 96,186 | 6.65 | 558.2 s | p=1.0000 |

Paired Flash counts: both 32, Local only 6, Global only 10, neither 2. Paired GLM counts: both 37, Local only 5, Global only 6, neither 2.

Token decomposition per successful page:

| Model | Strategy | Specification generation/repair | Teaching | Total |
|---|---|---:|---:|---:|
| DeepSeek-V4-Flash | Local Resume | 25,031 | 46,338 | 71,369 |
| DeepSeek-V4-Flash | Global Restart | 25,781 | 36,476 | 62,256 |
| GLM-5.2 | Local Resume | 37,342 | 55,043 | 92,385 |
| GLM-5.2 | Global Restart | 47,462 | 48,724 | 96,186 |

Calls and tokens per successful page include the costs of final-failure cases in the numerator; mean time to valid is computed only over successful cases.

Sources: `output/experiments/theory_aligned_20260714/retry_flash/local_vs_global_retry_report.json`, `retry_glm/local_vs_global_retry_report.json`, and `docs/EXPERIMENT_RESULTS.md` Sec. 7.

Allowed interpretation:

- no significant Local success-rate advantage is observed;
- Global is numerically better on Flash success and tokens per success;
- Local is slightly lower in GLM tokens and time but also slightly lower in success, with no significant success-rate difference;
- Local reduces solution-spec generation/repair cost, but rematerialization and teaching recomputation offset the saving;
- the current implementation provides specification-level repair, not fully checkpointed stage-local recovery.

Do not interpret nonsignificant p-values as strict equivalence.

## Cross-model primary fixed-budget results

All rows use 200 tasks, sample 0, Stage1 2 candidates x 2 repair rounds, and a blocked-external-resource browser audit.

| Model | AlgoTutorGen Machine OK | Direct Machine OK | Difference | 95% paired-bootstrap CI | McNemar p |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash | 196/200 (98.0%) | 118/200 (59.0%) | +39.0 pp | [32.0, 46.0] | 1.02e-20 |
| GLM-5.2 | 170/200 (85.0%) | 35/200 (17.5%) | +67.5 pp | [60.0, 74.5] | 1.48e-34 |
| Kimi-K2.5 | 160/200 (80.0%) | 87/200 (43.5%) | +36.5 pp | [27.5, 45.0] | 1.87e-13 |

Source: `docs/EXPERIMENT_RESULTS.md` Sec. 6.2. The descriptive 526/600 versus 240/600 totals must not be treated as 600 independent observations.

Final-quality results exist after failure-only retry (Flash 200/200 vs 118/200, GLM 196/200 vs 35/200, Kimi 194/200 vs 87/200), but the paper's cross-model comparison should prioritize the uniform primary fixed budget.

## Held-out task generalization

| Metric | AlgoTutorGen | Direct |
|---|---:|---:|
| Generation pass | 39/40 | 40/40 |
| Machine OK | 39/40 | 18/40 |
| Self-contained | 40/40 | 40/40 |

Difference: +52.5 percentage points; 95% paired-bootstrap CI [37.5, 67.5]; exact McNemar p=9.54e-7. The single Stage1 failure was rejected by a strict teaching-feedback warning.

Source: `docs/EXPERIMENT_RESULTS.md` Sec. 6.3 and `output/experiments/algotutorgen_plan_completion_20260713/heldout_40/`.

## Non-degenerate ablations

| Condition | Full | Ablation | Key boundary |
|---|---:|---:|---|
| Direct-to-SceneGraph | 49/50 Machine OK | 1/50 | Fixed runtime without executable trace/validation is insufficient. |
| VerifiedTrace-to-LLM-HTML | 49/50 Machine OK | 0/50 | Correct trace without deterministic compiler/runtime is insufficient; visible answer remains 50/50. |

Direct-to-SceneGraph difference: +96 pp, 95% CI [90,100], exact McNemar p=7.11e-15. Both ablations are 50/50 self-contained under the corrected resource parser.

Source: `docs/EXPERIMENT_RESULTS.md` Sec. 4.

## Browser-repair budget

| Call budget | Machine OK | Average tokens | Average generation time |
|---:|---:|---:|---:|
| 1 | 106/200 | 19.7k | 207.2 s |
| 2 | 10/200 | 36.8k | 347.2 s |
| 3 | 15/200 | 53.7k | 477.6 s |
| 5 | 6/200 | 87.2k | 733.9 s |

All 1,000 attempts were self-contained after the corrected resource parser. The 1-call condition is the best fixed budget. The result supports only that more free-HTML rewrite budget did not monotonically improve this evaluated repair method.

Source: `docs/EXPERIMENT_RESULTS.md` Sec. 8.2.

## Long-trace scalability

| Scale | Mean events/frames | Mean HTML | Mean load | Mean step latency | Mean JS heap |
|---|---:|---:|---:|---:|---:|
| Small | 104.4 | 1.40 MB | 120 ms | 14.7 ms | 6.3 MB |
| Medium | 543.3 | 23.25 MB | 1,933 ms | 45.4 ms | 59.1 MB |
| Large | 1,636.7 | 160.42 MB | 8,354 ms | 101.3 ms | 185.6 MB |

All 54 samples materialized; 52/54 completed browser measurement. KMP large contained 3,063 frames and a 581 MB HTML file; sliding-window unique large contained 5,533 frames and a 1.08 GB HTML file. Both exceeded the 60-second load budget.

Source: `docs/EXPERIMENT_RESULTS.md` Sec. 8.3 and `output/experiments/algotutorgen_plan_completion_20260713/long_trace_scalability/long_trace_scalability_report.json`.

## Secondary visual results

Stage2 versus Direct same-rubric averages:

- overall: 4.611 versus 4.596;
- problem-visual alignment: 4.835 versus 4.825, Holm p=0.856;
- state readability: 4.385 versus 4.505, Holm p=0.059;
- process-transition clarity: 4.320 versus 4.400, Holm p=0.326;
- instructional visual design: 4.905 versus 4.655, Holm p=1.56e-5, rank-biserial 0.624.

Only instructional visual design is significant after Holm correction. Source: `docs/EXPERIMENT_RESULTS.md` Sec. 9.

## Cost boundary

Original DeepSeek-V4-Pro main experiment:

- Stage1 selected-final: 1,066 calls, 15,369,433 tokens;
- Stage1 all attempts: 1,151 calls, 16,870,557 tokens;
- Direct HTML: 222 calls, 4,385,641 tokens;
- Stage1 selected-final averages: 5.33 calls and approximately 76.8k tokens per task;
- Direct averages: 1.11 calls and approximately 21.9k tokens per task.

Source: `docs/EXPERIMENT_RESULTS.md` Sec. 8.1. No model price configuration was frozen, so do not report monetary cost.

## Human-data boundary

The following are prepared but not completed:

- machine-evaluator calibration: 30 tasks x 4 methods = 120 blind pages, pending two human annotators;
- independent trace correctness audit: 40 tasks across 23 families, pending two human reviewers;
- expert study: planned 3 experts x 30 pairs, pending participants;
- student study: planned 24 students x 12 trials, pending participants and any required ethics process.

These materials may be described as future work or prepared protocols. No precision/recall, trace critical-error rate, expert preference, usability, or learning-outcome result may be reported.

Source: `docs/EXPERIMENT_RESULTS.md` Sec. 11.7.
