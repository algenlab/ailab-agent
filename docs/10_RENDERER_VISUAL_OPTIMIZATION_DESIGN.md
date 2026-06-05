# Renderer 可视化优化设计

## 1. 文档定位

本文档设计 renderer 的下一轮视觉优化方案，目标是解决 `paper/ailab-agent/shot` 截图中暴露的核心问题，并保持现有架构边界：

- LLM 不直接生成 HTML / CSS / JS。
- Renderer 只消费 BuildArtifact 和 SceneGraph。
- 前端不重新计算算法答案，不伪造 trace，不覆盖 validation / release gate 结果。
- 优化重点是“把已经存在的语义证据更清楚地呈现出来”，而不是绕过 compiler 或 validator。

涉及的主要现有文件：

- `algolab/renderer/export.py`：单文件 HTML、CSS、前端 runtime 和各 layout renderer。
- `algolab/renderer/panels.py`：页面骨架和固定面板。
- `algolab/renderer/layout_registry.py`：layout 到 renderer 的映射。
- `algolab/compiler/scene_compiler.py`：SemanticTrace 到 SceneGraph 的编译。
- `algolab/compiler/target_parser.py`：target id 解析。
- `algolab/schemas/scene_graph.py`：SceneGraph / SceneFrame / SceneObject 合同。

本设计不改变算法正确性链路，只增强视觉表达、空间布局、交互联动和可验收性。

## 2. 截图问题归纳

截图样本：

- `shot/35e7dd86e00a4a8395cf0d454e442ba0.jpg`：Bellman-Ford。
- `shot/6d60ae6c47ef36623e92b468c516f012.jpg`：Tarjan 割点与桥。
- `shot/6f727795f4081136ad39090e60c63fe2.jpg`：零钱兑换 DP。
- `shot/82f1d43ccb2d8e4901c7971045236aac.jpg`：二进制掩码枚举子集。
- `shot/8b2be2f4b5728462d22062e1b2c05047.jpg`：数位 DP。
- `shot/c4acb0322fd1e4694f957b6f70692312.jpg`：树形 DP。
- `shot/f89db9fec509fcbe6a1bbe257f6273b3.jpg`：二分答案平方根。

2026-06-04 进一步用 Playwright 对系统生成目录
`output/aaai/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1`
执行逐 case 截图复核：

- 成功 HTML case：71 个。
- 截图：213 张，每个 case 截第 1 步、中间步、最后一步。
- 生成使用模型：`gemini-3-flash-preview`。
- 截图目录：`shot/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1/`。
- contact sheet：`shot/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1/_contact_sheets/`，共 24 张。
- manifest：`shot/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1/manifest.json`。

该批截图覆盖数组/指针、DP、图、树、递归、字符串、区间结构、几何、网络流、链表、数学和 bit 操作等主要算法族。下面的问题归纳以这 213 张逐张复核结果为准。

主要问题：

1. 中央主可视化过小，图、树、递归状态经常缩成缩略图，无法承担教学主角。
2. 主画布空白过多，内容固定贴左上，未根据容器进行放大、居中、分区和重排。
3. 当前步骤的视觉锚点不强，标题写了当前对象，但对象本身没有足够明显的定位、描边、光晕、连线或局部放大。
4. 代码行同步可信度不足，多张截图左侧仍高亮第 1 行，削弱“代码执行过程可视化”的可信度。
5. 不同算法族渲染得过于同质化，图算法、DP、树形 DP、数位 DP、二分答案没有明显的算法专用视图。
6. 右侧讲解、提示、状态变化、当前状态内容重复，压缩了主舞台注意力。
7. 状态展示偏原始 JSON / list / dict，缺少面向算法语义的摘要。
8. 时间线块过多但语义弱，无法快速定位阶段、关键帧、循环轮次或递归深度。
9. 同一 case 的跨步骤布局不稳定：初始步骤可能有大图，中后期因为状态对象增多，主图突然缩小，用户的空间记忆被打断。
10. 原始数据结构经常被误当主视觉，例如 `nodes/edges`、`isConnected`、`tree.nodes`、链表 `nodes`、网络流 `capacity/flow` 表格直接占据主舞台，挤掉真正的算法过程图。
11. “表格可读”不等于“过程可教学”：不少 DP、矩阵、哈希、数学 case 能看清数值，但看不出当前值为何由依赖对象推出。
12. 几何、网络流、链表、单调栈、字符串专项算法、数学状态转换等族仍缺专用 primitive，当前多退化成数组/表格/map。

## 3. 设计目标

### 3.1 用户体验目标

renderer 应让用户在 3 秒内回答：

- 当前算法在做什么。
- 当前操作对象在哪里。
- 当前对象依赖哪些对象。
- 状态发生了什么变化。
- 当前步骤对应哪一行代码。
- 下一步会沿着哪个阶段继续。
- 当前主视图是否沿用上一关键步骤的空间布局，还是切换到了新的阶段。

### 3.2 视觉质量目标

- 主视觉成为第一注意力区域，而不是被代码、状态 JSON、时间线抢走。
- 同类算法在不同题目中保持稳定视觉语言。
- 当前对象、依赖对象、答案对象、冲突对象有清晰可区分的视觉层级。
- 小规模数据直接完整展示，大规模数据用焦点窗口、聚合、缩略导航和详情面板展示。
- 页面在 `1440x790` 截图尺寸下不出现核心图形不可读、严重空白、文字重叠或关键内容被截断。
- 同一算法 case 的主对象布局跨步骤保持稳定，辅助状态变化不能导致主图忽大忽小。
- 主舞台必须解释过程，不只展示当前 state 的静态快照。

### 3.3 工程目标

- 保持 SceneGraph 合同稳定，优先通过 renderer runtime 和 scene_compiler metadata 增强实现。
- 扩展时优先增加可测试的 layout strategy / visual pattern，而不是在单个算法里写特殊页面。
- 每项视觉增强都能通过 Playwright 截图、DOM 断言或 artifact 结构断言验证。

## 4. 总体方案

优化分为四层：

1. 舞台层：重构页面空间分配，让主可视化占据更大、更稳定的位置。
2. 布局层：为不同 layout 引入自适应测量、放大、居中、焦点窗口和算法族专用布局。
3. 语义层：把 targets、deps、marks、changes、code_line 映射为更强的视觉锚点和联动。
4. 验收层：增加截图质量检查、DOM 检查和算法族视觉回归样例。

推荐实施优先级：

1. 先修主舞台尺寸、fit 策略、居中和面板密度。
2. 再修当前对象高亮、依赖箭头、代码行同步和时间线摘要。
3. 然后补高风险算法族专用 renderer，包括 graph、tree、DP、digit DP、recursion/backtracking、range structure。
4. 最后补扩展族 renderer，包括 geometry、network flow、linked list、monotonic stack、specialized string、math/bit state machine。

新增硬规则：

- 主算法视图必须跨步骤稳定。新增状态对象只能进入 dock、detail、overlay 或折叠面板，不能把主图从可读尺寸压成缩略图。
- 原始 state 只能作为证据来源，不能默认成为主舞台。主舞台应呈现算法语义对象，例如图、路径、窗口、栈、区间、位图、公式链，而不是 raw JSON 的表格化复制。
- 可读性验收必须和教学性验收分开。一个表格“能看清数字”只能通过 readability，不代表通过 visual_trace_alignment。

## 5. 页面信息架构优化

### 5.1 现状

当前页面是三列结构：

```text
左侧代码/解法  |  中央主舞台/控制/时间线  |  右侧讲解/证据/状态
```

问题是左右两侧视觉重量过高，中央主舞台虽然宽，但内容本身被 `fitSceneToCanvas()` 缩到左上角。

### 5.2 新布局原则

桌面端保持三列，但调整比例：

```text
左侧 220-260px  |  中央 minmax(680px, 1fr)  |  右侧 300-340px
```

中央 hero 内部改为：

```text
步骤标题栏
主舞台，默认占中央卡片 70%-78% 高度
紧凑控制条
语义时间线，默认 1 行，可展开
```

关键变化：

- 主舞台高度从 `clamp(300px, 46vh, 450px)` 提升到 `clamp(420px, 62vh, 620px)`。
- 当视口高度低于 820px 时，右侧“当前状态”默认折叠，只保留讲解和本步关键变化。
- 左侧代码默认只显示代码和当前解法摘要，解法对比、Debug Drawer 保持折叠。
- 时间线默认展示关键帧摘要，非关键帧可通过拖动 range 或展开时间线查看。

### 5.3 面板优先级

首屏优先级：

1. 中央主舞台。
2. 当前步骤标题、操作 badge、当前对象。
3. 代码当前行。
4. 本步讲解和状态变化摘要。
5. 时间线。
6. 原始状态和 debug 证据。

右侧面板重组为：

- “本步讲解”：what / why / formula / invariant 合并展示，避免重复。
- “本步变化”：只展示 targets、deps、before、after、changes 的摘要。
- “对象详情”：点击主舞台对象后展示依赖、影响、值、角色。
- “原始状态”：默认折叠，保留调试入口。

## 6. 舞台自适应与缩放设计

### 6.1 现状问题

当前 `fitSceneToCanvas()` 只做“内容太大时缩小”，不会在内容太小时放大，也不会居中：

```javascript
const scale = Math.min(1, availableWidth / contentWidth, availableHeight / contentHeight) * 0.995;
```

这会导致小图、小树、小 DP 表固定在左上角，主舞台大量空白。

### 6.2 新 fit 策略

引入 `fitMode`：

- `contain`：内容完整放入舞台，允许适度放大。
- `focus`：围绕当前 target 和 deps 放大局部。
- `scroll`：内容过大时保留可滚动，不强行缩成不可读。
- `overview-detail`：左侧/上方小地图，右侧/下方展示当前焦点区域。

默认规则：

| 内容类型 | 小规模 | 中规模 | 大规模 |
|---|---|---|---|
| array / string | 放大居中 | 水平滚动 + 当前窗口 | 焦点窗口 + 小地图 |
| matrix / DP | 放大居中 | 当前格周围窗口 | 热区窗口 + 行列摘要 |
| graph | 力导向 / 层次布局放大 | 聚焦当前连通区域 | frontier / path 局部视图 |
| tree / recursion_tree | 层次树放大 | 当前子树聚焦 | 路径视图 + 栈视图 |
| map / state | 表格摘要 | 分组摘要 | 默认折叠 |
| geometry | 点平面放大 | hull / sweep / current edge 聚焦 | overview + 当前几何关系 |
| network flow | 网络图放大 | 当前增广路径聚焦 | 残量网络 detail |
| linked list | 链表节点箭头 | 当前指针窗口 | 反转/重连局部 detail |
| math / bit | 状态转换卡 | 当前公式链 | 位图/余数链 detail |

推荐缩放公式：

```text
rawScale = min(availableWidth / contentWidth, availableHeight / contentHeight)
scale = clamp(rawScale, minReadableScale, maxUsefulScale)
```

建议参数：

- `minReadableScale = 0.72`，低于此值时不要继续缩小，应切换滚动或焦点窗口。
- `maxUsefulScale = 1.85`，小图可放大，但不要巨大到破坏密度。
- 主图居中：`translate((availableWidth - contentWidth * scale) / 2, ...)`。

### 6.3 可读性底线

渲染前根据内容估算可读性：

- 节点圆直径低于 28px，判为不可读。
- 数组 / DP 单元宽度低于 34px，判为不可读。
- 节点 label 字号低于 11px，判为不可读。
- 当前 target 不在可视区域中心 60% 范围内，判为焦点失败。

不可读时不能继续整体缩小，应切到：

- 滚动舞台。
- 当前对象窗口。
- overview + detail。
- 算法族专用摘要视图。

### 6.4 跨步骤布局稳定性

逐张截图复核发现，很多 case 的首帧可读，但中间帧因为新增 `dist`、`dfn`、`low`、`queue`、`call_stack`、`memo`、`query_path` 等对象，主图被重新排入多面板 compound scene，导致图或树突然缩小。

新规则：

- 每个 frame 应确定一个 `primary_container`，例如 `graph`、`tree`、`dp`、`text`、`points`。
- 同一 phase 内 `primary_container` 不应变化。
- 辅助对象进入 dock，而不是和主对象平分舞台。
- 如果辅助对象过多，优先折叠为摘要 chip，例如 `dfn: 4 项`、`queue: [B,C]`、`memo: 3 keys`。
- 只有阶段发生语义切换时才允许主布局切换，例如从 build tree 切到 query path，且时间线必须显示该 phase transition。

推荐 metadata：

```json
{
  "layout_strategy": "stable_primary",
  "primary_container": "graph",
  "secondary_docks": ["distances", "queue", "dfn", "low"],
  "phase_group": "dfs_visit"
}
```

验收：

- 同一 `phase_group` 中，主容器 bounding box 面积变化不应超过 30%，除非进入 `overview_detail`。
- 主容器不能因为新增辅助 state 从舞台主区域降级为左上角缩略图。

## 7. 算法族专用视图设计

### 7.1 图算法视图

适用：BFS、DFS、Dijkstra、Bellman-Ford、Tarjan、拓扑排序、连通分量、省份、二分图染色、二分图匹配、Kruskal。

当前截图问题：图过小，节点/边不可辨认，状态表和图没有关联。

设计：

- 图区域至少占主舞台宽度 70%、高度 70%。
- 节点布局优先级：
  1. state 中有坐标，使用坐标。
  2. 树/DFS 类图使用层次布局。
  3. 一般图使用 deterministic force layout 或圆形布局加防重叠。
- 当前节点：蓝色实心或强描边，带 label 放大。
- 依赖节点/边：琥珀色，边宽增加。
- 已访问节点：绿色低饱和填充。
- frontier / queue / stack：作为图旁边的 dock 展示，不再埋在右侧 state。
- Tarjan 专用：
  - `dfn`、`low` 作为节点下方两行小标签。
  - DFS tree edge 和 back edge 使用不同线型。
  - 当前割点/桥用红橙色标记，必须有图上锚点。
- Bellman-Ford 专用：
  - 当前松弛边加粗并显示 `dist[u] + w < dist[v]`。
  - 本轮变化节点脉冲高亮。
  - 距离表贴近图，而不是放在远离图的普通表格里。
- Dijkstra / 0-1 BFS 专用：
  - frontier / deque / priority queue 作为 dock 展示。
  - 当前候选边显示 `dist[u] + w` 与 `dist[v]` 的比较。
  - 已确定节点、frontier 节点、未访问节点用稳定三态样式。
- 拓扑排序专用：
  - 入度归零节点从图中流入 queue dock。
  - 入度数字贴在节点旁，不放到远处表格。
- 二分图染色 / 匹配专用：
  - 左右分区布局，而不是普通圆形图。
  - 染色用节点左右/颜色双编码。
  - 匹配边、候选边、增广路径必须区别显示。
- Kruskal 专用：
  - 边按权重排序轨道展示，当前候选边与图上边同步高亮。
  - MST 已选边形成绿色子图，拒绝边用红色虚线。

### 7.2 DP 视图

适用：一维 DP、二维 DP、背包、LCS、树形 DP、状态压缩 DP、数位 DP。

当前截图问题：一维 DP 可读但语义弱，数位 DP 和树形 DP 被压缩成不可读列表。

设计：

- 一维 DP：
  - 当前 `i` 单元蓝色。
  - 依赖 `i-coin`、`i-1`、`prev` 单元琥珀色。
  - 更新前后用小浮层显示：`before -> after`。
  - 当前公式固定显示在表上方或右侧，不放入普通提示框。
- 二维 DP：
  - 当前格居中。
  - 依赖格用箭头或路径线连接。
  - 行列 header 固定显示。
  - 矩阵过大时显示当前格周围 `5x7` 窗口，边缘显示省略标记。
- 背包：
  - 物品维度和容量维度分离，当前 coin/item 作为上方 token。
  - 完全背包和 01 背包方向必须视觉区分，正向/反向箭头显示遍历方向。
- 状态压缩 DP：
  - `mask` 同时显示十进制、二进制和已选元素集合。
  - mark / unmark 必须直接作用到元素和 bit 位，不只在标题出现。
  - TSP 类状态显示为 `mask × last` 矩阵时，必须同步展示 mask 位图和当前城市路径。
- 数位 DP：
  - 不使用长列表作为主视图。
  - 主视图分三层：digit position、状态元组 `(pos, tight, started, ...)`、memo 命中/写入。
  - 递归展开只显示当前路径和相邻候选，完整递归栈放到侧边 compact dock。
  - 当前状态必须有大号状态卡，避免 `frame:dfs(...)` 缩成窄条。
- 区间 DP：
  - 区间 `[l,r]` 以区间带显示，split `k` 用垂直切分线。
  - 当前区间、左子区间、右子区间必须在矩阵和区间带中双向高亮。
- LCS / 编辑距离：
  - 矩阵必须带 text/pattern 或 word1/word2 轴标签。
  - 当前字符比较、replace/insert/delete 来源方向用箭头和标签说明。

### 7.3 树和递归视图

适用：树遍历、树形 DP、回溯、递归搜索。

当前截图问题：树被压缩到左上角，当前节点和返回值不可读。

设计：

- 使用层次树布局，根节点居上或居左，子树展开方向稳定。
- 当前递归路径加粗，从根到当前节点形成路径高亮。
- 当前节点使用蓝色，已完成子树使用绿色，尚未访问子树使用灰色。
- 树形 DP 节点必须展示：
  - 节点 value。
  - `take`。
  - `skip`。
  - return value 或局部最优值。
- 递归栈不应渲染成大量普通 map row，应作为栈 dock 展示，每一帧可点击定位到树节点。
- 对于树形 DP，当前节点旁边显示子节点贡献汇总，例如 `take = value + sum(child.skip)`。
- 回溯 / 全排列：
  - 主视图应是“当前路径 + 候选池 + 递归树/调用栈”，不是一列 raw call_stack。
  - 选择、撤销、剪枝必须在候选元素上直接体现。
  - 当前深度固定为视觉轴，避免每步新增一行表格导致主图缩小。
- LCA / 树直径：
  - LCA 的 ancestor jump 必须显示从当前节点向上的跳跃路径。
  - 树直径必须突出两次 DFS/BFS 的端点和最终最长路径。

### 7.4 二分和指针视图

适用：二分查找、二分答案、双指针、滑动窗口。

当前截图问题：数组清楚，但 `low / mid / high` 语义不够强。

设计：

- `low`、`mid`、`high` 使用固定颜色：
  - low：绿色。
  - mid：蓝色。
  - high：紫色。
- 当前搜索区间 `[low, high]` 用底部连续带标出。
- 被排除区间降灰，但保留可见。
- compare 步骤显示判定式，例如 `mid * mid <= n`，并用成功/失败颜色反馈。
- move 步骤用动画箭头或 ghost marker 表示指针从旧位置到新位置。

### 7.5 字符串专项视图

适用：KMP、Rabin-Karp、Z Algorithm、Manacher、滑动窗口字符串。

逐张截图复核发现，字符串类不能只复用 array renderer。不同字符串算法的关键语义不同：

- KMP：
  - text / pattern 双行对齐为主视图。
  - `i`、`j` 光标必须上下对应。
  - failure / next 回退用弧线或跳转箭头。
- Rabin-Karp：
  - 当前窗口、pattern、rolling hash 三条轨道同步。
  - hash 相等但字符不等时显示二次验证。
- Z Algorithm：
  - Z-box `[l,r]` 必须作为区间带。
  - 当前 `i`、复制来源、扩展比较必须在同一条字符串上体现。
- Manacher：
  - 中心、半径、镜像位置、当前回文范围必须以弧线或区间带显示。
  - 只展示 `p` 数组无法说明中心扩展过程。
- 字符串滑动窗口：
  - 当前 window 用连续底色或框线。
  - counts / seen 作为 compact dock，不抢主视图。

### 7.6 区间结构视图

适用：Fenwick Tree、Segment Tree、Sparse Table、Difference Array、Prefix Sum、Range Query。

要求：

- Fenwick：
  - `idx += lowbit(idx)` / `idx -= lowbit(idx)` 的跳转路径必须画成箭头。
  - bit 数组单元显示覆盖区间，例如 `bit[4] covers [1,4]`。
- Segment Tree：
  - build/query/update 必须使用树形区间节点，而不是 phase 标签或普通 map。
  - query path、update path、cover path 用不同颜色。
- Sparse Table：
  - 当前 query 拆成两个 block，两个 block 在原数组和 ST 表中同步高亮。
- Difference Array：
  - 区间 `[l,r]` 作为连续带，`diff[l] += x` 和 `diff[r+1] -= x` 作为两端影响点。
- Prefix Sum：
  - query `[l,r]` 显示为 `prefix[r+1] - prefix[l]` 的双端依赖。

### 7.7 几何视图

适用：Convex Hull、Convex Hull expansion、点集扫描、叉积判断。

当前截图问题：凸包 case 退化为点表、hull index 表和少量文本，几何关系没有成为主视图。

要求：

- 点集必须在二维坐标平面展示。
- 当前候选边、栈顶两点、待判断点使用不同颜色。
- 叉积方向用左转/右转标记和小箭头展示。
- hull 已确认边形成多边形折线。
- 被弹出的点保留灰色 ghost，说明为什么被移除。

### 7.8 网络流视图

适用：Edmonds-Karp、最大流、残量网络。

当前截图问题：网络流 case 主要显示多张 capacity/flow/residual 表，小图不可读，增广路径不明显。

要求：

- 主视图是残量网络图。
- 边标签显示 `flow/capacity` 和 residual。
- 当前 BFS frontier、parent tree、augmenting path 同步显示。
- 增广路径用高亮路径和瓶颈值标记。
- 一次 augment 后，正向边和反向边变化要在图上直接体现。

### 7.9 链表视图

适用：Reverse Linked List、快慢指针链表、链表环。

当前截图问题：链表 case 显示 raw `nodes`、`head`、`prev/current` 表格，缺少节点箭头和反转过程。

要求：

- 链表必须显示为节点链和箭头。
- `prev`、`curr`、`next` 指针以标签贴在节点上方。
- 反转边用动画或 ghost arrow 展示旧方向到新方向。
- 环检测必须画出环，不使用普通数组代替。

### 7.10 单调栈和堆视图

适用：Daily Temperatures、Next Greater Element、Kth Largest、Heap-based algorithms。

要求：

- 单调栈：
  - 主视图包含扫描数组、当前下标、栈 dock。
  - pop 时从栈顶到答案位置画影响箭头。
  - 当前温度与栈顶温度比较必须贴近元素显示。
- 堆：
  - 堆应以树形层级展示，不只是数组或 map。
  - push/pop 后显示上浮/下沉路径。
  - Kth Largest 要显示堆容量 k 和被淘汰元素。

### 7.11 数学和 bit 状态机视图

适用：GCD、Fast Power、Lowbit、Sieve、位运算分解。

要求：

- GCD：
  - 显示余数链：`gcd(a,b) -> gcd(b, a % b)`。
  - 当前替换关系用箭头，而非只展示 a/b 表格。
- Fast Power：
  - exponent 二进制位、base 平方、result 乘入条件并排展示。
- Lowbit：
  - 二进制位图显示 `x`、`-x`、`x & -x`。
- Sieve：
  - 数字网格显示 prime/composite 状态。
  - 当前 prime 的倍数划线或淡出，而不是布尔数组。

## 8. 当前对象、依赖与代码同步

### 8.1 视觉角色规范

统一角色颜色和层级：

| 角色 | 视觉 |
|---|---|
| current / hot | 蓝色强描边，必要时放大 1.08 倍 |
| dependency | 琥珀色填充或描边 |
| answer / accepted | 绿色 |
| conflict / wrong / pruned | 红色 |
| inactive / excluded | 灰色低对比 |
| frontier / pending | 青绿色 |

要求：

- 当前 target 必须在主视图中可见。
- deps 和 target 同时存在时，必须有依赖关系表达：箭头、连线、公式代入或路径带。
- 对象详情必须能从主舞台点击得到，而不是只在右侧 raw state 查找。

### 8.2 焦点框和局部放大

当当前对象小于可读阈值或不在中心区域时：

- 舞台自动滚动或平移到当前对象。
- 对当前对象周围创建 focus halo。
- 对复杂图/树显示局部 detail inset，保留 overview。

### 8.3 代码行同步

当前 `codeLineInfo()` 只按 `frame.code_line` 高亮，如果 code_line 缺失或越界会退到第 1 行。优化方案：

1. 保持降级提示，但视觉上不能把第 1 行伪装成可信当前行。
2. `code_line` 无效时，代码面板显示黄色状态：“code_line 缺失，无法可靠同步”。
3. `scene_compiler` 可从 event evidence 中保留 `op`、`targets`，renderer 在代码面板上方显示“语义步骤来源”，避免用户误以为第 1 行正在执行。
4. 后续可在 tracer / validator 层增加 code_line 覆盖率指标：
   - 关键帧 code_line 有效率。
   - code_line 是否落在非空代码行。
   - 连续多步固定第 1 行的异常比例。

## 9. 时间线优化

### 9.1 现状问题

时间线 tick 过多，标签短且重复，例如“初始化”“主循环”“enter frame”，不能帮助用户理解算法阶段。

### 9.2 新时间线结构

时间线分两层：

- 阶段轨道：初始化、主循环、递归展开、回溯、结果。
- 关键帧轨道：当前对象、op、目标摘要。

tick 内容：

```text
阶段名
op + target 摘要
```

示例：

```text
第 2 轮松弛
set dist[C]
```

```text
DFS 深度 3
enter node:A
```

### 9.3 折叠规则

- 默认只展示 keyframe。
- 连续相同 phase 的普通帧合并成一个区间块。
- 用户拖动 range 时仍可访问每一帧。
- 点击阶段块时跳到该阶段第一帧。

### 9.4 语义元数据

优先读取 `frame.evidence.timeline`，缺失时按以下信息推断：

- op。
- targets。
- state 中的 `i/j/k/mask/pos/depth/round`。
- frame id，如 `frame:dfs(...)`。

长期建议由 `scene_compiler.py::_timeline_for_event()` 增强：

- `phase`
- `iteration`
- `depth`
- `keyframe`
- `target_summary`
- `group_id`

## 10. 讲解、证据与状态面板优化

### 10.1 去重原则

当前“当前步骤”“为什么”“提示”“状态变化摘要”经常重复。新规则：

- `what`：一句话说明操作。
- `why`：说明算法原因，不重复 what。
- `formula`：只在有公式或依赖代入时展示。
- `hint`：只在用户交互或易错点存在时展示。
- `changes`：展示 before / after 或新增 / 删除，不重复状态全文。

### 10.2 当前状态摘要

右侧不再直接把所有 state 展成同权重 JSON。按类型摘要：

- array / matrix：显示形状、当前 target、变化数量。
- graph：显示节点数、边数、当前节点、frontier、visited 数。
- tree：显示节点数、当前节点、递归深度、已完成子树数。
- map：显示 key 数、变化 key、当前 key。
- recursion stack：显示深度和 top frame。

原始 JSON 保留在 Debug Drawer。

### 10.4 原始 state 降噪规则

逐张截图复核发现，raw state 经常被 renderer 自动转成主舞台对象，例如 `nodes/edges`、`isConnected`、`capacity`、`flow`、`memo`、`call_stack`、`query_path` 等。这些字段是证据，不一定是主视觉。

规则：

- 每个 frame 最多一个 primary data structure 进入主舞台。
- raw dict/list 默认进入右侧状态摘要或 debug，不进入主舞台，除非它对应当前算法族的主 primitive。
- 大于 8 行的 map/list 不应常驻主舞台，必须摘要化。
- `call_stack`、`memo`、`dfn`、`low`、`dist`、`parent`、`visited`、`counts` 默认作为 dock 或 overlay。
- 如果 state 中同时存在 raw input 和 derived visualization，优先展示 derived visualization。

示例：

| state 字段 | 默认处理 |
|---|---|
| `graph` | 主舞台，graph renderer |
| `dist` | graph 节点标签或 dock |
| `dfn/low` | Tarjan 节点标签 |
| `call_stack` | recursion dock |
| `memo` | compact dock / hit badge |
| `nodes/edges` for linked list | linked-list primitive，不是 raw table |
| `points` | geometry plane |
| `capacity/flow/residual` | edge labels，不是独立大表 |

### 10.3 对象详情面板

点击主舞台对象后，右侧“对象详情”显示：

- id。
- label / value。
- role。
- 当前 step 是否为 target / dep。
- 它依赖哪些对象。
- 它影响哪些对象。
- before / after。
- 所属容器和 layout。

这能替代大量常驻状态面板，降低默认噪音。

## 11. 视觉语言与样式规范

### 11.1 色彩

继续使用克制的教学工具风格，但提高语义色可辨识度：

- 背景：浅灰 `#f6f7fb`。
- 面板：白色。
- 主文字：深蓝灰。
- 当前：蓝。
- 依赖：琥珀。
- 成功/答案：绿。
- 错误/冲突：红。
- 待处理/frontier：青绿。
- 排除/未激活：灰。

避免：

- 所有元素都用蓝色描边。
- 单纯依靠颜色表达含义，必须配合形状、label、线型或位置。
- 高饱和大面积背景。

### 11.2 字体和密度

- 主舞台节点 label 不低于 12px。
- DP / array 单元值不低于 13px。
- 面板正文不低于 13px。
- 代码保持等宽字体，当前行高亮必须有足够对比。
- 卡片圆角不超过 8px，保持工具类界面密度。

### 11.3 动效

动效只用于表达状态变化：

- pointer move：150-220ms。
- mark / unmark：边框和填充过渡 120-180ms。
- dependency arrow 出现：淡入 120ms。
- focus pan：200-300ms。

必须支持 `prefers-reduced-motion`，降低或关闭动画。

## 12. SceneGraph 与 compiler 增强建议

renderer 能完成大部分视觉优化，但部分信息最好在 compiler 层补充，避免前端猜测。

建议为 SceneObject 或 frame evidence 增加的 metadata：

- `frame.meta.family`：`graph`、`dp`、`tree_dp`、`digit_dp`、`binary_search` 等。
- `frame.meta.focus_targets`：需要居中的对象。
- `frame.meta.layout_strategy`：`overview_detail`、`focus_window`、`full`、`scroll`。
- `frame.meta.primary_container`：当前主舞台对象，跨步骤稳定布局使用。
- `frame.meta.secondary_docks`：允许展示但不得挤压主舞台的辅助状态。
- `frame.meta.phase_group`：跨步骤布局稳定性检查使用。
- `object.meta.visual_weight`：主对象、辅助对象、背景对象权重。
- `object.meta.value_before` / `value_after`：方便主舞台直接显示变化。
- `object.meta.group`：阶段组、递归深度、循环轮次。
- `evidence.timeline.group_id`：时间线折叠使用。

兼容原则：

- 所有 metadata 都是 optional。
- 旧 artifact 没有 metadata 时仍按现有逻辑渲染。
- renderer 不依赖 metadata 计算算法结果，只用于展示。

## 13. 实施计划

### Phase 1：主舞台和默认布局

目标：

- 主舞台变大。
- 小内容自动放大居中。
- 大内容不再缩成不可读。
- 右侧状态默认降噪。

改动点：

- `export.py` CSS 中 `.hero`、`.canvas`、`.workspace`。
- `fitSceneToCanvas()` 改为支持放大、居中、min readable scale。
- 增加 `data-fit-mode` 和 `data-fit-scale` 便于测试。
- `panels.py` 调整右侧面板顺序，引入对象详情区域。

验收：

- 7 张截图对应页面中，主可视化内容占中央舞台可见面积至少 45%。
- 小图不再贴左上角。
- DP 单元、图节点、树节点可读。

### Phase 2：语义高亮和对象详情

目标：

- 当前 target、deps、answer、conflict 视觉层级清楚。
- 点击对象能看到依赖和影响。
- 状态变化摘要从右侧 raw state 中抽离出来。

改动点：

- `markClass()`、`objectMetaClass()`、CSS role class。
- `showDependencyDetail()` 扩展 before / after / container / layout。
- `renderChangeSummary()` 调整为主舞台或右侧对象详情的一部分。

验收：

- 每个有 target 的 frame，主舞台能找到至少一个对应 `data-object-id`。
- 每个有 deps 和 targets 的 frame，页面存在依赖表达。
- 点击当前对象后，对象详情包含 id、role、依赖、影响。

### Phase 3：算法族专用 renderer

目标：

- 图、树、DP、数位 DP、二分答案、回溯、字符串专项、区间结构各有清晰专用表达。

改动点：

- `renderGraph()`：布局、frontier dock、dfn/low/dist label。
- `renderTree()`：路径高亮、take/skip label、递归栈 dock。
- `renderMatrix()` / `renderArray()`：依赖窗口、指针带、公式浮层。
- 新增 digit DP 状态 renderer，可先作为 `visual pattern` 面板实现，再升级 layout。
- 新增 string-specialized pattern：KMP alignment、Rabin-Karp rolling hash、Z-box、Manacher radius。
- 新增 range-structure pattern：Fenwick lowbit path、segment tree cover path、sparse table query blocks。
- `scene_compiler.py` 增强 visual_patterns 和 timeline metadata。

验收：

- Tarjan 截图中 `dfn/low` 可见，当前节点可辨认。
- 树形 DP 截图中当前节点和 `take/skip` 可见。
- 数位 DP 截图不再显示不可读长竖条，当前状态卡可读。
- 二分截图中 `[low, high]` 区间和 `mid` 判定式可见。
- KMP/Rabin-Karp/Z/Manacher 中至少一个专项视觉关系可见。
- Fenwick/Segment Tree/Sparse Table 中 query/update 路径可见。

### Phase 3.5：扩展高风险族 renderer

目标：

- 几何、网络流、链表、单调栈、堆、数学/bit 族不再退化为 raw 表格。

改动点：

- `renderGeometry()` 强化点平面、当前边、叉积方向、hull 多边形。
- `renderGraph()` 增加 network-flow mode，显示 `flow/capacity/residual` 和 augmenting path。
- 新增 linked-list renderer 或 graph-like linked-list layout。
- 新增 monotonic-stack visual pattern，把数组、栈、答案箭头放入同一主视图。
- `renderHeap()` 强化树形堆和上浮/下沉路径。
- 新增 math-state-card / bit-view pattern，覆盖 GCD、fast power、lowbit、sieve。

验收：

- 凸包截图中点平面、当前边、hull 折线可见。
- Edmonds-Karp 截图中残量网络和增广路径可见。
- 链表反转截图中节点箭头和 `prev/curr/next` 指针可见。
- Daily Temperatures 截图中栈 pop 到答案位置的影响箭头可见。
- GCD/fast power/lowbit/sieve 中至少一个状态转换图可见。

### Phase 4：时间线和代码同步

目标：

- 时间线能表达阶段和关键帧。
- code_line 不可信时显式告警，不误导。

改动点：

- `renderTimeline()` 支持阶段折叠。
- `timelineMeta()` 支持 group。
- `renderCode()` 增加无效 code_line 的降级样式。
- validator 或 render report 增加 code_line coverage 指标。

验收：

- 连续重复 phase 被合并或弱化。
- 当前关键帧 tick 一眼可识别。
- code_line 缺失或越界时，代码面板显示警告，不只高亮第 1 行。

### Phase 5：截图回归和质量门禁

目标：

- 用自动化检查防止视觉退化。

改动点：

- 增加 Playwright 截图脚本或扩展现有截图脚本。
- 增加 DOM 检查：
- 主舞台非空。
- 当前对象存在。
- fit scale 合理。
- 无水平页面溢出。
- 核心文本未重叠。
- 跨步骤主容器尺寸稳定。
- 辅助 state 没有把主图压成缩略图。
- 可读性和可教学性分别打分。
- 增加 VLM rubric 中的可读性维度。

验收：

- 7 个截图样例对应 artifact 均通过 smoke。
- 生成报告记录每个样例的主舞台利用率、当前对象可见性和 code_line 状态。
- 71 个 algolab_full case 的 213 张截图中，`main_stage_utilization < 0.2` 的比例应持续下降，并对低于阈值的 case 输出原因分类。

## 14. 验收标准

### 14.1 人工验收

在 `1440x790` 视口下逐个检查：

- 当前对象是否一眼可见。
- 当前对象和依赖对象是否有视觉关系。
- 主舞台是否比左右面板更突出。
- 是否能不看 raw JSON 理解当前步骤。
- 是否能看出当前步骤对应的代码行是否可信。
- 同一 case 的主视图是否跨步骤保持稳定。
- 当前 frame 是否只显示了 state 快照，还是解释了算法转移。
- 表格可读时，是否也能看出依赖来源和更新原因。

### 14.2 自动验收

建议新增或扩展检查项：

- `canvas_has_rendered_objects`：主舞台有可见对象。
- `active_target_visible`：当前 target 的 DOM 节点存在并在 canvas bounding box 内。
- `readable_scale`：`data-fit-scale >= 0.72`，否则必须有 scroll 或 focus mode 标记。
- `dependency_visible`：有 deps + targets 时存在 dependency flow 或 pattern card。
- `code_line_status_visible`：code_line 无效时存在 warning。
- `no_major_overflow`：body 不出现非预期横向滚动。
- `timeline_keyframes_visible`：至少一个关键帧 tick 可见。
- `primary_container_stable`：同一 phase 内主容器尺寸和位置变化在阈值内。
- `raw_state_not_primary`：raw dict/list 辅助状态没有成为主舞台最大对象，除非它是该算法族的正式 primitive。
- `visual_trace_alignment`：当前 target 和 deps 在主视图中存在可见关系。
- `teaching_relation_visible`：当前步骤的公式、路径、比较、区间、边松弛或状态转换至少有一种可见表达。
- `family_renderer_used`：高风险族命中专用 renderer / pattern，而不是只走 generic map。

### 14.3 质量指标

可在 render report 中记录：

```json
{
  "visual_quality": {
    "main_stage_utilization": 0.58,
    "active_target_visible": true,
    "readable_scale": true,
    "dependency_visible": true,
    "code_line_valid_rate": 0.84,
    "layout_strategy": "focus_window",
    "primary_container_stable": true,
    "raw_state_not_primary": true,
    "teaching_relation_visible": true,
    "family_renderer": "graph_tarjan"
  }
}
```

这些指标不替代 VLM 评价，但能作为低成本回归门禁。

## 15. 风险与边界

风险：

- 如果只改 CSS，不改 layout 策略，复杂图和数位 DP 仍会不可读。
- 如果前端过度猜测算法族，可能和 trace 语义不一致。
- 如果强行动画化所有变化，会降低阅读效率。
- 如果放大过度，用户会失去全局上下文。
- 如果只追求主舞台利用率，可能把辅助证据隐藏过度，导致可验证性下降。
- 如果保留所有辅助状态在主舞台，主视图会再次被 raw 表格挤压。

边界：

- renderer 不修复错误 trace。
- renderer 不推断缺失的关键算法状态。
- renderer 不把 process validator 未通过的页面美化成可信演示。
- renderer 的算法族专用视图只能使用 SceneGraph / state / evidence 中已有字段。

## 16. 推荐最终效果

优化后的页面应呈现为：

- 中央是清晰、放大、居中的算法主视图。
- 当前对象和依赖对象直接在主视图中被锚定。
- 公式、依赖、状态变化靠近发生位置展示。
- 右侧只解释本步必要信息，原始状态折叠。
- 时间线表达阶段，而不是堆满重复 tick。
- 代码行同步可信，无法同步时明确提示。
- 不同算法族有各自自然的视觉模型，而不是统一退化成小图加表格。
- 同一 case 的主图跨步骤稳定，辅助状态以 dock/overlay/detail 的形式补充。
- 几何、网络流、链表、单调栈、字符串专项和数学/bit 不再以 raw 表格作为默认主视图。

这轮优化的判断标准不是“页面更漂亮”，而是用户能否更快、更准确地从画面理解算法正在怎样推进。
