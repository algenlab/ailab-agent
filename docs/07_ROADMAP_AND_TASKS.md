# AlgoLab 最终产品设计与实施方案

本文档是 AlgoLab 的主实施蓝图。它不是短期任务清单，而是从当前科研原型走向最终产品形态的完整设计方案。

使用方式：

- 人看它：理解最终产品长什么样、为什么这样拆阶段、现在该先做什么。
- AI 看它：知道每轮只能推进哪个明确任务，不能自由发挥、不能跨层乱改。

每轮开发前必须先读：

- `docs/00_PRODUCT_NORTH_STAR.md`
- `docs/01_FINAL_PAGE_SPEC.md`
- `docs/02_SYSTEM_ARCHITECTURE.md`
- `docs/03_AI_CODING_GUIDE.md`
- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`
- `docs/05_VISUAL_PRIMITIVES_AND_PATTERNS.md`
- 本文档

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

### 7.1 第一阶段横向验收样例

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

### 7.2 完整 V1 覆盖

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

## 10. 下一步执行建议

当前下一步应从 Phase 1 开始，而不是直接扩算法覆盖。

推荐顺序：

1. P1.1 重组页面信息架构。
2. P1.2 语义时间线。
3. P1.3 Debug Drawer。
4. P2.1 SceneFrame 教学载荷贯通。
5. P2.2 通用依赖关系和连接渲染。
6. P2.3 多视觉原语复合场景。
7. P2.4 通用 before / after 和状态变化表达。
8. P2.5 黄金样例视觉矩阵。
9. P3.1 TeachingStep 通用展示。
10. P3.2 用户可读的过程校验证据。
11. P4.1 通用预测交互。

原因：

- 页面教学骨架决定后续所有算法族的展示质量。
- SceneFrame、deps、teaching、evidence、interaction 是所有算法族共用的数据合同和渲染能力。
- 不同路径、BFS、二分、单调栈是横向验收样例，不是产品路线的中心。
- 先扩算法而不补通用页面、编译、校验和交互能力，会回到“轨迹播放器 + 校验面板”的问题。
