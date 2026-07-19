# AlgoTutorGen 实验结果总览

- **主实验：** 200 个任务、23 个算法族，每题使用 sample index 0 形成配对观察
- **完整稳健性集合：** 同一 200 个任务的 646 个具体样例
- **整理日期：** 2026-07-18

> 本文只汇总已经冻结的最终实验结果，不展示过程性结果。重要结果前置在第 0 节；第 1 节解释指标；第 6 节集中报告理论定向实验。

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
