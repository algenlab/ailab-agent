# Expert Audit of Algorithmic Trace Fidelity

## 1. 实验定位

本实验用于回答：AlgoTutorGen 生成的完整算法轨迹是否忠实于真实程序执行和目标算法语义。

它与视觉人工校准完全分开：

- 本实验检查 source、状态转移、算法操作、步骤完整性和时间顺序；
- 五方法视觉人工校准检查页面质量及 VLM 评价的可靠性；
- 视觉分数不能替代本实验，也不能用于支持 source-to-trace correctness。

论文中将本实验称为 **Expert Audit of Algorithmic Trace Fidelity**。评审者知道材料来自 AlgoTutorGen，因此只能称为 independent expert audit，不能声称 method-blind。

## 2. 启动条件与证据边界

确认性人工审计应在单执行插桩版本冻结后进行。进入抽样池的 artifact 必须满足：

1. 答案与 trace 来自同一次 instrumented execution；
2. `code_line` 由运行时捕获，而不是由 LLM 填写；
3. source、input、trace 和最终答案具有不可变哈希；
4. 自动 schema、oracle、projection 和 invariant 检查已经完成；
5. 每题有两个可审查 variants。

当前 `p0_4_source_trace/human_review` 中的 40 题、80 variants、306 events 包每个 variant 最多抽取 4 个事件，只能作为旧架构下的探索性 source-line 风险抽查，不能用于计算本文定义的完整 trace-perfect task rate。

单执行插桩加强的是 source、execution 与 trace 的绑定。即使人工审计通过，也不能表述为“形式化证明所有 trace 正确”，只能表述为“在覆盖全部算法族的分层独立专家审计中得到支持”。

## 3. 预注册与数据冻结

任何人工标注开始前，负责人应冻结并记录：

- 数据集版本和 200 题抽样池；
- artifact、instrumented source 和 trace 的 SHA-256；
- 抽样 seed、随机化 seed 和抽样脚本版本；
- 本文的标签定义、critical error 定义和排除规则；
- 主指标、置信区间方法和通过门禁；
- 60 题确认性样本与 10 题 stress set 的名单；
- 两位评审者的分配表和页面顺序。

标注开始后不得根据结果修改标签含义、抽样规则或门禁。

## 4. 样本设计

### 4.1 确认性样本

从冻结的 200 题中分层抽取 60 个任务，每题审查两个 variants，共 120 条完整 traces。

抽样按以下顺序进行：

1. 对全部 23 个算法族原则上各随机抽取至少 2 题；冻结 Full-200 中 `tree_dp` 仅有 1 题，因此该族全取 1 题，不重复抽样、不把同题两个 variants 伪装成两题；
2. 因单例族少出的 1 个名额与其余名额一起按算法族在 Full-200 中的规模分配，最终仍为 60 个不同任务；
3. 在各族内部同时按 trace 长度三分位和结构复杂度分层；
4. 固定公开 seed 后执行一次抽样，不得人工替换“看起来异常”的题；
5. 如果某题因冻结前已定义的技术原因不可审查，只能按同一层中的预生成替补顺序替换，并记录原因。

任务是主统计单位。两个 variants 都满足 trace-perfect，任务才记为 trace-perfect；任一 variant 存在 critical semantic error，任务即记为 critical-error task。

若 60 个任务中观察到 0 个关键错误，二项分布精确单侧 95% 上界约为 4.87%，因此可以支持“审计样本中的 task-level critical-error rate 不高于约 5%”这一有限表述。

### 4.2 Stress set

另选 10 个最长或结构最复杂的任务作为 stress set，每题仍审查两个 variants。该集合是有意选择的困难样本，必须单独报告，不能并入 60 题确认性样本的比例、置信区间或门禁。

## 5. 评审者与独立性

- 两名具有算法课程、算法竞赛、程序验证或算法工程背景的评审者独立标注；
- 正式评审前可使用 4–6 条、不属于确认性样本和 stress set 的 traces 进行规则校准；
- 校准结束后冻结 codebook；
- 正式评审期间两人不得讨论任务、标签或疑似错误；
- 两人全部提交并锁定后，才生成分歧清单；
- 分歧由第三名算法专家裁决，原始标签不得覆盖或删除。

论文同时报告裁决前一致性和裁决后结果。

## 6. 随机化与信息隔离

负责人生成私有映射表，评审材料只显示不可反推题目顺序的 `audit_id` 和 `variant_id`。两名评审者使用不同的确定性随机顺序。

评审页面不得显示：

- 自动验证是否通过；
- 系统置信度；
- repair 次数；
- source-line 自动诊断结果；
- projection、invariant 或 Machine OK 结论；
- 另一位评审者的标签。

页面可以显示算法策略名称，因为 strategy fidelity 本身需要判断；也可以显示 AlgoTutorGen 名称，但论文不得据此声称 method-blind。

## 7. 每条 trace 的评审材料

每条完整 trace 应在一个连续页面中提供：

1. 题目描述；
2. 具体输入；
3. 期望结果；
4. 算法策略名称；
5. 带稳定行号的完整 instrumented source；
6. 完整、有序、不可省略的 trace；
7. 每个事件的 pre-state、operation、post-state；
8. 每个事件自动捕获的 source line；
9. 事件 explanation/reason；
10. 最终答案和最终状态。

评审者必须从头到尾查看完整 trace。不能只展示若干独立事件，因为步骤遗漏、重复和顺序颠倒只能在完整上下文中判断。

## 8. 标注字段

### 8.1 事件级标签

每个事件均填写以下字段：

| 字段 | 允许值 | 判定问题 |
| --- | --- | --- |
| `source_line_alignment` | `exact` / `adjacent` / `wrong` / `unverifiable` | 自动记录的行是否对应产生该事件的真实语句 |
| `state_transition` | `correct` / `incorrect` | pre-state 到 post-state 是否符合源码执行 |
| `algorithmic_operation` | `correct` / `incorrect` | 当前操作是否符合目标算法及当前上下文 |
| `reason_state_consistency` | `consistent` / `inconsistent` | explanation/reason 是否与实际状态和操作一致 |
| `error_type` | 预定义错误类型或空 | 错误属于索引、分支、值、顺序、遗漏、解释等哪一类 |
| `notes` | 自由文本 | 对错误位置给出可复核的简短依据 |

`unverifiable` 只能用于 source-line，例如事件是运行时合成事件且不存在唯一源码对应行。它不计入 exact+adjacent 的分母，但必须单独报告数量和原因。缺少必要状态材料时，不允许用 `unverifiable` 掩盖，应按预注册排除规则记录为材料缺陷。

### 8.2 Variant 级标签

完整查看一条 trace 后填写：

| 字段 | 允许值 | 含义 |
| --- | --- | --- |
| `strategy_fidelity` | `pass` / `fail` | trace 是否真正实现声称的算法策略 |
| `step_completeness` | `pass` / `fail` | 是否覆盖所有影响算法理解的关键步骤 |
| `temporal_ordering` | `pass` / `fail` | 步骤是否以正确执行顺序出现 |
| `final_state_consistency` | `pass` / `fail` | 最终状态是否支持最终答案 |
| `critical_semantic_error` | `yes` / `no` | 是否存在至少一个预定义关键错误 |
| `trace_perfect` | `yes` / `no` | 整条 trace 是否满足下述统一通过规则 |
| `critical_error_types` | 多选或空 | 关键错误类型 |
| `notes` | 自由文本 | 指明首个关键错误事件及理由 |

`trace_perfect=yes` 要求：没有 critical semantic error；不存在错误状态转移或错误算法操作；没有关键步骤遗漏、重复或颠倒；最终状态支持答案。相邻一行但语义清楚的 source-line、非关键措辞瑕疵和省略无教学意义的机械重复步骤不单独导致 trace-perfect 失败。

## 9. Critical semantic error 的冻结定义

以下任一情况均为关键错误：

- 状态变化违反 instrumented source 或算法规则；
- 使用错误分支、索引、节点、边、距离、堆元素或 DP 值；
- 事件顺序导致错误的算法解释；
- 遗漏对算法理解或正确状态演化必不可少的步骤；
- explanation 与实际状态矛盾，并导致错误算法含义；
- 最终答案正确，但中间过程存在实质算法错误；
- trace 声称使用某策略，实际执行的是不一致的策略。

以下默认属于非关键问题：

- source line 相邻一行但语义位置明确；
- 文案不够精确但不改变算法含义；
- 省略重复且无教学意义的机械步骤；
- 纯视觉措辞或格式问题。

若非关键问题累计后会使学习者形成错误算法理解，评审者可以升级为关键错误，但必须在 notes 中说明依据，并进入第三方裁决。

## 10. 正式执行流程

1. **材料自动校验**：检查 60 题、23 families、120 variants 是否齐全，事件连续、状态字段完整、哈希一致。
2. **评审校准**：两位评审者共同完成 4–6 条独立 calibration traces，统一规则但不进入正式统计。
3. **独立评审**：两人分别按照自己的随机顺序审完全部 120 条完整 traces，期间不得讨论。
4. **数据锁定**：检查缺失值和非法标签；只允许补填遗漏，不能根据另一人结果修改已有判断。
5. **裁决前分析**：计算原始一致率、Cohen's kappa/weighted kappa，并保留每位评审者的错误率。
6. **第三方裁决**：只处理分歧项，裁决表同时保存 A、B、裁决结果和裁决理由。
7. **主结果分析**：按 task 为主单位计算确认性指标；事件级指标采用 task-cluster bootstrap。
8. **Stress 分析**：独立计算 10 题困难集合，不并入主比例。
9. **门禁判断**：逐项报告通过或失败，不允许选择性省略失败项。
10. **修复后确认**：若发现关键错误，可以修复系统，但不得在同一 60 题上反复调试后宣称确认性通过；应从未看过的 held-out pool 重新抽取确认性样本。

## 11. 统计口径

### 11.1 主指标

- **Trace-perfect task rate**：一题两个 variants 均为 trace-perfect 的任务比例，报告 Wilson 95% 双侧置信区间；
- **Critical-error task rate**：至少一个 variant 有关键错误的任务比例，报告 Clopper–Pearson 单侧 95% 上界；
- **Trace-perfect variant rate**：120 个 variants 中 trace-perfect 的比例，同时用 task-cluster bootstrap 处理同题相关性；
- **Event-level transition accuracy**：先计算每题事件正确率，再以题为 cluster 重采样 10,000 次，报告 95% percentile interval；
- **Source-line exact rate** 和 **exact+adjacent rate**：主结果采用 task-macro 平均和 task-cluster bootstrap；事件 micro-average 仅作描述性补充；
- **分算法族错误分布**：报告分子/分母和错误类型，不对每族仅 2 题的比例作过强推断。

### 11.2 双人一致性

裁决前报告：

- 所有标签的原始一致率；
- 二元标签的 Cohen's kappa；
- `exact / adjacent / wrong` 的线性 weighted kappa；
- `unverifiable` 数量及其一致率；
- critical error、trace-perfect 以及四项 variant 标签的一致性。

如果某个标签在两位评审者中都只有单一类别，例如所有任务均被判为“无关键错误”，kappa 因无方差可能为未定义。此时应报告 `kappa = NA (single-category prevalence)`、原始一致率和标签分布，不能把理想的全阴性结果错误判为一致性门禁失败。

### 11.3 预设门禁

确认性主张需要同时满足：

1. task-level trace-perfect 的 95% CI 下界不低于 90%；
2. critical-error task rate 的单侧 95% 上界不高于 5%；
3. source-line exact+adjacent 的 95% CI 下界不低于 90%；
4. 有两个以上实际类别的关键标签，其 kappa 不低于 0.60；若标签退化为单一类别，则原始一致率需不低于 95%，并按上一节报告 kappa 为 NA。

门禁判断以 60 题确认性样本的裁决后标签为准；评审可靠性使用裁决前标签。Stress set 不参与门禁。

## 12. 数据文件

建议固定以下文件，视觉人工校准数据不得放入本目录：

```text
expert_trace_audit/
├── protocol.md
├── frozen_manifest.json
├── sample_coverage.csv
├── reviewer_a/
│   ├── event_labels.csv
│   └── variant_labels.csv
├── reviewer_b/
│   ├── event_labels.csv
│   └── variant_labels.csv
├── adjudication/
│   ├── event_disagreements.csv
│   └── variant_disagreements.csv
├── stress_set/
│   └── ...
├── audit_statistics.json
└── audit_report.md
```

私有映射表单独保存，不提交给评审者。原始 A/B 标签只读保留；裁决结果写入新文件，不能覆盖原始数据。

## 13. 论文结果表模板

### 13.1 主结果

| 指标 | 分子/分母 | 估计值 | 95% CI 或单侧上界 | 门禁 | 结果 |
| --- | --- | --- | --- | --- | --- |
| Trace-perfect task | 待人工评估 | 待人工评估 | Wilson 95% CI | 下界 ≥ 90% | Pending |
| Critical-error task | 待人工评估 | 待人工评估 | 单侧 CP 95% 上界 | 上界 ≤ 5% | Pending |
| Trace-perfect variant | 待人工评估 | 待人工评估 | task-cluster bootstrap | 描述性 | Pending |
| Source-line exact | 待人工评估 | 待人工评估 | task-cluster bootstrap | 描述性 | Pending |
| Source-line exact+adjacent | 待人工评估 | 待人工评估 | task-cluster bootstrap | 下界 ≥ 90% | Pending |
| State-transition accuracy | 待人工评估 | 待人工评估 | task-cluster bootstrap | 描述性 | Pending |

### 13.2 裁决前一致性

| 标签 | 原始一致率 | Cohen's κ / weighted κ | 标签分布 | 备注 |
| --- | --- | --- | --- | --- |
| Source-line alignment | Pending | Pending | Pending | 三分类 weighted κ；unverifiable 单报 |
| State transition | Pending | Pending | Pending | 二元 κ |
| Algorithmic operation | Pending | Pending | Pending | 二元 κ |
| Reason–state consistency | Pending | Pending | Pending | 二元 κ |
| Critical semantic error | Pending | Pending | Pending | 单一类别时 κ=NA |
| Trace perfect | Pending | Pending | Pending | 单一类别时 κ=NA |

### 13.3 错误类型

| 错误类型 | Event 数 | Variant 数 | Task 数 | 涉及 families | 代表性说明 |
| --- | --- | --- | --- | --- | --- |
| 状态转移错误 | Pending | Pending | Pending | Pending | Pending |
| 分支/索引/节点错误 | Pending | Pending | Pending | Pending | Pending |
| 时间顺序错误 | Pending | Pending | Pending | Pending | Pending |
| 关键步骤遗漏 | Pending | Pending | Pending | Pending | Pending |
| explanation 矛盾 | Pending | Pending | Pending | Pending | Pending |
| 策略不一致 | Pending | Pending | Pending | Pending | Pending |

在两位专家完成正式标注前，所有结果必须保持 `Pending`，不得使用 LLM、VLM 或自动诊断结果预填人工标签。
