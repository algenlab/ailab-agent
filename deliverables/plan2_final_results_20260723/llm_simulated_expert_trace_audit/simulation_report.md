# LLM 模拟预评估结果

> **SYNTHETIC_LLM_PREVIEW：以下数据不是人工专家结果，只能用于流程预演。**

模拟样本包含 60 个任务、23 个算法族、120 条 traces 和 3883 个事件。

| 指标 | 模拟结果 | 区间/上界 |
| --- | --- | --- |
| Trace-perfect task | 57/60（95.0%） | Wilson 95% CI [86.3%, 98.3%] |
| Critical-error task | 1/60（1.7%） | 单侧95%上界 7.7% |
| Trace-perfect variant | 117/120（97.5%） | 描述性 |
| Source-line exact | 92.2% | 描述性 |
| Source-line exact+adjacent | 98.3% | task-macro 95% CI [98.5%, 99.1%] |
| State-transition accuracy | 99.97% | 描述性 |
| Algorithmic-operation accuracy | 99.97% | 描述性 |
| Reason-state consistency | 99.5% | 描述性 |

模拟双评审的 trace-perfect 原始一致率为 98.3%，Cohen's κ=0.791；critical-error 原始一致率为 99.2%，κ=0.663。

本次模拟故意保留 1 个关键错误任务以及少量 source-line、解释一致性问题。严格门禁结果为 **FAIL**：它展示了总体结果较好，但 60 题中出现 1 个关键错误后，关键错误率单侧95%上界无法压到5%以内，因此不能据此使用最强正确性表述。
