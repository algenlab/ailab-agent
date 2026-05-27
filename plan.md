你现在最需要的不是继续加功能，而是准备一套**项目说明书体系**。目标有两个：

1. **你自己能看懂：这个系统到底是什么、现在做到哪、以后往哪走。**
2. **AI 能看懂：不要自由发挥，知道该按什么边界写代码。**

我建议不要搞一堆散乱文档，先准备 **8 个核心文档**。

---

## 先定一个文档原则

用一个简单框架：
**人看的文档负责解释为什么，AI看的文档负责规定怎么做。**

技术文档常见会分成 tutorial、how-to、reference、explanation 四类，这是 Diátaxis 文档框架的核心思想：不同读者需求要用不同类型文档承载，不能混在一个大文档里。([diataxis.fr][1])

你的项目现在已经有 `SYSTEM_OVERVIEW.md`，里面记录了系统目标、输入输出、主流程、SemanticTrace、Tracer API、SceneGraph、校验门禁、Benchmark 等内容，这个可以作为现有系统总说明继续保留。

但它还不够，因为它偏“当前系统说明”，不够告诉 AI：

> 最终产品到底要做成什么样。
> 哪些能改，哪些不能改。
> 下一步怎么实现。
> 完成标准是什么。

---

# 你需要准备的 8 个文档

## 1. `00_PRODUCT_NORTH_STAR.md`

这是最重要的文档。

它回答：

> 我们到底要做什么产品？

建议写死一句话：

```text
AlgoLab 的目标是自动生成 VisuAlgo-style 的高质量交互式算法可视化页面。
输入算法题描述、样例输入和可选解法提示，系统自动生成可执行、可验证、可交互、可教学的单文件中文 HTML 页面。
```

这个文档只写产品，不写代码。

内容结构：

```text
1. 产品一句话定义
2. 对标对象：VisuAlgo，不是 Python Tutor，不是普通代码播放器
3. 目标用户：算法学习者、教师、算法题解作者
4. 核心体验：
   - 输入题目
   - 自动生成解法
   - 自动生成逐步动画
   - 支持修改输入
   - 支持预测下一步
   - 支持查看为什么
5. 非目标：
   - 不是任意代码调试器
   - 不是自由 HTML 生成器
   - 不是每个算法手写页面
6. V1 范围：
   - DP
   - 图搜索
   - 数组指针
   - 栈/队列
   - 哈希表
   - 树/堆/并查集
```

这个文档是给你自己和 AI 定方向的。以后 AI 写代码前必须先读它。

---

## 2. `01_FINAL_PAGE_SPEC.md`

这个文档描述最终页面应该长什么样。

你现在很多混乱来自“界面没定义清楚”。所以必须把页面拆成固定模块。

建议定义成：

```text
最终页面 = 顶部任务区 + 左侧输入区 + 中间可视化区 + 右侧讲解区 + 底部时间线 + Debug Drawer
```

每个区域写清楚：

```text
顶部任务区：
- 题目名称
- 输入
- 输出
- 可信度状态

左侧输入区：
- 题目描述
- JSON 输入编辑器
- 解法选择
- 重新生成按钮

中间可视化区：
- 主数据结构
- 当前操作高亮
- 依赖箭头
- before / after 状态

右侧讲解区：
- 当前阶段
- 当前步骤说明
- 为什么这样做
- 不变量
- 校验证据

底部时间线：
- 初始化
- 主循环
- 状态转移
- 返回答案
```

你之前的产品文档里已经提到最终页面要从“轨迹播放器 + 校验面板”升级成“帮助人理解算法的交互式算法实验室”，并且页面要包含任务与可信度、题目输入、主可视化、教学解释、语义时间线等模块。

这个文档要变成 AI 的 UI 施工图。

---

## 3. `02_SYSTEM_ARCHITECTURE.md`

这是给你自己看懂系统的。

你现在系统已经有主链路：

```text
ProblemInput
→ LLM 生成 solve / trace / verify
→ sandbox 执行
→ SemanticTrace
→ validators
→ SceneGraph
→ renderer
→ HTML
```

现有 `SYSTEM_OVERVIEW.md` 里已经描述了入口、pipeline、LLM generator、executor、sandbox、Tracer、validators、scene compiler、release gate、renderer/export 的调用顺序。

但建议单独抽一个更短的架构图文档，专门让你快速看懂。

结构可以按 arc42 思路写。arc42 架构模板强调要记录 introduction/goals、constraints、building blocks、runtime view、quality requirements 等内容。([arc42][2])

建议目录：

```text
1. 系统总图
2. 核心模块职责
3. 数据流
4. 运行时流程
5. 失败修复流程
6. 正确性门禁
7. 渲染边界
8. 质量目标
9. 当前限制
```

重点是每个模块只说三件事：

```text
输入是什么
输出是什么
不能做什么
```

---

## 4. `03_AI_CODING_GUIDE.md`

这是专门给 AI 写代码看的。

非常重要。

你现在用 AI 写代码，最大问题是 AI 会自由发挥。所以要给它一份硬规则。

内容建议：

```text
AI 开发规则：

1. 每次修改前必须阅读：
   - 00_PRODUCT_NORTH_STAR.md
   - 02_SYSTEM_ARCHITECTURE.md
   - 03_AI_CODING_GUIDE.md
   - 当前任务相关 spec

2. 不允许自由改架构。
3. 不允许让 LLM 直接生成 HTML。
4. Renderer 只能消费 SceneGraph。
5. tracker_code 必须优先使用 Tracer API。
6. 新算法优先复用已有视觉原语。
7. 每次改动必须增加或更新测试。
8. 每次任务必须跑相关测试。
9. 不能跨多个 Phase 一次性大改。
10. 修改完成必须写明：
    - 改了什么
    - 为什么改
    - 跑了哪些测试
    - 还有什么风险
```

你现在的系统核心原则已经是：LLM 只生成算法语义候选，不生成 HTML/CSS/JS；系统执行和校验 LLM 输出；Renderer 只消费 SceneGraph；新增算法优先复用通用视觉形态和固定语义 op。
这些都应该写进 AI Coding Guide。

---

## 5. `04_TRACE_AND_SCHEMA_CONTRACT.md`

这是系统最核心的“接口合同”。

它要告诉 AI：

> 生成的 trace 到底必须长什么样。

内容包括：

```text
1. SemanticTrace schema
2. event op 集合
3. target id 规范
4. deps 规范
5. state 规范
6. Tracer API 用法
7. 禁止写法
8. 正确示例
9. 错误示例
10. 校验失败如何 repair
```

你当前系统已经要求 `trace(input_data)` 返回 `semantic-trace-v1`，必须显式包含当前输入，事件字段必须使用 `op` 和 `targets`，旧式 `type/target`、旧式 map target 都不再接受。

这个文档以后就是 AI 生成 tracker 的“宪法”。

---

## 6. `05_VISUAL_PRIMITIVES_AND_PATTERNS.md`

这个文档定义“自动版 VisuAlgo”里有哪些视觉原语。

例如：

```text
array
matrix
graph
stack
queue
map
tree
heap
trie
union-find
recursion tree
string
geometry
```

每个视觉原语要写：

```text
适用算法
输入 state 格式
target id 格式
默认布局
支持的高亮方式
支持的交互
典型页面效果
```

例如 matrix：

```text
视觉原语：matrix / DP table

适用：
- Unique Paths
- LCS
- Edit Distance
- Knapsack

状态格式：
state["dp"] = [[...], [...], ...]

target:
dp[i][j]

默认交互：
- 高亮当前格
- 高亮依赖格
- 展示转移公式
- 支持预测下一格
```

你现在 `SYSTEM_OVERVIEW.md` 已经列了支持的视觉形态，比如 array + pointer、matrix / DP table、graph、stack / queue、map、tree、heap、trie、union-find、recursion_tree、string、geometry、ML primitives。

这个文档要把它们从“列表”升级成“设计规范”。

---

## 7. `06_EVALUATION_AND_BENCHMARK.md`

这个文档回答：

> 怎么证明系统真的好？

内容建议：

```text
1. Benchmark 范围
2. 算法族划分
3. 每个算法族有哪些题
4. 每个题需要哪些样例输入
5. 指标定义
6. baseline
7. 人工评价 rubric
8. 失败类型分类
```

指标可以写：

```text
最终答案正确率
trace schema 通过率
过程转移正确率
关键步骤覆盖率
SceneGraph 可渲染率
HTML 可运行率
交互完整性
页面教学质量评分
```

你当前系统已有确定性 benchmark、LLM benchmark、dashboard 和质量检查脚本，用于验证 pipeline、validator、compiler、renderer 稳定性。

这个文档要服务论文，也要服务 AI 回归测试。

---

## 8. `07_ROADMAP_AND_TASKS.md`

这是给 AI 执行任务用的。

格式必须非常具体，不能写“优化界面”这种空话。

应该写成：

```text
Phase 1：产品目标冻结
- [ ] 完成最终页面 spec
- [ ] 完成视觉原语规范
- [ ] 完成 5 个黄金样例

Phase 2：DP 页面打磨
- [ ] matrix 支持依赖箭头
- [ ] DP 当前步骤显示公式
- [ ] 右侧解释区显示不变量
- [ ] 增加预测下一步
- [ ] 增加 unique paths benchmark

Phase 3：Graph 页面打磨
...
```

每个任务都要有：

```text
目标
涉及文件
验收标准
必须运行的测试
禁止事项
```

AI 最需要这种文档。

---

# 还需要一个小文档：`ADR/`

建议加一个目录：

```text
docs/adr/
  0001-use-semantic-trace.md
  0002-renderer-only-consumes-scenegraph.md
  0003-use-tracer-api.md
  0004-focus-on-visualgo-style-classic-algorithms.md
```

ADR 是 Architecture Decision Record，用来记录重要架构决策、背景和后果；ADR 的常见定义就是记录一个重要架构决策，以及它的上下文和影响。([GitHub][3])

每个 ADR 不要长，写：

```text
# ADR-0003: 使用 Tracer API

## Context
LLM 手写 events 容易跳帧、格式错、coverage 不可控。

## Decision
所有新 tracker 优先使用 Tracer API。

## Consequences
好处：
- trace schema 稳定
- coverage 可统计
- sampled mode 可控

代价：
- prompt 更复杂
- 旧 tracker 需要兼容一段时间
```

这个对 AI 特别有用，因为 AI 经常不知道“为什么以前这么设计”。

---

# 推荐最终目录结构

```text
docs/
  00_PRODUCT_NORTH_STAR.md
  01_FINAL_PAGE_SPEC.md
  02_SYSTEM_ARCHITECTURE.md
  03_AI_CODING_GUIDE.md
  04_TRACE_AND_SCHEMA_CONTRACT.md
  05_VISUAL_PRIMITIVES_AND_PATTERNS.md
  06_EVALUATION_AND_BENCHMARK.md
  07_ROADMAP_AND_TASKS.md

  adr/
    0001-use-semantic-trace.md
    0002-renderer-only-consumes-scenegraph.md
    0003-use-tracer-api.md
    0004-focus-on-visualgo-style-classic-algorithms.md

  examples/
    unique_paths.md
    bfs.md
    binary_search.md
    monotonic_stack.md
```

---

# 现在先别写太多，先写这 4 个

优先级最高的是：

```text
1. 00_PRODUCT_NORTH_STAR.md
2. 01_FINAL_PAGE_SPEC.md
3. 03_AI_CODING_GUIDE.md
4. 07_ROADMAP_AND_TASKS.md
```

因为你现在最大的问题不是系统没有文档，而是：

```text
产品目标不够稳定
AI 施工边界不够清楚
任务拆分不够可执行
```

先把这 4 个写好，AI 写代码就不会乱跑。

---

# 给 AI 的启动提示词也要固定

以后每次让 AI 写代码，开头都应该这样：

```text
你是 AlgoLab 项目的长期实施工程师。

每轮开始必须先阅读：
- docs/00_PRODUCT_NORTH_STAR.md
- docs/01_FINAL_PAGE_SPEC.md
- docs/02_SYSTEM_ARCHITECTURE.md
- docs/03_AI_CODING_GUIDE.md
- docs/07_ROADMAP_AND_TASKS.md
- 当前任务相关源码和测试

本轮只能完成 docs/07_ROADMAP_AND_TASKS.md 中最靠前的一个未完成小任务。
不能跨 Phase。
不能自由改架构。
不能让 LLM 直接生成 HTML。
Renderer 只能消费 SceneGraph。
修改后必须增加或更新测试，并运行相关测试。
最后汇报：修改文件、测试结果、风险和下一步。
```

---

一句话总结：

> **你现在要准备的不是一个“大说明文档”，而是一套“产品北极星 + 页面规格 + 系统架构 + AI施工规则 + schema合同 + 视觉原语 + benchmark + roadmap”。**

这样你能看懂系统，AI 也知道要设计什么系统。

[1]: https://diataxis.fr/?utm_source=chatgpt.com "Diátaxis"
[2]: https://arc42.org/overview?utm_source=chatgpt.com "arc42 Template Overview"
[3]: https://github.com/architecture-decision-record/architecture-decision-record?utm_source=chatgpt.com "Architecture decision record (ADR)"
