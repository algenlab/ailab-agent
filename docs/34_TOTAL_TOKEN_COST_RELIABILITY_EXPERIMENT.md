# Total Token Cost-Reliability 实验报告

## 1. 实验状态

实验二已完成。分析复用冻结的 Full-200 日志，没有新增模型调用，也没有把不同批次的 Direct 初始页与 repair 结果拼接。200 个任务的 case ID 在 Direct、AlgoTutorGen 生成报告和 AlgoTutorGen Machine OK 报告之间严格一致。

本实验回答：Direct HTML 的可靠性差距是否只是模型 token 预算较少造成的；当 Direct 获得与 AlgoTutorGen 相近、甚至更高的实际模型成本时，能否追上 AlgoTutorGen 的 Machine OK。

## 2. 数据来源

| 数据 | 文件 | SHA-256 |
|---|---|---|
| Direct 初始页与最多 5 轮修复 | `output/experiments/direct_browser_repair_fair_20260723/fair_repair_report.json` | `19a2aab458b5f807534c2f91761bb4de2aae714fb94dc71fd0f3959feb785c9d` |
| AlgoTutorGen 模型 usage | `output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json` | `06aa770d5ec7be9cb32862f4ff420acb9cdab2d7d08112d170d93dbd36094112` |
| AlgoTutorGen Machine OK | `output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine_rendered_text/interaction_semantic_eval_report.json` | `b31a60d335cecab269a48e9d49fcb26a65e0c4128453e2f86e8d411099259b4d` |

Direct 的 200 个初始调用和 417 个 repair 调用均有完整 API usage。初始调用共 3,935,488 tokens，repair 共 15,647,489 tokens，最大策略总计 19,582,977 tokens。token 统一采用 API 返回的 `prompt_tokens + completion_tokens`，不是本地估算。

## 3. 冻结分析协议

### 3.1 固定 repair-budget 曲线

对每题重放：

```text
TotalTokens(i, r) = InitialDirectTokens(i) + RepairTokens(i, 1...r)
```

`r` 为最多修复次数。沿用原实验的 early stop 和 best-so-far；某题一旦 Machine OK，后续不再调用。

### 3.2 每题硬 token-cap 曲线

初始 Direct 调用是不可避免的已发生成本，始终计入。repair 只能整次纳入；如果加入下一次完整调用会超过 cap，则在调用前停止，不按 token 比例截断模型响应。Machine OK 使用已纳入版本中的 best-so-far，因此后续页面退化不会抹掉此前成功。

`84.4k tokens/题` 是 AlgoTutorGen 的全样本平均成本，不等同于 `每题硬 cap=84.4k`。后者因为初始成功即停止，实际 Direct 均值只有 39.6k。实验因此同时报告：

1. 字面硬-cap 重放，展示 cap 策略本身的行为；
2. 在冻结日志所有可实现硬 cap 中，寻找实际平均成本最接近 AlgoTutorGen 平均成本的点，作为主比较。

### 3.3 统计

主预算为 AlgoTutorGen operational all-attempt 成本；selected-final 为敏感性分析。二元结果按同一 case ID 配对，差值定义为 `AlgoTutorGen - Direct`。报告 10,000 次配对 bootstrap 95% CI 和双侧 exact McNemar 检验。曲线其余点只作描述，不逐点做显著性检验。

## 4. 固定 Repair-Budget 结果

| 最大修复次数 | 总 tokens/题 | Machine OK | 模型调用/题 | API latency/题 |
|---:|---:|---:|---:|---:|
| 0 | 19,677.440 | 106/200 (53.0%) | 1.000 | 207.241 s |
| 1 | 36,082.840 | 118/200 (59.0%) | 1.470 | 301.292 s |
| 2 | 51,056.595 | 119/200 (59.5%) | 1.880 | 384.316 s |
| 3 | 66,327.380 | 120/200 (60.0%) | 2.285 | 466.357 s |
| 5 | 97,914.885 | 120/200 (60.0%) | 3.085 | 632.044 s |

修复收益在第 3 次后饱和。最大预算相对初始增加 78,237.445 tokens/题，但 Machine OK 只从 106 增至 120。

## 5. AlgoTutorGen 成本

| 成本口径 | 总 tokens | tokens/题 | 模型调用/题 | API latency/题 | Machine OK |
|---|---:|---:|---:|---:|---:|
| selected-final lineage | 15,369,433 | 76,847.165 | 5.330 | 573.940 s | 198/200 |
| operational all-attempt | 16,870,557 | 84,352.785 | 5.755 | 629.222 s | 198/200 |

selected-final 只汇总最终采用结果的调用链。all-attempt 还计入主运行中被丢弃的候选和 5 题 retry 的失败/替换尝试，是实际运行成本，因此作为主口径。

现有日志没有独立的“纯本地编译”计时。selected-final 的流水线总时间为 114,848.991 s，API 调用时间为 114,787.917 s，只能恢复 61.074 s 的非模型流水线残差，其中还混有编译、渲染和调度开销；render phase 单独为 5.623 s。all-attempt 被丢弃路径的本地阶段无法从合并报告完整恢复。报告不把该残差误标为纯编译时间。

## 6. 主比较：Operational All-Attempt

Direct 硬 cap `192,625 tokens/题` 时，实际平均成本为 84,254.445 tokens/题，与 AlgoTutorGen 的 84,352.785 相差 98.340 tokens/题。结果为：

| 条件 | 实际 tokens/题 | Machine OK |
|---|---:|---:|
| AlgoTutorGen all-attempt | 84,352.785 | 198/200 (99.0%) |
| Direct cost-matched replay | 84,254.445 | 120/200 (60.0%) |

配对结果：

- 差值：`+39.0` 个百分点，方向为 AlgoTutorGen - Direct；
- paired-bootstrap 95% CI：`[+32.0, +46.0]` 个百分点；
- discordant pairs：AlgoTutorGen-only `80`，Direct-only `2`；
- exact McNemar：`p = 1.4078614e-21`。

在几乎相同的实际平均 token 成本下，Direct 少通过 78 题。

## 7. 敏感性分析

### 7.1 Selected-Final 成本匹配

Direct 硬 cap `175,808` 时实际使用 76,854.000 tokens/题，与 AlgoTutorGen selected-final 的 76,847.165 相差 6.835 tokens/题。Machine OK 仍为 120/200 对 198/200；差值 `+39.0` 个百分点，95% CI `[+32.0, +46.0]`，McNemar `p = 1.4078614e-21`。

### 7.2 字面硬 Cap

| Direct 每题硬 cap | Direct 实际 tokens/题 | Direct Machine OK |
|---:|---:|---:|
| 76,847.165 | 36,820.645 | 118/200 |
| 84,352.785 | 39,568.835 | 118/200 |

这两个点不是平均成本匹配点，只用于说明逐题 cap 与全样本平均成本的区别。

### 7.3 Direct 最大已观察预算

Direct 最多 5 次 repair 使用 97,914.885 tokens/题，比 AlgoTutorGen all-attempt 高 13,562.100 tokens/题，即高 16.1%；API latency 也为 632.044 s/题，对比 629.222 s/题。Machine OK 仍为 120/200，而 AlgoTutorGen 为 198/200。由于第 3 到第 5 次修复没有新增 Machine OK，这部分额外成本没有转化为可靠性收益。

## 8. 结论

在冻结的 200 题、Direct 初始页面、浏览器反馈器、整页重写方式、DeepSeek-V4-Pro 和最多五次 repair 的策略范围内，结果支持：可靠性差距不能由 Direct 模型 token 预算更低单独解释。Direct 在实际平均成本与 AlgoTutorGen 几乎相同、以及成本更高时，都停留在 120/200；AlgoTutorGen 为 198/200。

可用于论文的保守表述是：

> Under the frozen whole-page browser-repair policy, matching operational model-token cost did not close the reliability gap: AlgoTutorGen achieved 198/200 Machine OK versus 120/200 for Direct at nearly equal realized token cost.

该实验不是严格因果消融。两种方法承担的生成职责和工程组件不同；结果不能外推为“所有 Direct/browser repair 永远无法达到 99%”，也不能区分固定 shell、结构化表示、验证器和候选选择各自的独立因果贡献。

此外，当前 AlgoTutorGen 数据来自 `solve(input_data)` 与 `trace(input_data)` 分别执行的旧系统。迁移到论文描述的单执行架构后，Direct 曲线可以继续作为冻结对照，但 AlgoTutorGen 的 token 成本、API latency 和 198/200 必须重新测量，不能直接沿用本报告数值。

## 9. 可复现命令与产物

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/analyze_total_token_cost_reliability.py
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest -q tests/regression/test_total_token_cost_reliability.py
```

分析脚本：`scripts/analyze_total_token_cost_reliability.py`。

结果目录：`output/experiments/total_token_cost_reliability_20260725/`，包含：

- `total_token_cost_reliability.json`：协议、曲线、成本、统计和输入哈希；
- `budget_curve.csv`：固定 repair-budget 曲线；
- `token_cap_curve.csv`：硬 token-cap 重放曲线；
- `per_task_ledger.csv`：617 次调用的逐任务账本；
- `total_token_cost_reliability.md`：自动生成摘要；
- `total_token_cost_reliability.png`：成本-可靠性图。

## 10. 实验一和实验三还需补充的能力

### 10.1 实验一：Same-Shell Atomic-Service Ablation

当前不能直接按论文定义完成，主要缺口是：

1. **真正的单执行 Atomic 条件**：当前 `algolab/runtime/executor.py` 先执行 `solve_code`，再独立执行 `tracker_code`；prompt 也明确说明二者分别执行。现有 `TraceSession` 只保证 trace 那次执行中的服务状态与事件一起更新，不能证明最终答案和 trace 来自同一次算法执行。
2. **受控 Decoupled 接口**：需要同一 shell 下的状态更新 API 和显式事件记录 API，让模型分别调用，同时仍禁止直接写受保护状态。目前没有可用于公平对照的 Decoupled runtime。
3. **same-execution binding**：Atomic 记录需要 runtime-issued run ID，把 answer、typed events、逐步 service snapshots 和 callsites 绑定为一个执行记录；生成后检查 `solve == trace` 不能替代这个证据。
4. **prefix replay 与 final-state validator**：要对每个事件前缀重放并与当时 canonical state 比较，而不只是检查最终 trace schema/结果。
5. **unlogged mutation validator**：必须检测所有绕过服务边界的 canonical state 变化，否则“没有事件”既可能表示没有变化，也可能表示未记录变化。
6. **实验 harness**：实现 23-family pilot、Atomic/Decoupled 交错运行、固定随机化顺序、逐题机制指标、McNemar/bootstrap/Holm 分析，然后才能投入 Full-200。该实验需要新的 LLM 调用，预计成本最高。

现有 service-only prompt ablation、DSL 调用审计和 source/trace audit 不能替代上述因果消融。

### 10.2 实验三：Wrong-but-Self-Consistent Solver Audit

论文版实验同样依赖单执行记录。仍需：

1. 建立覆盖 23 个 family 的约 30 题冻结 mutation manifest，每题尝试两个确定性源码错误，并保存不适用 mutant；
2. mutation 必须作用于使用服务的算法执行本身，使错误状态转移和 typed events 在同一次运行中保持一致，不能只在正确 trace 生成后篡改事件；
3. 用 trusted oracle 过滤：只保留能正常执行且确实改变预期输出的 applicable mutants；
4. 对每个 mutant 运行 same-execution binding、prefix/final replay、deterministic replay、oracle agreement 和最终 ReleaseGate；
5. 输出逐 mutant 账本以及内部一致性通过率、oracle mismatch 率、release rejection 率和 Wilson 95% CI；任何错误 mutant 通过 release 都应作为阻断缺陷处理。

当前可以实现一个“双执行弱化版”：同时修改 `solve` 和 `trace` 使二者给出同一错误答案，再验证 oracle gate 拒绝。但它无法证明“系统忠实记录了同一次错误执行”，因此不能作为计划中实验三的正式结果。完成单执行 runtime 和 validator 后，实验三本身不需要新的 LLM 调用。
