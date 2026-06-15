# Benchmark 71 题清单

## 1. 打家劫舍 (`house_robber`)

- 算法族：一维 DP
- 解法：动态规划
- 思路：使用 dp[i] 记录前 i 间房屋的最大收益。
- 输入契约：输入 nums 数组。
- 复杂度：O(n) / O(n)
- 视觉形态：array

题目描述：

打家劫舍。给定一个非负整数数组 nums，每个元素表示一间房屋的金额。不能偷相邻的两间房屋，返回在不触发警报的情况下能够偷到的最高金额。

输入样例：

- sample 0: input = `{'nums': [2, 7, 9, 3, 1]}`, expected = `12`
- sample 1: input = `{'nums': [1, 2, 3, 1]}`, expected = `4`
- sample 2: input = `{'nums': []}`, expected = `0`

## 2. 二分查找 (`binary_search`)

- 算法族：二分
- 解法：闭区间二分
- 思路：维护闭区间，每次比较中点后丢弃一半。
- 输入契约：输入有序 nums 数组和 target。
- 复杂度：O(log n) / O(1)
- 视觉形态：array

题目描述：

二分查找。给定一个升序整数数组 nums 和目标值 target，如果 target 存在，返回它的下标；否则返回 -1。

输入样例：

- sample 0: input = `{'nums': [-1, 0, 3, 5, 9, 12], 'target': 9}`, expected = `4`
- sample 1: input = `{'nums': [-1, 0, 3, 5, 9, 12], 'target': 2}`, expected = `-1`
- sample 2: input = `{'nums': [5], 'target': 5}`, expected = `0`

## 3. 二分答案整数平方根 (`binary_answer_sqrt`)

- 算法族：数组指针 / 窗口 / 前缀
- 解法：答案域二分
- 思路：在 [0,n] 上二分，mid*mid<=n 时记录答案并向右搜索。
- 输入契约：输入非负整数 n。
- 复杂度：O(log n) / O(1)
- 视觉形态：array

题目描述：

给定非负整数 n，返回不超过 sqrt(n) 的最大整数。

输入样例：

- sample 0: input = `{'n': 8}`, expected = `2`
- sample 1: input = `{'n': 16}`, expected = `4`
- sample 2: input = `{'n': 1}`, expected = `1`

## 4. 有序数组两数之和 (`two_pointer_pair_sum`)

- 算法族：数组指针 / 窗口 / 前缀
- 解法：左右双指针
- 思路：根据当前两数之和与 target 的关系移动左指针或右指针。
- 输入契约：输入升序 nums 数组和 target。
- 复杂度：O(n) / O(1)
- 视觉形态：array

题目描述：

给定升序数组 nums 和 target，返回一组下标使两数之和等于 target，不存在返回空数组。

输入样例：

- sample 0: input = `{'nums': [1, 2, 4, 6, 10], 'target': 8}`, expected = `[1, 3]`
- sample 1: input = `{'nums': [1, 3, 5, 8], 'target': 20}`, expected = `[]`
- sample 2: input = `{'nums': [2, 7], 'target': 9}`, expected = `[0, 1]`

## 5. 滑动窗口最短子数组 (`sliding_window_min_len`)

- 算法族：数组指针 / 窗口 / 前缀
- 解法：滑动窗口收缩
- 思路：右端扩张累加，满足条件后移动左端收缩窗口。
- 输入契约：输入正整数 nums 数组和 target。
- 复杂度：O(n) / O(1)
- 视觉形态：array

题目描述：

给定正整数数组 nums 和 target，返回和至少为 target 的最短连续子数组长度，不存在返回 0。

输入样例：

- sample 0: input = `{'nums': [2, 3, 1, 2, 4, 3], 'target': 7}`, expected = `2`
- sample 1: input = `{'nums': [1, 1, 1], 'target': 5}`, expected = `0`
- sample 2: input = `{'nums': [5], 'target': 5}`, expected = `1`

## 6. 前缀和区间查询 (`prefix_sum_range`)

- 算法族：数组指针 / 窗口 / 前缀
- 解法：前缀和
- 思路：prefix[i+1]=prefix[i]+nums[i]，区间和由两个前缀项相减。
- 输入契约：输入 nums 数组和 query 闭区间。
- 复杂度：O(n) / O(n)
- 视觉形态：array

题目描述：

给定数组 nums 和闭区间 query=[l,r]，用前缀和返回区间和。

输入样例：

- sample 0: input = `{'nums': [2, 4, 6], 'query': [1, 2]}`, expected = `10`
- sample 1: input = `{'nums': [-1, 3, 5], 'query': [0, 1]}`, expected = `2`
- sample 2: input = `{'nums': [7], 'query': [0, 0]}`, expected = `7`

## 7. 差分数组区间加 (`difference_array_range_add`)

- 算法族：数组指针 / 窗口 / 前缀
- 解法：差分数组
- 思路：diff[l]+=delta，diff[r+1]-=delta，最后前缀还原。
- 输入契约：输入 nums 数组和 updates 区间更新列表。
- 复杂度：O(n+q) / O(n)
- 视觉形态：array

题目描述：

给定初始数组 nums 和若干 updates=[l,r,delta]，执行所有区间加后返回最终数组。

输入样例：

- sample 0: input = `{'nums': [1, 1, 1], 'updates': [[0, 1, 2]]}`, expected = `[3, 3, 1]`
- sample 1: input = `{'nums': [0, 0, 0, 0], 'updates': [[1, 3, 5], [2, 2, -2]]}`, expected = `[0, 5, 3, 5]`
- sample 2: input = `{'nums': [5], 'updates': [[0, 0, -3]]}`, expected = `[2]`

## 8. 快慢指针判环 (`fast_slow_cycle`)

- 算法族：数组指针 / 窗口 / 前缀
- 解法：Floyd 快慢指针
- 思路：slow 每轮走一步，fast 每轮走两步，相遇则存在环。
- 输入契约：输入 nums 数组，每个值是下一步下标。
- 复杂度：O(n) / O(1)
- 视觉形态：array

题目描述：

给定数组 nums，把下标 i 的下一步定义为 nums[i]，从 0 出发判断是否进入环。

输入样例：

- sample 0: input = `{'nums': [1, 2, 0]}`, expected = `True`
- sample 1: input = `{'nums': [1, 2, 3, 3]}`, expected = `True`
- sample 2: input = `{'nums': []}`, expected = `False`

## 9. 不同路径 (`unique_paths`)

- 算法族：二维 DP
- 解法：二维 DP 表
- 思路：每个格子的路径数来自上方和左侧。
- 输入契约：输入 m 和 n。
- 复杂度：O(mn) / O(mn)
- 视觉形态：matrix

题目描述：

不同路径。一个机器人位于 m x n 网格左上角，每次只能向下或向右移动一步，返回到达右下角的不同路径数量。

输入样例：

- sample 0: input = `{'m': 3, 'n': 7}`, expected = `28`
- sample 1: input = `{'m': 3, 'n': 2}`, expected = `3`
- sample 2: input = `{'m': 1, 'n': 5}`, expected = `1`

## 10. 0-1 背包等和划分 (`knapsack_01_subset_sum`)

- 算法族：DP 核心扩展
- 解法：0-1 背包可达性
- 思路：把目标设为总和一半，逆序容量更新 dp[c]，确保每个数只用一次。
- 输入契约：输入正整数 nums 数组。
- 复杂度：O(n * target) / O(target)
- 视觉形态：array

题目描述：

给定正整数数组 nums，判断能否把数组划分成两个元素和相等的子集。

输入样例：

- sample 0: input = `{'nums': [1, 5, 11, 5]}`, expected = `True`
- sample 1: input = `{'nums': [1, 2, 3, 5]}`, expected = `False`
- sample 2: input = `{'nums': [2, 2, 3, 5]}`, expected = `False`
- sample 3: input = `{'nums': [3, 3, 3, 4, 5]}`, expected = `True`

## 11. 完全背包零钱兑换 (`complete_knapsack_coin_change`)

- 算法族：DP 核心扩展
- 解法：完全背包最少硬币
- 思路：正序容量更新 dp[c]，允许同一种硬币被重复使用。
- 输入契约：输入 coins 数组和 amount。
- 复杂度：O(len(coins) * amount) / O(amount)
- 视觉形态：array

题目描述：

给定硬币面额 coins 和金额 amount，每种硬币可无限使用，返回凑成 amount 的最少硬币数，不可达返回 -1。

输入样例：

- sample 0: input = `{'coins': [1, 2, 5], 'amount': 11}`, expected = `3`
- sample 1: input = `{'coins': [2], 'amount': 3}`, expected = `-1`
- sample 2: input = `{'coins': [1], 'amount': 0}`, expected = `0`
- sample 3: input = `{'coins': [2, 3, 5], 'amount': 7}`, expected = `2`

## 12. 多重背包最大价值 (`bounded_knapsack_max_value`)

- 算法族：DP 核心扩展
- 解法：多重背包基础枚举
- 思路：每种物品基于上一层 dp 枚举可取数量 k，且 k 不能超过 counts[i]。
- 输入契约：输入 weights、values、counts 和 capacity。
- 复杂度：O(n * capacity * max_count) / O(capacity)
- 视觉形态：array

题目描述：

给定 weights、values、counts 和容量 capacity，每种物品最多 counts[i] 件，返回容量内最大价值。

输入样例：

- sample 0: input = `{'weights': [2, 3], 'values': [3, 4], 'counts': [2, 1], 'capacity': 5}`, expected = `7`
- sample 1: input = `{'weights': [2], 'values': [3], 'counts': [2], 'capacity': 5}`, expected = `6`
- sample 2: input = `{'weights': [4, 5], 'values': [6, 7], 'counts': [1, 1], 'capacity': 3}`, expected = `0`
- sample 3: input = `{'weights': [1, 3], 'values': [2, 5], 'counts': [3, 2], 'capacity': 6}`, expected = `11`

## 13. 最长公共子序列长度 (`lcs_length`)

- 算法族：DP 核心扩展
- 解法：LCS 二维 DP
- 思路：相等字符来自左上角加一，不等时取上方和左方最大值。
- 输入契约：输入 text1 和 text2 字符串。
- 复杂度：O(mn) / O(mn)
- 视觉形态：matrix

题目描述：

给定 text1 和 text2，返回它们最长公共子序列的长度。

输入样例：

- sample 0: input = `{'text1': 'abcde', 'text2': 'ace'}`, expected = `3`
- sample 1: input = `{'text1': 'abc', 'text2': 'abc'}`, expected = `3`
- sample 2: input = `{'text1': 'abc', 'text2': 'def'}`, expected = `0`
- sample 3: input = `{'text1': 'bsbininm', 'text2': 'jmjkbkjkv'}`, expected = `1`

## 14. 编辑距离 (`edit_distance`)

- 算法族：DP 核心扩展
- 解法：编辑距离二维 DP
- 思路：相等字符继承左上角，否则从删除、插入、替换三种操作中取最小值加一。
- 输入契约：输入 word1 和 word2 字符串。
- 复杂度：O(mn) / O(mn)
- 视觉形态：matrix

题目描述：

给定 word1 和 word2，返回把 word1 转换成 word2 所需的最少插入、删除、替换次数。

输入样例：

- sample 0: input = `{'word1': 'horse', 'word2': 'ros'}`, expected = `3`
- sample 1: input = `{'word1': 'intention', 'word2': 'execution'}`, expected = `5`
- sample 2: input = `{'word1': '', 'word2': 'abc'}`, expected = `3`
- sample 3: input = `{'word1': 'abc', 'word2': 'abc'}`, expected = `0`

## 15. 区间 DP 合并石子 (`interval_dp_merge_stones`)

- 算法族：DP 核心扩展
- 解法：按区间长度填表
- 思路：dp[i][j] 枚举最后一次切分点 k，再加当前区间总和。
- 输入契约：输入 stones 数组。
- 复杂度：O(n^3) / O(n^2)
- 视觉形态：matrix

题目描述：

给定石子堆数组 stones，每次合并相邻两段的代价为区间总和，返回合并成一堆的最小代价。

输入样例：

- sample 0: input = `{'stones': [3, 2, 4, 1]}`, expected = `20`
- sample 1: input = `{'stones': [1, 2]}`, expected = `3`
- sample 2: input = `{'stones': [5]}`, expected = `0`
- sample 3: input = `{'stones': [4, 1, 1]}`, expected = `8`

## 16. 状态压缩 DP 旅行回路 (`state_compression_tsp`)

- 算法族：DP 核心扩展
- 解法：bitmask TSP
- 思路：dp[mask][u] 表示已访问集合 mask 且停在 u 的最短路径，枚举未访问点扩展 mask。
- 输入契约：输入 dist 方阵。
- 复杂度：O(n^2 2^n) / O(n 2^n)
- 视觉形态：matrix

题目描述：

给定小规模距离矩阵 dist，从 0 出发访问所有点并回到 0，返回最短回路长度。

输入样例：

- sample 0: input = `{'dist': [[0, 1, 15], [1, 0, 2], [15, 2, 0]]}`, expected = `18`
- sample 1: input = `{'dist': [[0, 4, 1], [4, 0, 2], [1, 2, 0]]}`, expected = `7`
- sample 2: input = `{'dist': [[0, 5], [5, 0]]}`, expected = `10`
- sample 3: input = `{'dist': [[0, 2, 9], [2, 0, 6], [9, 6, 0]]}`, expected = `17`

## 17. 数位 DP 统计不含 7 (`digit_dp_no_seven`)

- 算法族：DP 核心扩展
- 解法：数位 DP 入门
- 思路：逐位处理 n 的前缀，维护当前前缀范围内不含禁用数字的计数。
- 输入契约：输入非负整数 n。
- 复杂度：O(d * 10) / O(d)
- 视觉形态：array

题目描述：

给定非负整数 n，统计 1 到 n 中十进制表示不包含数字 7 的正整数个数。

输入样例：

- sample 0: input = `{'n': 20}`, expected = `18`
- sample 1: input = `{'n': 7}`, expected = `6`
- sample 2: input = `{'n': 100}`, expected = `81`
- sample 3: input = `{'n': 0}`, expected = `0`

## 18. 图 BFS 最短层数 (`graph_bfs`)

- 算法族：BFS/DFS 基础图
- 解法：队列 BFS
- 思路：队列按层扩展，首次访问时确定距离。
- 输入契约：输入邻接表 graph 和起点 start。
- 复杂度：O(V+E) / O(V)
- 视觉形态：graph, queue

题目描述：

给定一个无权图的邻接表 graph 和起点 start，返回从 start 到所有可达节点的最短边数距离。

输入样例：

- sample 0: input = `{'graph': {'A': ['B', 'C'], 'B': ['D'], 'C': ['D'], 'D': []}, 'start': 'A'}`, expected = `{'A': 0, 'B': 1, 'C': 1, 'D': 2}`
- sample 1: input = `{'graph': {'1': ['2'], '2': ['3'], '3': [], '4': []}, 'start': '1'}`, expected = `{'1': 0, '2': 1, '3': 2}`

## 19. 图 DFS 遍历 (`graph_dfs_traversal`)

- 算法族：BFS/DFS 基础图
- 解法：递归 DFS
- 思路：进入递归帧时标记访问，按邻接表顺序深度优先探索未访问邻居。
- 输入契约：输入邻接表 graph 和起点 start。
- 复杂度：O(V+E) / O(V)
- 视觉形态：graph, stack

题目描述：

给定无权图邻接表 graph 和起点 start，使用递归 DFS 返回首次访问顺序。

输入样例：

- sample 0: input = `{'graph': {'A': ['B', 'C'], 'B': ['D'], 'C': [], 'D': []}, 'start': 'A'}`, expected = `['A', 'B', 'D', 'C']`
- sample 1: input = `{'graph': {'1': ['2'], '2': ['3'], '3': [], '4': []}, 'start': '1'}`, expected = `['1', '2', '3']`
- sample 2: input = `{'graph': {'S': ['A', 'B'], 'A': ['C'], 'B': ['C'], 'C': []}, 'start': 'S'}`, expected = `['S', 'A', 'C', 'B']`
- sample 3: input = `{'graph': {'X': []}, 'start': 'X'}`, expected = `['X']`
- sample 4: input = `{'graph': {'0': ['1'], '1': ['0', '2'], '2': []}, 'start': '0'}`, expected = `['0', '1', '2']`

## 20. 图连通分量 (`graph_connected_components`)

- 算法族：BFS/DFS 基础图
- 解法：DFS 收集连通分量
- 思路：从每个未访问节点开始 DFS，把同一连通块中的节点收集成一个分量。
- 输入契约：输入无向图邻接表 graph。
- 复杂度：O(V+E) / O(V)
- 视觉形态：graph, map

题目描述：

给定无向图邻接表 graph，返回所有连通分量，每个分量内节点按字典序排列。

输入样例：

- sample 0: input = `{'graph': {'A': ['B'], 'B': ['A'], 'C': []}}`, expected = `[['A', 'B'], ['C']]`
- sample 1: input = `{'graph': {'1': ['2'], '2': ['1', '3'], '3': ['2'], '4': ['5'], '5': ['4']}}`, expected = `[['1', '2', '3'], ['4', '5']]`
- sample 2: input = `{'graph': {'X': []}}`, expected = `[['X']]`
- sample 3: input = `{'graph': {'A': ['B', 'C'], 'B': ['A'], 'C': ['A'], 'D': []}}`, expected = `[['A', 'B', 'C'], ['D']]`
- sample 4: input = `{'graph': {'0': ['1'], '1': ['0'], '2': [], '3': ['4'], '4': ['3']}}`, expected = `[['0', '1'], ['2'], ['3', '4']]`

## 21. 拓扑排序 (`graph_topological_sort`)

- 算法族：BFS/DFS 基础图
- 解法：Kahn 入度队列
- 思路：维护入度表和零入度队列，每弹出一个节点就删除它的出边。
- 输入契约：输入 DAG 邻接表 graph。
- 复杂度：O(V+E) / O(V)
- 视觉形态：graph, queue, map

题目描述：

给定有向无环图 graph，返回一个合法拓扑序。

输入样例：

- sample 0: input = `{'graph': {'A': ['B', 'C'], 'B': ['D'], 'C': ['D'], 'D': []}}`, expected = `['A', 'B', 'C', 'D']`
- sample 1: input = `{'graph': {'1': ['3'], '2': ['3'], '3': []}}`, expected = `['1', '2', '3']`
- sample 2: input = `{'graph': {'S': ['A'], 'A': ['B'], 'B': []}}`, expected = `['S', 'A', 'B']`
- sample 3: input = `{'graph': {'X': []}}`, expected = `['X']`
- sample 4: input = `{'graph': {'0': ['1', '2'], '1': ['3'], '2': ['3'], '3': ['4'], '4': []}}`, expected = `['0', '1', '2', '3', '4']`

## 22. 二分图染色 (`graph_bipartite_coloring`)

- 算法族：BFS/DFS 基础图
- 解法：BFS 二分图染色
- 思路：每个未染色连通块从颜色 0 开始，相邻节点染成相反颜色。
- 输入契约：输入无向二分图邻接表 graph。
- 复杂度：O(V+E) / O(V)
- 视觉形态：graph, queue, map

题目描述：

给定无向二分图 graph，使用 BFS 染色返回每个节点的 0/1 颜色。

输入样例：

- sample 0: input = `{'graph': {'A': ['B', 'D'], 'B': ['A', 'C'], 'C': ['B', 'D'], 'D': ['A', 'C']}}`, expected = `{'A': 0, 'B': 1, 'D': 1, 'C': 0}`
- sample 1: input = `{'graph': {'1': ['2'], '2': ['1', '3'], '3': ['2']}}`, expected = `{'1': 0, '2': 1, '3': 0}`
- sample 2: input = `{'graph': {'X': []}}`, expected = `{'X': 0}`
- sample 3: input = `{'graph': {'L1': ['R1', 'R2'], 'L2': ['R2'], 'R1': ['L1'], 'R2': ['L1', 'L2']}}`, expected = `{'L1': 0, 'R1': 1, 'R2': 1, 'L2': 0}`
- sample 4: input = `{'graph': {'A': ['B'], 'B': ['A'], 'C': ['D'], 'D': ['C']}}`, expected = `{'A': 0, 'B': 1, 'C': 0, 'D': 1}`

## 23. Dijkstra 最短路 (`dijkstra_shortest_path`)

- 算法族：最短路 / MST
- 解法：堆优化 Dijkstra
- 思路：最小堆按当前候选距离弹出节点，用非负权边松弛邻居。
- 输入契约：输入 weighted_graph 邻接表和 start。
- 复杂度：O((V+E) log V) / O(V)
- 视觉形态：graph, heap, map

题目描述：

给定非负权有向图 weighted_graph 和起点 start，返回所有可达点最短距离。

输入样例：

- sample 0: input = `{'weighted_graph': {'A': [['B', 2], ['C', 5]], 'B': [['C', 1]], 'C': []}, 'start': 'A'}`, expected = `{'A': 0, 'B': 2, 'C': 3}`
- sample 1: input = `{'weighted_graph': {'S': [['A', 1], ['B', 4]], 'A': [['B', 2], ['T', 6]], 'B': [['T', 1]], 'T': []}, 'start': 'S'}`, expected = `{'S': 0, 'A': 1, 'B': 3, 'T': 4}`
- sample 2: input = `{'weighted_graph': {'1': [['2', 3]], '2': [], '3': []}, 'start': '1'}`, expected = `{'1': 0, '2': 3}`
- sample 3: input = `{'weighted_graph': {'X': []}, 'start': 'X'}`, expected = `{'X': 0}`

## 24. Bellman-Ford 最短路 (`bellman_ford_shortest_path`)

- 算法族：最短路 / MST
- 解法：Bellman-Ford 边松弛
- 思路：最多 V-1 轮扫描所有边，允许负权边但不包含负环。
- 输入契约：输入 edges=[u,v,w] 和 start。
- 复杂度：O(VE) / O(V)
- 视觉形态：graph, map

题目描述：

给定带权有向边列表 edges 和起点 start，返回所有可达点最短距离。

输入样例：

- sample 0: input = `{'edges': [['A', 'B', 4], ['A', 'C', 5], ['B', 'C', -2]], 'start': 'A'}`, expected = `{'A': 0, 'B': 4, 'C': 2}`
- sample 1: input = `{'edges': [['S', 'A', 1], ['S', 'B', 4], ['A', 'B', -1], ['B', 'T', 2]], 'start': 'S'}`, expected = `{'S': 0, 'A': 1, 'B': 0, 'T': 2}`
- sample 2: input = `{'edges': [['1', '2', 3], ['3', '4', -5]], 'start': '1'}`, expected = `{'1': 0, '2': 3}`
- sample 3: input = `{'edges': [['X', 'Y', 0]], 'start': 'X'}`, expected = `{'X': 0, 'Y': 0}`

## 25. Floyd-Warshall 全源最短路 (`floyd_warshall_all_pairs`)

- 算法族：最短路 / MST
- 解法：Floyd 中转点 DP
- 思路：按 k 阶段枚举中转点，更新任意 i 到 j 的距离。
- 输入契约：输入 dist 方阵，使用 100000000 表示不可达。
- 复杂度：O(n^3) / O(n^2)
- 视觉形态：matrix, graph

题目描述：

给定距离矩阵 dist，使用 Floyd-Warshall 返回所有点对最短距离。

输入样例：

- sample 0: input = `{'dist': [[0, 2, 9], [2, 0, 3], [9, 3, 0]]}`, expected = `[[0, 2, 5], [2, 0, 3], [5, 3, 0]]`
- sample 1: input = `{'dist': [[0, 1, 100000000], [100000000, 0, 2], [4, 100000000, 0]]}`, expected = `[[0, 1, 3], [6, 0, 2], [4, 5, 0]]`
- sample 2: input = `{'dist': [[0, 7], [7, 0]]}`, expected = `[[0, 7], [7, 0]]`
- sample 3: input = `{'dist': [[0, 5, 1], [5, 0, 1], [1, 1, 0]]}`, expected = `[[0, 2, 1], [2, 0, 1], [1, 1, 0]]`

## 26. 0-1 BFS 最短路 (`zero_one_bfs_shortest_path`)

- 算法族：最短路 / MST
- 解法：双端队列 0-1 BFS
- 思路：权重 0 的松弛节点进入队首，权重 1 的松弛节点进入队尾。
- 输入契约：输入 0/1 weighted_graph 和 start。
- 复杂度：O(V+E) / O(V)
- 视觉形态：graph, deque, map

题目描述：

给定边权只为 0 或 1 的有向图 weighted_graph 和起点 start，返回最短距离。

输入样例：

- sample 0: input = `{'weighted_graph': {'A': [['B', 0], ['C', 1]], 'B': [['C', 0]], 'C': []}, 'start': 'A'}`, expected = `{'A': 0, 'B': 0, 'C': 0}`
- sample 1: input = `{'weighted_graph': {'S': [['A', 1], ['B', 0]], 'A': [['T', 0]], 'B': [['A', 0], ['T', 1]], 'T': []}, 'start': 'S'}`, expected = `{'S': 0, 'B': 0, 'A': 0, 'T': 0}`
- sample 2: input = `{'weighted_graph': {'1': [['2', 1]], '2': [], '3': []}, 'start': '1'}`, expected = `{'1': 0, '2': 1}`

## 27. Kruskal 最小生成树 (`kruskal_mst_weight`)

- 算法族：最短路 / MST
- 解法：Kruskal + 并查集
- 思路：按权重排序边，只有连接不同集合的边才加入 MST。
- 输入契约：输入 edges=[u,v,w]。
- 复杂度：O(E log E) / O(V)
- 视觉形态：graph, union_find

题目描述：

给定无向带权边列表 edges，使用 Kruskal 返回最小生成树总权重。

输入样例：

- sample 0: input = `{'edges': [['A', 'B', 1], ['B', 'C', 2], ['A', 'C', 3]]}`, expected = `3`
- sample 1: input = `{'edges': [['A', 'B', 1], ['B', 'C', 1], ['C', 'D', 2], ['A', 'D', 4], ['B', 'D', 3]]}`, expected = `4`
- sample 2: input = `{'edges': [['X', 'Y', 5]]}`, expected = `5`

## 28. KMP 字符串匹配 (`kmp`)

- 算法族：字符串高级算法
- 解法：前缀表匹配
- 思路：使用 KMP 前缀表，trace 只记录初始化、一次前缀表更新、一次失配回退、一次成功匹配等关键步骤，不要逐字符展开全部循环。
- 输入契约：输入 text 和 pattern。
- 复杂度：O(n+m) / O(m)
- 视觉形态：string

题目描述：

实现字符串匹配。给定 text 和 pattern，返回 pattern 在 text 中第一次出现的起始下标；如果不存在返回 -1；如果 pattern 为空返回 0。希望使用 KMP 或等价的线性字符串匹配思路。

输入样例：

- sample 0: input = `{'text': 'ababc', 'pattern': 'abc'}`, expected = `2`
- sample 1: input = `{'text': 'aaaaa', 'pattern': 'bba'}`, expected = `-1`
- sample 2: input = `{'text': 'abc', 'pattern': ''}`, expected = `0`

## 29. Rabin-Karp 字符串匹配 (`rabin_karp`)

- 算法族：字符串高级算法
- 解法：滚动哈希匹配
- 思路：计算 pattern_hash，滚动维护 text 窗口哈希，哈希相等时确认字符。
- 输入契约：输入 text 和 pattern。
- 复杂度：O(n+m) / O(n)
- 视觉形态：string

题目描述：

给定 text 和 pattern，返回 pattern 在 text 中第一次出现的起始下标；使用 Rabin-Karp 滚动哈希比较每个等长窗口，哈希命中后再逐字符确认。

输入样例：

- sample 0: input = `{'text': 'abcdef', 'pattern': 'cde'}`, expected = `2`
- sample 1: input = `{'text': 'aaaaa', 'pattern': 'aa'}`, expected = `0`
- sample 2: input = `{'text': 'abc', 'pattern': 'abcd'}`, expected = `-1`

## 30. Z Algorithm 前缀匹配表 (`z_algorithm`)

- 算法族：字符串高级算法
- 解法：Z-box 线性扫描
- 思路：维护当前 Z-box [l,r]，在盒内复用镜像值，并继续比较扩展。
- 输入契约：输入 text 字符串。
- 复杂度：O(n) / O(n)
- 视觉形态：string

题目描述：

给定字符串 text，返回 Z 数组。z[i] 表示 text[i:] 与 text 的最长公共前缀长度。过程需要展示 Z-box 复用和向右扩展。

输入样例：

- sample 0: input = `{'text': 'aabcaabx'}`, expected = `[0, 1, 0, 0, 3, 1, 0, 0]`
- sample 1: input = `{'text': 'aaaaa'}`, expected = `[0, 4, 3, 2, 1]`
- sample 2: input = `{'text': 'abc'}`, expected = `[0, 0, 0]`

## 31. Manacher 最长回文子串长度 (`manacher`)

- 算法族：字符串高级算法
- 解法：回文半径扩展
- 思路：插入分隔符统一奇偶长度，使用 mirror 半径初始化并向两侧扩展。
- 输入契约：输入 text 字符串。
- 复杂度：O(n) / O(n)
- 视觉形态：string

题目描述：

给定字符串 text，返回最长回文子串长度。使用 Manacher 算法在插入分隔符后的字符串上维护每个中心的回文半径。

输入样例：

- sample 0: input = `{'text': 'ababa'}`, expected = `5`
- sample 1: input = `{'text': 'cbbd'}`, expected = `2`
- sample 2: input = `{'text': 'abc'}`, expected = `1`

## 32. 字符串滑动窗口最长无重复子串 (`string_sliding_window_unique`)

- 算法族：字符串高级算法
- 解法：无重复滑动窗口
- 思路：右端逐字符扩张窗口，遇到重复字符时移动左端并维护 window_counts。
- 输入契约：输入 text 字符串。
- 复杂度：O(n) / O(字符集大小)
- 视觉形态：string, map

题目描述：

给定字符串 text，返回不含重复字符的最长子串长度；过程需要展示窗口左右端和字符计数。

输入样例：

- sample 0: input = `{'text': 'abcabcbb'}`, expected = `3`
- sample 1: input = `{'text': 'bbbbb'}`, expected = `1`
- sample 2: input = `{'text': ''}`, expected = `0`

## 33. Trie 前缀匹配字符串路径 (`trie_prefix_match_string`)

- 算法族：字符串高级算法
- 解法：Trie 前缀路径匹配
- 思路：构建 Trie 并在每个节点维护 prefix_count，再沿 prefix 字符路径读取计数。
- 输入契约：输入 words 和 prefix。
- 复杂度：O(总字符数) / O(总字符数)
- 视觉形态：trie, string

题目描述：

给定字符串数组 words 和前缀 prefix，沿 Trie 的字符路径统计以 prefix 开头的单词数量。

输入样例：

- sample 0: input = `{'words': ['apple', 'app', 'ape', 'bat'], 'prefix': 'ap'}`, expected = `3`
- sample 1: input = `{'words': ['dog', 'door', 'deer'], 'prefix': 'doo'}`, expected = `1`
- sample 2: input = `{'words': ['cat', 'car'], 'prefix': 'z'}`, expected = `0`

## 34. 两数之和 (`two_sum`)

- 算法族：哈希表 / map
- 解法：哈希表一次遍历
- 思路：遍历数组，用哈希表记录已出现数值的下标，检查互补值。
- 输入契约：输入 nums 数组和 target。
- 复杂度：O(n) / O(n)
- 视觉形态：array, map

题目描述：

两数之和。给定整数数组 nums 和整数 target，请返回两个数的下标，使得它们相加等于 target。假设最多只有一个答案，可以返回空数组表示不存在。

输入样例：

- sample 0: input = `{'nums': [2, 7, 11, 15], 'target': 9}`, expected = `[0, 1]`
- sample 1: input = `{'nums': [3, 2, 4], 'target': 6}`, expected = `[1, 2]`
- sample 2: input = `{'nums': [1, 2, 3], 'target': 7}`, expected = `[]`

## 35. 和为 K 的子数组 (`subarray_sum_equals_k`)

- 算法族：哈希表 / map
- 解法：前缀和计数器
- 思路：维护前缀和出现次数，当前位置贡献 counts[prefix-k]。
- 输入契约：输入 nums 数组和 k。
- 复杂度：O(n) / O(n)
- 视觉形态：array, map

题目描述：

和为 K 的子数组。给定整数数组 nums 和整数 k，返回数组中和为 k 的连续子数组个数。

输入样例：

- sample 0: input = `{'nums': [1, 1, 1], 'k': 2}`, expected = `2`
- sample 1: input = `{'nums': [1, 2, 3], 'k': 3}`, expected = `2`
- sample 2: input = `{'nums': [1, -1, 0], 'k': 0}`, expected = `3`
- sample 3: input = `{'nums': [2, 4], 'k': 7}`, expected = `0`
- sample 4: input = `{'nums': [3], 'k': 3}`, expected = `1`

## 36. 插入排序 (`insertion_sort`)

- 算法族：排序
- 解法：插入排序
- 思路：逐步维护有序前缀，把当前元素插入正确位置。
- 输入契约：输入 nums 数组。
- 复杂度：O(n^2) / O(1)
- 视觉形态：array

题目描述：

给定整数数组 nums，使用插入排序思想将数组升序排列，返回排序后的数组。

输入样例：

- sample 0: input = `{'nums': [5, 2, 3, 1]}`, expected = `[1, 2, 3, 5]`
- sample 1: input = `{'nums': [1, 2, 3]}`, expected = `[1, 2, 3]`
- sample 2: input = `{'nums': [3, -1, 0, 3]}`, expected = `[-1, 0, 3, 3]`

## 37. 反转链表 (`reverse_linked_list`)

- 算法族：链表与缓存
- 解法：迭代三指针反转
- 思路：维护 prev/current/next，逐个把 current.next 指向 prev。
- 输入契约：输入 values 数组，按顺序表示链表节点值。
- 复杂度：O(n) / O(1)
- 视觉形态：tree

题目描述：

给定链表节点值 values，按迭代指针重连过程反转链表并返回反转后的值序列。

输入样例：

- sample 0: input = `{'values': [1, 2, 3]}`, expected = `[3, 2, 1]`
- sample 1: input = `{'values': [5]}`, expected = `[5]`
- sample 2: input = `{'values': []}`, expected = `[]`

## 38. 跳跃游戏 (`jump_game`)

- 算法族：贪心
- 解法：最远可达贪心
- 思路：从左到右维护最远可达位置 reach，若当前下标超过 reach 则失败。
- 输入契约：输入 nums 数组。
- 复杂度：O(n) / O(1)
- 视觉形态：array

题目描述：

给定非负整数数组 nums，每个位置表示最大跳跃长度，判断能否到达最后一个下标。

输入样例：

- sample 0: input = `{'nums': [2, 3, 1, 1, 4]}`, expected = `True`
- sample 1: input = `{'nums': [3, 2, 1, 0, 4]}`, expected = `False`
- sample 2: input = `{'nums': [0]}`, expected = `True`

## 39. 合并区间 (`merge_intervals`)

- 算法族：贪心
- 解法：排序后线性合并
- 思路：按起点排序，维护已合并结果的最后一个区间并按需扩展。
- 输入契约：输入 intervals，每个区间为 [start, end]。
- 复杂度：O(n log n) / O(n)
- 视觉形态：matrix

题目描述：

合并区间。给定若干闭区间 intervals，合并所有重叠区间并返回不重叠区间列表。

输入样例：

- sample 0: input = `{'intervals': [[1, 3], [2, 6], [8, 10], [15, 18]]}`, expected = `[[1, 6], [8, 10], [15, 18]]`
- sample 1: input = `{'intervals': [[1, 4], [4, 5]]}`, expected = `[[1, 5]]`
- sample 2: input = `{'intervals': [[1, 4], [0, 2], [3, 5]]}`, expected = `[[0, 5]]`
- sample 3: input = `{'intervals': []}`, expected = `[]`

## 40. 每日温度 (`daily_temperatures`)

- 算法族：栈 / 队列 / 单调栈
- 解法：单调栈
- 思路：维护温度单调递减的下标栈，遇到更高温度时弹栈并写答案。
- 输入契约：输入 temperatures 数组。
- 复杂度：O(n) / O(n)
- 视觉形态：array, stack

题目描述：

每日温度。给定整数数组 temperatures，返回每一天需要等几天才会出现更高温度；如果之后没有更高温度，则为 0。

输入样例：

- sample 0: input = `{'temperatures': [73, 74, 75, 71, 69, 72, 76, 73]}`, expected = `[1, 1, 4, 2, 1, 1, 0, 0]`
- sample 1: input = `{'temperatures': [30, 40, 50, 60]}`, expected = `[1, 1, 1, 0]`
- sample 2: input = `{'temperatures': [30, 60, 90]}`, expected = `[1, 1, 0]`

## 41. 二叉树中序遍历 (`binary_tree_inorder`)

- 算法族：树 / BST / LCA
- 解法：递归中序遍历
- 思路：递归进入左子树，访问当前节点，再进入右子树，并展示递归 frame 返回值。
- 输入契约：输入 tree。
- 复杂度：O(n) / O(h)
- 视觉形态：tree

题目描述：

给定一棵二叉树 tree，返回其中序遍历节点 id 序列。tree 使用 nodes 和 edges 表示，edges 的方向是父节点到子节点，子节点顺序表示左右子树。

输入样例：

- sample 0: input = `{'tree': {'nodes': [{'id': '1'}, {'id': '2'}, {'id': '3'}, {'id': '4'}, {'id': '5'}], 'edges': [['1', '2'], ['1', '3'], ['2', '4'], ['2', '5']]}}`, expected = `['4', '2', '5', '1', '3']`
- sample 1: input = `{'tree': {'nodes': [{'id': 'A'}, {'id': 'B'}, {'id': 'C'}], 'edges': [['A', 'B'], ['A', 'C']]}}`, expected = `['B', 'A', 'C']`
- sample 2: input = `{'tree': {'nodes': [{'id': 'R'}, {'id': 'L'}, {'id': 'LL'}, {'id': 'LR'}], 'edges': [['R', 'L'], ['L', 'LL'], ['L', 'LR']]}}`, expected = `['LL', 'L', 'LR', 'R']`
- sample 3: input = `{'tree': {'nodes': [{'id': 'X'}], 'edges': []}}`, expected = `['X']`
- sample 4: input = `{'tree': {'nodes': [{'id': '1'}, {'id': '2'}, {'id': '3'}, {'id': '4'}, {'id': '5'}, {'id': '6'}], 'edges': [['1', '2'], ['2', '3'], ['3', '4'], ['4', '5'], ['5', '6']]}}`, expected = `['6', '5', '4', '3', '2', '1']`

## 42. 二叉树最近公共祖先 (`lca`)

- 算法族：树 / BST / LCA
- 解法：后序 DFS
- 思路：DFS 返回当前子树是否命中 p 或 q；左右都命中时当前节点为 LCA。
- 输入契约：输入 tree、p、q。
- 复杂度：O(n) / O(h)
- 视觉形态：tree

题目描述：

给定一棵二叉树 tree，以及两个节点 p 和 q，返回它们的最近公共祖先节点 id。tree 使用 nodes 和 edges 表示，edges 的方向是父节点到子节点。

输入样例：

- sample 0: input = `{'tree': {'nodes': [{'id': '3'}, {'id': '5'}, {'id': '1'}, {'id': '6'}, {'id': '2'}, {'id': '0'}, {'id': '8'}, {'id': '7'}, {'id': '4'}], 'edges': [['3', '5'], ['3', '1'], ['5', '6'], ['5', '2'], ['1', '0'], ['1', '8'], ['2', '7'], ['2', '4']]}, 'p': '5', 'q': '1'}`, expected = `3`
- sample 1: input = `{'tree': {'nodes': [{'id': '3'}, {'id': '5'}, {'id': '1'}, {'id': '6'}, {'id': '2'}, {'id': '7'}, {'id': '4'}], 'edges': [['3', '5'], ['3', '1'], ['5', '6'], ['5', '2'], ['2', '7'], ['2', '4']]}, 'p': '7', 'q': '4'}`, expected = `2`
- sample 2: input = `{'tree': {'nodes': [{'id': '3'}, {'id': '5'}, {'id': '1'}, {'id': '6'}, {'id': '2'}, {'id': '7'}, {'id': '4'}], 'edges': [['3', '5'], ['3', '1'], ['5', '6'], ['5', '2'], ['2', '7'], ['2', '4']]}, 'p': '6', 'q': '4'}`, expected = `5`
- sample 3: input = `{'tree': {'nodes': [{'id': 'A'}, {'id': 'B'}, {'id': 'C'}, {'id': 'D'}], 'edges': [['A', 'B'], ['B', 'C'], ['C', 'D']]}, 'p': 'B', 'q': 'D'}`, expected = `B`
- sample 4: input = `{'tree': {'nodes': [{'id': 'A'}, {'id': 'B'}, {'id': 'C'}, {'id': 'D'}, {'id': 'E'}], 'edges': [['A', 'B'], ['A', 'C'], ['C', 'D'], ['C', 'E']]}, 'p': 'D', 'q': 'E'}`, expected = `C`

## 43. 二叉树直径 (`tree_diameter`)

- 算法族：树 / BST / LCA
- 解法：后序高度聚合
- 思路：每个递归 frame 返回子树高度，父节点用两个最大子树高度更新全局直径。
- 输入契约：输入 tree。
- 复杂度：O(n) / O(h)
- 视觉形态：tree

题目描述：

给定一棵二叉树 tree，返回任意两个节点之间最长路径的边数。需要后序聚合每个子树高度，并用两个最大子树高度更新直径。

输入样例：

- sample 0: input = `{'tree': {'nodes': [{'id': '1'}, {'id': '2'}, {'id': '3'}, {'id': '4'}, {'id': '5'}], 'edges': [['1', '2'], ['1', '3'], ['2', '4'], ['2', '5']]}}`, expected = `3`
- sample 1: input = `{'tree': {'nodes': [{'id': '1'}, {'id': '2'}, {'id': '3'}, {'id': '4'}], 'edges': [['1', '2'], ['2', '3'], ['3', '4']]}}`, expected = `3`
- sample 2: input = `{'tree': {'nodes': [{'id': 'A'}], 'edges': []}}`, expected = `0`
- sample 3: input = `{'tree': {'nodes': [{'id': '1'}, {'id': '2'}, {'id': '3'}, {'id': '4'}, {'id': '5'}, {'id': '6'}], 'edges': [['1', '2'], ['1', '3'], ['2', '4'], ['4', '5'], ['3', '6']]}}`, expected = `5`

## 44. 树形 DP 最大独立集 (`tree_max_independent_set`)

- 算法族：树形 DP
- 解法：树形 DP take/skip
- 思路：dp_take[u] 表示选择 u 的最优值，dp_skip[u] 表示不选择 u 的最优值。
- 输入契约：输入带 value 权重的 tree。
- 复杂度：O(n) / O(n)
- 视觉形态：tree

题目描述：

给定一棵带权树 tree，选择若干不相邻节点，使权重和最大，返回最大权重。需要展示 dp_take 和 dp_skip 的子树聚合过程。

输入样例：

- sample 0: input = `{'tree': {'nodes': [{'id': '1', 'value': 3}, {'id': '2', 'value': 2}, {'id': '3', 'value': 1}, {'id': '4', 'value': 10}, {'id': '5', 'value': 1}], 'edges': [['1', '2'], ['1', '3'], ['2', '4'], ['2', '5']]}}`, expected = `14`
- sample 1: input = `{'tree': {'nodes': [{'id': 'A', 'value': 5}, {'id': 'B', 'value': 4}, {'id': 'C', 'value': 6}], 'edges': [['A', 'B'], ['A', 'C']]}}`, expected = `10`
- sample 2: input = `{'tree': {'nodes': [{'id': 'R', 'value': 1}, {'id': 'L', 'value': 10}, {'id': 'M', 'value': 1}, {'id': 'N', 'value': 10}], 'edges': [['R', 'L'], ['R', 'M'], ['M', 'N']]}}`, expected = `20`
- sample 3: input = `{'tree': {'nodes': [{'id': 'X', 'value': 7}], 'edges': []}}`, expected = `7`

## 45. 数组中的第 K 个最大元素 (`kth_largest`)

- 算法族：堆 / TopK / Huffman
- 解法：小顶堆 TopK
- 思路：维护容量为 k 的小顶堆，堆顶就是当前第 k 大。
- 输入契约：输入 nums 数组和 k。
- 复杂度：O(n log k) / O(k)
- 视觉形态：array, heap

题目描述：

给定整数数组 nums 和整数 k，返回数组中第 k 个最大的元素。希望使用容量为 k 的小顶堆。

输入样例：

- sample 0: input = `{'nums': [3, 2, 1, 5, 6, 4], 'k': 2}`, expected = `5`
- sample 1: input = `{'nums': [3, 2, 3, 1, 2, 4, 5, 5, 6], 'k': 4}`, expected = `4`
- sample 2: input = `{'nums': [1], 'k': 1}`, expected = `1`
- sample 3: input = `{'nums': [-1, -3, 2, 0], 'k': 2}`, expected = `0`
- sample 4: input = `{'nums': [7, 7, 7], 'k': 2}`, expected = `7`
- sample 5: input = `{'nums': [9, 1, 8, 2, 7, 3], 'k': 3}`, expected = `7`
- sample 6: input = `{'nums': [10, 4, 6, 8], 'k': 4}`, expected = `4`
- sample 7: input = `{'nums': [5, -2, 11, 11, 0], 'k': 1}`, expected = `11`

## 46. Trie 前缀计数 (`trie_prefix`)

- 算法族：Trie
- 解法：Trie 插入与前缀统计
- 思路：把所有单词插入 Trie，再沿前缀路径统计匹配数量。
- 输入契约：输入 words 和 prefix。
- 复杂度：O(总字符数) / O(总字符数)
- 视觉形态：trie

题目描述：

给定字符串数组 words 和前缀 prefix，使用 Trie 思路统计有多少单词以 prefix 开头。

输入样例：

- sample 0: input = `{'words': ['apple', 'app', 'ape', 'bat'], 'prefix': 'ap'}`, expected = `3`
- sample 1: input = `{'words': ['dog', 'door', 'deer'], 'prefix': 'doo'}`, expected = `1`
- sample 2: input = `{'words': ['cat', 'car', 'dog'], 'prefix': 'z'}`, expected = `0`
- sample 3: input = `{'words': ['a'], 'prefix': 'a'}`, expected = `1`
- sample 4: input = `{'words': ['same', 'same', 'sample'], 'prefix': 'sam'}`, expected = `3`
- sample 5: input = `{'words': ['team', 'tear', 'tea', 'to'], 'prefix': 'tea'}`, expected = `3`
- sample 6: input = `{'words': ['alpha', 'beta'], 'prefix': ''}`, expected = `2`
- sample 7: input = `{'words': ['prefix', 'pre', 'prevent', 'post'], 'prefix': 'pre'}`, expected = `3`

## 47. 省份数量 (`provinces`)

- 算法族：并查集
- 解法：并查集合并
- 思路：相连城市执行 union，最后统计根节点数量。
- 输入契约：输入 isConnected 矩阵。
- 复杂度：O(n^2 α(n)) / O(n)
- 视觉形态：matrix, union_find

题目描述：

省份数量。给定城市连通矩阵 isConnected，如果两个城市直接或间接相连，则属于同一个省份。返回省份数量。

输入样例：

- sample 0: input = `{'isConnected': [[1, 1, 0], [1, 1, 0], [0, 0, 1]]}`, expected = `2`
- sample 1: input = `{'isConnected': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}`, expected = `3`

## 48. 全排列 (`permutations`)

- 算法族：回溯 / 递归
- 解法：回溯搜索树
- 思路：用 path 保存当前选择，递归选择未使用数字，返回时撤销选择。
- 输入契约：输入 nums 数组。
- 复杂度：O(n! n) / O(n)
- 视觉形态：array, recursion_tree

题目描述：

LeetCode 46. 全排列。给定不含重复数字的数组 nums，返回所有可能的排列。

输入样例：

- sample 0: input = `{'nums': [1, 2, 3]}`, expected = `[[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]`
- sample 1: input = `{'nums': [0, 1]}`, expected = `[[0, 1], [1, 0]]`
- sample 2: input = `{'nums': [1]}`, expected = `[[1]]`
- sample 3: input = `{'nums': [6]}`, expected = `[[6]]`
- sample 4: input = `{'nums': [-1, 2]}`, expected = `[[-1, 2], [2, -1]]`
- sample 5: input = `{'nums': [1, 2]}`, expected = `[[1, 2], [2, 1]]`
- sample 6: input = `{'nums': [2, 3, 4]}`, expected = `[[2, 3, 4], [2, 4, 3], [3, 2, 4], [3, 4, 2], [4, 2, 3], [4, 3, 2]]`
- sample 7: input = `{'nums': [4, 5]}`, expected = `[[4, 5], [5, 4]]`
- sample 8: input = `{'nums': [7, 8]}`, expected = `[[7, 8], [8, 7]]`
- sample 9: input = `{'nums': [9]}`, expected = `[[9]]`
- sample 10: input = `{'nums': [0]}`, expected = `[[0]]`
- sample 11: input = `{'nums': [-2]}`, expected = `[[-2]]`

## 49. 凸包 (`convex_hull`)

- 算法族：几何 / 扫描线
- 解法：Andrew 单调链
- 思路：按坐标排序点集，分别维护上下凸壳，使用 orientation/cross 判断转向。
- 输入契约：输入 points 二维点数组。
- 复杂度：O(n log n) / O(n)
- 视觉形态：geometry

题目描述：

给定二维点集 points，返回这些点的凸包顶点，按 Andrew 单调链算法的输出顺序排列。

输入样例：

- sample 0: input = `{'points': [[0, 0], [1, 1], [2, 0], [1, 2]]}`, expected = `[[0, 0], [2, 0], [1, 2]]`
- sample 1: input = `{'points': [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]}`, expected = `[[0, 0], [1, 0], [1, 1], [0, 1]]`

## 50. 线段树区间和 (`segment_tree_range_sum`)

- 算法族：区间结构
- 解法：线段树区间和 + 单点更新
- 思路：线段树节点 meta 记录覆盖区间与区间和，查询区间沿覆盖节点求和，更新路径从叶子回溯维护父节点。
- 输入契约：输入 nums 数组、query 闭区间和 update 单点赋值。
- 复杂度：O(log n) / O(n)
- 视觉形态：tree, array

题目描述：

给定整数数组 nums、闭区间 query=[l,r] 和单点赋值 update=[pos,value]，使用线段树先查询更新前区间和，再执行单点更新并查询更新后区间和。

输入样例：

- sample 0: input = `{'nums': [2, 1, 4, 5], 'query': [1, 3], 'update': [2, 6]}`, expected = `{'before': 10, 'after': 12}`
- sample 1: input = `{'nums': [3, -1, 2, 7, 4], 'query': [0, 2], 'update': [1, 5]}`, expected = `{'before': 4, 'after': 10}`

## 51. 树状数组前缀和 (`fenwick_tree_prefix_sum`)

- 算法族：区间结构
- 解法：树状数组前缀和 + 单点增量
- 思路：bit[i] 保存 lowbit 覆盖块，区间和由两个前缀和相减，更新沿 lowbit 路径向后同步。
- 输入契约：输入 nums 数组、query 闭区间和 update 单点增量。
- 复杂度：O(log n) / O(n)
- 视觉形态：array

题目描述：

给定整数数组 nums、闭区间 query=[l,r] 和单点增量 update=[pos,delta]，使用树状数组先查询更新前区间和，再执行单点增量更新并查询更新后区间和。

输入样例：

- sample 0: input = `{'nums': [1, 2, 3, 4, 5], 'query': [1, 3], 'update': [2, 4]}`, expected = `{'before': 9, 'after': 13}`
- sample 1: input = `{'nums': [5, -2, 6, 1], 'query': [0, 2], 'update': [1, 3]}`, expected = `{'before': 9, 'after': 12}`

## 52. 稀疏表区间最小值 (`sparse_table_range_min`)

- 算法族：区间结构
- 解法：稀疏表 RMQ
- 思路：st[k][i] 记录长度 2^k 区间最小值，查询时选择 k=log(length) 并合并两个重叠区间。
- 输入契约：输入 nums 数组和 query 闭区间。
- 复杂度：O(n log n) build, O(1) query / O(n log n)
- 视觉形态：matrix, array

题目描述：

给定整数数组 nums 和闭区间 query=[l,r]，使用稀疏表预处理固定长度区间最小值，再用两个重叠区间回答区间最小值查询。

输入样例：

- sample 0: input = `{'nums': [5, 2, 7, 3, 6, 1], 'query': [1, 4]}`, expected = `2`
- sample 1: input = `{'nums': [8, 4, 9, 0, 3], 'query': [2, 4]}`, expected = `0`

## 53. 最大公约数 (`gcd_euclid`)

- 算法族：数学与位运算
- 解法：Euclid 辗转相除
- 思路：反复使用 gcd(a,b)=gcd(b,a mod b)，直到余数为 0。
- 输入契约：输入整数 a 和 b。
- 复杂度：O(log min(a,b)) / O(1)
- 视觉形态：array

题目描述：

给定两个非负整数 a 和 b，使用 Euclid 算法返回它们的最大公约数。

输入样例：

- sample 0: input = `{'a': 48, 'b': 18}`, expected = `6`
- sample 1: input = `{'a': 270, 'b': 192}`, expected = `6`
- sample 2: input = `{'a': 17, 'b': 0}`, expected = `17`

## 54. 快速幂取模 (`fast_power_mod`)

- 算法族：数学与位运算
- 解法：二进制快速幂
- 思路：把指数拆成二进制，维护 powers 平方表，遇到 1 位就乘入答案。
- 输入契约：输入 base、exponent、mod。
- 复杂度：O(log exponent) / O(log exponent)
- 视觉形态：array

题目描述：

给定 base、exponent 和 mod，使用快速幂返回 base^exponent mod mod。

输入样例：

- sample 0: input = `{'base': 3, 'exponent': 5, 'mod': 13}`, expected = `9`
- sample 1: input = `{'base': 2, 'exponent': 10, 'mod': 1000}`, expected = `24`
- sample 2: input = `{'base': 7, 'exponent': 0, 'mod': 5}`, expected = `1`

## 55. 埃氏筛 (`sieve_primes`)

- 算法族：数学与位运算
- 解法：倍数标记筛法
- 思路：从每个质数 p 的 p*p 开始标记倍数为合数，剩余 True 下标为质数。
- 输入契约：输入整数 n。
- 复杂度：O(n log log n) / O(n)
- 视觉形态：array

题目描述：

给定整数 n，使用埃氏筛返回不超过 n 的所有质数。

输入样例：

- sample 0: input = `{'n': 20}`, expected = `[2, 3, 5, 7, 11, 13, 17, 19]`
- sample 1: input = `{'n': 10}`, expected = `[2, 3, 5, 7]`
- sample 2: input = `{'n': 1}`, expected = `[]`

## 56. 组合数 (`combinations_pascal`)

- 算法族：数学与位运算
- 解法：Pascal DP 表
- 思路：用 table[i][j] 表示 C(i,j)，由 C(i-1,j-1)+C(i-1,j) 转移。
- 输入契约：输入整数 n 和 k。
- 复杂度：O(nk) / O(nk)
- 视觉形态：matrix

题目描述：

给定 n 和 k，使用帕斯卡恒等式计算组合数 C(n,k)。

输入样例：

- sample 0: input = `{'n': 5, 'k': 2}`, expected = `10`
- sample 1: input = `{'n': 6, 'k': 3}`, expected = `20`
- sample 2: input = `{'n': 4, 'k': 0}`, expected = `1`

## 57. 位掩码枚举子集 (`bitmask_subsets`)

- 算法族：数学与位运算
- 解法：二进制子集枚举
- 思路：mask 的第 i 位表示是否选择 nums[i]，从 0 到 2^n-1 枚举所有子集。
- 输入契约：输入 nums 数组。
- 复杂度：O(n 2^n) / O(n 2^n)
- 视觉形态：array

题目描述：

给定数组 nums，使用二进制 mask 枚举所有子集。

输入样例：

- sample 0: input = `{'nums': [1, 2, 3]}`, expected = `[[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]]`
- sample 1: input = `{'nums': [0, 1]}`, expected = `[[], [0], [1], [0, 1]]`

## 58. lowbit 分解 (`lowbit_decomposition`)

- 算法族：数学与位运算
- 解法：lowbit 拆位
- 思路：反复取最低位的 1 所代表的值，并从 remaining 中减去该值。
- 输入契约：输入整数 n。
- 复杂度：O(popcount(n)) / O(popcount(n))
- 视觉形态：array

题目描述：

给定整数 n，每次取 lowbit(n)=n&-n 并删除最低位的 1，返回分解出的 lowbit 序列。

输入样例：

- sample 0: input = `{'n': 12}`, expected = `[4, 8]`
- sample 1: input = `{'n': 13}`, expected = `[1, 4, 8]`
- sample 2: input = `{'n': 0}`, expected = `[]`

## 59. Tarjan 强连通分量 (`tarjan_scc`)

- 算法族：图高级
- 解法：Tarjan SCC
- 思路：DFS 写入 dfn/low，使用 stack 维护当前搜索栈，low==dfn 时弹出一个强连通分量。
- 输入契约：输入有向图邻接表 graph。
- 复杂度：O(V+E) / O(V)
- 视觉形态：graph, stack, map

题目描述：

给定有向图 graph，使用 Tarjan 算法返回图中的强连通分量。

输入样例：

- sample 0: input = `{'graph': {'A': ['B'], 'B': ['C', 'D'], 'C': ['A'], 'D': ['E'], 'E': ['D']}}`, expected = `[['E', 'D'], ['C', 'B', 'A']]`
- sample 1: input = `{'graph': {'1': ['2'], '2': ['3'], '3': ['1'], '4': []}}`, expected = `[['3', '2', '1'], ['4']]`

## 60. 割点和桥 (`articulation_bridges`)

- 算法族：图高级
- 解法：Tarjan 割点和桥
- 思路：DFS 维护 dfn/low/parent；low[child] > dfn[u] 判定桥，low[child] >= dfn[u] 判定割点。
- 输入契约：输入无向图邻接表 graph。
- 复杂度：O(V+E) / O(V)
- 视觉形态：graph, map

题目描述：

给定无向图 graph，使用 Tarjan dfn/low 返回所有割点和桥。

输入样例：

- sample 0: input = `{'graph': {'A': ['B'], 'B': ['A', 'C', 'D'], 'C': ['B', 'D'], 'D': ['B', 'C', 'E'], 'E': ['D']}}`, expected = `{'articulation': ['B', 'D'], 'bridges': [['D', 'E'], ['A', 'B']]}`
- sample 1: input = `{'graph': {'1': ['2'], '2': ['1', '3'], '3': ['2']}}`, expected = `{'articulation': ['2'], 'bridges': [['2', '3'], ['1', '2']]}`

## 61. 二分图匹配 (`bipartite_matching`)

- 算法族：图高级
- 解法：DFS 增广路径匹配
- 思路：逐个左侧点寻找增广路径，成功后更新 match 映射。
- 输入契约：输入 graph、left、right。
- 复杂度：O(VE) / O(V)
- 视觉形态：graph, map

题目描述：

给定二分图的左侧点、右侧点和邻接表 graph，使用增广路径求最大匹配。

输入样例：

- sample 0: input = `{'graph': {'L1': ['R1', 'R2'], 'L2': ['R1'], 'L3': ['R2']}, 'left': ['L1', 'L2', 'L3'], 'right': ['R1', 'R2']}`, expected = `{'L1': 'R2', 'L2': 'R1'}`
- sample 1: input = `{'graph': {'A': ['X'], 'B': ['X', 'Y']}, 'left': ['A', 'B'], 'right': ['X', 'Y']}`, expected = `{'A': 'X', 'B': 'Y'}`

## 62. Edmonds-Karp 最大流 (`edmonds_karp`)

- 算法族：图高级
- 解法：BFS 增广路径最大流
- 思路：在残量网络中 BFS 寻找最短增广路径，再按瓶颈容量增加 flow。
- 输入契约：输入 graph、capacity、source、sink。
- 复杂度：O(VE^2) / O(E)
- 视觉形态：graph, queue, map

题目描述：

给定有向网络的 graph、capacity、source 和 sink，使用 Edmonds-Karp 教学版返回最大流。

输入样例：

- sample 0: input = `{'graph': {'S': ['A', 'B'], 'A': ['T'], 'B': ['T'], 'T': []}, 'capacity': {'S->A': 2, 'S->B': 1, 'A->T': 2, 'B->T': 1}, 'source': 'S', 'sink': 'T'}`, expected = `3`
- sample 1: input = `{'graph': {'S': ['A'], 'A': ['B', 'T'], 'B': ['T'], 'T': []}, 'capacity': {'S->A': 3, 'A->B': 2, 'A->T': 1, 'B->T': 2}, 'source': 'S', 'sink': 'T'}`, expected = `3`

## 63. 跳跃游戏扩展样例 (`jump_game_expansion`)

- 算法族：贪心
- 解法：最远可达贪心
- 思路：从左到右维护最远可达位置 reach，若当前下标超过 reach 则失败。
- 输入契约：输入 nums 数组。
- 复杂度：O(n) / O(1)
- 视觉形态：array
- Gate layer：expansion

题目描述：

给定非负整数数组 nums，每个位置表示最大跳跃长度，判断能否到达最后一个下标。

输入样例：

- sample 0: input = `{'nums': [1, 0, 1]}`, expected = `False`
- sample 1: input = `{'nums': [2, 0, 0]}`, expected = `True`
- sample 2: input = `{'nums': [1, 1, 0, 1]}`, expected = `False`
- sample 3: input = `{'nums': [4, 0, 0, 0, 0]}`, expected = `True`
- sample 4: input = `{'nums': [0, 1]}`, expected = `False`

## 64. Dijkstra 最短路扩展样例 (`dijkstra_shortest_path_expansion`)

- 算法族：最短路 / MST
- 解法：堆优化 Dijkstra
- 思路：最小堆按当前候选距离弹出节点，用非负权边松弛邻居。
- 输入契约：输入 weighted_graph 邻接表和 start。
- 复杂度：O((V+E) log V) / O(V)
- 视觉形态：graph, heap, map
- Gate layer：expansion

题目描述：

给定非负权有向图 weighted_graph 和起点 start，返回所有可达点最短距离。

输入样例：

- sample 0: input = `{'weighted_graph': {'A': [['B', 1]], 'B': [['C', 2]], 'C': []}, 'start': 'A'}`, expected = `{'A': 0, 'B': 1, 'C': 3}`
- sample 1: input = `{'weighted_graph': {'S': [['A', 2], ['B', 2]], 'A': [['T', 5]], 'B': [['T', 1]], 'T': []}, 'start': 'S'}`, expected = `{'S': 0, 'A': 2, 'B': 2, 'T': 3}`
- sample 2: input = `{'weighted_graph': {'0': [['1', 0], ['2', 4]], '1': [['2', 1]], '2': []}, 'start': '0'}`, expected = `{'0': 0, '1': 0, '2': 1}`
- sample 3: input = `{'weighted_graph': {'A': [['B', 3]], 'B': [], 'C': [['D', 1]], 'D': []}, 'start': 'C'}`, expected = `{'C': 0, 'D': 1}`

## 65. 第 K 大扩展样例 (`kth_largest_expansion`)

- 算法族：堆 / TopK / Huffman
- 解法：小顶堆 TopK
- 思路：维护容量为 k 的小顶堆，堆顶就是当前第 k 大。
- 输入契约：输入 nums 数组和 k。
- 复杂度：O(n log k) / O(k)
- 视觉形态：array, heap
- Gate layer：expansion

题目描述：

给定整数数组 nums 和整数 k，返回数组中第 k 个最大的元素，使用容量为 k 的小顶堆。

输入样例：

- sample 0: input = `{'nums': [9, 8, 7, 6], 'k': 1}`, expected = `9`
- sample 1: input = `{'nums': [4, 1, 4, 2, 8], 'k': 3}`, expected = `4`
- sample 2: input = `{'nums': [-5, -1, -3], 'k': 2}`, expected = `-3`
- sample 3: input = `{'nums': [10, 20], 'k': 2}`, expected = `10`

## 66. Trie 前缀计数扩展样例 (`trie_prefix_expansion`)

- 算法族：Trie
- 解法：Trie 插入与前缀统计
- 思路：把所有单词插入 Trie，再沿前缀路径统计匹配数量。
- 输入契约：输入 words 和 prefix。
- 复杂度：O(总字符数) / O(总字符数)
- 视觉形态：trie
- Gate layer：expansion

题目描述：

给定字符串数组 words 和前缀 prefix，使用 Trie 思路统计有多少单词以 prefix 开头。

输入样例：

- sample 0: input = `{'words': ['', 'a', 'ab'], 'prefix': ''}`, expected = `3`
- sample 1: input = `{'words': ['flow', 'flower', 'flight'], 'prefix': 'fl'}`, expected = `3`
- sample 2: input = `{'words': ['car', 'cart', 'dog'], 'prefix': 'car'}`, expected = `2`
- sample 3: input = `{'words': ['a', 'b'], 'prefix': 'c'}`, expected = `0`

## 67. 全排列扩展样例 (`permutations_expansion`)

- 算法族：回溯 / 递归
- 解法：回溯搜索树
- 思路：用 path 保存当前选择，递归选择未使用数字，返回时撤销选择。
- 输入契约：输入 nums 数组。
- 复杂度：O(n! n) / O(n)
- 视觉形态：array, recursion_tree
- Gate layer：expansion

题目描述：

给定不含重复数字的数组 nums，返回所有可能的排列。

输入样例：

- sample 0: input = `{'nums': [1, 2]}`, expected = `[[1, 2], [2, 1]]`
- sample 1: input = `{'nums': [3]}`, expected = `[[3]]`
- sample 2: input = `{'nums': [1, 2, 3]}`, expected = `[[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]`
- sample 3: input = `{'nums': [-1, 0]}`, expected = `[[-1, 0], [0, -1]]`

## 68. 最大公约数扩展样例 (`gcd_euclid_expansion`)

- 算法族：数学与位运算
- 解法：Euclid 辗转相除
- 思路：反复使用 gcd(a,b)=gcd(b,a mod b)，直到余数为 0。
- 输入契约：输入整数 a 和 b。
- 复杂度：O(log min(a,b)) / O(1)
- 视觉形态：array
- Gate layer：expansion

题目描述：

给定两个非负整数 a 和 b，使用 Euclid 算法返回它们的最大公约数。

输入样例：

- sample 0: input = `{'a': 54, 'b': 24}`, expected = `6`
- sample 1: input = `{'a': 0, 'b': 5}`, expected = `5`
- sample 2: input = `{'a': 81, 'b': 27}`, expected = `27`
- sample 3: input = `{'a': 14, 'b': 15}`, expected = `1`

## 69. 凸包扩展样例 (`convex_hull_expansion`)

- 算法族：几何 / 扫描线
- 解法：Andrew 单调链
- 思路：按坐标排序点集，分别维护上下凸壳，使用 orientation/cross 判断转向。
- 输入契约：输入 points 二维点数组。
- 复杂度：O(n log n) / O(n)
- 视觉形态：geometry
- Gate layer：expansion

题目描述：

给定二维点集 points，返回这些点的凸包顶点，按 Andrew 单调链算法的输出顺序排列。

输入样例：

- sample 0: input = `{'points': [[0, 0], [2, 0], [1, 1]]}`, expected = `[[0, 0], [2, 0], [1, 1]]`
- sample 1: input = `{'points': [[0, 0], [1, 1], [2, 2]]}`, expected = `[[0, 0], [2, 2]]`
- sample 2: input = `{'points': [[0, 0], [2, 0], [2, 2], [0, 2], [1, 1]]}`, expected = `[[0, 0], [2, 0], [2, 2], [0, 2]]`
- sample 3: input = `{'points': [[0, 0], [3, 0], [3, 1], [0, 1], [1, 0]]}`, expected = `[[0, 0], [3, 0], [3, 1], [0, 1]]`

## 70. 反转链表扩展样例 (`reverse_linked_list_expansion`)

- 算法族：链表与缓存
- 解法：迭代三指针反转
- 思路：维护 prev/current/next，逐个把 current.next 指向 prev。
- 输入契约：输入 values 数组，按顺序表示链表节点值。
- 复杂度：O(n) / O(1)
- 视觉形态：tree
- Gate layer：expansion

题目描述：

给定链表节点值 values，按迭代指针重连过程反转链表并返回反转后的值序列。

输入样例：

- sample 0: input = `{'values': [1, 2]}`, expected = `[2, 1]`
- sample 1: input = `{'values': [10, 20, 30, 40]}`, expected = `[40, 30, 20, 10]`
- sample 2: input = `{'values': [-1, 0, 1]}`, expected = `[1, 0, -1]`
- sample 3: input = `{'values': [7]}`, expected = `[7]`

## 71. Edmonds-Karp 扩展样例 (`edmonds_karp_expansion`)

- 算法族：图高级
- 解法：BFS 增广路径最大流
- 思路：在残量网络中 BFS 寻找最短增广路径，再按瓶颈容量增加 flow。
- 输入契约：输入 graph、capacity、source、sink。
- 复杂度：O(VE^2) / O(E)
- 视觉形态：graph, queue, map
- Gate layer：expansion

题目描述：

给定有向网络的 graph、capacity、source 和 sink，使用 Edmonds-Karp 教学版返回最大流。

输入样例：

- sample 0: input = `{'graph': {'S': ['A', 'B'], 'A': ['T'], 'B': ['T'], 'T': []}, 'capacity': {'S->A': 2, 'S->B': 2, 'A->T': 1, 'B->T': 2}, 'source': 'S', 'sink': 'T'}`, expected = `3`
- sample 1: input = `{'graph': {'S': ['A'], 'A': ['B', 'T'], 'B': ['T'], 'T': []}, 'capacity': {'S->A': 5, 'A->B': 3, 'A->T': 2, 'B->T': 4}, 'source': 'S', 'sink': 'T'}`, expected = `5`
- sample 2: input = `{'graph': {'S': ['A'], 'A': ['T'], 'T': []}, 'capacity': {'S->A': 1, 'A->T': 1}, 'source': 'S', 'sink': 'T'}`, expected = `1`
- sample 3: input = `{'graph': {'S': ['A', 'B'], 'A': ['B', 'T'], 'B': ['T'], 'T': []}, 'capacity': {'S->A': 2, 'S->B': 3, 'A->B': 1, 'A->T': 1, 'B->T': 2}, 'source': 'S', 'sink': 'T'}`, expected = `3`
