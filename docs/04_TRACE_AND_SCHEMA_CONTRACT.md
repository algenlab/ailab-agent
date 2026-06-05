# Trace 与 Schema 合同

## 1. 合同定位

SemanticTrace 是 AlgoLab 的核心中间表示。LLM 只能生成算法语义候选，不能直接生成页面。系统通过执行、校验和编译 SemanticTrace 来生成教学页面。

本文档是 tracker、validator、compiler、renderer 之间的接口合同。

V1 之后，通用 schema 只是最低要求。新增经典算法题必须同时满足对应算法族 trace 合同。算法族合同的目标是让同一套过程校验和演示门禁覆盖一族题，而不是让每道题写专用规则。

优先级：

- 答案正确：`solve`、`trace.result`、`verify` 一致。
- 过程正确：关键状态转移、deps、不变量和覆盖率可校验。
- 演示正确：trace 能讲清每一步，不跳关键步骤，不误导学习者。
- 视觉可运行：SceneGraph 和 HTML 能消费 trace。
- 视觉美观：后置增强。

## 2. 顶层 schema

`trace(input_data)` 必须返回 dict，并能通过 `SemanticTrace` 校验：

```json
{
  "schema_version": "semantic-trace-v1",
  "algorithm": "不同路径",
  "input_data": {"m": 3, "n": 7},
  "result": 28,
  "pseudocode": ["dp[i][j] = dp[i-1][j] + dp[i][j-1]"],
  "events": [
    {
      "step": 0,
      "op": "create",
      "targets": [{"id": "dp"}],
      "state": {"dp": [[1, 1, 1], [1, 1, 1]]},
      "reason": "初始化 DP 表。",
      "code_line": 1
    }
  ]
}
```

要求：

- `schema_version` 必须是 `semantic-trace-v1`。
- `input_data` 必须显式存在，并且与本次请求完全一致。
- `events` 不能为空。
- `events[i].step == i`。
- `result` 必须等于 `solve(input_data)` 的返回值。

## 3. Event schema

每个事件字段：

```json
{
  "step": 0,
  "op": "set",
  "targets": [{"id": "dp[1][2]"}],
  "value": 3,
  "before": 1,
  "after": 3,
  "deps": [{"id": "dp[0][2]"}, {"id": "dp[1][1]"}],
  "role": "answer",
  "reason": "写入上方和左侧路径数之和。",
  "state": {"dp": [[1, 1, 1], [1, 2, 3]], "i": 1, "j": 2},
  "code_line": 3
}
```

必须字段：

- `step`
- `op`
- `targets`
- `state`
- `code_line`

推荐字段：

- `value`
- `before`
- `after`
- `deps`
- `role`
- `reason`
- `teaching`
- `interaction`

## 4. 固定 op 集合

当前合法 op：

- `create`
- `set`
- `mark`
- `unmark`
- `move`
- `compare`
- `link`
- `unlink`
- `push`
- `pop`
- `enter`
- `exit`
- `explain`

新增算法通常不需要新增 op。只有现有 op 无法表达新的通用语义动作时，才允许扩展 schema、validator、compiler、renderer 和测试。

## 5. Target id 规范

推荐 target：

```text
数组/表格：nums[0]、dp[1][2]
切片：text[2:5]
哈希表：seen[2]、dist[B]、count[x]
图节点/边：node:A、edge:A->B
指针：pointer:left、pointer:mid
递归帧：frame:dfs(2)
几何点：point:3
字符串字符：text[3]、pattern[2]
容器：stack、queue、heap、tree、trie、frames、points、string
```

禁止在当前实现中直接使用未支持的新前缀 target，例如：

```text
range:1-3
number:n
interval:2-5
flow:A->B
```

这些前缀会被当前 trace validator 视为旧式冒号 target 或普通 symbol，不能稳定进入 SceneGraph。若要把它们变成正式合同，必须同步扩展：

- `algolab/compiler/target_parser.py`
- `algolab/verification/trace_validator.py`
- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/*`
- 对应 regression tests

在完成这些实现前，新算法应优先用已支持的数组、表格、节点、边、指针、frame、point、symbol 和容器 target 表达。

可落地替代表达：

```text
区间：用 nums[2:5]、query[0]、query[1]，或 tree 节点 label/meta 表达覆盖范围。
数字：用 n、mask、bits[0]、factor[2]、table[3][4]。
线段树节点：用 node:seg_1_4 或 node:seg(1,4)，前提是 state 中的 tree / segment_tree nodes 明确包含该 id。
网络流容量：用 cap[A->B]、flow[A->B] 或 edge:A->B + state 中的 capacity/flow map。
```

禁止旧写法：

```text
type / target       -> 必须改为 op / targets
seen:2              -> seen[2]
dist:A              -> dist[A]
map:seen            -> seen
seen['2']           -> seen[2]
```

## 6. Deps 规范

`deps` 表示当前操作依赖哪些对象。

必须提供 deps 的情况：

- DP 状态转移。
- 图搜索首次访问节点。
- 哈希表命中 complement。
- 单调栈弹出并写答案。
- 二分根据 mid 收缩区间。
- 树递归从子树返回结果。

示例：

```json
{
  "op": "set",
  "targets": [{"id": "dp[2][3]"}],
  "deps": [{"id": "dp[1][3]"}, {"id": "dp[2][2]"}]
}
```

## 7. State 规范

`state` 是当前帧可视化和过程校验的主要证据。

要求：

- 必须包含重建主视图所需的关键变量。
- DP 应包含完整或必要局部 `dp` 表。
- 图搜索应包含 `graph`、`queue` / frontier、`dist` / visited。
- 数组指针应包含数组、指针、窗口或区间。
- 栈队列应包含容器内容和当前扫描下标。
- 哈希表应包含 map 当前状态。

以下划线开头的 state 字段为内部元信息，编译 SceneGraph 时可隐藏，例如 `_trace_meta`。

## 8. 算法族 Trace 合同

### 8.1 通用族级要求

所有 family core case 必须满足：

- 有初始化事件。
- 有主循环或递归过程中的关键事件。
- 有答案事件或最终结果可定位。
- 关键状态变化不能只写自然语言，必须进入 `state`。
- 依赖型步骤必须提供 `deps`。
- 小规模样例不能只给最终状态。
- `reason` 必须解释当前操作的算法原因，而不是重复“执行下一步”。

如果某个算法族暂时不能强校验，trace 仍需尽量完整，但 report 必须标记为 `process_fallback` 或 `process_uncovered`。

### 8.2 动态规划

适用：

- 一维 DP、二维 DP、背包、LCS、编辑距离、区间 DP、树形 DP、状态压缩 DP、数位 DP 入门。

必须记录：

- 初始化：数组、表格、边界条件或初始状态。
- 转移：`targets` 指向当前状态，`deps` 指向来源状态。
- 当前值：`value`、`before` / `after` 或能从 `state` 中读出。
- 遍历变量：例如 `i`、`j`、`k`、`capacity`、`mask`、`digit`。
- 最终答案位置：例如 `dp[n-1]`、`dp[m-1][n-1]`、`dp[root][1]`。
- 明确 DP 合同：关键事件的 `state["dp_contract"]` 必须声明当前容器、答案位置和小规模 full-trace 期望更新。

推荐 state：

```json
{"dp": [[1, 1], [1, 2]], "i": 1, "j": 1, "formula": "dp[i][j] = dp[i-1][j] + dp[i][j-1]"}
```

推荐 `dp_contract`：

```json
{
  "containers": ["dp"],
  "answer_position": "dp[1][1]",
  "expected_targets": ["dp[1][1]"],
  "subfamily": "2d"
}
```

字段含义：

- `containers`：当前 DP 容器名称，例如 `["dp"]`、`["dp_take", "dp_skip"]`。
- `answer_position`：最终答案所在 target，必须在 `role="answer"` 的事件 `targets` 或 `deps` 中出现。
- `expected_targets`：小规模 full-trace 样例必须逐个写出的关键 DP target。
- `subfamily`：子族标签，例如 `1d`、`2d`、`knapsack_01`、`complete_knapsack`、`bounded_knapsack`、`lcs`、`edit_distance`、`interval_dp`、`tree`、`state_compression`、`digit_dp`。
- 背包类 trace 必须给出可区分子模式的信号：优先使用 `dp_contract.subfamily`，也可以在 `state` 中补充 `dp_mode` 或 `knapsack`；多重背包还必须在 `state` 中保留 `weights`、`values`、`counts` 和 `capacity`，避免把物品数量上限丢给自然语言解释。
- 数位 DP 入门版默认按 `n` 统计 `1..n` 中不含 forbidden digit 的数量，默认 forbidden digit 为 7；如果需要改变边界，`state` 必须用 `forbidden_digit`、`include_zero` 或 `count_range` 明确说明。

启用 `dp_contract` 后，process validator 会阻塞以下情况：

- 缺少 `create` 初始化事件，或初始化事件的 `state` 没有 DP 容器。
- 关键 `set` 事件缺少 `targets`、`deps`、`value` / `before` / `after` 或 `state`。
- 关键 `set` 事件的 `state` 缺少 DP 容器或循环变量，例如 `i`、`j`、`k`、`capacity_index`、`capacity`、`mask`、`current`。
- 转移事件缺少可复原公式，例如 `state["formula"]` 或 `teaching.formula`。
- `answer_position` 没有被答案事件明确引用。
- `expected_targets` 中的小规模关键更新没有对应 `set` 事件。

禁止：

- 只给最终 DP 表。
- 转移事件没有 deps。
- `reason` 只写“更新 dp”。
- 小规模样例跳过中间状态。

### 8.3 数组指针、窗口和前缀结构

适用：

- 二分、二分答案、双指针、滑动窗口、快慢指针、前缀和、差分、二维前缀。

必须记录：

- 指针位置：`left`、`right`、`mid`、`slow`、`fast`、`i`、`j`。
- 窗口或区间：用 state 字段和 `nums[l:r]` target 表达。
- 移动原因：比较结果、约束是否满足、窗口是否收缩。
- 前缀/差分递推：当前项和来源项。
- 明确数组指针合同：关键事件的 `state["array_contract"]` 必须声明子模式和小样例关键更新。

推荐 `array_contract`：

```json
{
  "submode": "sliding_window",
  "expected_targets": ["pointer:left", "pointer:right", "nums[0:3]"]
}
```

字段含义：

- `submode`：必填，当前支持 `binary_answer`、`two_pointer`、`sliding_window`、`prefix_sum`、`difference_array`、`fast_slow`。
- `expected_targets`：小规模 full-trace 样例必须覆盖的关键指针、窗口、前缀项或差分项。

子模式要求：

- `binary_answer`：记录答案域的 `left`、`right`、`mid`，每次收缩前要有 mid 比较，`mid` 必须等于 `(left + right) // 2`。
- `two_pointer`：记录 `left` / `right` 或 `i` / `j`，指针值必须在数组边界内，每次移动要说明比较结果。
- `sliding_window`：记录 `left`、`right`、窗口约束和 `window_sum` 等可复核状态，窗口边界不能无解释跳变。
- `prefix_sum`：逐步写出 `prefix[i]` 或 `prefix_sum[i]`，当前项必须等于来源数组前缀和。
- `difference_array`：逐步写出 `diff[i]` 或 `difference[i]`，区间更新后的差分值必须能由 `updates` 复核。
- `fast_slow`：记录 `slow`、`fast`，指针必须在数组状态表达的可达范围内。

启用 `array_contract` 后，process validator 会阻塞以下情况：

- 缺少或未知 `submode`。
- `expected_targets` 中的小规模关键 target 没有被 `set`、`move`、`mark`、`push` 或 `pop` 事件覆盖。
- `prefix_sum` 的前缀项与 `nums` 不一致。
- `difference_array` 的差分项与 `nums` 和已处理 `updates` 不一致。
- `sliding_window` 的指针越界、窗口跳变或 `window_sum` 与窗口内容不一致。
- `two_pointer`、`fast_slow`、`binary_answer` 的指针越界。
- 二分类 trace 出现错误 `mid` 计算、缺少 mid 比较或缺少区间收缩证据。

禁止：

- 指针直接跳到最终位置。
- 二分收缩区间但不记录 mid 比较。
- 前缀和只给最终数组。

### 8.4 图算法

适用：

- BFS、DFS、拓扑排序、连通分量、二分图染色、最短路、MST、Tarjan、匹配和网络流教学版。

必须记录：

- 图结构：`graph`、`nodes` / `edges` 或等价 state。
- 当前节点和当前边。
- frontier：`queue`、`stack`、`heap` 或 recursion frame。
- 访问状态：`visited`、`dist`、`parent`、`color`、`indegree`、`dfn`、`low`、`match`、`flow`。
- 边检查、首次访问、松弛、选边、增广等关键事件。
- 明确图合同：关键事件的 `state["graph_contract"]` 必须声明子模式和该模式的关键覆盖对象。

推荐 `graph_contract`：

```json
{
  "submode": "dijkstra",
  "source": "A",
  "expected_relax_edges": ["A->B"]
}
```

字段含义：

- `submode`：必填，当前支持 `bfs`、`dfs`、`dijkstra`、`topological_sort`、`mst`、`tarjan`、`network_flow`。
- P13.3 后基础图和最短路/MST 的强校验还支持 `connected_components`、`bipartite_coloring`、`bellman_ford`、`floyd_warshall`、`zero_one_bfs`。
- `source` / `sink`：源点和汇点，BFS/DFS/Dijkstra/网络流使用。
- `expected_nodes`：小图 full-trace 必须覆盖的节点。
- `expected_relax_edges`：Dijkstra、Bellman-Ford、0-1 BFS 必须记录 relax 的边。
- `expected_edges`：MST 必须记录选择或拒绝的边。
- `expected_paths`：网络流必须记录的增广路径。

子模式要求：

- BFS：起点入队、出队、检查边、首次访问、距离更新。
- DFS：进入节点、检查边、递归进入、退出节点。
- 连通分量：每个未访问起点开启新分量，节点只能进入一个分量，分量覆盖必须等于图中节点集合。
- 二分图染色：每个未染色连通块从颜色 0 开始，边两端颜色必须相反，重复访问不能改色。
- 拓扑：入度变化、入队原因、弹出顺序。
- Dijkstra：堆弹出、忽略过期项、relax 前后距离。
- Bellman-Ford：轮次、边松弛、是否变化。
- Floyd：`k` 阶段和 `dist[i][k] + dist[k][j]` 依赖。
- 0-1 BFS：双端队列 frontier，0 权边松弛进队首，1 权边松弛进队尾，dist 只能按 0/1 权重更新。
- Kruskal：排序边、查找根、选边/弃边原因。
- Tarjan：`dfn`、`low`、stack、SCC 形成。
- 网络流：增广路径、瓶颈、flow/capacity 更新。

启用 `graph_contract` 后，process validator 会阻塞以下情况：

- BFS 缺少 queue/frontier、pop、边检查、首次访问，或出现重复首次访问、错误 dist、queue 跳变。
- DFS 缺少 stack / recursion frame frontier，或缺少 `frame:*` 的 enter/exit。
- 连通分量缺少分量开始/收集事件、同一节点进入多个分量，或最终分量集合与图不一致。
- 二分图染色缺少 color state、相邻点同色，或重复访问时颜色不连续。
- Dijkstra 缺少 heap/frontier、edge relax、`old_dist`、`new_dist`、parent/predecessor，或对负权输入没有拒绝 / 降级说明。
- Bellman-Ford 缺少 round/iteration、relax 前后距离，或边松弛结果与 `old_dist + weight` 不一致。
- Floyd-Warshall 缺少 `k` 阶段、矩阵 state 或 `dist[i][k] + dist[k][j]` 依赖。
- 0-1 BFS 缺少 deque/frontier、0/1 权重约束、relax 前后距离或 deque 方向证据。
- 拓扑排序缺少 indegree 变化或入队原因。
- MST 缺少选边 / 弃边原因或 union-find 状态。
- Tarjan 缺少 dfn、low、stack 更新或 SCC component 弹栈事件。
- 网络流缺少 augmenting path、bottleneck、flow/capacity 或 flow 更新事件。

禁止：

- 只给最终 dist / parent。
- 访问节点但不记录来源边。
- relax 没有 before/after。
- 网络流直接写最终最大流。

### 8.5 字符串算法

适用：

- KMP、Rabin-Karp、Z Algorithm、Manacher、字符串滑动窗口、Trie 字符路径。

必须记录：

- 当前文本指针和模式指针。
- 表结构：`pi`、`z`、`radius`、`hash` 或窗口计数。
- 匹配、失配、回退、扩展或窗口移动原因。
- 当前字符 target：`text[i]`、`pattern[j]`。
- 明确算法族合同：关键事件的 `state["family_contract"]` 必须声明 `family`、`submode` 和小样例关键事件。

推荐 `family_contract`：

```json
{
  "family": "string",
  "submode": "kmp",
  "expected_tables": ["pi"],
  "expected_events": ["compare", "fallback"]
}
```

启用 `family_contract.family="string"` 后，process validator 会阻塞以下情况：

- 缺少 `text` / `pattern`、文本指针或模式指针。
- 缺少 `pi` / `z` / `radius` / `hash` 等表结构。
- 缺少 `text[i]` / `pattern[j]` 字符 target。
- 缺少失配、回退、扩展或窗口移动原因。

禁止：

- 只给匹配结果下标。
- prefix/z/radius 表没有逐步解释。
- KMP 失配回退没有 deps 或原因。

### 8.6 树、回溯和递归

适用：

- 树遍历、BST、LCA、树直径、树形 DP、全排列、组合、N 皇后、子集、数独、分治。

必须记录：

- 递归帧：`frame:dfs(...)` 或 `frames`。
- 当前节点或当前选择。
- 进入、选择、剪枝、记录答案、撤销、返回。
- 子树返回值或 path/used 状态。
- 明确算法族合同：树和回溯关键事件的 `state["family_contract"]` 必须声明对应 family。

推荐树递归 `family_contract`：

```json
{
  "family": "tree",
  "submode": "postorder",
  "expected_nodes": ["1"],
  "expected_frames": ["frame:dfs(1)"]
}
```

推荐回溯 `family_contract`：

```json
{
  "family": "backtracking",
  "submode": "permutation",
  "expected_events": ["choose", "record", "undo"]
}
```

启用 `family_contract.family="tree"` 后，process validator 会阻塞以下情况：

- 缺少 `tree` state 或当前节点 `current`。
- 缺少 `frame:*` 的 enter/exit。
- 缺少子树返回值、聚合结果或等价状态。
- `expected_nodes` / `expected_frames` 没有被 targets 或 deps 覆盖。

启用 `family_contract.family="backtracking"` 后，process validator 会阻塞以下情况：

- 缺少 `recursion_tree` / `search_tree`、`path` 或 `used`。
- 缺少 choose、record、undo 事件。
- `path` 或 `used` 出现无解释跳变。

禁止：

- 回溯只给最终解集。
- 递归没有 enter/exit 或等价状态。
- 撤销步骤缺失导致 path/used 跳变。

### 8.7 数据结构算法

适用：

- 栈、队列、单调栈、单调队列、堆、Trie、并查集、链表、LRU/LFU、区间结构。

必须记录：

- 容器 before/after 或完整当前状态。
- push/pop/union/find/query/update 的对象。
- 结构不变量相关字段：stack order、heap top、parent、rank/size、trie count、segment node meta。
- 与原数组或输入元素的 deps 关系。
- 堆、Trie 和链表必须使用 `state["family_contract"]` 显式声明结构合同。

推荐堆 `family_contract`：

```json
{
  "family": "heap",
  "submode": "topk",
  "expected_events": ["push", "pop"]
}
```

推荐 Trie `family_contract`：

```json
{
  "family": "trie",
  "submode": "insert_search",
  "expected_events": ["create_node", "terminal", "prefix_count"]
}
```

推荐链表 `family_contract`：

```json
{
  "family": "linked_list",
  "submode": "reverse",
  "expected_events": ["move_pointer", "link_change"]
}
```

启用这些 `family_contract` 后，process validator 会阻塞以下情况：

- 堆缺少 push/pop、完整 `heap` state，或缺少 `heap_top` / `heap[0]` 证据。
- Trie 缺少字符路径节点创建/访问、terminal 标记或 count / prefix_count。
- 链表缺少 pointer/current/prev/next 证据，或缺少 next/prev 改变事件。

禁止：

- 只标记“加入堆”但不更新 heap state。
- union-find 不记录 parent 变化。
- 链表只给最终 next 关系。

### 8.8 哈希、排序和贪心

适用：

- Two Sum、频次统计、前缀和计数、插入排序、快速排序分区、快速选择、跳跃游戏、区间贪心。

必须记录：

- 哈希表：`seen` / `count` 等 map 当前状态，当前 key、命中状态、写入事件和答案依赖。
- 排序：当前数组、`i` / `j` / `key` 等指针，比较、移动、写回事件，以及有序前缀证据。
- 贪心：当前扫描位置、局部选择依据、当前最优状态和候选状态，例如跳跃游戏的 `reach`、`previous_reach`、`candidate_reach`。

推荐哈希 `hash_contract`：

```json
{"submode": "two_sum"}
```

推荐排序 `sorting_contract`：

```json
{"submode": "insertion_sort"}
```

推荐贪心 `greedy_contract`：

```json
{"submode": "jump_game"}
```

启用这些合同后，process validator 会阻塞以下情况：

- 哈希命中 `seen[key]` 前没有在 state map 中写入该 key。
- Two Sum 的 `need`、命中状态或答案依赖与当前 `nums` / `target` 不一致。
- 插入排序的有序前缀不升序，或最终结果不保持输入多重集。
- 跳跃游戏的 `candidate_reach` / `reach` 不满足 `max(previous_reach, i + nums[i])`。

禁止：

- 哈希表只在自然语言中声明命中，不记录 `seen`。
- 排序只给最终有序数组，缺少中间移动或比较。
- 贪心只给最终布尔值，不记录局部选择依据。

### 8.9 数学、位运算和几何

适用：

- GCD、快速幂、筛法、组合数、bitmask、lowbit、凸包、方向判断、扫描线。

必须记录：

- 数学变量变化：余数、指数、当前乘积、mask、lowbit、组合表项。
- 几何变量：当前点、候选边、cross/orientation、hull。
- 每步公式或判断依据。

禁止：

- 只给最终数值。
- 几何删除点时不记录 cross/orientation。
- bitmask 枚举不记录 mask 与子集对应关系。

## 9. Tracer 兼容 API 用法

`Tracer` 是旧版兼容 API，用于历史 benchmark 和单元测试。新生成的 tracker 应优先使用 `TraceSession` DSL；只有维护旧产物时才直接使用 `Tracer`：

```python
def trace(input_data):
    tracer = Tracer(
        input_data,
        algorithm="不同路径",
        pseudocode=["dp[i][j] = dp[i-1][j] + dp[i][j-1]"],
    )
    dp = [[1] * input_data["n"] for _ in range(input_data["m"])]
    tracer.create("dp", state={"dp": [row[:] for row in dp]}, reason="初始化 DP 表。")
    tracer.result(dp[-1][-1])
    return tracer.to_trace()
```

常用方法：

- `create(target, ...)`
- `set(target, ...)`
- `mark(target, ...)`
- `unmark(target, ...)`
- `move(target, ...)`
- `compare(targets, ...)`
- `link(target, ...)`
- `unlink(target, ...)`
- `push(target, ...)`
- `pop(target, ...)`
- `enter(target, ...)`
- `exit(target, ...)`
- `explain(target=None, ...)`
- `table(name, rows)`
- `expect_updates(name, count)`
- `result(value)`
- `to_trace()`

`unmark`、`link`、`unlink`、`enter`、`exit` 只是在固定 SemanticTrace op 上提供便捷封装，不引入新 op。它们适合表达取消标记、建立 / 删除关系、进入 / 退出递归帧或作用域。维护旧 `Tracer` 代码时仍应优先复用这些固定 op、已有 target 规范和 state 证据，不要因为便捷方法存在而新增 target 前缀或 renderer 规则。

二维表或行长不一致的表可用 `table(name, rows)` 生成类型化引用。`table.cell(row, col)` 只返回真实存在的 `name[row][col]` target；越界会在 tracker 执行时抛错。`table.state()` 返回 `{name: rows}` 的深拷贝，可直接传给事件 `state`。

## 10. 正确示例

DP 转移：

```python
tracer.compare(
    [f"dp[{i}][{j}]"],
    deps=[f"dp[{i-1}][{j}]", f"dp[{i}][{j-1}]"],
    state={"dp": [row[:] for row in dp], "i": i, "j": j},
    role="candidate",
    reason="当前位置只能从上方或左侧到达。",
    code_line=3,
)
dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
tracer.set(
    f"dp[{i}][{j}]",
    value=dp[i][j],
    deps=[f"dp[{i-1}][{j}]", f"dp[{i}][{j-1}]"],
    state={"dp": [row[:] for row in dp], "i": i, "j": j},
    role="answer",
    reason="写入上方和左侧路径数之和。",
    code_line=3,
)
```

## 11. 错误示例

旧字段：

```json
{"step": 0, "type": "set", "target": "dp[1][2]"}
```

缺少输入：

```json
{"schema_version": "semantic-trace-v1", "algorithm": "二分查找", "events": []}
```

旧 map target：

```json
{"targets": [{"id": "seen:2"}]}
```

自然语言代替状态：

```json
{"op": "explain", "reason": "这里做动态规划", "state": {}}
```

## 12. Repair 原则

校验失败后，repair prompt 应优先修复：

1. schema 字段错误。
2. `input_data` 缺失或不一致。
3. `solve_result != trace.result`。
4. target id 不合法。
5. 关键步骤缺失。
6. DP / BFS / 二分等过程不变量不满足。
7. SceneGraph 无可渲染对象。

禁止通过删除 validator、放宽 release gate 或让 renderer 猜过程来 repair。
