# 五方法产物对比样例库

本目录从已完成的 Full-200 实验中抽取真实产物，用于在 GitHub 中快速横向查看。
抽样采用“一类算法家族一个典型案例”：覆盖全部 23 个家族、23 个案例、5 种方法，共 115 组方法产物。

> 本目录是实验产物展示，不替代完整统计结果。完整数字以 `docs/EXPERIMENT_RESULTS.md` 和 `docs/EXPERIMENT_RESULTS_DETAILED.md` 为准。

## 五种方法

| 方法 | 说明 | 每例保存内容 |
| --- | --- | --- |
| AlgoTutorGen / Stage2 | AlgoTutorGen 的验证链路与 Stage2 视觉增强产物。 | HTML、截图、审计摘要 |
| Direct HTML | 模型直接生成完整 HTML 的基线。 | HTML、截图、审计摘要 |
| WebGen-Agent | WebGen-Agent 生成的前端项目源码与审计截图。 | 源码、截图、审计摘要 |
| Direct + HTMLCure (strict) | Direct HTML 经 HTMLCure 修复后的 strict 结果。 | HTML、截图、审计摘要 |
| Direct-BrowserRepair (1-call) | Direct HTML 使用一次通用浏览器反馈修复后的结果。 | HTML、截图、审计摘要 |

## 如何阅读

- 点击案例进入同一输入下的五方法对比页。
- `page.html` 是实际用于视觉评审的页面；WebGen-Agent 因为是前端工程，保存在 `source/`。
- `screenshot.png` 是实验使用的真实截图。
- `audit.json` 包含九项机器判定、Machine OK、教学/视觉评分摘要和来源哈希。
- Machine OK 只有在九项判定全部通过时才为 PASS。

## 案例索引

| 家族 | 案例 | AlgoTutorGen / Stage2 | Direct HTML | WebGen-Agent | Direct + HTMLCure (strict) | Direct-BrowserRepair (1-call) |
| --- | --- | --- | --- | --- | --- | --- |
| BFS/DFS 基础图 | [拓扑排序](cases/graph_topological_sort/README.md) | PASS | PASS | PASS | PASS | PASS |
| DP 核心扩展 | [完全背包零钱兑换](cases/complete_knapsack_coin_change/README.md) | PASS | PASS | FAIL | PASS | PASS |
| Trie | [Trie 前缀计数](cases/trie_prefix/README.md) | PASS | FAIL | FAIL | FAIL | FAIL |
| 一维 DP | [打家劫舍](cases/house_robber/README.md) | PASS | PASS | FAIL | PASS | PASS |
| 二分 | [二分查找](cases/binary_search/README.md) | PASS | PASS | FAIL | FAIL | PASS |
| 二维 DP | [不同路径](cases/unique_paths/README.md) | PASS | FAIL | PASS | FAIL | FAIL |
| 几何 / 扫描线 | [凸包](cases/convex_hull/README.md) | PASS | PASS | FAIL | PASS | PASS |
| 区间结构 | [线段树区间和](cases/segment_tree_range_sum/README.md) | PASS | FAIL | FAIL | FAIL | FAIL |
| 哈希表 / map | [两数之和](cases/two_sum/README.md) | PASS | FAIL | FAIL | FAIL | FAIL |
| 回溯 / 递归 | [全排列](cases/permutations/README.md) | PASS | FAIL | FAIL | FAIL | FAIL |
| 图高级 | [割点和桥](cases/articulation_bridges/README.md) | PASS | PASS | FAIL | FAIL | PASS |
| 堆 / TopK / Huffman | [数组中的第 K 个最大元素](cases/kth_largest/README.md) | PASS | FAIL | FAIL | FAIL | FAIL |
| 字符串高级算法 | [KMP 字符串匹配](cases/kmp/README.md) | PASS | FAIL | FAIL | FAIL | FAIL |
| 并查集 | [省份数量](cases/provinces/README.md) | PASS | PASS | FAIL | FAIL | PASS |
| 排序 | [插入排序](cases/insertion_sort/README.md) | PASS | FAIL | FAIL | FAIL | FAIL |
| 数学与位运算 | [快速幂取模](cases/fast_power_mod/README.md) | PASS | PASS | FAIL | FAIL | PASS |
| 数组指针 / 窗口 / 前缀 | [有序数组两数之和](cases/two_pointer_pair_sum/README.md) | PASS | PASS | FAIL | PASS | PASS |
| 最短路 / MST | [Dijkstra 最短路](cases/dijkstra_shortest_path/README.md) | PASS | PASS | FAIL | FAIL | PASS |
| 栈 / 队列 / 单调栈 | [每日温度](cases/daily_temperatures/README.md) | PASS | FAIL | FAIL | FAIL | FAIL |
| 树 / BST / LCA | [二叉树最近公共祖先](cases/lca/README.md) | PASS | FAIL | PASS | FAIL | FAIL |
| 树形 DP | [树形 DP 最大独立集](cases/tree_max_independent_set/README.md) | PASS | FAIL | FAIL | FAIL | PASS |
| 贪心 | [合并区间](cases/merge_intervals/README.md) | PASS | FAIL | PASS | FAIL | FAIL |
| 链表与缓存 | [反转链表](cases/reverse_linked_list/README.md) | PASS | FAIL | FAIL | FAIL | FAIL |

## 重新生成

源实验目录存在时，在仓库根目录运行：

```bash
TMPDIR=.tmp python3 scripts/build_method_artifact_gallery.py
```

只验证已提交目录：

```bash
TMPDIR=.tmp python3 scripts/build_method_artifact_gallery.py --validate-only
```
