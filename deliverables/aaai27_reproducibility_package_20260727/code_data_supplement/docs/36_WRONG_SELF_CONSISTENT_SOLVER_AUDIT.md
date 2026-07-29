# 实验三：Wrong-but-Self-Consistent Solver Audit

## 实验概况

- 分析集：30 题，覆盖 23/23 个算法 family。
- Mutation 尝试：225 次。
- Applicable mutants：60 个，每题 2 个。
- Applicable 判定：正常执行且结果与 trusted expected 不一致。

## 实验结果

| 指标 | 结果 | 比例 | Wilson 95% CI |
|---|---:|---:|---:|
| 内部执行一致性 | 60/60 | 100.00% | [93.98%, 100.00%] |
| Oracle mismatch | 60/60 | 100.00% | [93.98%, 100.00%] |
| Pipeline oracle 检测 | 60/60 | 100.00% | [93.98%, 100.00%] |
| ReleaseGate 拒绝 | 60/60 | 100.00% | [93.98%, 100.00%] |
| 阻断缺陷 | 0/60 | 0.00% | - |

## Mutation 分布

| Mutation 类型 | 尝试 | Applicable | Not applicable |
|---|---:|---:|---:|
| 比较/边界 | 98 | 25 | 73 |
| 遗漏更新 | 92 | 0 | 92 |
| 错误返回 | 35 | 35 | 0 |
| 合计 | 225 | 60 | 165 |

## 结论

60 个错误 mutant 均产生了内部一致、可重放的执行记录，但结果全部与 trusted expected 不一致。Pipeline 检测并由 ReleaseGate 阻断了全部 60 个错误样本，未发现错误结果通过发布门。

实验结果表明：执行记录内部自洽不能单独保证算法正确，外部 oracle 或 verifier 仍然必要。

## 实验产物

- 汇总报告：`output/experiments/plan3_20260725/wrong_self_consistent_solver_audit/wrong_self_consistent_solver_audit.json`
- 全部尝试：`output/experiments/plan3_20260725/wrong_self_consistent_solver_audit/attempts.jsonl`
- Applicable 明细：`output/experiments/plan3_20260725/wrong_self_consistent_solver_audit/applicable_mutants.csv`
- Mutation 源码：`output/experiments/plan3_20260725/wrong_self_consistent_solver_audit/mutant_sources/`
