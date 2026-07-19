"""Freeze 40 independently sourced held-out tasks with executable oracles."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import inspect
import json
import math
import sys
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.cases import benchmark_cases
from scripts.run_llm_benchmark import load_family_capabilities, strong_family_ids_from_capabilities, validate_unseen_family_cases


DEFAULT_OUTPUT = ROOT / "benchmark/heldout_cases_v1.json"
FAMILY_META = {
    "dp_1d": ("一维 DP", "dp"),
    "dp_2d": ("二维 DP", "dp"),
    "dp_core": ("DP 核心扩展", "dp"),
    "binary_search": ("二分", "binary_search"),
    "array_pointer": ("数组指针 / 窗口 / 前缀", "array_pointer"),
    "basic_graph": ("BFS/DFS 基础图", "bfs"),
    "shortest_path_mst": ("最短路 / MST", "shortest_path_mst"),
    "string_advanced": ("字符串高级算法", "string"),
    "monotonic_stack": ("栈 / 队列 / 单调栈", "monotonic_stack"),
    "tree_bst_lca": ("树 / BST / LCA", "tree"),
    "tree_dp": ("树形 DP", "dp"),
    "union_find": ("并查集", "union_find"),
    "range_structure": ("区间结构", "range_structure"),
    "math_bit": ("数学与位运算", "math_bit"),
    "advanced_graph": ("图高级", "advanced_graph"),
}


def _definitions() -> list[dict[str, Any]]:
    def item(
        case_id: str,
        title: str,
        family_id: str,
        subfamily: str,
        problem: str,
        strategy: str,
        input_data: dict[str, Any],
        source_name: str,
        source_url: str,
    ) -> dict[str, Any]:
        family, profile = FAMILY_META[family_id]
        return {
            "id": case_id,
            "title": title,
            "problem": problem,
            "family": family,
            "family_id": family_id,
            "subfamily_id": subfamily,
            "gate_layer": "llm_eval",
            "support_level": "strong",
            "process_profile": profile,
            "strategy": strategy,
            "input_data": input_data,
            "source": {"name": source_name, "url": source_url},
        }

    return [
        item("heldout_frog_energy", "青蛙跳石最小体力", "dp_1d", "linear_dp", "青蛙从第 0 块石头出发，每次跳 1 或 2 块，代价为两块石头高度差的绝对值。返回到最后一块石头的最小总代价。", "dp[i] 取从 i-1 或 i-2 跳来的较小代价。", {"heights": [10, 30, 40, 20]}, "AtCoder Educational DP Contest A", "https://atcoder.jp/contests/dp/tasks/dp_a"),
        item("heldout_delete_and_earn", "删除并获得点数", "dp_1d", "value_dp", "选择一个数 x 可获得 x 点，同时必须删除所有 x-1 与 x+1。可重复处理剩余元素，返回最大得分。", "按数值聚合点数后做相邻不可同时选择的一维 DP。", {"nums": [3, 4, 2, 3, 3, 4]}, "LeetCode 740", "https://leetcode.com/problems/delete-and-earn/"),
        item("heldout_wiggle_subsequence", "最长摆动子序列", "dp_1d", "sequence_dp", "若相邻差值严格正负交替，则序列为摆动序列。返回给定数组最长摆动子序列长度。", "维护以上升差结尾和以下降差结尾的最优长度。", {"nums": [1, 7, 4, 9, 2, 5]}, "LeetCode 376", "https://leetcode.com/problems/wiggle-subsequence/"),
        item("heldout_maximal_square", "最大全 1 正方形面积", "dp_2d", "matrix_dp", "给定只含 0/1 的矩阵，返回其中只包含 1 的最大正方形面积。", "dp[i][j] 由左、上、左上三格最小值加一。", {"matrix": [["1", "0", "1", "0", "0"], ["1", "0", "1", "1", "1"], ["1", "1", "1", "1", "1"], ["1", "0", "0", "1", "0"]]}, "LeetCode 221", "https://leetcode.com/problems/maximal-square/"),
        item("heldout_dungeon_health", "地下城游戏最低初始生命", "dp_2d", "reverse_grid_dp", "骑士从左上角走到右下角，只能向右或向下。格子会增减生命，生命值始终至少为 1。返回所需最低初始生命。", "从终点反向 DP，记录进入每格前至少需要的生命。", {"dungeon": [[-2, -3, 3], [-5, -10, 1], [10, 30, -5]]}, "LeetCode 174", "https://leetcode.com/problems/dungeon-game/"),
        item("heldout_cherry_two_robots", "双机器人摘樱桃", "dp_2d", "multi_agent_grid_dp", "两个机器人从网格顶行两端出发，每行各向左下、下或右下移动；同一格樱桃只计一次。返回最大樱桃数。", "按行对两个列位置做三维状态转移。", {"grid": [[3, 1, 1], [2, 5, 1], [1, 5, 5], [2, 1, 1]]}, "LeetCode 1463", "https://leetcode.com/problems/cherry-pickup-ii/"),
        item("heldout_target_sum_ways", "目标和表达式数量", "dp_core", "subset_count", "给每个整数添加正号或负号，返回表达式结果等于 target 的方案数。", "用和差转换为子集计数，或直接维护可达和的计数。", {"nums": [1, 1, 1, 1, 1], "target": 3}, "LeetCode 494", "https://leetcode.com/problems/target-sum/"),
        item("heldout_coin_change_combinations", "零钱兑换组合数", "dp_core", "complete_knapsack", "给定不同面额 coins 和总额 amount，返回凑成总额的无序组合数量。", "完全背包按硬币外层、金额内层累计组合数。", {"amount": 5, "coins": [1, 2, 5]}, "LeetCode 518", "https://leetcode.com/problems/coin-change-ii/"),
        item("heldout_word_break", "单词拆分可行性", "dp_core", "string_dp", "判断字符串 s 是否可由词典中的一个或多个单词拼接而成，词典单词可以重复使用。", "dp[i] 表示前 i 个字符能否拆分，枚举前驱切分点。", {"s": "leetcode", "word_dict": ["leet", "code", "lee", "tcode"]}, "LeetCode 139", "https://leetcode.com/problems/word-break/"),
        item("heldout_kth_missing_positive", "第 k 个缺失正整数", "binary_search", "answer_binary_search", "给定严格递增正整数数组 arr 和 k，返回从 1 开始计数的第 k 个缺失正整数。", "arr[i]-i-1 是下标 i 前缺失数量，对其二分。", {"arr": [2, 3, 4, 7, 11], "k": 5}, "LeetCode 1539", "https://leetcode.com/problems/kth-missing-positive-number/"),
        item("heldout_ship_capacity", "D 天内送达包裹的最低运力", "binary_search", "binary_answer", "包裹必须按 weights 顺序装船，每天总重量不能超过运力。返回 days 天内送完的最低运力。", "对运力做答案二分，用贪心模拟所需天数。", {"weights": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "days": 5}, "LeetCode 1011", "https://leetcode.com/problems/capacity-to-ship-packages-within-d-days/"),
        item("heldout_median_two_sorted", "两个有序数组的中位数", "binary_search", "partition_binary_search", "给定两个有序数组，返回合并后的中位数。", "在较短数组上二分分割位置，使左右两侧元素数量和大小关系满足中位数条件。", {"nums1": [1, 3], "nums2": [2]}, "LeetCode 4", "https://leetcode.com/problems/median-of-two-sorted-arrays/"),
        item("heldout_trapping_rain_water", "接雨水", "array_pointer", "two_pointer", "给定柱高数组，返回下雨后可接的总水量。", "双指针维护左右最高柱，较低侧可立即结算。", {"height": [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]}, "LeetCode 42", "https://leetcode.com/problems/trapping-rain-water/"),
        item("heldout_longest_ones_k_flips", "最多翻转 K 个零后的最长连续 1", "array_pointer", "sliding_window", "二进制数组中最多把 k 个 0 翻成 1，返回最长连续 1 区间长度。", "滑动窗口维持窗口内零的数量不超过 k。", {"nums": [1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0], "k": 2}, "LeetCode 1004", "https://leetcode.com/problems/max-consecutive-ones-iii/"),
        item("heldout_group_ones_circular", "环形数组聚集所有 1 的最少交换", "array_pointer", "circular_window", "在环形二进制数组中，可交换任意两个位置。返回把所有 1 聚在一起所需的最少交换次数。", "窗口长度固定为 1 的总数，在双倍数组上最大化窗口内的 1。", {"nums": [0, 1, 0, 1, 1, 0, 0]}, "LeetCode 2134", "https://leetcode.com/problems/minimum-swaps-to-group-all-1s-together-ii/"),
        item("heldout_eventual_safe_nodes", "最终安全节点", "basic_graph", "dfs_cycle", "有向图中，从节点出发的每条路径最终都终止，则该节点安全。返回所有安全节点升序列表。", "DFS 三色标记检测是否能到达环，或在反图上拓扑删除。", {"graph": [[1, 2], [2, 3], [5], [0], [5], [], []]}, "LeetCode 802", "https://leetcode.com/problems/find-eventual-safe-states/"),
        item("heldout_parallel_courses", "完成所有课程的最少学期", "basic_graph", "topological_layers", "relations 中 [u,v] 表示课程 u 是 v 的先修课；每学期可同时学习所有先修已完成课程。返回完成 n 门课的最少学期，若有环返回 -1。", "拓扑 BFS 按层统计学期并检测环。", {"n": 3, "relations": [[1, 3], [2, 3]]}, "LeetCode 1136", "https://leetcode.com/problems/parallel-courses/"),
        item("heldout_open_lock", "打开转盘锁", "basic_graph", "state_bfs", "四位转盘锁每次可把一位加一或减一，遇到 deadends 状态会锁死。从 0000 到 target 最少需要多少次旋转，不可达返回 -1。", "把每个锁状态视为图节点，用 BFS 求最短层数。", {"deadends": ["0201", "0101", "0102", "1212", "2002"], "target": "0202"}, "LeetCode 752", "https://leetcode.com/problems/open-the-lock/"),
        item("heldout_cheapest_flight_k_stops", "K 次中转内最便宜航班", "shortest_path_mst", "bounded_bellman_ford", "给定航班 [u,v,price]，返回 src 到 dst 且最多 k 次中转的最低价格，不可达返回 -1。", "做 k+1 轮 Bellman-Ford 松弛，每轮只读取上一轮距离。", {"n": 4, "flights": [[0, 1, 100], [1, 2, 100], [2, 3, 100], [0, 3, 700], [1, 3, 600]], "src": 0, "dst": 3, "k": 1}, "LeetCode 787", "https://leetcode.com/problems/cheapest-flights-within-k-stops/"),
        item("heldout_minimum_effort_path", "最小体力消耗路径", "shortest_path_mst", "minimax_dijkstra", "网格路径的体力消耗定义为相邻格高度差绝对值的最大值。返回左上到右下路径的最小体力消耗。", "Dijkstra 的路径代价取当前代价与新边差值的最大值。", {"heights": [[1, 2, 2], [3, 8, 2], [5, 3, 5]]}, "LeetCode 1631", "https://leetcode.com/problems/path-with-minimum-effort/"),
        item("heldout_connect_points_mst", "连接所有点的最小费用", "shortest_path_mst", "prim_mst", "平面点之间连边代价为曼哈顿距离，返回连接所有点的最小总费用。", "在完全图上运行 Prim，动态计算到树的最短曼哈顿距离。", {"points": [[0, 0], [2, 2], [3, 10], [5, 2], [7, 0]]}, "LeetCode 1584", "https://leetcode.com/problems/min-cost-to-connect-all-points/"),
        item("heldout_longest_happy_prefix", "最长快乐前缀", "string_advanced", "kmp_prefix", "返回字符串中既是前缀又是后缀的最长非完整字符串。", "计算 KMP 前缀函数，答案长度为最后一个 pi 值。", {"s": "level"}, "LeetCode 1392", "https://leetcode.com/problems/longest-happy-prefix/"),
        item("heldout_minimum_window", "最小覆盖子串", "string_advanced", "string_sliding_window", "返回 s 中覆盖 t 全部字符及其次数的最短子串；无解返回空串。", "滑动窗口维护需求计数，满足后收缩左边界。", {"s": "ADOBECODEBANC", "t": "ABC"}, "LeetCode 76", "https://leetcode.com/problems/minimum-window-substring/"),
        item("heldout_repeated_substring", "重复子串模式", "string_advanced", "periodicity", "判断字符串能否由某个非空子串重复多次构成。", "利用 KMP 最长相等前后缀判断最小周期是否整除长度。", {"s": "abcabcabcabc"}, "LeetCode 459", "https://leetcode.com/problems/repeated-substring-pattern/"),
        item("heldout_largest_histogram_rectangle", "柱状图中最大矩形", "monotonic_stack", "monotonic_stack", "给定柱状图高度，返回可形成的最大矩形面积。", "单调递增栈在遇到更低柱时结算被弹出柱的左右边界。", {"heights": [2, 1, 5, 6, 2, 3]}, "LeetCode 84", "https://leetcode.com/problems/largest-rectangle-in-histogram/"),
        item("heldout_remove_k_digits", "移掉 K 位数字", "monotonic_stack", "greedy_stack", "从非负整数字符串中删除 k 位，使剩余数字最小；去除前导零，空结果返回 0。", "维护单调递增字符栈，当前位更小时弹出前面较大数字。", {"num": "1432219", "k": 3}, "LeetCode 402", "https://leetcode.com/problems/remove-k-digits/"),
        item("heldout_sliding_window_max", "滑动窗口最大值", "monotonic_stack", "monotonic_deque", "返回长度为 k 的每个滑动窗口中的最大值。", "单调递减双端队列保存仍在窗口内的候选下标。", {"nums": [1, 3, -1, -3, 5, 3, 6, 7], "k": 3}, "LeetCode 239", "https://leetcode.com/problems/sliding-window-maximum/"),
        item("heldout_bst_kth_smallest", "BST 第 k 小元素", "tree_bst_lca", "bst_inorder", "给定二叉搜索树的层序数组和 k，返回第 k 小节点值。", "中序遍历 BST 得到升序序列并计数。", {"nodes": [5, 3, 6, 2, 4, None, None, 1], "k": 3}, "LeetCode 230", "https://leetcode.com/problems/kth-smallest-element-in-a-bst/"),
        item("heldout_tree_right_view", "二叉树右视图", "tree_bst_lca", "level_order", "给定二叉树层序数组，返回从右侧看到的每层节点值。", "层序遍历并记录每层最后一个节点。", {"nodes": [1, 2, 3, None, 5, None, 4]}, "LeetCode 199", "https://leetcode.com/problems/binary-tree-right-side-view/"),
        item("heldout_bst_lca", "BST 最近公共祖先", "tree_bst_lca", "bst_lca", "给定二叉搜索树层序数组与节点值 p、q，返回二者最近公共祖先的值。", "利用 BST 大小关系同时向左或向右，首次分叉点即答案。", {"nodes": [6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], "p": 2, "q": 8}, "LeetCode 235", "https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-search-tree/"),
        item("heldout_tree_house_robber", "打家劫舍 III", "tree_dp", "take_skip_dp", "二叉树相邻父子节点不能同时选择，返回可选择节点值的最大和。", "树形 DP 对每个节点返回选择与不选择两种收益。", {"nodes": [3, 2, 3, None, 3, None, 1]}, "LeetCode 337", "https://leetcode.com/problems/house-robber-iii/"),
        item("heldout_binary_tree_cameras", "监控二叉树", "tree_dp", "tree_state_dp", "摄像头可监控自身、父节点和直接子节点。返回监控整棵树所需的最少摄像头数。", "后序遍历按未覆盖、放摄像头、已覆盖三种状态贪心。", {"nodes": [0, 0, None, 0, 0]}, "LeetCode 968", "https://leetcode.com/problems/binary-tree-cameras/"),
        item("heldout_equations_satisfiable", "等式方程可满足性", "union_find", "equation_union", "变量为小写字母，方程形式为 a==b 或 a!=b。判断能否同时满足全部方程。", "先合并所有等式，再检查不等式两端是否落在同一集合。", {"equations": ["a==b", "b!=c", "c==a"]}, "LeetCode 990", "https://leetcode.com/problems/satisfiability-of-equality-equations/"),
        item("heldout_earliest_friendship", "所有人成为朋友的最早时刻", "union_find", "offline_connectivity", "日志 [timestamp,a,b] 表示两人在该时刻成为朋友，友谊可传递。返回所有 n 个人连通的最早时间，不可能返回 -1。", "按时间排序后逐条 union，集合数变为 1 时返回时间。", {"n": 6, "logs": [[20190101, 0, 1], [20190104, 3, 4], [20190107, 2, 3], [20190211, 1, 5], [20190224, 2, 4], [20190301, 0, 3], [20190312, 1, 2], [20190322, 4, 5]]}, "LeetCode 1101", "https://leetcode.com/problems/the-earliest-moment-when-everyone-become-friends/"),
        item("heldout_count_smaller_after_self", "右侧小于当前元素的数量", "range_structure", "fenwick_tree", "对数组每个位置，返回其右侧严格小于该元素的数量。", "离散化后从右向左，用树状数组查询较小值频次并更新当前值。", {"nums": [5, 2, 6, 1]}, "LeetCode 315", "https://leetcode.com/problems/count-of-smaller-numbers-after-self/"),
        item("heldout_range_add_point_query", "区间增量后的点查询", "range_structure", "difference_array", "长度 n 的零数组依次执行闭区间增量 [left,right,delta]，返回指定 query 下标的最终值。", "差分数组做区间加法，再前缀恢复并读取查询点。", {"n": 5, "updates": [[1, 3, 2], [2, 4, 3], [0, 2, -2]], "queries": [0, 2, 4]}, "LeetCode 370", "https://leetcode.com/problems/range-addition/"),
        item("heldout_single_number_three", "只出现一次的数字 II", "math_bit", "bit_count", "除一个元素只出现一次外，其余元素都恰好出现三次。返回只出现一次的元素。", "逐位统计 1 的数量并对 3 取模，或维护有限状态位掩码。", {"nums": [2, 2, 3, 2]}, "LeetCode 137", "https://leetcode.com/problems/single-number-ii/"),
        item("heldout_nth_ugly_number", "第 n 个丑数", "math_bit", "number_sequence", "正整数的质因数只有 2、3、5 时称为丑数，1 也是丑数。返回第 n 个丑数。", "三指针动态生成分别乘 2、3、5 的下一个候选。", {"n": 10}, "LeetCode 264", "https://leetcode.com/problems/ugly-number-ii/"),
        item("heldout_source_scc_count", "缩点图零入度分量数", "advanced_graph", "tarjan_scc", "给定 n 个节点的有向边，先求强连通分量并缩点，返回缩点图中入度为 0 的分量数量。", "Tarjan 或 Kosaraju 求 SCC，再统计跨分量边带来的入度。", {"n": 5, "edges": [[0, 1], [1, 0], [1, 2], [2, 3], [3, 2], [4, 3]]}, "CP-Algorithms SCC", "https://cp-algorithms.com/graph/strongly-connected-components.html"),
        item("heldout_bipartite_matching_size", "二分图最大匹配数", "advanced_graph", "bipartite_matching", "给定左侧节点列表、右侧节点列表和允许匹配边，返回一对一最大匹配的边数。", "逐个左节点寻找增广路，必要时递归改配已匹配右节点。", {"left": ["A", "B", "C"], "right": ["X", "Y", "Z"], "edges": [["A", "X"], ["A", "Y"], ["B", "Y"], ["C", "Y"], ["C", "Z"]]}, "CP-Algorithms Kuhn Matching", "https://cp-algorithms.com/graph/kuhn_maximum_bipartite_matching.html"),
    ]


def _tree(nodes: list[Any]) -> list[dict[str, Any] | None]:
    return [None if value is None else {"value": value, "left": 2 * i + 1, "right": 2 * i + 2} for i, value in enumerate(nodes)]


def oracle(case_id: str, data: dict[str, Any]) -> Any:
    if case_id == "heldout_frog_energy":
        h = data["heights"]
        dp = [0] + [10**18] * (len(h) - 1)
        for i in range(1, len(h)):
            dp[i] = min(dp[i], dp[i - 1] + abs(h[i] - h[i - 1]))
            if i > 1:
                dp[i] = min(dp[i], dp[i - 2] + abs(h[i] - h[i - 2]))
        return dp[-1]
    if case_id == "heldout_delete_and_earn":
        points = Counter(data["nums"])
        take = skip = 0
        previous = None
        for value in sorted(points):
            gain = value * points[value]
            if previous is not None and value == previous + 1:
                take, skip = skip + gain, max(skip, take)
            else:
                best = max(take, skip)
                take, skip = best + gain, best
            previous = value
        return max(take, skip)
    if case_id == "heldout_wiggle_subsequence":
        nums = data["nums"]
        up = down = 1
        for a, b in zip(nums, nums[1:]):
            if b > a:
                up = down + 1
            elif b < a:
                down = up + 1
        return max(up, down)
    if case_id == "heldout_maximal_square":
        matrix = data["matrix"]
        dp = [[0] * (len(matrix[0]) + 1) for _ in range(len(matrix) + 1)]
        best = 0
        for i, row in enumerate(matrix, 1):
            for j, value in enumerate(row, 1):
                if str(value) == "1":
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
                    best = max(best, dp[i][j])
        return best * best
    if case_id == "heldout_dungeon_health":
        grid = data["dungeon"]
        m, n = len(grid), len(grid[0])
        dp = [[10**18] * (n + 1) for _ in range(m + 1)]
        dp[m][n - 1] = dp[m - 1][n] = 1
        for i in range(m - 1, -1, -1):
            for j in range(n - 1, -1, -1):
                dp[i][j] = max(1, min(dp[i + 1][j], dp[i][j + 1]) - grid[i][j])
        return dp[0][0]
    if case_id == "heldout_cherry_two_robots":
        grid = data["grid"]
        n = len(grid[0])
        states = {(0, n - 1): grid[0][0] + (grid[0][n - 1] if n > 1 else 0)}
        for row in grid[1:]:
            nxt: dict[tuple[int, int], int] = {}
            for (a, b), score in states.items():
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < n and 0 <= y < n:
                            nxt[(x, y)] = max(nxt.get((x, y), -1), score + row[x] + (row[y] if x != y else 0))
            states = nxt
        return max(states.values())
    if case_id == "heldout_target_sum_ways":
        counts = {0: 1}
        for value in data["nums"]:
            nxt: dict[int, int] = {}
            for total, count in counts.items():
                nxt[total + value] = nxt.get(total + value, 0) + count
                nxt[total - value] = nxt.get(total - value, 0) + count
            counts = nxt
        return counts.get(data["target"], 0)
    if case_id == "heldout_coin_change_combinations":
        dp = [1] + [0] * data["amount"]
        for coin in data["coins"]:
            for total in range(coin, data["amount"] + 1):
                dp[total] += dp[total - coin]
        return dp[-1]
    if case_id == "heldout_word_break":
        s, words = data["s"], set(data["word_dict"])
        dp = [True] + [False] * len(s)
        for i in range(1, len(s) + 1):
            dp[i] = any(dp[j] and s[j:i] in words for j in range(i))
        return dp[-1]
    if case_id == "heldout_kth_missing_positive":
        missing = []
        values = set(data["arr"])
        value = 1
        while len(missing) < data["k"]:
            if value not in values:
                missing.append(value)
            value += 1
        return missing[-1]
    if case_id == "heldout_ship_capacity":
        weights, days = data["weights"], data["days"]
        def needed(capacity: int) -> int:
            used, day_count = 0, 1
            for weight in weights:
                if used + weight > capacity:
                    day_count += 1
                    used = 0
                used += weight
            return day_count
        low, high = max(weights), sum(weights)
        while low < high:
            mid = (low + high) // 2
            if needed(mid) <= days:
                high = mid
            else:
                low = mid + 1
        return low
    if case_id == "heldout_median_two_sorted":
        values = sorted(data["nums1"] + data["nums2"])
        middle = len(values) // 2
        return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
    if case_id == "heldout_trapping_rain_water":
        height = data["height"]
        left, right, left_max, right_max, total = 0, len(height) - 1, 0, 0, 0
        while left < right:
            if height[left] <= height[right]:
                left_max = max(left_max, height[left])
                total += left_max - height[left]
                left += 1
            else:
                right_max = max(right_max, height[right])
                total += right_max - height[right]
                right -= 1
        return total
    if case_id == "heldout_longest_ones_k_flips":
        left = zeros = best = 0
        for right, value in enumerate(data["nums"]):
            zeros += value == 0
            while zeros > data["k"]:
                zeros -= data["nums"][left] == 0
                left += 1
            best = max(best, right - left + 1)
        return best
    if case_id == "heldout_group_ones_circular":
        nums = data["nums"]
        window = sum(nums)
        if window <= 1:
            return 0
        doubled = nums + nums
        current = sum(doubled[:window])
        best = current
        for right in range(window, len(nums) + window - 1):
            current += doubled[right] - doubled[right - window]
            best = max(best, current)
        return window - best
    if case_id == "heldout_eventual_safe_nodes":
        graph = data["graph"]
        color = [0] * len(graph)
        def safe(node: int) -> bool:
            if color[node]:
                return color[node] == 2
            color[node] = 1
            if all(safe(nxt) for nxt in graph[node]):
                color[node] = 2
            return color[node] == 2
        return [node for node in range(len(graph)) if safe(node)]
    if case_id == "heldout_parallel_courses":
        n = data["n"]
        graph = [[] for _ in range(n)]
        indegree = [0] * n
        for u, v in data["relations"]:
            graph[u - 1].append(v - 1)
            indegree[v - 1] += 1
        queue = deque(i for i, degree in enumerate(indegree) if degree == 0)
        semesters = seen = 0
        while queue:
            semesters += 1
            for _ in range(len(queue)):
                node = queue.popleft()
                seen += 1
                for nxt in graph[node]:
                    indegree[nxt] -= 1
                    if indegree[nxt] == 0:
                        queue.append(nxt)
        return semesters if seen == n else -1
    if case_id == "heldout_open_lock":
        dead = set(data["deadends"])
        target = data["target"]
        if "0000" in dead:
            return -1
        queue = deque([("0000", 0)])
        seen = {"0000"}
        while queue:
            state, steps = queue.popleft()
            if state == target:
                return steps
            for i, ch in enumerate(state):
                for delta in (-1, 1):
                    nxt = state[:i] + str((int(ch) + delta) % 10) + state[i + 1:]
                    if nxt not in dead and nxt not in seen:
                        seen.add(nxt)
                        queue.append((nxt, steps + 1))
        return -1
    if case_id == "heldout_cheapest_flight_k_stops":
        inf = 10**18
        dist = [inf] * data["n"]
        dist[data["src"]] = 0
        for _ in range(data["k"] + 1):
            nxt = dist[:]
            for u, v, price in data["flights"]:
                if dist[u] < inf:
                    nxt[v] = min(nxt[v], dist[u] + price)
            dist = nxt
        return -1 if dist[data["dst"]] == inf else dist[data["dst"]]
    if case_id == "heldout_minimum_effort_path":
        heights = data["heights"]
        m, n = len(heights), len(heights[0])
        dist = [[10**18] * n for _ in range(m)]
        dist[0][0] = 0
        heap = [(0, 0, 0)]
        while heap:
            effort, r, c = heapq.heappop(heap)
            if (r, c) == (m - 1, n - 1):
                return effort
            if effort != dist[r][c]:
                continue
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < m and 0 <= nc < n:
                    candidate = max(effort, abs(heights[r][c] - heights[nr][nc]))
                    if candidate < dist[nr][nc]:
                        dist[nr][nc] = candidate
                        heapq.heappush(heap, (candidate, nr, nc))
    if case_id == "heldout_connect_points_mst":
        points = data["points"]
        n = len(points)
        used = [False] * n
        dist = [10**18] * n
        dist[0] = 0
        total = 0
        for _ in range(n):
            node = min((i for i in range(n) if not used[i]), key=lambda i: dist[i])
            used[node] = True
            total += dist[node]
            for nxt in range(n):
                if not used[nxt]:
                    weight = abs(points[node][0] - points[nxt][0]) + abs(points[node][1] - points[nxt][1])
                    dist[nxt] = min(dist[nxt], weight)
        return total
    if case_id == "heldout_longest_happy_prefix":
        s = data["s"]
        pi = [0] * len(s)
        for i in range(1, len(s)):
            j = pi[i - 1]
            while j and s[i] != s[j]:
                j = pi[j - 1]
            if s[i] == s[j]:
                j += 1
            pi[i] = j
        return s[:pi[-1]]
    if case_id == "heldout_minimum_window":
        s, t = data["s"], data["t"]
        need = Counter(t)
        missing = len(t)
        left = 0
        best = (10**9, 0, 0)
        for right, ch in enumerate(s, 1):
            if need[ch] > 0:
                missing -= 1
            need[ch] -= 1
            while missing == 0:
                if right - left < best[0]:
                    best = (right - left, left, right)
                old = s[left]
                need[old] += 1
                if need[old] > 0:
                    missing += 1
                left += 1
        return "" if best[0] == 10**9 else s[best[1]:best[2]]
    if case_id == "heldout_repeated_substring":
        s = data["s"]
        return s in (s + s)[1:-1]
    if case_id == "heldout_largest_histogram_rectangle":
        heights = data["heights"] + [0]
        stack: list[int] = []
        best = 0
        for i, height in enumerate(heights):
            while stack and heights[stack[-1]] > height:
                h = heights[stack.pop()]
                left = stack[-1] + 1 if stack else 0
                best = max(best, h * (i - left))
            stack.append(i)
        return best
    if case_id == "heldout_remove_k_digits":
        stack: list[str] = []
        k = data["k"]
        for digit in data["num"]:
            while k and stack and stack[-1] > digit:
                stack.pop()
                k -= 1
            stack.append(digit)
        if k:
            stack = stack[:-k]
        return "".join(stack).lstrip("0") or "0"
    if case_id == "heldout_sliding_window_max":
        nums, k = data["nums"], data["k"]
        queue: deque[int] = deque()
        result = []
        for i, value in enumerate(nums):
            while queue and queue[0] <= i - k:
                queue.popleft()
            while queue and nums[queue[-1]] <= value:
                queue.pop()
            queue.append(i)
            if i >= k - 1:
                result.append(nums[queue[0]])
        return result
    if case_id in {"heldout_bst_kth_smallest", "heldout_tree_right_view", "heldout_bst_lca", "heldout_tree_house_robber", "heldout_binary_tree_cameras"}:
        nodes = data["nodes"]
        tree = _tree(nodes)
        def valid(index: int | None) -> bool:
            return index is not None and index < len(tree) and tree[index] is not None
        if case_id == "heldout_bst_kth_smallest":
            order: list[Any] = []
            def inorder(index: int) -> None:
                if not valid(index):
                    return
                inorder(2 * index + 1)
                order.append(nodes[index])
                inorder(2 * index + 2)
            inorder(0)
            return order[data["k"] - 1]
        if case_id == "heldout_tree_right_view":
            result = []
            queue = deque([0])
            while queue:
                level = []
                for _ in range(len(queue)):
                    index = queue.popleft()
                    level.append(nodes[index])
                    for child in (2 * index + 1, 2 * index + 2):
                        if valid(child):
                            queue.append(child)
                result.append(level[-1])
            return result
        if case_id == "heldout_bst_lca":
            index = 0
            low, high = sorted((data["p"], data["q"]))
            while valid(index):
                value = nodes[index]
                if value < low:
                    index = 2 * index + 2
                elif value > high:
                    index = 2 * index + 1
                else:
                    return value
        if case_id == "heldout_tree_house_robber":
            def rob(index: int) -> tuple[int, int]:
                if not valid(index):
                    return 0, 0
                left = rob(2 * index + 1)
                right = rob(2 * index + 2)
                take = nodes[index] + left[1] + right[1]
                skip = max(left) + max(right)
                return take, skip
            return max(rob(0))
        cameras = 0
        def camera_state(index: int) -> int:
            nonlocal cameras
            if not valid(index):
                return 2
            left = camera_state(2 * index + 1)
            right = camera_state(2 * index + 2)
            if left == 0 or right == 0:
                cameras += 1
                return 1
            return 2 if left == 1 or right == 1 else 0
        if camera_state(0) == 0:
            cameras += 1
        return cameras
    if case_id in {"heldout_equations_satisfiable", "heldout_earliest_friendship"}:
        if case_id == "heldout_equations_satisfiable":
            parent = {ch: ch for ch in "abcdefghijklmnopqrstuvwxyz"}
            def find(x: str) -> str:
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x
            for equation in data["equations"]:
                if equation[1:3] == "==":
                    parent[find(equation[0])] = find(equation[3])
            return all(equation[1:3] != "!=" or find(equation[0]) != find(equation[3]) for equation in data["equations"])
        parent = list(range(data["n"]))
        count = data["n"]
        def find_int(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for timestamp, a, b in sorted(data["logs"]):
            ra, rb = find_int(a), find_int(b)
            if ra != rb:
                parent[ra] = rb
                count -= 1
                if count == 1:
                    return timestamp
        return -1
    if case_id == "heldout_count_smaller_after_self":
        nums = data["nums"]
        return [sum(other < value for other in nums[i + 1:]) for i, value in enumerate(nums)]
    if case_id == "heldout_range_add_point_query":
        diff = [0] * (data["n"] + 1)
        for left, right, delta in data["updates"]:
            diff[left] += delta
            diff[right + 1] -= delta
        values, current = [], 0
        for value in diff[:-1]:
            current += value
            values.append(current)
        return [values[index] for index in data["queries"]]
    if case_id == "heldout_single_number_three":
        result = 0
        for bit in range(32):
            if sum((value >> bit) & 1 for value in data["nums"]) % 3:
                result |= 1 << bit
        return result - (1 << 32) if result >= (1 << 31) else result
    if case_id == "heldout_nth_ugly_number":
        values = [1]
        i2 = i3 = i5 = 0
        while len(values) < data["n"]:
            nxt = min(values[i2] * 2, values[i3] * 3, values[i5] * 5)
            values.append(nxt)
            while values[i2] * 2 <= nxt:
                i2 += 1
            while values[i3] * 3 <= nxt:
                i3 += 1
            while values[i5] * 5 <= nxt:
                i5 += 1
        return values[-1]
    if case_id == "heldout_source_scc_count":
        n = data["n"]
        graph = [[] for _ in range(n)]
        reverse = [[] for _ in range(n)]
        for u, v in data["edges"]:
            graph[u].append(v)
            reverse[v].append(u)
        seen: set[int] = set()
        order: list[int] = []
        def dfs(node: int) -> None:
            seen.add(node)
            for nxt in graph[node]:
                if nxt not in seen:
                    dfs(nxt)
            order.append(node)
        for node in range(n):
            if node not in seen:
                dfs(node)
        component = [-1] * n
        def assign(node: int, label: int) -> None:
            component[node] = label
            for nxt in reverse[node]:
                if component[nxt] < 0:
                    assign(nxt, label)
        label = 0
        for node in reversed(order):
            if component[node] < 0:
                assign(node, label)
                label += 1
        indegree = [0] * label
        for u, v in data["edges"]:
            if component[u] != component[v]:
                indegree[component[v]] += 1
        return sum(value == 0 for value in indegree)
    if case_id == "heldout_bipartite_matching_size":
        graph: dict[str, list[str]] = {node: [] for node in data["left"]}
        for left, right in data["edges"]:
            graph[left].append(right)
        matched: dict[str, str] = {}
        def augment(left: str, seen: set[str]) -> bool:
            for right in graph[left]:
                if right in seen:
                    continue
                seen.add(right)
                if right not in matched or augment(matched[right], seen):
                    matched[right] = left
                    return True
            return False
        return sum(augment(left, set()) for left in data["left"])
    raise KeyError(case_id)


def _hash_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_heldout_benchmark() -> dict[str, Any]:
    cases = []
    oracle_hash = hashlib.sha256(inspect.getsource(oracle).encode("utf-8")).hexdigest()
    for definition in _definitions():
        input_data = definition.pop("input_data")
        expected = oracle(definition["id"], input_data)
        sample = {
            "input_data": input_data,
            "expected": expected,
            "input_sha256": _hash_json(input_data),
            "expected_sha256": _hash_json(expected),
        }
        case = {
            **definition,
            "samples": [sample],
            "oracle": {"implementation": "scripts/freeze_heldout_benchmark.py:oracle", "sha256": oracle_hash},
        }
        case["case_sha256"] = _hash_json(case)
        cases.append(case)
    return {
        "schema_version": "unseen-family-cases-v1",
        "benchmark_version": "heldout-v1-20260713",
        "created_at": datetime.now().astimezone().isoformat(),
        "description": "Forty newly frozen sample-0 tasks from public problem sources. No solver, tracker, verifier, or generated artifact was used to author this file.",
        "cases": cases,
    }


def validate_payload(payload: dict[str, Any]) -> None:
    cases = payload.get("cases") or []
    if len(cases) != 40:
        raise ValueError(f"expected 40 held-out cases, found {len(cases)}")
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("held-out case ids are not unique")
    deterministic_ids = {case.id for case in benchmark_cases()}
    overlap = deterministic_ids & set(ids)
    if overlap:
        raise ValueError(f"held-out ids overlap deterministic cases: {sorted(overlap)}")
    strong = strong_family_ids_from_capabilities(load_family_capabilities())
    covered = {case["family_id"] for case in cases}
    if covered != strong:
        raise ValueError(f"strong-family coverage mismatch: missing={sorted(strong-covered)} extra={sorted(covered-strong)}")
    errors = validate_unseen_family_cases(payload)
    if errors:
        raise ValueError("; ".join(errors))
    for case in cases:
        sample = case["samples"][0]
        recomputed = oracle(case["id"], sample["input_data"])
        if recomputed != sample["expected"]:
            raise ValueError(f"oracle mismatch: {case['id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_heldout_benchmark()
    validate_payload(payload)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "cases": len(payload["cases"]), "families": len({case["family_id"] for case in payload["cases"]}), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
