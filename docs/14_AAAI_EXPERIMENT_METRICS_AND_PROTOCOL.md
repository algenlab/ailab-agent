# AAAI 实验指标与评估协议

## 0. 文档定位与本次重写说明

本文档是 AlgoLab 投稿 AAAI 的**可执行实验方案与评估协议总纲**。它在原 v1（仅整理指标口径）基础上重写，目标是给出一套从研究问题 → 实验条件 → 指标定义 → 评估工具（机器 gate / LLM judge / VLM judge / 人工盲评）→ 统计方法 → 论文表格的端到端方案。

它补充并收口以下文档，发生冲突时**以本文档为准**：

- `docs/06_EVALUATION_AND_BENCHMARK.md`：评估目标、benchmark 分层、基础指标。
- `docs/08_AAAI_EXPERIMENT_PLAN.md`：AAAI 实验矩阵、VLM 边界、baseline/消融框架。
- `docs/12_REPRODUCIBLE_AAAI_EXPERIMENT_PLAN.md`：frozen benchmark 可复现收口。
- `docs/13_LLM_DIRECT_VISUAL_RENDERER_DESIGN.md`：Stage2 Creative View 展示层实验。
- `SYSTEM_OVERVIEW.md`：当前代码实际架构与实验边界。

本文档**不新增系统能力，不改变 benchmark 口径**。它要明确：

1. 每个实验回答什么研究问题（RQ）。
2. 每类指标如何定义、聚合、解释。
3. 哪些指标可支撑 correctness claim，哪些只能用于 visual/teaching quality。
4. 用 LLM/VLM 做评估时如何控制偏差，使评分可信。
5. baseline、ablation、跨模型泛化、人工评估如何组织。
6. 当前 `output/aaai` 结果如何写入论文。

## 1. 投稿前必须正视的方法论风险（先读这一节）

这些是 AAAI 审稿人最可能攻击的点，实验设计的首要目标就是提前堵住它们。每条都给出**风险**与**本方案的对策**。

### R1. “71/71 = 100%” 在自建 frozen benchmark 上极可疑

- 风险：审稿人会认为 benchmark 是为了通过而设计的（benchmark overfitting），100% 不可信。
- 对策：
  1. 主 claim 严格限定为 “on the frozen benchmark, under the layered machine gate”，不外推到任意算法。
  2. **必须**增加 unseen split（见 §8）并报告其通过率——unseen 上不应是 100%，正是诚实性的体现。
  3. 报告 first-try（无 repair）通过率，把 100% 拆成 “first-try x/71 + repair 后 71/71”，让 repair 的贡献可见，避免 100% 看起来像零成本。
  4. 公开 benchmark 构造规则、family 分布、来源，证明不是挑出来的易题。

### R2. process_validator 已退化为轻量 sanity 层，但旧文档把它写成核心贡献

- 事实：`SYSTEM_OVERVIEW.md` §2 明确 `algolab/verification/process_families/*` 已删除，5500+ 行算法族手写 invariant 不再维护，`process_validator.py` 当前是 DSL-era 轻量 sanity 层。
- 风险：若论文宣称 “Process Invariant Validator” 为核心贡献，与代码事实不符，是诚信问题。
- 对策：
  1. 论文对 process 校验的表述降级为 “lightweight structural/process sanity checks + family registry coverage tagging”，不宣称形式化算法不变量证明。
  2. 真正可强力支撑 correctness 的是 **executable oracle**（solve / trace.result / verifier 三方一致）和 **trace replay audit**（§5.4），论文 correctness 叙事应以这两者为核心，而非 process invariant。
  3. `no_process_validator` 消融用于量化这层 sanity check 还剩多少边际贡献；若贡献很小要如实报告，并把它定位为“低成本早停 + 失败定位”而非“正确性保证”。

### R3. 单模型、单次运行，缺乏泛化与统计显著性

- 风险：只用 `deepseek-v4-pro` 跑一次，审稿人质疑结论是否依赖特定模型、是否可复现。
- 对策：
  1. 跨模型泛化实验（§7.3）：至少 3 个异构模型家族跑 Stage1 主链路。
  2. 多次重复 + 方差报告（§11）：主条件至少 3 次独立运行，报告 mean ± std 与 95% CI；条件间比较用配对检验。

### R4. 用 LLM/VLM 当裁判存在自评偏差

- 风险：生成模型与裁判模型同源会自抬分；位置偏差、长度偏差、自一致性差。
- 对策：见 §9 LLM/VLM-as-judge 协议——裁判与生成模型解耦、双向位置随机化、与人工评分做相关性校准、报告裁判自身可靠性（自一致性、与人类 agreement）。LLM/VLM 评分**永远不进入 correctness gate**，只作为 teaching/visual quality 的辅助证据。

### R5. baseline 不公平或不可比

- 风险：direct HTML baseline 没有 oracle/trace/gate，若直接用 “release pass rate” 对比会不公平地碾压 baseline，反而显得在操纵。
- 对策：baseline 与 AlgoLab 只在**共同可观测维度**上比较（visible answer 正确性、browser 可运行性、teaching 质量盲评），不把 AlgoLab 的 release gate 强加给 baseline；并明确 baseline 用 `--hide-expected` 公平模式（§10）。

## 2. 核心实验主张

推荐主 claim：

```text
AlgoLab decouples LLM generation, executable semantic tracing,
deterministic SceneGraph compilation, and browser rendering. On a frozen
benchmark of algorithm visualization tasks, it produces release-ready,
process-auditable, interactive artifacts under a layered machine gate, at
a controlled token cost, and generalizes across LLM backends and to an
unseen task split.
```

推荐 100% 表述（严格限定）：

```text
On the frozen 71-task seen benchmark, AlgoLab achieves 71/71 release-ready
artifacts under answer, trace, demo, SceneGraph, and browser gates;
first-try pass rate is X/71, and the remaining cases reach release after
bounded repair.
```

禁止表述：

- 系统保证任意算法题 100% 正确。
- browser smoke / VLM 截图 / Stage2 Creative View 成功 = 算法 correctness。
- direct HTML baseline 的 browser pass 可与 AlgoLab release gate 直接等价比较。
- process_validator 等价于每个算法族都有形式化证明。
- LLM/VLM 裁判分数证明 correctness。

## 3. 研究问题与实验映射

| RQ | 研究问题 | 主实验 | 主指标 | 评估工具 |
|---|---|---|---|---|
| RQ1 | LLM 生成的算法语义候选能否被系统验证并发布为正确产物？ | Stage1 主实验（§7.1） | `answer_correctness_ok`、`final_release_pass_rate` | 机器 oracle gate |
| RQ2 | 过程轨迹是否忠实可信，而非仅结果正确？ | Stage1 + trace replay 三方法（§5.4 / §15.4） | `trace_replay_independent_ok`、`dom_fidelity_ok`、`metamorphic_consistency_rate`、`process_pass_rate` | 机器独立重执行差分 + DOM-vs-JSON 保真差分 + 变形测试（LLM 过程忠实度评分降级为 teaching 可读性，**不进** RQ2 证据，见 §15.0/§15.4） |
| RQ3 | 解耦式架构相对端到端 LLM 生成有何优势？ | Baseline 对比（§10） | 共同维度对比表 | 机器 + answer audit + 盲评 |
| RQ4 | 各模块（repair / process / SceneGraph / teaching）贡献多大？ | Ablation（§7.2） | `release_ready_drop`、`failure_phase_shift` | 机器 gate |
| RQ5 | 结论是否跨 LLM backend 泛化、是否对 unseen 任务泛化？ | 跨模型 + unseen（§7.3, §8） | per-model / unseen pass rate | 机器 gate |
| RQ6 | 生成页面的教学与可视化质量如何？感知质量 + 教学功效双轨 | Teaching quality 评估（§9 感知质量）+ SLCG 教学功效实验（§15.15，本方案核心创新） | 感知：VLM rubric 分、人工盲评；功效：`visualization_gain` / `teaching_gain` / `interaction_gain` / `semantic_gain` 与学习曲线斜率 | 感知：VLM judge + 人工（裁判-生成解耦 + 偏差控制）；功效：机器出题/判分的 instance-specific probe（预测 / 反事实 / 追溯）+ C0/C1/C2/C2′ 条件矩阵 + 弱模型学生面板 + 人类小样本校准（无 LLM judge） |
| RQ7 | 方法成本是否可接受？ | 成本表（§6） | token / call / duration per success | 日志统计 |

论文叙事核心：AlgoLab 的贡献不是“生成更好看的网页”，而是把 LLM 生成拆成**可执行算法语义 + 可验证 trace + 确定性可视化编译 + 真实浏览器发布门禁**，从而把算法可视化生成从“看起来合理”变成“结果可验证、过程可审计、产物可复现”。

## 4. 实验分层与 Benchmark 分母

### 4.1 Stage1: verified generation（主 correctness 实验）

LLM 只生成 solver / tracker / verifier spec；系统负责 materialize、repair、trace validation、process/demo gate、SceneGraph compile、HTML render、browser smoke。这是论文主 correctness 证据。

当前最终结果（`output/aaai/stage1_final/reports/llm_benchmark_report_effective_71_71.json`）：

```text
total = 71, passed = 71, failed = 0, pass_rate = 1.0, browser smoke = 71/71
```

注意：effective report 替换了 `lca[0]` retry 后的结果。报告 repair 统计时**优先按最终 per-result `candidate_summary` 重新聚合**，或明确说明顶层 `candidate_selection` 来自合并前主报告。

### 4.2 Stage2: creative visual renderer（展示层实验，非 correctness gate）

读取已通过 Stage1 release gate 的 verified artifact，由 LLM 生成 creative/stage visual HTML。

当前结果（`output/aaai/stage2_final/creative_benchmark_report_merged.json`）：

```text
total_artifacts=71, creative_attempted=71, browser_smoke_ok=71,
strict_visual_quality_ok=59, strict_visual_quality_flagged=12,
manual_visual_acceptable=71
```

论文写法：strict geometry audit 是刻意保守的；同时报告自动 strict 分数与对全部 flagged case 的人工 Playwright 复审结论，12/12 flagged 经人工判为非阻塞性的自动审计误报。**不可**写成 “Stage2 pass rate = 59/71”，也**不可**写成 “Creative View proves correctness”。

### 4.3 Benchmark 分母

| 层级 | 数量 | 用途 |
|---|---:|---|
| all deterministic cases | 71 cases / 259 samples | 总覆盖清单（seen） |
| `family_core` | 62 cases / 222 samples | 算法族核心门禁 |
| `expansion` | 9 cases / 37 samples | 复杂变体与覆盖扩展 |
| Stage1 LLM primary setting | 71 cases / sample 0 | 真实 LLM 主实验（seen） |
| **unseen split** | 见 §8 | 泛化主证据，**不属于 frozen seen 71** |
| Stage2 creative setting | 71 verified artifacts | 展示层实验 |

所有百分比必须同时给分子和分母，如 `71/71 (100.0%)`、`59/71 (83.1%)`，不能只写百分比。

## 5. 主指标体系（机器 gate）

机器 gate 是 correctness 的**唯一权威来源**，优先级高于 browser smoke、截图、LLM/VLM 分数。

### 5.1 覆盖与输入指标

回答“分母是什么”：`N`、`case_id`、`sample_index`、`family_id`、`subfamily_id`、`gate_layer`、`case_set`、`case_style`。
聚合：Overall `x/71`；Family per-family `x/y`；gate layer 分开；case style（seen/unseen）分开。
约束：实验中途不得删题/改名/改变分母。

### 5.2 LLM 生成与解析指标

回答“模型是否生成了可执行规范”：`generation_success_rate`、`spec_parse_ok`、`materialization_success_rate`、`materialize_attempts`、`failure_phase`、`failure_type`。
读取自 `run_llm_benchmark.py` 报告：`total`、`passed`、`failed`、`failure_summary`、`results[].failure_type`、`results[].last_phase`、`candidate_selection.materialize_attempts`。

### 5.3 算法答案正确性指标（correctness 核心）

| 指标 | 含义 | 通过口径 |
|---|---|---|
| `solve_ok` | solver 成功运行 | 无异常/超时，返回 result |
| `answer_match` | solver result 与 expected/oracle 等价 | `results_equivalent(...)` 通过 |
| `trace_result_match` | `trace.result` 与 solver result 等价 | 防 trace 与答案不一致 |
| `verifier_match` | verifier/oracle 接受输出 | verifier 与 expected 或 solve result 一致 |
| `multi_solution_match` | 多候选解等价 | `--solutions > 1` 时适用 |
| `answer_correctness_ok` | 答案侧综合通过 | 见下式 |

```text
answer_correctness_ok =
  solve_ok AND answer_match AND trace_result_match
  AND (verifier_available == false OR verifier_match)
  AND (multi_solution_applicable == false OR multi_solution_match)
```

Direct HTML baseline 无 solver/trace/verifier gate，**不能**填 `answer_correctness_ok`，只能单独报告 `visible_answer_found` / `visible_answer_match` / `direct_html_browser_ok`（由 `scripts/audit_direct_html_answer.py` 产出）。

### 5.4 Trace 与过程正确性指标

| 指标 | 含义 | 通过口径 |
|---|---|---|
| `trace_schema_ok` | SemanticTrace schema 合法 | schema validation 通过 |
| `trace_ok` | trace 基础语义合法 | step/event/state/target/deps 检查通过 |
| `process_pass_rate` | family process sanity 通过率 | process validator 无 error |
| `process_ready` | 过程证据足以发布 | release gate process-ready 条件满足 |
| `num_events` | trace event 数 | 复杂度/教学成本分析 |
| `trace_replay_independent_ok` | **独立重执行差分**（强 RQ2 证据） | 把 solver 单独干净重跑作为 oracle，逐 event 比对 trace 声称的 state/before/after，全匹配为 true |
| `dom_fidelity_ok` | **DOM 渲染保真差分**（HTML 专属） | Playwright 抽 DOM 文本数值/状态，与 artifact JSON 真值逐项一致 |
| `metamorphic_consistency_rate` | **变形测试**（unseen / 无 oracle 时） | 节点重命名后 trace 同构、输入缩放后已知关系保持 |
| `trace_mutation_detected` | 后处理是否修改 trace facts | 必须为 false |

**RQ2 过程正确性的核心方法（针对 §1-R2 与 doc15 #3，零 LLM）**：trace 是否忠实是有真值的客观 claim，永不用 LLM 评分。三方法均独立于生成端：

1. **独立重执行 + 逐步差分**（主力，即真正的 `trace_replay_independent_ok`）：把 `solve` 单独干净重跑一遍，记录每步真实状态序列作 oracle 去比对 trace 的 `state/before/after/value`。**必须**全新执行当 oracle，而非拿 trace 内部字段对它自己（后者循环验证）。基于 `scripts/replay_llm_specs.py` 实现/补强。
2. **DOM 渲染保真差分**（HTML 专属，必补）：渲染出的 DOM 文本可能与 artifact JSON 事实不一致（前端 bug）。用 Playwright 抽取 DOM 显示的数值/状态，与 artifact JSON 真值逐项对比。**用 VLM 看截图判"数字对不对"是弱办法；DOM-text vs JSON 差分是硬办法**——DOM 是结构化文本，逐字段相等可机器判定，不需要任何视觉模型。
3. **变形测试 (metamorphic)**：无 oracle 时也能验。图算法节点重命名后 trace 应同构；输入缩放后已知关系应保持。对 unseen split 尤其有用。

逐 event 检查规则保持：

```text
event.step == index
event.targets / event.deps 可解析
event.before 与上一状态一致（存在时）
event.after 与当前状态一致（存在时）
event.value 与 after/result 语义一致（适用时）
event.state 可 JSON 序列化且稳定
answer-like event 与 trace.result 一致（存在时）
```

> 已明确移除：原 §9.4 "LLM-as-judge 过程忠实度"**不再作为 RQ2 证据**。LLM 评分只保留在 teaching 章节作为讲解可读性补充（详见 §9.4 与 §15.0 总原则）。

### 5.5 演示 + 交互正确性指标（机器行为断言，零 LLM）

#### 演示结构覆盖（沿用现有 [M] 检查）

检查 trace 是否足以支撑教学页面且不误导：`demo_readiness_pass_rate`、`demo_key_step_coverage`、`demo_reason_present`、`demo_deps_present`、`demo_state_present`。
失败类型：`demo_missing_reason` / `demo_missing_deps` / `demo_missing_state` / `demo_state_jump` / `demo_algorithm_mismatch` / `demo_key_step_missing`。

#### 交互正确性（Playwright 行为断言）

对应 §15.5：交互**能否正确工作**是机器可证 claim，绝不依赖 LLM/VLM。基础设施 `tests/browser_smoke.py`（已有）：点 `#next` 断言 counter 前进、点 timeline tick 断言 counter/range/active 同步。在此基础上引入论文必报的硬证据：

| 指标 | 含义 | 通过口径 |
|---|---|---|
| `frame_switch_ok` | 步进/跳帧后视图状态与目标 frame 一致 | Playwright 比对渲染状态 vs trace.frames[k] |
| `interaction_valid` | 各交互控件可触发且响应预期 | 对每控件 dispatch event，断言可观察输出 |
| `interaction_mutation_free_ok` | **交互不改变算法事实**（最强机器 claim） | 交互前后各 snapshot 渲染状态/trace，断言相等；答题/预测/步进只能切视图，不能动 `trace.result/state` |
| `debug_evidence_visible` | 关键调试信息（step/state/targets/deps）渲染到 DOM 且与 artifact JSON 一致 | DOM 抽取 vs JSON 真值逐字段相等 |

**`interaction_mutation_free_ok` 必须恒 true**——这是"交互安全可信"的论文级硬证据，零 LLM。建议在现有 browser_smoke 上显式补全此断言。

> 区分清楚：交互**能正确工作** = 机器可证（本节）；交互**对学习真的有用** = §15.15 SLCG 的因果功效问题，机器 gate 证不了，需要 SLCG。两者不能混。

### 5.6 SceneGraph / 渲染 / 浏览器指标

`scene_pass_rate`、`html_render_ok`、`browser_smoke_pass_rate`、`console_error_count`、`page_error_count`、`frame_switch_ok`、`interaction_valid`、`debug_evidence_visible`。
边界：`browser_smoke_ok` 只证明页面可运行，不证明答案正确。

### 5.7 最终发布指标

| 指标 | 定义 |
|---|---|
| `final_release_pass_rate` | answer + trace + process + demo + scene + browser 全通过 |
| `algolab_full_strict_release_gate_pass_rate` | 只统计 `condition=algolab_full` 的完整机器 release gate |
| `correctness_gate_pass_rate` | 只聚合具备机器 correctness gate 的 condition |

Direct HTML baseline 不进入 `correctness_gate_pass_rate` 分母。

## 6. Repair 与成本指标

### 6.1 Repair（Stage1 真实生成能力，单独成表）

`first_try_pass_rate`、`repair_attempt_rate`、`repair_success_rate`、`repair_failure_rate`、`repair_rounds_mean`、`repair_tokens`、`repair_duration_s`、`failure_transition`。
可读字段：`candidate_selection.{first_try_pass, repair_pass, repair_attempts, materialize_attempts}`、`model_usage.by_kind.repair`、`repair_failure_summary`、`results[].{candidate_summary, repair_failure_types}`。
由于 `effective_71_71` report 替换过 LCA retry，**最终论文 repair 表从 `results[]` 重新聚合**，避免与顶层 `candidate_selection` 口径不一致。

### 6.2 成本与效率

`model_call_count`、`prompt/completion/total_tokens`（total/mean/p95/max）、`avg_total_tokens_per_case`、`token_per_success`、`duration_s`、`avg_duration_s`（标明 per-call 还是 per-case）、`estimated_cost`（无价格配置写 `null` 并保留 `cost_estimation_available=false`）。

当前 Stage1：`call_count=82`、`total_tokens=1028846`、`duration_s=10781.005`、`by_kind.generation.total_tokens=944784`、`by_kind.repair.total_tokens=84062`。
当前 Stage2：`model_call_count=105`、`total_tokens=1064765`、`llm_duration_s=14656.866`、`avg_total_tokens_per_attempted=14996.69`、`avg_llm_duration_s_per_attempted=206.43`。

## 7. 实验条件矩阵

### 7.1 主条件

| Condition | 含义 | 入口 |
|---|---|---|
| `algolab_full` | 完整链路（含 repair + process + SceneGraph + teaching overlay） | `scripts/run_llm_benchmark.py` |
| `algolab_full_no_teaching` | 关 teaching overlay，仅 correctness 主链路 | `--no-teaching-enrichment` |

### 7.2 内部消融（解释模块贡献，不得包装成外部 baseline）

| Condition | 目的 | 入口 |
|---|---|---|
| `no_repair` | repair loop 对最终通过率的贡献 | `--max-rounds 0`（或等价）|
| `no_process_validator` | process sanity 对错误检出/失败定位的边际贡献（参见 §1-R2，预期贡献有限，如实报告） | `scripts/run_no_process_validator_ablation.py` |
| `no_scenegraph_compiler` | 结构化视觉编译器对可运行性与交互稳定性的贡献 | `scripts/run_no_scenegraph_compiler_ablation.py` |
| `no_teaching` / `no_interaction` | teaching overlay 与交互的收益与成本 | `output/component_ablation_*` 现有四象限条件 |

每个 ablation 至少报告：`release_ready_drop`、`failure_phase_shift`、`browser_ok_but_not_correct`、`mean_repair_rounds_delta`、`token_delta`。

### 7.3 跨模型泛化（RQ5，新增，强烈建议补）

固定 benchmark 与协议，仅替换生成 LLM backend，至少覆盖 **3 个异构家族**（如 deepseek-v4-pro / GPT 系 / Gemini 系；可加 Qwen 或 Claude）。每个模型报告：`first_try_pass_rate`、`final_release_pass_rate`、`failure_phase` 分布、`avg_total_tokens_per_case`、`repair_success_rate`。
论点：解耦架构使“正确性”主要由系统 gate 保证，因此不同 backend 都能达到高 release rate，差异主要体现在 first-try 率与成本上——这正是解耦设计的卖点。
模型由 `ALGOLAB_LLM_MODEL` / `ALGOLAB_LLM_TIMEOUT_S` / `ALGOLAB_LLM_MAX_TOKENS` 控制；每次运行在报告中记录实际模型。

## 8. Unseen 与鲁棒性实验（RQ5，必做）

Unseen split 是反驳 “benchmark overfitting” 的核心证据，**不计入 frozen seen 71 的分母**。

指标：`unseen_pass_rate`、`seen_style_pass_rate`、`unseen_style_pass_rate`、`family_generalization_pass_rate`、`failure_type_by_style`。

构造约束（防泄漏）：unseen registry（`benchmark/unseen_family_cases.json`）只含题目描述、family 元数据、sample input、expected output；**不得**包含 deterministic `code` / `tracker_code` / `verifier_code`。

诚实性要求：unseen 通过率**预期低于 seen 100%**。论文应正面报告这一 gap，并按 failure_phase 分析失败集中在哪一层（生成端 vs 系统端）。如果 unseen 上系统 gate 仍能拦住错误产物（即“失败=被 gate 拒绝”而非“错误产物被发布”），这本身就是强结论。

## 9. LLM / VLM-as-judge 评估协议（教学/视觉质量，非 correctness）

### 9.1 通用边界

- LLM/VLM 裁判**永不**判定 final answer 正确性，不进入任何 correctness gate。
- 裁判分数与机器 gate pass/fail **分开展示**。
- 无人工评分时报告 `human_teaching_quality: missing`，**不得**用 LLM/VLM 冒充人工。

### 9.2 偏差控制（针对 §1-R4，必须落实）

1. **裁判-生成解耦**：评估教学/视觉质量的裁判模型，应与被评页面的生成模型**不同源**（如生成用 deepseek，VLM judge 用 gemini-3-flash 系；跨模型实验中交叉评判）。
2. **位置/顺序随机化**：成对比较时随机化 A/B 顺序，并做双向重复（A-B 与 B-A 各一次）以检测位置偏差。
3. **匿名化**：截图与页面中隐藏系统/方法名称，避免品牌偏好。
4. **裁判可靠性自检**：报告裁判**自一致性**（同一输入重复评分的方差）与**与人工的相关性/agreement**（见 §9.4 校准）。若裁判与人工相关性低，则该维度只作定性参考。
5. **rubric 锚定**：使用固定 rubric（见下），要求裁判输出结构化 JSON + 证据引用，降低自由发挥。

### 9.3 VLM 截图教学质量 rubric

来源 `benchmark/vlm_screenshot_rubric.json`（`vlm-screenshot-rubric-v1`），6 维 1–5 分，入口 `scripts/run_vlm_screenshot_eval.py`，多条件合并 `scripts/merge_vlm_condition_reports.py`：

| 维度 | 含义 |
|---|---|
| `layout_readability` | 布局清晰，无严重遮挡，desktop/mobile 可读 |
| `algorithm_state_visibility` | 当前状态/目标/依赖/路径/指针/区间可见 |
| `teaching_explanation` | 当前步骤解释具体，有公式/原因/before-after |
| `interaction_affordance` | 播放/步进/预测/输入/judge 入口清楚 |
| `evidence_alignment` | 截图展示与 visible evidence/targets/deps 对齐 |
| `overall_teaching_quality` | 是否适合作教学 demo 或论文配图 |

VLM 输出 schema：`case_id/condition/screenshot/viewport/scores{6维}/confidence/issues[]{severity,category,message}/suggested_caption`。报告 per-condition 均值 + 低分率 + high-confidence issue 计数。

### 9.4 LLM-as-judge 过程忠实度（teaching 可读性辅助，**非** RQ2 correctness 证据）

> 边界提醒：按 §15.0 总原则与 §15.4，过程是否忠实是有真值的客观 claim，由 §15.4 的"独立重执行差分 + DOM 保真差分 + 变形测试"三方法回答，**LLM 评分不再进入 RQ2 证据链**。本节保留只为 teaching 章节的讲解可读性补充，与 correctness 完全解耦。

除 VLM 视觉评分外，可选加一个**纯文本 LLM judge** 评估页面讲解相对真实 trace 的"过程忠实度"，仅作为 `trace_replay_ok`（机器）已通过后的**可读性**补充：
- 输入：题目 + 真实执行得到的 trace 摘要 + 页面讲解文本。
- 评分维度（1–5）：`process_faithfulness`（讲解是否符合真实步骤）、`explanation_clarity`、`no_hallucinated_step`（是否编造未发生的步骤）。
- 同样遵守 §9.2 偏差控制。该分数**不**替代机器 oracle/replay，只用于 teaching 章节。

## 10. Baseline 对比（RQ3）

### 10.1 外部生成 baseline

| Baseline | 类型 | 主要比较指标 | 入口 |
|---|---|---|---|
| Direct HTML（hide-expected 公平模式） | 端到端 LLM HTML | browser pass、visible answer audit、teaching 盲评 | `run_direct_html_baseline.py --hide-expected` |
| Direct JS/Canvas（可选） | 端到端 LLM code app | browser pass、visible answer audit、interaction | 端到端 prompt 变体 |
| Code2Video / Manim-style（文献对照，定性） | 教育视频生成范式 | render success、answer/process 可审计性、N/A interaction | 文献/复现（若可得） |
| ALGOGEN passive AV（文献对照） | prior verifiable passive AV | answer correctness、passive render、N/A interaction | 文献对照 |
| AlgoLab | **verified branching AV**（B 路径选择 + D 错误诊断，§15.5） | release gate、trace/process、`branch_gate_pass_rate`、`injected_error_diagnosis_acc` | `run_llm_benchmark.py` |

### 10.2 公平比较原则（针对 §1-R5）

- baseline 用 `--hide-expected`（`condition=direct_html_no_expected`，`expected_visible_to_model=false`）；expected-visible 只作 leaked/auxiliary baseline 单列。
- **只在共同可观测维度对比**：visible answer 正确性、browser 可运行、teaching 盲评质量。不把 AlgoLab 的 release gate 强加给 baseline。
- Direct HTML 单独拆指标：`direct_html_browser_ok`、`visible_answer_found`、`visible_answer_match`、`trace_available`(通常 false)、`scenegraph_available`(通常 false)、`release_gate_available`(false)、`schema_enforced_interaction_safety`(false)、`verified_branch_count`(=1 即 single trace)。
- **结构性输的维度**（baseline 不需要跑实验就 N/A）：`schema_enforced_interaction_safety`（端到端 onclick 无 schema 隔离）、`verified_branching`（端到端 LLM 不会预跑 alternative trace 树）、`injected_error_diagnosis`（无错误注入器基础设施）。这三条是 verified branching AV 的结构性卖点。
- 论点框定为：端到端 baseline 可能“看起来能跑”，但**无可审计的过程证据**且 visible-answer 正确率显著低于 AlgoLab 的 oracle 通过率——这正是解耦+验证架构的价值。

## 11. 统计方法与可复现（针对 §1-R3）

- **重复运行**：`algolab_full` 主条件、各 ablation、跨模型实验，每个至少 **3 次独立运行**（不同随机种子 / 不同时间），报告 `mean ± std` 与 95% CI。
- **条件比较**：full vs 各 ablation、AlgoLab vs baseline 用配对统计检验（如 per-case 配对的 McNemar 检验用于通过/失败二元结果；Wilcoxon 用于分数/成本）。报告 p 值或效应量。
- **人工评分一致性**：见 §12，报告 inter-rater agreement。
- **可复现包**：用 `scripts/build_reproducibility_package.py` 生成 manifest（命令、数据输入、输出路径、模型配置），不调 LLM、不含密钥。论文附录给出 frozen benchmark 版本号、模型版本、关键超参（timeout/max_tokens/max_rounds/max_candidates）。
- **per-case 明细**：用 `scripts/build_evaluation_report.py` 产出 `case_metrics.csv/json`，展开每题 answer/trace/process/demo/scene/browser/token，供审稿人复核与做 family-level 分析。

## 12. 轻量但可信的人类评估方案（RQ6，必做）

目标：用尽可能小的人力，得到统计上可辩护的教学质量证据，并校准 VLM/LLM judge。

### 12.1 设计

- **样本**：从 71 个 verified case 中分层抽样（覆盖主要 family）选 **15–20 个 overlapping case**；每 case 比较 2–4 个 condition 的页面（如 Direct HTML / AlgoLab verified view / AlgoLab creative view，可选 human-authored AV reference）。
- **评分者**：**3 名**评估者（最少），具备基础算法知识；彼此独立，互不讨论。
- **盲评**：隐藏系统/方法名称；页面/截图顺序随机化；同一 case 内各 condition 顺序随机。
- **形式**：可用静态截图组 + 可交互页面链接（IDE 内 Simple Browser 起本地 HTTP server 打开，避免 file:// 失败）。
- **任务**：① 6 维 rubric 打分（1–5）；② 强制成对偏好（forced-choice，避免全打中间分）；③ 可选一句话理由。

### 12.2 人工 rubric（与 VLM 维度对齐，便于校准）

| 指标 | 说明 |
|---|---|
| `algorithm_correctness` | 页面内容是否符合算法事实 |
| `process_faithfulness` | 步骤是否忠实于真实执行过程 |
| `interaction_usefulness` | 交互是否帮助学习 |
| `explanation_clarity` | 讲解是否清楚 |
| `visual_readability` | 页面是否可读 |
| `overall_preference` | 盲评整体偏好（forced-choice） |

### 12.3 可信度指标（必须报告）

- **inter-rater agreement**：序数评分用 Krippendorff's α 或 weighted Cohen's κ（两两）/ Fleiss' κ（多评分者）；偏好用 Fleiss' κ。
- **human vs VLM/LLM judge 相关性**：Spearman ρ / Kendall τ，逐维度报告。这是 §9.2-4 裁判可靠性校准的关键结果——若相关性高，则 VLM 大规模分数可信；若低，VLM 分数降级为定性参考。
- **样本量诚实声明**：明确 n=15–20、评分者=3，定位为 “lightweight human study”，不夸大为大规模用户研究。

### 12.4 落地

- 用 `scripts/build_evaluation_report.py`，**无人工 CSV 时显式标 `human_teaching_quality: missing`**，绝不用自动 proxy 估算冒充。
- 准备一个简单的评分收集表（CSV：rater_id, case_id, condition(anonymized), 6 维分, preference），人工填完后并入 evaluation report 计算 α/κ 与相关性。

## 13. 论文表格建议

### Table 1: Main Machine Gate (seen, algolab_full, mean±std over 3 runs)

| Metric | AlgoLab full |
|---|---:|
| Generation/spec parse | x/71 |
| Solve execution | x/71 |
| Answer correctness (independent vs `expected`) | x/71 |
| Trace validity (schema + structural) | x/71 |
| **Trace replay (independent re-execution)** | x/71 |
| **DOM fidelity (Playwright DOM-text vs JSON)** | x/71 |
| **Metamorphic consistency (rename / scale)** | x/71 |
| **Interaction mutation-freedom** | 71/71 (must) |
| Process pass | x/71 |
| Demo readiness | x/71 |
| Scene validity | x/71 |
| Browser smoke | x/71 |
| First-try release ready | x/71 |
| Final release ready | 71/71 |
| Model calls / Total tokens | 82 / 1028846 |

### Table 2: External Generation Comparison (common observable dims only)

| Method | Type | Visible answer match | Process auditable | Render success | Interaction validity |
|---|---|---:|---:|---:|---:|
| Direct HTML (hide-expected) | end-to-end HTML | x/N | No | browser pass | partial |
| Direct JS/Canvas | end-to-end code app | x/N | No | browser pass | partial |
| Code2Video / Manim-style | video gen | audit if available | limited | render pass | N/A |
| ALGOGEN | passive verifiable AV | available | available | passive render | N/A |
| AlgoLab | verifiable interactive AV | oracle (answer_correctness_ok) | Yes (trace replay) | browser pass | Playwright interaction |

### Table 3: Cross-Model Generalization

| Backend | First-try pass | Final release | Repair success | Avg tokens/case |
|---|---:|---:|---:|---:|
| deepseek-v4-pro | x/71 | x/71 | x% | x |
| Model B | x/71 | x/71 | x% | x |
| Model C | x/71 | x/71 | x% | x |

### Table 4: Unseen Generalization

| Split | Final release pass | seen-style | unseen-style | dominant failure phase |
|---|---:|---:|---:|---|
| seen 71 | 71/71 | - | - | - |
| unseen | x/M | x/y | x/y | generation / system |

### Table 5: Internal Ablation (Δ vs full)

| Variant | Answer | Trace | Scene | Browser | Release ready | Release Δ | Failure phase shift |
|---|---:|---:|---:|---:|---:|---:|---|
| Full | x/71 | x/71 | x/71 | x/71 | x/71 | 0 | - |
| No repair | x/71 | x/71 | x/71 | x/71 | x/71 | -Δ | → generation/execution |
| No process validator | x/71 | x/71 | x/71 | x/71 | x/71 | -Δ | → process/demo |
| No SceneGraph compiler | x/71 | x/71 | N/A | x/71 | x/71 | -Δ | → scene/browser |

### Table 6: Stage2 Creative View

| Metric | Value |
|---|---:|
| Creative attempted | 71/71 |
| Browser/runtime success | 71/71 |
| Strict visual audit pass | 59/71 |
| Strict audit flagged | 12/71 |
| Manual visual acceptable | 71/71 |
| Strict audit false positives among flagged | 12/12 |
| Layout repair attempts | 34 |
| Total tokens | 1064765 |

### Table 7: Teaching Quality (VLM + Human, anonymized)

| Method | Layout | State vis | Explanation | Interaction | Evidence | Human overall | Human-VLM ρ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct HTML | | | | | | | |
| Human-authored AV ref | | | | | | | |
| AlgoLab verified view | | | | | | | |
| AlgoLab creative view | | | | | | | |

无人工评价时 Human 列写 `missing`；同时报告 inter-rater α/κ。

### Table 8: SLCG Teaching Efficacy (RQ6 因果功效，零 LLM judge)

> 详见 §15.15。本表回答"加讲解/交互是否真的让学习者多答对"，是 RQ6 与现有 VLM 感知评分互补的因果证据。学生面板用弱模型留头部空间（如 `gpt-5-nano` / `qwen-turbo`），生成模型固定 deepseek-v4-pro 与之解耦。

| Condition | Probe acc (predict) | Probe acc (counterfactual) | Probe acc (trace-back) | Learning curve slope |
|---|---:|---:|---:|---:|
| C0 prior floor (题面 only) | x/y | x/y | x/y | - |
| C1 visualization only (`no_teaching`) | x/y | x/y | x/y | β |
| C2′ placebo explanation (等长无义) | x/y | x/y | x/y | β |
| C2 full teaching+interaction (`full`) | x/y | x/y | x/y | β |

派生 delta（每条都做配对显著性检验）：

| Δ | 公式 | 解释 |
|---|---|---|
| `visualization_gain` | acc(C1) − acc(C0) | 可视化本身贡献 |
| `teaching_gain` | acc(C2) − acc(C1) | 讲解层贡献 |
| `interaction_gain` | acc(full) − acc(no_interaction) | 交互层贡献 |
| `semantic_gain` | acc(C2) − acc(C2′) | 必须显著 > 0；否则讲解只是凑字数 |

可信度附表：simulated-learner vs 人类小样本 Spearman ρ（同 §12 校准 VLM 的逻辑，这里校准的是**学习结果**而非感知质量）。

## 14. 执行清单（按优先级）

P0（投稿核心证据）：
1. 生成 `case_metrics.csv/json`，展开 Stage1 per-case 全字段（`build_evaluation_report.py`）。
2. 从 `effective_71_71` 的 `results[]` 重新聚合 repair 表与 first-try 率。
3. **RQ2 三方法（零 LLM）**：
   - `trace_replay_independent_ok`：独立重执行差分（`replay_llm_specs.py` 跑全量 71，要求"全新执行当 oracle"，不要拿 trace 字段对它自己）。
   - `dom_fidelity_ok`：Playwright DOM-text vs artifact JSON 真值差分（HTML 专属硬证据）。
   - `metamorphic_consistency_rate`：变形测试（节点重命名 / 输入缩放）。
4. **§5.5 交互硬 claim**：在 `tests/browser_smoke.py` 上补 `interaction_mutation_free_ok` 断言（交互前后 snapshot 必须相等）。
5. **Gate Soundness 受控错误注入**（§15.3b，doc15 #1）：构造负样本，报告 `gate_rejection_rate`——把 71/71 从可疑变可信的唯一硬证据。
6. Direct HTML `--hide-expected` + answer audit，按 §10.2 公平口径并入 Table 2。

P1（泛化与显著性，强烈建议）：
7. 跨模型泛化：≥3 个 backend 跑 Stage1，填 Table 3。
8. Unseen split 跑通并诚实报告 gap（按 §15.12 改名 `held_out_task_pass_rate`），填 Table 4。
9. 主条件 + 各 ablation 各重复 3 次，统计检验**只打未饱和量**（first-try 率、token 成本、Wilcoxon），filling Table 1/5。

P2（质量、教学功效、裁判可信度、交互升级）：
10. VLM rubric 全量评分，裁判与生成模型解耦 + 位置随机化 + 自一致性自检。
11. 15–20 个 overlapping case、3 名评分者的人工盲评，报告 α/κ 与 human-VLM 相关性。
12. **SLCG 教学功效实验（§15.15，本方案核心创新）**：
    - **前置（必须先做）**：产出一批 teaching-enrichment 开启且含 interaction 的 artifact——当前 `output/aaai/stage1_final` 71 份 verified artifact 共 2768 帧 interaction 全为 0，不修复无法跑 C2/交互条件。
    - 实例特定 probe（预测 / 反事实 / 追溯）+ C0/C1/C2/C2′ 矩阵 + 弱模型学生面板 + 学习曲线斜率 + 人类小样本校准，填 Table 8。
13. **D 错误诊断交互（§15.5，与 §15.3b 同期）**：直接复用 P0 #5 的错误注入器输出，UI 端做"K 份 trace 并排找错"形态，新增 `injected_error_diagnosis_acc`。边际成本低，先于 B 上线。
14. **B 路径选择交互（§15.5，论文核心 interaction 创新）**：solver 在每个决策点 fork alternative trace，全部通过 §15.3-§15.5 gate；UI 切换分支不动 trace。新增 `verified_branch_count` / `branch_gate_pass_rate` / `branch_switch_mutation_free_ok`，把 SLCG `interaction_gain` 从恒 0 解锁。
15. Stage2 strict visual audit 当作有测量误差的分类器报 precision/recall（doc15 #5），别再写"人工 100% 推翻 strict"。

## 15. 指标的具体评估方法（claim 类型 → 方法）

本节回收口一个 doc 之前没讲清的问题：**5.4 trace/过程正确性、5.5 演示正确性、交互、教学这些指标，产物是 HTML，到底用什么方法评估“真的对/真的有用”，什么时候才该动用 LLM/VLM。**

详细审查与缺口见 `docs/15_EXPERIMENT_METRICS_REVIEW_AND_GAPS.md`，本节给可执行评估方案。

### 15.0 核心原则：claim 的性质决定方法

不是“产物是 HTML 就上 LLM”。先判 claim 属于哪一类，再选方法：

| 要证明的 | 性质 | 唯一有效方法 | LLM/VLM 角色 |
|---|---|---|---|
| 它**正确**（trace 忠实、答案对、交互不改事实） | 客观、有真值 | 确定性机器验证（重执行 / 差分 / Playwright） | 不能当证据，至多可读性补充 |
| 它**质量好**（讲解清楚、布局可读） | 主观、无真值 | 判官评分（LLM/VLM）+ 人工校准 | 可以，但只是 proxy，必须校准 |
| 它**真的提高教学**（加讲解/交互→学得更好） | 因果、看结果 | 学习结果实验（对照 + 度量） | 绝对不能；LLM 早已会该算法 |

一句话：correctness 永不用 LLM（有更硬的办法）；teaching 功效永不用 LLM judge（它证明不了）。

本节按 §5/§6 的指标分组逐一给出评估方法、数据来源与判定口径。方法标签统一为：**[M] 机器确定性**、**[J] LLM/VLM 判官（需校准）**、**[H] 人工**。

### 15.1 评 5.1 覆盖与输入指标 —— [M] 全机器，无判官

指标：`N`、`case_id`、`sample_index`、`family_id`、`subfamily_id`、`gate_layer`、`case_set`、`case_style`。

- 方法：直接从 frozen benchmark 注册表与 `run_llm_benchmark.py` 报告字段读取，不涉及任何评分。
- 数据来源：`benchmark/*` 注册表 + `results[].{case_id,family_id,subfamily_id,gate_layer,case_set,case_style,sample_index}`。
- 判定：分母完整性校验——实验前后 `N` 与 case 列表必须一致（哈希比对 benchmark 文件），中途不得删题/改名/改分母。
- 聚合：Overall `x/71`；per-family `x/y`；gate layer 分列；seen/unseen 分列。
- 易错点：unseen 不计入 frozen seen 71 分母（见 §8、§15.12）。

### 15.2 评 5.2 LLM 生成与解析指标 —— [M] 全机器

指标：`generation_success_rate`、`spec_parse_ok`、`materialization_success_rate`、`materialize_attempts`、`failure_phase`、`failure_type`。

- 方法：完全由 pipeline 状态机判定，无评分。`generate_solution_spec()` 是否返回 → `normalize_solution_spec()`/`parse_variants()` 是否成功 → sandbox materialize 是否成功，逐阶段记布尔与计数。
- 数据来源：`results[].{failure_type,last_phase,checks,errors}`、`candidate_selection.materialize_attempts`、`failure_summary`。
- 判定：`spec_parse_ok` = 顶层 JSON object 合法且 `variants` 可解析；`materialization_success_rate` = 至少一个 variant 通过 sandbox execution 的 case 占比。
- 失败归因：`failure_phase` 必须落到唯一阶段（generate / parse / materialize / trace / process / demo / scene / render），供 ablation 的 `failure_phase_shift` 使用。

### 15.3 评 5.3 算法答案正确性指标 —— [M] 机器 oracle，分独立性标注

指标：`solve_ok`、`answer_match`、`trace_result_match`、`verifier_match`、`multi_solution_match`、`answer_correctness_ok`。

- 方法：全部确定性等价判定，**零 LLM**。`results_equivalent()`（`algolab/verification/result_normalizer.py`）做无序/集合/数值容差归一化。
- **独立性分级（必须在论文标注，见 doc15 #2）**：
  - **independent-of-generation（强）**：`answer_match` = solve 结果 vs 外部固定 `expected`。这是唯一独立于生成端的真值证据（71/71 都有 expected）。
  - **self-consistency（弱，证明忠实/无内部矛盾，不证答案对）**：`trace_result_match`（trace.result vs solve，同源）、`verifier_match`（LLM 生成 verifier，仅 61/71 存在且与 solver 可能同错）。
- 数据来源：artifact `expected_result`、`verifier_result`、`variants[].result`、`validation.checks`。
- 等价口径披露：归一化把不同顺序的合法解判等价（如 articulation/bridges 列表无序），论文须明确这点，避免“等价掩盖错误”的质疑。
- baseline 边界：direct HTML 无 solver/trace，**不得**填 `answer_correctness_ok`，只能填 `visible_answer_match`（§15.12）。

### 15.3b 评 Gate Soundness —— [M] 受控错误注入（doc15 #1，P0 新增）

仅有 pass rate 无法区分“gate 严+模型强”与“gate 松什么都放行”。必须新增**负样本**实验回答“gate 会不会拒错”：

- 方法：对已通过的 artifact 注入受控错误（篡改 `solve` 返回值 / 篡改 `trace.result` / 删关键 deps / 错位 `before/after/state` / 末值≠expected），构造应被拒绝的样本。
- 指标：`gate_rejection_rate` = 被拒负样本 / 注入负样本，按错误类型分桶（answer-level / trace-level / structural）。
- 判定：注入 N 个、拦住 N−k 个，`k`（漏网数）即 gate 误接受度。理想 `gate_rejection_rate = 1.0`。
- 意义：把 `71/71` 从“可疑”变“可信”的唯一硬证据，应作为 P0，优先级高于跨模型/unseen。

### 15.4 评 5.4 Trace/过程正确性：重执行差分，不用 LLM

trace 正不正确是有真值的客观问题。§9.4 的“LLM 过程忠实度评分”**从 RQ2 correctness 证据中移除**，降级为讲解可读性辅助。强方法三种，均无 LLM：

1. **独立重执行 + 逐步差分（主力，即真正的 `trace_replay_ok`）**：把 `solve` 单独干净重跑一遍，记录每步真实状态序列，作为 oracle 去比对 trace 声称的 `state/before/after/value`。必须是**全新执行当 oracle**，而非拿 trace 内部字段对它自己（后者是循环验证）。指标：`trace_replay_independent_ok`、逐 event `state_match_rate`。
2. **DOM 渲染保真差分（HTML 专属，必补）**：渲染出的 DOM 文本可能与 artifact JSON 事实不一致（前端 bug）。用 Playwright 抽取 DOM 显示的数值/状态，与 artifact JSON 真值逐项对比。**用 VLM 看截图判“数字对不对”是弱办法；DOM-text vs JSON 差分是硬办法。** 指标：`dom_fidelity_ok`、`dom_value_mismatch_count`。
3. **变形测试（metamorphic）**：无 oracle 时也能验。图算法节点重命名后 trace 应同构；输入缩放后已知关系应保持。对 unseen split 尤其有用。指标：`metamorphic_consistency_rate`。

其余 §5.4 schema 类指标 `trace_schema_ok`、`trace_ok`、`process_pass_rate`、`process_ready`、`trace_mutation_detected` 仍走 [M] 现有 validator；`num_events` 仅作复杂度统计。`trace_mutation_detected` 必须恒 false。

### 15.5 评 5.5 演示正确性 + 交互正确性：Playwright 行为断言，不用 LLM

`tests/browser_smoke.py`（1186 行）已有基础设施：点 `#next` 断言 counter 前进、点 timeline tick 断言 counter/range/active 同步。交互正确性走确定性行为断言，不是 LLM。

5.5 指标（`demo_readiness_pass_rate`、`demo_key_step_coverage`、`demo_reason_present`、`demo_deps_present`、`demo_state_present` 及各 `demo_*` 失败类型）：`algolab/verification/demo_readiness.py` 本就是结构化机器检查（阶段覆盖、关键步 reason/state/deps），继续走 [M]。

5.6 交互运行指标（`frame_switch_ok`、`interaction_valid`、`debug_evidence_visible` 等）：[M] Playwright 行为断言。最强、最该写进论文的机器可证 claim：

- **交互不改变算法事实（interaction mutation-freedom）**：交互前后各 snapshot 一次渲染状态/trace，断言相等。答题、步进、预测只能切视图，不能动 `trace.result/state`。指标：`interaction_mutation_free_ok`（必须恒 true）。这是“交互安全可信”的硬证据，零 LLM。建议在现有 browser_smoke 上显式补全此断言。

> 区分清楚："交互**能正确工作**"=机器可证；"交互**对学习有用**"=下面 §15.15 的功效问题，机器证不了。

#### 主动参与型交互（升级方向：B 路径选择 + D 错误诊断）

当前 `choice / input / judge` 三类交互均为被动答题，用户没在算法过程里做任何事，与 §15.15 SLCG 的 probe 在功能上重叠。建议升级两类**主动参与**交互，统一原则：**用户操作只在预先验证过的 alternative trace 之间切换，从不动态生成新 trace**——by-construction safety 不动。

- **B 路径选择**：在每个算法决策点，由 solver 预跑出 N 条 alternative trace（如二分的左/右、DFS 儿子顺序、DP 状态转移源），每条独立通过 §15.3-§15.5 gate；运行时用户选哪条就切到对应 trace。教学上把"看完帧猜下一步"升级为"主动模拟算法决策"；评估上让 SLCG `interaction_gain` 第一次有有意义差分（当前因 enrichment 缺失恒为 0）。
- **D 错误诊断**：复用 §15.3b Gate Soundness 的错误注入器，每 case 备 1 份正确 trace + K 份注入已知错误（off-by-one / 比较反向 / 末位漏判）的 mutated trace，让学习者找哪份对、错在哪步。错误注入器已在 P0，UI 端边际成本只在"K 份并排呈现"。

非对称性（排期参考）：

| 维度 | B 路径选择 | D 错误诊断 |
|---|---|---|
| 工程量 | 中（需新建 alternative branch executor + SceneGraph 多 trace packaging） | 中偏低（注入器复用 §15.3b） |
| 用户认知负担 | 低（前向决策） | 高（反向 debug，依赖正确算法内化模型） |
| 71 case 通用性 | 通用 | family 不均匀（off-by-one 密集 family 强，简单遍历类弱） |
| SLCG 协同 | 强（直接对接预测型 probe） | 中（对接反事实型 probe + 新增 `diagnosis_accuracy`） |

推荐顺序：**先 D 后 B**——D 与 §15.3b 同期可出，B 单独排期作为论文核心 interaction 创新。

新增/扩展指标（均不破坏 `interaction_mutation_free_ok`）：

| 指标 | 含义 |
|---|---|
| `verified_branch_count` | 每 case 的预生成 alternative trace 数（含正确 + alternative + 注入错误） |
| `branch_gate_pass_rate` | 全部预生成分支通过 §15.3-§15.5 gate 的比例（必须 = 1.0） |
| `branch_switch_mutation_free_ok` | 用户切换分支前后，**当前选中分支内**的算法事实快照 bytewise 相等（B 类断言） |
| `injected_error_diagnosis_acc` | SLCG 学生面板在 D 类交互上的诊断准确率（per error-type 分桶） |

论文叙事升级（同步 §10 baseline 表 + contribution 列表）：从 "verifiable interactive AV" 升级为 **"verified branching AV"**——产物不是单条 trace，而是已验证的 trace tree，用户的"交互"是在 verified state space 中导航。Direct HTML / video AV / passive AV 在该维度上结构性输。

### 15.6 评 5.6 SceneGraph / 渲染 / 浏览器指标 —— [M] 机器，附边界

指标：`scene_pass_rate`、`html_render_ok`、`browser_smoke_pass_rate`、`console_error_count`、`page_error_count`、`frame_switch_ok`、`interaction_valid`、`debug_evidence_visible`。

- 方法：`scene_validator.py`（schema、frame 非空、mark/edge 引用存在）走 [M]；浏览器侧由 `browser_smoke_html_paths()` 与 `tests/browser_smoke.py` 在 Chromium 内断言。
- 数据来源：`results[].release_gate`、browser smoke 日志、artifact `scenes`。
- 判定：`browser_smoke_ok` = 页面可打开 + `#title`/`#counter`/`#canvas` 可见 + 无 console/page error。
- **硬边界**：`browser_smoke_ok` 只证明页面可运行，**不证明答案正确**；不得用它替代 §15.3/§15.4 的 oracle。`console_error_count`/`page_error_count` 必须为 0 才算 pass。

### 15.7 评 5.7 最终发布指标 —— [M] 机器组合门

指标：`final_release_pass_rate`、`algolab_full_strict_release_gate_pass_rate`、`correctness_gate_pass_rate`。

- 方法：对每 case 取 answer + trace + process + demo + scene + browser 各层布尔的合取，[M]。
- 数据来源：`results[].release_gate.release_ready` + strict warning 标志。
- 判定：`final_release_pass_rate` = 全层通过且无 errors 的 case 占比；strict 模式下任意 warning 即判失败。
- 分母边界：direct HTML baseline 不进 `correctness_gate_pass_rate` 分母（无机器 correctness gate）。
- 统计注意：该指标在 full 条件饱和（71/71）时方差为 0，显著性检验应改打未饱和的 first-try 率与成本（见 §15.10、§11）。

### 15.8 评 6.1 Repair 指标 —— [M] 从 results[] 重聚合

指标：`first_try_pass_rate`、`repair_attempt_rate`、`repair_success_rate`、`repair_failure_rate`、`repair_rounds_mean`、`repair_tokens`、`repair_duration_s`、`failure_transition`。

- 方法：[M] 计数，无评分。
- 数据来源：**优先从 `results[].candidate_summary` 逐 case 重聚合**（因 `effective_71_71` 替换过 lca retry，顶层 `candidate_selection` 与 results 口径可能不一致，见 doc15 §1）；辅以 `model_usage.by_kind.repair`、`repair_failure_summary`。
- 当前实测：first-try 61/71 = 85.9%，repair 后 71/71；这是未饱和、有方差的量，适合做显著性。

### 15.9 评 6.2 成本与效率指标 —— [M] 日志统计

指标：`model_call_count`、`prompt/completion/total_tokens`(total/mean/p95/max)、`avg_total_tokens_per_case`、`token_per_success`、`duration_s`、`avg_duration_s`、`estimated_cost`。

- 方法：[M] 从 `record_model_call()` 聚合。
- 数据来源：`model_usage.{call_count,prompt_tokens,completion_tokens,total_tokens,duration_s,by_kind}`。
- 口径：明确标注 per-call 还是 per-case；`prompt_tokens` 与 `completion_tokens` 分列（避免 reasoning/verbosity 混淆）；无价格配置时 `estimated_cost=null` 且 `cost_estimation_available=false`。

### 15.10 评 §7 实验条件 / §7.2 Ablation 指标 —— [M] 条件间 delta

每个 ablation 报告：`release_ready_drop`、`failure_phase_shift`、`browser_ok_but_not_correct`、`mean_repair_rounds_delta`、`token_delta`。

- 方法：[M]，full 与各 variant 在同一 benchmark 上 per-case 配对计算 delta。
- 关键指标 `browser_ok_but_not_correct`：浏览器能跑但 oracle 不通过的 case 数——直接量化“能跑≠正确”，是解耦架构卖点的硬证据。
- 统计：per-case 配对，二元结果用 McNemar，分数/成本用 Wilcoxon（§11）。

### 15.11 评 §7.3 跨模型泛化指标 —— [M] 固定协议换 backend

每模型报告：`first_try_pass_rate`、`final_release_pass_rate`、`failure_phase` 分布、`avg_total_tokens_per_case`、`repair_success_rate`。

- 方法：[M]，固定 benchmark 与 gate，仅换 `ALGOLAB_LLM_MODEL`，≥3 个异构家族。
- 论点：final release 主要由系统 gate 保证，跨 backend 都应高；差异集中在 first-try 率与成本——正是解耦设计卖点。报告须记录每次实际模型版本。

### 15.12 评 §8 Unseen 指标 —— [M]，但须如实重命名

指标：`unseen_pass_rate`、`seen_style_pass_rate`、`unseen_style_pass_rate`、`held_out_task_pass_rate`、`failure_type_by_style`。

- 方法：[M]，同 Stage1 gate，但 case 来自 `benchmark/unseen_family_cases.json`。
- **如实定位（doc15 #6）**：已核对该 split 的 15 个 family **全部是 seen 子集**，故它是“已知族内留出新题（held-out tasks）”，不是跨族泛化。原 `family_generalization_pass_rate` 改名 `held_out_task_pass_rate`，claim 写“generalizes to unseen *tasks* within supported families”。
- 防泄漏：unseen registry 只含题面/family 元数据/sample input/expected，不含 deterministic `code/tracker_code/verifier_code`（已确认）。
- 诚实性：unseen 通过率预期低于 seen 100%；若失败=被 gate 拒绝而非错误产物被发布，本身即强结论。

### 15.13 评 §9 教学/视觉感知质量指标 —— [J] 判官 + [H] 校准

指标：VLM 6 维 rubric（`layout_readability`/`algorithm_state_visibility`/`teaching_explanation`/`interaction_affordance`/`evidence_alignment`/`overall_teaching_quality`），及 §9.4 文本 LLM 过程忠实度（仅 teaching 可读性，不入 RQ2 correctness）。

- 方法：[J] 判官评分，**必须**裁判-生成解耦、A/B 位置随机化、匿名化、rubric 锚定 + 结构化 JSON（§9.2）。
- 可靠性自检：报告裁判自一致性（重复评分方差）+ 与人工 Spearman ρ/agreement；相关低则降级为定性。
- 硬边界：永不进 correctness gate；无人工时 `human_teaching_quality: missing`，不得用 LLM 冒充人工。

### 15.14 评 §12 人工质量指标 —— [H] 盲评 + 一致性

指标：6 维人工 rubric（`algorithm_correctness`/`process_faithfulness`/`interaction_usefulness`/`explanation_clarity`/`visual_readability`/`overall_preference`）。

- 方法：[H]，15–20 overlapping case，≥3 评分者，盲评 + 顺序随机 + forced-choice。
- 必报可信度：inter-rater agreement（Krippendorff's α / weighted κ / Fleiss' κ）+ human-VLM 相关（Spearman ρ / Kendall τ）。
- 诚实声明：n 与评分者数明确，定位 lightweight human study。

### 15.15 评教学功效：Simulated-Learner Comprehension Gain (SLCG)

教学功效是“加了讲解/交互，是否真的提高教学”，这是因果 claim。难点：LLM 早已会二分查找，问它“看了这页学会没”毫无意义。**SLCG 把“LLM 已经会”从 bug 反转为实验的控制变量。**

核心思路：不让 LLM “学”，而是测“在固定先验下，讲解能让学习者多答对多少只能靠跟上这次具体执行才能答对的问题”。delta 即讲解贡献，先验被减掉。

#### 15.15.1 探针 probe（机器出题、机器判分，绕开 LLM judge）

从已验证 trace 自动生成**实例特定**问题，答案在 trace 里有真值，判分确定性：

- **预测型**（看前 k 帧，揭晓前预测第 k+1 步）：下一步选哪个 mid / 哪些元素被排除 / `dp[2][3]` 变成几。
- **反事实型**（最强，纯靠记忆答不出）：若第 5 步比较用 `<=` 而非 `<`，下一帧状态会怎样。
- **追溯型**：第 7 步为什么淘汰右半区，答案落到本次执行的 state/deps。

三类都无法靠“我知道该算法”答对，必须真的跟上了本次轨迹。判分对 trace 真值，零 LLM。

#### 15.15.2 条件矩阵（操纵“学习者能看到什么”）

| 条件 | 学习者输入 | 作用 |
|---|---|---|
| C0 先验地板 | 只给题面 | 测纯先验能答多少（命门，扣除“本来就会”） |
| C1 只可视化 | `no_teaching` 页（裸 state） | 可视化本身的贡献 |
| C2 讲解+交互 | `full` 页 | 完整教学层 |
| C2′ 安慰剂讲解 | 等长但内容打乱/无关的讲解 | 控制 verbosity：证明起作用的是语义而非字多 |

C1/C2 直接复用 `output/component_ablation_*` 的 `full / no_teaching / no_interaction / no_teaching_interaction` 四象限产物，缺的只是“出题+答题+判分”这把尺子。

#### 15.15.3 度量（把教学性变成可做显著性检验的 delta）

```text
visualization_gain = acc(C1) - acc(C0)
teaching_gain      = acc(C2) - acc(C1)
interaction_gain   = acc(full) - acc(no_interaction)
semantic_gain      = acc(C2) - acc(C2')   # 必须显著 > 0，否则讲解只是凑字数
```

C0 地板把“模型本来就会”量化扣除，剩下的 delta 才是页面真正教进去的。这是多数 AV 教学评估漏掉的，也是本方法的核心贡献点。

补充 **学习曲线斜率**：让学习者逐帧推进、每步预测下一步，画正确率随帧数上升曲线，斜率=学习速率。讲解有效→曲线更陡，比单点正确率更有说服力。

#### 15.15.4 学习者面板（弱模型制造头部空间，与生成模型解耦）

强模型会顶满天花板（delta=0）。用弱学生模型留可提升空间（如 `gpt-5-nano` / `qwen-turbo` / `doubao-seed-2-0-lite` / `gpt-oss-20b`）。生成用 deepseek-v4-pro，学生用别家弱模型，天然解耦；每条件多次运行给统计功效。

#### 15.15.5 可信度控制（审稿人攻击点的对策）

1. **先验地板 C0**：量化扣除先验，回答“是不是模型本来就会”。
2. **安慰剂讲解 C2′**：等长无义讲解，证明是语义内容而非屏幕字数起作用。
3. **人类小样本校准**：子集上让真人跑同一套探针，报 simulated-learner 与人类正确率的 Spearman ρ。高→大规模 LLM 学生分可信；低→降级为定性。逻辑同 §12 VLM-人工校准，但这里校准的是**学习结果**而非感知质量。

#### 15.15.6 真人产品信号（可选复用）

页面本就有预测/选择交互。线上记录真人首次答题正确率，teaching-on vs off 对比——内嵌在产物里的行为学习信号。

#### 15.15.7 落地前置条件与诚实边界

- **前置依赖（重要）**：当前 `output/aaai/stage1_final` 的 71 份 verified artifact **interaction frame 数为 0**（核对：2768 帧全部无 interaction），说明该批是 `--no-teaching-enrichment` 或 enrichment 未注入交互产出。SLCG 的 C2/交互条件依赖 teaching enrichment 真正写入了 `teaching`/`interaction` overlay，因此跑 SLCG **前必须先产出一批 teaching-enrichment 开启、且含 interaction 的 artifact**，否则 C2 与 C1 无差异、`interaction_gain` 恒为 0。
- **判分依赖 trace 真值**：探针答案来自 §15.1 的独立重执行结果，确保“正确答案”本身可信。
- **诚实声明**：SLCG 测的是 *comprehension / predictability gain*，不是教室长期保持率（retention）。论文须如实表述，并把 C0/C2′/人类校准作为有效性论证一并报告。

#### 15.15.8 SLCG 与现有 RQ 的关系

SLCG 服务 RQ6（教学质量）的**功效**侧，与 §9 的 VLM/人工**感知质量**评分互补：VLM 答“看起来清不清楚”，SLCG 答“是否真的让学习者多答对”。两者都不进 correctness gate。

### 15.16 评 §10 Direct HTML / Baseline 共同可观测指标 —— [M] + [J/H]，不进入 correctness gate

Direct HTML baseline 没有 `solve/trace/verifier/SceneGraph/release_gate`，因此只能在**共同可观测维度**上比较：页面能否运行、页面是否显示答案、显示答案是否匹配 expected、教学/视觉质量是否更好。不得把 AlgoLab 的机器 release gate 强加给 baseline。

#### 15.16.1 `direct_html_browser_ok` —— [M] 浏览器运行性

- 方法：Playwright 打开 baseline HTML，检查页面加载完成、关键容器可见、无 console/page error。
- 数据来源：`scripts/run_direct_html_baseline.py` 产出的 HTML 路径、browser smoke 日志、`results[].ok`。
- 判定：页面可打开且无 JS error 为 true；超时、空白页、脚本错误、关键内容不可见均为 false。
- 边界：该指标只证明 baseline 页面能运行，**不证明答案正确或过程可信**。

#### 15.16.2 `visible_answer_found` —— [M] 可见答案可抽取性

- 方法：用 `scripts/audit_direct_html_answer.py` 从 DOM 文本中抽取可见答案候选。
- 数据来源：baseline HTML DOM 文本、case expected。
- 判定：分四态而非布尔——`found_strict`（标注/已知 selector 抽到）/ `found_loose`（启发式抽到）/ `found_llm_assisted`（兜底，独立标注）/ `not_found`。
- **抽取不到的两种归因（必须拆开报）**：
  - `not_found_due_to_extractor`：测量噪声（canvas / 跨 DOM 节点 / 格式怪 / hover 态）——不算 baseline 缺陷
  - `not_found_due_to_artifact`：baseline 真实缺陷（页面只显示中间值，未渲染最终答案）——算 baseline 失败
  - 归因依赖 15-20 case 人工小样本校准，报 `extraction_recall_rate` / `extraction_precision`（同 §12 / §15.13 校准套路）
- 边界：找到答案文本不等于答案正确，更不等于过程正确。

#### 15.16.3 `visible_answer_match` —— [M] 可见答案匹配

- 方法：将 `visible_answer_found` 抽取到的答案与外部 fixed expected 做 `results_equivalent(...)` 或 baseline audit 的等价归一化比较。
- 数据来源：`direct_html_answer_audit.json` 的 `visible_answer_match` / `visible_answer_match_rate`。
- 判定：抽取答案与 expected 等价为 true；找不到答案或不等价为 false。
- **必须报双边界**（避免抽取测量误差污染 baseline 比较）：
  - `match_optimistic = answer_match / N`（所有 not_found 算 baseline 错；审稿人怀疑抽取器太弱时看这个）
  - `match_pessimistic = answer_match / (N - not_found_due_to_extractor)`（扣测量噪声后的最公平估计）
  - `match_among_present = answer_match / answer_present_in_page`（仅在确认页面真渲染了答案的 case 上算）
- 边界：这是 Direct HTML 与 AlgoLab 可公平比较的最强答案指标；它仍然只验证页面**展示的最终答案**，不验证 trace、过程、SceneGraph 或交互绑定。AlgoLab 的结构化 artifact 完全绕过抽取不确定性，这本身是解耦架构的额外卖点。

#### 15.16.4 `trace_available` —— [M] 过程证据架构属性（非比较指标）

- **重新定位**：Direct HTML 由设计就不产出独立 trace，`trace_available = false` 是 by construction 已知，不是测量结果。原写法把它当 baseline 对比维度会落进 R5 "用 AlgoLab 自己的 gate 评 baseline" 的攻击。
- **架构属性记录（不跑实验）**：AlgoLab=true / Direct HTML=false 永远成立。论文写成 contribution-level 声明，不进 head-to-head 表："AlgoLab emits machine-auditable process traces by construction; end-to-end HTML baselines do not — this is an architectural property, not an empirical comparison."
- **可选实测替代** `embedded_process_evidence_found`（P2）：扫 baseline HTML 内嵌 `<script>` JSON / `data-*` 属性 / 自然语言步骤列表，看是否承载结构化步骤信息。报为 baseline 内部测量，**与 `trace_available` 分开**，不要混成一个数。
- 边界：自然语言 step list 不能冒充机器 trace；`embedded_process_evidence_found = true` 仅意味"页面里有疑似步骤信息"，仍需通过与 AlgoLab 同级的 schema/target/deps 检查才能升级为机器可审计 trace。

#### 15.16.5 `scenegraph_available` —— [M] 视觉语义证据架构属性（非比较指标）

- **重新定位**：Direct HTML 由设计就不产出独立 SceneGraph，`scenegraph_available = false` 是 by construction 已知，不是测量结果。同 §15.16.4 一样，原写法会落进 R5 "用 AlgoLab 自己的 gate 评 baseline" 的攻击。
- **架构属性记录（不跑实验）**：AlgoLab=true / Direct HTML=false 永远成立。论文写成 contribution-level 声明，不进 head-to-head 表。
- **可选实测替代** `visual_binding_evidence_found`（P2）：扫 baseline HTML 看是否有 `data-id` / `data-target` / 与算法对象（数组下标、节点名、dp 单元）对应的 DOM 标识，能否机器解析。与 `scenegraph_available` 分开报，避免混淆。
- 边界：CSS class 名 / 颜色编码 / 装饰性 SVG 不能冒充结构化视觉绑定；`visual_binding_evidence_found = true` 仅说明"DOM 含算法对象引用"，要升到 SceneGraph 等级仍需通过 mark/edge/evidence 引用一致性检查。

#### 15.16.6 `release_gate_available` —— [M] 机器发布门可用性

- 方法：检查 baseline 是否存在 answer + trace + process/demo + scene + browser 的组合机器 gate。
- 数据来源：baseline report metadata。
- 判定：Direct HTML baseline 为 false；AlgoLab full 为 true。
- 边界：该指标不参与 baseline pass/fail，而是解释为什么 baseline 不能进入 `correctness_gate_pass_rate` 分母。

#### 15.16.7 `baseline_teaching_quality` —— [J] + [H] 感知质量（全量评估，§15.13 + §15.14 联合协议）

**评估范围**：Direct HTML / AlgoLab verified / AlgoLab creative 三 condition × **全量 71 case**。VLM 跑全量；人工跑 15-20 overlapping case 子集做校准。

**六步流水线**：

1. **截图标准化**：每 case × 3 condition，固定 viewport（如 1440×900）+ DPR + wait 条件（DOM ready + 静态稳定 + 关键元素可见）+ 截屏种类（首屏 + 关键交互后），同条件下完全可复现。

2. **匿名化**：去 system 名/品牌色/路径标识；DOM 中 `data-system="algolab"` 类标识在评分前 strip；文件名重命名为随机 hash。**不匿名 = 评分作废**。

3. **VLM 全量评分（§15.13）**：
   - 判官 ≠ 生成模型；至少 2 个不同家族判官（如 gemini + GPT 系）做交叉评以降低单判官偏差
   - 6 维 rubric（layout / state visibility / explanation / interaction affordance / evidence alignment / overall），1-5 分
   - A/B 位置双向随机（同 case 跑 A→B→C 与 C→B→A 两次）
   - 结构化 JSON：`scores{6维} / confidence / issues[]{severity, category, message}`
   - 自一致性自检：每 condition 抽 10% 重复评 3 次，报方差

4. **人工盲评（§15.14，校准用 15-20 overlapping case）**：
   - 3 名独立评分者，互不讨论
   - condition 顺序随机化；同 case 内顺序也随机
   - 每 case 三任务：① 6 维 rubric 1-5 分 ② forced-choice 成对偏好 ③ 一句话理由
   - 一致性指标：Krippendorff's α / Fleiss' κ

5. **聚合（per-condition 报全量）**：
   - `mean_score` per 6 维（VLM 全量 + 人工子集）
   - `low_score_rate`（≤2 占比）
   - `high_confidence_issue_count`（VLM `issues[]` 中 confidence > 阈值）
   - `human_preference_distribution`（forced-choice 投票）

6. **校准（决定 VLM 全量分能否当主证据）**：
   - 在 15-20 overlapping case 上算 `human_VLM_spearman_rho` per dim
   - ρ > 0.7 → VLM 71 case 全量分作主证据
   - 0.4 ≤ ρ ≤ 0.7 → VLM 仅辅助，重要结论靠人工子集
   - ρ < 0.4 → VLM 降级为定性参考

**统计**：condition 间比较走 per-case 配对（同 case_id 配 3 condition），分数用 Wilcoxon、forced-choice 偏好用 Fleiss' κ + 多数投票，同 §11。

**硬边界**：
- 永不进 correctness gate；只评感知质量。
- 无人工校准时整节标 `human_teaching_quality: missing`，**不得用 VLM 全量分顶替人工**。
- VLM 全量分若校准未通过（ρ < 0.4），论文表 7 该列写 "not calibrated"，不写数字。


### 15.17 评 Stage2 Creative View 指标 —— [M] + [H/J]，展示层不证明 correctness

Stage2 Creative View 读取已通过 Stage1 release gate 的 verified artifact，再生成 creative/stage visual HTML。Stage2 的所有指标只回答展示层是否可运行、是否视觉可接受、是否保持对 verified artifact 的引用；**不得**写成算法 correctness 证据。

#### 15.17.1 `creative_attempted` —— [M] Stage2 尝试覆盖率

- 方法：统计有多少 Stage1 verified artifact 被送入 creative renderer。
- 数据来源：`creative_benchmark_report_merged.json` 的 `total_artifacts`、`creative_attempted`。
- 判定：`creative_attempted / total_artifacts`；未尝试的 case 必须列明原因。
- 边界：尝试生成不代表生成成功。

#### 15.17.2 `creative_generation_ok` —— [M] Creative HTML 生成成功率

- 方法：检查 creative renderer 是否产出 HTML 文件、是否通过 sanitizer/基本结构检查。
- 数据来源：`results[].creative_ok`、`results[].html`、generation report。
- 判定：HTML 存在、非空、未触发 sanitizer blocking error 为 true。
- 边界：该指标不证明浏览器可运行，也不证明视觉质量。

#### 15.17.3 `creative_browser_smoke_ok` —— [M] Creative 页面运行性

- 方法：Playwright 打开 creative HTML，检查页面加载、关键区域可见、无 console/page error。
- 数据来源：`results[].browser_smoke_ok`、browser smoke 日志。
- 判定：浏览器运行成功为 true；空白页、JS error、关键容器缺失、超时为 false。
- 边界：与 Stage1 一样，browser smoke 只证明可运行，不证明 correctness。

#### 15.17.4 `strict_visual_quality_ok` —— [M] 自动几何/布局审计

- 方法：Playwright + Chromium headless 加载页面，注入 JS 调 `getBoundingClientRect()` 算 rect 重叠 / 裁剪 / 文本遮挡 / 关键区不可见。
- 数据来源：`results[].last_strict_visual_quality_ok`、`stage_overlap_count`、`stage_clipped_count`、`stage_text_occlusion_count`、layout audit report。
- 判定：所有 strict blocking 几何问题为 0 时 true。
- **rect 法的结构性 false positive（解释 12/71 误报）**：透明 padding/margin、`overflow:hidden`/`clip-path` 截断、`visibility:hidden`/`opacity:0` 仍返回完整 rect、z-index 上层不透明遮蔽、canvas/SVG rect 占满但实际只画一角、line-height 内边距、sub-pixel 渲染。这些情况下 rect 数学说重叠但视觉无冲突。
- **改造（L1 算法层小修，纯 DOM）**：
  1. `getComputedStyle` 过滤 `visibility:hidden / opacity≈0 / display:none / 无 background+border+text` 的视觉无效元素
  2. 用 `clip-path / overflow:hidden / clip` 修正 rect（与 clip 区域取交得到实际可见 rect）
  3. sub-pixel 容差：rect 重叠 < 2px 不算
  4. `document.elementsFromPoint(x,y)` 在重叠区中心采样校验栈顶
- **改造（L2 兜底，L1 后 precision 仍 < 0.8 才上）**：rect 检出当候选区，截图小 patch 做颜色签名 / 像素差分确认。
- **必须做（L3 方法论）**：当作有测量误差的分类器报 precision/recall（doc15 #5）。在 15-20 labeled 子集上 vs 人工 ground truth 校准；主表写 `strict_pass = X/71 (precision=P, recall=R)`，**禁止写 "12/12 manual override"**。
- 边界：strict audit 是保守分类器；false 不等价于页面不可用，必须结合 §15.17.6 的人工/校准结果报告。

#### 15.17.5 `strict_visual_quality_flagged` —— [M] 自动审计标记数

- 方法：统计 strict visual audit 判为 failed/flagged 的 case 数。
- 数据来源：`creative_benchmark_report_merged.json` 的 `strict_visual_quality_flagged` 或逐 case audit 字段。
- 判定：按 case 聚合 flagged/total，并输出 flagged case 清单和原因分桶。
- 边界：不得把 flagged case 直接手工改写为 pass；应保留自动分类器原始输出。

#### 15.17.6 `manual_visual_acceptable` —— [H] 人工复审可接受性

- 方法：对 strict flagged case 做人工 Playwright 复审，记录是否存在阻塞性视觉问题。
- 数据来源：人工复审 CSV/markdown、截图、Playwright 复现路径。
- 判定：人工认为无阻塞性遮挡、裁剪、错位，且核心内容可读时为 true。
- 边界：人工复审不能覆盖掉 strict 指标；论文应同时报告 strict flagged 与 manual acceptable，并说明分歧。

#### 15.17.7 `strict_audit_precision_recall` —— [H] 校准后的审计器可信度

- 方法：把 strict visual audit 当作分类器，在人工标注子集上计算 precision/recall/F1。
- 数据来源：strict audit 输出 + 人工标签。
- 判定：以人工标签为 ground truth，报告 auditor precision/recall；若 precision 低，只能说 strict audit 保守，不能把全部 flagged 写成系统失败。
- 边界：这是解决 “strict 59/71 但人工 71/71” 诚信风险的必要校准。

#### 15.17.8 `layout_repair_attempts` —— [M] Stage2 布局修复成本

- 方法：统计 creative HTML 因 visual audit/browser smoke 失败进入 layout repair 的次数。
- 数据来源：`results[].layout_repair_attempts`、`layout_repair_retries`、attempt reports。
- 判定：报告 total/mean/p95，并按失败原因分桶。
- 边界：这是展示层成本指标，不进入 Stage1 token/correctness 主表。

#### 15.17.9 `creative_model_usage` —— [M] Stage2 模型成本

- 方法：聚合 Stage2 creative generation 和 layout repair 的 model calls、token、duration。
- 数据来源：`creative_benchmark_report_merged.json` 的 `model_calls` / summary model usage。
- 判定：报告 call_count、total_tokens、avg_total_tokens_per_attempted、llm_duration_s、avg_llm_duration_s_per_attempted。
- 边界：必须与 Stage1 成本分开报告，避免把展示层开销混进 correctness pipeline 成本。

## 16. 最终边界

论文必须坚持四条边界：

1. Stage1 机器 oracle gate（answer + trace replay）是 correctness 主证据。
2. Stage2 是 visual freedom / teaching presentation 证据，不是 correctness。
3. LLM/VLM 裁判只评 teaching/visual quality，需做偏差控制并与人工校准，永不进 correctness gate。
4. baseline、ablation、跨模型、unseen、VLM、人评各自回答不同 RQ，不能混成一个 pass rate。

这样的实验结构才能支撑 AAAI 叙事：AlgoLab 的贡献不是“生成更好看的网页”，而是把 LLM 生成拆成可执行算法语义、可验证 trace、确定性可视化编译和真实浏览器发布门禁，从而提升算法可视化生成的正确性、过程可审计性、跨模型稳定性与可复现性。
