# Expert Audit of Algorithmic Trace Fidelity：LLM 模拟预评估详细报告

> **证据状态：`SYNTHETIC_LLM_PREVIEW`**
> 本报告记录的是 LLM 设计并由固定脚本生成的模拟预评估数据，不是真实算法专家标注，不能在论文中写成“人工审计结果”或“专家验证结论”。

## 1. 实验目的

本实验用于预演正式的 **Expert Audit of Algorithmic Trace Fidelity**，检查计划中的抽样、标注、统计和论文结果表是否能够正常工作。

它希望模拟回答以下问题：

1. 完整 trace 是否忠实反映算法状态演化，而不是只在最后得到正确答案；
2. trace event 的 source line 是否与实际算法语句对齐；
3. 状态转移、算法操作和 explanation 是否相互一致；
4. 两位独立评审者是否能对 critical semantic error 和 trace-perfect 形成稳定判断；
5. 当前预设门禁在 60 题规模下是否足够严格。

本实验不评价页面视觉效果，也不用于验证 VLM 页面评分。五方法视觉人工校准是另一项独立实验。

## 2. 数据性质与证据边界

### 2.1 使用了哪些真实信息

模拟数据基于冻结的 Full-200 主实验报告：

```text
output/experiments/algotutorgen_full_200_20260706/
└── algolab_full_final/llm_benchmark_report.json
```

以下信息来自真实实验产物：

- 任务 ID 和题目名称；
- `family_id`；
- 每题的两个 variant ID；
- 每条 trace 的真实事件数量；
- Full-200 中各算法族的实际规模。

### 2.2 哪些数据是模拟的

以下内容不是人工或外部 LLM 实际审查结论，而是模拟标签：

- event-level source-line、状态转移、算法操作和解释一致性计数；
- variant-level critical error 和 trace-perfect；
- 两位模拟评审者 `LLM_SIM_A`、`LLM_SIM_B` 的标签；
- 第三方裁决后的 task/variant 结果；
- 由这些模拟标签计算出的置信区间、kappa 和门禁结果。

本轮没有调用两个外部 LLM 逐事件阅读完整 source 和 trace。具体做法是：由当前 LLM 设计一个不过度理想化的预期结果结构，再用固定 seed 的确定性脚本把该结构映射到真实任务元数据。因此，这是一份流程测试和论文表格预演数据，不是模型评审实验，更不是人工专家实验。

## 3. 样本设计

### 3.1 抽样规模

- 抽取任务：60 个；
- 覆盖算法族：23 个；
- 每题 variants：2 个；
- 完整 traces：120 条；
- trace events：3,883 个；
- 固定随机 seed：`20260723`。

### 3.2 分层抽样方法

抽样程序首先按 `family_id` 分组，并对每个任务计算由 seed 和任务 ID 决定的稳定哈希顺序：

1. 每个算法族优先选择两个不同任务；
2. 冻结 Full-200 中 `tree_dp` 只有一个任务，因此该族全取一个任务，不重复同一题；
3. 剩余名额从其他算法族的未选任务中按固定哈希顺序补足；
4. 最终得到 60 个不同任务，并覆盖全部 23 个算法族；
5. 同一 seed 重复运行会得到相同样本和相同模拟标签。

各算法族样本量如下：

| 算法族 | 任务数 | 算法族 | 任务数 |
| --- | ---: | --- | ---: |
| advanced_graph | 2 | array_pointer | 3 |
| backtracking_recursion | 2 | basic_graph | 6 |
| binary_search | 4 | dp_1d | 3 |
| dp_2d | 3 | dp_core | 3 |
| geometry_sweep | 2 | greedy | 2 |
| hash_map | 2 | heap_topk_huffman | 2 |
| linked_list_cache | 2 | math_bit | 3 |
| monotonic_stack | 2 | range_structure | 2 |
| shortest_path_mst | 3 | sorting | 2 |
| string_advanced | 3 | tree_bst_lca | 4 |
| tree_dp | 1 | trie | 2 |
| union_find | 2 |  |  |

## 4. 模拟标注方法

### 4.1 模拟原则

模拟数据遵循三个原则：

1. **总体偏向系统表现较好**：符合系统已经通过自动 oracle、schema、projection 和 invariant 检查的背景；
2. **不生成全满分结果**：保留 source-line、解释一致性和算法状态错误；
3. **不强行让全部门禁通过**：60 题中保留一个关键错误，使结果不能支持最强 correctness 主张。

### 4.2 Event-level 模拟字段

每条 variant 使用真实 event 数量，并生成以下汇总计数：

| 字段 | 含义 |
| --- | --- |
| `source_line_exact_count` | source line 与事件真实语句精确一致 |
| `source_line_adjacent_count` | 相邻一行，但语义位置明确 |
| `source_line_wrong_count` | 指向错误源码位置 |
| `source_line_unverifiable_count` | 无法确定唯一源码对应行 |
| `state_transition_correct/incorrect_count` | pre-state 到 post-state 是否正确 |
| `algorithmic_operation_correct/incorrect_count` | 操作是否符合目标算法 |
| `reason_state_consistent/inconsistent_count` | explanation 是否与状态和操作一致 |

常规 variant 使用较低的错误概率，并根据 task/variant 哈希加入小幅变化。三个指定 variant 被赋予不同类型的问题，以避免结果过于整齐。

### 4.3 Variant-level 模拟字段

每条 variant 生成：

- strategy fidelity；
- step completeness；
- temporal ordering；
- final-state consistency；
- critical semantic error；
- trace-perfect；
- simulated issue 及问题类型。

120 条 variants 中，117 条被模拟为 trace-perfect，3 条包含明确问题。其中只有1条被判为 critical semantic error，另外2条属于非关键但足以让整条 trace 不再被标记为 perfect 的质量问题。

### 4.4 两位模拟评审者

生成两套独立的 variant-level 模拟标签：

- `LLM_SIM_A`：115 条 trace-perfect、5 条非 perfect；2 条被标为 critical；
- `LLM_SIM_B`：115 条 trace-perfect、5 条非 perfect；1 条被标为 critical。

两位模拟评审者对大多数样本一致，但在两个边界 variant 上存在分歧。裁决结果单独存入 task/variant 汇总，不覆盖两位模拟评审者的原始标签。

## 5. 指标和统计方法

### 5.1 Task-level 主指标

任务是主统计单位，而不是把同一任务中的数十个相关事件当作独立样本。

**Trace-perfect task**：一题两个 variants 都是 trace-perfect，该任务才算通过。

\[
\widehat{p}_{\text{task-perfect}}
=\frac{N(\text{两个 variants 均 perfect})}{60}
\]

该指标报告 Wilson 95% 双侧置信区间。

**Critical-error task**：一题任一 variant 存在 critical semantic error，该任务即失败。

\[
\widehat{p}_{\text{critical}}
=\frac{N(\text{至少一个 critical variant})}{60}
\]

该指标报告 Clopper–Pearson 单侧 95% 上界。

### 5.2 Event-level 指标

Source-line 同时报告：

- event micro-average：所有可验证事件合并计算；
- task macro-average：先算每题比例，再对60题平均；
- task-cluster bootstrap 95% 区间：以任务为 cluster 重采样10,000次。

状态转移、算法操作和 reason-state consistency 在本模拟报告中作为描述性 event-level 指标。

### 5.3 双评审一致性

对 trace-perfect 和 critical-error 计算：

- 原始一致率；
- Cohen's \(\kappa\)。

\[
\kappa=\frac{p_o-p_e}{1-p_e}
\]

其中 \(p_o\) 为观察一致率，\(p_e\) 为根据两位评审者标签边际分布得到的随机一致率。

### 5.4 预设门禁

| 门禁 | 通过条件 |
| --- | --- |
| Trace-perfect task | Wilson 95% CI 下界不低于90% |
| Critical-error task | 单侧95%上界不高于5% |
| Source exact+adjacent | task-cluster 95% CI 下界不低于90% |
| 关键标签一致性 | Cohen's κ 不低于0.60 |

四项需同时满足，才能认为最强确认性门禁通过。

## 6. 总体结果

### 6.1 Task 和 variant 结果

| 指标 | 模拟结果 | 区间或说明 |
| --- | ---: | --- |
| Trace-perfect task | 57/60（95.0%） | Wilson 95% CI：86.3%–98.3% |
| Critical-error task | 1/60（1.7%） | 单侧95%上界：7.7% |
| Trace-perfect variant | 117/120（97.5%） | 描述性结果 |
| Critical-error variant | 1/120（0.8%） | 描述性结果 |

点估计显示整体表现较好，但样本量为60时，57/60 的 Wilson 下界只有86.3%；同时只要出现1个关键错误，critical-error rate 的单侧95%上界就上升到7.7%。因此，这两个门禁均未通过。

### 6.2 Event-level 结果

3,883 个模拟事件的计数如下：

| 指标 | 正确/对齐 | 问题事件 | 模拟比例 |
| --- | ---: | ---: | ---: |
| Source-line exact | 3,573/3,876 可验证事件 | — | 92.2% |
| Source-line adjacent | 237/3,876 可验证事件 | — | 6.1% |
| Source-line exact+adjacent | 3,810/3,876 | 66 wrong | 98.3% |
| Source-line unverifiable | — | 7/3,883 | 0.2% |
| State transition | 3,882/3,883 | 1 incorrect | 99.97% |
| Algorithmic operation | 3,882/3,883 | 1 incorrect | 99.97% |
| Reason-state consistency | 3,863/3,883 | 20 inconsistent | 99.5% |

Source exact+adjacent 的 task macro-average 为98.8%，task-cluster bootstrap 95%区间为98.5%–99.1%。该门禁通过。

### 6.3 模拟双评审一致性

| 标签 | 原始一致率 | Cohen's κ | 解释 |
| --- | ---: | ---: | --- |
| Trace-perfect | 118/120（98.3%） | 0.791 | 较强一致性 |
| Critical semantic error | 119/120（99.2%） | 0.663 | 实质一致性；受极低阳性率影响 |

两项 kappa 均超过0.60。Critical error 的原始一致率很高，但由于正例极少，kappa 会受到 prevalence effect 影响，因此必须同时报告原始一致率和标签分布。

## 7. 三个模拟问题案例

### 7.1 `lcs_length`：关键算法状态错误

- 题目：最长公共子序列长度；
- 算法族：`dp_core`；
- 受影响 variant：`v2`；
- variant 事件数：151；
- task 两个 variants 总事件数：265；
- 模拟错误：1个状态转移错误、1个算法操作错误、1个 reason-state 不一致；
- 裁决：`critical_semantic_error=yes`，`trace_perfect=no`。

该案例模拟“最终结果可能正确，但中间 DP 状态更新存在实质错误”的情况。因为错误会改变算法解释，所以属于 critical semantic error。它导致 `dp_core` 中1/3任务成为 critical-error task。

### 7.2 `articulation_bridges`：非关键 source-line 集中错误

- 题目：割点和桥；
- 算法族：`advanced_graph`；
- 受影响 variant：`v1`；
- variant 事件数：64；
- source exact：53；
- adjacent：4；
- wrong：7；
- 状态和算法操作错误：0；
- 裁决：`critical_semantic_error=no`，`trace_perfect=no`。

该案例的 task-level exact+adjacent rate 为94.5%。算法状态仍正确，但多个事件映射到不准确的源码位置，因此不能称为完美 trace；由于没有改变算法事实，本模拟将其归为非关键问题。

### 7.3 `permutations`：非关键 explanation 不精确

- 题目：全排列；
- 算法族：`backtracking_recursion`；
- 受影响 variant：`v1`；
- variant 事件数：133；
- reason-state inconsistent：14；
- 状态和算法操作错误：0；
- task-level reason consistency：93.5%；
- 裁决：`critical_semantic_error=no`，`trace_perfect=no`。

该案例模拟 explanation 对回溯状态描述不够准确，但没有改变实际状态和最终算法含义的情况，因此作为明显质量问题报告，但不升级为 critical semantic error。

## 8. 分算法族结果

以下均为模拟标签，只用于检查报告格式。每族样本量很小，不能据此进行可靠的族间优劣比较。

| 算法族 | 任务数 | Trace-perfect | Critical-error | Source exact+adjacent | Reason consistency |
| --- | ---: | ---: | ---: | ---: | ---: |
| advanced_graph | 2 | 1/2 | 0/2 | 96.4% | 99.3% |
| array_pointer | 3 | 3/3 | 0/3 | 99.3% | 100.0% |
| backtracking_recursion | 2 | 1/2 | 0/2 | 97.6% | 96.7% |
| basic_graph | 6 | 6/6 | 0/6 | 98.2% | 100.0% |
| binary_search | 4 | 4/4 | 0/4 | 100.0% | 100.0% |
| dp_1d | 3 | 3/3 | 0/3 | 99.4% | 100.0% |
| dp_2d | 3 | 3/3 | 0/3 | 100.0% | 100.0% |
| dp_core | 3 | 2/3 | 1/3 | 98.9% | 99.4% |
| geometry_sweep | 2 | 2/2 | 0/2 | 97.8% | 100.0% |
| greedy | 2 | 2/2 | 0/2 | 98.5% | 100.0% |
| hash_map | 2 | 2/2 | 0/2 | 98.0% | 100.0% |
| heap_topk_huffman | 2 | 2/2 | 0/2 | 98.8% | 100.0% |
| linked_list_cache | 2 | 2/2 | 0/2 | 100.0% | 100.0% |
| math_bit | 3 | 3/3 | 0/3 | 99.0% | 99.7% |
| monotonic_stack | 2 | 2/2 | 0/2 | 99.2% | 100.0% |
| range_structure | 2 | 2/2 | 0/2 | 99.4% | 100.0% |
| shortest_path_mst | 3 | 3/3 | 0/3 | 98.3% | 100.0% |
| sorting | 2 | 2/2 | 0/2 | 98.2% | 100.0% |
| string_advanced | 3 | 3/3 | 0/3 | 98.8% | 100.0% |
| tree_bst_lca | 4 | 4/4 | 0/4 | 99.6% | 100.0% |
| tree_dp | 1 | 1/1 | 0/1 | 97.4% | 100.0% |
| trie | 2 | 2/2 | 0/2 | 98.3% | 100.0% |
| union_find | 2 | 2/2 | 0/2 | 99.2% | 100.0% |

## 9. 门禁判断

| 门禁 | 模拟结果 | 是否通过 |
| --- | --- | --- |
| Trace-perfect task CI 下界 ≥ 90% | 下界86.3% | 否 |
| Critical-error 单侧上界 ≤ 5% | 上界7.7% | 否 |
| Source exact+adjacent CI 下界 ≥ 90% | 下界98.5% | 是 |
| 关键标签 κ ≥ 0.60 | 0.791、0.663 | 是 |
| 四项联合门禁 | 两项通过、两项失败 | **FAIL** |

这个结果是有意设计的：点估计看起来较好，但并没有轻易通过最强统计门禁。它说明在60题规模下，只出现一个关键错误仍不足以支持“关键错误率低于5%”的强主张。

## 10. 可以得到的模拟结论

如果真实人工审计得到相近结果，可以谨慎表述为：

> 在覆盖23个算法族的60任务审计中，95.0%的任务在两个 variants 上均达到 trace-perfect，source-line exact-or-adjacent rate 为98.3%。然而，审计发现1个包含关键算法状态错误的任务，使 task-level critical-error rate 的单侧95%上界达到7.7%；因此最强的5%关键错误率门禁没有通过。

但当前不能在论文中使用上述句子作为事实，因为本报告的数据是模拟生成的。当前只可以写：

> We prepared a preregistered 60-task expert-audit protocol and validated its sampling, annotation, adjudication, and statistical-analysis pipeline using clearly marked synthetic preview labels. Human expert labels remain pending.

## 11. 局限性

1. 模拟评审者没有真实阅读完整 trace，无法发现预设模式之外的新错误；
2. event-level 数据是汇总计数，不是逐事件人工标签；
3. 模拟分歧由固定规则生成，不能代表真实专家认知差异；
4. 当前 artifact 尚不能自动证明所有算法语义正确；
5. `tree_dp` 在 Full-200 中只有1个不同任务，无法满足每族至少2题；
6. 该数据不能用于证明系统正确、VLM 合理或人工评审已完成；
7. 不能把 `LLM_SIM_A/B` 描述成真人专家，也不能与真实人工标签合并后统一报告。

## 12. 正式实验应如何替换模拟数据

正式实验应保持相同的60题抽样和统计代码，但进行以下替换：

1. 冻结单执行插桩版本和 runtime-captured source line；
2. 为每条 trace 生成包含完整 source、pre-state、operation、post-state 和 explanation 的评审页面；
3. 两位算法专家独立审查120条完整 traces；
4. 保存逐事件和逐 variant 原始标签；
5. 第三位专家只裁决分歧，不覆盖原始标签；
6. 用真实标签重新生成 task、variant、event、family 和门禁表；
7. 如果发现关键错误并修复系统，应换新的 held-out confirmatory sample。

## 13. 复现方式与文件

生成命令：

```bash
TMPDIR=/ssd1/liaokunpeng/.tmp \
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 \
scripts/generate_llm_simulated_trace_audit_preview.py \
  --output-dir deliverables/plan2_final_results_20260723/llm_simulated_expert_trace_audit
```

相关文件：

| 文件 | 内容 |
| --- | --- |
| `simulation_summary.json` | 全部汇总指标、置信区间和门禁 |
| `simulated_task_results.csv` | 60题 task-level 数据 |
| `simulated_variant_results.csv` | 120条 variant-level 数据及事件汇总计数 |
| `simulated_reviewer_labels.csv` | 两位模拟评审者的240条标签 |
| `simulation_report.md` | 简版结果报告 |
| `DETAILED_EXPERIMENT_REPORT.md` | 本详细实验报告 |
| `scripts/generate_llm_simulated_trace_audit_preview.py` | 固定 seed 的数据生成脚本 |

所有输出均带有 `SYNTHETIC_LLM_PREVIEW` 或 `workflow_preview_only_not_human_evidence` 标记，以防与真实人工证据混淆。
