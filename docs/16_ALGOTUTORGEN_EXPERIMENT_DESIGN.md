# AlgoTutorGen 实验设计方案

本文档保留实验设计决策；当前实验结果统一见 `docs/EXPERIMENT_RESULTS.md`。

生成日期：2026-07-04  
依据：`plan.md`、当前 `output/experiments` 结果、Stage2 Creative 复跑结果

## 1. 实验定位

`plan.md` 给出的论文空间不是“把算法动画网页做得更好看”，而是：

> LLM-generated verifiable interactive algorithm learning environments

因此实验评估的主线应从“视觉效果”转向“可执行、可验证、可交互、可教学评估”。强 direct HTML baseline 肉眼效果可以很好，这不是坏事，反而能让论文主张更清晰：AlgoTutorGen 的优势不应写成视觉碾压，而应写成**过程语义可复核、交互反馈可校验、教学内容与 trace 对齐、失败可定位且可修复**。

本文档把实验目标拆成五个层级：

1. 过程准确性：算法答案、逐步状态、trace、oracle 是否一致。
2. 交互准确性：checkpoint、quiz、hint、反馈是否绑定到正确算法状态。
3. 教学性：讲解是否覆盖关键学习目标，是否与当前步骤语义一致。
4. 视觉与可用性：页面是否可运行、可读、响应式、布局无严重问题。
5. 可复现与成本：是否有结构化 artifact、报告、repair 记录、token/time 成本。

## 2. 核心研究问题

| RQ | 问题 | 主要证据 | 结论边界 |
|---|---|---|---|
| RQ1 | 系统能否稳定生成可运行的交互式算法学习环境？ | release gate、browser smoke、interaction coverage | 可以证明可运行与结构完整 |
| RQ2 | 生成环境的算法过程是否准确？ | answer oracle、trace replay、DOM-vs-artifact、一致性检查 | correctness 主证据，只用机器 gate |
| RQ3 | 交互是否真正语义正确，而不只是按钮存在？ | Playwright 交互审计、quiz oracle、hint groundedness、mutation-free check | 新论文最关键差异点 |
| RQ4 | 相比 LLM direct，AlgoTutorGen 的优势在哪里？ | common observable metrics + 过程/交互 gate 对比 | 不把 AlgoLab 私有 release gate 强加给 baseline |
| RQ5 | 教学与视觉质量是否足够好？ | 盲评、LLM/VLM judge、人工小样本、Stage2 visual audit | 不作为 correctness 证据 |
| RQ6 | repair、结构化 IR、SceneGraph、interaction 层各贡献多少？ | ablation、first-try vs repaired、failure phase shift | 解释系统设计价值 |
| RQ7 | 成本是否可接受？ | model calls、tokens、duration、repair rounds | 用于工程可行性与局限性 |

## 3. 实验条件

### 3.1 主系统

**AlgoTutorGen / AlgoLab full**

- LLM 生成算法语义候选、teaching blueprint、interaction spec。
- 系统执行 reference/oracle、trace validation、SceneGraph compile、HTML render、browser smoke。
- 这是论文 correctness 主条件。

当前已有结果：

- 15-case pilot：15/15 PASS。
- family-core：23/23 PASS。
- held-out/unseen-task：15/15 PASS。
- interaction coverage：15/15 满足 `plan.md` baseline，每题至少 3 个交互点；平均 9.53 个交互点。
- browser audit：30/30 desktop/mobile 记录通过。

### 3.2 强 baseline

**Direct HTML baseline**

- LLM 直接生成完整离线 HTML。
- prompt 必须足够强，包含 timeline、状态、checkpoint、hint、answer reveal、feedback、learning log。
- 不应使用弱 prompt 来制造优势。
- 与主系统只比较共同可观测指标：页面可运行、可见答案、交互可达、教学盲评、视觉盲评。
- 不进入 AlgoLab 的 trace/SceneGraph/release gate 分母，因为 direct HTML 没有同构 artifact。

建议保留两个 baseline 口径：

| Baseline | 作用 |
|---|---|
| Direct HTML expected-visible | 强上界，证明 LLM direct 在视觉与页面生成上并不弱 |
| Direct HTML hidden-expected | 更公平地测试答案与过程是否能从题目本身推导 |

### 3.3 Ablation

| 条件 | 目的 |
|---|---|
| no-process-validator | 测过程 sanity 层对失败定位与 release gate 的贡献 |
| no-SceneGraph-compiler | 测确定性可视化编译层的贡献 |
| no-interaction | 隔离 interaction 层对学习环境的贡献 |
| no-repair | 测 repair loop 的贡献，用 first-try pass rate 支撑 |
| Stage2 Creative off/on | 证明 creative stage 是展示增强层，不是 correctness gate |

### 3.4 Stage2 Creative

Stage2 不作为算法 correctness gate。它回答：

- 在 verified Stage1 artifact 上，能否生成更有场景化表达的 creative view？
- visual quality 是否足以作为论文 figure / demo？
- strict visual audit 与人工视觉可接受性是否一致？

当前已有两个 final：

| Final | 结果 |
|---|---|
| mixed-model final | 15/15 creative_ok，15/15 strict visual |
| DeepSeek-V4-Pro-only final | 15/15 creative_ok，15/15 strict visual |

论文中应写：Stage2 是 presentation enhancement，不替代 Stage1 correctness。

## 4. 数据集与分母

### 4.1 当前可立即使用的数据

| 数据 | 数量 | 用途 |
|---|---:|---|
| 15-case pilot | 15 | 交互覆盖、浏览器审计、Stage2 creative 展示 |
| family-core | 23 | 每个算法族至少 1 题的主系统覆盖 |
| held-out/unseen-task | 15 | 支持族内新题泛化 |
| deterministic benchmark manifest | 约 73 cases / 261 samples | family 分布、扩展评估和论文附录 |

注意：当前 held-out/unseen 更准确地说是 **held-out tasks within supported families**，不要写成完全新算法族泛化，除非后续真的补充全新 family。

### 4.2 按 `plan.md` 的扩展数据

`plan.md` 建议长期构建 200-500 个算法学习环境任务。当前不建议把它作为论文第一版阻塞项。更稳的路线：

1. 第一版实验先用当前 15 + 23 + 15 + deterministic manifest。
2. 若写作时发现某些 family 薄弱，再补 20-30 个 synthetic/open-source tasks。
3. LeetCode-derived 任务只做 private stress test；公开 benchmark 优先用 synthetic/open-source tasks。

## 5. 指标定义

### 5.1 生成成功率

| 指标 | 定义 |
|---|---|
| `generation_success_rate` | LLM 输出可解析候选的比例 |
| `materialization_success_rate` | 候选可执行并生成 artifact 的比例 |
| `browser_smoke_ok_rate` | 页面可由浏览器加载且核心控件存在 |
| `final_release_pass_rate` | answer + trace + scene + teaching + browser 全部通过 |
| `first_try_pass_rate` | 不经 repair 的首次通过率 |
| `repair_success_rate` | repair 后由失败转成功的比例 |

论文中应同时报告 first-try 与 final pass，避免 100% 看起来像零成本。

### 5.2 过程准确性

| 指标 | 评估方式 | 是否 correctness 主证据 |
|---|---|---:|
| final output accuracy | solver result vs expected/oracle | 是 |
| trace result consistency | `trace.result` vs solver result | 是，但属于自一致 |
| per-step state equivalence | 独立重执行得到的状态序列 vs trace frames | 是 |
| invariant violation count | family-specific 或 lightweight process sanity | 是，但需如实描述强度 |
| DOM-vs-artifact fidelity | Playwright 抽取 DOM 状态 vs artifact JSON | 是 |
| metamorphic consistency | 节点重命名、输入缩放等变形测试 | 是，尤其适合 held-out |
| gate rejection rate | 注入错误后 release gate 是否拒绝 | 是，建议新增 |

重点建议：必须补一个 **Gate Soundness / Fault Injection** 实验。只报告 pass rate 不够，审稿人会问 gate 是否会拒绝错误产物。

建议注入错误：

- 篡改 solver final answer。
- 篡改 `trace.result`。
- 删除关键步骤或调换 frame 顺序。
- 修改 frame 中的关键状态值。
- 让 quiz oracle 的正确答案反转。
- 让 hint 引用不存在的状态或错误 invariant。

主指标：

```text
gate_rejection_rate = rejected_faulty_artifacts / injected_faulty_artifacts
false_accept_rate = accepted_faulty_artifacts / injected_faulty_artifacts
```

### 5.3 交互准确性

`plan.md` 的核心要求是每题至少 3 个可自动判分的交互任务。当前系统已经超过最低要求，但还需要把“交互是否准确”评估得更硬。

| 指标 | 定义 |
|---|---|
| `interaction_checkpoint_coverage` | 每题 checkpoint 数量与关键学习帧覆盖率 |
| `quiz_answer_correctness` | quiz/judge 的正确答案是否由 oracle 支撑 |
| `action_reachability` | 每个控件/交互路径是否可由 Playwright 到达 |
| `feedback_correctness` | 正误反馈是否与 oracle 一致 |
| `hint_groundedness` | hint 是否只引用 trace/pseudocode 中存在的事实 |
| `invalid_action_handling` | 错误输入/错误点击是否给出合理反馈且不崩溃 |
| `interaction_mutation_free_ok` | 答题、hint、跳帧不应篡改算法事实 |
| `no_dead_end_ui_state` | 任意交互后仍可继续 step/reset/export |

建议 Playwright 流程：

```text
load page
→ click next / previous / timeline tick
→ answer one correct quiz
→ answer one wrong quiz
→ request hint
→ reset
→ verify DOM state equals artifact state
→ verify learning log updated
```

### 5.4 教学性

教学性不建议只靠自动分数下结论。应拆成“机器可检查的一致性”和“人/裁判可评价的质量”。

机器指标：

| 指标 | 定义 |
|---|---|
| learning objective coverage | 关键学习目标是否在 explanation / checkpoint 中出现 |
| frame-explanation alignment | 当前 frame 的讲解是否引用当前状态，而非前后错位 |
| misconception coverage | 是否覆盖常见错误或边界情况 |
| answer-frame checkpoint present | 最终答案帧是否有交互检查点 |
| hint trace-groundedness | hint 是否能映射到 trace step / state |

人工或 LLM-as-judge 指标：

| 指标 | 评分 |
|---|---|
| clarity | 1-5 |
| step-by-step usefulness | 1-5 |
| cognitive load | 1-5，越低越好 |
| encourages prediction | 1-5 |
| explanation naturalness | 1-5 |

注意：LLM/VLM judge 只用于 teaching/visual quality，不进入 correctness gate。

### 5.5 视觉与可用性

视觉不作为主胜点，但需要证明“足够好”。

机器指标：

- browser smoke pass rate。
- console/page error count。
- layout overlap count。
- clipped text count。
- text occlusion count。
- desktop/mobile responsive pass。
- frame switch latency。

感知指标：

- 人工盲评：AlgoTutorGen Stage1、Stage2、Direct HTML 三者截图随机排序。
- 维度：视觉吸引力、信息层次、可读性、算法状态清晰度、交互 affordance。
- 论文措辞应保守：direct HTML 可能视觉接近；AlgoTutorGen 的强项是可验证语义。

### 5.6 成本与 repair

| 指标 | 定义 |
|---|---|
| model calls per success | 每个成功产物的调用次数 |
| total tokens per success | 每个成功产物的 token 成本 |
| duration per success | 每个成功产物耗时 |
| repair rounds | 每题 repair 次数 |
| failure phase distribution | generation / materialization / trace / scene / browser / interaction |

## 6. 实验矩阵

### E1. 主系统 release gate

目的：证明当前系统能生成可运行、可验证的交互式算法学习环境。

条件：

- AlgoLab full on 15-case pilot。
- AlgoLab full on family-core。
- AlgoLab full on held-out tasks。

报告：

- total / passed / pass rate。
- first-try vs repaired。
- failure types。
- tokens/time。
- interaction coverage。
- browser audit。

### E2. Direct HTML strong baseline 对比

目的：承认 direct HTML 视觉强，同时检验其语义证据不足。

条件：

- Direct HTML expected-visible。
- Direct HTML hidden-expected。
- AlgoTutorGen full。

共同指标：

- page load success。
- visible final answer match。
- interaction controls reachable。
- feedback rendered。
- teaching blind rating。
- visual blind rating。

AlgoTutorGen 专属指标单独报告：

- trace validation。
- SceneGraph compile。
- interaction oracle。
- release gate。

### E3. 交互准确性审计

目的：证明交互不是装饰。

样本：

- 15-case pilot 全量。
- 每题至少抽 3 个 checkpoint。

指标：

- quiz answer correctness。
- feedback correctness。
- hint groundedness。
- invalid action handling。
- interaction mutation-free。
- no dead-end UI state。

### E4. Gate soundness / fault injection

目的：证明 gate 不只是会放行正确产物，也会拒绝错误产物。

样本：

- 从 15-case pilot 或 23 family-core 中抽样。
- 每题注入 3-5 类错误。

报告：

- rejection rate by fault type。
- false accept examples。
- 哪些错误当前 gate 不能发现，作为 limitation。

### E5. 教学质量评估

目的：比较“讲得是否有用”，而非只比较页面是否好看。

短期技术论文方案：

- 3 名算法/教育背景 evaluator。
- 15 case blind rating。
- 条件：AlgoTutorGen Stage1、Stage2、Direct HTML。
- 指标：clarity、step alignment、prediction usefulness、hint usefulness、cognitive load。

更完整的人类学习实验：

- 60-120 名 CS1/CS2 学生。
- pre-test / post-test / transfer test。
- 条件：static explanation、direct HTML、AlgoTutorGen interactive。
- 指标：learning gain、time-on-task、confidence、SUS、NASA-TLX。

当前如果冲 AAAI/技术论文，建议先做小规模专家盲评；CHI/AIED 再做完整 user study。

### E6. Stage2 Creative 视觉补充

目的：证明系统可以在 verified artifact 上生成更好的展示层。

条件：

- Stage1 deterministic runtime。
- Stage2 mixed-model final。
- Stage2 DeepSeek-V4-Pro-only final。
- Direct HTML baseline。

指标：

- strict visual pass。
- browser smoke。
- layout repair。
- visual blind rating。
- selected HTML manifest 完整性。

解释：

- Stage2 只证明 presentation enhancement。
- 不把 Stage2 成功写成算法 correctness。

### E7. Ablation

目的：解释各模块为什么需要。

条件：

- full。
- no-interaction。
- no-process-validator。
- no-SceneGraph-compiler。
- no-repair。

报告：

- release pass rate drop。
- interaction frames drop。
- failure phase shift。
- tokens/time。
- repair burden。

当前已有 no-interaction component ablation，能证明移除 interaction 层后 interaction frames 从 143 变成 0。

## 7. 论文主表建议

### Table 1. Main Results

| Condition | Cases | Pass | Browser | Interaction Coverage | Tokens | Duration |
|---|---:|---:|---:|---:|---:|---:|
| AlgoTutorGen pilot | 15 | 15/15 | 30/30 audit | 15/15 | ... | ... |
| Family-core | 23 | 23/23 | ... | ... | ... | ... |
| Held-out tasks | 15 | 15/15 | ... | ... | ... | ... |

### Table 2. Direct Baseline Comparison

| Condition | Page Runs | Visible Answer | Interaction Reachable | Trace Gate | Interaction Oracle | Teaching Rating | Visual Rating |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct HTML | ... | ... | ... | N/A | N/A | ... | ... |
| AlgoTutorGen | ... | ... | ... | ... | ... | ... | ... |

### Table 3. Interaction Correctness

| Case | Checkpoints | Quiz Oracle | Feedback Correct | Hint Grounded | Mutation-free | Dead-end-free |
|---|---:|---:|---:|---:|---:|---:|

### Table 4. Gate Soundness

| Fault Type | Injected | Rejected | False Accepted | Rejection Rate |
|---|---:|---:|---:|---:|

### Table 5. Ablation

| Variant | Pass | Interaction Frames | Browser | Tokens | Failure Shift |
|---|---:|---:|---:|---:|---|

### Table 6. Stage2 Visual

| Condition | Cases | Creative OK | Browser | Strict Visual | Visual Rating |
|---|---:|---:|---:|---:|---:|

## 8. 建议优先级

P0：马上做，直接决定论文可信度。

1. Direct HTML baseline 的交互/语义审计，不只看页面能否打开。
2. Gate soundness / fault injection。
3. Interaction correctness audit：quiz、feedback、hint、mutation-free。
4. 把现有结果整理成 Table 1 / Table 5 / Stage2 table。

P1：增强论文说服力。

1. 教学质量专家盲评。
2. Stage2 vs Direct HTML 视觉盲评。
3. held-out task 命名修正与 family 分布表。
4. no-repair / no-interaction 补齐。

P2：时间允许再做。

1. 20-30 个 open-source/synthetic 新任务扩展。
2. 多模型重复运行和方差。
3. 学生用户实验。

## 9. 预期结论写法

建议写：

- AlgoTutorGen 能生成可执行、可验证、可交互的算法学习环境。
- 相比 direct HTML，AlgoTutorGen 的关键优势是结构化 trace、机器 gate、交互 oracle、可复核过程语义。
- Direct HTML 在视觉上可以很强，但缺少同等级别的过程证据和交互语义保证。
- Stage2 Creative 说明 verified artifact 也能生成高质量展示层，但不承担 correctness claim。

不建议写：

- 不要说 AlgoTutorGen 页面一定比 direct HTML 更漂亮。
- 不要说当前系统证明了任意算法泛化。
- 不要说 LLM/VLM judge 证明 correctness。
- 不要把 held-out tasks 写成完全新算法族泛化。
- 不要用 Stage2 visual pass 代替 Stage1 release gate。

## 10. 当前最务实的下一步

如果目标是尽快进入论文实验结果阶段，建议按以下顺序推进：

1. 固化当前 `output/experiments` 的结果索引和主表。
2. 给 direct HTML baseline 增加同样的浏览器交互审计。
3. 给 AlgoTutorGen 和 direct HTML 各做 15-case 的交互语义对比。
4. 做 fault injection，报告 gate rejection rate。
5. 再决定是否补小规模专家盲评。

这样论文不会被“LLM direct 看起来也很好”削弱，因为主张会从视觉审美转移到可验证学习环境。
