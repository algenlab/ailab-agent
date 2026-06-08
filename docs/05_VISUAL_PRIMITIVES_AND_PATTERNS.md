# 视觉原语与页面模式

## 1. 文档定位

本文档记录当前代码真实支持的视觉原语、target 规范、SceneGraph 编译规则和页面模式。

当前系统还不是最终版。视觉层的阶段性目标是支撑实验指标提升：

- 答案正确：视觉不能伪造答案，必须只展示 BuildArtifact 中通过 gate 的结果。
- 步骤正确：targets、deps、state 和 visual marks 必须能对应 trace 的真实事件。
- 过程解释可信：页面讲解必须来自 `frame.teaching`、`frame.evidence`、`reason`、`deps` 和 `state`。
- 可视化效果：同一类语义对象稳定映射到固定 layout，不让 LLM 自由写页面。
- 交互性：优先支持能被 trace 证据支撑的交互，而不是纯前端猜算法。

新增算法族时，先判断现有视觉原语能否承载语义对象。只有现有 target / state / layout 无法表达关键过程时，才扩展 parser、compiler、renderer 和测试。

## 2. 当前视觉链路

真实视觉链路：

```text
SemanticTrace event
  -> target_parser.parse_target()
  -> scene_compiler.compile_frame()
  -> SceneFrame.objects / marks / evidence / teaching / interaction
  -> renderer.export.render_html()
  -> 固定单文件中文 HTML runtime
```

核心原则：

- LLM 不生成 HTML / CSS / JS。
- Renderer 不理解具体算法题，只根据 SceneGraph 对象、layout meta、marks、evidence 渲染。
- 视觉对象必须来自 state、targets、deps 或 input_data。
- 页面中的讲解、交互反馈、公式展开和过程证据只能读当前 artifact / SceneGraph。

## 3. 当前 target parser 支持范围

`algolab/compiler/target_parser.py` 当前支持：

| target 写法 | parse kind | 说明 |
|---|---|---|
| `nums[3]` | `indexed` | 一维索引，数字下标 |
| `dp[1][2]` | `indexed` | 二维索引，数字下标 |
| `nums[1:4]` | `slice` | 半开切片，要求 state 中存在对应元素 |
| `dist[A]` | `map` | 非数字 key 的 map bracket |
| `seen[2]` | `indexed` | 数字 key 会先被当成 indexed；state 中仍可用 dict 暴露 `seen[2]` 对象 |
| `node:A` | `node` | 图、树、Trie、并查集、几何等节点 |
| `edge:A->B` | `edge` | 有向边，必须包含 `->` |
| `pointer:left` | `pointer` | 指针，位置来自 event.value 或 state 中同名变量 |
| `frame:dfs(2)` | `frame` | 递归帧 / 调用帧 |
| `point:3` | `point` | 几何点 |
| `char:x` | `char` | 字符引用，当前较少使用 |
| `stack`、`queue`、`deque`、`heap`、`tree`、`trie`、`frames`、`points`、`string` | `container` | 容器 target |
| 其它字符串 | `symbol` | 标量 label 或兜底符号 |

不建议当前使用：

- `range:1-3`
- `number:n`
- `interval:0-2`
- `flow:A->B`
- `segment:A->B`

这些前缀没有完整 parser / validator / compiler / renderer / test 链路。需要表达时，优先放进 state，并使用现有 target：

- 区间：`query`、`update_path`、`node:seg(1,4)`、`bit[4]`、`st[2][3]`
- 数字：`n`、`mask`、`bits[0]`、`factor[2]`、`table[3][4]`
- 网络流：`edge:A->B`、`cap[A->B]`、`flow[A->B]`、`residual[A->B]`
- 线段：geometry state 中的 `segments`，由 Scene Compiler 生成 `segment:*` 对象

## 4. Scene Compiler 的对象生成规则

`scene_compiler.py::_objects_from_state()` 当前按 state 类型生成对象。

| state 形态 | 当前生成 |
|---|---|
| 标量 `int/float/str/bool/None` | `LABEL` |
| 一维标量 list | `CONTAINER(layout=array)` + `CELL` |
| key 为 `stack/queue/deque/heap` 的一维 list | 对应 layout 的 container + cell |
| 二维 list | `CONTAINER(layout=matrix)` + 二维 cell |
| 普通 dict | `CONTAINER(layout=map)` + key-value label |
| `graph` / `adjacency` 或所有 value 是 list 的 dict | `CONTAINER(layout=graph)` + node / edge |
| `tree` / `binary_tree` / `segment_tree` 且含 nodes/edges | `CONTAINER(layout=tree)` |
| `recursion_tree` / `call_tree` / `search_tree` 且含 nodes/edges | `CONTAINER(layout=recursion_tree)` |
| `trie` 且含 nodes/edges | `CONTAINER(layout=trie)` |
| `union_find` / `dsu` 且含 dict parent | `CONTAINER(layout=union_find)` |
| `points` list | `CONTAINER(layout=geometry)` + point nodes |
| `geometry` / `plane` / `sweep` 且含 points | geometry points / segments / hull / sweep |
| `text` / `pattern` / `s` / `t` / `string` | `CONTAINER(layout=string)` + char cells |
| ML-like dict | `CONTAINER(layout=ml)` 和 tensor / batch / parameter 等对象 |

`_objects_from_refs()` 会从 targets / deps 补充 node、edge、pointer、frame、point、char、slice、map、container、symbol 等对象。
注意：补充对象只能保证页面有可显示对象，不代表 target 一定语义正确；语义正确仍依赖 trace validator 和 process validator。

## 5. Renderer 支持的 layout

`algolab/renderer/layout_registry.py` 当前 layout 映射：

| layout | renderer |
|---|---|
| `array` | array |
| `matrix` | matrix |
| `string` | string |
| `heap` | heap |
| `queue` | queue |
| `deque` | queue |
| `stack` | stack |
| `graph` | graph |
| `tree` | tree |
| `trie` | tree |
| `union_find` | tree |
| `recursion_tree` | tree |
| `geometry` | geometry |
| `ml` / `tensor` / `batch` / `parameter` / `loss_curve` / `gradient_vector` / `decision_boundary` / `training_epoch` / `prediction` | ml |
| `computational_graph` | graph |
| `map` | map |
| `generic` | map |

`capabilities.py` 还声明了 `teaching_2d`、`creative`、`spatial_3d` 为 stable，`hybrid_2_5d` 为 planned。主实验和主页面仍应以 `teaching_2d` 的稳定 SceneGraph renderer 为准。

## 6. SceneFrame 中的视觉证据

每个 `SceneFrame` 当前包含：

- `objects`：可渲染对象。
- `marks`：target role 标记。
- `state`：当前公开 state，去掉 `_` 开头字段。
- `interaction`：choice / input / judge。
- `teaching`：what / why / formula / invariant / common_mistake / hint。
- `evidence`：operation、targets、deps、value、before、after、changes、timeline、process、visual_patterns。

页面右侧的“讲解”“系统校验”“本步证据”“当前状态”“交互”“代码”都读取这些字段。

## 7. 当前 visual patterns

`scene_compiler.py` 会给对象附加 `meta.visual_pattern` / `meta.visual_patterns`，renderer 用 CSS 和辅助面板展示。

当前主要 pattern：

| pattern | 触发条件 | 用途 |
|---|---|---|
| `dependency_flow` | event 同时有 deps 和 targets | 依赖对象到目标对象的通用流向 |
| `dp_dependency` | matrix target + matrix deps | DP 表依赖箭头 |
| `formula_substitution` | DP 依赖且有 formula / value | 公式替换和本步证据 |
| `dp_formula_substitution` | DP target / deps | 高亮当前格与依赖格 |
| `dp_dependency_arrow` | DP dep -> target arrow | 表格内依赖箭头 |
| `graph_frontier` | state 中 queue / frontier / heap / open_set | 图 frontier |
| `graph_visit_state` | state.visited | 已访问节点 |
| `graph_current_node` | state.current / node / u | 当前节点 |
| `graph_relax_edge` | deps 中 edge 且有图状态 | 当前松弛 / 访问边 |
| `graph_relax_target` | target 是 node 且有图状态 | 松弛目标节点 |
| `graph_path_highlight` | state.path / path_edges | 路径高亮 |
| `graph_edge_label` | edge 有 weight / label | 边权 / 标签 |
| `string_alignment` | text / pattern / s / t / string | 字符串双行对齐和 cursor |
| `string_window` | state.window / left/right | 字符串窗口 |
| `string_fallback_arc` | j_before/j_after 或 fallback_from/to | KMP 等回退弧线 |
| `tree_return_value` | state.return_values / return_value | 树递归返回值 |
| `backtracking_choice` | recursion_tree 上 MARK/ENTER/PUSH/LINK | 回溯选择 |
| `backtracking_undo` | recursion_tree 上 UNMARK/EXIT/POP/UNLINK | 回溯撤销 |
| `range_structure` | segment_tree / bit / st | 区间结构容器 |
| `range_query_path` | state.query_path 或查询相关 target | 查询路径 |
| `range_update_path` | state.update_path 或更新相关 target | 更新路径 |
| `range_cover_path` | state.cover_path 或覆盖相关 target | 覆盖区间 |
| `network_flow_edge_label` | capacity / flow / residual | 网络流边标签 |
| `network_flow_augmenting_path` | augmenting_path / augmenting_edges | 增广路径 |

这些 pattern 是提升“过程解释可信”和“可视化效果”的主要抓手。后续优化应优先补 pattern，而不是新增自由页面。

## 8. 页面模式

当前固定页面不是单一播放器，而是“四区一线一抽屉”：

- 顶部任务与可信度区：题目、输出、当前解法、badge。
- 左侧题目与输入区：题目描述、输入、expected、解法、解法对比、重新生成 payload。
- 中间主可视化区：SceneGraph objects、controls、语义时间线。
- 右侧教学与证据区：讲解、系统校验、本步证据、状态、交互、代码。
- 底部 / 中部时间线：每帧 phase、keyframe、operation；SceneGraph 保留完整帧，但 keyframe 标记最多 50 个。
- Debug Drawer：raw validation、raw state、release gate、artifact JSON。

页面允许增强：

- 更清晰的 layout。
- 更好的 formula 展示。
- 更强的 deps 点击联动。
- 更好的移动端布局。
- 更细的 visual pattern 样式。
- 更稳定的 Playwright 检查。

页面不允许：

- 前端重新计算答案并覆盖 artifact 结果。
- 前端修改 trace 伪装成重新生成。
- 用动画掩盖 process validator 失败。
- 读取 LLM 直接生成的 HTML 作为主链路内容。

## 9. 原语总览

| 原语 | 当前状态 | 主要 state | 主要 target | 主要指标贡献 |
|---|---|---|---|---|
| array + pointer | 稳定 | `nums`、`left/right/mid` | `nums[i]`、`pointer:left` | 步骤正确、交互性 |
| matrix / DP table | 稳定 | `dp`、`grid`、`i/j` | `dp[i][j]` | 步骤正确、解释可信 |
| graph | 稳定 | `graph`、`queue`、`dist`、`visited` | `node:A`、`edge:A->B` | 步骤正确、可视化效果 |
| stack / queue / deque | 稳定 | `stack`、`queue`、`deque` | `stack`、`queue` | 步骤正确、交互性 |
| map / hash table | 稳定 | `seen`、`count`、`dist` | `seen[x]`、`dist[A]` | 答案正确、步骤正确 |
| tree | 稳定 | `tree.nodes/edges` | `node:x`、`edge:x->y` | 过程解释可信 |
| heap | 稳定 | `heap` | `heap`、`heap[0]` | 步骤正确 |
| trie | 稳定，使用 tree renderer | `trie.nodes/edges` | `node:abc`、`edge:a->ab` | 步骤正确 |
| union-find | 稳定，使用 tree renderer | `union_find.parent` | `node:x`、`edge:x->root` | 步骤正确 |
| recursion_tree | 稳定，使用 tree renderer | `recursion_tree.nodes/edges` | `frame:*`、`node:*` | 解释可信、交互性 |
| string | 稳定 | `text`、`pattern`、`i/j` | `text[i]`、`pattern[j]` | 步骤正确、视觉效果 |
| geometry | 稳定基础版 | `points`、`geometry` | `point:i` | 视觉效果 |
| range structure | 可组合，不是独立 renderer | `segment_tree`、`bit`、`st` | `node:*`、`bit[i]`、`st[i][j]` | 步骤正确 |
| math / bit | 可组合，不是独立 renderer | `bits`、`table`、`mask` | `bits[i]`、`table[i][j]` | 解释可信 |
| linked list | 可组合，不是独立 renderer | `tree/nodes/edges` 或 graph-like | `node:*`、`edge:*`、`pointer:*` | 视觉效果待增强 |
| ML primitives | 扩展方向 | `ml` / `training` | `parameter:*` 等 | 非主路径 |

## 10. array + pointer

适用：

- 二分查找 / 二分答案。
- 双指针。
- 滑动窗口。
- 快慢指针。
- 前缀和 / 差分。
- 排序扫描。

推荐 state：

```json
{
  "nums": [1, 3, 5, 7],
  "left": 0,
  "right": 3,
  "mid": 1,
  "array_contract": {
    "submode": "binary_answer",
    "expected_targets": ["pointer:left", "pointer:right", "pointer:mid"]
  }
}
```

推荐 target：

- `nums[0]`
- `nums[2]`
- `nums[1:3]`
- `pointer:left`
- `pointer:right`
- `pointer:mid`

当前实现：

- 一维 list 自动生成 array。
- pointer 位置来自 event.value 或 state 中同名变量。
- slice 生成 highlight 和 slice cell 对象。
- timeline 会把 move / compare / set 组织成主循环或关键转移。

注意：

- 指针 target 本身不是数组元素，pointer 移动时仍要在 state 中保留数组和指针值。
- 二分 compare 事件中的 left/right/mid 应对应比较前窗口，移动 pointer 的事件再更新区间。

## 11. matrix / DP table

适用：

- 一维 / 二维 DP。
- 背包。
- LCS / 编辑距离。
- 区间 DP。
- Floyd-Warshall。
- 稀疏表。
- 表格型数学过程。

推荐 state：

```json
{
  "dp": [[1, 1, 1], [1, 2, 3]],
  "i": 1,
  "j": 2,
  "formula": "dp[i][j] = dp[i-1][j] + dp[i][j-1]",
  "dp_contract": {
    "containers": ["dp"],
    "answer_position": "dp[1][2]",
    "expected_targets": ["dp[1][1]", "dp[1][2]"],
    "subfamily": "2d"
  }
}
```

推荐 target / deps：

- target：`dp[1][2]`
- deps：`dp[0][2]`、`dp[1][1]`

当前实现：

- 二维 list 自动生成 matrix。
- matrix deps 到 matrix target 会生成 dependency arrow。
- 对象会附加 `dp_formula_substitution`、`dp_dependency_arrow` 等 pattern。
- 右侧本步证据会展示 deps、formula、value、state change。

指标意义：

- `process_pass_rate` 依赖每个关键 DP set 事件的 target / deps / value / state。
- `process_faithfulness` 依赖 formula、teaching.why、invariant 与 deps 一致。

注意：

- 小 DP 表不要抽样跳格。当前 `Tracer.expect_updates()` 可帮助记录 coverage。
- 不要只在最后给完整 dp 表；必须逐步 set 关键单元。

## 12. graph

适用：

- BFS / DFS。
- 连通分量。
- 拓扑排序。
- Dijkstra / Bellman-Ford / 0-1 BFS。
- Kruskal / Prim。
- Tarjan。
- 网络流 / 匹配教学版。

推荐 state：

```json
{
  "graph": {"A": ["B", "C"], "B": ["D"], "C": []},
  "queue": ["B", "C"],
  "dist": {"A": 0, "B": 1, "C": 1},
  "visited": {"A": true, "B": true},
  "current": "A",
  "graph_contract": {
    "submode": "bfs",
    "source": "A",
    "expected_nodes": ["A", "B", "C"]
  }
}
```

推荐 target：

- `node:A`
- `edge:A->B`
- `dist[B]`
- `queue`

当前实现：

- graph dict 自动生成 nodes / edges。
- input_data 中的 graph 也可补充基础图对象。
- state.queue / frontier / heap / open_set 会标记 frontier。
- state.visited 会标记已访问节点。
- state.current / node / u 会标记当前节点。
- path / path_edges / augmenting_path 会高亮路径。
- weights / capacity / flow / residual 会显示边标签。

注意：

- 加权边如果 state.graph 的邻居是 dict / tuple，Scene Compiler 会从邻居中取目标 id，但权重标签主要来自 state.weights / capacity / flow 等 map。
- Dijkstra、网络流等不要只展示最终 dist / flow，必须记录 relax / augmenting path。

## 13. stack / queue / deque

适用：

- 单调栈。
- BFS 队列。
- 单调队列。
- 括号匹配。
- 表达式求值。

推荐 state：

```json
{
  "nums": [73, 74, 75],
  "stack": [0, 1],
  "i": 2,
  "answer": [1, 1, 0],
  "family_contract": {
    "family": "monotonic_stack",
    "submode": "daily_temperatures"
  }
}
```

推荐 target：

- `stack`
- `queue`
- `deque`
- `answer[1]`
- `nums[2]`

当前实现：

- key 为 stack / queue / deque 的一维 list 会使用专用 layout。
- 可以和 array 同帧组合。
- 单调栈的过程证据在特定 pop / answer 场景下会生成 stack pop evidence。

注意：

- 栈中如果存的是原数组下标，teaching 和 state 应明确说明。
- 需要让 deps 指向导致 pop / answer 写入的当前元素和被弹出的候选。

## 14. map / hash table

适用：

- Two Sum。
- 频次统计。
- 前缀和计数。
- 图 dist / parent / indegree。
- Trie / LRU 的辅助映射。

推荐 state：

```json
{
  "nums": [2, 7, 11],
  "seen": {"2": 0},
  "need": 2,
  "i": 1
}
```

推荐 target：

- `seen[2]`
- `count[x]`
- `dist[A]`
- `parent[B]`

当前实现：

- 普通 dict 会生成 map layout。
- map row id 形如 `key[item]`。
- 非数字 key 在 parser 中是 map；数字 key 可能被 parse 为 indexed，但只要 state 暴露对应对象，trace validator 和 renderer 仍可定位。

注意：

- 不要使用 `seen:2`、`dist:A`、`map:seen`。
- map key 最好在 state 中统一转成字符串，避免 Python int key 和 JSON string key 造成对齐问题。

## 15. tree / trie / union-find / recursion_tree

### tree

适用：

- 二叉树遍历。
- LCA。
- 树直径。
- 树形 DP。
- 层序遍历。

推荐 state：

```json
{
  "tree": {
    "nodes": [{"id": "3", "label": "3"}, {"id": "5", "label": "5"}],
    "edges": [["3", "5"]]
  },
  "current": "5",
  "return_values": {"5": 2}
}
```

当前实现：

- `tree` / `binary_tree` / `segment_tree` 且含 nodes / edges 会进入 tree layout。
- `return_values` 和 `return_value` 会触发 `tree_return_value` pattern。

### trie

推荐 state：

```json
{
  "trie": {
    "nodes": [{"id": "root"}, {"id": "root/a"}],
    "edges": [{"from": "root", "to": "root/a", "label": "a"}]
  },
  "word": "app",
  "pos": 1
}
```

当前实现：

- trie 使用 tree renderer，但 container layout 为 `trie`。
- 终止节点、prefix_count 等应放在 node meta 或 state map 中。

### union-find

推荐 state：

```json
{
  "union_find": {
    "parent": {"0": "0", "1": "0", "2": "2"},
    "rank": {"0": 1, "1": 0, "2": 0}
  }
}
```

当前实现：

- `union_find` / `dsu` 需要 dict parent。
- 会生成 node 和 parent edge。
- list parent 只会作为普通 array 展示，不会自动生成 forest。

### recursion_tree

推荐 state：

```json
{
  "recursion_tree": {
    "nodes": [{"id": "root", "label": "[]"}, {"id": "choose1", "label": "[1]"}],
    "edges": [["root", "choose1"]]
  },
  "path": [1],
  "used": [true, false]
}
```

当前实现：

- recursion_tree 使用 tree renderer。
- choice / undo 会通过 op 触发 `backtracking_choice` / `backtracking_undo`。

## 16. heap

适用：

- TopK。
- 堆排序。
- Dijkstra frontier。
- Huffman。
- 合并 K 路链表。

推荐 state：

```json
{
  "heap": [3, 5, 8],
  "k": 3,
  "current": 9
}
```

推荐 target：

- `heap`
- `heap[0]`

当前实现：

- key 为 `heap` 的一维 list 使用 heap layout。
- renderer 会展示堆层级。

注意：

- Python heapq 的数组顺序不是排序数组。teaching 应说明 heap invariant，而不是把它讲成有序列表。
- 如果是 Dijkstra，heap 中元素建议结构化为简单 label 或同步在 state 中提供 dist map。

## 17. string

适用：

- KMP。
- Rabin-Karp。
- Z Algorithm。
- Manacher。
- 滑动窗口字符串。
- 基础匹配。

推荐 state：

```json
{
  "text": "ababc",
  "pattern": "abc",
  "i": 3,
  "j": 1,
  "pi": [0, 0, 1],
  "window": {"left": 1, "right": 3},
  "family_contract": {
    "family": "string",
    "submode": "kmp"
  }
}
```

推荐 target：

- `text[3]`
- `pattern[1]`
- `pi[2]`

当前实现：

- text / pattern / s / t / string 生成 string layout。
- i / j 会作为 cursor。
- pattern 可以根据 i-j 生成 alignment offset。
- window / left/right 会触发 `string_window`。
- fallback_from / fallback_to 或 j_before / j_after 会触发 fallback arc。

注意：

- 字符串算法的 deps 应指向字符和表项，例如 `text[i]`、`pattern[j]`、`pi[j-1]`。
- 不能只记录最终匹配位置。

## 18. geometry

适用：

- 凸包。
- 扫描线。
- 方向判断。
- 线段相交。

推荐 state：

```json
{
  "geometry": {
    "points": [
      {"id": "0", "x": 0, "y": 0},
      {"id": "1", "x": 1, "y": 2}
    ],
    "hull": ["0", "1"],
    "segments": [{"from": "0", "to": "1", "label": "候选边"}],
    "sweep_x": 1
  }
}
```

推荐 target：

- `point:0`
- `points`

当前实现：

- `points` list 或 geometry.points 生成 geometry layout。
- segments、hull、sweep_x / sweep_y 会生成附加对象。
- segment 对象由 compiler 生成，不建议 tracker 直接引用 `segment:*` target。

## 19. range structure

适用：

- 线段树。
- 树状数组。
- 稀疏表。
- 区间查询 / 更新。

推荐表达：

- 线段树：`segment_tree` 使用 nodes / edges，target 用 `node:*`。
- 树状数组：`bit` 使用 array，target 用 `bit[i]`。
- 稀疏表：`st` 使用 matrix，target 用 `st[i][j]`。

推荐 state：

```json
{
  "segment_tree": {
    "nodes": [{"id": "1", "label": "[0,3] sum=10"}],
    "edges": []
  },
  "query": [1, 3],
  "query_path": ["node:1"],
  "cover_path": ["node:1"]
}
```

当前实现：

- `segment_tree` 会按 tree layout 展示。
- `bit` 是普通 array。
- `st` 是 matrix。
- query_path / update_path / cover_path 会触发 range visual patterns。

注意：

- 不要使用未实现的 `range:` target。
- 区间范围应写在 node label、state.query 或 node meta 中。

## 20. math / bit

适用：

- GCD。
- 快速幂。
- 筛法。
- 组合数。
- bitmask。
- lowbit。

推荐 state：

```json
{
  "n": 13,
  "mask": 5,
  "bits": [1, 0, 1],
  "table": [[1, 1], [1, 2]],
  "answer": 8
}
```

推荐 target：

- `bits[0]`
- `table[1][1]`
- `mask`
- `answer`

当前实现：

- `bits` 是 array。
- `table` 是 matrix。
- `mask`、`answer` 是 label。

注意：

- 不要使用 `number:n`。
- 如果要表达二进制贡献，优先用 `bits[i]` 加 teaching.formula。

## 21. linked list

当前 linked list 不是独立 renderer。建议暂用 tree / graph-like nodes + edges 表达：

```json
{
  "tree": {
    "nodes": [{"id": "a", "label": "1"}, {"id": "b", "label": "2"}],
    "edges": [{"from": "a", "to": "b", "label": "next"}]
  },
  "current": "a",
  "prev": null,
  "next": "b"
}
```

推荐 target：

- `node:a`
- `edge:a->b`
- `pointer:current`
- `pointer:prev`

限制：

- 当前没有正式 linked_list layout。
- 双向链表、LRU 的 prev/next 样式需要 renderer 增强。
- 反转链表要显式记录 unlink / link 或 state 中边方向变化，不能只展示最终链。

## 22. ML primitives

ML primitive 是扩展方向，不是当前算法题主路径。

当前 compiler 能识别：

- `ml`
- `model`
- `training`
- `linear_regression`
- `logistic_regression`

以及字段：

- tensor / features / weights / matrix / activations
- batch
- parameters
- loss / loss_curve / loss_history
- gradient / gradients
- computational_graph
- decision_boundary
- epoch
- prediction

除非实验专门评估 ML demo，否则不要让 ML primitive 影响经典算法 benchmark。

## 23. 交互模式

`Interaction` schema 支持：

- `choice`
- `input`
- `judge`

字段：

- `prompt`
- `options`
- `answer`
- `explanation`
- `wrong_explanation`
- `option_explanations`

renderer 当前会：

- 为 choice 渲染多个按钮。
- 为 input 渲染输入框和检查按钮。
- 为 judge 渲染正确 / 错误按钮。
- 展示反馈，并说明反馈来源来自 interaction 字段。

交互设计原则：

- 交互答案必须能从当前 frame 的 state / deps / teaching 得到。
- 不要让 renderer 自行推理下一步。
- 预测下一步、公式填空、判断依赖是否正确，是当前最适合提升教学性指标的交互。

## 24. 新增原语的实施清单

新增视觉原语前必须同步完成：

1. `target_parser.py` 支持新 target。
2. `trace_validator.py` 能判断 target 是否存在。
3. `scene_compiler.py` 能从 state 生成对象。
4. `scene_compiler.py` 能生成必要 visual pattern / evidence。
5. `layout_registry.py` 映射 layout。
6. `export.py` renderer 能展示 layout。
7. `tests/` 中加入 deterministic fixture。
8. benchmark report 能区分新增原语导致的 scene/html failure。

未完成以上步骤时，新算法族应优先用现有原语降级表达。
