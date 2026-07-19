# 五方法产物样例库设计

## 目标

在仓库内增加一份可直接浏览的产物样例库，让读者无需访问被忽略的 `output/` 目录，也能对同一算法案例下五种方法的真实页面、截图和评价结果进行横向比较。

## 方案选择

考虑过三种组织方式：

1. **按方法分目录**：复制最简单，但同一案例的横向比较需要在五个目录间来回跳转。
2. **按案例分目录（采用）**：一个案例下并列五种方法，最适合论文审阅和差异检查。
3. **只保存截图**：体积最小，但缺少可检查的 HTML、WebGen 源码和机器指标。

采用第二种方案，并保留必要源码。样例库不是新的实验结果，只是已完成实验的可浏览抽样。

## 抽样规则

从 Full-200 的 23 个算法家族中各选一个典型案例，形成 23 个案例、5 种方法、共 115 组方法产物。选择优先考虑算法辨识度和跨方法文件完整性。

| 算法家族 | 案例 ID | 案例 |
| --- | --- | --- |
| BFS/DFS 基础图 | `graph_topological_sort` | 拓扑排序 |
| DP 核心扩展 | `complete_knapsack_coin_change` | 完全背包零钱兑换 |
| Trie | `trie_prefix` | Trie 前缀计数 |
| 一维 DP | `house_robber` | 打家劫舍 |
| 二分 | `binary_search` | 二分查找 |
| 二维 DP | `unique_paths` | 不同路径 |
| 几何 / 扫描线 | `convex_hull` | 凸包 |
| 区间结构 | `segment_tree_range_sum` | 线段树区间和 |
| 哈希表 / map | `two_sum` | 两数之和 |
| 回溯 / 递归 | `permutations` | 全排列 |
| 图高级 | `articulation_bridges` | 割点和桥 |
| 堆 / TopK / Huffman | `kth_largest` | 数组中的第 K 个最大元素 |
| 字符串高级算法 | `kmp` | KMP 字符串匹配 |
| 并查集 | `provinces` | 省份数量 |
| 排序 | `insertion_sort` | 插入排序 |
| 数学与位运算 | `fast_power_mod` | 快速幂取模 |
| 数组指针 / 窗口 / 前缀 | `two_pointer_pair_sum` | 有序数组两数之和 |
| 最短路 / MST | `dijkstra_shortest_path` | Dijkstra 最短路 |
| 栈 / 队列 / 单调栈 | `daily_temperatures` | 每日温度 |
| 树 / BST / LCA | `lca` | 二叉树最近公共祖先 |
| 树形 DP | `tree_max_independent_set` | 树形 DP 最大独立集 |
| 贪心 | `merge_intervals` | 合并区间 |
| 链表与缓存 | `reverse_linked_list` | 反转链表 |

## 目录结构

```text
artifacts/method_comparison_samples/
├── README.md
├── manifest.json
└── cases/
    └── <case_id>/
        ├── README.md
        ├── case.json
        ├── algotutorgen_stage2/
        │   ├── page.html
        │   ├── screenshot.png
        │   └── audit.json
        ├── direct_html/
        ├── webgen_agent/
        │   ├── source/
        │   ├── screenshot.png
        │   └── audit.json
        ├── htmlcure_strict/
        └── browser_repair_1call/
```

除 WebGen-Agent 外，每种方法保存实际评审页面 `page.html`。WebGen-Agent 保存完整的生成工作区源码，但排除 `node_modules`、`dist`、缓存和 Git 元数据。

## 审计摘要

每个 `audit.json` 只保留可公开、可解释的信息：

- 方法名、案例 ID 和算法家族；
- 九项机器判定及 `machine_ok`；
- 教学总分、视觉总分和 11 个细分分数；
- strengths、weaknesses、recommendation 和置信度；
- 原始产物的仓库相对来源路径；
- 当前样例库内的页面、截图或源码入口。

不复制 API 密钥、原始模型响应、绝对用户路径或模型调用凭据。

## 可读性

根 `README.md` 说明五种方法、抽样边界和文件入口，并提供 23 个案例的 Machine OK 对照表。每个案例的 `README.md` 展示五张截图、页面/源码链接和九项指标表，便于在 GitHub 中直接查看。

## 验证

生成器必须在缺少任意源文件时失败，而不是静默跳过。自动测试检查：

- 恰好覆盖 23 个不同算法家族；
- 每个案例恰好包含五种方法；
- 所有截图非空；
- 非 WebGen 方法包含非空 HTML；
- WebGen 包含入口 HTML、依赖清单和源码；
- 所有 `audit.json` 含完整九项指标且不含绝对 `/ssd1/` 路径；
- 根清单和各案例 README 中的相对链接存在。

