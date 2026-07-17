# 实验结果方法对比重构设计

## 目标

重构 `docs/EXPERIMENT_RESULTS.md`，使读者能够先看清参与比较的方法，再在统一指标下横向核对数据。文档仍保留理论审计、泛化、成本和限制，但不再按实验执行时间线堆叠结果。

## 主比较方法

主结果固定比较以下五种完整方法或修复条件：

1. AlgoTutorGen：本文方法，使用可执行规格、SemanticTrace、验证门禁、SceneGraph 和固定 Runtime。
2. Direct HTML：单次自由生成完整 HTML/CSS/JavaScript。
3. WebGen-Agent：外部网页生成 agent baseline。
4. Direct + HTMLCure：对 Direct HTML 进行 HTMLCure 修复；主表使用 strict self-contained 口径。
5. Direct + BrowserRepair：基于浏览器反馈重写 Direct HTML；主表使用最佳固定预算 1-call first-call control，并明确真正反馈重写从 call 2 开始。

Direct-to-SceneGraph、VerifiedTrace-to-LLM-HTML、no-repair、no-interaction 等属于消融，不与上述完整方法混排。

## 文档结构

1. `如何阅读这份结果`：给出 benchmark、统一审计协议和 Machine OK 定义。
2. `比较了哪些方法`：用方法说明表交代输入、生成方式、反馈/修复、Runtime 和 self-contained 边界。
3. `主结果总览`：
   - 基础可靠性表：Load、Answer、Interaction、Machine OK。
   - 教学行为表：Correct/Wrong Feedback、Hint、Show Answer、Log、Mutation-free。
   - 数值统一使用 `count/200 (percentage)`。
4. `结果怎么解释`：按方法概括主要失分位置，不重复逐项抄表。
5. `修复与成本`：比较调用数、token、时间以及 BrowserRepair 固定预算曲线；HTMLCure blocked 仅作敏感性分析。
6. `泛化与稳健性`：跨输入、跨模型和 held-out。
7. `为什么完整链有效`：nested survival、非退化消融、语义保持、mutation 和 noninterference。
8. `教学与视觉辅助指标`：Naps、TRAKLA2、LORI/MERLOT、Stage2 VLM，并明确不是 correctness 或学习增益。
9. `限制与证据索引`：集中列出 claim boundary 和原始报告路径。

## 数据口径

- 主方法比较统一使用 200 个任务的 sample index 0。
- AlgoTutorGen 主行使用 selected-final 结果，并明确 primary 为 195/200、五题来自记录在案的 targeted retry。
- HTMLCure 主行使用 strict self-contained 结果；blocked-external 91/200 只作为敏感性分析。
- BrowserRepair 主行使用固定预算 1-call first-call control，不从多预算中逐题选择最优结果，也不把它相对主 Direct 行的数值差解释为 repair gain。
- 没有完全相同审计字段的方法不得用空值伪装为可比结果；必须从冻结报告重新汇总或明确标注不可用。
- Machine OK 始终定义为九项浏览器行为的合取，不把教学文本质量、视觉审美或真人学习效果混入其中。
- 一个核心数字只在主表完整出现一次，后文用引用和解释代替重复表格。

## 验证

- 从冻结 JSON 报告重新核对五种方法的九项机器指标。
- 与 `latex/evidence-ledger.md` 中已冻结数字交叉检查。
- 检查所有证据路径存在。
- 运行 Markdown 表格/标题结构检查、`git diff --check` 和现存回归测试。

## 非目标

- 不改实验产物或重新运行昂贵 LLM/VLM/浏览器实验。
- 不把传统人工编写的 Python Tutor、VisuAlgo 等系统强行加入 200 题端到端主表。
- 不修改论文主稿数字，除非发现冻结证据之间存在明确冲突。
