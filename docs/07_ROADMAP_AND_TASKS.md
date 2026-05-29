# AlgoLab 最终产品设计与实施方案

本文档是 AlgoLab 的主实施蓝图。它不是短期任务清单，而是从当前科研原型走向最终产品形态的完整设计方案。

当前 Phase 0 到 Phase 9 已经形成可运行的 V1 基线：deterministic benchmark、release gate、SceneGraph 编译、Debug Drawer 和浏览器 smoke 均可作为不可退化证据。后续开发不应继续把“某一道题跑通”当作主要目标，而应把任务单位提升为“经典算法族能力”：同一套 trace 合同、过程校验、语义演示规则和视觉原语要能覆盖一族题。

使用方式：

- 人看它：理解最终产品长什么样、为什么这样拆阶段、现在该先做什么。
- AI 看它：知道每轮只能推进哪个明确任务，不能自由发挥、不能跨层乱改。
- 执行 AI 看它：先判断当前要增强哪个算法族能力，再按该族的 benchmark、trace contract、validator、demo readiness 和回归测试顺序推进。

每轮开发前必须先读：

- `docs/00_PRODUCT_NORTH_STAR.md`
- `docs/01_FINAL_PAGE_SPEC.md`
- `docs/02_SYSTEM_ARCHITECTURE.md`
- `docs/03_AI_CODING_GUIDE.md`
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`
- `docs/05_VISUAL_PRIMITIVES_AND_PATTERNS.md`
- 本文档

从 V1.1 开始，每轮开发还必须先读：

- `docs/06_EVALUATION_AND_BENCHMARK.md` 的 benchmark 分层和算法族能力矩阵。
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md` 的算法族 trace 合同。

## 1. 最终产品定义

AlgoLab 最终产品是：

> 一个面向经典算法题的可验证交互式算法实验室。用户输入题目描述、样例输入和可选解法提示，系统生成可执行、可验证、可交互、可教学、可复现的中文单文件算法可视化页面。

最终页面不是轨迹播放器，也不是调试面板，而是一个教学实验环境：

- 学生能看懂每一步为什么发生。
- 教师能拿页面讲解算法过程。
- 题解作者能把文字题解变成交互式教学页面。
- 研究人员能复现实验、比较 baseline、统计失败类型。

## 2. 产品成功标准

一个算法页面只有同时满足以下条件，才算达到最终产品目标：

- 可执行：`solve(input_data)`、`trace(input_data)`、`verify(input_data)` 都能在沙箱中执行。
- 可验证：答案一致，trace schema 合法，过程校验通过，scene 校验通过，release gate 通过。
- 可视化正确：SceneGraph 对象、marks、arrows、state 和语义对象能一一对应。
- 可教学：每个关键步骤显示当前操作、为什么、公式、不变量、涉及对象和校验证据。
- 可交互：支持播放、跳转、输入修改、解法对比、预测下一步、依赖点击、代码同步。
- 可复现：输入、模型配置、raw LLM 输出、repair 过程、artifact、HTML、截图和失败分类可保存。

从算法族正确性角度看，后续优先级固定为：

| 优先级 | 目标 | 解释 | 发布含义 |
|---|---|---|---|
| P0 | 答案正确 | `solve(input_data)`、`trace.result`、`verify(input_data)` 一致，且样例 expected 通过 | 不通过则不能生成正式产物 |
| P1 | 过程正确 | 状态转移、访问顺序、依赖对象、数据结构不变量和覆盖率通过族级校验 | 不通过则不能标记为强支持 |
| P2 | 演示正确 | trace 足够讲清算法，不跳关键步骤，不把对象绑定错，不给出反算法解释 | 不通过则只能作为工程调试产物 |
| P3 | 可视化可运行 | SceneGraph、HTML、播放、步进和 Debug Drawer 正常 | 不通过则不能进入 dashboard |
| P4 | 视觉质量 | 布局、美观、动画、交互 polish 和教学页面观感 | 后置增强，不阻塞算法族正确性建设 |

下一阶段的核心目标是 P0 到 P2。视觉效果可以继续稳定降级，但算法正确性、过程正确性和演示语义正确性不能降级。

## 3. 最终页面设计

最终页面采用“四区一线一抽屉”：

```text
顶部任务与可信度区
左侧题目与输入区 + 中间主可视化区 + 右侧教学解释区
底部语义时间线
Debug Drawer
```

### 3.1 顶部任务与可信度区

目标：

- 第一眼说明题目、输入、输出、解法和可信度。

必须显示：

- 题目名称。
- 当前输入摘要。
- 当前输出。
- 当前解法名称、复杂度。
- 可信度徽章。

可信度徽章使用人话：

```text
代码执行通过
轨迹覆盖完整
过程转移通过校验
可视化对象绑定正确
```

禁止：

- 主界面只显示 `artifact_ready PASS`、`trace_ready PASS` 这类工程字段。
- 让前端重新计算答案作为可信度来源。

### 3.2 左侧题目与输入区

目标：

- 让用户知道系统正在解决什么题、用什么输入、有什么解法。

必须显示：

- 题目描述。
- JSON 输入编辑器或只读输入视图。
- expected output，如果用户提供。
- 解法选择列表。
- 重新生成按钮。

最终交互：

- 修改输入后重新生成 trace。
- 切换多个解法 variant。
- 对比两个解法。
- 查看当前输入对应的 expected / verifier 结果。

约束：

- 输入修改必须回到 `ProblemInput -> BuildArtifact -> HTML` 主链路。
- 不允许前端临时改 trace 伪装成新生成结果。

### 3.3 中间主可视化区

目标：

- 展示当前步骤最重要的数据结构、依赖关系和状态变化。

必须显示：

- 主数据结构。
- 当前操作对象。
- 依赖对象。
- before / after。
- 依赖箭头或连接关系。
- 当前值变化。

DP 示例：

```text
dp[2][3] = dp[1][3] + dp[2][2]
         = 4 + 6
         = 10
```

图搜索示例：

```text
从 A 出队
检查边 A -> B
B 首次访问，dist[B] = dist[A] + 1
B 入队
```

二分示例：

```text
区间 [left, right] = [0, 5]
mid = 2
nums[mid] < target
下一步 left = mid + 1
```

### 3.4 右侧教学解释区

目标：

- 把当前步骤讲清楚，把系统校验翻译成学习者能理解的证据。

每帧尽量包含：

- 当前阶段。
- 当前操作。
- 为什么这样做。
- 涉及对象。
- 状态变化。
- 公式。
- 不变量。
- 对应代码行。
- 本步校验证据。
- 常见错误或提示。

主讲解必须优先展示教学解释；raw validation report 放 Debug Drawer。

### 3.5 底部语义时间线

目标：

- 用户能看出算法阶段，而不是只看到第几帧。

时间线阶段示例：

- DP：初始化、边界条件、主循环、状态转移、返回答案。
- BFS：起点入队、弹出队首、检查邻居、首次访问、结束。
- 二分：初始化区间、比较中点、收缩区间、返回结果。
- 回溯：进入递归、做选择、记录答案、撤销选择。

最低能力：

- 跳转任意帧。
- 显示阶段名称。
- 区分关键帧和普通帧。
- 支持播放、暂停、上一步、下一步。

### 3.6 Debug Drawer

目标：

- 保留工程证据，但不干扰学习体验。

包含：

- raw validation report。
- release gate 详情。
- trace schema 结果。
- process validator 结果。
- scene validator 结果。
- raw state JSON。
- artifact JSON 下载入口。
- HTML / screenshot / benchmark 链接。

默认折叠。

## 4. 系统设计

最终产品仍使用当前主链路：

```text
ProblemInput
  -> LLM 生成 solve / trace / verify
  -> sandbox 执行
  -> SemanticTrace
  -> validators
  -> SceneGraph
  -> renderer
  -> HTML + artifact JSON
```

### 4.1 不可破坏的边界

- LLM 不直接生成 HTML/CSS/JS。
- Renderer 只消费 SceneGraph 和 BuildArtifact。
- Renderer 不理解具体算法题。
- 新 tracker 优先使用 Tracer API。
- 新算法优先复用固定 SemanticOp 和视觉原语。
- 不恢复旧 trace 字段兼容。
- 不恢复旧式 map target。
- 不通过放宽 validator 发布错误产物。

### 4.2 核心模块责任

`algolab/generation/`

- 生成 `solve`、`trace`、`verify`。
- 生成多解法 variant。
- 根据错误信息 repair。
- 不生成页面。

`algolab/runtime/`

- 沙箱执行生成代码。
- 注入 Tracer。
- 检查 solve / trace / verify 一致性。
- 不自动修复旧格式 trace。

`algolab/verification/`

- 检查 schema、target、process、scene、release gate。
- 分类失败类型。
- 不渲染页面。

`algolab/compiler/`

- 解析 target。
- 把 SemanticTrace 编译成 SceneGraph。
- 生成可渲染对象、marks、arrows、teaching、evidence。

`algolab/renderer/`

- 把 BuildArtifact 和 SceneGraph 渲染为单文件中文 HTML。
- 展示教学解释、视觉对象、时间线、交互和 Debug Drawer。
- 不执行算法，不修复算法错误。

`tests/`

- 覆盖 schema、trace、process、scene、renderer、browser smoke、benchmark。

`scripts/`

- 构建 dashboard、evaluation manifest、evaluation report、benchmark report。

## 5. 数据合同设计

### 5.1 SemanticTrace

`trace(input_data)` 必须返回 `semantic-trace-v1`：

- `schema_version`
- `algorithm`
- `input_data`
- `result`
- `pseudocode`
- `events`

事件必须使用：

- `op`
- `targets`
- `deps`
- `state`
- `reason`
- `code_line`
- 可选 `teaching`
- 可选 `interaction`

禁止：

- `type`
- `target`
- 缺失 `input_data`
- `seen:2`
- `dist:A`
- `map:seen`

### 5.2 SceneGraph

SceneGraph 是 renderer 的唯一输入。

最终 SceneFrame 应支持：

- `objects`
- `marks`
- `state`
- `interaction`
- `teaching`
- `evidence`
- `code_line`
- `operation`
- `title`
- `description`

### 5.3 TeachingStep

教学字段目标：

- `what`：当前做什么。
- `why`：为什么这样做。
- `formula`：当前公式。
- `invariant`：当前不变量。
- `common_mistake`：常见错误。
- `hint`：学习提示。

缺失时 renderer 必须稳定降级，但黄金样例和 benchmark 应逐步要求关键帧提供这些字段。

### 5.4 Interaction

交互字段目标：

- `choice`：选择题预测下一步。
- `input`：填写下一个值。
- `judge`：判断当前步骤是否合法。
- `wrong_explanation`：可选，错误反馈解释，必须来自当前 trace / teaching 证据。
- `option_explanations`：可选，按选项给出解释，renderer 只读取该字段，不按算法名编造错误原因。

交互只读 trace，不修改 trace。

## 6. 视觉原语设计

当前稳定原语：

- array / pointer
- matrix / DP table
- graph
- stack / queue / deque
- map / hash table
- tree
- heap
- trie
- union-find
- recursion_tree
- string
- geometry

当前可组合但还不是独立稳定 layout：

- linked list
- range structure
- math / bit

扩展原则：

- 能映射到稳定原语时，不新增 target 前缀。
- 新 target 前缀必须同步改 parser、validator、compiler、renderer 和测试。
- `range:`、`number:`、`interval:`、`flow:` 当前不能直接写入 trace。
- 网络流容量用 `cap[A->B]`、`flow[A->B]` 或 `edge:A->B` + state map 表达。
- 区间结构用 `segment_tree` nodes/edges、`bit[i]`、`st[i][j]` 表达。

## 7. 算法覆盖设计

### 7.1 覆盖原则

后续覆盖扩展必须按算法族推进，而不是按题目硬编码推进。

| 概念 | 正确用途 | 禁止用法 |
|---|---|---|
| 算法族 | 建设可复用能力，例如 DP、图搜索、字符串、树、区间结构 | 把算法族只当成 dashboard 分类标签 |
| 代表题 | 检查算法族能力是否覆盖核心模式 | 为代表题写一次性 validator 或 renderer 特判 |
| benchmark case | 回归样本和泛化压力测试 | 让系统记住 case，或只为 case 放宽规则 |
| trace contract | 约束 LLM/fixture 如何表达过程 | 用自然语言解释替代结构化 state/deps |
| process validator | 证明过程不变量和覆盖率 | 只检查最终答案后宣称过程正确 |
| demo readiness | 证明演示不会误导学习者 | 用视觉好看掩盖过程跳步或依赖错误 |

新增算法题时先回答：

1. 它属于哪个算法族和子模式。
2. 能否用现有视觉原语表达。
3. 需要补哪个族级 trace 字段、state 字段或 deps 规则。
4. 是否已有 process validator 可以复用。
5. 如果不能强校验，是否明确标记为 `process_fallback` 或 `process_uncovered`。

只有当多个题目暴露同一个缺口时，才新增族级能力。不得为了单题绕过 schema、target、process 或 SceneGraph 约束。

### 7.2 第一阶段横向验收样例

第一阶段目标是把核心页面、通用编译层、教学解释、过程校验和交互能力打磨到可演示、可测、可复现。

这些样例用于横向验收系统能力，不表示路线图要先做某个算法族专页：

- 不同路径：验收 matrix、依赖连接、公式、不变量。
- BFS 最短层数：验收 graph + queue + map、首次访问证据。
- 二分查找：验收 array + pointer、区间收缩、预测交互。
- 每日温度：验收 array + stack、pop 原因、答案写入。
- Two Sum：验收 array + map、哈希命中依赖。
- KMP：验收 string + array、失配回退。
- LCA：验收 tree + recursion_tree、递归返回值。
- 省份数量：验收 matrix / union-find、连通性过程。
- 全排列：验收 recursion_tree、选择和撤销。
- 凸包：验收 geometry、叉积和 hull 更新。

第一阶段 benchmark：80 到 120 个题目样例。扩展 benchmark 时先保证这些样例能覆盖通用能力矩阵，再增加同族变体。

### 7.3 完整 V1 覆盖

完整 V1 逐步扩展到 200 到 300 个经典样例。

覆盖族：

- 数组基础与前缀结构。
- 数组指针。
- 排序与选择。
- 栈、队列、双端队列。
- 哈希表与集合。
- 链表。
- 字符串。
- 动态规划。
- 贪心。
- 图遍历。
- 图最短路。
- 图连通性。
- 最小生成树。
- 网络流与匹配入门。
- 树与二叉树。
- 堆与优先队列。
- Trie 与自动机入门。
- 并查集。
- 回溯与搜索树。
- 递归与分治。
- 位运算。
- 数学与数论。
- 计算几何。
- 区间与高级数据结构。
- 缓存与设计类经典题。

### 7.4 算法族能力等级

每个算法族必须用同一套等级描述当前支持强度：

| 等级 | 含义 | 最低证据 |
|---|---|---|
| strong | 有族级 process invariant、覆盖规则、代表 benchmark、正反例测试和可运行演示 | family core cases 必须通过 |
| medium+ | 生成和可视化稳定，部分子模式有强校验，复杂变体仍可能 fallback | core 子模式通过，扩展子模式可分阶段 |
| medium | 有 benchmark 和视觉表达，答案一致性可靠，但过程校验主要覆盖结构或部分规则 | 不得宣传为强过程正确 |
| basic | 可用 schema、answer、scene gate 和通用视觉原语表达，但没有族级不变量 | 必须在报告中显示 fallback/uncovered |
| planned | 文档规划中，尚未形成稳定实现 | 不能进入 release gate 强能力统计 |

能力等级按算法族统计，不按单题宣传。一个族如果只有一两个题通过，最多只能说明“代表题可运行”，不能直接升级为 strong。

### 7.5 V1.1 算法族能力矩阵

当前 V1 基线已经证明主链路可行。V1.1 到 V1.4 的目标是把下表逐步做实。

| 算法族 | 目标支持强度 | 核心子模式 | 代表 case 目标 | 强校验重点 | 演示正确性重点 |
|---|---|---|---:|---|---|
| 数组基础与前缀结构 | strong | 前缀和、差分、二维前缀、原地标记、前缀积 | 12-20 | 前缀递推、区间还原、边界下标、输入不变性 | 显示区间来源和增量含义 |
| 数组指针与窗口 | strong | 二分、二分答案、双指针、滑动窗口、快慢指针 | 18-30 | 窗口边界、mid 计算、指针单调移动、终止条件 | 每次移动必须说明比较或约束变化 |
| 排序与选择 | medium+ | 插入、归并、快速排序分区、快速选择、计数排序 | 15-25 | 比较/交换/移动合法性、分区不变量、有序前缀 | 不跳过关键交换和分区边界 |
| 栈队列与单调结构 | strong | 单调栈、单调队列、括号匹配、表达式基础 | 14-24 | 栈/队列状态连续、单调性、答案写入依赖 | push/pop 原因和弹出贡献可见 |
| 哈希表与集合 | medium+ | Two Sum、频次计数、前缀和计数、去重、窗口计数 | 12-22 | map 写入顺序、命中前后关系、计数变化 | 命中 complement 或计数条件必须可解释 |
| 链表与缓存 | medium | 反转链表、快慢指针、合并链表、LRU/LFU 基础 | 10-18 | next/prev 指针变化、环检测、cache map/list 一致 | 指针重连不能只给最终状态 |
| 字符串算法 | strong | KMP、Rabin-Karp、Z、Manacher、滑动窗口字符串 | 18-30 | prefix/z/radius/hash 表复核、失配回退、窗口哈希 | 对齐、回退和中心扩展原因清楚 |
| 动态规划 | strong | 一维、二维、背包、区间、树形、状态压缩、数位 DP 入门 | 35-60 | 初始化、转移依赖、遍历顺序、答案位置、覆盖率 | 公式代入、deps、边界条件和不变量可见 |
| 贪心 | medium+ | 区间调度、跳跃游戏、分发糖果、Huffman、合并区间 | 15-25 | 排序依据、局部选择合法性、堆/区间状态 | 必须说明为什么当前选择不会破坏最优性 |
| 图遍历与连通性 | strong | BFS、DFS、拓扑、二分图染色、连通分量、环检测 | 22-36 | visited/dist/color/indegree 状态、队列/栈顺序 | 首次访问、回边、入度变化要逐步解释 |
| 最短路与 MST | medium+ | Dijkstra、Bellman-Ford、Floyd、0-1 BFS、Kruskal、Prim | 18-30 | relax 合法性、dist 单调性、parent、union-find | 每次松弛或选边原因可见 |
| 图高级与网络流 | medium+ | Tarjan SCC、割点桥、二分图匹配、Edmonds-Karp | 12-20 | dfn/low、stack、match、capacity/flow 守恒 | 增广路径和 lowlink 更新不能跳步 |
| 树与二叉树 | strong | 遍历、BST、LCA、树直径、树形 DP、层序 | 18-30 | 递归返回、祖先关系、子树聚合、访问顺序 | 调用栈和返回值必须可讲解 |
| 堆与优先队列 | medium+ | TopK、堆排序基础、双堆中位数、Dijkstra PQ | 10-18 | heap property、push/pop、堆顶含义 | 堆顶选择和调整过程清楚 |
| Trie 与自动机 | medium+ | Trie 插入/查询、前缀计数、Aho-Corasick 入门 | 8-16 | 节点路径、计数、fail 指针基础一致性 | 当前字符沿哪条边走必须明确 |
| 并查集 | strong | 连通分量、路径压缩、按秩合并、Kruskal | 10-18 | parent forest、find path、union 后分量变化 | 合并原因和根变化可见 |
| 回溯与递归搜索 | medium+ | 全排列、组合、N 皇后、子集、数独入门 | 12-22 | 选择/撤销、used/path 连续性、剪枝条件 | 递归树、候选、回退不能缺关键帧 |
| 位运算与数论 | medium+ | GCD、快速幂、筛法、组合数、bitmask、lowbit | 14-24 | 余数、平方表、筛标记、mask 枚举、lowbit 分解 | 每一步数值变化和公式含义清楚 |
| 计算几何与扫描线 | medium | 凸包、方向判断、线段相交、扫描线事件 | 8-16 | cross/orientation、栈式 hull、事件排序 | 删除/保留点的几何原因可见 |
| 区间与高级数据结构 | medium+ | 线段树、树状数组、稀疏表、区间查询/更新 | 12-22 | query/update 路径、区间合并、lowbit、st 递推 | 覆盖区间和合并来源必须清楚 |

总目标样例数：V1.1 先扩到 160 到 220 个 deterministic samples；V1.2 到 V1.3 扩到 250 到 350 个 samples；V1.4 再引入 LLM benchmark 的算法族通过率统计。数量是覆盖压力，不是硬编码目标。

## 8. 评估设计

### 8.1 自动指标

- 最终答案正确率。
- solve / trace 一致率。
- verifier 一致率。
- trace schema 通过率。
- process invariant 通过率。
- 关键步骤覆盖率。
- SceneGraph 可渲染率。
- HTML 可运行率。
- JS error 数量。
- 交互完整性。

### 8.2 教学指标

- 当前步骤解释完整度。
- 公式可见率。
- 依赖对象可见率。
- 不变量展示率。
- 预测交互可用率。
- 页面教学质量人工评分。

### 8.3 Baseline

- LLM 直接生成 HTML。
- LLM 生成 trace，但无 process validator。
- LLM 生成 trace，但无 SceneGraph compiler。
- 完整 AlgoLab。

### 8.4 Ablation

- 无 SemanticTrace。
- 无 Tracer API。
- 无 process invariant。
- 无 repair loop。
- 无 SceneGraph compiler。
- 完整系统。

## 9. 实施原则

AI 每轮只能完成最靠前的一个未完成任务。

任务必须包含：

- 目标。
- 涉及文件。
- 验收标准。
- 必须运行的测试。
- 禁止事项。

执行规则：

- 不跨 Phase 大改。
- 不把多个独立系统塞进一轮。
- 每个代码任务必须有测试。
- 修改 renderer 时至少跑 offline regression；涉及浏览器交互时跑 browser smoke。
- 修改 validator 时必须包含正例和反例。
- 修改 target 语法时必须同步 parser、validator、compiler、renderer 和测试。
- 运行 Python 文件必须使用 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3`。

## Phase 0：文档和实施边界冻结

目标：

- 确保后续实施有统一产品目标、架构边界、trace 合同、视觉原语和任务入口。

### P0.1 核心文档体系

状态：已完成。

涉及文件：

- `docs/00_PRODUCT_NORTH_STAR.md`
- `docs/01_FINAL_PAGE_SPEC.md`
- `docs/02_SYSTEM_ARCHITECTURE.md`
- `docs/03_AI_CODING_GUIDE.md`
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`
- `docs/05_VISUAL_PRIMITIVES_AND_PATTERNS.md`
- `docs/06_EVALUATION_AND_BENCHMARK.md`
- `docs/07_ROADMAP_AND_TASKS.md`

验收标准：

- 产品目标清楚。
- 页面规格清楚。
- 架构边界清楚。
- AI 编码规则清楚。
- trace 合同清楚。
- 视觉原语覆盖新增经典算法族。

验证命令：

```bash
find docs -maxdepth 2 -type f | sort
```

### P0.2 ADR 和黄金样例

状态：已完成。

涉及文件：

- `docs/adr/0001-use-semantic-trace.md`
- `docs/adr/0002-renderer-only-consumes-scenegraph.md`
- `docs/adr/0003-use-tracer-api.md`
- `docs/adr/0004-focus-on-visualgo-style-classic-algorithms.md`
- `docs/examples/unique_paths.md`
- `docs/examples/bfs.md`
- `docs/examples/binary_search.md`
- `docs/examples/monotonic_stack.md`

验收标准：

- ADR 解释关键架构决策。
- 黄金样例能指导 renderer、validator、benchmark 改造。

验证命令：

```bash
find docs/adr docs/examples -maxdepth 1 -type f | sort
```

## Phase 1：教学页面骨架升级

目标：

- 把现有页面从“轨迹播放器 + 校验面板”升级成“交互式算法实验室”的基本形态。

### P1.1 重组页面信息架构

状态：已完成。

目标：

- 将页面组织为顶部可信度、左侧输入与解法、中间主可视化、右侧教学解释、底部语义时间线、Debug Drawer。

涉及文件：

- `algolab/renderer/panels.py`
- `algolab/renderer/export.py`
- `tests/browser_smoke.py`
- `tests/offline_regression.py`

验收标准：

- 主界面优先展示教学解释和主可视化。
- raw validation report 进入 Debug Drawer 或折叠区域。
- 顶部 badge 使用人话描述可信度。
- 旧的播放、上一步、下一步、range 控件继续可用。
- 页面在桌面和窄屏下不出现明显遮挡。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不修改算法结果。
- 不让 renderer 重新执行算法。
- 不把 Debug 信息作为主教学内容。

### P1.2 语义时间线

状态：已完成。

目标：

- 建立底部语义时间线 UI，使页面具备阶段名称、关键帧标记和稳定降级能力。
- 本任务先做通用时间线容器和现有字段读取；跨算法阶段生成策略在 P3.3 完成。

涉及文件：

- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/export.py`
- `tests/offline_regression.py`
- `tests/browser_smoke.py`

验收标准：

- 底部时间线能显示阶段名称或关键帧说明。
- 无阶段信息时稳定降级为帧编号和操作名。
- 时间线点击、range 跳转、播放控制使用同一个当前帧索引。
- 页面不依赖具体题名来生成阶段文案。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不按具体题名硬编码阶段。
- 不破坏现有 range 跳转。

### P1.3 Debug Drawer

状态：已完成。

目标：

- 将 raw validation、state、artifact、release gate 放入可折叠 Debug Drawer。

涉及文件：

- `algolab/renderer/panels.py`
- `algolab/renderer/export.py`
- `tests/browser_smoke.py`

验收标准：

- Debug Drawer 默认折叠。
- 能展开查看 raw validation report、state、release gate。
- 主页面不依赖 Debug Drawer 才能理解当前步骤。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不删除工程证据。
- 不把 raw JSON 直接塞到主讲解区。

## Phase 2：通用可视化编译层

目标：

- 建立跨算法族复用的 `SemanticTrace -> SceneGraph -> Renderer` 表达能力。
- DP、BFS、二分、单调栈等只作为验收样例，不作为专用产品路线。

### P2.1 SceneFrame 教学载荷贯通

状态：已完成。

目标：

- 让 `operation`、`title`、`description`、`teaching`、`evidence`、`interaction`、`code_line` 从 SemanticTrace 稳定进入 SceneFrame。

涉及文件：

- `algolab/schemas/scene_graph.py`
- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/export.py`
- `tests/offline_regression.py`

验收标准：

- SceneFrame 能保存当前操作、教学解释、校验证据和代码行。
- renderer 能在缺失字段时稳定降级。
- 至少覆盖 matrix、graph、array、stack、map 五类样例。
- 不把任何算法名写成 renderer 分支条件。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
```

禁止事项：

- 不让 renderer 从 `algorithm` 字符串猜教学内容。
- 不为不同路径、BFS、二分等单题写专用 UI 字段。

### P2.2 通用依赖关系和连接渲染

状态：已完成。

目标：

- 把 `deps` 统一编译为可视化依赖关系，用于 DP 转移、图松弛、哈希命中、单调栈弹出、二分区间收缩等场景。

涉及文件：

- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/export.py`
- `tests/offline_regression.py`
- `tests/browser_smoke.py`

验收标准：

- 当前对象、依赖对象、依赖方向能在主可视化区看见。
- matrix 依赖可以显示箭头或等价连接。
- graph 依赖可以显示当前边、父节点或松弛来源。
- array / stack / map 依赖可以通过联动高亮和说明表达。
- 无法画几何箭头时必须有稳定的文本化连接说明。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不从 HTML runtime 重新推导依赖。
- 不新增未实现的 target 前缀。

### P2.3 多视觉原语复合场景

状态：已完成。

目标：

- 支持一个帧里同时展示多个相关原语，例如 graph + queue + map、array + stack、tree + recursion_tree、heap + array。

涉及文件：

- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/layout_registry.py`
- `algolab/renderer/export.py`
- `tests/offline_regression.py`
- `tests/browser_smoke.py`

验收标准：

- BFS 页面能同时看到 graph、queue、dist / visited。
- 单调栈页面能同时看到原数组、栈、answer。
- 树递归页面能同时看到 tree 和 frame / call stack。
- 多原语布局不会互相遮挡，窄屏下能纵向降级。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不把多视图拼接写死为某个算法族。

### P2.4 通用 before / after 和状态变化表达

状态：已完成。

目标：

- 用统一方式展示当前帧的值变化、指针移动、容器 push / pop、边选择、parent 改写等状态变化。

涉及文件：

- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/export.py`
- `tests/offline_regression.py`

验收标准：

- `before`、`after`、`value` 和 state diff 能进入本步讲解。
- 数组写入、map 更新、指针移动、queue / stack 变化都能表达。
- 没有 before / after 时能退化为 state diff。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
```

禁止事项：

- 不用前端重算 diff 以外的算法语义。

### P2.5 黄金样例视觉矩阵

状态：已完成。

目标：

- 用一组横向黄金样例验证通用可视化编译层，而不是只验证单个算法。

涉及文件：

- `docs/examples/`
- `tests/fixtures.py`
- `tests/offline_regression.py`
- `tests/browser_smoke.py`

验收标准：

- 至少覆盖 `unique_paths`、`bfs`、`binary_search`、`monotonic_stack`。
- 每个样例明确主原语、辅助原语、关键 deps、关键 teaching 字段。
- browser smoke 检查主画布非空、关键对象可见、步骤切换无 JS error。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不把黄金样例变成 renderer 专用分支。

## Phase 3：通用教学解释与证据层

目标：

- 让每个算法族都能用统一教学字段解释“当前做什么、为什么、依赖谁、是否被校验通过”。

### P3.1 TeachingStep 通用展示

状态：已完成。

目标：

- 右侧讲解区统一展示 `what`、`why`、`formula`、`invariant`、`common_mistake`、`hint`。

涉及文件：

- `algolab/schemas/semantic_trace.py`
- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/export.py`
- `tests/offline_regression.py`

验收标准：

- DP 可展示转移公式和值代入。
- BFS / Dijkstra 可展示距离来源或松弛规则。
- 二分 / 滑动窗口可展示收缩或移动原因。
- 单调栈 / 单调队列可展示维护的不变量。
- 无 `formula` 的算法不被迫伪造公式，可展示规则或不变量。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
```

禁止事项：

- 不把 `teaching` 只设计成 DP 公式容器。

### P3.2 用户可读的过程校验证据

状态：已完成。

目标：

- 把 process validator 的关键结果翻译成学习者能读懂的本步证据，同时保留 raw report 在 Debug Drawer。

涉及文件：

- `algolab/verification/process_validator.py`
- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/export.py`
- `tests/offline_regression.py`

验收标准：

- DP 转移、BFS 首次访问、二分区间收缩、单调栈弹出至少能显示一类用户可读校验证据。
- blocking error 和 warning 不被吞掉。
- raw validation report 仍能在 Debug Drawer 查看。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
```

禁止事项：

- 不为了页面好看放宽 validator。

### P3.3 阶段标签和关键帧策略

状态：已完成。

目标：

- 统一生成和展示算法阶段标签，使时间线能按语义组织。

涉及文件：

- `algolab/compiler/scene_compiler.py`
- `algolab/generation/prompts/tracker_system.txt`
- `algolab/renderer/export.py`
- `tests/offline_regression.py`
- `tests/browser_smoke.py`

验收标准：

- 初始化、主循环、关键转移、返回结果等阶段能稳定显示。
- 没有阶段字段时可按 op / role / event 位置降级。
- 时间线不按具体题名硬编码阶段。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不破坏现有 range 跳转和播放控制。

### P3.4 代码同步

状态：已完成。

目标：

- 当前帧能高亮或展示对应 `code_line`，帮助学习者把语义步骤和伪代码 / 代码对应起来。

涉及文件：

- `algolab/renderer/export.py`
- `algolab/generation/prompts/tracker_system.txt`
- `tests/offline_regression.py`

验收标准：

- 当前帧显示 `code_line`。
- prompt 要求关键事件提供准确 `code_line`。
- 无 `code_line` 或越界时稳定降级。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
```

禁止事项：

- 不让 renderer 猜代码行。

## Phase 4：通用学习交互层

目标：

- 把页面从播放器升级为交互式算法实验室，所有交互都只读 SceneGraph / BuildArtifact，不修改 trace。

### P4.1 通用预测交互

状态：已完成。

涉及文件：

- `algolab/schemas/semantic_trace.py`
- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/export.py`
- `tests/offline_regression.py`
- `tests/browser_smoke.py`

验收标准：

- 支持 `choice`、`input`、`judge`。
- 正误反馈可见。
- 交互不改变 trace。
- DP、二分、BFS、单调栈至少各有一种可验证交互样例。
- 无 interaction 字段时页面保持播放、跳转和讲解能力。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不把交互答案写死在 renderer。

### P4.2 点击依赖对象

状态：已完成。

涉及文件：

- `algolab/renderer/export.py`
- `tests/browser_smoke.py`

验收标准：

- 点击当前对象显示它依赖谁。
- 点击依赖对象显示它影响谁。
- 对象说明来自 SceneGraph marks、deps、evidence。
- matrix、graph、array / stack 至少各有一个覆盖样例。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不从算法名推断依赖关系。

### P4.3 输入重新生成和解法切换入口

状态：已完成。

目标：

- 页面提供输入修改、重新生成、解法 variant 切换的产品入口；真正重新生成必须回到主 pipeline。

涉及文件：

- `algolab/renderer/export.py`
- `algolab/pipeline.py`
- `tests/browser_smoke.py`

验收标准：

- 页面能展示当前输入和 variant 列表。
- 重新生成入口清楚标明会重新走 pipeline。
- 当前静态 HTML 环境无法在线调用后端时，必须给出稳定降级说明和 artifact 输入。
- 切换 variant 不混用不同 SceneGraph。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不允许前端临时改 trace 伪装成新输入结果。

### P4.4 解法对比

状态：已完成。

涉及文件：

- `algolab/renderer/export.py`
- `tests/browser_smoke.py`

验收标准：

- 能并排或快速切换比较两个 variant。
- 显示复杂度、关键步骤数、结果一致性。
- 不同解法使用各自 SceneGraph。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不把多个 variant 的状态混在一起。

## Phase 5：通用过程校验能力层

目标：

- 把“过程可验证”从少数样例扩展成按算法族可复用的校验框架。

### P5.1 算法族校验注册表

状态：已完成。

目标：

- 明确每个算法族使用哪些 process invariant、coverage rule 和 failure type。

涉及文件：

- `algolab/verification/process_validator.py`
- `tests/offline_regression.py`
- `tests/benchmark_regression.py`
- `docs/06_EVALUATION_AND_BENCHMARK.md`

验收标准：

- DP、BFS、二分、单调栈、哈希、树、并查集至少有注册入口或明确降级策略。
- 未覆盖算法族不会假装通过强校验，只能通过基础 schema / scene / answer gate。
- 失败分类能进入 benchmark report。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

禁止事项：

- 不用一个过宽的规则覆盖所有算法族。
- 不放宽已有 blocking validator。

### P5.2 横向 process invariant 覆盖

状态：已完成。

目标：

- 为核心算法族补正例和反例，使校验能力跟视觉覆盖同步扩展。

涉及文件：

- `algolab/verification/process_validator.py`
- `tests/offline_regression.py`
- `tests/benchmark_regression.py`

验收标准：

- DP：关键转移依赖和值正确。
- BFS：首次发现节点的距离或父节点来源正确。
- 二分：区间收缩方向和边界合法。
- 单调栈：弹出和答案写入满足单调性解释。
- 并查集：union / find 后 parent 或 root 关系可核对。
- 每类至少一个反例能失败。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

禁止事项：

- 不把 process validator 做成只看最终答案。

### P5.3 关键步骤覆盖率

状态：已完成。

目标：

- 检查小规模样例是否记录了关键过程，避免 trace 只给最终结果。

涉及文件：

- `algolab/verification/process_validator.py`
- `tests/benchmark_cases.py`
- `tests/benchmark_regression.py`

验收标准：

- DP 小表必须记录关键内部格更新。
- BFS 小图必须记录出队、检查边、首次访问。
- 二分必须记录比较 mid 和收缩区间。
- 单调栈必须记录 push / pop 和答案写入。
- coverage warning / error 能进入 evaluation report。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

禁止事项：

- 不只增加 expected output，不补过程验收。

## Phase 6：Trace 生成和 Repair 强化

目标：

- 让 LLM 更稳定地产生可校验、可教学的 trace。

### P6.1 Tracker prompt 强化

状态：已完成。

涉及文件：

- `algolab/generation/prompts/tracker_system.txt`
- `tests/offline_regression.py`

验收标准：

- prompt 明确要求 Tracer API。
- prompt 明确要求 teaching 字段。
- prompt 明确要求关键 set 事件提供 deps、value、state、reason、code_line。
- prompt 明确禁止旧字段和旧 map target。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
```

禁止事项：

- 不让 LLM 生成 HTML。

### P6.2 Repair 分类

状态：已完成。

涉及文件：

- `algolab/generation/solution_generator.py`
- `algolab/verification/*`
- `scripts/run_llm_benchmark.py`
- `tests/offline_regression.py`

验收标准：

- schema_error、target_error、process_error、coverage_error、scene_error 能进入 repair 上下文。
- repair prompt 能指出具体失败 step / target。
- benchmark report 能统计 repair 前后失败类型。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
```

禁止事项：

- 不吞掉 validator 错误。

### P6.3 Tracer API 扩展评估

状态：已完成。

涉及文件：

- `algolab/runtime/tracer.py`
- `tests/tracer_regression.py`
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`

验收标准：

- 评估是否需要 `link`、`unlink`、`enter`、`exit` 便捷方法。
- 如新增方法，必须有 tracer regression。
- 文档和 prompt 同步更新。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.tracer_regression
```

禁止事项：

- 不在同一任务里同时大改 renderer。

## Phase 7：经典算法族扩展

目标：

- 在稳定页面和验证能力基础上，扩展 V1 经典算法覆盖。

每新增一个算法族必须按同一流程：

1. 增加 golden example 文档。
2. 增加 deterministic benchmark。
3. 明确视觉原语映射。
4. 明确 process validator 是否需要增强。
5. 增加 renderer / browser smoke 覆盖。
6. 更新 evaluation report 分类。

### P7.1 字符串算法组

状态：已完成。

范围：

- KMP 深化。
- Rabin-Karp。
- Z Algorithm。
- Manacher。

涉及文件：

- `tests/benchmark_cases.py`
- `algolab/verification/process_validator.py`
- `algolab/renderer/export.py`
- `docs/examples/`

验收标准：

- text / pattern / pi / z / radius 可见。
- 失配回退或半径扩展过程可解释。
- 每类至少一个 benchmark。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

### P7.2 树和递归组

状态：已完成。

范围：

- 树遍历。
- LCA 深化。
- 树直径。
- 树形 DP。
- 回溯搜索树。

验收标准：

- 当前节点、递归栈、返回值、子树聚合可见。
- frame 与 tree 节点能联动。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

### P7.3 区间结构组

状态：已完成。

范围：

- 线段树。
- 树状数组。
- 稀疏表。

验收标准：

- 不使用 `range:` target。
- 区间覆盖用 tree nodes label/meta 或 matrix 表示。
- query / update 路径可见。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

### P7.4 数学与位运算组

状态：已完成。

范围：

- GCD。
- 快速幂。
- 筛法。
- 组合数。
- 位掩码枚举。
- lowbit。

验收标准：

- 不使用 `number:` target。
- 位图、表格或数组状态可见。
- 关键数学不变量可解释。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

### P7.5 图高级组

状态：已完成。

范围：

- SCC / Tarjan。
- 割点和桥。
- 二分图匹配。
- Edmonds-Karp 教学版。

验收标准：

- dfn / low / stack / match / capacity / flow 可见。
- 不使用未实现 `flow:` target。
- 至少一个失败反例进入 process validator 测试。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

## Phase 8：评估、Dashboard 和论文产物

目标：

- 建立可复现评估闭环，服务论文和项目迭代。

### P8.1 Evaluation manifest

状态：已完成。

涉及文件：

- `scripts/build_evaluation_manifest.py`
- `scripts/build_evaluation_report.py`
- `output/evaluation/`

验收标准：

- manifest 记录题目、输入、expected、算法族、视觉形态、产物路径。
- report 按算法族统计通过率和失败类型。
- report 记录模型配置和 repair 轮次。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_manifest.py
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_report.py
```

禁止事项：

- 不把 output 临时产物当作唯一真相。

### P8.2 浏览器截图回归

状态：已完成。

涉及文件：

- `tests/browser_smoke.py`
- `scripts/check_benchmark_html.py`
- `output/*`

验收标准：

- 至少覆盖 unique paths、BFS、binary search、daily temperatures。
- 检查 JS error。
- 检查主画布非空。
- 检查主要文本和控件不重叠。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

禁止事项：

- 不只检查文件存在。

### P8.3 Baseline 与 Ablation 报告

状态：已完成。

涉及文件：

- `scripts/run_llm_benchmark.py`
- `scripts/build_evaluation_report.py`
- `docs/06_EVALUATION_AND_BENCHMARK.md`

验收标准：

- 支持直接 HTML baseline。
- 支持无 process validator / 无 SceneGraph compiler ablation 的统计口径。
- 输出失败分类。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_report.py
```

禁止事项：

- 不把 baseline 逻辑混入主 pipeline 发布路径。

## Phase 9：发布形态

目标：

- 形成可演示、可复现、可维护的 V1 产品和论文资产。

### P9.1 Demo Dashboard

状态：已完成。

涉及文件：

- `scripts/build_demo_dashboard.py`
- `output/dashboard/`

验收标准：

- dashboard 展示黄金样例、算法族覆盖、校验状态、HTML 链接、artifact 链接。
- 页面能按算法族筛选。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_demo_dashboard.py --output-dir output/dashboard --style both
```

### P9.2 Reproducibility Package

状态：已完成。

涉及文件：

- `docs/06_EVALUATION_AND_BENCHMARK.md`
- `benchmark/`
- `scripts/`
- `tests/`

验收标准：

- 记录环境、模型配置、样例输入、运行命令、输出路径。
- 一条命令能跑确定性质量检查。
- LLM benchmark 和 deterministic benchmark 分开。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

### P9.3 V1 Release Gate

状态：已完成。

验收标准：

- 第一阶段 80 到 120 个样例通过 deterministic benchmark。
- 黄金样例 browser smoke 通过。
- Debug Drawer 可查看工程证据。
- 评估报告能输出失败分类。
- 文档和命令使用指定 Python 解释器。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

## 10. V1.1 之后的实施路线

当前下一步不再从 Phase 1 开始。Phase 0 到 Phase 9 已经作为 V1 基线完成，后续从 Phase 10 开始。

总原则：

- 先做算法族正确性，再做视觉 polish。
- 先扩 deterministic benchmark 和 family validator，再扩 LLM benchmark。
- 新增 case 只能作为算法族能力证据，不能变成单题硬编码。
- 每个算法族先跑通核心子模式，再扩复杂变体。
- 每个任务都必须保留失败分类，不能只给 pass/fail。

### 10.1 后续阶段总览

| 阶段 | 名称 | 目标 | 是否阻塞下一阶段 |
|---|---|---|---|
| Phase 10 | 算法族治理和 benchmark 分层 | 让系统知道每个 case 属于哪个族、哪个子模式、哪个门禁层 | 阻塞 |
| Phase 11 | 答案正确性和 oracle 强化 | 每个族有独立参考解、边界样例、随机样例或性质测试 | 阻塞 |
| Phase 12 | 算法族 trace contract | 让 LLM/fixture 按族生成结构化过程，而不是自然语言流水账 | 阻塞 |
| Phase 13 | family process validator 扩展 | 把核心算法族升级到 strong 或 medium+ | 阻塞 |
| Phase 14 | demo readiness gate | 检查演示语义是否完整、不误导 | 阻塞 dashboard 宣传 |
| Phase 15 | LLM benchmark 和 repair 泛化 | 评估真实模型在算法族上的通过率和修复能力 | 不阻塞 deterministic gate |
| Phase 16 | 算法族覆盖扩容 | 扩到 250 到 350 个 deterministic samples | 不阻塞前面质量任务 |
| Phase 17 | 视觉和交互增强 | 在语义正确的基础上优化教学页面 | 后置 |

### 10.2 每轮执行模板

执行 AI 每次只能选择最靠前阶段中的一个任务。每个任务必须按下面顺序完成：

1. 阅读本 roadmap、evaluation 文档、trace contract 和视觉原语文档。
2. 确认本轮算法族、子模式、目标等级和不做事项。
3. 先加或更新测试，覆盖正例和反例。
4. 再改 benchmark / contract / validator / pipeline / renderer 中必要部分。
5. 运行本任务最小验证；阶段收尾或合并前再运行全量质量检查。
6. 更新报告或文档中对应状态。
7. 输出本轮新增的算法族能力、还不能保证的边界和失败分类。

禁止：

- 因为某个 case 失败而放宽 validator。
- 因为 renderer 暂时不好画而让 LLM 直接生成 HTML。
- 用算法名在 renderer 里写题目专用分支。
- 只增加 benchmark case，不增加对应族级 contract、validator 或 fallback 说明。
- 把 `process_fallback` 或 `process_uncovered` 伪装成 strong。

### 10.3 验证分层

从 Phase 12 开始，默认使用分层验证，避免每个小任务都运行完整浏览器 smoke。

| 改动类型 | 本任务最小验证 | 阶段收尾验证 | 合并前验证 |
|---|---|---|---|
| 纯文档 / prompt / contract | `git diff --check`，必要时跑相关静态检查 | 对应文档检查脚本 | `scripts/run_quality_checks.py` |
| trace contract / Tracer API | 相关 contract 测试或 `-m tests.benchmark_regression` | family release gate | `scripts/run_quality_checks.py` |
| process validator | 相关 family 正反例测试；没有细分测试时跑 `-m tests.benchmark_regression` | `scripts/check_family_release_gate.py` | `scripts/run_quality_checks.py` |
| benchmark / oracle | 相关 benchmark/property/oracle 脚本 | family release gate | `scripts/run_quality_checks.py` |
| evaluation / dashboard 数据 | 对应 report/dashboard 构建脚本 | family release gate | `scripts/run_quality_checks.py` |
| renderer / HTML runtime / browser 交互 | `bash scripts/run_browser_smoke_container.sh` 或目标页面 smoke | 容器内 `tests.browser_smoke` | `bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py` |
| LLM benchmark / repair | 小规模 `--limit` 或目标 family 运行 | family split report | 不要求每次全量，论文实验冻结时全量跑 |

浏览器 smoke 必须走 `scripts/run_browser_smoke_container.sh`。当前宿主机 glibc 2.17 不能运行 Playwright 自带 node；不要把该环境失败记作代码失败，也不要为了通过门禁降级浏览器检查。容器脚本默认使用当前机器已缓存的 `iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest`，并以宿主机 UID/GID 写入挂载目录，避免生成 root-owned 产物。外部 CI 可以用 `ALGOLAB_PLAYWRIGHT_IMAGE=mcr.microsoft.com/playwright/python:v1.59.0-noble ALGOLAB_CONTAINER_INSTALL_DEPS=1` 覆盖为官方 Playwright 镜像。

执行环境还必须允许访问 Docker daemon。脚本会优先使用普通 `docker`，失败后自动尝试 `sudo -n docker`。若 `docker run` 报 `/var/run/docker.sock: permission denied` 且 sudo docker 也不可用，需要运维层面把当前用户加入 `docker` 组、配置免密 `sudo docker`，或在有 Docker 权限的 CI 上运行；执行 AI 只能记录环境阻塞，不能跳过 browser gate。

全量质量检查只在以下情况默认运行：

- Phase 收尾。
- 准备提交或推送。
- 修改 renderer、HTML runtime、pipeline、release gate、全局 validator 调度。
- 执行 AI 无法判断局部验证是否覆盖改动风险。

科研原型阶段允许“局部验证通过 + 明确剩余风险”作为单个小任务的完成状态。不得用未跑全量检查来宣称整个阶段完成。

## Phase 10：算法族治理和 Benchmark 分层

目标：

- 把 benchmark 从“样例列表”升级为“算法族能力证据库”。
- 每个 case 都有 family id、子模式、门禁层、目标强度和校验能力声明。
- release gate 能区分 smoke、family core、expansion、LLM eval。

### P10.1 算法族注册表文件

状态：已完成。

完成证据：

- 新增 `benchmark/family_capabilities.json` 独立注册表，覆盖现有 deterministic benchmark 的 18 个 family label。
- 新增 `scripts/check_family_capabilities.py`，会在 benchmark family 未注册、process profile 未知、非 strong profile 缺少 fallback 边界或目标样例数不满足时失败。
- `tests/benchmark_regression.py` 增加注册表覆盖和未注册 family 失败路径测试。
- `docs/06_EVALUATION_AND_BENCHMARK.md` 记录独立注册表、现有 family label 和检查命令。

建议涉及文件：

- `benchmark/family_capabilities.json` 或 `benchmark/family_capabilities.yaml`
- `algolab/verification/process_validator.py`
- `scripts/check_family_capabilities.py`
- `tests/benchmark_regression.py`
- `docs/06_EVALUATION_AND_BENCHMARK.md`

目标：

- 建立独立的算法族注册表，避免只从 `process_validator.py` 推断支持能力。
- 每个族声明：`family_id`、中文名、目标等级、当前等级、核心子模式、视觉原语、process profile、benchmark 目标数、fallback 边界。

注册表示例：

```json
{
  "family_id": "dynamic_programming",
  "label": "动态规划",
  "target_level": "strong",
  "current_level": "strong",
  "subfamilies": ["1d", "2d", "knapsack", "interval", "tree_dp", "bitmask", "digit_dp"],
  "visual_primitives": ["array", "matrix", "tree", "recursion_tree", "math_bit"],
  "process_profile": "dp",
  "gate_layers": ["smoke", "family_core", "expansion"]
}
```

验收标准：

- 注册表覆盖 `tests/benchmark_cases.py` 中所有现有 family。
- 每个 family 都能映射到 process profile：`strong`、`fallback` 或 `uncovered`。
- 未注册 family 会让检查脚本失败。
- 文档中算法族名称与注册表一致。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

### P10.2 Benchmark case 元数据扩展

状态：已完成。

完成证据：

- `tests/benchmark_cases.py` 为每个 `BenchmarkCase` 暴露 `family_id`、`subfamily_id`、`gate_layer`、`support_level`、`process_profile`、`oracle_type`、`demo_required`。
- `scripts/build_evaluation_manifest.py` 输出 case 级元数据，并在 summary 中聚合 family id、subfamily、gate layer、support level、process profile、oracle type 和 demo_required 数量。
- `scripts/build_demo_dashboard.py` 在 demo record、核心 CSV、页面筛选和 family coverage 中展示并按 family + gate layer 聚合。
- `tests/benchmark_regression.py` 增加 case 元数据、manifest 统计和 dashboard gate layer 聚合测试。

建议涉及文件：

- `tests/benchmark_cases.py`
- `benchmark/benchmark_cases_list.md`
- `scripts/build_evaluation_manifest.py`
- `scripts/build_demo_dashboard.py`
- `tests/benchmark_regression.py`

目标：

- 给每个 case 增加可统计元数据：`family_id`、`subfamily_id`、`gate_layer`、`support_level`、`process_profile`、`oracle_type`、`demo_required`。

建议字段：

| 字段 | 含义 |
|---|---|
| `family_id` | 稳定英文 id，例如 `dynamic_programming` |
| `subfamily_id` | 子模式，例如 `knapsack_01` |
| `gate_layer` | `smoke`、`family_core`、`expansion`、`llm_eval` |
| `support_level` | 当前 case 对应强度：`strong`、`medium_plus`、`medium`、`basic` |
| `process_profile` | 绑定 process validator 注册项 |
| `oracle_type` | `closed_form`、`independent_reference`、`bruteforce`、`property` |
| `demo_required` | 是否进入演示正确性门禁 |

验收标准：

- 现有 case 迁移后 benchmark 仍全部通过。
- evaluation manifest 输出 family/subfamily/gate_layer 统计。
- dashboard 能按 family 和 gate layer 聚合。
- release gate 仍保留 V1 deterministic 样例范围，同时新增 V1.1 family gate 报告。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_manifest.py --output-dir output/evaluation
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

### P10.3 分层门禁报告

状态：已完成。

完成证据：

- 新增 `scripts/check_family_release_gate.py`，独立生成 family release gate，不改变 `scripts/check_v1_release_gate.py` 的 V1 结论。
- 输出 `output/release_gate/family_release_gate.json` 和 `output/release_gate/family_release_gate.md`，报告每个算法族的 case 数、sample 数、answer pass、process pass、demo readiness 和 fallback/uncovered 数量。
- family gate 会实际执行 deterministic `solve`、`trace`、`verify`，并对 trace 运行 `validate_process`。
- `current_level=strong` 的算法族如果使用 `process_fallback` 或 `process_uncovered` 会失败；`medium/basic` fallback 会作为 warning 明示。
- `tests/benchmark_regression.py` 增加分层门禁报告与 strong fallback 失败路径测试。

建议涉及文件：

- `scripts/check_v1_release_gate.py`
- `scripts/check_family_release_gate.py`
- `scripts/build_evaluation_report.py`
- `output/release_gate/`
- `docs/06_EVALUATION_AND_BENCHMARK.md`

目标：

- 保留当前 V1 release gate。
- 新增 family release gate，不改变既有 V1 结论。
- 报告每个算法族的：case 数、sample 数、answer pass、process pass、demo readiness、fallback/uncovered 数量。

验收标准：

- 输出 `output/release_gate/family_release_gate.json`。
- 输出 `output/release_gate/family_release_gate.md`。
- `strong` 算法族如果出现 `process_fallback` 或 `process_uncovered`，报告必须失败。
- `medium/basic` 算法族可以 fallback，但必须在报告中明示。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

## Phase 11：答案正确性和 Oracle 强化

目标：

- 每个算法族的最终答案正确性不依赖 LLM 自证。
- deterministic benchmark 中每个 case 都有独立 verifier 或参考 oracle。
- 对适合随机化的小规模输入增加 brute force / property 测试。

### P11.1 Oracle 类型规范

状态：已完成。

完成证据：

- `tests/benchmark_cases.py` 为每个 benchmark case 暴露 `oracle_type`、`oracle_risk`、`oracle_notes` 和 `oracle_reference`。
- 缺少 verifier 的 case 会自动标记 `missing_verifier`；verifier 与 solve 结构过于相同的 case 会自动标记 `verifier_matches_solve`。
- 当前发现并标记了树、树形 DP、区间结构、数学位运算和图高级中 verifier 与 solve 结构相同的 case，strong family 不再把这类 verifier 当作唯一答案正确性证据。
- 新增 `tests/oracles/`，提供 DP、图、字符串、排序、并查集、区间结构等独立 oracle 示例，并补充树、数学和图高级风险 case 的参考入口。
- `scripts/build_evaluation_manifest.py` 和 `scripts/build_demo_dashboard.py` 输出 oracle 风险字段，方便 report/dashboard 明示风险。
- `tests/benchmark_regression.py` 增加 P11.1 oracle 元数据、风险标记和独立示例覆盖测试。

建议涉及文件：

- `docs/06_EVALUATION_AND_BENCHMARK.md`
- `tests/benchmark_cases.py`
- `tests/oracles/`
- `tests/benchmark_regression.py`

目标：

- 规范四类 oracle：

| Oracle | 适用 | 要求 |
|---|---|---|
| `closed_form` | 不同路径、组合数等 | 公式必须独立于 solve 实现 |
| `independent_reference` | BFS、Dijkstra、排序等 | 代码结构不得复制被测 solve |
| `bruteforce` | 小规模 DP、回溯、图搜索 | 输入规模受控，能穷举验证 |
| `property` | 排序、堆、并查集、字符串表 | 检查性质而非单个答案 |

验收标准：

- 每个 benchmark case 声明 oracle 类型。
- 没有 verifier 或 verifier 与 solve 结构过于相同的 case 必须被标记。
- 至少 DP、图、字符串、排序、并查集、区间结构有独立 oracle 示例。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

### P11.2 小规模随机样例生成器

状态：已完成。

完成证据：

- 新增 `tests/property_cases.py`，用固定默认 seed 为 DP、基础图、字符串、排序、并查集和区间结构生成小规模 deterministic random samples。
- 第一批覆盖 house robber、subset sum、LCS、编辑距离、0/1 knapsack、BFS layers、DFS connected、topological sort、Dijkstra positive、KMP、Z Algorithm、Manacher、insertion sort、merge sort、quickselect、union/find connectivity 和 range sum query/update。
- 新增 `scripts/run_property_benchmark.py`，输出 `output/property_benchmark/property_benchmark_report.json` 和 `property_benchmark_report.md`。
- 报告显式记录 `release_gate_included: false`，随机样例不进入 V1 release gate；`summary.family_robustness` 按 family 聚合 total、passed、failed、pass_rate、subfamilies 和 failure type 分布。
- 每条结果包含 `family`、`family_id`、`subfamily`、`subfamily_id`、`input`、`expected`、`actual`、`ok`、`failure_type`，失败类型覆盖 `answer_mismatch`、`exception`、`oracle_error`。
- `tests/benchmark_regression.py` 增加固定 seed 稳定性、覆盖子族、报告字段和写文件行为测试。

建议涉及文件：

- `tests/property_cases.py`
- `tests/oracles/`
- `scripts/run_property_benchmark.py`
- `docs/06_EVALUATION_AND_BENCHMARK.md`

目标：

- 为适合的小规模算法族生成 deterministic random samples。
- 固定 seed，输出可复现报告。

第一批覆盖：

- DP：house robber、subset sum、LCS、编辑距离、小背包。
- 图：BFS、DFS 连通、拓扑排序、Dijkstra 小正权图。
- 字符串：KMP、Z、Manacher 小字符串。
- 排序：插入、归并、快速选择。
- 并查集：随机 union/find 与连通性 brute force 对比。
- 区间结构：随机数组和 query/update。

验收标准：

- 脚本固定 seed 后结果稳定。
- 失败报告包含 family、subfamily、input、expected、actual、failure_type。
- 随机样例不进入 V1 release gate，但进入 family robustness report。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_property_benchmark.py --output-dir output/property_benchmark
```

### P11.3 输入边界样例库

状态：已完成。

完成证据：

- 新增 `benchmark/boundary_cases.json`，为当前全部 `family_core` deterministic benchmark case 登记边界覆盖或不适用原因。
- 边界类别固定为 `empty`、`single`、`duplicate`、`zero_or_negative`、`extreme`、`no_solution`、`multiple_solutions`。
- 新增 `scripts/check_boundary_cases.py`，校验边界登记与 `tests/benchmark_cases.py` 当前 `family_core` case 对齐，并输出 `output/boundary_cases/boundary_cases.json` 和 `boundary_cases.md`。
- 报告按 case 和 family 汇总 covered / not applicable / missing categories；缺失边界不改变 V1 release gate，但会让 strong `family_core` case 进入 `strong_upgrade_blocked_cases`，阻塞 strong 等级升级。
- `tests/benchmark_regression.py` 增加边界登记 schema、family_core 覆盖、not applicable reason、family 统计、写文件行为和 strong upgrade blocker 反例测试。

建议涉及文件：

- `benchmark/boundary_cases.json`
- `tests/benchmark_cases.py`
- `scripts/check_boundary_cases.py`

目标：

- 每个 family core case 至少覆盖：空输入、单元素、重复值、负数或零、极端边界、无解、有多个解。
- 不适用的边界必须写明原因。

验收标准：

- `family_core` 层的每个算法族有边界样例统计。
- 缺失边界不阻塞 expansion，但阻塞 strong 等级升级。

必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py
```

## Phase 12：算法族 Trace Contract

目标：

- 把 `semantic-trace-v1` 从通用 schema 扩展为算法族级过程合同。
- LLM、deterministic fixture 和 repair prompt 都按同一套族合同工作。

### P12.1 DP Trace Contract

状态：已完成。

建议涉及文件：

- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`
- `algolab/generation/prompts/tracker_system.txt`
- `algolab/runtime/tracer.py`
- `tests/benchmark_regression.py`

合同要求：

- 必须有初始化事件。
- 每个关键状态写入必须有 `targets`、`deps`、`before` 或 `value`、`state`。
- `state` 必须包含当前 DP 容器和循环变量。
- 转移事件必须能复原公式。
- 最终答案位置必须明确。
- 小规模 full-trace case 不能只给最终表。

验收标准：

- 1D、2D、背包、区间、树形、状态压缩至少各有一个正例 contract test。
- 缺少 deps、缺少初始化、错误答案位置、跳过关键更新的反例会失败。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- `algolab/verification/process_validator.py` 新增显式 `state["dp_contract"]` 校验。
- `tests/benchmark_regression.py` 覆盖 1D、2D、背包、区间、树形、状态压缩 DP 正例。
- 反例覆盖缺少 deps、缺少初始化、错误答案位置、跳过关键更新。
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md` 和 `algolab/generation/prompts/tracker_system.txt` 已写明 DP contract 字段与 tracker 输出要求。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。

Phase 12 收尾验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

### P12.2 图算法 Trace Contract

状态：已完成。

建议涉及文件：

- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`
- `algolab/generation/prompts/tracker_system.txt`
- `algolab/runtime/tracer.py`
- `tests/benchmark_regression.py`

合同要求：

- BFS/DFS 必须记录 frontier 或 recursion frame。
- 最短路必须记录 edge relax、old dist、new dist、parent 或 predecessor。
- 拓扑排序必须记录 indegree 变化和入队原因。
- MST 必须记录选边、弃边原因和 union-find 状态。
- Tarjan 必须记录 dfn/low/stack 更新。
- 网络流必须记录 augmenting path、bottleneck、flow/capacity 更新。

验收标准：

- 每个子模式至少有一个正例和一个过程错误反例。
- 对无权 BFS，重复首次访问、错误 dist、queue 跳变必须失败。
- 对 Dijkstra，负权输入必须被拒绝或降级说明。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- `algolab/verification/process_validator.py` 新增显式 `state["graph_contract"]` 校验。
- `tests/benchmark_regression.py` 覆盖 BFS、DFS、Dijkstra、拓扑排序、MST、Tarjan、网络流正例。
- 反例覆盖每个子模式，并单独覆盖 BFS 重复首次访问、错误 dist、queue 跳变，以及 Dijkstra 负权输入。
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md` 和 `algolab/generation/prompts/tracker_system.txt` 已写明 graph contract 字段与 tracker 输出要求。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。

### P12.3 字符串、树、回溯和数据结构 Trace Contract

状态：已完成。

建议涉及文件：

- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`
- `docs/05_VISUAL_PRIMITIVES_AND_PATTERNS.md`
- `algolab/generation/prompts/tracker_system.txt`
- `tests/benchmark_regression.py`

合同要求：

- 字符串：必须记录 text/pattern 指针、prefix/z/radius/hash 表和失配/扩展原因。
- 树：必须记录进入/退出 frame、当前节点、子树返回值和聚合结果。
- 回溯：必须记录 choose、enter、record、prune、undo。
- 堆：必须记录 push/pop、heap top、调整后的 heap。
- Trie：必须记录字符路径、节点创建、计数或 terminal 标记。
- 链表：必须记录 pointer 和 next/prev 改变，不能只给最终链。

验收标准：

- 每个子模式的最小 trace 能被 schema、target、process 和 scene 校验消费。
- 自然语言解释不能替代 `state`。
- 演示关键帧必须有 `reason`。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- `algolab/verification/process_validator.py` 新增显式 `state["family_contract"]` 校验。
- `tests/benchmark_regression.py` 覆盖字符串、树、回溯、堆、Trie、链表正例，并确认最小 trace 可被 schema、target、process 和 scene 校验消费。
- 反例覆盖缺 text/pattern 指针和表结构、缺树递归 enter/exit 和返回值、回溯缺 choose/undo、堆缺 pop/heap_top、Trie 缺 terminal/count、链表缺 pointer/next-prev 改变。
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md` 和 `algolab/generation/prompts/tracker_system.txt` 已写明 family contract 字段与 tracker 输出要求。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。

## Phase 13：Family Process Validator 扩展

目标：

- 把算法族正确性落到可执行 validator。
- 每个强支持族都必须有可复用 invariant，而不是 case 专用判断。

### P13.1 数组指针、窗口和前缀结构 validator

状态：已完成。

建议涉及文件：

- `algolab/verification/process_validator.py`
- `tests/benchmark_regression.py`
- `tests/benchmark_cases.py`

范围：

- 二分查找和二分答案。
- 双指针。
- 滑动窗口。
- 前缀和、差分、二维前缀。
- 快慢指针基础。

校验重点：

- 指针不越界。
- 指针移动与比较/约束结果一致。
- 窗口状态连续。
- 前缀递推正确。
- 区间查询用正确前缀项还原。

验收标准：

- 错误 mid、错误窗口收缩、错误 prefix/diff 更新的反例失败。
- 至少 18 个 deterministic samples 覆盖该族。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- `algolab/verification/process_validator.py` 新增 `array_pointer` strong family 注册和 `array_contract` 过程校验，覆盖 `binary_answer`、`two_pointer`、`sliding_window`、`prefix_sum`、`difference_array`、`fast_slow`。
- 二分过程校验补充 `mid == (left + right) // 2` 检查；二分识别只把 `pointer:mid`、算法名或 state 同时含 `left/right/mid` 作为二分信号，避免双指针误判成二分。
- 数组合同会阻塞指针越界、滑动窗口跳变或 `window_sum` 错误、prefix/diff 递推错误、`expected_targets` 缺失等过程错误。
- `algolab/verification/trace_validator.py` 允许二维列表整行 target（例如 `updates[0]`）作为合法 state path，与 Scene Compiler 对整行引用的解析保持一致。
- `tests/benchmark_cases.py` 新增 6 个 `array_pointer` family core case、18 个 deterministic samples：二分答案整数平方根、有序数组两数之和、滑动窗口最短子数组、前缀和区间查询、差分数组区间加、快慢指针判环。
- `benchmark/family_capabilities.json` 注册 `array_pointer` strong family；`benchmark/boundary_cases.json` 补齐 6 个新增 family core case 的边界覆盖或不适用原因。
- `tests/benchmark_regression.py` 覆盖错误 mid、错误窗口收缩、错误 prefix/diff 更新、双指针误判二分、差分 `updates[0]` target 和 18 个 samples 的 family gate 统计。
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`、`algolab/generation/prompts/tracker_system.txt`、`docs/06_EVALUATION_AND_BENCHMARK.md` 和 `benchmark/benchmark_cases_list.md` 已同步数组指针族合同与当时 39 case / 99 samples benchmark 口径；P13.2 后统计由 DP 扩容任务继续更新。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py`。

### P13.2 DP validator 扩展

状态：已完成。

建议涉及文件：

- `algolab/verification/process_validator.py`
- `tests/benchmark_cases.py`
- `tests/benchmark_regression.py`

范围：

- 一维 DP。
- 二维 DP。
- 0/1 背包、完全背包、多重背包基础。
- LCS、编辑距离。
- 区间 DP。
- 树形 DP。
- 状态压缩 DP。
- 数位 DP 入门。

校验重点：

- 初始化合法。
- 遍历顺序合法。
- `deps` 与转移公式一致。
- 小规模 case 覆盖关键更新。
- 最终答案位置正确。

验收标准：

- DP family core 至少 35 个 samples。
- 每个 DP 子模式有正例。
- 每个强校验子模式有至少一个反例。
- 不能因为复杂 DP 不能强校验而让整个 DP 降级；只允许子模式明确 fallback。

完成证据：

- `algolab/verification/process_validator.py` 的 DP profile 保持 strong，并覆盖 DP contract、打家劫舍、不同路径、0-1 背包、完全背包、多重背包、LCS、编辑距离、区间 DP、树形 DP、状态压缩 DP 和数位 DP 入门校验；完全背包按 active coins 复核，多重背包按 `counts` 上限复核，数位 DP 默认统计 `1..n` 中不含 7 的数字数量。
- `tests/benchmark_cases.py` 新增 8 个 DP core cases / 32 samples：`knapsack_01_subset_sum`、`complete_knapsack_coin_change`、`bounded_knapsack_max_value`、`lcs_length`、`edit_distance`、`interval_dp_merge_stones`、`state_compression_tsp`、`digit_dp_no_seven`；当前 deterministic benchmark 为 47 cases / 131 samples，DP family core process_profile=dp 为 40 samples。
- `tests/benchmark_regression.py` 新增并接入 `test_phase13_dp_validator_expands_family_core_samples_and_rejects_digit_dp_errors()`，覆盖 DP samples 下限、子模式集合、strong profile，以及打家劫舍、不同路径、0-1 背包、完全背包、多重背包、LCS、编辑距离、区间 DP、树形 DP、状态压缩 DP、数位 DP 反例。
- `benchmark/family_capabilities.json` 注册 `DP 核心扩展` strong family；`benchmark/boundary_cases.json` 登记 8 个新增 DP core cases 的边界覆盖或不适用原因。
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`、`algolab/generation/prompts/tracker_system.txt` 和 `benchmark/benchmark_cases_list.md` 已同步 DP subfamily、数位 DP 统计约定、多重背包 count 上限和 47 cases / 131 samples benchmark 口径。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... inspect.getsource(regression.run_all) ... PY`，确认 P13.2 测试接入 `run_all()`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py`。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

Phase 13 收尾验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate
```

### P13.3 图基础、最短路和 MST validator

状态：已完成。

建议涉及文件：

- `algolab/verification/process_validator.py`
- `tests/benchmark_cases.py`
- `tests/benchmark_regression.py`

范围：

- BFS、DFS、连通分量。
- 拓扑排序。
- 二分图染色。
- Dijkstra、Bellman-Ford、Floyd、0-1 BFS。
- Kruskal、Prim。

校验重点：

- visited/dist/color/indegree 状态连续。
- relax 前后值正确。
- Dijkstra 仅对非负权强校验。
- Bellman-Ford 轮次和松弛次数合理。
- Floyd 的 `k` 阶段依赖正确。
- Kruskal 选边与 union-find 一致。

验收标准：

- 图基础 family core 至少 22 个 samples。
- 最短路/MST 至少 18 个 samples。
- 错误 dist、错误 relax、错误拓扑入度、错误 MST 选边反例失败。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- `algolab/verification/process_validator.py` 的基础图 profile 保持 strong，并扩展 `graph_contract` 子模式到 BFS、DFS、连通分量、拓扑排序、二分图染色；新增 `shortest_path_mst` strong profile，覆盖 Dijkstra、Bellman-Ford、Floyd-Warshall、0-1 BFS 和 Kruskal MST 的 relax / matrix / union-find 过程校验。
- `tests/benchmark_cases.py` 新增并注册 9 个 family core cases / 38 samples：`graph_dfs_traversal`、`graph_connected_components`、`graph_topological_sort`、`graph_bipartite_coloring`、`dijkstra_shortest_path`、`bellman_ford_shortest_path`、`floyd_warshall_all_pairs`、`zero_one_bfs_shortest_path`、`kruskal_mst_weight`；当前 deterministic benchmark 为 56 cases / 169 samples。
- `tests/benchmark_regression.py` 新增并接入 `test_phase13_graph_validator_expands_core_shortest_mst_samples_and_rejects_process_errors()`，覆盖基础图和最短路/MST samples 下限、strong profile、核心子模式集合，以及错误 Dijkstra relax、错误拓扑入度、错误 MST 选边等反例。
- `benchmark/family_capabilities.json` 已同步 `basic_graph` 的 5 case / 22 samples target，并注册 `最短路 / MST` strong family；`benchmark/boundary_cases.json` 登记 9 个新增 family core cases 的七类边界覆盖或不适用原因。
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`、`docs/06_EVALUATION_AND_BENCHMARK.md`、`benchmark/benchmark_cases_list.md` 和 V1 release gate 样例范围已同步 P13.3 图算法族和 56 cases / 169 samples 口径。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile tests/benchmark_cases.py algolab/verification/process_validator.py tests/benchmark_regression.py scripts/check_v1_release_gate.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py`。

### P13.4 字符串 validator 扩展

状态：已完成。

建议涉及文件：

- `algolab/verification/process_validator.py`
- `tests/benchmark_cases.py`
- `tests/benchmark_regression.py`

范围：

- KMP。
- Rabin-Karp。
- Z Algorithm。
- Manacher。
- 字符串滑动窗口。
- Trie 前缀匹配的字符串部分。

校验重点：

- prefix table。
- rolling hash。
- z array。
- palindrome radius。
- 指针回退和窗口移动。

验收标准：

- 字符串 family core 至少 18 个 samples。
- 每个表结构有独立 oracle 复核。
- 错误 prefix/z/radius/hash 反例失败。

完成证据：

- `algolab/verification/process_validator.py` 的 `string` strong profile 覆盖 KMP prefix、Rabin-Karp rolling hash、Z 数组、Manacher radius、字符串滑动窗口和 Trie 前缀路径；滑动窗口允许带明确收缩原因的重复中间帧，但会阻塞无解释跳变、错误 `window_counts` 和错误前缀计数。
- `tests/benchmark_cases.py` 新增并接入 2 个字符串 family core cases / 6 samples：`string_sliding_window_unique` 和 `trie_prefix_match_string`；当前 deterministic benchmark 为 58 cases / 175 samples，字符串 family core 为 6 cases / 18 samples。
- `tests/oracles/__init__.py` 新增 `string_unique_window_reference` 和 `trie_prefix_count_reference`，`tests/benchmark_regression.py` 校验新增 oracle 引用可独立复核所有样例。
- `benchmark/family_capabilities.json` 已同步 `string_advanced` strong family 的 6 case / 18 samples target；`benchmark/boundary_cases.json` 登记 2 个新增字符串 core cases 的边界覆盖或不适用原因。
- `docs/06_EVALUATION_AND_BENCHMARK.md` 和 `benchmark/benchmark_cases_list.md` 已同步 58 cases / 175 samples 口径。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

### P13.4.5 长文件拆分与模块边界整理

状态：已完成。

目标：

- 降低后续 P13.5-P13.7 继续扩展 validator 和 benchmark 时的维护成本。
- 只做等价拆分，不新增算法族、不新增 benchmark case、不改变现有校验语义。
- 保持现有公开入口兼容，避免影响脚本、测试和论文实验口径。

背景：

- `algolab/verification/process_validator.py` 已接近 5000 行，多个 family validator、公共 target/state helper 和注册表混在同一文件。
- `tests/benchmark_cases.py` 已超过 7000 行，case metadata、solve/trace/verify 代码和 case 聚合混在同一文件。
- `tests/benchmark_regression.py` 已接近 4000 行，Phase 12/13 合同测试、benchmark 元数据测试、报告测试和 release gate 测试混在同一文件。

建议涉及文件：

- `algolab/verification/process_validator.py`
- `algolab/verification/process_families/`
- `tests/benchmark_cases.py`
- `tests/benchmark_families/`
- `tests/benchmark_regression.py`
- `tests/regression/`
- `docs/07_ROADMAP_AND_TASKS.md`

拆分方案：

1. `process_validator.py` 只保留稳定入口和总调度：
   - `ProcessFamilyRegistration`
   - `PROCESS_VALIDATION_REGISTRY`
   - `process_validation_registry()`
   - `process_validation_profile_for_family()`
   - `process_failure_type_for_message()`
   - `validate_process()`
   - 公共 level / failure type 常量。
2. 新增 `algolab/verification/process_families/common.py`：
   - target/ref/state 解析 helper。
   - 数字、图边、树节点、字符串窗口等跨 family 复用的小工具。
   - 不放任何具体算法族策略。
3. 新增 `algolab/verification/process_families/dp.py`：
   - DP contract、house robber、unique paths、subset sum、LCS、编辑距离、背包、区间 DP、状态压缩 DP、数位 DP 相关校验。
4. 新增 `algolab/verification/process_families/graph.py`：
   - graph contract、BFS/DFS/连通分量、拓扑、二分图、最短路、MST 相关校验。
5. 新增 `algolab/verification/process_families/array_pointer.py`：
   - 二分答案、双指针、滑动窗口、前缀和、差分、快慢指针相关校验。
6. 新增 `algolab/verification/process_families/string.py`：
   - KMP、Rabin-Karp、Z Algorithm、Manacher、字符串滑动窗口、Trie 前缀路径相关校验。
7. 新增 `algolab/verification/process_families/tree_range_math.py`：
   - 当前已存在的树、区间结构、数学位运算、图高级和回溯类校验先集中迁移到一个模块；后续 P13.5-P13.7 再按 family 继续细分。
8. `tests/benchmark_cases.py` 只保留：
   - `BenchmarkInput`
   - `BenchmarkCase`
   - `_metadata_for_case()`
   - `benchmark_cases()` 聚合入口。
9. 新增 `tests/benchmark_families/`：
   - `array_pointer.py`
   - `dp.py`
   - `graph.py`
   - `string.py`
   - `tree_range_math.py`
   - 每个模块导出 `cases() -> tuple[BenchmarkCase, ...]`。
10. `tests/benchmark_regression.py` 保留 `run_all()` 和兼容入口；把大块测试迁移到 `tests/regression/`：
    - `trace_contracts.py`
    - `phase13_families.py`
    - `benchmark_metadata.py`
    - `reports_and_gates.py`
    - 原测试函数名尽量保留，避免历史定位失效。

执行顺序：

1. 先拆 `process_validator.py`，只移动函数和 import，不改函数体逻辑。
2. 跑 `py_compile` 和 process validator 相关回归，确认导入路径正确。
3. 再拆 `tests/benchmark_cases.py`，保持 `benchmark_cases()` 返回顺序、case id、sample 数完全不变。
4. 用脚本打印拆分前后的 `(case_count, sample_count, case_ids)`，确认没有丢 case 或改顺序。
5. 最后拆 `tests/benchmark_regression.py`，保留 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression` 兼容入口。
6. 全量跑 family、boundary、release gate 和 quality checks。

约束：

- 不新增算法族。
- 不新增 benchmark case 或 sample。
- 不修改 renderer。
- 不修改 LLM prompt 行为，除非只是 import 路径说明。
- 不改变现有错误文本；如果必须调整错误文本，需要在完成证据中逐条说明原因。
- 不把拆分任务和 P13.5 功能实现混在一起。

验收标准：

- 以下公开 import 继续可用：
  - `from algolab.verification.process_validator import validate_process`
  - `from algolab.verification.process_validator import process_validation_registry`
  - `from tests.benchmark_cases import benchmark_cases`
- `benchmark_cases()` 的 case 数、sample 数和 case id 顺序与拆分前一致。
- `process_validator.py`、`tests/benchmark_cases.py`、`tests/benchmark_regression.py` 行数明显下降。
- `algolab/verification/process_families/` 和 `tests/benchmark_families/` 的模块边界清晰，单个文件不继续承载多个不相关 family 的新增逻辑。
- P13.1-P13.4 已有验证继续通过。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/verification/process_validator.py tests/benchmark_cases.py tests/benchmark_regression.py
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

完成证据：

- 拆分前核心长文件行数：`process_validator.py` 4868 行、`tests/benchmark_cases.py` 7027 行、`tests/benchmark_regression.py` 3858 行。
- 拆分后核心入口行数：`process_validator.py` 559 行、`tests/benchmark_cases.py` 679 行、`tests/benchmark_regression.py` 71 行。
- 新增 `algolab/verification/process_families/`：`common.py` 放公共 target/state/helper，`array_pointer.py`、`dp.py`、`graph.py`、`string.py` 放已完成 strong family 校验，`contracts.py` 放 Phase 12 family contract 校验，`tree_range_math.py` 暂存树、区间结构、数学位运算、图高级和回溯等既有校验，供 P13.5-P13.7 继续细分。
- 新增 `tests/benchmark_families/`：按 family 拆出 `array_pointer.py`、`dp.py`、`graph.py`、`string.py`、`tree_range_math.py`，每个模块导出 `cases()`。
- 新增 `tests/regression/`：拆出 `trace_contracts.py`、`phase13_families.py`、`benchmark_metadata.py`、`reports_and_gates.py` 和共享 `helpers.py`；`tests/benchmark_regression.py` 保留 `run_all()` 和 `-m` 兼容入口。
- `benchmark_cases()` 在 P13.4.5 等价拆分时保持 58 cases / 175 samples，case id 顺序哈希保持 `4ee2bfa63281410716bf5a56839892a24b7c829e5e3be1caaeee11fbf008c42e`；P13.5 扩样例后当前样例数见 P13.5 完成证据。
- `tests.benchmark_cases` 继续 re-export `UNIQUE_PATHS_CODE` 和 `UNIQUE_PATHS_TRACKER`，兼容 `tests.tracer_regression` 的既有公开导入入口。
- 新增 `test_phase13_long_files_are_split_without_changing_public_contracts()`，覆盖新模块导入、公开入口、legacy constant re-export、case 数 / sample 数 / 顺序哈希和核心入口行数。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... import tests.tracer_regression ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.tracer_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/verification/process_validator.py algolab/verification/process_families/*.py tests/benchmark_cases.py tests/benchmark_families/*.py tests/benchmark_regression.py tests/regression/*.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py`。
- 本轮只做等价拆分；未新增算法族、未新增 benchmark case/sample、未修改 renderer 或 HTML runtime。

### P13.5 树、回溯、Trie 和堆 validator

状态：已完成。

建议涉及文件：

- `algolab/verification/process_validator.py`
- `tests/benchmark_cases.py`
- `tests/benchmark_regression.py`

范围：

- 树遍历、BST、LCA、树直径、树形 DP。
- 回溯排列、组合、N 皇后、子集、数独入门。
- Trie 插入、查询、前缀计数。
- 堆、TopK、双堆中位数。

校验重点：

- recursion frame enter/exit 成对。
- 子树返回值聚合正确。
- choose/undo 状态连续。
- used/path 不跳变。
- heap property。
- trie path 和 count/terminal 一致。

验收标准：

- 树 family core 至少 18 个 samples。
- 回溯 family core 至少 12 个 samples。
- 堆/Trie 至少各 8 个 samples。
- 递归跳帧、撤销缺失、heap property 错误、trie count 错误反例失败。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- 新增 `heap`、`trie`、`backtracking` process profile；`tree` profile 增加 `_validate_recursion_frame_balance`，阻塞递归 frame 未进入退出、跳帧退出和缺少 exit。
- `algolab/verification/process_families/tree_range_math.py` 新增 `_validate_recursion_frame_balance` 和 `_validate_trie_prefix_count`；堆继续复用 `_validate_heap_property`；回溯继续复用 family contract 的 `path/used` 连续性和 recursion tree 结构校验。
- `tests/benchmark_families/tree_range_math.py` 扩充现有 P13.5 cases，不新增 case：树相关 18 samples（`tree_bst_lca` 14 + `tree_dp` 4）、回溯 12 samples、堆 8 samples、Trie 8 samples；当前 deterministic benchmark 为 58 cases / 207 samples。
- `benchmark/family_capabilities.json` 将 `heap_topk_huffman`、`trie`、`backtracking_recursion` 从 `uncovered/basic` 提升为 strong process profile 支撑的 `medium_plus`，并同步样例阈值；`tree_bst_lca` / `tree_dp` 样例阈值同步到 18 samples 合计。
- `tests/regression/phase13_families.py` 新增 `test_phase13_tree_backtracking_trie_heap_validator_expands_samples_and_rejects_process_errors()`，覆盖样例阈值、profile 注册、递归跳帧、回溯 used/path 跳变与缺 exit、heap property 错误和 Trie prefix_count 错误反例。
- `benchmark/boundary_cases.json`、`benchmark/benchmark_cases_list.md`、`docs/06_EVALUATION_AND_BENCHMARK.md` 已同步 207 samples 口径和 P13.5 新增边界样例说明。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... P13.5 samples execute and validate ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/verification/process_validator.py algolab/verification/process_families/*.py tests/benchmark_cases.py tests/benchmark_families/*.py tests/benchmark_regression.py tests/regression/*.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate`。
- 本轮未修改 renderer、HTML runtime 或 LLM HTML 生成路径；新增能力仍只通过 SemanticTrace -> validator -> SceneGraph 链路表达。

### P13.6 哈希、排序、链表、贪心 validator

状态：已完成。

建议涉及文件：

- `algolab/verification/process_validator.py`
- `tests/benchmark_cases.py`
- `tests/benchmark_regression.py`

范围：

- 哈希表、集合、频次统计、前缀和计数。
- 插入、归并、快排分区、快速选择、计数排序。
- 反转链表、合并链表、环检测、LRU 基础。
- 区间贪心、跳跃游戏、Huffman。

校验重点：

- map 命中前必须已写入。
- 排序过程维护局部不变量。
- 链表指针重连状态连续。
- 贪心排序依据和选择状态可追踪。

验收标准：

- 哈希从 fallback 升级到至少 medium+。
- 排序从 medium 升级到 medium+。
- 链表从 basic/planned 升级到 medium。
- 贪心从 basic 升级到 medium+。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- 新增 `algolab/verification/process_families/hash_sort_linked_greedy.py`，注册并启用 `hash`、`sorting`、`linked_list`、`greedy` 过程校验：Two Sum 的 map 写入/命中顺序，插入排序有序前缀和多重集保持，链表 current/prev/next 重连连续性，跳跃游戏 reach 局部最优更新。
- `algolab/verification/process_validator.py` 中 `hash` 从 fallback 升级为 strong / algorithm，并新增 strong profile：`sorting`、`linked_list`、`greedy`；错误分类覆盖哈希、排序、链表和贪心关键 token。
- `tests/benchmark_families/hash_sort_linked_greedy.py` 新增并接入 4 个 family core cases / 12 samples：`two_sum`、`insertion_sort`、`reverse_linked_list`、`jump_game`；当前 deterministic benchmark 为 60 cases / 213 samples，case id 顺序哈希为 `2858686a9dd7a35e9d11d62c4d2166a5e95cdcd3a30c6853c82c7e106645f975`。
- `tests/benchmark_cases.py` 已同步 metadata：`hash_map` / `sorting` 为 `medium_plus`，`linked_list_cache` 为 `medium`，`greedy` 为 `medium_plus`；`benchmark/family_capabilities.json` 和 `benchmark/boundary_cases.json` 已同步 P13.6 family capability 与边界样例。
- `tests/regression/phase13_families.py` 新增并通过 `test_phase13_hash_sorting_linked_list_greedy_validator_upgrades_profiles_and_rejects_process_errors()`，覆盖 profile 升级、样例阈值、capability 口径，以及哈希未写入即命中、插入排序有序前缀错误、链表跳过 current 重连、跳跃游戏 reach 错误等反例。
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`、`docs/06_EVALUATION_AND_BENCHMARK.md`、`benchmark/benchmark_cases_list.md` 和 `algolab/generation/prompts/tracker_system.txt` 已同步 P13.6 trace contract、过程校验注册表、benchmark 清单和 tracker prompt 约束。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... P13.6 focused regression ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... P13.6 materialize samples ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/verification/process_validator.py algolab/verification/process_families/*.py tests/benchmark_cases.py tests/benchmark_families/*.py tests/benchmark_regression.py tests/regression/*.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py`。
- 本轮未修改 renderer、HTML runtime 或 LLM HTML 生成路径；链表视觉仍按文档允许的 `nodes` / `edges` / `pointer` 组合表达进入 SceneGraph。

### P13.7 数学、几何、区间结构、图高级 validator

状态：已完成。

建议涉及文件：

- `algolab/verification/process_validator.py`
- `tests/benchmark_cases.py`
- `tests/benchmark_regression.py`

范围：

- GCD、快速幂、筛法、组合数、bitmask、lowbit。
- 凸包、方向判断、线段相交、扫描线基础。
- 线段树、树状数组、稀疏表。
- Tarjan、割点桥、二分图匹配、Edmonds-Karp。

校验重点：

- 数学表和状态转移可复核。
- 几何 cross/orientation 正确。
- 区间 query/update 路径正确。
- dfn/low、match、flow/capacity 不变量正确。

验收标准：

- 每个族至少保持当前 strong 或 medium+ 能力，不因扩展降低。
- 网络流只做教学版小图强校验，大图可 fallback 但必须标记。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- `algolab/verification/process_validator.py` 已注册 `range_structure`、`geometry`、`math_bit`、`advanced_graph` strong process profile；P13.7 本轮将 `geometry_sweep` 从 `uncovered/basic` 升级为 `geometry/medium_plus`，并把 `_validate_convex_hull` 接入 algorithm invariant。
- `algolab/verification/process_families/tree_range_math.py` 覆盖区间结构、数学位运算、图高级和凸包几何校验：线段树 / 树状数组 / 稀疏表，GCD / 快速幂 / 筛法 / 组合数 / bitmask / lowbit，Tarjan / 割点桥 / 二分图匹配 / Edmonds-Karp，以及凸包点引用和 hull 一致转向。
- `tests/benchmark_cases.py` 中 `convex_hull` 已同步为 `support_level=medium_plus`、`process_profile=geometry`；`benchmark/family_capabilities.json` 中 `geometry_sweep` 已同步为 `current_level=medium_plus`、`process_profile=geometry`、`fallback_boundaries=[]`。
- `tests/regression/phase13_families.py` 新增并接入 `test_phase13_math_geometry_range_advanced_graph_validator_upgrades_geometry_and_preserves_profiles()`，覆盖 geometry profile 升级、range/math/advanced_graph 不降级、capability 口径和错误 hull 顺序反例。
- 当前 deterministic benchmark 保持 60 cases / 213 samples；`convex_hull` 2 个样例已 materialize 且 `release_ready=True`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... P13.7 focused regression ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... convex_hull materialize samples ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate`。
- 本轮未修改 renderer、HTML runtime 或 LLM HTML 生成路径；几何、区间、数学和网络流仍只通过 SemanticTrace -> validator -> SceneGraph 链路表达，未引入 `range:`、`number:`、`interval:` 或 `flow:` target。

## Phase 14：Demo Readiness Gate

目标：

- 证明页面演示语义正确，而不是只证明答案正确。
- 该阶段仍不追求视觉 polish，只检查演示是否能讲清算法且不误导。

### P14.1 Demo readiness schema

状态：已完成。

建议涉及文件：

- `algolab/schemas/`
- `algolab/verification/demo_readiness.py`
- `algolab/pipeline.py`
- `tests/benchmark_regression.py`

检查项：

- 每个关键帧有 `operation` 或 `op`。
- 每个关键帧有 `reason`。
- 涉及转移的关键帧有 `deps`。
- `state` 能复原当前可视化对象。
- 关键阶段标签存在：初始化、主循环、转移/访问、答案。
- 不能有“算法名和过程矛盾”的明显错误，例如 BFS trace 解释成 DFS。

验收标准：

- 输出 `demo_readiness.status`：`pass`、`warn`、`fail`。
- family core 中 `demo_required=true` 的 case 必须 pass。
- expansion case 可以 warn，但不能 fail 后进入 dashboard 强展示。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- 新增 `algolab/schemas/demo_readiness.py`，定义 `DemoReadinessReport`、`DemoReadinessVariantReport` 和 `status=pass|warn|fail`。
- `algolab/schemas/validation.py` 的 `ValidationReport` 已包含 `demo_readiness`，BuildArtifact JSON 可直接暴露演示语义门禁结果。
- 新增 `algolab/verification/demo_readiness.py`，P14.1 先做通用 schema 级检查：关键帧 reason/state、明显 deps 缺失、初始化/答案阶段、退化输入短路径、BFS/DFS 明显矛盾；族级严格规则留到 P14.2。
- `algolab/pipeline.py` 在 process validation 之后、SceneGraph 编译之前执行 demo readiness；`fail` 会进入 validation errors 并阻塞 release gate，不让缺演示证据的产物进入发布链路。
- `tests/regression/reports_and_gates.py` 新增并接入 `test_demo_readiness_schema_passes_family_core_and_blocks_missing_demo_evidence()`，覆盖 `unique_paths` 正例和缺 reason/deps/state 的失败路径。
- 60 个 `demo_required=true` deterministic cases 的首样本 demo readiness 均为 `pass`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/schemas/demo_readiness.py algolab/schemas/validation.py algolab/verification/demo_readiness.py algolab/pipeline.py tests/regression/reports_and_gates.py tests/benchmark_regression.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... demo_required_first_sample_cases ... PY`，输出 `demo_required_first_sample_cases 60`、`failures []`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate`。
- 本轮未修改 renderer、HTML runtime 或 LLM HTML 生成路径；Renderer 仍只消费 SceneGraph / BuildArtifact，demo readiness 只读取已执行得到的 SemanticTrace。

### P14.2 族级演示完整性规则

状态：已完成。

建议涉及文件：

- `algolab/verification/demo_readiness.py`
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`
- `docs/06_EVALUATION_AND_BENCHMARK.md`

按族检查：

- DP：初始化、转移、公式、答案位置。
- 图：frontier/visited、边检查、首次访问或 relax。
- 二分/窗口：当前窗口、比较、移动原因。
- 单调栈：push/pop、被弹元素贡献。
- 字符串：指针、表项、失配或扩展原因。
- 树/回溯：进入、选择、返回、撤销。
- 堆/并查集：结构变化前后和不变量。

验收标准：

- 每个 strong 算法族至少有一个 demo readiness 正例和一个反例。
- 失败分类进入 evaluation report：`demo_missing_reason`、`demo_missing_deps`、`demo_state_jump`、`demo_algorithm_mismatch`。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_report.py --output-dir output/evaluation --manifest output/evaluation/evaluation_manifest.json --dashboard output/dashboard/dashboard.json
```

完成证据：

- `algolab/verification/demo_readiness.py` 已在 P14.1 通用 schema 检查之上新增族级演示完整性规则，覆盖 DP、图、二分 / 窗口、单调栈、字符串 / Trie、树 / 回溯 / 递归、堆和并查集。
- DP 演示检查初始化、转移写入、转移 deps、公式证据和 `answer_position`；图演示检查 frontier / visited / dist / color / indegree / union-find 等过程状态、边检查、首次访问或 relax deps；二分检查 mid 状态、mid 比较帧和无比较证据的区间跳变；窗口检查边界或聚合状态；单调栈检查 push / pop、pop deps 和被弹元素贡献写入；字符串检查指针、表项 / 哈希 / 半径 / 前缀计数，并允许空 pattern、空 text、pattern 长于 text 的合法短路径；递归 / 回溯检查 enter / exit 和撤销；堆检查 `heap_type`、heap state 和 `heap_top`；并查集检查 union 后结构状态。
- 当前 deterministic benchmark 为 60 cases / 213 samples；`process_validation_registry()` 中 20 个 strong process profile 均有对应 benchmark case 可作为 demo readiness 正例。
- `tests/regression/reports_and_gates.py` 新增 P14.2 覆盖：所有 strong profile 正例通过，并对每个 profile 构造缺 reason 反例；族级反例覆盖 DP 缺公式 / 答案引用、BFS 缺边 / deps、二分状态跳变、单调栈缺 pop deps、KMP 缺表项、回溯缺撤销、堆缺不变量、并查集 union 后缺结构状态。
- P14.2 合法边界正例覆盖拓扑排序 `indegree[...]` + `edge:u->v` deps、二分图染色不被误判为二分查找、Kruskal MST 的 `union_find` / `mst_edges` 过程状态、空 pattern 和 pattern 长于 text 的字符串短路径。
- `scripts/run_llm_benchmark.py` 的 `classify_failure()` 明确识别 `demo_missing_reason`、`demo_missing_deps`、`demo_state_jump`、`demo_algorithm_mismatch`；`scripts/build_evaluation_report.py` 会从 `failure_type=` marker 聚合 failure summary，合成 LLM report 测试已验证这些 demo failure type 进入 `evaluation_report.json` 和 `evaluation_failure_types.csv`。
- `tests.benchmark_cases` 继续 re-export `UNIQUE_PATHS_CODE` 和 `UNIQUE_PATHS_TRACKER`，兼容 `tests.tracer_regression` 的既有公开导入入口，不修改 `tests/tracer_regression.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... import tests.tracer_regression ... PY`，确认 `UNIQUE_PATHS_CODE` / `UNIQUE_PATHS_TRACKER` 可从 `tests.benchmark_cases` 导入。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.tracer_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... P14.2 focused demo readiness tests ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/verification/demo_readiness.py tests/regression/reports_and_gates.py tests/benchmark_cases.py tests/tracer_regression.py tests/benchmark_regression.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_report.py --output-dir output/evaluation --manifest output/evaluation/evaluation_manifest.json --dashboard output/dashboard/dashboard.json`。
- 真实 `output/evaluation/evaluation_report.json` 的 `failure_type_summary` 由当前真实 LLM benchmark report 输入决定；本轮不伪造真实 LLM 失败数据，demo failure type 进入 evaluation report 的链路由合成 LLM report 回归测试覆盖。
- 本轮未修改 renderer、HTML runtime 或 LLM HTML 生成路径；demo readiness 只读取已执行得到的 SemanticTrace，Renderer 仍只消费 SceneGraph / BuildArtifact。

### P14.3 Dashboard 展示算法族正确性

状态：已完成。

建议涉及文件：

- `scripts/build_demo_dashboard.py`
- `algolab/renderer/`
- `output/dashboard/`
- `tests/browser_smoke.py`

目标：

- dashboard 不只展示页面链接，还展示算法族能力等级。
- 每个算法族显示 answer/process/demo/scene/html 五列状态。
- fallback/uncovered 必须显眼，不得和 strong 混在一起。

验收标准：

- dashboard 能按 family、support level、gate layer 过滤。
- 每个 case 能打开 artifact、validation report、demo readiness report。
- browser smoke 覆盖 dashboard 的 family summary。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_demo_dashboard.py --output-dir output/dashboard --style both
```

如果本轮修改了 renderer、HTML runtime 或 dashboard 浏览器交互，再额外运行目标 browser smoke。Phase 14 收尾或合并前再运行：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py
```

完成证据：

- `scripts/build_demo_dashboard.py` 现在为每个 demo 写出 `demo_readiness_report.json`，dashboard record 暴露 `artifact_json`、`validation_report_json`、`demo_readiness_report_json` 三类可打开证据链接。
- dashboard record 新增 `layer_statuses`，按 `answer/process/demo/scene/html` 五层从既有 `BuildArtifact.validation.release_gate`、`demo_readiness` 和实际 HTML 导出链接派生状态；不修改 trace、SceneGraph 或 renderer 主链路。
- `family_coverage` 聚合 `gate_statuses`、`current_level`、`target_level`、`process_status`、`process_failure_type` 和 `fallback_boundaries`，从 `benchmark/family_capabilities.json` 与 process registry 显示算法族能力等级和 fallback/uncovered 边界。
- dashboard HTML 的 family summary 显示“算法族能力等级”，包含 Answer / Process / Demo / Scene / HTML 五层状态和 “Fallback / uncovered” 列；demo 卡片显示五层状态并新增 `demo readiness` 链接。
- dashboard 过滤器支持 family、support level、gate layer 和状态；卡片包含 `data-support-level`，browser smoke 覆盖 support level 过滤和 artifact / validation / demo readiness 链接。
- `tests/regression/reports_and_gates.py` 的 `test_demo_dashboard_exposes_phase14_family_layer_statuses_and_reports()` 覆盖 dashboard JSON 字段、报告文件落盘和 HTML 文案；`tests/benchmark_regression.py` 已接入该测试。
- `tests/browser_smoke.py` 增强 `_check_demo_dashboard_filtering_and_links()`，覆盖 dashboard family summary、support level 过滤和三类证据链接。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... test_demo_dashboard_exposes_phase14_family_layer_statuses_and_reports ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile scripts/build_demo_dashboard.py tests/browser_smoke.py tests/benchmark_regression.py tests/regression/reports_and_gates.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_demo_dashboard.py --output-dir output/dashboard --style both`，输出 `output/dashboard/index.html`。
- 已通过：`bash scripts/run_browser_smoke_container.sh`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression`。
- 已通过：`bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py`。
- 本轮未修改 renderer、HTML runtime 或 LLM HTML 生成路径；dashboard 只展示已生成 artifact / validation / capability registry 证据，Renderer 仍只消费 SceneGraph / BuildArtifact。

## Phase 15：LLM Benchmark 和 Repair 泛化

目标：

- 在 deterministic benchmark 稳定后，评估真实 LLM 对算法族 trace contract 的遵循程度。
- repair 不只是修 schema，而要能根据族级错误修复过程。

### P15.1 LLM benchmark family split

状态：已完成。

建议涉及文件：

- `scripts/run_llm_benchmark.py`
- `benchmark/llm_family_sets.json`
- `docs/06_EVALUATION_AND_BENCHMARK.md`
- `tests/benchmark_regression.py`

目标：

- LLM benchmark 按 family/subfamily 分层抽样。
- 每个族至少包含 seen-style 和 unseen-style 题目。
- 报告每个族的生成成功率、repair 成功率、失败类型。

验收标准：

- 输出 `output/llm_benchmark/family_summary.json`。
- 支持 `--family`、`--gate-layer`、`--limit-per-family`。
- LLM benchmark 失败不影响 deterministic release gate，但影响真实产品能力评分。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py --output-dir output/llm_benchmark --condition algolab_full --limit-per-family 1
```

论文实验冻结或 Phase 15 收尾时再运行不带 limit 的完整 LLM benchmark。

完成证据：

- 新增 `benchmark/llm_family_sets.json`，覆盖当前 deterministic benchmark 的所有 `family_id`，并按 sample style 标记 `seen_style` / `unseen_style`。
- `scripts/run_llm_benchmark.py` 支持 `--family`、`--gate-layer`、`--limit-per-family` 和 `--family-sets`，抽样时按 family / subfamily 做稳定分层限量。
- LLM benchmark 每条结果写入 `family_id`、`subfamily_id`、`gate_layer`、`support_level`、`process_profile` 和 `case_style`。
- `write_report()` 同步输出 `output/llm_benchmark/family_summary.json`，按 family 汇总生成成功率、repair 成功率、失败类型、subfamily、gate layer 和 seen / unseen style 分布。
- `tests/regression/reports_and_gates.py` 新增 P15.1 回归，覆盖 family set 配置、family / gate 过滤、每族限量抽样和 family summary 输出。
- `docs/06_EVALUATION_AND_BENCHMARK.md` 与 `benchmark/README.md` 已同步 LLM family split 运行方式和输出路径。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile scripts/run_llm_benchmark.py tests/regression/reports_and_gates.py tests/benchmark_regression.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... test_llm_benchmark_family_split_selection_and_summary ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... validate_llm_family_sets(load_llm_family_sets()) ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression`。
- 已通过：`git diff --check -- scripts/run_llm_benchmark.py tests/regression/reports_and_gates.py tests/benchmark_regression.py benchmark/llm_family_sets.json docs/06_EVALUATION_AND_BENCHMARK.md benchmark/README.md docs/07_ROADMAP_AND_TASKS.md`。
- 未运行真实 LLM benchmark 全量命令；该命令会调用外部模型，论文实验冻结或 Phase 15 收尾时再按模型配置执行。

### P15.2 族级 Repair Prompt

状态：已完成。

建议涉及文件：

- `algolab/generation/repair.py`
- `algolab/verification/repair_context.py`
- `algolab/generation/prompts/`
- `tests/benchmark_regression.py`

目标：

- repair prompt 能区分：答案错误、trace 跳步、deps 错、process invariant 错、demo readiness 错。
- 对 DP、图、字符串、树、回溯等族给出具体修复指令。

验收标准：

- 构造反例能生成明确 repair context。
- repair context 不要求 LLM 直接改 HTML。
- 失败类型保留在报告中，不能被 repair 吞掉。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- 新增 `algolab/generation/repair.py`，集中构造 solution repair prompt，把结构化错误上下文、族级修复要求和原始错误信息稳定传给 repair LLM。
- `algolab/verification/repair_context.py` 扩展 repair context，保留原始 `failure_type`，并新增 `repair_category`、`repair_instruction`、`family`、`family_guidance` 和 `forbidden_actions`。
- repair context 现在能区分答案一致性、trace schema、trace 跳步、target / deps、process invariant、coverage、demo readiness、scene binding 和 execution 等修复类别。
- 针对 DP、图、字符串、树、回溯、数组指针和数据结构族提供族级修复指导；未知族保持 schema / target / deps / state 的保守修复指导。
- `algolab/generation/prompts/repair_system.txt` 已同步 P15.2 规则，明确 demo readiness failure type、repair_category、family_guidance 和禁止直接生成 HTML / CSS / JS。
- `tests/regression/reports_and_gates.py` 新增并接入 `test_phase15_family_repair_context_and_prompt_distinguish_failure_categories()`，覆盖答案错误、trace schema、trace 跳步、deps 错、process invariant 和 demo readiness 反例上下文，以及 prompt 中的族级 DP 指导和 HTML 禁止项。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/verification/repair_context.py algolab/generation/repair.py algolab/generation/solution_generator.py tests/regression/reports_and_gates.py tests/benchmark_regression.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... test_phase15_family_repair_context_and_prompt_distinguish_failure_categories ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression`。
- 本轮未运行真实 LLM repair；测试使用 fake `chat_json` 验证 prompt 内容和 failure type 保留，不调用外部模型。

### P15.3 Unseen family evaluation

状态：已完成。

建议涉及文件：

- `benchmark/unseen_family_cases.json`
- `scripts/run_llm_benchmark.py`
- `scripts/build_evaluation_report.py`

目标：

- 证明系统不是只记住 deterministic case。
- 对每个强支持族准备未进入 deterministic fixture 的题目描述和样例输入。

验收标准：

- unseen case 不允许共享 deterministic tracker 代码。
- 只允许通过 LLM 生成、repair、校验和编译链路。
- 报告区分 seen-style 和 unseen-style。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py --output-dir output/llm_benchmark_unseen --condition algolab_full --case-set unseen --limit-per-family 1
```

Phase 15 收尾时再运行完整 unseen family evaluation。

完成证据：

- 新增 `benchmark/unseen_family_cases.json`，覆盖当前 `benchmark/family_capabilities.json` 中所有 `current_level=strong` 的 family；每条 unseen case 只包含题目描述、family / subfamily 元数据、样例输入和 expected output。
- unseen registry 和 loader 会拒绝 `code`、`tracker_code`、`verifier_code` 字段，case id 不能与 deterministic fixture 重名，且 `gate_layer` 固定为 `llm_eval`、`support_level` 固定为 `strong`。
- `scripts/run_llm_benchmark.py` 新增 `--case-set deterministic|unseen` 和 `--unseen-cases`，`case_set=unseen` 时只从 unseen registry 构造 `ProblemInput`，仍走 LLM 生成、repair、sandbox 执行、校验、SceneGraph compiler 和 renderer 链路。
- LLM benchmark result / report / `family_summary.json` 现在写入并聚合 `case_set`、`case_style`、`case_set_summary` 和 `case_style_summary`；unseen case 固定标记为 `case_style=unseen_style`。
- `scripts/build_evaluation_report.py` 新增 `case_style_summary` 和 `evaluation_case_styles.csv`，评估报告 Markdown 增加 Seen / Unseen Style Summary，区分 seen-style 与 unseen-style。
- `tests/regression/reports_and_gates.py` 新增并接入 `test_phase15_unseen_family_cases_are_independent_and_reported()`，覆盖 strong family registry 覆盖、禁止代码字段、unseen 选择不共享 deterministic tracker、request metadata、LLM report 聚合和 evaluation report 聚合。
- `docs/06_EVALUATION_AND_BENCHMARK.md` 与 `benchmark/README.md` 已同步 unseen family evaluation 运行命令、registry 边界和报告字段。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile scripts/run_llm_benchmark.py scripts/build_evaluation_report.py tests/regression/reports_and_gates.py tests/benchmark_regression.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m json.tool benchmark/unseen_family_cases.json`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... validate_unseen_family_cases(load_unseen_family_cases()) ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... test_phase15_unseen_family_cases_are_independent_and_reported ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression`。
- 本轮未运行真实 unseen LLM evaluation；该命令会调用外部模型，Phase 15 收尾或论文实验冻结时按模型配置运行完整命令。
- 本轮未修改 renderer、HTML runtime 或 LLM HTML 生成路径；Renderer 仍只消费 SceneGraph / BuildArtifact，unseen case 不能绕过 SemanticTrace、validator 和 SceneGraph compiler。

## Phase 16：算法族覆盖扩容

目标：

- 在 family registry、oracle、trace contract、process validator 和 demo readiness gate 都稳定后，扩充覆盖面。
- 扩容不以视觉效果为主要验收标准。

### P16.1 Core families 扩到 160 到 220 samples

状态：已完成。

范围：

- DP。
- 数组指针与前缀结构。
- 图基础。
- 字符串。
- 树。
- 单调结构。
- 并查集。
- 区间结构。

验收标准：

- `family_core` 和 `smoke` 全通过。
- strong family 的 process pass rate 为 100%。
- demo_required case 全部 demo readiness pass。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate
```

Phase 16 收尾或准备提交时再运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

完成证据：

- 当前 deterministic benchmark 已达到 P16.1 的 160 到 220 samples 窗口：`scripts/check_family_release_gate.py --output-dir output/release_gate` 输出 `60 cases / 213 samples`。
- family release gate summary 新增 `gate_layer_samples`，报告明确区分 gate layer 的 case 数与 sample 数；当前 `gate_layers={"family_core": 60}`，`gate_layer_samples={"family_core": 213}`。
- family release gate 结果为 `overall_ready=True`，`answer_pass_rate=1.0`，`process_pass_rate=1.0`，`demo_readiness_pass_rate=1.0`，`process_fallback_cases=0`，`process_uncovered_cases=0`。
- P16.1 范围内的 DP、数组指针与前缀结构、图基础、字符串、树、单调结构、并查集和区间结构均有 deterministic family_core case，且 answer / process / demo readiness 全部通过。
- `tests/regression/reports_and_gates.py` 新增并接入 `test_phase16_core_family_sample_window_and_gates_are_ready()`，覆盖 160 到 220 sample 窗口、family_core 样例层、P16.1 范围 family 存在性、strong family process 100%、fallback / uncovered 为 0、demo_required 全部 ready。
- `docs/06_EVALUATION_AND_BENCHMARK.md` 已同步 family release gate 输出 `gate_layer_samples` 的说明。
- 本轮没有为制造样例数而追加 benchmark samples；原因是当前 213 deterministic samples 已满足 P16.1 窗口，直接追加会冲破现有 V1 release gate 的 220 sample 上限。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile scripts/check_family_release_gate.py tests/regression/reports_and_gates.py tests/benchmark_regression.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... test_phase16_core_family_sample_window_and_gates_are_ready ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate`。
- Phase 16 收尾或提交前仍需运行完整 `scripts/run_quality_checks.py`；本轮聚焦 P16.1 的 family gate 闭环。
- 本轮未修改 renderer、HTML runtime 或 LLM HTML 生成路径；Renderer 仍只消费 SceneGraph / BuildArtifact。

### P16.2 Expansion families 扩到 250 到 350 samples

状态：已完成。

范围：

- 贪心。
- 最短路与 MST。
- 堆。
- Trie。
- 回溯。
- 数学与位运算。
- 几何。
- 链表与缓存。
- 图高级与网络流教学版。

验收标准：

- expansion case 允许部分 medium/basic，但必须准确报告。
- 不允许出现 silent pass 的 process_uncovered。
- 每个新增算法族至少有一个 dashboard 页面。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate
```

扩容批次完成后再运行全量质量检查。

完成证据：

- 新增 `expansion` gate layer 的 9 个 deterministic cases / 37 samples：`jump_game_expansion`、`dijkstra_shortest_path_expansion`、`kth_largest_expansion`、`trie_prefix_expansion`、`permutations_expansion`、`gcd_euclid_expansion`、`convex_hull_expansion`、`reverse_linked_list_expansion`、`edmonds_karp_expansion`。
- 当前 deterministic benchmark 为 `69 cases / 250 samples`，满足 P16.2 的 250 到 350 samples 窗口；family release gate summary 为 `gate_layers={"expansion": 9, "family_core": 60}`、`gate_layer_samples={"expansion": 37, "family_core": 213}`。
- P16.2 范围内的贪心、最短路 / MST、堆、Trie、回溯、数学与位运算、几何、链表与缓存、图高级均有至少 1 个 `expansion` case；answer / process / demo readiness 全部通过。
- 本轮没有把既有 `family_core` case 改成 `expansion`，P16.1 的 V1 baseline 仍保持 `family_core=213 samples`，V1 release gate 改为显式统计 `smoke` / `family_core` baseline 样本窗口，同时在报告中保留 deterministic 总样本数。
- `benchmark/llm_family_sets.json` 已同步新增 expansion cases，避免 LLM family split 对新增 deterministic case 出现配置缺口。
- `benchmark/benchmark_cases_list.md` 与 `docs/06_EVALUATION_AND_BENCHMARK.md` 已同步 69 cases / 250 samples、baseline 213 samples 和 expansion 分层口径。
- `tests/regression/reports_and_gates.py` 新增并接入 `test_phase16_expansion_family_samples_and_dashboard_pages_are_ready()`，覆盖 250 到 350 总样本窗口、expansion case/family 覆盖、`process_uncovered=0`、各 expansion family 的 answer/process/demo readiness 通过，以及每个 expansion family 至少生成一个 dashboard stable HTML 页面。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile tests/benchmark_cases.py tests/benchmark_families/expansion.py scripts/check_v1_release_gate.py tests/regression/reports_and_gates.py tests/regression/phase13_families.py tests/benchmark_regression.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... expansion materialize/process focused check ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... test_phase16_expansion_family_samples_and_dashboard_pages_are_ready ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_v1_release_gate.py --output-dir output/release_gate`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py --output-dir output/release_gate`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression`。
- Phase 16 收尾或提交前仍需运行完整 `scripts/run_quality_checks.py`；本轮聚焦 P16.2 的 deterministic expansion 和 family gate 闭环。
- 本轮未修改 renderer、HTML runtime 或 LLM HTML 生成路径；Renderer 仍只消费 SceneGraph / BuildArtifact。

### P16.3 算法族能力降级策略

状态：已完成。

建议涉及文件：

- `algolab/verification/`
- `scripts/build_evaluation_report.py`
- `docs/06_EVALUATION_AND_BENCHMARK.md`

目标：

- 当复杂变体无法强校验时，系统明确降级，不误报。
- 降级原因写入 report 和 Debug Drawer。

降级类型：

- `answer_only`：只有答案和 verifier 可靠。
- `schema_scene_only`：trace 可渲染但过程不强校验。
- `process_fallback`：有基础过程证据但无族级 invariant。
- `process_uncovered`：未覆盖算法族。
- `demo_warn`：可演示但缺少部分教学字段。

验收标准：

- 所有降级都可在 evaluation report 统计。
- strong family 的 family core 不允许降级。

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

完成证据：

- 新增结构化降级证据 `BuildArtifact.validation.degradations`，固定支持 `answer_only`、`schema_scene_only`、`process_fallback`、`process_uncovered`、`demo_warn`，每条记录包含降级原因、来源、affected variant 和 blocking 标记。
- `algolab/verification/degradation.py` 统一定义降级类型、trace profile 降级识别、LLM result 降级提取和计数工具；pipeline 会把未覆盖 process profile、schema/scene-only release 状态和 demo warning 写入 artifact validation。
- 稳定 HTML 的 Debug Drawer 新增 `Degradation policy` 区块，仍只读取 BuildArtifact / validation report，不让 renderer 直接消费 LLM HTML 或重新计算算法。
- `scripts/check_family_release_gate.py` 输出 `summary.degradation_summary`，并显式记录 strong family 的 `smoke` / `family_core` 降级拦截；当前 69 cases / 250 samples 的 process fallback / uncovered / degradation 计数均为 0。
- `scripts/build_evaluation_report.py` 输出 `degradation_summary` 和 `evaluation_degradations.csv`，可同时统计 LLM benchmark result 与 family release gate 中的五类降级。
- `docs/06_EVALUATION_AND_BENCHMARK.md` 已同步降级类型、输出位置和门禁规则。
- `tests/regression/reports_and_gates.py` 新增并接入 `test_phase16_degradation_policy_enters_evaluation_reports_and_artifact_debug()`，覆盖 LLM report 降级聚合、family gate 降级统计、evaluation CSV / Markdown 输出、artifact validation 降级字段和 Debug Drawer 展示。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/schemas/validation.py algolab/verification/degradation.py algolab/verification/demo_readiness.py algolab/pipeline.py algolab/renderer/export.py scripts/check_family_release_gate.py scripts/build_evaluation_report.py tests/regression/reports_and_gates.py tests/benchmark_regression.py`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... test_phase16_degradation_policy_enters_evaluation_reports_and_artifact_debug ... PY`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate`，`overall_ready=True`，`process_fallback_cases=0`，`process_uncovered_cases=0`，`degradation_summary` 五类计数均为 0。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression`。
- 已通过：`bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py`。
- 本轮未修改 LLM 直接生成 HTML 的边界；Renderer 仍只消费 BuildArtifact / SceneGraph / validation report 中的结构化证据。

## Phase 17：视觉和交互增强

目标：

- 在算法族正确性稳定后，提升页面教学质量。
- 视觉增强只消费已有 SceneGraph / BuildArtifact，不改变算法正确性来源。

### P17.1 族级视觉模式增强

状态：已完成。

范围：

- DP 依赖箭头、公式代入、状态表。
- 图 relax、frontier、路径高亮。
- 字符串双行对齐、回退弧线、窗口。
- 树递归帧、返回值气泡。
- 回溯递归树、选择/撤销动画。
- 区间结构 query/update 路径。
- 网络流 residual/capacity 边标签。

验收标准：

- 不新增算法名专用 renderer 分支。
- 所有增强通过 SceneGraph object/mark/arrow/meta 表达。
- browser smoke 覆盖每类核心视觉模式。
- 必须用真实浏览器生成并保存截图证据；不能只依赖 DOM 断言或静态 HTML 检查。截图至少覆盖 desktop 和 mobile 视口，以及 DP、图、字符串、树、回溯、区间结构、网络流代表页面。

本任务最小验证：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/capture_phase17_screenshots.py --output-dir output/phase17_screenshots
bash scripts/run_browser_smoke_container.sh
```

如果只改视觉文档或 SceneGraph meta，不改 HTML runtime，可只运行相关 renderer/offline regression。只要修改 renderer、HTML runtime、布局 CSS、交互 JS 或 dashboard 展示，就必须提交 `output/phase17_screenshots/phase17_screenshots.json` 中记录的截图路径和人工查看结论。Phase 17 收尾或合并前再运行全量质量检查。

完成证据：

- Scene Compiler 为 P17.1 七类模式补充通用 SceneObject / arrow `meta.visual_patterns`：DP 公式代入与依赖箭头、图 frontier / relax / path、字符串双行对齐 / 窗口 / 回退弧线、树递归返回值、回溯选择 / 撤销、区间结构 query / update / cover 路径、网络流 flow / capacity / residual 边标签。
- Renderer 新增通用 `renderVisualPatternPanel`、对象 meta class、图 / 树边标签和树返回值气泡；相关 runtime 只读取当前 frame 的 SceneGraph objects / marks / arrows / evidence，不读取算法名，不让前端重新计算算法答案。
- `tests/fixtures.py` 新增 `phase17_visual_pattern_artifact()` 和七类确定性视觉模式 fixture；`tests/offline_regression.py` 覆盖 SceneGraph meta 与 renderer runtime 无算法名分支；`tests/browser_smoke.py` 覆盖每类核心视觉模式的真实浏览器 DOM。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/compiler/scene_compiler.py algolab/renderer/export.py tests/fixtures.py tests/offline_regression.py tests/browser_smoke.py`。
- 已通过：P17.1 focused offline regression：`test_phase17_scene_compiler_emits_family_visual_pattern_meta()`、`test_phase17_renderer_declares_generic_visual_pattern_runtime()`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression`。
- 已通过：`bash scripts/run_browser_smoke_container.sh python scripts/capture_phase17_screenshots.py --output-dir output/phase17_screenshots`，manifest 为 `output/phase17_screenshots/phase17_screenshots.json`，`ok=true`，desktop / mobile 覆盖 `unique_paths`、`dijkstra_shortest_path`、`kmp`、`lca`、`permutations`、`segment_tree_range_sum`、`edmonds_karp`。
- 已通过：`bash scripts/run_browser_smoke_container.sh python -m tests.browser_smoke`。
- 人工查看：抽查 `output/phase17_screenshots/phase17_contact_sheet.jpg` 与 `segment_tree_range_sum_desktop.png`，代表页面非空，主视图、讲解区、时间线和 Debug Drawer 可辨；manifest 中全部截图文件非空且无 browser console / page error。
- 本轮未修改 LLM HTML 生成边界；Renderer 仍只消费 BuildArtifact / SceneGraph / validation report 中的结构化证据。

### P17.2 交互学习增强

状态：已完成。

范围：

- 预测下一步。
- 点击依赖对象。
- 公式展开。
- 错误选项解释。
- 解法对比。
- 输入修改后重新生成。

验收标准：

- 交互只读 trace，不在前端伪造新 trace。
- 输入修改必须回到 `ProblemInput -> BuildArtifact -> HTML` 主链路。
- 错误选项不能由 renderer 编造算法逻辑。
- 必须用真实浏览器截图或录屏式截图序列验证交互前后状态；至少保存交互前、点击/输入后、错误提示/反馈状态三类截图证据。

本任务最小验证：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/capture_phase17_screenshots.py --output-dir output/phase17_screenshots
bash scripts/run_browser_smoke_container.sh
```

交互功能阶段收尾或准备提交时再运行：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py
```

完成证据：

- `Interaction` schema 新增可选 `wrong_explanation` 和 `option_explanations`，错误选项解释由 trace / teaching 提供；renderer 只读取当前 SceneGraph frame 的 `interaction`、`teaching`、`evidence`，不按算法名推导错误原因。
- Renderer 新增公式展开控件，展示 `frame.teaching.formula`、`frame.evidence.targets/deps/value`、过程核对和 visual object meta 中的代入证据；展开动作只改变 DOM 展示，不修改 trace、SceneGraph 或 artifact。
- 现有预测下一步、依赖点击、解法对比和输入修改后重新生成入口继续保持只读约束：静态 HTML 只准备 `ProblemInput -> BuildArtifact -> HTML` artifact 输入，不在前端伪造新 trace。
- `tests/fixtures.py` 的黄金视觉矩阵补充 choice 错误选项解释；`tests/offline_regression.py` 覆盖结构化错误解释和公式展开 runtime 不读取算法名、不写 ARTIFACT；`tests/browser_smoke.py` 覆盖真实浏览器下公式展开、错误选项反馈来源、trace 不变性、依赖点击、解法对比和输入重新生成降级入口。
- `scripts/capture_phase17_screenshots.py` 的 manifest 新增 `interaction_screenshots`，保存 `before`、`after_click`、`after_input`、`error_feedback` 四类真实浏览器截图证据；默认 Phase 17 截图覆盖 desktop / mobile 的 `binary_search`、`unique_paths`、`dijkstra_shortest_path`、`kmp`、`lca`、`permutations`、`segment_tree_range_sum`、`edmonds_karp`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile algolab/schemas/semantic_trace.py algolab/renderer/export.py tests/fixtures.py tests/offline_regression.py tests/browser_smoke.py scripts/build_demo_dashboard.py scripts/capture_phase17_screenshots.py`。
- 已通过：P17.2 focused offline regression：`test_golden_visual_matrix_declares_prediction_interactions_for_core_examples()`、`test_renderer_declares_readonly_prediction_interactions()`、`test_renderer_declares_phase17_formula_expand_and_structured_wrong_feedback()`。
- 已通过：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression`。
- 已通过：`bash scripts/run_browser_smoke_container.sh python scripts/capture_phase17_screenshots.py --output-dir output/phase17_screenshots`，manifest 为 `output/phase17_screenshots/phase17_screenshots.json`，`ok=true`，交互截图包含 `interaction_formula_before`、`interaction_formula_expanded`、`interaction_regenerate_payload`、`interaction_wrong_feedback`。
- 已通过：`bash scripts/run_browser_smoke_container.sh python -m tests.browser_smoke`。
- 已通过：`bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py`，结果 `quality_checks: PASS`。
- 人工查看：抽查 `output/phase17_screenshots/phase17_interaction_formula_expanded_desktop.png` 和 `output/phase17_screenshots/phase17_interaction_wrong_feedback_desktop.png`，页面非空，公式展开来源、输入重新生成降级提示和错误选项解释反馈可辨。
- 本轮未修改 LLM 直接生成 HTML 的边界；Renderer 仍只消费 BuildArtifact / SceneGraph / validation report 中的结构化证据，不执行 LLM 代码、不重新计算算法答案。

## 11. 当前推荐执行顺序

已完成到 P17.2。当前 Phase 17 已完成；完整历史顺序保留下方供审计：

1. P10.1 算法族注册表文件。
2. P10.2 Benchmark case 元数据扩展。
3. P10.3 分层门禁报告。
4. P11.1 Oracle 类型规范。
5. P11.2 小规模随机样例生成器。
6. P12.1 DP Trace Contract。
7. P12.2 图算法 Trace Contract。
8. P12.3 字符串、树、回溯和数据结构 Trace Contract。
9. P13.1 数组指针、窗口和前缀结构 validator。
10. P13.2 DP validator 扩展。
11. P13.3 图基础、最短路和 MST validator。
12. P13.4 字符串 validator 扩展。
13. P13.4.5 长文件拆分与模块边界整理。
14. P13.5 树、回溯、Trie 和堆 validator。
15. P13.6 哈希、排序、链表、贪心 validator。
16. P13.7 数学、几何、区间结构、图高级 validator。
17. P14.1 Demo readiness schema。
18. P14.2 族级演示完整性规则。
19. P14.3 Dashboard 展示算法族正确性。
20. P15.1 LLM benchmark family split。
21. P15.2 族级 Repair Prompt。
22. P15.3 Unseen family evaluation。
23. P16.1 Core families 扩到 160 到 220 samples。
24. P16.2 Expansion families 扩到 250 到 350 samples。
25. P16.3 算法族能力降级策略。
26. P17.1 族级视觉模式增强。
27. P17.2 交互学习增强。

这样安排的原因：

- 先建立算法族注册和 benchmark 分层，后续所有扩展才有统一统计口径。
- 先做答案 oracle，再做过程 validator，避免 validator 校验的是错误答案过程。
- 先写 trace contract，再写 LLM repair，避免 repair 没有目标格式。
- demo readiness 在 process validator 后面，因为演示正确性依赖过程语义。
- 视觉增强放到最后，因为它应当消费已经正确的语义结构，而不是替代正确性。
