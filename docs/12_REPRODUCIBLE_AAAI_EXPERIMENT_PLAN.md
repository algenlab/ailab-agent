# 可复现 AAAI 实验收口计划

## 1. 文档定位

本文档把根目录 `suggestion.md` 中的下一步实验建议，落成当前代码库可执行的实验计划。

它不是替代已有文档，而是对已有计划的收口：

- `docs/08_AAAI_EXPERIMENT_PLAN.md`：定义 broad benchmark / baseline / VLM 框架。
- `docs/09_LLM_SUCCESS_REPAIR_PLAN.md`：处理早期真实 LLM 通过率修复。
- `docs/10_RENDERER_VISUAL_OPTIMIZATION_DESIGN.md` 和 `docs/11_RENDERER_FIT_AND_SEMANTIC_UPGRADE_PLAN.md`：处理 renderer 可读性、截图与布局问题。
- `SYSTEM_OVERVIEW.md`：描述当前代码实际架构，包括 DSL-era、`SemanticTrace -> SceneGraph -> HTML`、release gate、以及最新 LLM teaching enrichment。

本文档的目标是：把“当前系统在固定 benchmark 上观察到 100% 通过”整理成 AAAI 审稿人能复核的、分层的、可复现实验证据，而不是继续只扩大算法覆盖数量。

## 2. 对 suggestion.md 的分析结论

`suggestion.md` 的核心判断是正确的：下一阶段不应继续只证明“还能覆盖更多算法”，而应把可靠性 claim 拆成可审计的多层证据。

需要保留的建议：

- 主 claim 应从“算法可视化工具”提升为“LLM 生成可执行算法与可验证语义轨迹，再由确定性编译器生成交互式算法可视化的可靠生成框架”。
- 100% 必须限定在 frozen benchmark、oracle、release gate 和实验协议内。
- direct HTML baseline 必须使用 expected hidden 的公平设置；expected visible 只能作为 leaked / auxiliary baseline。
- 主结果表必须拆分 parse/spec、execution、answer、trace、demo、scene、browser、interaction、cost 等层级。
- 必须补过程正确性审计，因为当前 `process_validator` 已经是 DSL-era 轻量 sanity 层，不再是旧版每算法族手写 invariant 重算。
- teaching overlay 需要单独 ablation：它提升讲解/交互，不应被写成 correctness gate。

需要收紧或调整的地方：

- 关于扩大 benchmark 的建议，本轮收口不采纳。实验固定使用已有 71-case deterministic benchmark；工作重点是把 71/71 的 correctness、visual、teaching、baseline、ablation 和 cost 证据链做完整、可复现、可追溯。
- 当前 `scripts/run_llm_benchmark.py` 构造 `ProblemInput` 时没有打开 `teaching_enrichment`，所以 `output/aaai/llm_algolab_full_*` 主要证明 full pipeline release gate，不代表 LLM teaching overlay 已纳入标准 benchmark。teaching 应作为新 condition 或显式 flag 单独跑。
- 全量 trace teaching enrichment 虽然已经按用户需求实现，但真实 `permutations` 38 帧实验耗时约 512 秒，token 成本很高。论文里应把 full trace vs selected frames 写成质量/成本 trade-off，不应默认承诺所有长 trace 都低延迟。
- 如果引用外部工作和 AAAI deadline，最终论文前必须重新核对官方来源。本文档只把它们作为实验动机，不把外部事实当成本地机器证据。

## 3. 当前本地证据快照

以下是 2026-06-08 工作区里已经存在的主要实验输出。

### 3.1 AlgoLab full pipeline

DeepSeek-V4-Pro:

```text
output/aaai/llm_algolab_full_deepseek_v4_pro_c12_k3_r1_full1/llm_benchmark_report.json
total = 71
passed = 71
failed = 0
pass_rate = 1.0
condition = algolab_full
browser_smoke = true
```

Gemini:

```text
output/aaai/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1/llm_benchmark_report.json
total = 71
passed = 71
failed = 0
pass_rate = 1.0
condition = algolab_full
browser_smoke = true
```

这两份报告是当前“主系统 release-ready generation”最强证据。论文中应写成：

```text
On a frozen 71-task deterministic benchmark, AlgoLab reaches 71/71 release-ready artifacts under the full machine gate.
```

不要写成无边界的“保证所有算法 100% 正确”。

### 3.2 Direct HTML no-expected baseline

DeepSeek-V4-Pro, timeout 1200:

```text
output/aaai/direct_html_no_expected_deepseek_v4_pro_c12_acceptance_prompt_maxtok65536_timeout1200_full1/llm_benchmark_report.json
total = 71
passed = 10
failed = 61
pass_rate = 0.14084507042253522
```

Gemini:

```text
output/aaai/direct_html_no_expected_gemini_3_flash_c12_acceptance_prompt_maxtok65536_full1/llm_benchmark_report.json
total = 71
passed = 65
failed = 6
pass_rate = 0.9154929577464789
```

DeepSeek-V4-Pro, timeout 2400:

```text
output/direct_html_no_expected_deepseek_v4_pro_c12_acceptance_prompt_maxtok65536_timeout2400_full1/llm_benchmark_report.json
total = 71
passed = 13
failed = 58
pass_rate = 0.18309859154929578
```

这些通过率主要是 browser smoke / HTML 可运行口径，不能和 AlgoLab full release gate 直接等价比较。

### 3.3 Direct HTML answer audit

Gemini answer audit:

```text
output/aaai/direct_html_no_expected_gemini_3_flash_c12_acceptance_prompt_maxtok65536_full1_answer_audit/direct_html_answer_audit.json
audited_html = 65
visible_answer_found_rate = 1.0
visible_answer_match_rate = 0.9230769230769231
```

DeepSeek timeout 1200 answer audit:

```text
output/aaai/direct_html_no_expected_deepseek_v4_pro_c12_acceptance_prompt_maxtok65536_timeout1200_full1_answer_audit/direct_html_answer_audit.json
audited_html = 10
visible_answer_found_rate = 1.0
visible_answer_match_rate = 1.0
```

DeepSeek timeout 2400 answer audit:

```text
output/direct_html_no_expected_deepseek_v4_pro_c12_acceptance_prompt_maxtok65536_timeout2400_full1_answer_audit/direct_html_answer_audit.json
audited_html = 13
visible_answer_found_rate = 1.0
visible_answer_match_rate = 0.9230769230769231
```

answer audit 只审计 direct HTML 成功打开的页面里是否能找到可见答案，以及答案是否匹配 expected。它不提供 trace/process/SceneGraph/release gate 证据。

### 3.4 Teaching overlay 实验

全量 trace teaching enrichment:

```text
output/teaching_overlay_visual_check/multi_case_llm/permutations.html
output/teaching_overlay_visual_check/multi_case_llm/permutations.json
output/teaching_overlay_visual_check/multi_case_llm/llm_teaching_report_permutations_all_frames.json
```

结果：

```text
case_id = permutations
frames = 38
teaching_frames = 38
interaction_frames = 7
llm_calls = 2
```

这证明最新 teaching overlay 可以全量读取 trace 并生成讲解/交互，但它还不是 `run_llm_benchmark.py` 的标准 condition。下一轮实验必须把 teaching 纳入可重复 benchmark，而不是只保留临时目录证据。

### 3.5 Renderer visual audit

目录：

```text
output/renderer_visual_audit/
```

用途：

- renderer 视觉质量回归。
- HTML / JSON / screenshots。
- 修复 answer badge、scene badge、graph/tree/trie/math/string 等布局问题过程中的审查证据。

这些是视觉优化证据，不是主 correctness 证据。

## 4. 论文 claim 边界

推荐主 claim：

> AlgoLab decouples LLM generation, executable semantic tracing, deterministic SceneGraph compilation, and browser rendering. On a frozen benchmark of algorithm visualization tasks, it achieves release-ready artifacts under a layered machine gate.

推荐 100% 表述：

> On the frozen 71-task deterministic benchmark, AlgoLab achieves 71/71 release-ready generation under answer, trace, demo, SceneGraph, and browser gates.

禁止表述：

- “系统保证任意算法 100% 正确。”
- “browser smoke 通过等价于算法正确。”
- “VLM 评分证明 correctness。”
- “teaching overlay 证明过程正确。”
- “process validator 是每个算法族的完整手写 invariant proof。”

## 5. 实验矩阵

### 5.1 必跑 conditions

| condition | 目的 | 当前状态 |
|---|---|---|
| `algolab_full` | 主系统 release gate | 已有 DeepSeek/Gemini 71/71 输出，需要重跑 frozen final |
| `algolab_full_teaching_full_trace` | 主系统 + teaching overlay 全量 trace | 只有临时 `permutations` 证据，需要纳入 benchmark |
| `algolab_full_teaching_selected_6` | teaching overlay 选 6 帧摘要 | 需要显式实验，用于质量/成本 trade-off |
| `algolab_full_no_teaching` | teaching ablation | 当前 `run_llm_benchmark.py` 默认近似此条件 |
| `direct_html_no_expected` | 公平 direct HTML baseline | 已有输出，需要固定最终模型/timeout |
| `direct_html_no_expected_answer_audit` | direct HTML 可见答案审计 | 已有输出，需要进入主表 |
| `no_repair` | repair 贡献 | 需要用最新系统复跑 |
| `no_scenegraph_compiler` | SceneGraph 中间表示贡献 | 脚本存在，需要复跑或确认最新输出 |
| `no_process_validator` | process/demo/release gate 贡献 | 脚本存在，需要复跑或确认最新输出 |

### 5.2 建议新增 conditions

| condition | 目的 | 实现建议 |
|---|---|---|
| `raw_event_json` | 验证 DSL 对 trace 正确性的贡献 | 新增 baseline：LLM 直接输出 events JSON，不执行 DSL mutation |
| `direct_scenegraph` | 验证 SceneGraph compiler 的贡献 | 新增 baseline：LLM 直接输出 SceneGraph 或近似 visual spec |
| `trace_replay_audit` | 补强过程正确性 | 新增离线脚本，从 events 重放 before/after/state diff |
| `expert_frame_audit` | 人工或专家审计 | 导出抽样帧和 rubric 表 |

## 6. 主结果表设计

每个 case 一行机器可审计记录，建议输出为：

```text
case_id
sample_index
family_id
subfamily_id
gate_layer
support_level
model
condition
input_size
expected_result
repair_rounds
generation_ok
spec_parse_ok
solve_ok
trace_ok
answer_match
verifier_match
multi_solution_match
process_ready
demo_ready
scene_valid
browser_smoke_ok
interaction_valid
release_ready
num_events
num_frames
teaching_frames
interaction_frames
latency_generate_s
latency_execute_s
latency_teaching_s
latency_render_s
prompt_tokens
completion_tokens
total_tokens
html_size_kb
artifact_size_kb
failure_phase
failure_type
warning_count
strict_warning_count
```

主论文表格应展示分层 gate，而不是只展示一个 pass rate：

| metric | AlgoLab full | AlgoLab + teaching | direct HTML no-expected | no repair | no SceneGraph |
|---|---:|---:|---:|---:|---:|
| spec parse | x/y | x/y | N/A | x/y | x/y |
| execution | x/y | x/y | N/A | x/y | x/y |
| answer correctness | x/y | x/y | visible answer audit | x/y | x/y |
| trace validity | x/y | x/y | N/A | x/y | N/A |
| demo readiness | x/y | x/y | N/A | x/y | N/A |
| scene validity | x/y | x/y | N/A | x/y | x/y |
| browser smoke | x/y | x/y | x/y | x/y | x/y |
| release ready | x/y | x/y | N/A | x/y | x/y |
| avg tokens | ... | ... | ... | ... | ... |
| avg latency | ... | ... | ... | ... | ... |

### 6.1 指标分层

最终实验不能只报告 `passed / total`。每个 case 必须同时记录以下指标，最后再按 condition、model、family 聚合。

### 6.2 覆盖与输入指标

这些指标回答“实验分母是什么”：

| metric | 含义 | 口径 |
|---|---|---|
| `N` | case 总数 | 固定为当前 71-case deterministic benchmark |
| `case_id` | 题目唯一标识 | 不允许实验中途删题或重命名来改变分母 |
| `family_id` / `subfamily_id` | 算法类别 | 用于报告 family-level success，不只看整体均值 |
| `sample_index` | 同一 case 的采样序号 | 主实验建议 sample0；多 sample 只能作为补充 |
| `input_size` | 输入规模 | 用于解释 trace length、latency、HTML size |
| `expected_result` | oracle 期望答案 | 只用于系统验证，不泄露给公平 direct HTML baseline |

### 6.3 生成与解析指标

这些指标回答“LLM 是否生成了可执行规范”：

| metric | 含义 | 失败说明 |
|---|---|---|
| `generation_ok` | LLM 调用是否返回可解析内容 | false 表示超时、API 失败、空输出或格式完全不可用 |
| `spec_parse_ok` | 生成的 solver/tracker/spec 是否通过结构解析 | false 表示代码块、JSON/schema 或入口函数不符合要求 |
| `repair_rounds` | 使用了多少轮自动 repair | 用于证明 repair 的贡献和成本 |
| `failure_phase` | 首个失败阶段 | 建议枚举为 generation、parse、execution、answer、trace、scene、browser、teaching |
| `failure_type` | 更细失败原因 | 例如 timeout、syntax_error、wrong_answer、schema_error、browser_error |

聚合时至少报告：

- `spec_parse_ok / N`
- `generation_ok / N`
- 平均 `repair_rounds`
- failure phase top-k

### 6.4 算法答案正确性指标

这些指标是 correctness 的核心，优先级高于 browser 和截图：

| metric | 含义 | 口径 |
|---|---|---|
| `solve_ok` | 生成 solver 是否成功运行 | 运行失败、异常、超时都算 false |
| `answer_match` | solver 输出是否匹配 expected | 主 correctness 指标之一 |
| `verifier_match` | verifier 或 oracle 是否接受输出 | 用于多格式答案或近似等价答案 |
| `multi_solution_match` | 多解问题是否被 oracle 接受 | 不能只做字符串相等 |
| `expected_visible_to_model` | expected 是否暴露给模型 | direct HTML baseline 必须为 false |

论文中 `answer correctness` 只能来自这些 oracle 级指标，不能来自页面能打开、截图好看或 VLM 评价。

### 6.5 Trace 与过程正确性指标

这些指标回答“过程是不是跟算法执行一致”：

| metric | 含义 | 口径 |
|---|---|---|
| `trace_ok` | trace schema 和基本语义是否通过 | 来自现有 trace / process gate |
| `num_events` | trace event 数量 | 用于解释教学成本和页面复杂度 |
| `num_frames` | SceneGraph frame 数量 | 通常与可视化步骤数对应 |
| `process_ready` | 过程是否足够支撑 demo | 不能等价写成完整算法证明 |
| `demo_ready` | 是否满足可演示 artifact 要求 | release gate 的一部分 |
| `trace_replay_ok` | 离线 replay audit 是否通过 | 新增审计指标，检查 before/after/target/deps/state 一致性 |
| `trace_mutation_detected` | teaching overlay 是否修改 trace facts | 必须为 false |

聚合时至少报告：

- `trace_ok / N`
- `demo_ready / N`
- `trace_replay_ok / N`
- `num_events` 和 `num_frames` 的 mean / p95 / max

### 6.6 SceneGraph、渲染与浏览器指标

这些指标回答“生成结果是否稳定可打开、可读”：

| metric | 含义 | 口径 |
|---|---|---|
| `scene_valid` | SceneGraph schema 是否通过 | full pipeline 和 no-repair 等条件都应记录 |
| `browser_smoke_ok` | HTML 是否能在浏览器中打开并完成 smoke | 必须用容器 Playwright |
| `console_error_count` | 浏览器 console/page error 数量 | release artifact 应为 0 或进入 warning |
| `main_object_visible` | 主可视对象是否可见 | 来自 screenshot audit |
| `overlap_count` | 关键元素重叠数量 | 用于证明视觉改进没有回退 |
| `answer_badge_occlusion` | answer badge 是否遮挡主对象 | 必须单独记录，避免重复标记对象问题回归 |
| `mobile_readable` | mobile 截图是否可读 | 不作为算法 correctness，但作为 artifact 质量 |

Browser pass 只能说明 artifact 可打开，不能单独作为 correctness。

### 6.7 Teaching 与交互指标

这些指标只评估讲解和交互质量，不进入算法 correctness gate：

| metric | 含义 | 口径 |
|---|---|---|
| `teaching_enabled` | 是否启用 LLM teaching enrichment | none/full_trace/6_frames |
| `frames_sent_to_llm` | 送给 LLM 的 trace frame 数 | full trace 为 `len(trace.events)` |
| `teaching_frames` | 最终带讲解的 frame 数 | 衡量覆盖率 |
| `teaching_coverage` | `teaching_frames / num_frames` | full trace 预期更高 |
| `interaction_frames` | 带交互题的 frame 数 | 衡量交互覆盖 |
| `interaction_coverage` | `interaction_frames / num_frames` | 不要求每帧都有交互 |
| `choice_validity` | choice interaction 的答案是否在 options 中 | 必须为 100% |
| `interaction_valid` | 所有交互控件是否可点击且不破坏状态 | browser interaction audit |
| `explanation_duplication_count` | 重复、无意义讲解数量 | 用来检查 answer/current step/why 重复问题 |
| `explanation_groundedness` | 讲解是否只引用当前 trace 事实 | 可由规则、抽样人工或 VLM 辅助审计 |

teaching 表必须同时报告质量收益和成本：更多 frame 讲解不一定等于更优，如果 latency/token 过高，需要在论文里写成 trade-off。

### 6.8 Baseline 与 ablation 专用指标

Direct HTML baseline 不能使用 full pipeline 的 trace/SceneGraph gate，因此要单独报告：

| metric | 含义 |
|---|---|
| `direct_html_browser_ok` | 直接生成 HTML 是否打开成功 |
| `visible_answer_found` | 页面中是否能找到可见答案 |
| `visible_answer_match` | 可见答案是否匹配 expected |
| `trace_available` | direct HTML 通常为 false |
| `scenegraph_available` | direct HTML 通常为 false |
| `release_gate_available` | direct HTML 为 false |

Ablation 必须报告：

| metric | 含义 |
|---|---|
| `release_ready_drop` | 相对 `algolab_full` 的 release-ready 下降 |
| `failure_phase_shift` | 去掉模块后失败集中在哪一层 |
| `browser_ok_but_not_correct` | 能打开但 correctness 不通过的数量 |
| `mean_repair_rounds_delta` | repair ablation 对修复轮数和成功率的影响 |

### 6.9 成本与效率指标

这些指标回答“方法是否可用、是否太贵”：

| metric | 含义 | 聚合 |
|---|---|---|
| `prompt_tokens` | prompt token 数 | mean / p95 / max |
| `completion_tokens` | completion token 数 | mean / p95 / max |
| `total_tokens` | 总 token 数 | mean / p95 / max |
| `llm_calls` | 每个 case 的 LLM 调用次数 | mean / max |
| `latency_generate_s` | 主生成耗时 | mean / p95 |
| `latency_execute_s` | solver/tracker 执行耗时 | mean / p95 |
| `latency_teaching_s` | teaching enrichment 耗时 | mean / p95 / max |
| `latency_render_s` | render/export 耗时 | mean / p95 |
| `html_size_kb` | HTML 体积 | mean / p95 / max |
| `artifact_size_kb` | artifact 总体积 | mean / p95 / max |

teaching full trace 必须额外报告 `num_frames` 与 `latency_teaching_s`、`prompt_tokens` 的关系，防止只报告视觉效果而隐藏长 trace 成本。

### 6.10 最终聚合口径

最终表格至少按三层聚合：

- Overall：71-case 总体 `x/71`。
- Family：每个 major family 的 `x/y`，避免某一类失败被整体均值掩盖。
- Condition：`algolab_full`、`teaching_full_trace`、`teaching_6_frames`、direct HTML、ablation 分开报告。

所有百分比必须同时给出分子和分母，例如 `71/71 (100.0%)`，不能只写百分比。

### 6.11 具体评估方法

本节把核心指标落成实际评估方法。原则是：能由 artifact / report / Playwright 自动计算的指标必须自动计算；需要新增脚本的指标必须输出 case-level JSON/CSV，不能只给口头结论。

#### 6.11.1 算法答案正确性

数据来源：

- `scripts/run_llm_benchmark.py` 生成的 `llm_benchmark_report.json`。
- 每个通过 case 对应的 BuildArtifact JSON，例如 `llm_<case_id>_<sample>.json`。
- `algolab/pipeline.py` 中的 `_try_materialize()`、`execute_variant()`、`run_verifier()`、`results_equivalent()`。

评估方法：

| metric | 自动评估方法 | 通过口径 |
|---|---|---|
| `solve_ok` | 执行 LLM 生成的 `solve(input_data)`，并完成 `execute_variant()` materialization。 | 无异常、无超时、返回 result，且生成可用 trace。 |
| `answer_match` | 用 `results_equivalent(variant.result, expected_result, case_id/family/subfamily)` 比较。 | 所有发布 variant 的 result 都被 expected/oracle 接受。 |
| `verifier_match` | 如果 `verifier_code` 非空，运行 `verify(input_data)` 得到 `verifier_result`，再与 expected 或 solve result 比较。 | 有 expected 时 verifier 必须匹配 expected；无 expected 时 verifier 必须匹配 solve result。 |
| `multi_solution_match` | 当 `--solutions > 1` 时，对所有 good variants 的 result 两两比较。 | 所有解法结果等价；如果主实验 `solutions=1`，该指标记为 `N/A`。 |

case-level 字段建议：

```text
solve_ok
answer_match
verifier_available
verifier_expected_match
verifier_solve_match
multi_solution_applicable
multi_solution_match
answer_correctness_ok
```

`answer_correctness_ok` 的计算：

```text
answer_correctness_ok =
  solve_ok
  AND answer_match
  AND (verifier_available == false OR verifier_expected_match OR verifier_solve_match)
  AND (multi_solution_applicable == false OR multi_solution_match)
```

注意：

- direct HTML baseline 没有 solver/trace/verifier gate，不能填 `answer_correctness_ok`；只能填 `visible_answer_match`。
- verifier 是可执行 oracle，不是形式化证明；论文不能写成 verifier 证明算法正确。
- 如果 `verifier_code` 不存在，`verifier_available=false`，不能把它统计成 verifier failure。

需要补的脚本能力：

```text
scripts/collect_repro_case_metrics.py
```

该脚本读取 benchmark report 和 artifact JSON，把上述字段展开到：

```text
output/repro_aaai_tables/case_metrics.csv
output/repro_aaai_tables/case_metrics.json
```

#### 6.11.2 Trace 与过程正确性

数据来源：

- artifact 中的 `variants[].trace`。
- artifact 中的 `scenes`。
- `artifact.validation.release_gate`。
- `artifact.validation.demo_readiness`。
- `algolab/verification/trace_validator.py`。
- 新增 `scripts/audit_trace_replay_consistency.py`。

评估方法：

| metric | 自动评估方法 | 通过口径 |
|---|---|---|
| `trace_ok` | 对 `variant.trace` 执行 Pydantic schema validation 和 `validate_trace(trace)`。 | 无 trace validation error；warning 单独统计。 |
| `num_events` | `len(variant.trace.events)`。 | 不设 pass/fail，用于长度、成本、复杂度分析。 |
| `num_frames` | `len(scene.frames)`。 | 不设 pass/fail，但应大于 0 且与可视化可导航帧一致。 |
| `process_ready` | 读取 `artifact.validation.release_gate.process_ready`。 | true 表示该 artifact 至少有 expected、verifier 或多解法交叉证据支撑过程发布。 |
| `demo_ready` | 读取 `artifact.validation.demo_readiness.status`。 | `status == "pass"`；`warn` 需要单独记录，不能静默忽略。 |
| `trace_replay_ok` | 新增离线 replay audit，从 event state 和 before/after 重放一致性。 | 每个 event 零错误；任何 target/value/state 不一致都算该 case 失败。 |
| `trace_mutation_detected` | teaching enrichment 前后对 `trace.model_dump()` 做 stable JSON hash。 | 必须为 false。 |

`trace_replay_ok` 的具体检查：

```text
for each event:
  1. event.step == index
  2. event.targets / event.deps can be resolved from input_data or event.state
  3. event.before equals the target value in previous event.state, if before is present
  4. event.after equals the target value in current event.state, if after is present
  5. event.value is consistent with event.after or with role=answer/mark semantics, if applicable
  6. event.state is JSON-serializable and stable under canonicalization
  7. answer-like event is consistent with trace.result and state["answer"] / state["result"], if present
```

新增脚本输出：

```text
output/repro_aaai_r5_trace_replay_audit/trace_replay_audit.json
output/repro_aaai_r5_trace_replay_audit/trace_replay_audit.csv
output/repro_aaai_r5_trace_replay_audit/trace_replay_audit.md
```

case-level 字段建议：

```text
trace_schema_ok
trace_warning_count
num_events
num_frames
process_ready
demo_ready
demo_status
demo_warning_count
trace_replay_ok
trace_replay_error_count
trace_replay_failure_step
trace_mutation_detected
```

重要边界：

- 当前 `process_validator` 是 DSL-era 轻量 sanity 层，不能单独写成“每个算法族均有完整 invariant proof”。
- `trace_replay_ok` 是补强过程一致性的独立 audit，不替代 answer oracle。
- teaching overlay 只能修改 SceneGraph 的 teaching/interaction 字段，不能改变 trace facts。

#### 6.11.3 SceneGraph、渲染与浏览器

数据来源：

- artifact 中的 `scenes`。
- `algolab/verification/scene_validator.py`。
- `scripts/run_llm_benchmark.py` 的 `browser_smoke`。
- `tests/browser_smoke.py`。
- `scripts/audit_renderer_visual_quality.py`。

评估方法：

| metric | 自动评估方法 | 通过口径 |
|---|---|---|
| `scene_valid` | 对每个 SceneGraph 执行 `validate_scene(scene)`。 | 无 scene validation error；warning 单独统计。 |
| `browser_smoke_ok` | 容器 Playwright 打开 HTML，检查 title/counter/canvas 和 JS error。 | 页面打开成功，canvas 非空，无 console/page error。 |
| `console_error_count` | Playwright 监听 `console.error` 和 `pageerror`。 | release artifact 目标为 0。 |
| `main_object_visible` | `audit_renderer_visual_quality.py` 抽 first/middle/last 帧测量 rendered objects、primary visible ratio、clip。 | 主对象非空、未严重裁剪、active target 可见。 |
| `overlap_count` | 统计遮挡/裁剪类 failure categories。 | `fixed_overlay_blocks_primary`、`primary_clip_detected`、`svg_internal_clip` 等为 0。 |
| `answer_badge_occlusion` | 检查 answer badge / answer-like object 与 primary scene 的面积占比和相交。 | 不遮挡 primary scene；`answer_primary_area_ratio <= 0.35`。 |
| `mobile_readable` | Playwright 切到 `390x820`，检查无水平溢出、canvas 和控件可见。 | 无 horizontal overflow，主视图和控制区可用。 |

浏览器必须使用容器命令：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/audit_renderer_visual_quality.py \
  --artifact-dir output/repro_aaai_r1_algolab_full_deepseek \
  --output-dir output/repro_aaai_r6_visual_audit_algolab_full \
  --capture-screenshots
```

`audit_renderer_visual_quality.py` 已有的关键字段：

```text
canvas_has_rendered_objects
rendered_object_count
primary_visible_ratio
primary_clip_detected
active_target_visible
answer_primary_area_ratio
fixed_overlay_blocks_primary
svg_internal_clip_count
no_major_overflow
family_renderer_used
failure_categories
ok
```

建议把文档里的 `overlap_count` 落成以下派生字段：

```text
overlap_or_occlusion_count =
  count(failure_categories in {
    "fixed_overlay_blocks_primary",
    "primary_clip_detected",
    "primary_visible_ratio_low",
    "answer_steals_primary",
    "svg_internal_clip",
    "semantic_anchor_clipped"
  })
```

case-level 字段建议：

```text
scene_valid
scene_warning_count
browser_smoke_ok
console_error_count
page_error_count
main_object_visible
primary_visible_ratio_min
primary_clip_count
overlap_or_occlusion_count
answer_badge_occlusion
answer_primary_area_ratio_max
mobile_readable
visual_audit_ok
visual_failure_categories
```

完整 browser interaction smoke 还应跑：

```bash
bash scripts/run_browser_smoke_container.sh
```

它会执行 `tests.browser_smoke.run_all()`，覆盖 next/prev/range/timeline/debug drawer、choice/input/judge feedback、以及交互不修改 trace。

重要边界：

- `browser_smoke_ok` 只证明 artifact 可打开，不证明算法答案正确。
- `main_object_visible`、`mobile_readable` 是 artifact quality，不进入 correctness gate。
- 如果 visual audit 失败，不能通过隐藏元素、放宽阈值或跳过截图来提高结果。

#### 6.11.4 Teaching 与交互

数据来源：

- `algolab/generation/teaching_enricher.py`。
- teaching benchmark report。
- enriched SceneGraph 的 `frames[].teaching` 和 `frames[].interaction`。
- 浏览器 interaction audit。
- 新增 `scripts/audit_teaching_interaction_quality.py`。

评估方法：

| metric | 自动评估方法 | 通过口径 |
|---|---|---|
| `teaching_enabled` | 从 condition 或 `ProblemInput.teaching_enrichment` 记录。 | 取值固定为 `none`、`full_trace`、`6_frames`。 |
| `frames_sent_to_llm` | 记录 `select_teaching_events(trace, max_frames)` 的返回长度。 | full trace 等于 `len(trace.events)`；6 frames 不超过 6。 |
| `teaching_frames` | 统计 `frame.teaching` 中 `what` 或 `why` 非空的帧数。 | 不要求 100%，但必须报告覆盖率。 |
| `teaching_coverage` | `teaching_frames / num_frames`。 | full trace 预期高于 no teaching / 6 frames。 |
| `interaction_frames` | 统计 `frame.interaction` 非空的帧数。 | 不要求每帧都有交互，但必须报告分子分母。 |
| `interaction_coverage` | `interaction_frames / num_frames`。 | 用于比较 none/full_trace/6_frames。 |
| `choice_validity` | 静态检查 choice 的 options、answer、prompt、option_explanations。 | `answer` 必须是 options 原文，目标 100%。 |
| `interaction_valid` | 浏览器中真实点击 choice/input/judge，并比较点击前后 `JSON.stringify(frames())`。 | 有反馈，正确答案反馈正确，交互不修改 trace/result。 |
| `explanation_duplication_count` | 规则检查 teaching/current step/why/answer/interaction 文案重复。 | 越低越好；重复完全相同或高相似度记 1。 |
| `explanation_groundedness` | 规则抽取讲解中的数字、变量、target、answer-like 结论，并在当前 trace frame 中找证据。 | 无 unsupported claim。 |

choice 静态检查规则：

```text
for each frame.interaction where type == "choice":
  1. prompt is non-empty
  2. options is a non-empty list
  3. answer exactly equals one option string after normalization
  4. option_explanations keys, if present, must map to existing options
  5. wrong_explanation must not contradict answer
```

浏览器交互检查规则：

```text
for each interactive frame:
  before = JSON.stringify(frames())
  perform user action:
    choice: click one option
    input: fill interaction.answer and submit
    judge: click the expected true/false button
  assert feedback is visible
  assert JSON.stringify(frames()) == before
  assert result/debug release gate remains unchanged
```

重复讲解检查规则：

```text
normalize(text):
  lower-case
  remove whitespace and punctuation
  remove boilerplate prefixes such as "当前步骤", "为什么", "答案", "结果"

for each frame:
  compare {
    frame.title,
    frame.operation,
    teaching.what,
    teaching.why,
    teaching.hint,
    interaction.prompt,
    interaction.explanation,
    top answer/result text
  }
  exact normalized match => duplication_count += 1
  similarity >= 0.85 => duplication_count += 1
```

groundedness 检查规则：

```text
evidence pool for a frame =
  frame.state
  frame.evidence.targets
  frame.evidence.deps
  frame.evidence.value
  frame.evidence.before
  frame.evidence.after
  trace.events[step].reason
  trace.result
  previous/current/next event summaries

extract from teaching/interaction:
  numbers
  quoted strings
  variable names such as dp/dist/parent/visited/path/answer/result
  target-like ids such as arr[2], node:A, edge:A->B
  answer-like conclusions

unsupported_claim_count =
  extracted facts not found in evidence pool after canonical normalization
```

case-level 字段建议：

```text
teaching_enabled
teaching_mode
frames_sent_to_llm
teaching_frames
teaching_coverage
interaction_frames
interaction_coverage
choice_count
choice_valid_count
choice_validity
interaction_valid
interaction_trace_mutation_count
explanation_duplication_count
unsupported_claim_count
explanation_groundedness
teaching_audit_ok
```

新增脚本输出：

```text
output/repro_aaai_r2_teaching_full_trace/teaching_metrics.json
output/repro_aaai_r2_teaching_full_trace/teaching_metrics.csv
output/repro_aaai_r2_teaching_full_trace/teaching_quality_audit.json
output/repro_aaai_r2_teaching_full_trace/teaching_quality_audit.md
```

重要边界：

- teaching 指标只评估讲解/交互质量，不进入 answer correctness。
- full trace condition 的 `frames_sent_to_llm` 不限制为 6；必须记录真实 `len(trace.events)`。
- 如果 teaching LLM 失败并 fallback 到 3 frames，report 中必须记录 `teaching_fallback_used=true`，不能混入 full trace 成功组。

## 7. Teaching overlay 专项实验

### 7.1 实验问题

RQ-T1：全量 trace teaching 是否显著增加 teaching/interaction coverage？

RQ-T2：全量 trace teaching 相比 6 帧摘要，是否提升解释质量或交互质量？

RQ-T3：全量 trace teaching 的 token / latency 成本是否可接受？

RQ-T4：teaching overlay 是否保持 trace immutability，即不修改 operation/state/result/evidence？

### 7.2 条件

| condition | trace frames sent to LLM | expected |
|---|---:|---|
| `no_teaching` | 0 | 只有 scene compiler fallback teaching |
| `teaching_full_trace` | `len(trace.events)` | 更多 step-level teaching，更多 interaction，成本最高 |
| `teaching_6_frames` | up to 6 scored frames | 低成本关键帧教学 |
| `teaching_3_frames` | up to 3 scored frames | fallback / budget baseline |

### 7.3 需要的代码入口

当前 `ProblemInput` 已有：

```text
teaching_enrichment: bool
```

但 `scripts/run_llm_benchmark.py` 的 `make_request()` 当前没有打开该字段，也没有暴露 `max_teaching_frames`。下一轮需要：

1. 给 `run_llm_benchmark.py` 增加参数：

```text
--teaching-enrichment / --no-teaching-enrichment
--teaching-max-frames full|6|3
```

2. 或新增专门实验脚本：

```text
scripts/run_teaching_enrichment_benchmark.py
```

3. 报告中增加：

```text
teaching_enabled
teaching_max_frames
teaching_llm_calls
teaching_prompt_tokens
teaching_completion_tokens
teaching_duration_s
teaching_frames
interaction_frames
choice_answer_problems
trace_mutation_detected
```

### 7.4 验收

- `trace.model_dump()` 在 enrichment 前后完全一致。
- SceneGraph 中只有 `frame.teaching` / `frame.interaction` 被 overlay 修改。
- choice interaction 的 `answer` 必须匹配 options 原文。
- browser smoke 中点击 quiz 不修改 trace/result。
- full trace condition 至少在 71-case sample0 上报告成功率、平均 token 和平均耗时。

## 8. 过程正确性审计

当前系统说明已经明确：DSL-era `process_validator` 是轻量 sanity 层。为了让论文中的“过程正确”更可信，必须增加独立 audit。

### 8.1 Trace replay consistency

新增脚本建议：

```text
scripts/audit_trace_replay_consistency.py
```

检查：

- 每个 event 的 `targets` 能从 state/input 定位。
- `before` 与上一帧 state 对应 target 一致。
- `after` 与当前帧 state 对应 target 一致。
- `value` 与 `after` 或 mark role 一致。
- `deps` 指向已存在对象。
- answer event 的 value/result/state answer 一致。

输出：

```text
trace_replay_audit.json
trace_replay_audit.csv
trace_replay_audit.md
```

### 8.2 Reference trace audit

选 50-100 个代表 case，建立 deterministic reference tracer 或 fixture 关键状态。

比较：

- 最终答案。
- 关键变量序列，例如 `dp`、`dist`、`parent`、`visited`、`stack`。
- 必须出现的关键事件类型，例如 relax、push/pop、union、recursive enter/exit。

这不是为了替代主 pipeline，而是补强“过程不是瞎编”的证据。

### 8.3 Expert frame audit

抽样策略：

- 每个 major family 抽 3-5 个 case。
- 每个 case 抽 first / middle / last / answer / high-risk 5 帧。
- 两名算法背景标注者盲审。

rubric：

| item | scale | question |
|---|---:|---|
| step correctness | 1-5 | 当前步骤是否符合算法？ |
| state faithfulness | 1-5 | 可视状态是否忠实反映 trace？ |
| highlight correctness | 1-5 | target/deps 高亮是否指向正确对象？ |
| explanation faithfulness | 1-5 | 讲解是否只解释已有事实？ |
| interaction relevance | 1-5 | 交互题是否与当前步骤相关？ |

报告：

- 平均分。
- family-level 分数。
- annotator agreement。
- 争议样例和失败截图。

## 9. 视觉和交互质量实验

机器 gate 通过后，还需要证明页面可教学、可读、可交互。

### 9.1 Browser screenshot audit

使用容器 Playwright，不直接使用宿主机 Playwright：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/audit_renderer_visual_quality.py ...
```

指标：

- canvas 非空。
- 主对象可见。
- 元素重叠数量。
- answer badge 不遮挡主结构。
- semantic target/deps 可见。
- desktop/mobile 截图都可读。

### 9.2 Interaction audit

检查：

- next / prev / play / range。
- solution tabs。
- quiz choice/judge/input。
- wrong answer feedback。
- formula expander。
- debug drawer。
- 点击对象显示 dependency detail。
- 所有交互不修改 trace/result。

### 9.3 VLM screenshot review

VLM 只评估视觉/教学，不判断答案正确。

rubric：

| dimension | meaning |
|---|---|
| layout readability | 是否有重叠、裁剪、主结构不可读 |
| algorithm state visibility | 当前状态是否清楚 |
| semantic highlight | target/deps 是否可见 |
| explanation clarity | 讲解是否具体 |
| interaction discoverability | 交互是否明显 |
| evidence alignment | 画面、讲解、状态面板是否一致 |

禁止：

- 用 VLM 分数替代 answer correctness。
- 让 VLM 读取源码或判断隐藏状态。

## 10. 执行阶段

### R0：冻结实验版本和输出口径

状态：待执行。

目标：

- 确定代码 commit / dirty diff snapshot。
- 冻结 71-case deterministic benchmark。
- 写出 experiment manifest。
- 明确所有 condition、模型、timeout、max_tokens、concurrency。

产物：

```text
output/repro_aaai_r0_manifest/experiment_manifest.json
output/repro_aaai_r0_manifest/experiment_manifest.md
```

验收：

- manifest 中记录所有输入 case、sample_index、expected、family/subfamily、脚本命令、模型配置。

### R1：重跑 full pipeline final

状态：待执行。

目标：

- 用最新代码重跑 `algolab_full`。
- 确认 71/71 是否仍成立。
- browser smoke 必须开启。

命令模板：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/run_llm_benchmark.py \
  --output-dir output/repro_aaai_r1_algolab_full_deepseek \
  --condition algolab_full \
  --case-set deterministic \
  --max-rounds 1 \
  --timeout-s 1200 \
  --browser-smoke \
  --concurrency 12
```

验收：

```text
total = 71
passed = 71
failed = 0
browser_failed = 0
```

### R2：teaching overlay benchmark

状态：待执行。

目标：

- 把 teaching enrichment 纳入标准 benchmark。
- 至少跑 `no_teaching`、`teaching_full_trace`、`teaching_6_frames`。
- 报告讲解帧、交互帧、token、latency、失败/降级次数。

前置开发：

- 给 benchmark 脚本增加 teaching 参数，或新增 teaching benchmark 脚本。
- 增加 report schema 和 regression test。

验收：

- 71-case sample0 都有报告行。
- full trace condition 不修改 trace facts。
- choice answer problems 为 0。
- 生成 contact sheet 或抽样截图。

### R3：direct HTML no-expected final baseline

状态：待执行。

目标：

- 固定模型和 timeout，重跑 direct HTML expected hidden。
- 跑 answer audit。

命令模板：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/run_direct_html_baseline.py \
  --hide-expected \
  --output-dir output/repro_aaai_r3_direct_html_no_expected \
  --timeout-s 1200 \
  --browser-smoke \
  --concurrency 12

/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/audit_direct_html_answer.py \
  --report output/repro_aaai_r3_direct_html_no_expected/llm_benchmark_report.json \
  --output-dir output/repro_aaai_r3_direct_html_no_expected_answer_audit
```

验收：

- report 记录 browser pass。
- answer audit 记录 visible answer found / match。
- 主文明确 direct HTML 不具备 trace/process/SceneGraph gate。

### R4：已有 ablation final

状态：待执行。

目标：

- 重跑 no repair。
- 重跑 no process validator。
- 重跑 no SceneGraph compiler。
- 合并 failure summary。

验收：

- 每个 condition 有真实不同执行路径。
- browser smoke 开启。
- 不把 ablation 通过率冒充 full pipeline。

### R5：trace replay / process audit

状态：待执行。

目标：

- 新增并运行 trace replay consistency audit。
- 至少覆盖 full pipeline 成功 artifact。

验收：

- 输出 json/csv/md。
- 每个 failure 有 case_id、step、target、reason。
- 主表新增 trace replay pass rate。

### R6：visual / interaction audit final

状态：待执行。

目标：

- 对 full pipeline 和 teaching condition 生成截图。
- 跑 renderer visual audit。
- 跑 interaction audit。
- 可选跑 VLM screenshot review。

验收：

- desktop/mobile 截图可打开。
- browser console/page error 为 0。
- 交互不修改 trace/result。
- VLM 只作为教学质量，不进入 correctness gate。

### R7：paper table / artifact package

状态：待执行。

目标：

- 生成论文主表、baseline 表、ablation 表、teaching 表、cost 表。
- 打包可复现 artifact。

产物：

```text
output/repro_aaai_tables/
output/repro_aaai_package/
```

验收：

- 每个表格都有生成脚本。
- 每个数字可追溯到 report JSON。
- README 写清楚复现命令和环境。

## 11. 推荐最终表格

### Table 1：Release gate cascade

列：

```text
condition
model
N
spec_parse
execution
answer
trace_schema
demo_ready
scene_valid
browser_smoke
release_ready
```

### Table 2：Baseline comparison

列：

```text
condition
browser_ok
visible_answer_found
visible_answer_match
trace_available
scenegraph_available
release_gate_available
```

### Table 3：Ablation

列：

```text
condition
release_ready
failure_phase_top1
failure_phase_top2
browser_ok
mean_repair_rounds
```

### Table 4：Teaching overlay

列：

```text
condition
frames_sent_to_llm
teaching_frames
interaction_frames
choice_validity
trace_mutation
prompt_tokens
completion_tokens
latency_s
browser_ok
```

### Table 5：Cost

列：

```text
condition
mean_prompt_tokens
mean_completion_tokens
mean_latency_s
p95_latency_s
mean_html_kb
mean_artifact_kb
```

## 12. 最小投稿实验组合

如果时间非常紧，最小组合是：

1. 最新代码重跑 `algolab_full` 71-case，browser smoke 开启。
2. 重跑 direct HTML no-expected，并跑 answer audit。
3. 重跑 no repair / no SceneGraph / no process validator 三个 ablation。
4. 跑 teaching overlay 3 条件：none / full trace / 6 frames。
5. 跑 trace replay audit。
6. 生成 desktop 截图和 renderer visual audit。
7. 把所有数字落到统一 CSV / JSON / Markdown 表。

## 13. 执行约束

执行 AI 必须遵守：

- Python 固定使用 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3`。
- 浏览器命令固定走 `bash scripts/run_browser_smoke_container.sh`。
- 不修改 expected output。
- 不删除失败 case。
- 不跳过失败 family。
- 不放宽 validator、oracle、demo readiness 或 browser smoke 来提高通过率。
- 不把 direct HTML browser pass 当成 correctness。
- 不把 VLM 分数当成机器 gate。
- 不提交 API key。
- 如果实验失败，保留 failed JSON 和 failure summary。

## 14. 最终论文叙述建议

论文中最稳的三句话：

1. End-to-end LLM visualizers entangle algorithm execution, visual layout, and pedagogy, causing hallucinated states and unstable demos.
2. AlgoLab decouples these concerns: LLMs generate executable solvers and DSL traces; deterministic validators and compilers transform verified traces into interactive visualizations.
3. Correctness is not judged from pixels or browser success; it is enforced by answer oracles, executable traces, schema validation, release gates, and artifact-level evidence.

中文对应：

1. 端到端 LLM 可视化把算法执行、布局和教学解释混在同一次生成里，容易产生幻觉状态和不稳定页面。
2. AlgoLab 将这些职责拆开：LLM 生成可执行解法和 DSL trace，系统通过确定性校验器和编译器把已验证 trace 转成交互式可视化。
3. 正确性不从截图或 browser pass 判断，而由答案 oracle、可执行 trace、schema validation、release gate 和 artifact 级证据共同约束。
