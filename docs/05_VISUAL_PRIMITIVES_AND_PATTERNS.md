# 视觉原语与页面模式

## 1. 文档定位

本文档定义 AlgoLab 自动版 VisuAlgo 中可复用的视觉原语。新增算法应优先映射到这些原语，而不是手写专用页面。

V1 之后的短期重点是算法族正确性，不是视觉 polish。视觉原语的责任是稳定承载语义对象、依赖关系和过程证据，保证后续能做教学页面。新增算法族时，先确认答案正确、过程正确和演示语义正确，再增强动画和布局。

每个视觉原语都应说明：

- 适用算法。
- 输入 state 格式。
- target id 格式。
- 默认布局。
- 支持的高亮方式。
- 支持的交互。
- 典型页面效果。

V1 的算法覆盖目标是尽可能覆盖经典算法教学场景。算法族可以很多，但视觉原语必须收敛。新增算法优先进入以下通用形态：

- 线性结构：array、linked list、stack、queue、deque。
- 表格结构：matrix、DP table、prefix table。
- 图结构：graph、tree、trie、union-find forest、recursion tree。
- 优先级结构：heap、priority queue。
- 区间结构：segment tree、Fenwick tree、sparse table。
- 文本结构：string、pattern、prefix function。
- 数学结构：number line、bit mask、factor table、mod table。
- 几何结构：point set、line segment、polygon、sweep line。

## 1.1 覆盖矩阵

新增算法族实施前，先按下表选择视觉原语。表中“当前可落地”表示可以用现有 target parser、scene compiler 和 renderer 的基础能力表达；“需扩展”表示文档允许规划，但实施前必须补 parser / validator / compiler / renderer / tests。

表中的 `i`、`j`、`key`、`A` 是说明占位符。真正写入 trace 时必须替换成具体 id，例如 `nums[3]`、`dp[1][2]`、`seen[7]`、`node:A`。

| 算法族 | 推荐视觉原语 | 当前可落地表达 | 需扩展项 |
|---|---|---|---|
| 数组基础、前缀和、差分、前缀积、原地标记 | array + pointer、matrix | `nums[3]`、`prefix[3]`、`product[3]`、`diff[3]`、`grid[1][2]` | 二维前缀的区域框选可先用 deps 多格表达，后续可加区间高亮 |
| 二分、二分答案、双指针、滑动窗口、快慢指针、荷兰国旗 | array + pointer | `nums[3]`、`pointer:left`、`pointer:right`、`pointer:mid`、`pointer:slow`、`pointer:fast`、`nums[2:5]` | 指针样式和窗口带状高亮可继续增强 |
| 排序与选择、分治排序、快速选择 | array + pointer、heap、recursion_tree | `nums[3]`、`pointer:i`、`pointer:j`、`heap[0]`、`frame:sort(0,4)` | 归并分治可组合 recursion_tree；稳定分区动画需增强 |
| 栈、队列、双端队列、单调结构、MinStack、队列实现栈、栈实现队列 | stack / queue / deque、array | `stack`、`queue`、`deque`、`min_stack`、`nums[3]` | 容器元素到原数组下标的联动样式需增强 |
| 哈希表与集合 | map / hash table、array | `seen[7]`、`count[x]`、`dist[A]` | 集合可用 map value 为 true 表达 |
| 链表与 LRU / LFU 链表部分 | linked list、map | 当前用 `nodes` + `edges` 映射到 graph/tree 风格，`pointer:head` 等指针可表达 | 需要正式 linked_list layout、next/prev 专用边样式 |
| 字符串匹配、KMP、Rabin-Karp、Z、Manacher | string、array、matrix | `text[3]`、`pattern[1]`、`pi[2]`、`z[4]`、`radius[5]` | 双行对齐、回退弧线和哈希窗口可增强 |
| 动态规划 | matrix / DP table、array、tree、recursion_tree、math / bit | `dp[3]`、`dp[1][2]`、`tree`、`frames`、`bits[2]` | 状态压缩 DP 可先用 bit 数组表达，后续加 bitmask 原语 |
| 贪心、区间调度、活动选择、跳跃游戏、分发糖果、合并区间、最少箭数、Huffman | array + pointer、heap、geometry、tree | `intervals[3]` 可先用数组 / matrix，`jump[3]`、`candy[3]`、`heap[0]` | interval 专用条带图可扩展；Huffman 树可用 tree |
| 图遍历、连通性、拓扑、环检测、二分图、欧拉路径 | graph、queue、stack、map | `node:A`、`edge:A->B`、`queue`、`stack`、`color[A]`、`indegree[A]` | 欧拉路径的边消耗顺序可先用 role 标记，后续加 path trail |
| SCC、割点、桥、Tarjan | graph、stack、map | `node:A`、`edge:A->B`、`dfn[A]`、`low[A]`、`stack` | lowlink 专用面板需规范字段 |
| 最短路、SPFA、0-1 BFS、A*、差分约束 | graph、heap、queue、map | `dist[A]`、`heap[0]`、`queue`、`edge:A->B`、`node:A`、`relax_count[A]` | A* 的启发式 `h/f/g` 可用 map 表达；差分约束用 shortest-path 视图 |
| MST、匹配、网络流入门 | graph、union-find、queue、map | `edge:A->B`、`node:A`、`union_find`、`parent[A]`、`match[A]`、`cap[A->B]`、`flow[A->B]` | residual capacity、flow/capacity 边标签需要 renderer 增强 |
| 树与二叉树 | tree、recursion_tree、queue | `tree` 的 nodes/edges、`node:3`、`edge:3->5`、`frame:dfs(3)` | 多返回值气泡和子树聚合视图可增强 |
| 堆与优先队列 | heap、array、tree | `heap`、`heap[0]` | 双堆中位数需要两个 heap 容器并排布局 |
| Trie 与自动机 | trie、string、graph | `trie` nodes/edges、`text[3]`、`node:abc` | fail 指针可用 `edge:u->v` + role 表达，后续加虚线边 |
| 并查集 | union-find、array、graph | `union_find`、`parent[1]`、`node:1`、`edge:1->0` | parent 为 list 时先用 array，forest 视图需要 dict parent |
| 回溯、递归、分治、汉诺塔、主定理示例 | recursion_tree、array、tree | `frame:dfs(2)`、`frames`、`path[1]`、`used[1]`、`tower[0]` | 分治区间可先用数组切片，后续加区间节点 |
| 位运算、数论、组合数学、GCD、快速幂、筛法、扩展欧几里得、Brian Kernighan | math / bit、array、matrix | `bits[2]`、`factor[2]`、`table[3][4]`、`mask`、`a`、`b`、`gcd` | 不使用 `number:` 前缀；数字线是规划增强 |
| 计算几何、扫描线 | geometry、array、queue | `point:3`、`points[3]`；线段由 state 中的 `segments` 生成 | `segment:` 只由 scene compiler 生成，不建议 tracker 直接引用 |
| 线段树、树状数组、稀疏表 | range structure、tree、array、matrix | `segment_tree` nodes/edges、`bit[4]`、`st[2][3]` | 不使用 `range:` 前缀；区间覆盖用 node label/meta 表达 |
| 缓存与设计题 | linked list、map、stack / queue | `cache[7]`、`node:7`、`edge:7->9`、`queue` | LRU 双向链表需要 linked_list layout 增强 |

## 1.2 当前实现状态

现有稳定布局来自 runtime capabilities 和 Scene Compiler：

- 稳定：array、matrix、graph、queue、stack、map、tree、heap、trie、union_find、recursion_tree、string、geometry。
- 可组合但还不是独立布局：linked list、range structure、math / bit。
- 扩展方向：ML primitives、number line、interval timeline、residual network、bitmask board。

实施原则：

- 能用稳定布局表达时，不新增 target 前缀。
- 新 target 前缀不得只写进文档，必须同步实现和测试。
- renderer 不按算法名猜页面，只按 SceneGraph 对象和 layout meta 渲染。
- benchmark 扩算法覆盖时，优先补 trace contract、state 字段、deps 和 process validator；只有现有原语无法承载语义对象时才扩 renderer。
- 视觉效果不足不能作为跳过过程校验的理由。可以先用稳定原语朴素展示，但不能让 trace 缺关键状态。

## 1.3 算法族扩展时的视觉决策

执行 AI 新增算法族或子模式前，按下面顺序判断：

1. 现有原语能否表达主状态。
2. 现有 target 语法能否定位关键对象。
3. `deps` 能否表达依赖关系。
4. SceneGraph 是否能生成对象、mark、arrow 和 state。
5. 如果视觉不够美观，是否可以先用现有布局降级展示。
6. 只有语义对象无法稳定定位时，才新增 parser/compiler/renderer 能力。

常见决策：

| 算法族需求 | 优先做法 | 不要做 |
|---|---|---|
| 区间覆盖 | 用 `segment_tree` nodes/edges、`bit[i]`、`st[i][j]` 和 node meta | 直接引入未实现的 `range:` target |
| 网络流容量 | 用 `edge:A->B`、`cap[A->B]`、`flow[A->B]` 和 state map | 直接引入未实现的 `flow:` target |
| 数字状态 | 用 `mask`、`bits[i]`、`factor[i]`、`table[i][j]` | 直接引入未实现的 `number:` target |
| 链表 | 暂用 nodes/edges + pointer + map 表达 | 为某道链表题写专用页面 |
| 贪心区间 | 先用 array/matrix 表达区间起止和排序顺序 | 在 trace 里使用未实现的 `interval:` target |
| 字符串对齐 | 先用 string + array + pointer 表达 | 让 renderer 按算法名猜 KMP/Z/Manacher |

## 2. array + pointer

适用：

- 二分查找。
- 二分答案。
- 双指针。
- 滑动窗口。
- 快慢指针。
- 插入排序。
- 快速排序分区。
- 快速选择。
- 前缀和 / 差分数组。
- Two Sum 的数组扫描。

state：

```json
{"nums": [1, 3, 5], "left": 0, "right": 2, "mid": 1}
```

target：

- `nums[0]`
- `nums[2]`
- `pointer:left`
- `pointer:right`
- `pointer:mid`

默认布局：

- 水平数组。
- 指针显示在单元格上方或下方。
- 当前窗口用带状背景标出。

交互：

- 点击单元格查看当前值和角色。
- 点击指针查看移动原因。
- 二分可预测下一次区间。

## 3. matrix / DP table

适用：

- 不同路径。
- LCS。
- 编辑距离。
- 背包。
- 省份数量的邻接矩阵辅助视图。
- 区间 DP。
- 数位 DP 表。
- Floyd-Warshall。
- 二维前缀和。
- 稀疏表。

state：

```json
{"dp": [[1, 1, 1], [1, 2, 3]], "i": 1, "j": 2}
```

target：

- `dp[1][2]`
- `grid[0][3]`
- `isConnected[2][1]`

默认布局：

- 二维表格。
- 当前格高亮。
- deps 格子用次级高亮。
- 依赖箭头从 deps 指向当前格。
- 公式显示在表格旁或下方。

交互：

- 预测下一格。
- 点击依赖格显示来源。
- 展开当前转移公式。

典型页面效果：

```text
dp[i][j] = dp[i-1][j] + dp[i][j-1]
```

## 4. graph

适用：

- BFS。
- DFS。
- 拓扑排序。
- Dijkstra 基础版本。
- Bellman-Ford。
- Floyd-Warshall 的节点松弛视图。
- 0-1 BFS。
- A* 基础演示。
- 连通分量。
- 二分图染色。
- 强连通分量。
- 割点和桥。
- Kruskal / Prim。
- 二分图匹配和增广路径。
- Edmonds-Karp 网络流教学版。

state：

```json
{"graph": {"A": ["B", "C"]}, "queue": ["B", "C"], "dist": {"A": 0, "B": 1}}
```

target：

- `node:A`
- `edge:A->B`

默认布局：

- 节点-边图。
- 当前节点高亮。
- frontier / queue 节点使用统一角色色。
- 当前边加粗或闪烁。

交互：

- 点击节点查看距离、访问状态和父节点。
- 点击边查看是否被松弛或访问。
- BFS 可预测下一个出队节点。

## 5. stack / queue / deque

适用：

- 单调栈。
- BFS 队列。
- 括号匹配。
- 滑动窗口候选队列。
- 单调队列。
- 表达式求值。
- 循环队列。

state：

```json
{"stack": [0, 1, 5], "i": 6, "temperatures": [73, 74]}
```

target：

- `stack`
- `queue`
- `deque`

默认布局：

- 栈垂直显示，顶部明确。
- 队列水平显示，head / tail 明确。
- 与数组视图联动显示下标。

交互：

- 点击元素显示原数组下标。
- 弹出时显示为什么不再需要该候选。
- 入栈 / 入队时显示维护的不变量。

## 6. map / hash table

适用：

- Two Sum。
- 频次统计。
- 前缀和计数。
- BFS / Dijkstra 的距离表。
- 分组异位词。
- 去重集合。
- LRU / LFU 的 key 到节点映射。

state：

```json
{"seen": {"2": 0, "7": 1}, "i": 1, "target": 9}
```

target：

- `seen[2]`
- `dist[B]`
- `count[x]`

默认布局：

- key-value 表。
- 当前查询 key 高亮。
- 命中或未命中状态明确。

交互：

- 点击 key 查看来源下标或更新步骤。
- Two Sum 可显示 complement 查找过程。

## 7. tree

适用：

- 二叉树 DFS。
- BST。
- LCA。
- 路径和。
- 树直径。
- 树形 DP。
- 层序遍历。
- 序列化 / 反序列化。
- 平衡树判断。

state：

```json
{"tree": {"nodes": [{"id": "3"}], "edges": [["3", "5"]]}, "current": "5"}
```

target：

- `node:3`
- `edge:3->5`

默认布局：

- 层级树布局。
- 当前递归路径高亮。
- 返回值可显示在节点旁。

交互：

- 点击节点查看左右子树返回值。
- 展开递归调用栈。

## 8. heap

适用：

- TopK。
- 堆排序。
- Huffman。
- 合并 K 路链表。
- 数据流中位数。
- 任务调度。
- Dijkstra 优先队列。

state：

```json
{"heap": [4, 5, 6], "k": 3, "x": 7}
```

target：

- `heap`
- `heap[0]`

默认布局：

- 堆数组和树形视图双视图。
- 堆顶突出显示。
- push / pop 时显示调整路径。

交互：

- 点击堆节点查看数组下标。
- TopK 可显示“为什么丢弃或保留当前元素”。

## 9. trie

适用：

- 前缀树插入。
- 前缀查询。
- 单词统计。
- 自动补全。
- Aho-Corasick 多模式匹配教学版。

state：

```json
{"trie": {"root": {"children": {"a": {}}}}, "word": "app", "pos": 2}
```

target：

- `trie`
- `node:a`
- `edge:a->p`

默认布局：

- 树形字符节点。
- 当前字符路径高亮。
- 终止节点有标记。

交互：

- 点击路径显示前缀。
- 查询时显示匹配或断裂位置。

## 10. union-find

适用：

- 省份数量。
- 连通分量。
- 最小生成树辅助过程。
- 冗余连接。
- 岛屿数量变体。
- 路径压缩。
- 按秩合并。

state：

```json
{"parent": [0, 0, 2], "rank": [1, 0, 0]}
```

如果需要 forest 视图，当前实现更推荐使用 dict parent：

```json
{"union_find": {"parent": {"0": "0", "1": "0", "2": "2"}, "rank": {"0": 1, "1": 0, "2": 0}}}
```

target：

- `parent[1]`
- `node:1`
- `edge:1->0`

默认布局：

- parent 数组。
- forest 视图。
- union 时显示两个根。

交互：

- 点击节点查看根节点。
- 路径压缩时显示 parent 改写。

## 11. recursion_tree

适用：

- 全排列。
- 组合。
- 子集。
- N 皇后。
- 数独。
- 括号生成。
- 分割回文串。
- DFS 搜索树。
- 回溯。

state：

```json
{"path": [1, 2], "used": [true, true, false], "depth": 2}
```

target：

- `frame:dfs(2)`
- `frames`
- `nums[1]`

默认布局：

- 递归树或调用栈。
- 当前 path 高亮。
- 选择和撤销分别显示。

交互：

- 展开 / 折叠递归层。
- 点击 frame 查看局部变量。

## 12. string

适用：

- KMP。
- Rabin-Karp。
- Z Algorithm。
- Manacher。
- 基础字符串匹配。
- 字符串哈希。
- 最长回文子串。

state：

```json
{"text": "ababc", "pattern": "abc", "i": 4, "j": 2, "pi": [0, 0, 1]}
```

target：

- `text[3]`
- `pattern[2]`
- `pi[2]`

默认布局：

- text 和 pattern 分两行。
- 当前比较字符对齐。
- 前缀表作为数组显示。

交互：

- 点击字符查看匹配关系。
- 失配时显示 j 回退来源。

## 13. geometry

适用：

- 凸包。
- 扫描线。
- 点线面基础算法。
- 叉积与方向判断。
- 线段相交。
- 最近点对教学版。

state：

```json
{"points": [[0, 0], [1, 2]], "hull": [[0, 0]], "current": 1}
```

target：

- `point:0`
- `points`

默认布局：

- 坐标平面。
- 当前点高亮。
- hull 边连线。
- orientation / cross 结果显示。

交互：

- 点击点查看坐标。
- 点击边查看加入或弹出原因。

## 14. ML primitives

适用：

- 参数更新演示。
- loss curve。
- 梯度下降。
- 简单决策边界。

对象类型：

- `tensor`
- `batch`
- `parameter`
- `loss_curve`
- `gradient_vector`
- `decision_boundary`
- `training_epoch`
- `prediction`

约束：

- ML primitive 属于扩展方向，不是 V1 算法题主路径。
- 不应影响经典算法页面稳定性。

## 15. linked list

适用：

- 反转链表。
- 合并两个有序链表。
- 合并 K 路链表的链表视图。
- 快慢指针判环。
- 删除倒数第 N 个节点。
- 链表相交。
- LRU 的双向链表。

state：

```json
{"nodes": [{"id": "a", "value": 1}, {"id": "b", "value": 2}], "head": "a", "slow": "a", "fast": "b"}
```

target：

- `node:a`
- `edge:a->b`
- `pointer:slow`
- `pointer:fast`
- `pointer:head`

默认布局：

- 水平链表。
- next 边用箭头表示。
- 指针显示在节点上方。
- 断链和重连用 before / after 对比。

交互：

- 点击节点查看 value 和 next。
- 反转时显示当前边被改向。
- 判环时显示 slow / fast 相遇过程。

## 16. range structure

适用：

- 线段树。
- 树状数组。
- 稀疏表。
- 区间最值。
- 区间和。
- 区间更新教学版。

state：

```json
{"tree": [0, 10, 4, 6], "query": [1, 3], "index": 2}
```

target：

- `tree[1]`
- `bit[4]`
- `node:seg(1,4)`
- `segment_tree[1]`
- `st[2][3]`

注意：不要在当前实现里使用 `range:1-3` 这类新前缀。区间语义应先放在 state 的 `query`、节点 label 或 node meta 里；如果要把 `range:` 变成正式 target，必须同步扩展 target parser、trace validator、scene compiler、renderer 和测试。

默认布局：

- 线段树用区间树展示。
- 树状数组用数组加 lowbit 覆盖区间展示。
- 稀疏表用二维表展示。

交互：

- 点击节点显示它覆盖的区间。
- query 时高亮被拆分出来的区间。
- update 时显示向上或向后传播路径。

## 17. math / bit

适用：

- 最大公约数。
- 快速幂。
- 埃氏筛。
- 质因数分解。
- 组合数。
- 模运算。
- 位掩码 DP。
- 子集枚举。
- lowbit。

state：

```json
{"n": 13, "mask": 5, "bits": [1, 0, 1], "answer": 8}
```

target：

- `bits[0]`
- `mask`
- `factor[2]`
- `table[3][4]`

注意：不要在当前实现里使用 `number:n` 这类新前缀。当前可先用 `n`、`mask`、`bits[0]`、`factor[2]`、`table[3][4]` 表达；如果要把 `number:` 变成正式 target，必须同步扩展 target parser、trace validator、scene compiler、renderer 和测试。

默认布局：

- 数字线或位图。
- 当前位、当前因子、当前指数高亮。
- 表格型数学过程使用 matrix。

交互：

- 点击 bit 查看贡献值。
- 快速幂显示指数折半。
- 筛法显示倍数标记过程。
