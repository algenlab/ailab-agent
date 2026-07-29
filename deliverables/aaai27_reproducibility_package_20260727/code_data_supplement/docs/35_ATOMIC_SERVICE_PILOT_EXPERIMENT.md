# 实验一：Atomic-Service Ablation

## Pilot 结果

| 指标 | Atomic | Decoupled | 差值（Atomic - Decoupled） | 95% bootstrap CI | McNemar p |
|---|---:|---:|---:|---:|---:|
| Machine OK | 22/23（95.65%） | 20/23（86.96%） | +8.70 pp | [-8.70, 26.09] pp | 0.625 |
| Generation pass | 22/23（95.65%） | 20/23（86.96%） | +8.70 pp | [-8.70, 26.09] pp | 0.625 |

Pilot 给出正向点估计，但未达到显著性标准，因此继续进行 Full-200。

## Full-200 主结果

| 指标 | Atomic | Decoupled | 差值（Atomic - Decoupled） | 95% bootstrap CI | McNemar p |
|---|---:|---:|---:|---:|---:|
| Machine OK | 183/200（91.50%） | 162/200（81.00%） | **+10.50 pp** | [3.50, 17.00] pp | **0.00460** |
| Generation pass | 187/200（93.50%） | 164/200（82.00%） | **+11.50 pp** | [5.00, 18.00] pp | **0.00109** |

Machine OK 不一致对为 Atomic-only 36 题、Decoupled-only 15 题；Generation pass 不一致对为 Atomic-only 35 题、Decoupled-only 12 题。

## 敏感性分析

排除 Pilot 的 23 个 case 后，剩余 177 对结果如下：

| 指标 | Atomic | Decoupled | 差值（Atomic - Decoupled） | 95% bootstrap CI | McNemar p |
|---|---:|---:|---:|---:|---:|
| Machine OK | 164/177（92.66%） | 142/177（80.23%） | **+12.43 pp** | [5.65, 19.77] pp | **0.00126** |
| Generation pass | 168/177（94.92%） | 144/177（81.36%） | **+13.56 pp** | [6.78, 20.34] pp | **0.000182** |

敏感性分析与 Full-200 主结果方向一致。

## 执行机制指标

Full-200 中 Atomic 有 187 题、Decoupled 有 164 题生成可审计执行记录；两侧共同可观测配对样本为 152 题。对共同可观测样本，以下指标均为 152/152，通过率差值均为 0 pp，McNemar p 均为 1.000：

- execution validation
- same-execution binding
- prefix replay
- 无漏记 mutation
- 无 state/event mismatch

未生成执行记录的题目记为未观测，不计为机制失败。

## 成本与延迟

| 指标 | Atomic | Decoupled | 差值 | 95% bootstrap CI |
|---|---:|---:|---:|---:|
| 模型调用/题 | 6.235 | 7.025 | -0.790 | [-1.540, -0.025] |
| 修复调用/题 | 1.000 | 1.880 | -0.880 | [-1.130, -0.630] |
| Tokens/题 | 85,189.8 | 94,081.2 | -8,891.3 | [-19,072.0, 1,526.9] |
| API latency/题 | 615.7 s | 698.6 s | -82.8 s | [-155.9, -8.5] s |
| 端到端耗时/题 | 619.6 s | 704.1 s | -84.5 s | [-158.0, -9.8] s |
| 总 tokens | 17,037,968 | 18,816,236 | -1,778,268 | - |

## 失败分布

- Atomic：13 题 generation failure，其中 12 题为 visual warning、1 题为 generation failure；另有 4 题在机器审计中出现页面 JavaScript 语法错误。
- Decoupled：36 题 generation failure，其中 21 题为 visual warning、9 题为 generation failure、6 题为 execution failure；另有 2 题在机器审计中出现页面 JavaScript 语法错误。
- Decoupled generation failure 中可见的手工事实提交问题包括 9 题 claim mismatch、5 题无 pending state transition、1 题 unlogged transition。

## 结论

以预先指定的 Machine OK 为主要指标，Full-200 显示 Atomic 相对 Decoupled 提高 10.50 pp，95% bootstrap CI 不跨 0，精确 McNemar 检验 p=0.00460。排除 Pilot case 后仍提高 12.43 pp，结果保持一致。该实验支持 Atomic 条件在本评估设置下具有更高的生成可靠性；同时，Atomic 使用更少模型调用、修复调用和 tokens，API latency 也更低。

## 实验产物

- Pilot 分析：`output/experiments/plan3_20260725/atomic_service_manual_claim_pilot/atomic_service_pilot_report.json`
- Full-200 原始结果：`output/experiments/plan3_20260725/atomic_service_manual_claim_full200/atomic/llm_benchmark_report.json`
- Full-200 原始结果：`output/experiments/plan3_20260725/atomic_service_manual_claim_full200/decoupled/llm_benchmark_report.json`
- Full-200 机器审计：`output/experiments/plan3_20260725/atomic_service_manual_claim_full200/machine_audits/atomic/interaction_semantic_eval_report.json`
- Full-200 机器审计：`output/experiments/plan3_20260725/atomic_service_manual_claim_full200/machine_audits/decoupled/interaction_semantic_eval_report.json`
- 配对分析及 177-pair 敏感性分析：`output/experiments/plan3_20260725/atomic_service_manual_claim_full200/atomic_service_full200_report.json`
