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
| renderer / HTML runtime / browser 交互 | 相关 browser smoke 或目标页面 smoke | `tests.browser_smoke` | `scripts/run_quality_checks.py` |
| LLM benchmark / repair | 小规模 `--limit` 或目标 family 运行 | family split report | 不要求每次全量，论文实验冻结时全量跑 |

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

状态：待执行。

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

### P13.4 字符串 validator 扩展

状态：待执行。

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

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

### P13.5 树、回溯、Trie 和堆 validator

状态：待执行。

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

### P13.6 哈希、排序、链表、贪心 validator

状态：待执行。

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

### P13.7 数学、几何、区间结构、图高级 validator

状态：待执行。

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

## Phase 14：Demo Readiness Gate

目标：

- 证明页面演示语义正确，而不是只证明答案正确。
- 该阶段仍不追求视觉 polish，只检查演示是否能讲清算法且不误导。

### P14.1 Demo readiness schema

状态：待执行。

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

### P14.2 族级演示完整性规则

状态：待执行。

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

### P14.3 Dashboard 展示算法族正确性

状态：待执行。

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
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

## Phase 15：LLM Benchmark 和 Repair 泛化

目标：

- 在 deterministic benchmark 稳定后，评估真实 LLM 对算法族 trace contract 的遵循程度。
- repair 不只是修 schema，而要能根据族级错误修复过程。

### P15.1 LLM benchmark family split

状态：待执行。

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

### P15.2 族级 Repair Prompt

状态：待执行。

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

### P15.3 Unseen family evaluation

状态：待执行。

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

## Phase 16：算法族覆盖扩容

目标：

- 在 family registry、oracle、trace contract、process validator 和 demo readiness gate 都稳定后，扩充覆盖面。
- 扩容不以视觉效果为主要验收标准。

### P16.1 Core families 扩到 160 到 220 samples

状态：待执行。

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

### P16.2 Expansion families 扩到 250 到 350 samples

状态：待执行。

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

### P16.3 算法族能力降级策略

状态：待执行。

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

## Phase 17：视觉和交互增强

目标：

- 在算法族正确性稳定后，提升页面教学质量。
- 视觉增强只消费已有 SceneGraph / BuildArtifact，不改变算法正确性来源。

### P17.1 族级视觉模式增强

状态：待执行。

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

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

如果只改视觉文档或 SceneGraph meta，不改 HTML runtime，可只运行相关 renderer/offline regression。Phase 17 收尾或合并前再运行全量质量检查。

### P17.2 交互学习增强

状态：待执行。

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

本任务最小验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

交互功能阶段收尾或准备提交时再运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

## 11. 当前推荐执行顺序

下一轮执行 AI 应从这里开始：

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
13. P13.5 树、回溯、Trie 和堆 validator。
14. P13.6 哈希、排序、链表、贪心 validator。
15. P13.7 数学、几何、区间结构、图高级 validator。
16. P14.1 Demo readiness schema。
17. P14.2 族级演示完整性规则。
18. P14.3 Dashboard 展示算法族正确性。
19. P15.1 LLM benchmark family split。
20. P15.2 族级 Repair Prompt。
21. P15.3 Unseen family evaluation。
22. P16.1 Core families 扩到 160 到 220 samples。
23. P16.2 Expansion families 扩到 250 到 350 samples。
24. P16.3 算法族能力降级策略。
25. P17.1 族级视觉模式增强。
26. P17.2 交互学习增强。

这样安排的原因：

- 先建立算法族注册和 benchmark 分层，后续所有扩展才有统一统计口径。
- 先做答案 oracle，再做过程 validator，避免 validator 校验的是错误答案过程。
- 先写 trace contract，再写 LLM repair，避免 repair 没有目标格式。
- demo readiness 在 process validator 后面，因为演示正确性依赖过程语义。
- 视觉增强放到最后，因为它应当消费已经正确的语义结构，而不是替代正确性。
