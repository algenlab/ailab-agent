# 过程正确性校验

目标：在结果正确之外，提高 trace 每一步过程的可信度。

Invariant 是“算法运行过程中必须始终成立的性质”。它不是页面渲染规则，而是过程校验规则。

例子：

- BFS：`dist[v]` 必须等于从起点到 `v` 的最短边数。
- 0-1 背包：处理前 `i` 个数后，`dp[j]` 必须等于是否能凑出 `j`。
- 二分：`mid` 必须落在当前 `[left, right]` 窗口内。
- 小顶堆：父节点必须不大于子节点。

当前新增一层 `process_validator`，位置：

- `algolab/verification/process_validator.py`

当前提示词位置：

- `algolab/generation/prompts/tracker_system.txt`：首次生成解法、代码和语义 trace 的系统提示词。
- `algolab/generation/prompts/repair_system.txt`：当执行、结果、trace、process 或 scene 校验失败时，用于修复上一轮 JSON 的系统提示词。

它在 pipeline 中位于：

`solve/trace/verifier -> trace validator -> process validator -> scene compiler -> scene validator`

## Invariant 分级

`validate_process(trace)` 默认开启全部层级。也可以在测试或 benchmark 诊断时使用 `validate_process(trace, levels="core")` 或 `levels=["structure", "algorithm"]` 单独打开某几层。

### Core invariant

通用过程一致性，不关心具体算法族，也不关心 renderer：

- `set` 事件的 `after` 必须和当前 `state` 中目标值一致。
- `set` 事件的 `before` 必须和上一帧 `state` 中目标值一致。
- `deps` 应能在当前 `state` 中解析。
- `reason` 提到核心对象时，应能在 `targets/deps/state` 中找到依据。

### Structure invariant

视觉结构本身必须合法。它只检查状态对象的结构性质，不要求给某个算法写专用 renderer：

- 堆：检查小顶堆/大顶堆父子顺序。
- 单调栈：在 state 明确声明 `stack_order` 或 `monotonic` 时检查单调性。
- 并查集：检查 parent forest 是否存在非法环或指向不存在节点。
- 拓扑排序：检查 `topo_order` 是否违反有向边方向。
- BST：在 tree 明确声明 `kind=bst` 时检查左小右大。
- MST：检查 `mst_edges/mst` 不成环且边数不超过约束。
- 几何凸包：检查 `geometry.hull` 是否引用已有点并保持一致转向。
- 回溯搜索树：检查 `recursion_tree/search_tree` 是否为单根无重复访问树。

### Algorithm invariant

算法族转移或数学性质。它是测试/质量门禁，不改变 prompt schema，也不改变 renderer：

- 不同路径二维 DP：只检查 `set dp[i][j]` 的转移是否满足 `dp[i-1][j] + dp[i][j-1]`。
- 打家劫舍一维 DP：检查已写入位置是否满足 `max(dp[i-1], dp[i-2] + nums[i])`。
- 0-1 背包 / 分割等和子集：检查 `set dp[j]` 是否满足前缀数字集合的可达性。
- BFS：检查 `dist` 中每个节点距离是否等于从起点 BFS 得到的最短层数。
- 二分查找：检查 `left/right/mid` 是否越界，`mid` 是否落在当前窗口内。
- Dijkstra：检查当前 `dist` 不得小于真实最短路。
- LCS：检查 `set dp[i][j]` 是否满足最长公共子序列转移。
- 编辑距离：检查 `set dp[i][j]` 是否满足插入/删除/替换转移。
- KMP：检查 `pi/prefix/lps/next` 中被 `set` 的前缀函数值。
- 完全背包：在 state 明确声明 `dp_mode=complete_min` 或 `complete_count` 时检查转移。
- 区间 DP：在 state 明确声明 `dp_mode=merge_stones` 或 `interval_dp=merge_stones` 时检查石子合并类转移。
- LCA：当输入含 `tree/p/q` 且 state 给出 `lca/answer` 时检查最近公共祖先。
- Tarjan：检查 `low/lowlink` 不大于 `dfn/disc`。

## 为什么不会触发连锁膨胀

Invariant 不参与页面布局，也不定义新的 trace op。新增 invariant 时，理想情况下只需要：

- 复用已有 state key，例如 `dp`、`graph`、`dist`、`tree`、`geometry`。
- 在 `process_validator.py` 增加一个小检查函数。
- 在离线测试里增加一个能被抓住的反例。

只有当某类算法需要全新的视觉形态时，才考虑修改 schema/compiler/renderer；普通算法族过程校验不应要求同步改 prompt 和 renderer。

## 已验证

- 反例测试可以抓住错误 DP、错误 BFS 距离、错误二分窗口、错误 0-1 背包可达性、错误 KMP 前缀函数、错误完全背包、错误区间 DP、错误 BST/LCA/Tarjan/MST/凸包/回溯树。
- 分级开关测试可以证明 `core`、`structure`、`algorithm` 能独立启用，不会互相误触发。
- 现有 deterministic quality checks 通过。
- LeetCode 416 重新生成的产物通过 process validator：
  - `output/leetcode_416_partition_equal_subset_sum_process_checked.html`
  - `output/leetcode_416_partition_equal_subset_sum_process_checked.json`
  - `output/leetcode_416_partition_equal_subset_sum_process_checked.png`

## 边界

这不是任意算法的形式化证明。

当前能更强保证的是：对已覆盖 invariant 的算法族，trace 中关键 `set` 状态不能随便编；它必须和对应转移或可达性一致。

下一步应继续补：

- Manacher 半径 / Z 算法 / Trie 前缀状态
- 扫描线活动集合和线段交点
- 网络流残量网络 / 增广路径
- reason 文本和 deps 的更强语义对齐
