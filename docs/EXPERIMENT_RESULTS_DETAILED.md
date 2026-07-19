# AlgoTutorGen 实验结果详细记录

- **主实验：** 200 个任务、23 个算法族，每题使用 sample index 0 形成配对观察
- **完整稳健性集合：** 同一 200 个任务的 646 个具体样例
- **整理日期：** 2026-07-19

> 本文是 [EXPERIMENT_RESULTS.md](./EXPERIMENT_RESULTS.md) 的详细版。第 0—9 节完整保留最终冻结结果，第 10 节以后补充实验协议、数据分布、完整统计、失败明细、成本和证据索引。本文仍不把被补跑替代的旧数字、debug probe 或历史演变过程当作论文结果。

| 想查什么 | 对应章节 |
| --- | --- |
| 最重要的 Full-200、跨模型和 held-out 结果 | 第 0 节 |
| 指标、预算和统计术语 | 第 1 节 |
| 最终数据集与比较方法 | 第 2 节 |
| 系统成本、BrowserRepair 和 HTMLCure | 第 3 节 |
| 跨输入与长轨迹 | 第 4 节 |
| 功能/教学/表示消融与 fault injection | 第 5 节 |
| 理论定向实验 | 第 6 节 |
| 教学和视觉代理评价 | 第 7 节 |
| 外部方法、跨模型明细和 Judge 稳健性 | 第 8 节 |
| 结果与主张边界 | 第 9 节 |
| 最终数据来源、Benchmark 分布和详细协议 | 第 10—11 节 |
| 完整配对统计、逐族结果、失败明细和成本 | 第 12 节 |
| 理论与实验的逐项对应 | 第 13 节 |
| 原始报告、脚本和复现入口 | 第 14 节 |
| 自动实验与待人工项目的最终状态 | 第 15 节 |

## 0. 核心结果表（先看这里）

先认识后续表格中的五种方法。它们面对相同的算法任务，但生成流程和模型调用预算并不完全相同。

| 方法 | 通俗介绍 | 与其他方法的主要区别 |
| --- | --- | --- |
| **AlgoTutorGen（本文方法）** | 模型先生成可执行的算法方案，再实际运行得到逐步轨迹；轨迹通过检查后，由固定编译器和固定网页 Runtime 生成教学页面 | 算法状态、页面场景和教学交互分层生成，并在多个阶段执行机器检查 |
| **Direct HTML** | 模型根据题目直接一次性编写完整 HTML、CSS 和 JavaScript 页面 | 没有独立的可执行轨迹、SceneGraph 编译和固定 Runtime，页面逻辑主要由模型自由生成 |
| **WebGen-Agent** | 使用外部多步骤网页生成 agent 完成页面，再用本文相同的浏览器指标进行审计 | 比 Direct HTML 多了 agent 工作流，但最终仍是自由生成的网页代码 |
| **Direct + HTMLCure** | 先取得 Direct HTML 页面，再交给 HTMLCure 判断并修复网页 | 属于生成后修复；正式结果使用 strict 口径，页面依赖外部资源也会判为失败 |
| **Direct-BrowserRepair** | 根据浏览器检查结果反复重写整份自由 HTML | 1-call 条件尚未读取浏览器反馈；从第 2 次调用开始才进行反馈修复 |

### 0.1 Full-200 基础可靠性

本节使用同一组 200 个任务的 sample index 0。`通过数/200（通过率）` 表示在 200 个页面中，有多少页面通过对应检查。

**Machine OK 首次定义：** 同一个页面必须同时通过九项浏览器行为检查：页面加载、答案正确、交互可达、正确反馈、错误反馈、提示、显示答案、学习日志和教学操作不改算法状态。它是九项的合取，不是平均分。`strict` 表示 HTML 文件本身必须不依赖外部资源；BrowserRepair `1-call` 只包含一次页面生成，尚未读取浏览器反馈。

九项检查的具体判定规则如下。这里的“通过”均指浏览器自动审计通过，不是 LLM/VLM 主观评分。

| 检查项 | 自动审计如何判定通过 | 不能直接推出什么 |
| --- | --- | --- |
| 页面加载（Load） | 页面主体非空，且没有阻断审计的脚本或页面错误 | 不代表答案或交互正确 |
| 答案正确（Answer） | HTML 或浏览器页面中能找到与标准答案 `expected` 一致的最终答案 | 不代表算法轨迹和讲解全部正确 |
| 交互可用（Interaction） | 能找到可见、可操作的学习者作答检查点 | 不代表反馈、提示和日志可用 |
| 正确反馈（Correct FB） | 提交已知正确答案后出现可识别反馈 | 不评价反馈文字的教学质量 |
| 错误反馈（Wrong FB） | 提交刻意构造的错误答案后出现可识别反馈 | 不代表提示或显示答案可用 |
| 提示（Hint） | 点击提示后出现反馈内容或预期页面变化 | 不代表提示一定能提升学习效果 |
| 显示答案（Show） | 点击显示答案后出现答案或反馈内容 | 不评价显示答案的教学时机 |
| 学习日志（Log） | 操作后可见日志非空，且相较操作前发生变化 | 不代表日志适合长期学习分析 |
| 教学操作不改答案（Mutation-free） | 提交、提示、显示答案等教学操作前后的受保护答案摘要保持不变 | 不等于对全部内部算法状态的形式化证明 |
| 九项全部通过（Machine OK） | 同一页面上述九项全部为通过 | 不是九项通过率的平均值，也不是最低单项通过数 |

五种方法的九项完整结果如下：

| 方法 | Load | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **AlgoTutorGen（最终结果）** | **200/200（100.0%）** | **200/200（100.0%）** | **200/200（100.0%）** | **199/200（99.5%）** | **198/200（99.0%）** | **200/200（100.0%）** | **200/200（100.0%）** | **200/200（100.0%）** | **200/200（100.0%）** | **198/200（99.0%）** |
| Direct HTML | 188/200（94.0%） | **200/200（100.0%）** | 149/200（74.5%） | 120/200（60.0%） | 125/200（62.5%） | 132/200（66.0%） | 133/200（66.5%） | 135/200（67.5%） | 149/200（74.5%） | 98/200（49.0%） |
| WebGen-Agent | 194/200（97.0%） | 169/200（84.5%） | 154/200（77.0%） | 74/200（37.0%） | 89/200（44.5%） | 136/200（68.0%） | 148/200（74.0%） | 109/200（54.5%） | 154/200（77.0%） | 45/200（22.5%） |
| Direct + HTMLCure（strict） | 75/200（37.5%） | 75/200（37.5%） | 62/200（31.0%） | 52/200（26.0%） | 51/200（25.5%） | 53/200（26.5%） | 53/200（26.5%） | 59/200（29.5%） | 62/200（31.0%） | 40/200（20.0%） |
| Direct-BrowserRepair（最多 1 次调用；无浏览器反馈） | 186/200（93.0%） | **200/200（100.0%）** | 155/200（77.5%） | 128/200（64.0%） | 133/200（66.5%） | 137/200（68.5%） | 138/200（69.0%） | 143/200（71.5%） | 155/200（77.5%） | 106/200（53.0%） |

AlgoTutorGen 最终有 200/200 个任务通过生成与物化检查，其中 198/200 个页面进一步通过完整的九项浏览器行为检查。`Generation pass` 只说明产生了有效机器 artifact，不等于 Machine OK。

AlgoTutorGen 与主 Direct HTML 的任务级配对统计如下。`pp` 是百分点；`95% CI` 是通过率差值的区间估计；`McNemar p` 检验同一任务上两种方法的通过/失败是否明显偏向一方：

| 比较 | AlgoTutorGen | Direct HTML | 通过率差值 | 95% CI | 仅 AlgoTutorGen 通过 / 仅 Direct 通过 | McNemar p |
| --- | --- | --- | --- | --- | --- | --- |
| Machine OK | 198/200 | 98/200 | +50.0 pp | [43.0,57.0] | 101 / 1 | `4.06e-29` |

**指标注释：**

- **Load：** 页面能正常打开，并且没有阻断主要功能的错误。
- **Answer：** 页面上显示的最终答案与标准答案 `expected` 一致；不代表算法每一步、轨迹或讲解都正确。
- **Interaction：** 页面存在可达、可操作的学习者作答检查点；反馈、提示、显示答案和日志分别由后续独立指标检查。
- **Machine OK：** 本文定义的九项浏览器行为检查全部通过；它不是各项分数的平均值，任何一项失败都会使该页面失败。

**结果直读：** AlgoTutorGen 有 198/200 个页面同时通过九项检查；Direct HTML、WebGen-Agent、HTMLCure strict 和 BrowserRepair 1-call 分别为 98/200、45/200、40/200 和 106/200。Direct HTML 与 BrowserRepair 1-call 都能在 200/200 页面显示正确答案，但完整行为通过数明显低于答案通过数。

最终两个 Machine OK 失败任务是 `stack_valid_parentheses_full_core`（Wrong FB 失败）和 `string_longest_common_prefix_full_core`（Correct FB、Wrong FB 失败）；两页的 Load、Answer、Interaction、Hint、Show、Log 和 Mutation-free 均通过。

**主表口径：** 各方法的模型调用预算并不相同。BrowserRepair 的 1-call 条件尚未读取浏览器反馈；而且它与主 Direct 行不是逐题同一冻结页面，因此 106/200 对 98/200 不能直接解释为 repair 带来的提升。

### 0.2 九项指标的失败交集

下表按每个页面失败的九项数量重新分组。三列之和均为 200；“失败至少两项”表示同一页面存在多个失败，不能把各单项失败数直接相加。

| 方法 | 九项全部通过 | 恰好失败一项 | 失败至少两项 |
| --- | --- | --- | --- |
| **AlgoTutorGen（最终结果）** | **198/200（99.0%）** | 1/200（0.5%） | 1/200（0.5%） |
| Direct HTML | 98/200（49.0%） | 25/200（12.5%） | 77/200（38.5%） |
| WebGen-Agent | 45/200（22.5%） | 36/200（18.0%） | 119/200（59.5%） |
| Direct + HTMLCure（strict） | 40/200（20.0%） | 12/200（6.0%） | 148/200（74.0%） |
| Direct-BrowserRepair（最多 1 次调用；无浏览器反馈） | 106/200（53.0%） | 25/200（12.5%） | 69/200（34.5%） |

**结果直读：** AlgoTutorGen 的两个失败页面中，一个只失败一项，另一个失败两项。Direct HTML、WebGen-Agent、HTMLCure strict 和 BrowserRepair 1-call 分别有 77、119、148 和 69 个页面同时失败至少两项，因此 Machine OK 会低于任何单项通过数。

### 0.3 更换生成模型后的最终结果

本表只使用补跑完成后的最终结果。Direct 列是相同模型、相同 200 题上的冻结 Direct baseline。浏览器审计统一阻断外部资源，但两列不是相同模型调用次数或相同 token 预算。

| 生成模型 | AlgoTutorGen 九项全部通过 | Direct 九项全部通过 | 通过率差值 | 95% 置信区间 | McNemar 配对检验 p 值 |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V4-Flash | 200/200（100.0%） | 118/200（59.0%） | +41.0 pp | [34.5,48.0] | `4.14e-25` |
| GLM-5.2 | 196/200（98.0%） | 35/200（17.5%） | +80.5 pp | [75.0,86.0] | `2.81e-47` |
| Kimi-K2.5 | 194/200（97.0%） | 87/200（43.5%） | +53.5 pp | [46.0,60.5] | `4.79e-30` |

**指标注释：**

- **通过率差值：** AlgoTutorGen 通过率减去 Direct 通过率；`pp` 表示“百分点”，不是相对百分比。
- **95% 置信区间（95% CI）：** 对差值不确定范围的估计；本表三个区间都没有跨过 0。
- **McNemar p：** 对同一批任务上的成对通过/失败结果做检验；p 值很小表示不一致任务明显偏向其中一方，但 p 值本身不表示差距有多大。

**结果直读：** AlgoTutorGen 在 Flash、GLM 和 Kimi 上最终分别有 200、196 和 194 个页面通过 Machine OK，对应 Direct baseline 分别为 118、35 和 87 个。本文不再展示补跑前的固定预算结果。

### 0.4 Held-out 新任务结果

Held-out v1 包含 40 个未进入主实验的新任务，覆盖 15 个算法族。

| 数据集 | AlgoTutorGen 生成通过（Generation pass） | AlgoTutorGen 九项全部通过 | Direct 生成通过 | Direct 九项全部通过 | Machine OK 差值 | 95% 置信区间 | McNemar p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Held-out v1（40 题） | 39/40 | 39/40 | 40/40 | 18/40 | +52.5 pp | [37.5,67.5] | `9.54e-7` |

**指标注释：**

- **Generation pass：** 生成和物化阶段得到了有效 artifact；它不自动等于最终浏览器检查通过。
- **Machine OK 差值：** 39/40 与 18/40 的通过率相差 52.5 个百分点。
- **Held-out：** 这些任务没有进入主实验集合，但仍是一个固定的 40 题集合，不能代表全部开放域算法。

**结果直读：** AlgoTutorGen 在 40 个新任务中有 39 个生成并通过完整浏览器检查，Direct 有 40 个生成成功、18 个通过完整检查。

## 1. 指标与统计术语的通俗注释

### 1.1 浏览器行为指标

| 指标 | 通俗含义 | 不能直接推出什么 |
| --- | --- | --- |
| Load | 页面能打开，主要脚本和功能没有被错误阻断 | 不代表答案正确或交互完整 |
| Answer | 页面可见最终答案与 `expected` 一致 | 不代表过程、反馈或按钮可用 |
| Interaction | 学习者作答检查点可以找到并实际操作 | 不代表反馈、提示、显示答案或日志正确 |
| Correct FB | 答对时给出正确方向的反馈 | 不评价反馈文字是否具有最佳教学质量 |
| Wrong FB | 答错时给出正确方向的反馈 | 不代表提示或显示答案功能可用 |
| Hint | 提示按钮能产生预期提示行为 | 不代表学生因此获得学习增益 |
| Show | 显示答案按钮能正常工作 | 不评价学习效果 |
| Log | 提交行为能进入学习日志 | 不代表日志内容适合长期学习分析 |
| Mutation-free | 教学操作没有改写最终答案或算法事实 | 只覆盖已定义和已执行的操作检查 |
| Machine OK | 上述九项全部通过 | 不是平均分，也不是视觉评分或真人学习效果 |

### 1.2 成本与规模指标

| 术语 | 通俗含义 | 读法 |
| --- | --- | --- |
| Generation pass | 生成和 materialization 阶段产生有效 artifact | 只说明生成链走通，不等于浏览器 Machine OK |
| Materialization | 实际执行生成的 solver/tracker，并把结果变成可检查的语义轨迹和 artifact | 不是只检查文本格式 |
| Self-contained | HTML 不依赖外部网络资源 | 不代表答案或交互正确 |
| Fixed budget | 每题的候选数、修复轮数或调用上限固定 | 便于比较同一资源上限下的结果 |
| Strict | 按全部合同直接判定，包括 self-contained 要求 | 引入外部资源也会导致失败 |
| Blocked-external | 浏览器阻断外部请求后再测行为 | 只做敏感性分析，不会让文件本身变成 self-contained |
| Artifact | 一次生成、执行和验证后保存的机器可读产物 | 它可以继续被编译、渲染和审计 |
| Gate | 自动验收门，检查答案、轨迹、场景或浏览器合同 | 通过某一个 gate 不代表其他 gate 也通过 |
| Held-out | 没有进入主实验生成集合的固定新任务 | 支持有限集合上的泛化检查，不等于开放域泛化 |
| Stage1 / Stage2 | Stage1 负责可执行语义与固定 Runtime；Stage2 只增强展示层 | Stage2 结果不能替代 Stage1 correctness |
| Fault injection | 人工向正常样本注入已定义错误，再看验证器能否拒绝 | 只覆盖注入的错误类型 |
| LLM/VLM judge | 用语言模型或视觉语言模型按 rubric 给分或选 winner | 不是人工评审，也不进入算法 correctness gate |
| 模型调用（calls） | 调用生成模型的总次数 | 越少通常表示模型调用开销越低 |
| 总 tokens | 全部模型调用记录的 prompt 与 completion token 总量 | 不是货币成本；价格还取决于具体模型和计价 |
| calls/task | 平均每题调用模型多少次 | 总调用数除以任务数 |
| tokens/task | 平均每题消耗多少 token | `k` 表示千，例如 76.8k 约为 76,800 |
| tokens/success | 全部任务总 token 除以成功任务数 | 包含失败尝试的消耗；越低通常越省 |
| calls/success | 全部任务总调用数除以成功任务数 | 包含失败尝试；越低通常表示成功效率更高 |
| Mean time to valid | 从开始到得到有效结果的平均时间 | 越低表示平均等待时间更短 |
| Frames | 一个可视化页面包含的平均过程帧数 | 越多通常表示轨迹更长 |
| HTML | 生成的单文件 HTML 平均体积 | 越大通常越影响传输和加载 |
| Load time | 页面完成加载所需时间 | 越低越快 |
| Step latency | 点击下一步等单次步进操作的响应延迟 | 越低越流畅 |
| JS heap | 浏览器 JavaScript 堆内存占用 | 越低通常越省内存 |
| N/A | 该指标不适用于该系统 | 不能当作失败或 0 分 |

### 1.3 统计指标

| 术语 | 通俗含义 | 读法 |
| --- | --- | --- |
| pp | 百分点 | 99% 与 49% 相差 50 pp |
| 95% CI | 对差异可能范围的区间估计 | 差值区间不跨 0，表示观察到的方向较稳定 |
| McNemar p | 同一任务上两个方法通过/失败的配对检验 | p 小表示不一致对明显偏向一方；不表示效应大小 |
| Holm p | 对多次显著性检验做校正后的 p 值 | 用于降低多重比较造成的偶然显著 |
| Rank-biserial | 配对等级效应量，范围约为 -1 到 1 | 正值偏向表中第一个方法；绝对值越大，方向性差异越强 |
| Raw agreement | 两次评价直接给出相同 winner 的比例 | 越高表示排序越一致 |
| Flip | 两次评价的 winner 发生改变的比例 | 越低表示排序越稳定 |
| Cohen's kappa | 扣除随机一致后的评价者一致性 | 类别极不平衡时，可能与 raw agreement 看起来矛盾 |

## 2. 最终数据集与比较方法

### 2.1 最终数据规模与质量检查

| 集合 | 任务数 | 具体样例数 | 算法族 | 主要用途 |
| --- | --- | --- | --- | --- |
| Full-200 主 benchmark | 200 | 200 个 sample index 0 | 23 | 任务级配对主实验 |
| 完整 deterministic benchmark | 200 | 646 | 23 | 跨输入重放、release gate 和数据完整性检查 |
| Held-out v1 | 40 | 40 个 sample index 0 | 15 | 固定新任务上的泛化检查 |

主实验每个任务只使用一个 sample index 0，因此 200 行可以做任务级配对统计。646 个样例来自同一批 200 个任务，任务内样例彼此相关，不能当成 646 个独立新任务。

| 最终数据质量检查 | 结果 | 通俗说明 |
| --- | --- | --- |
| Answer/process release gate | 646/646 | 每个具体样例的答案与基础过程检查均通过 |
| Demo-ready | 200/200 | 每个任务都具备生成教学页面所需的完整字段 |
| 教学字段完整性 | 200/200 | 学习目标、交互任务、常见误区、提示策略和 Stage2 brief 均已补齐 |
| 题面与冻结字段检查 | 弱题面 0；locked-field error 0 | 最终题面均通过检查，测试输入、expected 和 oracle 等冻结字段未被误改 |

### 2.2 比较方法与冻结口径

| 方法 | 输入与起点 | 生成或修复方式 | 最终运行方式（Runtime） | 主表采用的冻结条件 |
| --- | --- | --- | --- | --- |
| **AlgoTutorGen（本文方法）** | 题目、输入、expected、可选策略 | LLM 生成可执行 spec；沙箱物化 SemanticTrace；经过结果、trace、过程连续性和 scene 门禁；再生成受限 teaching overlay | 确定性 SceneGraph compiler + 固定 Web Runtime | DeepSeek-V4-Pro 最终结果：generation 200/200、Machine OK 198/200 |
| **Direct HTML** | 与本文方法相同的题目、输入和 expected | 一次自由生成完整 HTML/CSS/JavaScript；主条件没有浏览器反馈修复 | 模型自由生成 | 冻结 full-200 Direct baseline |
| **WebGen-Agent** | 题目与页面要求 | 外部网页生成 agent 路径，多步生成网页 | agent 生成 | full-200 外部 baseline；统一离线浏览器审计 |
| **Direct + HTMLCure** | Direct HTML 候选页 | HTMLCure 对页面进行修复并决定是否接受改写 | 修复后的自由 HTML | strict self-contained 条件；引入外部资源的页面按失败处理 |
| **Direct-BrowserRepair pipeline** | Direct HTML 候选页 | 后续调用可读取通用浏览器反馈并整页重写 | 修复后的自由 HTML | 独立固定预算实验；从 call 2 开始包含反馈重写 |

**表格注释：**

- **Runtime：** 最终在浏览器中负责显示和交互的运行代码。AlgoTutorGen 使用固定 Runtime，其余方法由模型或修复器生成自由 HTML。
- **SemanticTrace：** 在沙箱中实际执行 solver/tracker 后得到的逐步算法状态记录。
- **SceneGraph：** 从 SemanticTrace 确定性编译出的可视化场景数据，固定 Web Runtime 只消费这层数据。
- **Gate：** 对答案、trace、过程连续性、scene 或浏览器行为执行的自动验收检查。
- **Teaching overlay：** 只补充讲解和教学交互的受限层，不应修改答案或算法事实。
- **冻结条件：** 主表实际采用的已保存实验条件，说明结果来自哪个预算和哪个最终候选。

Direct-to-SceneGraph、VerifiedTrace-to-LLM-HTML、no-interaction 等是消融或派生条件，不是完整方法，因此不放进这一方法表。

## 3. 修复策略与成本的直接结果

### 3.1 模型调用与 token 使用量

Stage1 与 Direct 页面生成成本：

| 条件 | 模型调用总数 | token 总数 | 平均调用数/题（calls/task） | 平均 token/题（tokens/task） |
| --- | --- | --- | --- | --- |
| AlgoTutorGen 最终采用链路 | 1,066 | 15,369,433 | 5.33 | 76.8k |
| Direct HTML | 222 | 4,385,641 | 1.11 | 21.9k |

其他生成与自动评价阶段：

| 阶段 | 模型调用总数 | token 总数 | 成本属于什么 |
| --- | --- | --- | --- |
| Stage2 最终采用链路 | 247 | 2,774,765 | 创意展示层最终页面生成 |
| Stage2 strict scene-salience VLM | 200 | 492,701 | 辅助的真实场景显著性/算法可读性压力评价 |
| 五方法统一教学与视觉盲评 | 1,001 | 3,565,397 | 999 个页面由 Gemini 评分，1 个页面按渲染失败最低分计入；另有 2 次格式重试 |
| Completion-phase paired LLM reviews | 1,202 | 4,177,949 | 1,200 对教学消融与新增 judge 稳健性评价，另含 2 次格式重试 |

**指标注释：** 调用数表示实际请求模型的次数；token 表示模型输入和输出的计量单位。表中生成成本只统计最终采用链路；自动评价成本单独列出。由于没有冻结模型价格，不能从 token 直接换算统一货币成本。

**结果直读：** AlgoTutorGen 最终采用链路平均每题使用 5.33 次调用和 76.8k tokens；Direct HTML 平均每题使用 1.11 次调用和 21.9k tokens。五方法统一教学与视觉评价覆盖 1,000 个页面，共产生 1,001 次模型调用，其中 2 次是格式重试。

### 3.2 Direct-BrowserRepair 固定调用上限

| 每题最多调用次数 | 页面加载 | 答案正确 | 交互可用 | 九项全部通过 | 平均 token/题 | 平均生成时间 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 186/200 | 200/200 | 155/200 | **106/200** | 19.7k | 207.2 s |
| 2 | 179/200 | 179/200 | 20/200 | 10/200 | 36.8k | 347.2 s |
| 3 | 185/200 | 184/200 | 41/200 | 15/200 | 53.7k | 477.6 s |
| 5 | 188/200 | 191/200 | 30/200 | 6/200 | 87.2k | 733.9 s |

**指标注释：** “每题最多调用次数”是独立的 fixed-budget 条件，不是同一页面逐轮累计后的存活数。1-call 只使用单次生成页；从 2-call 开始才包含浏览器反馈后的整页重写。平均生成时间以秒（s）计，越低表示平均等待越短。

**结果直读：** 四个预算中，1-call 的 Machine OK 最高，为 106/200；2、3、5-call 分别为 10/200、15/200 和 6/200。调用上限增加时，平均 token 和平均生成时间均增加。

修正资源解析后，四个预算共 1,000 个尝试均满足 self-contained 检查。该结果说明本实验中的自由整页反馈重写没有随预算单调改善，不能外推成所有 browser-repair 方法的普遍规律。

### 3.3 HTMLCure 的 strict 与 blocked-external 口径

HTMLCure full-200 共生成 269 个候选，接受 126 个改写。strict 条件要求文件本身不依赖外部资源，Machine OK 从 Direct 的 98/200 降到 40/200；配对中 fail→pass 为 1，pass→fail 为 59，exact McNemar `p=1.06e-16`。126 个接受改写中有 125 个引入 Google Fonts。下表是在浏览器中阻断外部请求后的敏感性结果。

| 阻断外部请求后的指标 | Direct HTML | HTMLCure |
| --- | --- | --- |
| 页面加载（Load） | 188/200 | 200/200 |
| 答案正确（Answer） | 200/200 | 200/200 |
| 交互可用（Interaction） | 149/200 | 148/200 |
| 正确回答反馈 | 120/200 | 112/200 |
| 错误回答反馈 | 125/200 | 120/200 |
| 提示可用 | 132/200 | 129/200 |
| 显示答案可用 | 133/200 | 130/200 |
| 学习日志可用 | 135/200 | 136/200 |
| 教学操作不改算法状态（Mutation-free） | 149/200 | 148/200 |
| 九项全部通过（Machine OK） | 98/200 | 91/200 |

**指标注释：** `strict` 检查文件本身是否 self-contained；`blocked-external` 只是运行时阻断网络请求，再观察页面行为。blocked 条件不会把依赖外部资源的文件变成 self-contained，因此只能作为敏感性分析。

**结果直读：** blocked-external 条件下，HTMLCure 的 Load 为 200/200、Machine OK 为 91/200；Direct 对应为 188/200 和 98/200。两者 Machine OK 的 McNemar `p=0.118`。

## 4. 其他稳健性、泛化与规模结果

跨模型和 held-out 结果已经前置到第 0.3、0.4 节。本节保留同题换输入和长轨迹规模数据。

### 4.1 同一任务更换输入

| 输入范围 | 结构化重放通过数 | 通过率 | 数据说明 |
| --- | --- | --- | --- |
| 主实验 sample index 0 | 200/200 | 100.00% | 每题的主输入 |
| 额外输入 | 426/446 | 95.52% | 同一批任务的其他具体输入 |
| 全部样例 | 626/646 | 96.90% | 主输入与额外输入合计 |

**指标注释：** 这里的“通过”表示冻结主实验的 solver/tracker/scene 链在新输入上结构化重放成功，不是浏览器 Machine OK。646 行来自同一批 200 个任务，任务内样例彼此相关，不能当作 646 个独立且均衡的新任务。

**结果直读：** 主输入通过 200/200，额外输入通过 426/446，合计通过 626/646。20 个失败来自 solve/trace 边界、expected 归一化、target 引用以及空或断连输入。

### 4.2 长轨迹规模

| 规模（Scale） | 平均过程帧数（frames） | 平均 HTML 体积 | 平均加载时间 | 单步操作延迟 | JS 堆内存 |
| --- | --- | --- | --- | --- | --- |
| Small | 104.4 | 1.40 MB | 120 ms | 14.7 ms | 6.3 MB |
| Medium | 543.3 | 23.25 MB | 1,933 ms | 45.4 ms | 59.1 MB |
| Large | 1,636.7 | 160.42 MB | 8,354 ms | 101.3 ms | 185.6 MB |

**指标注释：** `frames` 是页面保存的算法过程状态数；HTML 体积以 MB 计；平均加载时间和单步延迟以毫秒（ms）计；JS heap 是浏览器 JavaScript 堆内存。除 frames 外，其余四项通常越低越好。每个规模各有 18 个样本：frames 和 HTML 平均值使用全部 18 个；Small、Medium 的浏览器指标各测得 18 个，Large 的加载、延迟和内存指标来自成功测量的 16 个样本。

**结果直读：** 从 Small 到 Large，平均帧数、HTML 体积、加载时间、步进延迟和内存占用均增加。54/54 个样本完成 materialization，52/54 完成浏览器测量。KMP large 为 3,063 frames、581 MB；sliding-window unique large 为 5,533 frames、1.08 GB，两者都超过 60 秒加载预算。

## 5. 消融、组件必要性与验证器故障实验

### 5.1 Full-200 功能消融

| 条件 | 九项全部通过（Machine OK） | 页面加载 | 答案正确 | 交互可用 | 条件说明 |
| --- | --- | --- | --- | --- | --- |
| Full | 198/200 | 200/200 | 200/200 | 200/200 | 完整系统 |
| No teaching | 198/200 | 200/200 | 200/200 | 200/200 | 删除教学讲解，保留机器功能合同 |
| No interaction | 0/200 | 200/200 | 200/200 | 0/200 | 删除学生作答和反馈交互 |
| No teaching + interaction | 0/200 | 200/200 | 200/200 | 0/200 | 同时删除教学讲解与交互 |
| No SceneGraph compiler | 0/200 | 200/200 | 100/200 | 0/200 | 跳过确定性 SceneGraph compiler，只保留退化 trace 展示 |

**指标注释：** 每一行都继续按同一九项浏览器合同计算。No interaction 的 0/200 表示完整合同要求交互而该条件没有交互，不表示加载和答案也为 0。`No teaching` 与 Full 的 Machine OK 相同，是因为 Machine OK 不评价讲解文字质量。

**结果直读：** 删除教学文本不改变 Machine OK；移除交互或 SceneGraph compiler 后，完整合同降为 0/200。

### 5.2 教学质量消融

该实验使用匿名 LLM judge 比较完整系统与三个教学/交互消融版本，每个比较均为同一批 200 对页面。

| 比较 | Full wins | Full overall | 消融 overall | Teaching-effectiveness 差值 | Holm 校正 p |
| --- | --- | --- | --- | --- | --- |
| Full vs No teaching | 200/200 | 4.941 | 2.200 | +3.285 | `4.95e-35` |
| Full vs No interaction | 200/200 | 4.984 | 1.224 | +3.910 | `5.89e-41` |
| Full vs No teaching + interaction | 200/200 | 4.994 | 1.196 | +3.960 | `1.41e-42` |

**指标注释：** `overall` 和 `Teaching-effectiveness` 是 1–5 分的 LLM-judge 代理评分；三项 Teaching-effectiveness 比较的 matched-pairs rank-biserial 均为 1.0。它们说明代理评价明显偏向完整教学版本，不是真人学习效果。

### 5.3 非退化表示消融

| 50 题条件 | 完整系统（Full） | 消融版本（Ablation） | 直接说明 |
| --- | --- | --- | --- |
| Direct-to-SceneGraph | 49/50 | 1/50 | 保留固定 Runtime，但让模型直接产出 SceneGraph，跳过可执行 trace 与验证 |
| VerifiedTrace-to-LLM-HTML | 49/50 | 0/50 | 提供正确 trace，但最终仍由模型自由生成 HTML；50/50 页面显示正确答案 |

**指标注释：** 表内数值是 Machine OK。0/50 不等于 0/50 显示错误答案；它表示没有页面同时满足全部九项浏览器合同。Direct-to-SceneGraph 的配对差为 +96 pp，95% CI `[90,100]`，McNemar `p=7.11e-15`。

**结果直读：** 只有固定 Runtime 或只有正确 trace 都不足以得到完整可靠页面；完整的 trace—scene—runtime refinement chain 才通过 49/50。

### 5.4 Fault injection

最终 validator 接受 200/200 个 clean controls，并拒绝 2,246/2,400 个注入故障（93.58%）。

| 注入故障类型 | 被拒绝 |
| --- | --- |
| Wrong solve result | 200/200 |
| Wrong trace result | 200/200 |
| Wrong trace input | 200/200 |
| Empty trace events | 200/200 |
| Wrong trace state | 200/200 |
| Wrong interaction answer | 200/200 |
| Missing trace target | 200/200 |
| Empty SceneGraph objects | 200/200 |
| Wrong expected result | 198/200 |
| Deleted trace event | 48/200 |
| Reordered trace events | 200/200 |
| Missing SceneGraph reference | 200/200 |

**指标注释：** `clean controls` 是未注入错误的正常 artifact；每个故障类型注入 200 次。单事件删除只有 48/200 被拒绝，是因为被删除的 explain、mark 或重复事件在当前语义合同下可能冗余。

**与第 6.5 节的口径区别：** 本节使用全部 2,400 个注入样本。第 6.5 节排除 200 个语义不确定的 `trace_event_deleted` 样本，并把 2 个无序结果等价重排归入 semantics-preserving，因此语义违规分母为 2,198。两个分母不能混用。

## 6. 理论定向实验

本章集中整理 `plan/plan1.md` 对应的理论定向实验。理论公式由数学推导成立；下面的实验只检查定理假设在当前实现中是否近似成立、实现是否出现反例，以及理论模型能否解释实测结果。

### 6.1 理论主张与实验对应关系

| 理论主张 | 实验检查什么 | 直接结果 | 当前结论 |
| --- | --- | --- | --- |
| 定理 1：理想阶段局部恢复成本不高于全局重启 | 当前实现保留 solution spec 的 Local Resume 是否优于丢弃 spec 的 Global Restart | Flash 38/50 vs 42/50；GLM 42/50 vs 43/50，均无显著 Local 优势 | 当前实现不是完整 checkpoint recovery，理论关键前提不成立 |
| 定理 2：局部表示契约可以组合保持算法状态 | Trace、SceneGraph、Runtime 的 canonical state 是否逐帧一致 | 294/294 artifacts、55,108/55,108 frames 一致 | 支持已评估表示上的 preservation，不证明源 trace 的独立算法正确性 |
| 定理 3：教学状态不应污染算法事实状态 | 合法/非法 overlay 与随机教学动作是否改变算法状态 | 372 个主集合 variants、369 个跨模型 scenes 状态保持；1,561,298 次动作中 0 个观察违规 | 有限测试未找到反例，不等于形式证明 |
| 命题 4：嵌套合同联合存活率等于条件存活率乘积 | C1—C6 的累计和条件存活率在哪一层下降 | AlgoTutorGen 下游存活接近 1；Direct、WebGen、BrowserRepair 等在交互和反馈层继续下降 | 支持“约束纠缠发生在多个义务共享一个自由页面状态”的诊断 |
| 配套审计：契约应拒绝语义错误但接受无害变化 | semantic violations 与 semantics-preserving transformations 能否被区分 | 2,198/2,198 违规被拒绝，392/392 保持变换被接受 | 只覆盖定义的 mutation suite，不是 universal validator 证明 |

### 6.2 Local Resume vs Global Restart：负结果

两种策略使用同一组 50 个分层任务、同一模型、结构化输出空间、validator 和每题最多 3 次 policy decision。Local 保留当前 solution spec 并调用 repair；Global 丢弃 spec 后重新 generation。两者都会重新执行 materialization 和 teaching。

#### 6.2.1 端到端结果与恢复成功率

| 模型 | 策略 | 最终成功 | Token/成功页 | Calls/成功页 | 平均 time-to-valid |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V4-Flash | Local Resume | 38/50（76.0%） | 71,369 | 6.63 | 172.9 s |
| DeepSeek-V4-Flash | Global Restart | 42/50（84.0%） | 62,256 | 5.50 | 194.2 s |
| GLM-5.2 | Local Resume | 42/50（84.0%） | 92,385 | 6.69 | 533.8 s |
| GLM-5.2 | Global Restart | 43/50（86.0%） | 96,186 | 6.65 | 558.2 s |

**指标注释：** `Success` 是在预算内生成有效 Stage1 artifact，不是浏览器 Machine OK。`Token/成功页` 和 `Calls/成功页` 把最终失败任务的消耗也计入分子；`time-to-valid` 只在成功任务上统计首次得到有效 artifact 的时间。

#### 6.2.2 配对成功分布

| 模型 | 两者均成功 | 仅 Local 成功 | 仅 Global 成功 | 两者均失败 | Local−Global | McNemar exact p |
| --- | --- | --- | --- | --- | --- | --- |
| DeepSeek-V4-Flash | 32 | 6 | 10 | 2 | -8.0 pp | 0.4545 |
| GLM-5.2 | 37 | 5 | 6 | 2 | -2.0 pp | 1.0000 |

**结果直读：** Flash 上 Global 多成功 4 题，GLM 上 Global 多成功 1 题；两组配对检验都没有发现显著的 Local 成功率优势。p 值不显著不能解释为两策略严格等价。

#### 6.2.3 Token 成本分解

| 模型 | 策略 | Spec generation/repair token/成功页 | Teaching token/成功页 | 总 token/成功页 |
| --- | --- | --- | --- | --- |
| Flash | Local | 25,031 | 46,338 | 71,369 |
| Flash | Global | 25,781 | 36,476 | 62,256 |
| GLM | Local | 37,342 | 55,043 | 92,385 |
| GLM | Global | 47,462 | 48,724 | 96,186 |

Local 在两个模型上都降低了 spec generation/repair 成本，但 repair 后重新 materialize 并重新调用 teaching。Flash 的 teaching 重算超过了 spec 节省量；GLM 的 spec 节省较大，所以总 token 略低，但成功率仍少 1 题。

#### 6.2.4 有限预算理论拟合

该拟合用同一批运行估计首轮/恢复概率和平均成本，是 in-sample explanatory fit，不是独立预测集。

| 模型 | 策略 | 预测成功率 | 实测成功率 | 绝对误差 | Token/成功页相对误差 |
| --- | --- | --- | --- | --- | --- |
| Flash | Local | 76.89% | 76.00% | 0.89 pp | 0.26% |
| Flash | Global | 85.72% | 84.00% | 1.72 pp | <0.01% |
| GLM | Local | 83.15% | 84.00% | 0.85 pp | 0.23% |
| GLM | Global | 87.06% | 86.00% | 1.06 pp | <0.01% |

**理论边界：** 该负结果不否定理想 stage-local recovery 定理，而是说明当前实现违反“成功阶段可 checkpoint、失败只重试当前阶段、下游已验证工作不重算”的关键前提。

### 6.3 Trace→Scene→Runtime 语义保持与确定性

统一投影比较 `trace.events[t].state → scene.frames[t].state → runtime frame().state`。布局坐标、CSS 和教学文字不进入 canonical algorithm state。

| 数据集 | Artifact 全帧通过 | 等价 frames | Frame equivalence |
| --- | --- | --- | --- |
| Main 200 | 200/200 | 9,421/9,421 | 100.0% |
| Held-out representation audit set | 40/40 | 4,568/4,568 | 100.0% |
| Long-trace 54 | 54/54 | 41,119/41,119 | 100.0% |
| **总计** | **294/294** | **55,108/55,108** | **100.0%** |

20 个分层普通 artifact 分别重新编译和渲染 10 次；每个 artifact 只有一个 render hash，每个 compiled variant 只有一个 projection hash。

**指标注释：** `Artifact 全帧通过` 表示该 artifact 的每一帧都通过状态投影比较。Held-out representation audit 使用 40 个可审计 artifact；第 0.4 节的 held-out 生成实验仍按其冻结口径报告 39/40。

**解释边界：** 结果支持已评估 artifact 上的表示级语义保持和测试环境确定性，不证明 source trace 的每一步都符合独立算法语义，也不是像素级形式验证。

### 6.4 Nested contract survival

合同层级固定为：C1 答案正确；C2 在 C1 基础上页面加载；C3 再要求交互可达；C4 再要求正确与错误双向反馈；C5 再要求 hint、show-answer 和 learning log；C6 最后要求教学操作不干扰算法状态。

#### 6.4.1 累计存活率

累计存活率表示从 C1 开始一直满足到当前层的页面比例。

| 方法/条件 | C1 | C2 | C3 | C4 | C5 | C6 |
| --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen main | 100.0% | 100.0% | 100.0% | 99.0% | 99.0% | 99.0% |
| Direct HTML main | 100.0% | 94.0% | 74.5% | 54.0% | 49.0% | 49.0% |
| AlgoTutorGen Flash final | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Direct Flash | 99.0% | 95.0% | 81.0% | 65.5% | 59.0% | 59.0% |
| AlgoTutorGen GLM final | 99.0% | 99.0% | 99.0% | 98.0% | 98.0% | 98.0% |
| Direct GLM | 100.0% | 91.0% | 53.0% | 38.0% | 17.5% | 17.5% |
| AlgoTutorGen Kimi final | 97.5% | 97.5% | 97.5% | 97.0% | 97.0% | 97.0% |
| Direct Kimi | 99.5% | 95.0% | 68.0% | 52.5% | 43.5% | 43.5% |
| WebGen-Agent | 84.5% | 84.5% | 67.5% | 27.5% | 22.5% | 22.5% |
| Direct-BrowserRepair-5 | 95.5% | 92.5% | 14.0% | 6.0% | 3.0% | 3.0% |
| HTMLCure blocked-external | 100.0% | 100.0% | 74.0% | 49.5% | 45.5% | 45.5% |

#### 6.4.2 条件存活率

条件存活率 `α_i` 的分母是已经通过上一层全部合同的页面。例如 `α4` 表示已经通过答案、加载和交互的页面中，还有多少同时通过双向反馈。

| 方法/条件 | α1 | α2 | α3 | α4 | α5 | α6 |
| --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen main | 100.0% | 100.0% | 100.0% | 99.0% | 100.0% | 100.0% |
| Direct HTML main | 100.0% | 94.0% | 79.3% | 72.5% | 90.7% | 100.0% |
| AlgoTutorGen Flash final | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Direct Flash | 99.0% | 96.0% | 85.3% | 80.9% | 90.1% | 100.0% |
| AlgoTutorGen GLM final | 99.0% | 100.0% | 100.0% | 99.0% | 100.0% | 100.0% |
| Direct GLM | 100.0% | 91.0% | 58.2% | 71.7% | 46.1% | 100.0% |
| AlgoTutorGen Kimi final | 97.5% | 100.0% | 100.0% | 99.5% | 100.0% | 100.0% |
| Direct Kimi | 99.5% | 95.5% | 71.6% | 77.2% | 82.9% | 100.0% |
| WebGen-Agent | 84.5% | 100.0% | 79.9% | 40.7% | 81.8% | 100.0% |
| Direct-BrowserRepair-5 | 95.5% | 96.9% | 15.1% | 42.9% | 50.0% | 100.0% |
| HTMLCure blocked-external | 100.0% | 100.0% | 74.0% | 66.9% | 91.9% | 100.0% |

**结果直读：** AlgoTutorGen 的主要损失发生在最前面的 generation/answer 或极少数双向反馈边界；自由 HTML、agent 和 repair 条件在加载、交互与双向反馈处继续丢失。多数方法的 `α6=100%` 只表示已经通过 C5 的页面没有在当前 mutation-free 检查上继续下降，不表示全部页面通过。

**理论边界：** 联合存活率等于条件存活率乘积是概率链式法则，不依赖各合同独立。实验贡献是定位损失边界，而不是提出新的概率定理。

### 6.5 Semantic mutation 契约辨别力

| 变换类别 | 期望 | 直接结果 |
| --- | --- | --- |
| 定义的 semantic violations | Reject | 2,198/2,198 |
| Teaching-text rewrites | Accept | 195/195 |
| Visual-metadata changes | Accept | 195/195 |
| Equivalent unordered-result reorderings | Accept | 2/2 |
| **Semantics-preserving total** | **Accept** | **392/392** |

第 5.4 节全部注入样本中的 `trace_event_deleted` 不直接视为真实语义破坏，因为被删除事件可能是冗余 explain/mark。两个原本像 `expected_result_wrong` 的接受样例来自无序集合式结果重排，经 case-aware oracle 判定语义等价后归为 preserving。

**解释边界：** 结果说明 validator 完整区分了本实验定义的有限 mutation suite，不代表对所有未来错误 universal soundness 或 completeness。

### 6.6 Teaching overlay 隔离与跨模型复用

| Overlay 条件 | 规模 | 直接结果 |
| --- | --- | --- |
| 冻结 overlay 重放 | 372 个 SceneGraph variants | 372/372 state hash 保持 |
| Concise 合法 overlay | 372 | 372/372 保持 |
| Detailed 合法 overlay | 372 | 372/372 保持 |
| Schema-valid random-text overlay | 372 | 372/372 保持 |
| 非法 `final_answer` / `state` 写入 | 372 | 372/372 被 sanitizer 清洗，state hash 保持 |
| Negative step | 372 | 372/372 schema reject |
| Nonexistent step | 372 | 372/372 contract warn/reject |
| GLM cross-model overlay | 369 个可映射 scenes | 369/369 state hash 保持；169 完整应用，200 因 step 集差异部分应用 |

**指标注释：** `state hash` 是 canonical algorithm state 的摘要。hash 保持表示教学文字和教学交互没有改写受保护算法事实；`step not found` 表示两模型 trace 的步骤集合不同，不是状态污染。非法字段结果是 sanitization，不应写成所有未知字段都由 schema 直接拒绝。

### 6.7 Pedagogical noninterference property-based stress

| 覆盖量 | 结果 |
| --- | --- |
| 唯一页面 | 240（main 200 + held-out audit 40） |
| 随机动作序列 | 24,000 |
| 总动作 | 1,561,298 |
| 纯教学动作 | 435,859 |
| 导航/variant 动作 | 1,125,439 |
| 页面通过 | 240/240 |
| Overlay artifacts 通过 | 240/240 |
| 观察到的状态污染违规 | 0 |

每页执行 100 条、每条 30–100 个动作的随机序列。纯教学动作要求 artifact hash、当前算法 state hash 和 step 均不变；导航与 variant 切换允许当前帧变化，但必须落到目标 verified frame，并保持完整 artifact hash 不变。

**结果直读：** 在 1,561,298 次浏览器动作中没有找到教学状态污染算法事实状态的反例。

**解释边界：** 这是大规模反例搜索，不是对全部未来浏览器执行的形式化 noninterference 证明。

## 7. 教学与视觉辅助指标

本节使用五种方法各自冻结的 Full-200 最终页面。Naps 和 TRAKLA2-style 由最终 HTML 与浏览器审计直接计算；教学与视觉分数由 `gemini-3-flash-preview` 在隐藏方法名称后按同一 rubric 评价。它们都是自动代理指标，不属于 Machine OK，也不构成真人学习效果证据。

**指标首次说明：**

- **Naps engagement（0–5）：** 自动判断页面支持的学习者参与层级：0 不可观看、1 观看、2 作答并获得双向反馈、3 修改输入并重跑、4 自己构造、5 展示或同伴分享。它不是页面质量分，也不是真实学生投入度。
- **TRAKLA2-style（0–7）：** 检查页面运行、答案可见、操作可达、双向反馈、显示答案、学习日志和教学操作不改算法状态七项；`Core pass` 表示七项全部通过。它不是 TRAKLA2 官方认证，也不包含 Hint。
- **教学 Overall（1–5）：** 内容质量、学习目标对齐、反馈适应、交互易用、展示设计、教学有效性和易用性七维均值。
- **视觉 Overall（1–5）：** 题面—视觉贴合、算法状态可读性、过程变化清晰度和教学视觉设计四维均值。
- **全维度 ≥3：** 同一页面的全部教学七维或视觉四维都不低于 3 分；它比只看平均分更严格。

### 7.1 五方法核心教学与视觉结果

| 方法 | Naps 均值（0–5） | TRAKLA2 Core pass | 教学 Overall（1–5） | 教学全维度 ≥3 | 视觉 Overall（1–5） | 视觉全维度 ≥3 |
| --- | --- | --- | --- | --- | --- | --- |
| **AlgoTutorGen / Stage2** | **1.990** | **198/200** | **4.856** | **198/200** | **4.755** | **199/200** |
| Direct HTML | 1.480 | 99/200 | 4.203 | 110/200 | 4.561 | 186/200 |
| WebGen-Agent | 1.415 | 47/200 | 3.969 | 76/200 | 4.441 | 177/200 |
| Direct + HTMLCure（strict） | 0.590 | 40/200 | 3.147 | 44/200 | 4.300 | 163/200 |
| Direct-BrowserRepair（1-call） | 1.510 | 107/200 | 4.297 | 118/200 | 4.670 | 191/200 |

**结果直读：** AlgoTutorGen / Stage2 在本节六个汇总指标上均为最高。BrowserRepair 1-call 的教学和视觉代理分高于主 Direct，但两者不是逐题同一冻结页面，不能把差值直接解释为一次 repair 的因果收益。

### 7.2 教学代理指标明细

#### 7.2.1 Naps 与 TRAKLA2-style 自动行为

Naps 的层级数量按 `0 / 1 / 2 / 3 / 4 / 5` 顺序列出，即“不可观看 / 观看 / 作答 / 修改 / 构造 / 展示”。

| 方法 | Naps 层级数量（0/1/2/3/4/5） | Naps 均值 | TRAKLA2 Core pass | TRAKLA2 平均满足项（0–7） |
| --- | --- | --- | --- | --- |
| **AlgoTutorGen / Stage2** | 0 / 2 / 198 / 0 / 0 / 0 | **1.990** | **198/200（99.0%）** | **6.990** |
| Direct HTML | 12 / 80 / 108 / 0 / 0 / 0 | 1.480 | 99/200（49.5%） | 5.310 |
| WebGen-Agent | 6 / 118 / 63 / 13 / 0 / 0 | 1.415 | 47/200（23.5%） | 4.965 |
| Direct + HTMLCure（strict） | 125 / 32 / 43 / 0 / 0 / 0 | 0.590 | 40/200（20.0%） | 2.145 |
| Direct-BrowserRepair（1-call） | 14 / 70 / 116 / 0 / 0 / 0 | 1.510 | 107/200（53.5%） | 5.465 |

**结果直读：** WebGen-Agent 有 13 个页面达到“修改输入并重跑”层级，但双向反馈和完整自动练习组件通过数较低；AlgoTutorGen 的 198 个页面达到“作答并获得双向反馈”，且同样有 198 个页面通过 TRAKLA2-style 七项检查。

#### 7.2.2 LORI/MERLOT-informed 教学盲评

下表所有分数均为 1–5 分，越高表示代理评价越正面。`评分覆盖` 中的“VLM”表示截图由 Gemini 评分；“失败最低分”表示页面自身无法完成渲染，未修复 baseline，而是将全部维度按 1 分计入 200 页分母。

| 方法 | 评分覆盖 | Overall | 内容质量 | 目标对齐 | 反馈适应 | 交互易用 | 展示设计 | 教学有效性 | 易用性 | 全七维 ≥3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **AlgoTutorGen / Stage2** | 200 VLM | **4.856** | **4.945** | **4.900** | **4.960** | **4.975** | 4.385 | **4.935** | **4.895** | **198/200** |
| Direct HTML | 200 VLM | 4.203 | 4.720 | 4.605 | 3.300 | 3.885 | 4.460 | 4.180 | 4.270 | 110/200 |
| WebGen-Agent | 199 VLM + 1 失败最低分 | 3.969 | 4.600 | 4.685 | 2.660 | 3.560 | 4.425 | 3.805 | 4.050 | 76/200 |
| Direct + HTMLCure（strict） | 200 VLM | 3.147 | 4.100 | 4.180 | 1.930 | 2.160 | 4.300 | 2.990 | 2.370 | 44/200 |
| Direct-BrowserRepair（1-call） | 200 VLM | 4.297 | 4.795 | 4.685 | 3.435 | 3.985 | **4.490** | 4.370 | 4.320 | 118/200 |

**指标注释：** 浏览器行为证据用于反馈、交互和功能判断，截图用于内容呈现与展示设计；方法名称不进入评分提示。WebGen-Agent 的 `tarjan_scc` 页面自身出现渲染死循环，按七个教学维度均为 1 分计入，而不是删除该失败页或修复后重评。

### 7.3 五方法同 rubric 视觉盲评

| 方法 | 评分覆盖 | Overall | 题面—视觉贴合 | 算法状态可读性 | 过程变化清晰度 | 教学视觉设计 | 全四维 ≥3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **AlgoTutorGen / Stage2** | 200 VLM | **4.755** | **4.640** | 4.670 | **4.915** | **4.795** | **199/200** |
| Direct HTML | 200 VLM | 4.561 | 4.455 | 4.605 | 4.660 | 4.525 | 186/200 |
| WebGen-Agent | 199 VLM + 1 失败最低分 | 4.441 | 4.500 | 4.645 | 4.150 | 4.470 | 177/200 |
| Direct + HTMLCure（strict） | 200 VLM | 4.300 | 4.350 | 4.445 | 4.050 | 4.355 | 163/200 |
| Direct-BrowserRepair（1-call） | 200 VLM | 4.670 | 4.590 | **4.725** | 4.730 | 4.635 | 191/200 |

**结果直读：** AlgoTutorGen / Stage2 的视觉 Overall、题面贴合、过程变化和教学视觉设计均值最高；BrowserRepair 1-call 的算法状态可读性均值最高。这里报告的是自动视觉代理评分，不是人工审美或学习效果结论。

### 7.4 Stage2 单独展示层检查

Stage2 只增强展示层，算法 correctness 仍由 Stage1 负责。下面两组结果只描述 AlgoTutorGen 的 Stage2 页面，不用于替代上面的五方法同口径比较。

#### 7.4.1 浏览器与布局机器审计

| 最终检查 | 直接结果 | 说明 |
| --- | --- | --- |
| Creative OK | 200/200 | 最终页面均同时通过 Stage2 浏览器与严格布局条件 |
| Browser smoke | 200/200 | 最终页面均可在浏览器运行 |
| Strict layout audit | 200/200 | 最终页面均通过严格布局检查 |
| 实际审计帧 | 1,494 | 平均约 7.47 帧/页面 |
| 非许可重叠 / 裁切 / 文字遮挡 | 0 / 0 / 0 | 最终页面上的三类布局错误计数 |

**指标注释：** `Creative OK` 表示页面同时满足 Stage2 浏览器与严格布局条件；`Browser smoke` 检查页面可运行；严格布局审计检查非许可 overlap、clipped 和 text occlusion。它们都不检查算法答案，也不等于人工审美偏好。

#### 7.4.2 辅助 strict scene-salience 压力审计

这是一套比第 7.3 节更窄、更严格的辅助 rubric，要求页面具有清晰的真实场景映射；抽象算法页面即使算法状态可读，也可能在该指标上失败。

| 辅助 VLM 指标 | 直接结果 | 平均分或构成 |
| --- | --- | --- |
| 有效响应 | 200/200 | 0 个调用失败 |
| Strict scenario salience 通过 | 51/200 | 平均 2.645；通过阈值 3.5 |
| Algorithm readability 通过 | 193/200 | 平均 4.235；通过阈值 3.0 |
| 算法状态可见 | 196/200 | 4 个页面未识别到可见算法状态 |
| Generic / non-generic visual | 107 / 93 | 107 个被判为通用算法图，93 个具有非通用场景视觉 |

**结果直读：** 严格真实场景显著性只有 51/200，而算法可读性为 193/200。这说明 Stage2 更稳定地呈现了算法状态，但并非每个抽象算法都获得了强现实场景隐喻；因此该指标保留为辅助压力测试，不替代第 7.3 节的五方法四维比较。

## 8. 外部方法、跨模型明细与 Judge 稳健性

### 8.1 外部方法补充

| 方法 | 可直接报告的结果 | 指标适用范围与说明 |
| --- | --- | --- |
| WebGen-Agent | 200/200 generation，Machine OK 45/200 | `tarjan_scc` 审计超时，保守计为失败 |
| HTMLCure | strict Machine OK 40/200；blocked-external Machine OK 91/200 | blocked-external 只做敏感性分析 |
| EduVisAgent | 冻结公开实现输出教学计划和逐 section UI-plan 文本；按六个教学部分估算，200 题约需 7,600 次模型调用 | 不输出可统一审计的网页，九项浏览器指标未定义，因此不进入数值主表 |
| 传统系统 exact-overlap | Algorithm Visualizer N=3、Python Tutor N=2、LeetCode Solution Visualizer N=2；在各自支持范围内通过步骤导航、状态和终态检查 | 依赖人工模板、在线服务或 adapter；unsupported case 与 tutoring-specific 指标为 N/A，不能记为失败 |

**指标注释：** `N` 是传统系统实际存在可比支持的任务数量，不是完整 200 题分母。

传统系统 exact-overlap 的能力检查如下。各系统只在确实存在精确支持的少量任务上测试，因此不能把不同分母直接用于排名。

| 系统与实际支持范围 | Load | Forward | Back/reset | Play/run | State | Code sync | Final | Input control | External-free |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Algorithm Visualizer，固定样例 N=3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 |
| Python Tutor，精确 sample-0 N=2 | 2/2 | 2/2 | 2/2 | N/A | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 |
| LeetCode Solution Visualizer，适配后 N=2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 |

**边界说明：** 预测判分、双向反馈、hint、show-answer 和 learning log 对这些系统没有统一定义，记为 N/A 而不是失败。候选审计共登记 11 个系统；除已执行的 WebGen-Agent 和 HTMLCure 外，没有新系统同时满足任意任务输入、可运行浏览器 artifact、无人值守 Full-200 和同一九项合同。

### 8.2 跨模型最终结果明细

| 模型 | AlgoTutorGen 最终 generation | AlgoTutorGen 最终 Machine OK | Direct generation | Direct Machine OK |
| --- | --- | --- | --- | --- |
| DeepSeek-V4-Flash | 200/200（100.0%） | 200/200（100.0%） | 198/200 | 118/200（59.0%） |
| GLM-5.2 | 198/200（99.0%） | 196/200（98.0%） | 200/200 | 35/200（17.5%） |
| Kimi-K2.5 | 195/200（97.5%） | 194/200（97.0%） | 200/200 | 87/200（43.5%） |

**指标注释：** `generation` 表示生成和物化得到有效 artifact；`Machine OK` 表示九项浏览器行为全部通过。表中只保留补跑完成后的最终数据，不展示补跑前结果。Direct 使用相同模型和任务，但调用次数和 token 预算不同。

以下是最终结果的九项机器指标，所有数值均以 200 为分母：

| 模型 / 方法 | Load | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Flash / AlgoTutorGen | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 |
| Flash / Direct | 190 | 198 | 164 | 142 | 146 | 153 | 154 | 145 | 164 | 118 |
| GLM / AlgoTutorGen | 198 | 198 | 198 | 196 | 196 | 198 | 198 | 198 | 198 | 196 |
| GLM / Direct | 182 | 200 | 107 | 82 | 88 | 60 | 88 | 80 | 107 | 35 |
| Kimi / AlgoTutorGen | 195 | 195 | 195 | 194 | 194 | 195 | 195 | 195 | 195 | 194 |
| Kimi / Direct | 190 | 199 | 137 | 119 | 111 | 125 | 117 | 125 | 137 | 87 |

最终 Machine OK 的任务级配对分布：

| 模型 | 仅 AlgoTutorGen 通过 | 仅 Direct 通过 | 两者都通过 | 两者都失败 |
| --- | --- | --- | --- | --- |
| Flash | 82 | 0 | 118 | 0 |
| GLM | 162 | 1 | 34 | 3 |
| Kimi | 109 | 2 | 85 | 4 |

### 8.3 Judge 稳健性

每一行都对同一批 200 对页面进行匿名模型评价。

| Judge 与展示顺序 | AlgoTutorGen wins | Direct wins | Ties |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro frozen | 193 | 6 | 1 |
| DeepSeek-V4-Pro swapped | 194 | 4 | 2 |
| gemini-3-flash-preview frozen | 191 | 9 | 0 |
| gemini-3-flash-preview swapped | 190 | 10 | 0 |

**指标注释：** `frozen` 使用原始展示顺序，`swapped` 交换两种方法的左右或先后顺序；`wins` 是文本 LLM judge 根据结构化页面证据选为更好页面的次数，`ties` 是平局次数。这里的 Gemini 不使用第 7.3 节的截图 VLM 口径。这是模型评价稳健性，不是人工评审一致性或 judge 正确性。

**结果直读：** DeepSeek 顺序交换的 winner agreement 为 95.5%、flip 为 4.5%、kappa 为 0.289；Gemini 分别为 97.5%、2.5%、0.724；两个模型 frozen-order winner agreement 为 93.0%、kappa 为 0.092。

## 9. 结果与主张边界

最终结果支持以下结论：AlgoTutorGen 在 Full-200、三种替代生成模型和 held-out 集合上都保持较高的完整行为通过率；正确答案本身不足以代表页面可靠，主要差异出现在交互、双向反馈和状态隔离；完整的 trace—scene—runtime 链比单独保留正确 trace 或固定 Runtime 更可靠。理论定向实验还表明，当前实现保持了已评估表示的状态投影，并在有限 mutation suite 和 1,561,298 次随机动作中未发现状态污染反例。

当前结果不能外推为学生学习效果、任意算法的形式化正确性、validator 的 universal soundness/completeness、开放域泛化或更低成本。五方法视觉表是自动代理评分，不能表述为人工审美结论；BrowserRepair 1-call 的算法状态可读性均值也高于 Stage2。人工校准、专家评审和学生实验尚未完成，因此本文不报告相应结果。

---

## 10. 详细版的数据口径与来源优先级

### 10.1 收录原则

本详细版遵循以下规则：

1. 只把已经完成并冻结的实验写成结果，不把 pilot、debug、shard、resume 或失败重试目录分别当作独立实验。
2. 同一实验如果存在补跑后的最终结果，只报告最终冻结结果。跨模型部分只使用 Flash 200/200、GLM 196/200、Kimi 194/200 的最终 Machine OK，不再展示补跑前数字。
3. 同一个数字如果在旧汇总和新机器报告中冲突，以时间更晚、口径更明确的最终机器报告为准。
4. 200 个任务的 sample index 0 是主配对单位；646 个样例用于同题换输入，不当作 646 个相互独立的新任务。
5. 自动 judge、VLM 和严格场景显著性只作为代理评价；没有真人数据时不推断学习效果。
6. 原始 case、HTML、JSON、截图和逐帧记录保留在 output 目录，本文件汇总其中可以直接支撑论文主张的结果。

### 10.2 最终数据源优先级

| 实验族 | 最终结果来源 | 读取口径 |
| --- | --- | --- |
| Full-200 Stage1 与 Direct | [experiment_summary.json](../output/experiments/algotutorgen_full_200_20260706/report/experiment_summary.json)；[interaction_semantic_eval_report.json](../output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine/interaction_semantic_eval_report.json) | 使用 selected-final Stage1 和冻结 Direct 页面 |
| 主实验配对统计 | [paired_statistics.json](../output/experiments/algotutorgen_completion_20260713/statistics/paired_statistics.json) | 200 个相同 case ID；seeded paired bootstrap、exact McNemar、Holm |
| 三个替代生成模型 | [multimodel_summary.json](../output/experiments/algotutorgen_multimodel_full200_20260713/multimodel_summary.json) | 只读取 final_quality 和 final_stage1，不读取补跑前结果 |
| Held-out 40 | [heldout_40](../output/experiments/algotutorgen_plan_completion_20260713/heldout_40) | 原始生成结果固定为 39/40；后续补齐的第 40 个 artifact 只用于表示审计 |
| Direct-BrowserRepair | [budget_curve_report.json](../output/experiments/algotutorgen_plan_completion_20260713/direct_browser_repair_5/budget_curve_report.json) | 四个独立预算：1、2、3、5 calls |
| WebGen-Agent | [report.json](../output/external_baselines/webgen/audit_all200_sample0/report.json) | Full-200 sample 0；统一九项浏览器审计 |
| HTMLCure | [htmlcure_full200_analysis.json](../output/external_baselines/htmlcure_all200_sample0/htmlcure_full200_analysis.json) | strict 为正式结果；blocked-external 为敏感性分析 |
| 646 样例重放 | [cross_input_replay_report.json](../output/experiments/algotutorgen_completion_20260713/cross_input_replay/cross_input_replay_report.json) | 冻结主 artifact 在同题其他输入上的结构化重放 |
| 长轨迹 | [long_trace_scalability_report.json](../output/experiments/algotutorgen_plan_completion_20260713/long_trace_scalability/long_trace_scalability_report.json) | 18 个任务 × small/medium/large |
| Full-200 功能消融 | [ablation_machine_statistics.json](../output/experiments/algotutorgen_completion_20260713/statistics/ablation_machine_statistics.json) | 与 Full 同 case 配对 |
| 教学质量消融 | [ablation_paired_statistics.json](../output/experiments/algotutorgen_completion_20260713/statistics/ablation_paired_statistics.json) | 200 对匿名 LLM 评价 |
| 非退化表示消融 | [nondegenerate_ablations](../output/experiments/algotutorgen_plan_completion_20260713/nondegenerate_ablations) | 50 个分层任务 |
| Fault injection | [gate_fault_injection_report.json](../output/experiments/algotutorgen_plan_completion_20260713/validator_fault_rerun/gate_fault_injection_report.json) | 使用最终 validator 重跑的 2,400 个 fault；旧 completion summary 的 fault 字段已过期 |
| 理论定向实验 | [theory_aligned_20260714](../output/experiments/theory_aligned_20260714) | 语义保持、mutation、overlay、noninterference、Local/Global、合同存活率 |
| 五方法教学与视觉评价 | [all_method_auxiliary_eval_report.json](../output/experiments/all_method_auxiliary_eval_20260718/all_method_auxiliary_eval_report.json) | 当前五方法同 rubric 最终结果 |
| 传统系统 overlap | [overlap_study_summary.json](../output/external_baselines/traditional_systems/overlap_study_summary.json) | 仅在系统实际支持的 exact-overlap 小集合内报告 |

### 10.3 容易混淆的来源

- 跨模型 JSON 同时保存 primary_fixed_budget 和 final_quality。本文件按用户冻结口径只报告 final_quality。
- completion_summary.json 中较早的 fault rejection 结果已被 validator_fault_rerun 覆盖，正式数字是 2,246/2,400。
- Held-out 原始生成是 39/40。理论审计为了覆盖 40 个 artifact 做过定向补齐，但不能把主生成结果改写为 40/40。
- Stage2 有多轮视觉报告。五方法正式教学与视觉比较以 all_method_auxiliary_eval_20260718 为准；较早 Stage2 报告只用于 Stage2 机器布局和 strict scene-salience 辅助审计。
- HTMLCure strict 与 blocked-external 是两个不同问题：前者检查文件本身是否离线自包含，后者只是在运行时阻断网络。

## 11. 详细实验协议

### 11.1 Benchmark 结构

最终主数据文件为 [algo_learn_env_benchmark.json](../benchmark/algo_learn_env_benchmark.json)。

| 维度 | 最终分布 |
| --- | --- |
| 任务 | 200 |
| 具体样例 | 646 |
| 算法族 | 23 |
| 难度 | easy 43；medium 157 |
| 数据来源 | deterministic_synthetic 71；public_synthetic 129 |
| Gate layer | family_core 62；expansion 138 |
| Oracle 类型 | independent_reference 119；bruteforce 59；property 19；closed_form 3 |
| Oracle 风险标记 | none 185；verifier_matches_solve 15 |
| 支持等级 | strong 145；medium_plus 53；medium 2 |
| 每题样例数 | 3 个样例的任务 156；4 个 22；2 个 11；5 个 8；8 个 2；12 个 1 |
| 主实验单位 | 每题 sample index 0，共 200 对 |
| 稳健性单位 | 同一 200 题的全部 646 行，不视为独立平衡样本 |

23 个算法族的任务分布如下：

| 算法族 | 任务数 |
| --- | ---: |
| 数组指针 / 窗口 / 前缀 | 21 |
| BFS/DFS 基础图 | 18 |
| DP 核心扩展 | 16 |
| 字符串高级算法 | 15 |
| 树 / BST / LCA | 15 |
| 哈希表 / map | 14 |
| 排序 | 13 |
| 堆 / TopK / Huffman | 10 |
| 栈 / 队列 / 单调栈 | 10 |
| 贪心 | 10 |
| 一维 DP | 9 |
| 二分 | 9 |
| 数学与位运算 | 7 |
| 最短路 / MST | 6 |
| 二维 DP | 5 |
| 图高级 | 5 |
| 并查集 | 5 |
| 区间结构 | 3 |
| Trie | 2 |
| 几何 / 扫描线 | 2 |
| 回溯 / 递归 | 2 |
| 链表与缓存 | 2 |
| 树形 DP | 1 |

以下字段在最终 200 题中均为 200/200 非空：

| 字段组 | 完整性 |
| --- | ---: |
| learning_objectives | 200/200 |
| interaction_tasks | 200/200 |
| common_misconceptions | 200/200 |
| hint_policy | 200/200 |
| stage2_visual_brief | 200/200 |
| real_world_context | 200/200 |
| oracle_type / oracle_risk | 200/200 |
| process_profile | 200/200 |

Held-out v1 使用 [heldout_cases_v1.json](../benchmark/heldout_cases_v1.json)，包含 40 题和 15 个算法族。BFS/DFS、DP 核心、一维 DP、二分、二维 DP、字符串、数组指针、最短路、栈队列、树各 3 题；区间结构、图高级、并查集、数学位运算、树形 DP 各 2 题。

### 11.2 输入、配对与独立性

- Full-200 的 AlgoTutorGen、Direct、WebGen-Agent、HTMLCure 和 BrowserRepair 都通过 case_id 对齐到相同 200 题。
- 主统计只对 sample index 0 做任务级配对，因此每题权重相同。
- 646 样例中的同题样例共享 solver、tracker 和任务定义，存在组内相关性。
- 三模型汇总中的 600 行是相同 200 题在三个模型上的重复观察，正式显著性检验按模型分别完成，不把 600 行当成独立样本。
- 传统系统只对 exact-overlap 任务报告，N/A 不记作失败。
- 自动评价若页面自身无法渲染，不删除样本；WebGen-Agent 的 1 个失败页按最低分计入 200 页分母。

### 11.3 主要生成协议

| 条件 | 模型 | 任务与输入 | 生成预算 | 并发 | 关键设置 |
| --- | --- | --- | --- | ---: | --- |
| AlgoTutorGen 主实验 | DeepSeek-V4-Pro | 200 题 sample 0 | solutions=2；max_candidates=2；max_rounds=2 | 8 | LLM max_tokens=32768；strict warnings；teaching enrichment；单题总 timeout=3000 s |
| Direct HTML 主实验 | DeepSeek-V4-Pro | 同一 200 题 sample 0 | solutions=1；max_candidates=1；max_rounds=2 | 8 | expected 对模型可见；要求完整教学页面；无浏览器反馈修复；单题 timeout=2400 s |
| 跨模型 AlgoTutorGen | Flash、GLM、Kimi | 同一 200 题 sample 0 | 统一起始预算 2 candidates × 2 rounds；仅对失败任务做最终质量重试，最多 3 × 3 | 16 | browser shards=16；外部资源阻断；最终表只报告补跑后的冻结页面 |
| Held-out AlgoTutorGen | DeepSeek-V4-Pro | 40 个新任务 sample 0 | 2 candidates × 2 rounds | 8 | LLM timeout=900 s；单题 timeout=2400 s |
| Held-out Direct | DeepSeek-V4-Pro | 同一 40 题 | 1 candidate；最多 2 rounds | 8 | expected 可见；无浏览器反馈 |
| WebGen-Agent | DeepSeek-V4-Pro | 200 题 sample 0 | max_iter=5 | 8 | feedback model=DeepSeek-V4-Pro；VLM=gemini-3-flash-preview |
| HTMLCure | Repair: DeepSeek-V4-Pro；Evaluator: Gemini | 冻结 Direct 200 页 | max_iterations=1；共生成 269 个 repair candidates | 8 shards | vision_in_repair=false；browser_use_agent=false |
| Direct-BrowserRepair | DeepSeek-V4-Pro | 独立 200 题运行 | 固定预算 1/2/3/5 calls；repair max_tokens=12000 | 按实验脚本分片 | 只向修复器暴露通用浏览器反馈；不暴露隐藏九项指标；每题目标 80k tokens |
| Stage2 | DeepSeek-V4-Pro | 200 个已验证 Stage1 artifact | 最终 247 次模型调用 | 并行分片运行 | 只增强展示层；47 次 creative-quality repair；不替代 Stage1 correctness |

### 11.4 浏览器与运行环境

| 项目 | 记录 |
| --- | --- |
| Python | /ssd1/liaokunpeng/agent-py310-cu/bin/python3 |
| 浏览器 | Playwright Chromium；跨模型冻结路径为 /ms-playwright/chromium-1223/chrome-linux64/chrome |
| 跨模型容器用户 | 1020:1021 |
| 主实验浏览器并发 | 8 |
| 跨模型浏览器分片 | 16 |
| Judge 并发 | completion 阶段每个 cell 为 8 |
| 外部资源 | strict 条件要求自包含；跨模型和 BrowserRepair 统一阻断外部请求 |
| LLM API | OpenAI-compatible；密钥只从环境或本地忽略配置读取，文档不保存明文 |
| 缓存 | Full-200 主报告记录为未使用缓存 |
| 截图失败处理 | 保留任务分母；无法渲染时按预先定义的最低分策略处理 |

### 11.5 九项浏览器审计的执行顺序

1. 打开最终 HTML，并收集 page error、console error 和主体内容。
2. 检查页面是否能进入可审计状态，得到 Load。
3. 从 HTML 或渲染页面抽取可见最终答案，与 expected 比较，得到 Answer。
4. 定位可见、可操作的 learner checkpoint，得到 Interaction。
5. 提交已知正确答案，观察反馈方向，得到 Correct FB。
6. 构造并提交错误答案，观察反馈方向，得到 Wrong FB。
7. 触发 Hint、Show answer，并确认页面出现预期内容或状态变化。
8. 触发提交后读取 learning log，确认日志非空且发生变化。
9. 比较教学操作前后受保护的答案或 canonical algorithm-state 摘要，得到 Mutation-free。
10. 九项均为 true 时，Machine OK 才为 true。

审计器对页面行为做自动检查，不对反馈文字的深层教学质量作最终判断。视觉、教学有效性和真人学习效果由其他实验或未来人工研究处理。

### 11.6 统计方法

主二元指标使用同一 case ID 的配对向量。对第 i 个任务，令 AlgoTutorGen 结果为 a_i，比较方法结果为 b_i，则通过率差值为：

Δ = (1/n) Σ(a_i - b_i)。

95% 配对 bootstrap 的实现细节：

- 固定随机种子：20260713。
- 重采样次数：10,000。
- 每次按任务对共同重采样，不拆开 a_i 与 b_i。
- 取 bootstrap 差值分布的 2.5% 和 97.5% 分位数。

Exact McNemar 只使用不一致对：A-only 与 B-only，在二者总数上执行双侧二项检验。多指标同时检验时使用 Holm 校正。

1—5 分的配对代理评分使用双侧 Wilcoxon signed-rank；效应量使用 matched-pairs rank-biserial：

r_rb = (正秩和 - 负秩和) / (正秩和 + 负秩和)。

Judge 稳健性同时报告 raw agreement、winner flip rate 和 Cohen kappa。类别极不平衡时，kappa 可能明显低于 raw agreement，因此两者必须一起读。

## 12. 详细数值与失败分析

### 12.1 Full-200 九项完整配对统计

| 指标 | AlgoTutorGen | Direct | 差值 | 95% bootstrap CI | McNemar p | Holm p |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Machine OK | 198/200 | 98/200 | +50.0 pp | [43.0,57.0] | 4.063e-29 | 4.063e-28 |
| Load | 200/200 | 188/200 | +6.0 pp | [3.0,9.5] | 0.0004883 | 0.0009766 |
| Answer | 200/200 | 200/200 | +0.0 pp | [0.0,0.0] | 1 | 1 |
| Interaction | 200/200 | 149/200 | +25.5 pp | [19.5,31.5] | 8.882e-16 | 3.553e-15 |
| Correct FB | 199/200 | 120/200 | +39.5 pp | [32.5,46.5] | 6.783e-23 | 6.105e-22 |
| Wrong FB | 198/200 | 125/200 | +36.5 pp | [29.5,43.0] | 4.023e-21 | 3.219e-20 |
| Hint | 200/200 | 132/200 | +34.0 pp | [27.5,40.5] | 6.776e-21 | 4.743e-20 |
| Show | 200/200 | 133/200 | +33.5 pp | [27.0,40.0] | 1.355e-20 | 8.132e-20 |
| Log | 200/200 | 135/200 | +32.5 pp | [26.0,39.0] | 5.421e-20 | 2.711e-19 |
| Mutation-free | 200/200 | 149/200 | +25.5 pp | [19.5,31.5] | 8.882e-16 | 3.553e-15 |

Answer 的差值为 0，而其余主要交互和反馈指标有明显差距。这是“答案正确不等于完整教学页面可靠”的直接统计证据。

### 12.2 分算法族的 Machine OK

| 算法族 | 任务数 | AlgoTutorGen | Direct | WebGen-Agent | HTMLCure strict | BrowserRepair-1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BFS/DFS 基础图 | 18 | 18/18 | 10/18 | 4/18 | 4/18 | 10/18 |
| DP 核心扩展 | 16 | 16/16 | 7/16 | 5/16 | 3/16 | 7/16 |
| Trie | 2 | 2/2 | 0/2 | 0/2 | 0/2 | 1/2 |
| 一维 DP | 9 | 9/9 | 4/9 | 1/9 | 3/9 | 4/9 |
| 二分 | 9 | 9/9 | 4/9 | 3/9 | 3/9 | 4/9 |
| 二维 DP | 5 | 5/5 | 3/5 | 3/5 | 2/5 | 3/5 |
| 几何 / 扫描线 | 2 | 2/2 | 2/2 | 0/2 | 1/2 | 2/2 |
| 区间结构 | 3 | 3/3 | 1/3 | 1/3 | 0/3 | 1/3 |
| 哈希表 / map | 14 | 14/14 | 6/14 | 3/14 | 1/14 | 6/14 |
| 回溯 / 递归 | 2 | 2/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| 图高级 | 5 | 5/5 | 3/5 | 1/5 | 2/5 | 4/5 |
| 堆 / TopK / Huffman | 10 | 10/10 | 7/10 | 2/10 | 3/10 | 7/10 |
| 字符串高级算法 | 15 | 14/15 | 4/15 | 7/15 | 0/15 | 5/15 |
| 并查集 | 5 | 5/5 | 4/5 | 0/5 | 0/5 | 4/5 |
| 排序 | 13 | 13/13 | 7/13 | 2/13 | 3/13 | 9/13 |
| 数学与位运算 | 7 | 7/7 | 4/7 | 0/7 | 0/7 | 4/7 |
| 数组指针 / 窗口 / 前缀 | 21 | 21/21 | 15/21 | 5/21 | 7/21 | 15/21 |
| 最短路 / MST | 6 | 6/6 | 3/6 | 0/6 | 0/6 | 5/6 |
| 栈 / 队列 / 单调栈 | 10 | 9/10 | 5/10 | 0/10 | 2/10 | 5/10 |
| 树 / BST / LCA | 15 | 15/15 | 4/15 | 5/15 | 2/15 | 4/15 |
| 树形 DP | 1 | 1/1 | 0/1 | 0/1 | 0/1 | 1/1 |
| 贪心 | 10 | 10/10 | 4/10 | 3/10 | 4/10 | 4/10 |
| 链表与缓存 | 2 | 2/2 | 1/2 | 0/2 | 0/2 | 1/2 |
| **总计** | **200** | **198/200** | **98/200** | **45/200** | **40/200** | **106/200** |

AlgoTutorGen 的两个失败分别落在字符串高级算法和栈/队列/单调栈；其余 21 个算法族在主冻结页面上均为全通过。

### 12.3 Family-core 与 expansion 分层

| Gate layer | 任务数 | AlgoTutorGen | Direct | WebGen-Agent | HTMLCure strict | BrowserRepair-1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| family_core | 62 | 62/62 | 19/62 | 11/62 | 6/62 | 23/62 |
| expansion | 138 | 136/138 | 79/138 | 34/138 | 34/138 | 83/138 |

这张表只表示两个数据层的结果分布。family_core 并不自动比 expansion 更难；二者任务构成不同。

### 12.4 九项失败组合

#### AlgoTutorGen

| 失败项组合 | 页面数 |
| --- | ---: |
| Wrong FB | 1 |
| Correct FB + Wrong FB | 1 |

#### Direct HTML

| 失败项组合 | 页面数 |
| --- | ---: |
| Interaction + Correct FB + Wrong FB + Hint + Show + Log + Mutation-free | 39 |
| Load + Interaction + Correct FB + Wrong FB + Hint + Show + Log + Mutation-free | 12 |
| Correct FB | 11 |
| Wrong FB | 9 |
| Correct FB + Wrong FB + Log | 8 |
| Hint + Show | 5 |
| Correct FB + Hint + Show | 4 |
| Correct FB + Wrong FB + Hint + Show + Log | 3 |
| Log | 3 |
| Wrong FB + Hint + Show | 2 |
| 其他六种低频组合 | 6 |

#### WebGen-Agent

| 失败项组合 | 页面数 |
| --- | ---: |
| Interaction + Correct FB + Wrong FB + Hint + Show + Log + Mutation-free | 34 |
| Correct FB + Wrong FB + Log | 27 |
| Correct FB + Wrong FB | 15 |
| Correct FB | 12 |
| Log | 8 |
| Wrong FB | 7 |
| Answer | 7 |
| Load + Answer + 其余七项 | 6 |
| Answer + Interaction + 其余六项 | 6 |
| Correct FB + Wrong FB + Hint | 5 |
| Answer + Correct FB | 4 |
| Correct FB + Log | 3 |
| 其他低频组合 | 21 |

#### HTMLCure strict

| 失败项组合 | 页面数 |
| --- | ---: |
| 九项全部失败 | 125 |
| Interaction + Correct FB + Wrong FB + Hint + Show + Log + Mutation-free | 13 |
| Wrong FB | 6 |
| Correct FB | 4 |
| Correct FB + Hint + Show | 4 |
| Wrong FB + Hint + Show | 2 |
| 其余六种单页组合 | 6 |

#### Direct-BrowserRepair 1-call

| 失败项组合 | 页面数 |
| --- | ---: |
| Interaction + Correct FB + Wrong FB + Hint + Show + Log + Mutation-free | 32 |
| Load + Interaction + Correct FB + Wrong FB + Hint + Show + Log + Mutation-free | 13 |
| Correct FB | 11 |
| Wrong FB | 9 |
| Correct FB + Wrong FB + Log | 5 |
| Hint + Show | 5 |
| Correct FB + Hint + Show | 4 |
| Log | 3 |
| Correct FB + Wrong FB + Hint + Show + Log | 3 |
| Wrong FB + Hint + Show | 2 |
| 其他低频组合 | 7 |

### 12.5 主实验和替代模型的具体失败页面

| 条件 | 生成失败 | 已生成页面中的 Machine OK 失败 |
| --- | --- | --- |
| 主 AlgoTutorGen | 无 | stack_valid_parentheses_full_core：Wrong FB；string_longest_common_prefix_full_core：Correct FB、Wrong FB |
| Flash 最终 | 无 | 无 |
| GLM 最终 | articulation_bridges、z_algorithm 未生成有效 artifact | first_unique_char_synthetic、trie_prefix_match_string 的 Correct FB 与 Wrong FB 失败 |
| Kimi 最终 | articulation_bridges、bst_insert_inorder_synthetic、mountain_peak_index_synthetic、stack_remove_adjacent_duplicates_full_core、stock_span_synthetic 未生成有效 artifact | group_anagrams_synthetic 的 Correct FB 与 Wrong FB 失败 |
| Held-out | heldout_bipartite_matching_size 未通过原始生成 gate | 同一任务缺少完整交互、反馈、提示、显示答案、日志和 Mutation-free |

缺失 artifact 在统一审计表中会表现为页面加载、答案和后续行为均失败；这类失败应与“页面已生成但反馈语义不完整”区分。

Direct HTML 的 12 个 Load 失败页面及浏览器错误如下：

| Case | 主要浏览器错误 |
| --- | --- |
| array_product_except_self_full_edge | JavaScript Unexpected token |
| dp_decode_ways_full_transfer | JavaScript Unexpected number |
| dp_max_subarray_full_core | 变量重复声明 |
| graph_connected_components | Invalid Unicode escape |
| permutations | 空 DOM 节点调用 querySelectorAll |
| sieve_primes | Invalid or unexpected token |
| stack_remove_adjacent_duplicates_full_edge | Unexpected string |
| stack_valid_parentheses_full_core | Unexpected token |
| trie_prefix | 空 DOM 节点绑定 addEventListener |
| trie_prefix_expansion | Unexpected identifier |
| trie_prefix_match_string | Unexpected identifier |
| two_sum | 空 DOM 节点写入 textContent |

WebGen-Agent 的 tarjan_scc 页面在审计时发生渲染超时，保守记为失败。HTMLCure 接受的 126 个改写中，125 个引入 Google Fonts，因此 strict 条件会把这些页面判为非自包含。

### 12.6 生成与评价成本明细

#### 主实验与 Stage2

| 阶段 | Calls | Tokens | Calls/task | Tokens/task | 说明 |
| --- | ---: | ---: | ---: | ---: | --- |
| Stage1 selected-final lineage | 1,066 | 15,369,433 | 5.33 | 76.8k | 最终选中 artifact 对应的生成链 |
| Stage1 all attempts | 1,151 | 16,870,557 | 5.76 | 84.4k | 包含未被最终采用的候选和失败尝试 |
| Direct HTML | 222 | 4,385,641 | 1.11 | 21.9k | 冻结 Direct 生成 |
| Stage2 final | 247 | 2,774,765 | 1.24 | 13.9k | 最终 200 个展示层页面 |
| Stage2 strict scene-salience VLM | 200 | 492,701 | 1.00 | 2.46k | 辅助压力审计 |
| 五方法教学/视觉统一评价 | 1,001 | 3,565,397 | 约 1.00/页 | 约 3.57k/页 | 999 页由 Gemini 评分，1 页按渲染失败最低分计入；另有 2 次格式重试 |
| Completion paired reviews | 1,202 | 4,177,949 | 约 1.00/对 | 约 3.48k/对 | 1,200 对，另有 2 次格式重试 |

#### 三个替代模型的最终质量运行

下表的 AlgoTutorGen 成本包括为得到最终冻结页面而实际执行的失败任务重试；Direct 是同模型冻结生成。它不是等 token 比较。

| 模型 | Algo calls | Algo tokens | Algo calls/task | Algo tokens/task | Direct calls | Direct tokens | Direct calls/task | Direct tokens/task |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4-Flash | 992 | 10,405,206 | 4.96 | 52.0k | 254 | 4,769,718 | 1.27 | 23.8k |
| GLM-5.2 | 1,799 | 23,857,273 | 9.00 | 119.3k | 231 | 4,683,119 | 1.16 | 23.4k |
| Kimi-K2.5 | 2,321 | 26,599,884 | 11.61 | 133.0k | 265 | 3,483,532 | 1.33 | 17.4k |

由于没有冻结各模型的统一价格，本文件不换算货币成本。不同模型 token 计数也不应直接解释为相同计算量。

### 12.7 Held-out 九项完整配对统计

| 指标 | AlgoTutorGen | Direct | 差值 | 95% bootstrap CI | McNemar p | Holm p |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Machine OK | 39/40 | 18/40 | +52.5 pp | [37.5,67.5] | 9.537e-7 | 9.537e-6 |
| Load | 40/40 | 36/40 | +10.0 pp | [2.5,20.0] | 0.125 | 0.25 |
| Answer | 40/40 | 40/40 | +0.0 pp | [0.0,0.0] | 1 | 1 |
| Interaction | 39/40 | 26/40 | +32.5 pp | [17.5,47.5] | 0.0002441 | 0.0009766 |
| Correct FB | 39/40 | 21/40 | +45.0 pp | [30.0,60.0] | 7.629e-6 | 6.866e-5 |
| Wrong FB | 39/40 | 22/40 | +42.5 pp | [27.5,57.5] | 1.526e-5 | 0.0001221 |
| Hint | 39/40 | 23/40 | +40.0 pp | [25.0,55.0] | 3.052e-5 | 0.0002136 |
| Show | 39/40 | 23/40 | +40.0 pp | [25.0,55.0] | 3.052e-5 | 0.0002136 |
| Log | 39/40 | 24/40 | +37.5 pp | [22.5,52.5] | 6.104e-5 | 0.0003052 |
| Mutation-free | 39/40 | 26/40 | +32.5 pp | [17.5,47.5] | 0.0002441 | 0.0009766 |

### 12.8 646 样例重放的逐族结果

| 算法族 | 通过/总数 | 通过率 |
| --- | ---: | ---: |
| 图高级 | 12/12 | 100.00% |
| 数组指针 / 窗口 / 前缀 | 62/63 | 98.41% |
| 回溯 / 递归 | 15/16 | 93.75% |
| BFS/DFS 基础图 | 60/61 | 98.36% |
| 二分 | 27/27 | 100.00% |
| 一维 DP | 27/27 | 100.00% |
| 二维 DP | 15/15 | 100.00% |
| DP 核心扩展 | 54/56 | 96.43% |
| 几何 / 扫描线 | 6/6 | 100.00% |
| 贪心 | 32/33 | 96.97% |
| 哈希表 / map | 44/44 | 100.00% |
| 堆 / TopK / Huffman | 34/36 | 94.44% |
| 链表与缓存 | 6/7 | 85.71% |
| 数学与位运算 | 21/21 | 100.00% |
| 栈 / 队列 / 单调栈 | 30/30 | 100.00% |
| 区间结构 | 6/6 | 100.00% |
| 最短路 / MST | 20/22 | 90.91% |
| 排序 | 39/39 | 100.00% |
| 字符串高级算法 | 43/45 | 95.56% |
| 树 / BST / LCA | 48/50 | 96.00% |
| 树形 DP | 1/4 | 25.00% |
| Trie | 10/12 | 83.33% |
| 并查集 | 14/14 | 100.00% |
| **总计** | **626/646** | **96.90%** |

按 gate layer：family_core 为 210/222（94.59%），expansion 为 416/424（98.11%）。sample index 0 为 200/200；额外输入为 426/446。

20 个失败输入如下：

| Case | Sample | 主要边界 |
| --- | ---: | --- |
| bellman_ford_shortest_path | 2 | 断连图中不可达节点表示导致 solve、trace、expected 不一致 |
| digit_dp_no_seven | 3 | n=0 边界结果不一致 |
| graph_topological_sort | 1 | 两个合法拓扑序被按列表顺序严格比较 |
| heap_last_stone_full_edge | 1 | 两块石头边界结果错误 |
| jump_game | 1 | 生成 trace 使用了不支持的 note 参数 |
| kmp | 2 | 空 pattern 导致 trace 索引越界 |
| lis_length_synthetic | 2 | 空数组上调用 max |
| merge_k_sorted_lists_synthetic | 1 | 引用了不存在的切片 target |
| permutations_expansion | 2 | 等价排列集合的输出顺序不同 |
| rabin_karp | 2 | pattern 长于 text 时索引越界 |
| reverse_linked_list | 2 | 空链表输入越界 |
| rotate_array_right_synthetic | 2 | 空数组上取模除零 |
| tree_level_order_synthetic | 1 | 空树 root=None 未处理 |
| tree_max_independent_set | 1 | 树节点 schema/ID 假设不一致 |
| tree_max_independent_set | 2 | 树节点 schema/ID 假设不一致 |
| tree_max_independent_set | 3 | 单节点树 schema/ID 假设不一致 |
| tree_path_sum_exists_full_core | 2 | 空树 root=None 未处理 |
| trie_prefix | 4 | 重复单词下 solve 与 trace 计数不一致 |
| trie_prefix_expansion | 1 | solve 与 trace 的前缀计数不一致 |
| zero_one_bfs_shortest_path | 2 | 不可达节点的额外 infinity 项与 expected 不一致 |

这些失败说明 sample-0 上通过的生成代码不保证对同题所有边界输入都稳健。部分失败是算法实现错误，部分是等价结果归一化或输入 schema 的问题。

### 12.9 长轨迹的分布与极端值

第 4.2 节报告均值；下表补充分位与极值。HTML、heap 使用十进制近似单位。

| Scale | Frames 中位数 [min,max] | HTML 中位数 [min,max] | Load 中位数 [min,max] | Step latency 中位数 [min,max] | Heap 中位数 [min,max] |
| --- | --- | --- | --- | --- | --- |
| Small | 80 [27,276] | 0.90 MB [0.43,5.10] | 98 ms [68,283] | 12.8 ms [9.5,24.9] | 5.4 MB [3.6,14.2] |
| Medium | 458.5 [43,2,013] | 9.29 MB [1.29,160.16] | 477 ms [115,18,527] | 35.3 ms [14.9,142.7] | 26.9 MB [6.1,373.4] |
| Large | 1,292 [58,5,533] | 50.00 MB [7.01,1,082.15] | 2,821 ms [368,51,406] | 94.4 ms [30.4,258.1] | 119.7 MB [22.0,658.2] |

Small、Medium 各 18/18 完成浏览器测量；Large 为 16/18。两个 Large 失败页：

| Case | Frames | HTML | 浏览器结果 |
| --- | ---: | ---: | --- |
| kmp | 3,063 | 581.09 MB | Page.goto 超过 60 秒 |
| string_sliding_window_unique | 5,533 | 1.082 GB | Page.goto 超过 60 秒 |

大页面使用完整帧快照，因此 HTML 体积近似随帧数和单帧状态共同增长。当前结果支持后续采用 delta encoding、按需加载和时间线虚拟化。

### 12.10 Direct-BrowserRepair 的完整预算记录

| Budget | Machine OK | Strict Machine OK | Self-contained | 平均 calls | 平均 tokens | token 中位数 | 超过 80k | 平均生成时间 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 106/200 | 106/200 | 200/200 | 1.000 | 19,677 | 19,789 | 0/200 | 207.2 s |
| 2 | 10/200 | 10/200 | 200/200 | 2.000 | 36,806 | 36,800 | 0/200 | 347.2 s |
| 3 | 15/200 | 15/200 | 200/200 | 3.000 | 53,717 | 53,661 | 0/200 | 477.6 s |
| 5 | 6/200 | 6/200 | 200/200 | 5.000 | 87,193 | 86,831 | 193/200 | 733.9 s |

四个预算是独立冻结条件。1-call 没有浏览器反馈，2-call 才包含一次反馈重写。增加调用后行为下降，说明当前通用反馈加整页重写容易破坏原有答案或交互；它不是对所有浏览器修复算法的普遍否定。

### 12.11 Full-200 消融的完整机器统计

| 消融 | Full | 消融 | Full−消融 | 95% bootstrap CI | McNemar p |
| --- | ---: | ---: | ---: | --- | ---: |
| No repair | 198/200 | 193/200 | +2.5 pp | [0.5,5.0] | 0.0625 |
| No teaching | 198/200 | 198/200 | 0.0 pp | [0.0,0.0] | 1.0 |
| No interaction | 198/200 | 0/200 | +99.0 pp | [97.5,100.0] | 4.98e-60 |
| No teaching + interaction | 198/200 | 0/200 | +99.0 pp | [97.5,100.0] | 4.98e-60 |
| No SceneGraph compiler | 198/200 | 0/200 | +99.0 pp | [97.5,100.0] | 4.98e-60 |

No teaching 与 Full 的 Machine OK 相同，是因为九项行为合同不评价讲解文本质量；教学质量差异由下面的匿名 judge 表体现。

### 12.12 教学消融的七维完整结果

| 消融 | 维度 | Full 均值 | 消融均值 | 均值差 | Holm p | Rank-biserial |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| no_teaching | 内容质量 | 5.000 | 1.855 | +3.145 | 6.71e-35 | 1.000 |
| no_teaching | 目标对齐 | 4.995 | 1.825 | +3.170 | 6.71e-35 | 1.000 |
| no_teaching | 反馈适应 | 4.965 | 2.330 | +2.635 | 1.54e-34 | 1.000 |
| no_teaching | 交互易用 | 4.855 | 3.165 | +1.690 | 1.50e-32 | 1.000 |
| no_teaching | 展示设计 | 4.920 | 1.770 | +3.150 | 6.85e-35 | 1.000 |
| no_teaching | 教学有效性 | 5.000 | 1.715 | +3.285 | 4.95e-35 | 1.000 |
| no_teaching | 易用性 | 4.850 | 2.740 | +2.110 | 1.57e-33 | 1.000 |
| no_interaction | 内容质量 | 4.980 | 1.575 | +3.405 | 1.81e-35 | 1.000 |
| no_interaction | 目标对齐 | 4.995 | 1.450 | +3.545 | 5.52e-36 | 1.000 |
| no_interaction | 反馈适应 | 4.995 | 1.000 | +3.995 | 7.18e-44 | 1.000 |
| no_interaction | 交互易用 | 4.990 | 1.010 | +3.980 | 2.55e-43 | 1.000 |
| no_interaction | 展示设计 | 4.950 | 1.350 | +3.600 | 4.09e-36 | 1.000 |
| no_interaction | 教学有效性 | 4.995 | 1.085 | +3.910 | 5.89e-41 | 1.000 |
| no_interaction | 易用性 | 4.980 | 1.100 | +3.880 | 3.96e-40 | 1.000 |
| no_teaching_interaction | 内容质量 | 5.000 | 1.520 | +3.480 | 1.08e-35 | 1.000 |
| no_teaching_interaction | 目标对齐 | 5.000 | 1.400 | +3.600 | 4.09e-36 | 1.000 |
| no_teaching_interaction | 反馈适应 | 4.990 | 1.000 | +3.990 | 1.05e-43 | 1.000 |
| no_teaching_interaction | 交互易用 | 5.000 | 1.005 | +3.995 | 7.18e-44 | 1.000 |
| no_teaching_interaction | 展示设计 | 4.970 | 1.350 | +3.620 | 4.09e-36 | 1.000 |
| no_teaching_interaction | 教学有效性 | 5.000 | 1.040 | +3.960 | 1.41e-42 | 1.000 |
| no_teaching_interaction | 易用性 | 5.000 | 1.060 | +3.940 | 6.80e-42 | 1.000 |

所有 rank-biserial 都为 1.0，表示所有非零配对差异都朝向 Full；但这些仍是 LLM judge 的代理结果，不是学生学习增益。

### 12.13 尚未完成的真人部分

| 项目 | 已准备材料 | 当前状态 | 不能报告的结果 |
| --- | --- | --- | --- |
| Machine evaluator calibration | 30 tasks × 4 methods = 120 个盲化页面；两份 annotator 表 | 等待两名人工标注者 | precision、recall、F1、FPR、FNR、人工 kappa |
| Independent trace audit | 40 tasks，覆盖 23 families；两份 reviewer 表 | 等待两名人工 reviewer | critical semantic error rate、逐族人工正确率 |
| Expert review | 3 位专家 × 30 对 | 协议与页面已准备，尚无参与者 | 专家偏好、质量均值、一致性 |
| Student study | 24 名学生 × 12 trials | 协议、量表和分析脚本已准备，尚无参与者 | 学习增益、SUS、认知负荷、保持与迁移 |

协议文件为 [31_HUMAN_EXPERT_REVIEW_PROTOCOL.md](./31_HUMAN_EXPERT_REVIEW_PROTOCOL.md) 和 [32_STUDENT_USER_STUDY_PROTOCOL.md](./32_STUDENT_USER_STUDY_PROTOCOL.md)。在真实标注和参与者数据到位前，只能描述“协议已准备”，不能填写正面结果。

## 13. 理论实验的详细对应关系

完整公式与推导单独见 [18_THEORY_AND_DIRECTED_EXPERIMENTS.md](./18_THEORY_AND_DIRECTED_EXPERIMENTS.md)。本节记录实验怎样对应理论中的可检查前提。

| 理论对象 | 可执行检查 | 实验规模 | 结果 | 结论边界 |
| --- | --- | ---: | --- | --- |
| 理想局部恢复成本 | Local Resume 与 Global Restart 在相同 50 题、相同模型、最多 3 次 policy decision 下比较 | 2 模型 × 2 策略 × 50 | Local 未取得显著成功率优势 | 当前实现重做 materialization 和 teaching，不满足完整 checkpoint 前提 |
| Trace→Scene→Runtime 组合保持 | 对每一帧提取 canonical algorithm state 并逐层比较 | 294 artifacts；55,108 frames | 55,108/55,108 一致 | 不独立证明 source trace 算法正确 |
| 确定性 | 20 个 artifact 各重新编译、渲染 10 次 | 200 次重复 | 每个 artifact 只有一个 render/projection hash | 只覆盖冻结环境 |
| 教学非干扰 | Overlay 变换、非法字段、跨模型 overlay、随机浏览器动作 | 372 variants；369 scenes；1,561,298 actions | 未观察到 state pollution | 有限反例搜索，不是形式证明 |
| 合同辨别力 | 语义破坏应拒绝，语义保持变化应接受 | 2,198 bad；392 good | 2,198/2,198 reject；392/392 accept | 只覆盖定义的 mutation suite |
| 约束乘法存活 | 从答案到加载、交互、反馈、教学和非干扰逐层计算条件率 | 11 个方法/条件 | 自由 HTML 在交互和反馈层持续下降 | 概率链式法则是恒等式；实验贡献是定位下降边界 |

## 14. 证据与复现索引

### 14.1 主要机器报告

| 内容 | 最终报告 |
| --- | --- |
| 主 Stage1 生成 | [llm_benchmark_report.json](../output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json) |
| 主 Direct 生成 | [llm_benchmark_report.json](../output/experiments/algotutorgen_full_200_20260706/direct_html_expected_visible/llm_benchmark_report.json) |
| 主九项浏览器审计 | [interaction_semantic_eval_report.json](../output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine/interaction_semantic_eval_report.json) |
| 主配对统计 | [paired_statistics.json](../output/experiments/algotutorgen_completion_20260713/statistics/paired_statistics.json) |
| 跨模型汇总 | [multimodel_summary.json](../output/experiments/algotutorgen_multimodel_full200_20260713/multimodel_summary.json) |
| Held-out | [heldout_40](../output/experiments/algotutorgen_plan_completion_20260713/heldout_40) |
| BrowserRepair | [direct_browser_repair_5](../output/experiments/algotutorgen_plan_completion_20260713/direct_browser_repair_5) |
| WebGen-Agent | [report.json](../output/external_baselines/webgen/audit_all200_sample0/report.json) |
| HTMLCure | [htmlcure_full200_analysis.json](../output/external_baselines/htmlcure_all200_sample0/htmlcure_full200_analysis.json) |
| Cross-input replay | [cross_input_replay_report.json](../output/experiments/algotutorgen_completion_20260713/cross_input_replay/cross_input_replay_report.json) |
| Long trace | [long_trace_scalability_report.json](../output/experiments/algotutorgen_plan_completion_20260713/long_trace_scalability/long_trace_scalability_report.json) |
| Full-200 ablation | [statistics](../output/experiments/algotutorgen_completion_20260713/statistics) |
| Non-degenerate ablation | [nondegenerate_ablations](../output/experiments/algotutorgen_plan_completion_20260713/nondegenerate_ablations) |
| Final fault injection | [gate_fault_injection_report.json](../output/experiments/algotutorgen_plan_completion_20260713/validator_fault_rerun/gate_fault_injection_report.json) |
| Theory-aligned experiments | [theory_aligned_20260714](../output/experiments/theory_aligned_20260714) |
| Five-method auxiliary evaluation | [all_method_auxiliary_eval_report.json](../output/experiments/all_method_auxiliary_eval_20260718/all_method_auxiliary_eval_report.json) |
| Traditional overlap | [overlap_study_summary.json](../output/external_baselines/traditional_systems/overlap_study_summary.json) |
| Prompt appendix | [20_ALGOTUTORGEN_PROMPT_APPENDIX.md](./20_ALGOTUTORGEN_PROMPT_APPENDIX.md) |

### 14.2 主要执行与分析脚本

| 任务 | 脚本 |
| --- | --- |
| Stage1 / Direct 生成 | [run_llm_benchmark.py](../scripts/run_llm_benchmark.py) |
| 九项浏览器审计 | [run_interaction_semantic_eval.py](../scripts/run_interaction_semantic_eval.py) |
| 审计分片合并 | [merge_interaction_semantic_reports.py](../scripts/merge_interaction_semantic_reports.py) |
| 配对统计 | [analyze_paired_experiments.py](../scripts/analyze_paired_experiments.py) |
| 跨模型生成 | [run_cross_model_generation_experiment.py](../scripts/run_cross_model_generation_experiment.py) |
| 同题换输入 | [run_cross_input_replay.py](../scripts/run_cross_input_replay.py) |
| 长轨迹 | [run_long_trace_scalability.py](../scripts/run_long_trace_scalability.py) |
| BrowserRepair | [run_direct_browser_repair_baseline.py](../scripts/run_direct_browser_repair_baseline.py) |
| 浏览器反馈构造 | [build_browser_repair_feedback.py](../scripts/build_browser_repair_feedback.py) |
| HTMLCure | [run_htmlcure_baseline.py](../scripts/run_htmlcure_baseline.py) |
| WebGen-Agent 审计 | [audit_webgen_agent_baseline.py](../scripts/audit_webgen_agent_baseline.py) |
| Fault injection | [run_gate_fault_injection.py](../scripts/run_gate_fault_injection.py) |
| 语义保持 | [run_semantic_preservation_audit.py](../scripts/run_semantic_preservation_audit.py) |
| Noninterference | [run_noninterference_stress.py](../scripts/run_noninterference_stress.py) |
| Nested contract | [analyze_nested_contract_survival.py](../scripts/analyze_nested_contract_survival.py) |
| 五方法辅助评价 | [run_all_method_auxiliary_eval.py](../scripts/run_all_method_auxiliary_eval.py) |
| Judge 稳健性 | [analyze_judge_robustness.py](../scripts/analyze_judge_robustness.py) |
| 人工研究分析 | [analyze_human_study.py](../scripts/analyze_human_study.py) |

### 14.3 最小复现入口

确定性质量检查：

    /ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py

查看各实验脚本参数：

    /ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py --help
    /ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_interaction_semantic_eval.py --help
    /ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/analyze_paired_experiments.py --help

更完整的历史复现包说明见 [reproducibility/README.md](../output/experiments/algotutorgen_tables/reproducibility/README.md)。其中部分目录保留早期实验入口；复现论文最终数字时，应按第 10.2 节的来源优先级选择最终报告。

## 15. 最终状态清单

| 项目 | 状态 |
| --- | --- |
| Full-200 主生成与九项行为审计 | 完成 |
| Direct、WebGen-Agent、HTMLCure、BrowserRepair | 完成 |
| 三个替代生成模型最终结果 | 完成 |
| Held-out 40 | 完成 |
| 646 样例重放 | 完成 |
| 长轨迹 54 | 完成 |
| 功能、教学、非退化表示消融 | 完成 |
| Final fault injection | 完成 |
| 理论定向实验 | 完成 |
| 五方法教学与视觉代理评价 | 完成 |
| Judge 顺序和跨模型稳健性 | 完成 |
| Machine evaluator 人工校准 | 材料完成，标注待进行 |
| Independent trace 人工审计 | 材料完成，标注待进行 |
| 专家评审 | 协议完成，参与者待招募 |
| 学生实验 | 协议完成，参与者待招募 |

详细版最终支持的主结论与第 9 节一致：AlgoTutorGen 的优势主要来自可执行轨迹、确定性表示链和受隔离教学交互共同提供的完整行为可靠性，而不是只把最终答案写对。代价是更多模型调用和 token；长轨迹仍存在明显体积与加载瓶颈；自动代理评价不能替代真人学习效果实验。

