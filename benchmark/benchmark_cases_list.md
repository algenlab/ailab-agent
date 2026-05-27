# Benchmark 14 题清单

## 1. 打家劫舍 (`house_robber`)

- 算法族：一维 DP
- 解法：动态规划
- 思路：使用 dp[i] 记录前 i 间房屋的最大收益。
- 输入契约：输入 nums 数组。
- 复杂度：O(n) / O(n)
- 视觉形态：array

题目描述：

LeetCode 198. 打家劫舍。给定一个非负整数数组 nums，每个元素表示一间房屋的金额。不能偷相邻的两间房屋，返回在不触发警报的情况下能够偷到的最高金额。

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

LeetCode 704. 二分查找。给定一个升序整数数组 nums 和目标值 target，如果 target 存在，返回它的下标；否则返回 -1。

输入样例：

- sample 0: input = `{'nums': [-1, 0, 3, 5, 9, 12], 'target': 9}`, expected = `4`
- sample 1: input = `{'nums': [-1, 0, 3, 5, 9, 12], 'target': 2}`, expected = `-1`
- sample 2: input = `{'nums': [5], 'target': 5}`, expected = `0`

## 3. 不同路径 (`unique_paths`)

- 算法族：二维 DP
- 解法：二维 DP 表
- 思路：每个格子的路径数来自上方和左侧。
- 输入契约：输入 m 和 n。
- 复杂度：O(mn) / O(mn)
- 视觉形态：matrix

题目描述：

LeetCode 62. 不同路径。一个机器人位于 m x n 网格左上角，每次只能向下或向右移动一步，返回到达右下角的不同路径数量。

输入样例：

- sample 0: input = `{'m': 3, 'n': 7}`, expected = `28`
- sample 1: input = `{'m': 3, 'n': 2}`, expected = `3`
- sample 2: input = `{'m': 1, 'n': 5}`, expected = `1`

## 4. 图 BFS 最短层数 (`graph_bfs`)

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

## 5. KMP 字符串匹配 (`kmp`)

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

## 6. 两数之和 (`two_sum`)

- 算法族：哈希表 / map
- 解法：哈希表一次遍历
- 思路：遍历数组，用哈希表记录已出现数值的下标，检查互补值。
- 输入契约：输入 nums 数组和 target。
- 复杂度：O(n) / O(n)
- 视觉形态：array, map

题目描述：

LeetCode 1. 两数之和。给定整数数组 nums 和整数 target，请返回两个数的下标，使得它们相加等于 target。假设最多只有一个答案，可以返回空数组表示不存在。

输入样例：

- sample 0: input = `{'nums': [2, 7, 11, 15], 'target': 9}`, expected = `[0, 1]`
- sample 1: input = `{'nums': [3, 2, 4], 'target': 6}`, expected = `[1, 2]`
- sample 2: input = `{'nums': [1, 2, 3], 'target': 7}`, expected = `[]`

## 7. 每日温度 (`daily_temperatures`)

- 算法族：栈 / 队列 / 单调栈
- 解法：单调栈
- 思路：维护温度单调递减的下标栈，遇到更高温度时弹栈并写答案。
- 输入契约：输入 temperatures 数组。
- 复杂度：O(n) / O(n)
- 视觉形态：array, stack

题目描述：

LeetCode 739. 每日温度。给定整数数组 temperatures，返回每一天需要等几天才会出现更高温度；如果之后没有更高温度，则为 0。

输入样例：

- sample 0: input = `{'temperatures': [73, 74, 75, 71, 69, 72, 76, 73]}`, expected = `[1, 1, 4, 2, 1, 1, 0, 0]`
- sample 1: input = `{'temperatures': [30, 40, 50, 60]}`, expected = `[1, 1, 1, 0]`
- sample 2: input = `{'temperatures': [30, 60, 90]}`, expected = `[1, 1, 0]`

## 8. 插入排序 (`insertion_sort`)

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

## 9. 二叉树最近公共祖先 (`lca`)

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

## 10. 数组中的第 K 个最大元素 (`kth_largest`)

- 算法族：堆 / TopK / Huffman
- 解法：小顶堆 TopK
- 思路：维护容量为 k 的小顶堆，堆顶就是当前第 k 大。
- 输入契约：输入 nums 数组和 k。
- 复杂度：O(n log k) / O(k)
- 视觉形态：array, heap

题目描述：

LeetCode 215. 给定整数数组 nums 和整数 k，返回数组中第 k 个最大的元素。希望使用容量为 k 的小顶堆。

输入样例：

- sample 0: input = `{'nums': [3, 2, 1, 5, 6, 4], 'k': 2}`, expected = `5`
- sample 1: input = `{'nums': [3, 2, 3, 1, 2, 4, 5, 5, 6], 'k': 4}`, expected = `4`

## 11. Trie 前缀计数 (`trie_prefix`)

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

## 12. 省份数量 (`provinces`)

- 算法族：并查集
- 解法：并查集合并
- 思路：相连城市执行 union，最后统计根节点数量。
- 输入契约：输入 isConnected 矩阵。
- 复杂度：O(n^2 α(n)) / O(n)
- 视觉形态：matrix, union_find

题目描述：

LeetCode 547. 省份数量。给定城市连通矩阵 isConnected，如果两个城市直接或间接相连，则属于同一个省份。返回省份数量。

输入样例：

- sample 0: input = `{'isConnected': [[1, 1, 0], [1, 1, 0], [0, 0, 1]]}`, expected = `2`
- sample 1: input = `{'isConnected': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}`, expected = `3`

## 13. 全排列 (`permutations`)

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

## 14. 凸包 (`convex_hull`)

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
