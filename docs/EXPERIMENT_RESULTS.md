# AlgoTutorGen 实验结果：方法、指标与证据总览

- **结果冻结窗口：** 2026-07-06 至 2026-07-14
- **统一整理日期：** 2026-07-17
- **主实验：** 200 个任务、23 个算法族，每题使用 sample index 0 形成配对观察
- **完整稳健性集合：** 同一 200 个任务的 646 个具体样例
- **机器可读证据：** `output/experiments/`、`output/external_baselines/`

## 0. 如何阅读这份结果

这份文档先回答两个最直接的问题：比较了哪些方法，以及它们在相同浏览器行为指标上分别通过了多少题。成本、泛化、消融、理论定向审计、教学质量和视觉质量放在后续独立章节，不再与主方法表混在一起。

主方法表统一使用 200 个任务的 sample index 0。所有数值都写成 `通过数/200（通过率）`。主表比较的是冻结产物在统一黑盒浏览器协议下的行为，不表示所有方法使用了相同模型调用预算；各方法的预算和生成条件在方法说明及成本章节中单独列出。

`Machine OK` 是以下九项检查的合取，而不是平均分：

1. `Load`：页面成功加载且没有阻断行为的错误；
2. `Answer`：页面可见最终答案与 expected 一致；
3. `Interaction`：学习者交互控件可达；
4. `Correct FB`：正确回答得到方向正确的反馈；
5. `Wrong FB`：错误回答得到方向正确的反馈；
6. `Hint`：提示按钮真实工作；
7. `Show`：显示答案按钮真实工作；
8. `Log`：提交行为进入学习日志；
9. `Mutation-free`：教学操作不改变最终答案或算法事实。

任何一项失败，该页面的 `Machine OK` 就是失败。这个指标衡量浏览器行为完整性，不衡量视觉偏好，也不证明学生真的学得更好。

## 1. 比较了哪些方法

| 方法 | 输入与起点 | 生成或修复方式 | 最终 Runtime | 主表采用的冻结条件 |
|---|---|---|---|---|
| **AlgoTutorGen（本文方法）** | 题目、输入、expected、可选策略 | LLM 生成可执行 spec；沙箱物化 SemanticTrace；经过结果、trace、过程连续性和 scene 门禁；再生成受限 teaching overlay | 确定性 SceneGraph compiler + 固定 Web Runtime | DeepSeek-V4-Pro selected-final；primary 为 195/200，5 个失败任务使用记录在案的 targeted retry |
| **Direct HTML** | 与本文方法相同的题目、输入和 expected | 一次自由生成完整 HTML/CSS/JavaScript；主条件没有浏览器反馈修复 | 模型自由生成 | 冻结 full-200 Direct baseline |
| **WebGen-Agent** | 题目与页面要求 | 外部网页生成 agent 路径，多步生成网页 | agent 生成 | full-200 外部 baseline；统一离线浏览器审计 |
| **Direct + HTMLCure** | Direct HTML 候选页 | HTMLCure 对页面进行修复并决定是否接受改写 | 修复后的自由 HTML | strict self-contained 条件；引入外部资源的页面按失败处理 |
| **Direct-BrowserRepair pipeline** | Direct HTML 候选页 | 后续调用可读取通用浏览器反馈并整页重写 | 修复后的自由 HTML | 固定预算 1-call first-call control，因为它是该预算曲线的最佳结果；真正反馈重写从 call 2 开始 |

Direct-to-SceneGraph、VerifiedTrace-to-LLM-HTML、no-repair、no-interaction 等是消融条件，不是完整方法，因此不放进这一方法表。

## 2. Full-200 主结果

### 2.1 基础可靠性

| 方法 | Load | Answer | Interaction | Machine OK |
|---|---:|---:|---:|---:|
| **AlgoTutorGen** | **200/200（100.0%）** | **200/200（100.0%）** | **200/200（100.0%）** | **198/200（99.0%）** |
| Direct HTML | 188/200（94.0%） | **200/200（100.0%）** | 149/200（74.5%） | 98/200（49.0%） |
| WebGen-Agent | 194/200（97.0%） | 169/200（84.5%） | 154/200（77.0%） | 45/200（22.5%） |
| Direct + HTMLCure（strict） | 75/200（37.5%） | 75/200（37.5%） | 62/200（31.0%） | 40/200（20.0%） |
| Direct-BrowserRepair（1-call first-call control） | 186/200（93.0%） | **200/200（100.0%）** | 155/200（77.5%） | 106/200（53.0%） |

### 2.2 教学交互行为

| 方法 | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free |
|---|---:|---:|---:|---:|---:|---:|
| **AlgoTutorGen** | **199/200（99.5%）** | **198/200（99.0%）** | **200/200（100.0%）** | **200/200（100.0%）** | **200/200（100.0%）** | **200/200（100.0%）** |
| Direct HTML | 120/200（60.0%） | 125/200（62.5%） | 132/200（66.0%） | 133/200（66.5%） | 135/200（67.5%） | 149/200（74.5%） |
| WebGen-Agent | 74/200（37.0%） | 89/200（44.5%） | 136/200（68.0%） | 148/200（74.0%） | 109/200（54.5%） | 154/200（77.0%） |
| Direct + HTMLCure（strict） | 52/200（26.0%） | 51/200（25.5%） | 53/200（26.5%） | 53/200（26.5%） | 59/200（29.5%） | 62/200（31.0%） |
| Direct-BrowserRepair（1-call first-call control） | 128/200（64.0%） | 133/200（66.5%） | 137/200（68.5%） | 138/200（69.0%） | 143/200（71.5%） | 155/200（77.5%） |

### 2.3 各方法主要损失在哪里

- **AlgoTutorGen：** 200 个页面全部加载、显示正确答案并提供交互；最终 2 个失败都发生在反馈合同，完整通过为 198/200。优势不是“更会显示答案”，而是把答案、过程、界面和教学行为维持在同一条可验证链上。
- **Direct HTML：** 200/200 都显示了正确答案，但 Load 降到 188、Interaction 降到 149，最终只有 98/200 同时满足九项合同。主要问题发生在浏览器程序和教学反馈的组合边界。
- **WebGen-Agent：** Load 和 Interaction 分别为 194 与 154，但 Answer 只剩 169，Correct/Wrong Feedback 进一步降到 74/89，最终 Machine OK 为 45/200。多步 agent 生成没有自动消除答案、DOM 和反馈之间的耦合。
- **HTMLCure：** strict 条件只有 40/200。126 个被接受的改写中有 125 个引入 Google Fonts，首先破坏了 self-contained 合同；即使阻断外部请求做敏感性分析，Machine OK 也只有 91/200。
- **BrowserRepair pipeline：** 最佳固定预算是 1-call first-call control，Machine OK 为 106/200。它回溯到每题的初始生成页，而主 Direct 行使用主实验冻结页，两行不是逐页同一版本，因此不能把 106 对 98 解释成 repair gain。真正加入整页反馈重写后，2/3/5-call 分别降到 10、15、6；更多重写预算没有带来单调收益。

AlgoTutorGen 相对 Direct HTML 的 Machine OK 高 50.0 个百分点，95% paired-bootstrap CI 为 `[43.0, 57.0]`。200 个配对任务中，101 个只有 AlgoTutorGen 通过，1 个只有 Direct 通过，exact McNemar `p=4.06e-29`。外部方法行用于补充方法背景；由于生成预算不同，不能把这张表解释为通用网页 agent 排名。

## 3. 修复策略与成本

### 3.1 AlgoTutorGen 用更多模型调用换取完整行为可靠性

| 条件 | 模型调用 | 总 tokens | 平均 calls/task | 平均 tokens/task |
|---|---:|---:|---:|---:|
| AlgoTutorGen selected-final | 1,066 | 15,369,433 | 5.33 | 76.8k |
| AlgoTutorGen 全部尝试与 retry | 1,151 | 16,870,557 | 5.76 | 84.4k |
| Direct HTML | 222 | 4,385,641 | 1.11 | 21.9k |

这些数字说明 AlgoTutorGen 用更高的生成、执行和验证成本换取更高的完整行为可靠性。实验没有冻结模型价格，因此不报告货币成本，也不能声称本文方法更便宜。

### 3.2 Direct-BrowserRepair 固定预算曲线

| 固定调用上限 | Load | Answer | Interaction | Machine OK | 平均 tokens | 平均生成时间 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 186/200 | 200/200 | 155/200 | **106/200** | 19.7k | 207.2 s |
| 2 | 179/200 | 179/200 | 20/200 | 10/200 | 36.8k | 347.2 s |
| 3 | 185/200 | 184/200 | 41/200 | 15/200 | 53.7k | 477.6 s |
| 5 | 188/200 | 191/200 | 30/200 | 6/200 | 87.2k | 733.9 s |

四行是独立 fixed-budget 条件，不是同一批页面的累计存活曲线。1-call 只使用冻结的初始生成页；2-call 才包含一次浏览器反馈重写。更多整页重写可能修复一个问题，同时破坏已经成立的答案、交互或反馈合同。

### 3.3 HTMLCure 的 strict 与 blocked-external 口径

HTMLCure full-200 共生成 269 个候选，接受 126 个改写。strict 条件要求文件本身不依赖外部资源，Machine OK 为 40/200。将外部请求在浏览器中阻断后，行为敏感性结果为 91/200，McNemar `p=0.118`，仍未超过 Direct 的 98/200。blocked 条件不会让文件本身变成 self-contained，因此只作为敏感性分析。

| Blocked-external 指标 | Direct HTML | HTMLCure |
|---|---:|---:|
| Load | 188/200 | 200/200 |
| Answer | 200/200 | 200/200 |
| Interaction | 149/200 | 148/200 |
| Correct feedback | 120/200 | 112/200 |
| Wrong feedback | 125/200 | 120/200 |
| Hint | 132/200 | 129/200 |
| Show answer | 133/200 | 130/200 |
| Learning log | 135/200 | 136/200 |
| Machine OK | 98/200 | 91/200 |

### 3.4 Local Resume 没有显著优于 Global Restart

当前 Local Resume 只保留 solution spec；repair 后仍重新执行 materialization，并重新生成 teaching，因此还不是完整 checkpoint recovery。

| 模型 | 策略 | Success | Tokens/success | Calls/success | Mean time to valid | McNemar p |
|---|---|---:|---:|---:|---:|---:|
| Flash | Local Resume | 38/50 | 71,369 | 6.63 | 172.9 s | 0.4545 |
| Flash | Global Restart | 42/50 | 62,256 | 5.50 | 194.2 s | 0.4545 |
| GLM | Local Resume | 42/50 | 92,385 | 6.69 | 533.8 s | 1.0000 |
| GLM | Global Restart | 43/50 | 96,186 | 6.65 | 558.2 s | 1.0000 |

Flash 上 Global 的成功数和 token/success 数值更好；GLM 上 Local 稍省 token 和时间，但少成功一题。两组成功率差异都不显著。系统已经实现语义解耦和验证解耦，但还没有实现完整的计算恢复解耦。

## 4. 稳健性、泛化与规模边界

### 4.1 同一任务换输入：626/646

冻结主实验的 solver/tracker 后，在全部 646 个样例上重放，626/646 通过（96.90%）。sample 0 为 200/200，额外输入为 426/446。20 个失败来自 solve/trace 边界、expected 归一化、target 引用以及空或断连输入。

646 行具有 case 内相关性，不能当成 646 个独立平衡任务与主表合并。这一结果说明结构化系统可以暴露额外输入上的错误，但没有消除生成代码的输入泛化问题。

### 4.2 更换生成模型：架构差距仍为正

下表统一使用 2 candidates × 2 repairs 的 fixed budget。

| 模型 | AlgoTutorGen Machine OK | Direct Machine OK | 差值 | 95% CI | McNemar p |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash | 196/200（98.0%） | 118/200（59.0%） | +39.0 pp | [32.0,46.0] | `1.02e-20` |
| GLM-5.2 | 170/200（85.0%） | 35/200（17.5%） | +67.5 pp | [60.0,74.5] | `1.48e-34` |
| Kimi-K2.5 | 160/200（80.0%） | 87/200（43.5%） | +36.5 pp | [27.5,45.0] | `1.87e-13` |

三种模型的差值都为正且配对显著，但 AlgoTutorGen 的绝对成功率从 98% 降到 80%。固定 Runtime 没有让上游模型能力变得无关。Failure-only 3×3 retry 后，Flash、GLM、Kimi 的 final-quality Machine OK 分别为 200/200、196/200、194/200；这些数字不能替代统一预算主表。

### 4.3 Held-out 新任务：39/40 对 18/40

Held-out v1 冻结 40 个新任务、15 个算法族。AlgoTutorGen generation 和 Machine OK 均为 39/40；Direct generation 为 40/40，Machine OK 为 18/40。差值为 +52.5 pp，95% CI `[37.5,67.5]`，McNemar `p=9.54e-7`。

唯一 Stage1 失败 `heldout_bipartite_matching_size` 被严格 teaching-feedback warning 拒绝。后续 targeted retry 补齐的第 40 个 artifact 只用于表示保持和非干扰审计；原始 held-out 生成结果仍然是 39/40。这支持有限冻结集合上的泛化，不支持开放域算法的普遍成功率主张。

### 4.4 长轨迹：逐帧完整状态复制不能无界扩展

| Scale | 平均 frames | 平均 HTML | Load | Step latency | JS heap |
|---|---:|---:|---:|---:|---:|
| Small | 104.4 | 1.40 MB | 120 ms | 14.7 ms | 6.3 MB |
| Medium | 543.3 | 23.25 MB | 1,933 ms | 45.4 ms | 59.1 MB |
| Large | 1,636.7 | 160.42 MB | 8,354 ms | 101.3 ms | 185.6 MB |

54/54 个样本完成 materialization，52/54 完成浏览器测量。KMP large 为 3,063 frames、581 MB；sliding-window unique large 为 5,533 frames、1.08 GB，两者都超过 60 秒加载预算。后续需要 frame virtualization、增量状态或压缩表示。

## 5. 为什么完整分解链有效

### 5.1 约束是逐层存活的

依次要求 C1 答案、C2 加载、C3 交互、C4 双向反馈、C5 hint/show/log、C6 mutation-free 后，累计存活率如下：

| 方法 | C1 Answer | C2 Load | C3 Interaction | C4 Feedback | C5 Teaching support | C6 Noninterference |
|---|---:|---:|---:|---:|---:|---:|
| AlgoTutorGen | 100.0% | 100.0% | 100.0% | 99.0% | 99.0% | 99.0% |
| Direct HTML | 100.0% | 94.0% | 74.5% | 54.0% | 49.0% | 49.0% |

Direct 的损失不是一次发生，而是在 Load、Interaction 和 Feedback 等组合边界逐层累积。AlgoTutorGen 在交互之前保持 100%，只在反馈处损失两个页面，之后不再继续坍塌。这是 constraint entanglement 的直接行为证据。

### 5.2 两个非退化消融排除简单解释

| 50 题条件 | Full | Ablation | 说明 |
|---|---:|---:|---|
| Direct-to-SceneGraph | 49/50 | 1/50 | 固定 Runtime 没有可执行 trace 与验证仍然不够 |
| VerifiedTrace-to-LLM-HTML | 49/50 | 0/50 | 正确 trace 接自由 HTML 仍然无法维持完整教学行为 |

Direct-to-SceneGraph 保留固定 Runtime，但让 LLM 跳过可执行语义轨迹直接写 SceneGraph。VerifiedTrace-to-LLM-HTML 提供正确 SemanticTrace，却让 LLM 自由生成最终 HTML，虽然 50/50 都显示答案，Machine OK 仍为 0/50。可靠性来自完整 refinement chain，而不是某一个单独模块。

### 5.3 分解后的边界经过独立审计

| 被检查的性质 | 观察结果 | 最强可支持解释 |
|---|---:|---|
| Trace→Scene→Runtime 投影 | 294/294 artifacts，55,108/55,108 帧一致 | 已评估表示之间保持 canonical algorithm state |
| 确定性重编译/重渲染 | 20 artifacts × 10 次，每个只有一个 projection/render hash | 测试环境中结果稳定 |
| 定义的语义违规 | 2,198/2,198 被拒绝 | gate 识别 mutation suite 中定义的错误 |
| 定义的语义保持变换 | 392/392 被接受 | 教学文字、视觉 metadata 和等价重排没有被误拒绝 |
| 教学非干扰压力测试 | 240/240 页面，1,561,298 次动作，0 个观察到的违规 | 有限随机序列中未找到教学污染算法状态的反例 |

55,108 帧由主集合 9,421 帧、补齐审计用 held-out 集合 4,568 帧和 long-trace 集合 41,119 帧组成。这个结果支持 representation-level preservation，不证明源 trace 的每一步都符合独立算法语义，也不是像素级形式验证。392 个被接受的保持变换包括 195 个教学文字重写、195 个 visual metadata 修改和 2 个无序结果等价重排。mutation 结果只说明定义的 mutation suite 被完整区分，不是 universal validator soundness/completeness。

教学隔离实验还对 Flash 主集合的 372 个 SceneGraph variants 应用了原始、简洁、详细和随机合法 overlay，state hash 全部保持。非法 `final_answer`/`state` 写入被清洗；negative step 被 schema 拒绝；跨模型 GLM overlay 映射到 369 个场景后也全部保持 state hash。

浏览器随后在 main 200 与 held-out 40 共 240 个页面上运行 24,000 个随机动作序列，包括 435,859 个纯教学动作和 1,125,439 个导航/variant 动作。正确表述是“没有在有限 property-based 压力测试中找到反例”，不是“形式化证明永远 noninterfering”。

### 5.4 Full-200 功能消融与 fault injection

| 条件 | Machine OK | 解释 |
|---|---:|---|
| Full | 198/200 | 完整系统 |
| No repair | 193/200 | 5 个 primary 失败没有被救回 |
| No teaching | 198/200 | Machine OK 不评价讲解文字质量 |
| No interaction | 0/200 | 学习交互合同消失 |
| No teaching + interaction | 0/200 | 同样发生功能坍塌 |
| No SceneGraph compiler | 0/200 | trace-only fallback 无完整编译行为 |

fault injection 修复前接受 200/200 clean controls、拒绝 1,843/2,400 故障；补充顺序和引用完整性检查后仍接受 200/200 clean controls，并拒绝 2,246/2,400（93.58%）。单事件删除仍有 152/200 被接受，因为部分事件在当前合同下可以冗余。

## 6. 教学与视觉指标是辅助证据

功能可靠不自动意味着讲解质量更高。以下指标用于补充教学和展示质量，不属于 Machine OK，也不构成真人学习效果证据。

### 6.1 教学代理指标

| 指标 | AlgoTutorGen | Direct HTML | 含义边界 |
|---|---:|---:|---|
| Naps engagement（0–5） | 1.990 | 1.480 | 可观察参与层级，不是学习增益 |
| TRAKLA2-style core pass | 0.990 | 0.495 | 七项自动练习行为的合取，不是官方认证 |
| LORI/MERLOT-informed overall（1–5） | 4.886 | 3.403 | 匿名 LLM judge 的学习资源代理评分 |
| 匿名配对 winner | 193 | 6 | 另有 1 个 tie |

Judge 稳健性矩阵中，DeepSeek 顺序交换 winner agreement 为 95.5%，Gemini 为 97.5%，两个模型 frozen-order agreement 为 93.0%。winner 高度集中时 kappa 会受 prevalence effect 影响，因此 raw agreement 与 kappa 必须同时报告。

### 6.2 Stage2 Creative Visual

Stage2 只增强展示层，算法 correctness 仍由 Stage1 负责。`creative-ok` 表示页面通过浏览器 smoke 和严格布局审计，不表示算法答案正确或视觉上一定更受偏好。repair 后 200/200 页面 creative-ok，1,494 个审计帧最终 overlap、clipped 和 text occlusion 均为 0。

| 视觉维度 | Stage2 | Direct | Holm p | Rank-biserial |
|---|---:|---:|---:|---:|
| 题面—视觉贴合 | 4.835 | 4.825 | 0.856 | -0.032 |
| 算法状态可读性 | 4.385 | 4.505 | 0.059 | -0.236 |
| 过程变化清晰度 | 4.320 | 4.400 | 0.326 | -0.146 |
| 教学视觉设计 | 4.905 | 4.655 | `1.56e-5` | 0.624 |

Holm 校正后只有“教学视觉设计”显著。Direct 在单截图的算法状态可读性和过程变化清晰度上数值略高，因此不能声称 Stage2 在所有视觉维度全面优于 Direct。

## 7. 结论与主张边界

整组实验支持以下结论：

1. **正确答案是弱指标。** AlgoTutorGen、Direct 和 BrowserRepair 1-call first-call control 都能在 200/200 页面显示 expected，但 Machine OK 分别为 198、98 和 106。
2. **自由 HTML 的主要损失发生在组合行为。** Direct、WebGen-Agent、HTMLCure 和 BrowserRepair 都在加载、交互或双向反馈处继续丢失。
3. **完整 refinement chain 才是关键。** 正确 trace、固定 Runtime 或更多整页重写预算中的任一单项都不足。
4. **分解边界可以被执行审计。** 已评估帧保持状态投影，定义的 mutation suite 能区分错误与无害变化，教学压力测试没有找到污染反例。
5. **可靠性差距具有有限稳健性。** 跨模型和 held-out 结果保持正差，但绝对成功率仍受模型、输入和预算影响。
6. **可靠性不是免费的。** AlgoTutorGen 使用更多模型调用和 tokens；长轨迹会造成 HTML 与内存膨胀；Local Resume 尚未实现理想 checkpoint recovery。

当前证据不支持以下表述：提高学生成绩、保持率或迁移能力；对任意算法全过程的形式化正确性证明；validator 对全部错误 universal soundness/completeness；Stage2 在全部视觉维度显著优于 Direct；100% first-try success；把 646 个样例视为独立平衡任务；把 40 个 held-out case 外推到开放域；或者声称 AlgoTutorGen 比 Direct 更便宜。

## 8. 详细查阅表

### 8.1 指标与统计术语

| 术语 | 含义 | 读法 |
|---|---|---|
| Generation pass | 生成/materialization 阶段产生有效 artifact | 不等于最终浏览器 Machine OK |
| Machine OK | 九项浏览器检查全部通过 | 是合取，不是平均分 |
| Self-contained | HTML 不依赖外部网络资源 | 不代表答案或交互正确 |
| Primary | 所有方法共享的固定预算条件 | 用于公平主比较 |
| Selected-final / final-quality | 允许候选和 retry 后最终采用的 artifact | 不能冒充 first-try 结果 |
| pp | 百分点 | 99% 与 49% 相差 50 pp |
| 95% CI | 差异的区间估计 | 差值 CI 不跨 0 表示方向较稳定 |
| McNemar p | 同一任务上两个方法通过/失败的配对检验 | p 小表示不一致对明显偏向一方，不代表效应大小 |
| Holm p | 多重比较校正后的 p 值 | 降低多次检验带来的偶然显著 |
| Rank-biserial | 配对等级效应量，约 -1 到 1 | 正值偏向表中第一个方法，绝对值越大差异越强 |
| Raw agreement / flip | 两次 judge 的 winner 一致率/改变率 | agreement 高且 flip 低表示排序较稳 |
| Cohen's kappa | 扣除随机一致后的评价者一致性 | 类别不平衡时可能与 raw agreement 看起来矛盾 |
| Creative OK | 浏览器可运行且严格布局审计通过 | 不检查算法答案，也不等于主观视觉偏好 |
| N/A | 指标对该系统不适用 | 不能当作失败或 0 分 |

### 8.2 外部方法补充说明

- **WebGen-Agent：** 200/200 generation，Machine OK 45/200；family core 为 11/62，expansion 为 34/138。`tarjan_scc` 两次审计超时，保守计为失败。
- **HTMLCure：** strict 结果见主表；blocked-external 结果只用于敏感性分析。
- **EduVisAgent：** 冻结公开实现输出教学计划和逐 section UI-plan 文本，不输出可审计网页。按六个教学部分估算，200 题约需 7,600 次模型调用，但九项浏览器指标未定义，因此只作为相关工作，不进入数值主表。
- **传统系统 exact-overlap：** Algorithm Visualizer N=3、Python Tutor N=2、LeetCode Solution Visualizer N=2 在各自支持范围内通过步骤导航、状态和终态检查，但依赖人工模板、在线服务或 adapter。unsupported case 与 tutoring-specific 指标为 N/A，不能记为失败。

### 8.3 跨模型 final-quality 与候选预算

| 模型 | Primary generation | Primary Machine OK | Final generation | Final Machine OK | Direct Machine OK |
|---|---:|---:|---:|---:|---:|
| Flash | 196/200 | 196/200 | 200/200 | 200/200 | 118/200 |
| GLM | 172/200 | 170/200 | 198/200 | 196/200 | 35/200 |
| Kimi | 160/200 | 160/200 | 195/200 | 194/200 | 87/200 |

Primary 第一候选通过 451/600，第二候选额外救回 77 个，最终 generation 为 528/600。按 selected round 的观测下界，无修复为 315/600，至多一次修复为 447/600，至多两次修复为 528/600。推荐保留 2×2 作为公平主预算，3×3 只用于 failure-only final-quality。

### 8.4 Judge 稳健性

| Judge / order | AlgoTutorGen wins | Direct wins | Ties |
|---|---:|---:|---:|
| DeepSeek frozen | 193 | 6 | 1 |
| DeepSeek swapped | 194 | 4 | 2 |
| Gemini frozen | 191 | 9 | 0 |
| Gemini swapped | 190 | 10 | 0 |

DeepSeek 顺序交换 agreement 95.5%、flip 4.5%、kappa 0.289；Gemini 为 97.5%、2.5%、0.724；两个模型 frozen-order winner agreement 为 93.0%、kappa 0.092。

### 8.5 人工数据状态

| 项目 | 规模 | 状态 |
|---|---:|---|
| Machine evaluator calibration | 30 tasks × 4 methods = 120 blind pages | `pending_human_labels` |
| Independent trace audit | 40 tasks、23 families、双人审核 | `pending_human_labels` |
| Expert study | 3 experts × 30 blind pairs | `pending_human_data` |
| Student study | 24 students × 12 trials | `pending_human_data` |

`pending_human_labels` 表示材料和分析脚本已准备，但没有真实标注；`pending_human_data` 表示协议已准备，但没有真实参与者。现阶段不能报告 evaluator precision/recall、trace critical-error rate、专家偏好、SUS 或学习结果。

协议见 `docs/31_HUMAN_EXPERT_REVIEW_PROTOCOL.md` 和 `docs/32_STUDENT_USER_STUDY_PROTOCOL.md`。

## 9. 原始证据与复现索引

### 9.1 数据与统一审计

- Benchmark：`benchmark/README.md`
- Main benchmark artifact：`output/experiments/algotutorgen_full_200_20260706/`
- Final completion audit：`output/experiments/algotutorgen_plan_completion_20260713/final_completion_audit.json`
- 论文数字账本：`latex/evidence-ledger.md`

### 9.2 主方法行为结果

- AlgoTutorGen / Direct HTML：`output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine/interaction_semantic_eval_report.json`
- WebGen-Agent：`output/external_baselines/webgen/audit_all200_sample0/report.json`
- HTMLCure strict：`output/external_baselines/htmlcure_all200_sample0/behavior_audit/interaction_semantic_eval_report.json`
- HTMLCure blocked：`output/external_baselines/htmlcure_all200_sample0/behavior_audit_external_blocked/interaction_semantic_eval_report.json`
- HTMLCure paired analysis：`output/external_baselines/htmlcure_all200_sample0/htmlcure_full200_analysis.json`
- Direct-BrowserRepair：`output/experiments/algotutorgen_plan_completion_20260713/direct_browser_repair_5/`

### 9.3 教学、视觉和统计

- 外部评价方法：`output/experiments/algotutorgen_full_200_20260706/external_eval_methods/external_eval_methods_report.json`
- Stage2：`output/experiments/algotutorgen_full_200_20260706/stage2_eval/stage2_visual_eval_report.json`
- 配对统计：`output/experiments/algotutorgen_completion_20260713/statistics/`
- Judge robustness：`output/experiments/algotutorgen_completion_20260713/judge_robustness/judge_robustness_report.json`

### 9.4 消融、稳健性和 fault injection

- Completion summary：`output/experiments/algotutorgen_completion_20260713/completion_summary.json`
- Browser ablations：`output/experiments/algotutorgen_completion_20260713/ablation_audits/`
- Teaching pair reviews：`output/experiments/algotutorgen_completion_20260713/ablation_pair_reviews/`
- Cross-input replay：`output/experiments/algotutorgen_completion_20260713/cross_input_replay/cross_input_replay_report.json`
- Post-fix fault rerun：`output/experiments/algotutorgen_plan_completion_20260713/validator_fault_rerun/`
- 非退化消融：`output/experiments/algotutorgen_plan_completion_20260713/nondegenerate_ablations/`
- Multi-model summary：`output/experiments/algotutorgen_multimodel_full200_20260713/multimodel_summary.json`
- Held-out：`output/experiments/algotutorgen_plan_completion_20260713/heldout_40/`
- Long-trace：`output/experiments/algotutorgen_plan_completion_20260713/long_trace_scalability/long_trace_scalability_report.json`

### 9.5 理论定向实验

- 汇总目录：`output/experiments/theory_aligned_20260714/`
- Semantic preservation：`output/experiments/theory_aligned_20260714/semantic_preservation_report.json`
- Semantic mutation：`output/experiments/theory_aligned_20260714/semantic_mutation_report.json`
- Nested contract：`output/experiments/theory_aligned_20260714/nested_contract_survival_report.json`
- Overlay：`output/experiments/theory_aligned_20260714/cross_model_overlay_report.json`
- Noninterference：`output/experiments/theory_aligned_20260714/noninterference_stress_report.json`
- Retry Flash：`output/experiments/theory_aligned_20260714/retry_flash/local_vs_global_retry_report.json`
- Retry GLM：`output/experiments/theory_aligned_20260714/retry_glm/local_vs_global_retry_report.json`

### 9.6 Prompt、协议与论文

- 完整 Prompt：`docs/20_ALGOTUTORGEN_PROMPT_APPENDIX.md`
- 实验设计：`docs/16_ALGOTUTORGEN_EXPERIMENT_DESIGN.md`
- 指标协议：`docs/14_AAAI_EXPERIMENT_METRICS_AND_PROTOCOL.md`
- 人工协议：`docs/31_HUMAN_EXPERT_REVIEW_PROTOCOL.md`、`docs/32_STUDENT_USER_STUDY_PROTOCOL.md`
- 论文主文：`latex/main.tex`
- 补充材料：`latex/supplement.tex`

本文档是 `docs/` 中唯一人工维护的实验结果总览。数字冲突时，优先使用 `output/` 的冻结机器结果，其次使用 `latex/evidence-ledger.md`；历史计划和设计稿只用于追溯。
