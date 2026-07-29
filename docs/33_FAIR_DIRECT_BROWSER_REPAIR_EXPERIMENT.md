# 公平 Direct-BrowserRepair Repair-Budget 实验

## 1. 实验目的

本实验回答的问题是：在固定同一批初始 Direct 页面后，增加“最多可用的浏览器反馈修复次数”是否能提高最终页面的 Machine OK，通过页面是否会因额外重写而丢失，以及实际需要多少模型调用、token 和时间。

这里的 `repair budget = r` 表示：初始页面之外，最多允许调用模型修复 (r) 次。它不是“强制执行恰好 (r) 次”，也不是总调用次数。最大预算 5 因而最多产生 1 个冻结初始页和 5 个修复页。

## 2. 公平协议

全部 200 个任务使用同一份冻结 Direct 初始页面。逐文件 SHA-256 核对结果为 200/200 一致，没有重新生成初始页。

每题按以下策略执行：

1. 用真实 Playwright 浏览器对当前页面执行完整九项 Machine OK 审计。
2. 如果九项全部通过，立即停止，不再调用修复模型。
3. 如果未通过，另开页面收集通用浏览器反馈，包括加载错误、控制台错误、DOM 摘要、可见控件和点击后的可见状态变化。
4. 将完整上一版 HTML 与浏览器反馈交给模型，生成完整的新单文件 HTML；不再截取 HTML 尾部。
5. 审计新页面并记录逐项 fail→pass、pass→fail 转移。
6. 始终保存历史最优页面：优先选择九项通过数更多的版本；分数相同则保留更早版本。
7. 最多执行 5 次修复。达到上限仍未通过时，发布 best-so-far 页面，而不是最后一次重写页面。

Machine OK 的九项为：页面加载、答案正确、交互可达、正确反馈、错误反馈、提示、显示答案、学习日志、教学操作不改算法状态。九项必须同时为真。

为了避免针对隐藏测试直接优化，模型只看到通用浏览器观察，不看到 `machine_ok`、`correct_feedback_ok`、`wrong_feedback_ok` 等九项审计字段。200 题的 417 个修复 prompt 均通过检查，没有隐藏指标字段泄漏。

## 3. 运行配置

| 配置项 | 设置 |
| --- | --- |
| 任务数 | 200 |
| 模型 | DeepSeek-V4-Pro |
| 最大 repair budget | 5 次修复；最多 6 个页面版本 |
| 任务并发 | 32 |
| 浏览器 worker | 8 |
| 单次最大输出 | 32,768 tokens |
| API 超时 | 1,800 s |
| 浏览器超时 | 120 s |
| 可恢复 API 重试 | 最多 5 次 |
| 外部资源 | 浏览器中阻断 |
| 上一版页面输入 | 完整 HTML，417/417 次均完整包含 |
| 基础设施失败 | 0/200 |

完整运行墙钟时间为 3,714 s，即约 61.9 分钟。单次修复输出最大为 30,820 tokens，417 次修复中没有一次达到 32,000 tokens，因此没有证据表明结果受 32,768-token 输出上限截断。

## 4. 主要结果

| Repair budget | Machine OK | 通过率 | 相对初始新增通过 | 实际修复调用总数 | 平均实际修复次数/题 | 新增 repair tokens/题 | 新增生成时间/题 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 106/200 | 53.0% | 0 | 0 | 0.000 | 0 | 0.0 s |
| 1 | 118/200 | 59.0% | +12 | 94 | 0.470 | 16,405 | 94.1 s |
| 2 | 119/200 | 59.5% | +13 | 176 | 0.880 | 31,379 | 177.1 s |
| 3 | 120/200 | 60.0% | +14 | 257 | 1.285 | 46,650 | 259.1 s |
| 5 | 120/200 | 60.0% | +14 | 417 | 2.085 | 78,237 | 424.8 s |

表中的 token 和时间只计算新增 repair 调用，不重复计算已经冻结的初始页面生成成本。平均值以全部 200 题为分母；106 个首轮通过任务的 repair 成本为 0。

成功曲线为 106→118→119→120→120，随 repair budget 单调不降。相对 budget 0，budget 1、2、3/5 分别增加 12、13、14 个通过任务；对应配对 exact McNemar 双侧 (p) 值分别为 0.000488、0.000244、0.000122。由于 budget 之间是嵌套的自适应策略，这些检验表示相同任务上的累计净改善，不应解释为彼此独立的实验样本。

各预算通过率的 Wilson 95% 区间为：budget 0 `[46.09%, 59.80%]`，budget 1 `[52.08%, 65.58%]`，budget 2 `[52.58%, 66.06%]`，budget 3/5 `[53.08%, 66.54%]`。

## 5. 九项完整结果

| Repair budget | Load | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free | Machine OK |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 186/200 | 200/200 | 155/200 | 128/200 | 133/200 | 137/200 | 138/200 | 143/200 | 155/200 | 106/200 |
| 1 | 200/200 | 200/200 | 165/200 | 139/200 | 144/200 | 151/200 | 151/200 | 157/200 | 165/200 | 118/200 |
| 2 | 200/200 | 200/200 | 166/200 | 140/200 | 145/200 | 152/200 | 153/200 | 158/200 | 166/200 | 119/200 |
| 3 | 200/200 | 200/200 | 166/200 | 140/200 | 146/200 | 152/200 | 153/200 | 158/200 | 166/200 | 120/200 |
| 5 | 200/200 | 200/200 | 166/200 | 140/200 | 146/200 | 152/200 | 153/200 | 158/200 | 166/200 | 120/200 |

一次修复首先消除了全部 14 个加载失败，并改善了交互、反馈、提示、显示答案和学习日志。后续预算的增益较小：第 2 次修复新增 1 个 Machine OK，第 3 次再新增 1 个；第 4、5 次没有新增完整通过页面。

## 6. 转移与 best-so-far

| 修复轮次 | 实际调用数 | fail→pass | fail→fail | 整体 pass→fail |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 94 | 12 | 82 | 0 |
| 2 | 82 | 1 | 81 | 0 |
| 3 | 81 | 1 | 80 | 0 |
| 4 | 80 | 0 | 80 | 0 |
| 5 | 80 | 0 | 80 | 0 |
| 合计 | 417 | 14 | 403 | 0 |

整体 pass→fail 为 0，是 early-stop 的直接结果：页面一旦 Machine OK，就不会再被整体重写。未通过页面的单项指标仍可能退化；417 次转移中，九项通过数增加 27 次、不变 385 次、下降 5 次。best-so-far 保证这些局部退化不会覆盖更好的历史页面。

按最终 best-so-far 页面统计，120 题九项全部通过，26 题只失败一项，54 题失败至少两项。80 个未通过页面中，34 个页面的共同问题是交互不可达，连带正确/错误反馈、提示、显示答案、学习日志和 mutation-free 七项同时失败；其余主要是单独的正确反馈或错误反馈问题。

## 7. 成本

417 次 repair 调用共使用 15,647,489 tokens，其中输入 6,998,333、输出 8,649,156。平均每次 repair 为 37,524 tokens，平均输出 20,741 tokens，95 分位输出 25,282 tokens，最大输出 30,820 tokens。

94 个首轮未通过、实际进入 repair 的任务平均使用 166,463 repair tokens，中位数 183,844，最大 238,241。全部 200 题平均使用 78,237 repair tokens；中位数为 0，因为超过一半任务首轮通过并立即停止。

## 8. 结论与表述边界

公平的 adaptive repair-budget 实验表明，浏览器反馈整页修复能把 Machine OK 从 106/200 提高到 120/200，即增加 7.0 个百分点。主要收益集中在第一次修复；第 2、3 次各救回 1 题，第 4、5 次没有进一步增加完整通过数，却显著增加 token 和时间。

因此可以写成：

> Starting from the same frozen Direct pages, an early-stopping, best-so-far browser-repair policy improved Machine OK from 106/200 to 120/200. Most gains occurred after the first repair, while budgets beyond three repairs added cost without further complete successes.

该结果支持“浏览器修复有有限但真实的增益，并呈明显边际收益递减”。它不能证明所有 browser-repair 方法最多只能达到 60%，也不能把第 4、5 次没有新增通过外推到不同模型、不同反馈器或局部编辑式修复。

## 9. 结果文件

- 汇总 JSON：[`fair_repair_report.json`](../output/experiments/direct_browser_repair_fair_20260723/fair_repair_report.json)
- 简表：[`fair_repair_report.md`](../output/experiments/direct_browser_repair_fair_20260723/fair_repair_report.md)
- 冻结初始页清单：[`frozen_initial_manifest.csv`](../output/experiments/direct_browser_repair_fair_20260723/frozen_initial_manifest.csv)
- 逐任务转移：[`per_task_transitions.csv`](../output/experiments/direct_browser_repair_fair_20260723/per_task_transitions.csv)
- 各预算页面与机器审计：[`direct_browser_repair_fair_20260723`](../output/experiments/direct_browser_repair_fair_20260723)
- 运行脚本：[`run_direct_browser_repair_fair.py`](../scripts/run_direct_browser_repair_fair.py)
