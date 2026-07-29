# Plan2 补充实验结果

- 实验计划：`plan/plan2.md`
- 冻结主集合：200 个任务、23 个算法族、sample index 0
- 整理日期：2026-07-23

本文只报告最终可核验结果。自动实验与人工实验分开记录；没有真实人工标签的部分统一标为 `pending_human_labels`。

## 0. 直接结果

| 实验 | 当前结果 | 结论 |
| --- | --- | --- |
| P0-1 服务组合审计 | 200 题、399 variants；187/200 题组合了至少两个服务；使用 20/21 个目录内服务；目录外调用 0 | 冻结集合中，已有服务可以被组合并跨算法族复用 |
| P0-2 提示词配对消融 | Hybrid generation 192/200、Machine OK 187/200；Service-only generation 181/200、Machine OK 181/200 | Service-only − Hybrid 的 Machine OK 为 -3.0 pp，95% CI [-7.5, +1.5] pp；未通过 -3 pp 不劣界限 |
| P0-3 PVCR ownership audit | 200/200 个 artifact 一致；12,709/12,709 个状态通过核心语义 ownership；浏览器错误 0 | Stage2 保持了验证 artifact、解法/帧导航、canonical state 和答案绑定；更强的 sanitizer/Verified fallback 目标未完全达到 |
| P0-4 Source-to-trace | 自动审计完成；自动 exact+adjacent 为 299/413（72.40%）；两位人工评审均为 0/306 | 自动结果只能作为风险诊断；强 source-aligned 主张仍被阻断 |
| P1 人工视觉校准 | 30 题 × 5 方法 = 150 个匿名页面已准备；两位评审均为 0/150 | `pending_human_labels`，不能报告人工相关性或偏好结果 |

### 统一分母

| 单位 | 数量 | 说明 |
| --- | --- | --- |
| case | 200 | Full-200 中的任务数 |
| variant | 399 | 其中 `sorting_merge_two_full_core` 只有 1 个 variant，其余题各 2 个 |
| event / frame state | 12,709 | P0-1/P0-4 按 trace event 统计；P0-3 对同一批状态逐帧做浏览器比较 |

## 1. P0-1：服务组合与复用

这里的“服务”指 tracker 通过 `TraceSession` 调用的固定语义服务，例如 `array`、`pointer`、`graph`、`table` 和 `tree`。一题使用多个服务，表示它的两个 variants 合计调用了至少两个不同服务，而不是模型新写了多个网页组件。

| 指标 | 结果 | 通俗解释 |
| --- | --- | --- |
| 覆盖范围 | 200 cases、399 variants、23 families、7 个宏观组 | 审计覆盖完整冻结集合 |
| 使用过的目录内服务 | 20/21 | 只有 `intervals` 没在该集合中出现 |
| 目录外服务调用 | 0 | 没有发现绕过服务目录的 `TraceSession` 工厂调用 |
| 多服务任务 | 187/200（93.5%） | 大多数任务通过组合多个现有服务表达过程 |
| 多服务 variant | 297/399（74.44%） | 约四分之三的单个解法也使用了至少两个服务 |
| 跨至少两个算法族复用 | 15 个服务 | 同一服务出现在多个 family 中 |
| 跨至少两个宏观组复用 | 13 个服务 | 同一服务跨越更粗粒度的算法类别 |

每题服务数分布如下：

| 每题不同服务数 | 题数 |
| --- | --- |
| 1 | 13 |
| 2 | 65 |
| 3 | 75 |
| 4 | 40 |
| 5 | 6 |
| 6 | 1 |

复用范围最大的几个服务如下：

| 服务 | 覆盖题数 | 覆盖算法族 | 覆盖宏观组 |
| --- | --- | --- | --- |
| `array` | 138 | 18 | 7 |
| `scalar` | 71 | 13 | 7 |
| `pointer` | 64 | 12 | 7 |
| `map` | 49 | 12 | 6 |
| `tree` | 49 | 14 | 6 |
| `stack` | 35 | 10 | 7 |
| `table` | 24 | 9 | 7 |

### Source-line 风险诊断

以下指标检查 trace event 的 `code_line` 是否过度集中。它们不能直接证明语义对齐正确。

| 指标 | 结果 | 含义 |
| --- | --- | --- |
| `code_line=1` | 3,552/12,709（27.95%） | 约四分之一事件被映射到第一行 |
| 单行 collapse | 55/399（13.78%） | 一个 variant 的全部事件只映射到同一行 |
| 首行 collapse | 50/399（12.53%） | 全部事件都只映射到第一行 |
| dominant line ≥80% | 147/399（36.84%） | 至少 80% 事件集中在同一源码行 |
| 越界 `code_line` | 30/12,709（0.24%） | 行号超出源码范围 |
| 严格 answer-event 命中 return 行 | 263/402（65.42%） | 这里只统计 `role=answer` 的事件，与 P0-4 的自动启发式分母不同 |

结果文件：`output/experiments/plan2_20260722/p0_1_service_audit/`。

## 2. P0-2：提示词配对消融

两个条件使用相同的 200 题、模型、温度、候选数、修复轮数、token 上限和超时设置，唯一有意改变的是提示词：

| 条件 | 方法说明 |
| --- | --- |
| Hybrid current | 当前完整提示词，保留服务 API、输出 schema、算法族模板和题目 strategy 提示 |
| Service-only | 保留服务 API、输出 schema 和中性组合说明，删除算法族模板和题目 strategy 提示 |

两侧各使用 8 并发，总 API 并发为 16。200 对题目与输入完全一致，配对 payload SHA256 为 `f324797a34c9b9c1d66dae019afb64aed869c4da34946a72705c857241ace4a0`；两侧均无 `invalid_run` 或基础设施失败。

### 生成与失败结果

| 指标 | Hybrid current | Service-only |
| --- | --- | --- |
| 首次 specification 有效 | 121/200（60.5%） | 85/200（42.5%） |
| 最终 generation pass | 192/200（96.0%） | 181/200（90.5%） |
| 最终失败 | 8/200 | 19/200 |
| 失败构成 | visual warning 8 | visual warning 13；correctness 2；execution 3；generation 1 |
| Unknown DSL call-free | 194/200（97.0%） | 171/200（85.5%） |

`首次 specification 有效` 表示模型第一次返回的结构化规格无需 JSON 级重试；`generation pass` 表示最终得到两个可发布 variant。`Unknown DSL call-free` 要求所有候选和修复尝试都没有调用目录外的 `TraceSession` 方法。

### 九项 Machine 结果

Machine OK 是后面九项行为全部通过的交集，而不是平均分。生成失败的 case 按九项全部失败计入完整 200 题分母。

| 条件 | Load | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid current | 192/200 | 192/200 | 192/200 | 187/200 | 188/200 | 192/200 | 192/200 | 192/200 | 192/200 | 187/200（93.5%） |
| Service-only | 181/200 | 181/200 | 181/200 | 181/200 | 181/200 | 181/200 | 181/200 | 181/200 | 181/200 | 181/200（90.5%） |

Hybrid 的 192 个生成成功页面中，5 个页面在正确反馈、错误反馈或两者上仍有问题，因此 Machine OK 为 187。Service-only 的 181 个生成成功页面全部通过九项检查，其 Machine OK 损失全部来自前面的 19 个生成失败 case。

### 配对统计与核心判定

差值统一按 `Service-only − Hybrid` 计算。

| 指标 | 配对差值 | 95% bootstrap CI | Holm 校正后 p | 结果 |
| --- | --- | --- | --- | --- |
| Machine OK | -3.0 pp | [-7.5, +1.5] pp | 0.595 | -3 pp 不劣界限未通过 |
| 首次 specification 有效 | -18.0 pp | [-27.0, -9.0] pp | 0.0022 | Service-only 明显更低 |
| 最终 generation pass | -5.5 pp | [-10.0, -1.0] pp | 0.346 | 校正后不显著 |
| Unknown DSL call-free | -11.5 pp | [-17.0, -6.5] pp | 0.00051 | Service-only 明显更低 |

预设核心规则要求 Machine OK 差值的 95% CI 下界不低于 -3 pp。实测下界为 -7.5 pp，因此不劣性结论为 `false`。结果支持“固定服务接口仍能覆盖多数任务”，但不支持“删除算法族模板和 strategy 提示不会降低可靠性”。

### 调用与服务组合

| 配对均值 | Hybrid current | Service-only | Service-only − Hybrid |
| --- | --- | --- | --- |
| 模型调用次数 / case | 5.375 | 6.560 | +1.185 |
| Tokens / case | 68,703.6 | 85,797.1 | +17,093.5 |
| API latency / case | 550.1 s | 712.1 s | +162.0 s |
| 端到端耗时 / case | 557.1 s | 721.1 s | +164.0 s |
| 每题服务数（共同成功的 176 题） | 2.864 | 3.278 | +0.415 |

Service-only 并没有换来更低成本：平均调用、token 和耗时都更高。两侧共同成功的 176 题中，Service-only 平均组合了更多服务，但单行 collapse-free 为 135/176，低于 Hybrid 的 147/176；因此更多服务调用不等于更稳定的 trace 表达。

结果文件：`output/experiments/plan2_20260722/p0_2_prompt_ablation/full200/`。

## 3. P0-3：PVCR ownership audit

该实验在相同 case、variant 和 frame 下比较 Verified View 与 Creative View。核心判定检查两边是否绑定同一个验证 artifact、当前解法和帧，并呈现相同的 canonical algorithm state。DOM 标签、class 和辅助文案可能因两套确定性 shell 的实现不同而变化，因此只作为界面差异诊断，不作为核心语义成败门槛。

### 覆盖与总结果

| 指标 | 结果 |
| --- | --- |
| case / variant / state | 200 / 399 / 12,709 |
| artifact 字节一致 | 200/200 |
| artifact 语义一致 | 200/200 |
| 已实际审计状态 | 12,709/12,709 |
| 浏览器错误 | 0 |
| Verified View 状态与预期不一致 | 0/12,709 |
| Creative View 状态与预期不一致 | 0/12,709 |
| 核心语义全部一致的状态 | 12,709/12,709（100.0%） |
| 核心语义全部一致的 case | 200/200（100.0%） |

### 核心语义 ownership

这里的“核心语义全部一致”要求以下四项在同一个状态上同时通过。每项分母都是完整的 12,709 个状态。

| 维度 | 一致状态 | 通俗含义 |
| --- | --- | --- |
| Artifact binding | 12,709/12,709 | 两个 View 使用同一个验证 artifact |
| Navigation binding | 12,709/12,709 | 当前 case、variant 和 frame 一致，没有切换到其他解法的轨迹 |
| Canonical state binding | 12,709/12,709 | 当前算法状态一致，而且两边都与 artifact 中的预期帧相同 |
| Answer binding | 12,709/12,709 | 当前解法绑定的验证答案一致 |

严格 DOM skeleton 与界面文字 hash 仍保留在结果文件中，供定位两套 shell 的展示差异使用。它们不等价于算法状态错误，也不进入核心 ownership 门禁。

### 故障注入

对 20 个 artifact 分别注入五类异常资产，共 100 次。最终按页面实际行为分别报告，不再统一简写成“逃逸”。

| 故障类型 | 尝试数 | 实际结果 |
| --- | --- | --- |
| 页面级 HTML | 20 | 20 次被提取为可嵌入的 stage asset；shell 均保持完整 |
| 保留 shell ID | 20 | 20 次全部被 sanitizer 拒绝 |
| 外部 URL | 20 | 20 次检测到外部请求尝试；审计浏览器拦截了请求，shell 保持完整 |
| renderer exception | 20 | 20 次全部进入通用 fallback；shell 保持完整 |
| 非法 template/script 结构 | 20 | 20 次被当前最小 sanitizer 接受；shell 均保持完整 |
| 合计 | 100 | sanitizer 拒绝 20、通用 fallback 20、外部请求尝试 20、接受为 stage asset 40、shell 破坏 0 |

所有 80 个实际打开的故障页面都保持外层 shell 完整。当前实现通过了核心语义 ownership 门禁，但没有通过更强的“所有异常资产都被拒绝或回退到完整 Verified View”目标：

- 核心语义状态一致：`true`；
- 所有 case 核心语义一致：`true`；
- 所有故障均被拒绝或回退到完整 Verified View：`false`。

因此可以声称 Stage2 在冻结集合中复用了 Stage1 的验证 artifact 与 canonical algorithm state；不能把当前 sanitizer 描述为安全沙箱，也不能声称所有外部资源或异常结构都会被预先拒绝。

结果文件：`output/experiments/plan2_20260722/p0_3_shell_ownership_variant_fix/shell_ownership_audit.json`。

## 4. P0-4：Source-to-trace 对齐审计

### 自动审计

| 指标 | 结果 |
| --- | --- |
| case / variant / event | 200 / 399 / 12,709 |
| 交互事件 | 2,919 |
| `code_line=1` | 3,552/12,709（27.95%） |
| 单行 collapse | 55/399（13.78%） |
| dominant line ≥80% | 147/399（36.84%） |
| 越界事件 | 30/12,709（0.24%） |
| 自动 answer exact | 263/413 |
| 自动 answer adjacent | 36/413 |
| 自动 exact+adjacent | 299/413（72.40%） |

这里的 299/413 使用 P0-4 的 answer 边界启发式；P0-1 的 263/402 只统计严格 `role=answer` 事件，两者不能混用。自动 exact+adjacent 只是筛查源码行风险，不是人工正确率。

### 人工包

| 项目 | 状态 |
| --- | --- |
| 抽样 | 40 cases、80 variants、306 events、覆盖 23 families |
| Reviewer A | 0/306 |
| Reviewer B | 0/306 |
| 当前状态 | `pending_human_labels` |

只有两位真实评审完成独立标注后，才能报告 exact+adjacent 的 Wilson 95% CI、critical-error rate、exact agreement 和 Cohen κ。强主张门禁为：

- exact+adjacent 的 Wilson 95% CI 下界至少 0.90；
- critical-error rate 不高于 0.05；
- 两项同时满足。

当前没有人工标签，所以较强的 “source-aligned trace” 表述仍被阻断。

结果文件：`output/experiments/plan2_20260722/p0_4_source_trace/`。

## 5. P1：五方法人工视觉校准

匿名评审包已经准备完成，但没有生成或代填任何人工分数。

| 指标 | 结果 |
| --- | --- |
| 题数 | 30 |
| 方法数 | 5 |
| 匿名页面 | 150 |
| 覆盖算法族 | 23 |
| 页面文件 | 150 HTML + 150 PNG |
| Reviewer A 完成页 | 0/150 |
| Reviewer B 完成页 | 0/150 |
| 当前状态 | `pending_human_labels` |

两位评审需要对每页的四个维度分别给 1–5 分：题面与视觉一致性、算法状态可读性、过程变化清晰度、教学视觉设计。完成后才计算 human–VLM Spearman、All≥3 一致率、PVCR 对四个基线的配对偏好，以及评审者间一致性。

公开评审包位于 `output/experiments/plan2_20260722/p1_visual_human_calibration/`；盲化映射单独保存在 `output/experiments/plan2_20260722/private_keys/p1_visual_human_calibration_blind_key.json`。

## 6. 结果与主张边界

- P0-1 支持“冻结 200 题中多个已有服务被组合并跨算法类别复用”；它不能证明所有未知任务都不需要新服务，也不能单独证明服务接口的因果贡献。
- P0-2 的 Service-only 条件仍达到 181/200 Machine OK，但未通过相对 Hybrid 的 -3 pp 不劣性门禁；算法族模板和 strategy 提示对首次规格有效性与避免未知 DSL 调用仍有明显帮助。
- P0-3 在完整分母下通过核心语义 ownership 门禁：两个 View 的验证 artifact、解法/帧导航、canonical state 和答案绑定均一致。严格 DOM/文字完全一致仅作为界面差异诊断；当前最小 sanitizer 也不能被表述为安全沙箱。
- P0-4 的自动行号指标只能用于风险定位。没有真实双人标注前，不报告人工正确率或 source-aligned 强主张。
- P1 目前只有评审材料，没有人工评价结果；VLM 评价不能替代人工校准。
- `invalid_runs/`、早期 diagnostics、retry smoke 和单题 smoke 不进入本文结果表。
