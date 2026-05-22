# 经典算法覆盖矩阵

覆盖策略：按“视觉形态”覆盖经典算法，而不是给每个算法单独写 prompt 和 renderer。

## 当前视觉形态

| 视觉形态 | 已有能力 | 代表算法 | 状态 | 后续新增同类算法工作量 |
|---|---|---|---|---|
| array + pointer | 数组 cell、高亮、指针标签 | 二分查找、双指针、滑动窗口、排序、前缀和 | 已验证 fixture + 浏览器 | 低 |
| matrix / DP table | 二维表格、高亮、依赖说明 | 不同路径、背包、LCS、编辑距离 | 已验证 fixture + 浏览器 | 低 |
| graph | 节点、边、访问状态 | BFS、DFS、拓扑排序、基础最短路 | 已验证 fixture + 浏览器 | 中 |
| stack | 垂直容器、push/pop 高亮 | 单调栈、括号匹配、递归调用栈 | 已验证 fixture + 浏览器 | 低 |
| queue / deque | 横向队列、队首/队尾标识 | BFS 队列、单调队列、滑窗候选队列 | 已验证 fixture + 浏览器 | 低 |
| map / hash table | key-value 列表 | Two Sum、频次统计、哈希去重 | 已验证 fixture + 浏览器 | 低 |
| tree | 层级树布局 | 二叉树遍历、BST、LCA、树形 DP、Huffman 合并树 | 已验证 fixture + 浏览器 | 中 |
| heap | 按层展示数组堆 | 堆操作、TopK、堆排序、合并 K 路、Huffman | 已验证 fixture + 浏览器 | 中 |
| trie | 前缀树布局 | Trie 插入/查询、单词搜索前缀 | 已验证 fixture + 浏览器 | 中 |
| union-find | parent forest | 合并、连通分量、路径压缩、冗余连接 | 已验证 fixture + 浏览器 | 中 |
| recursion_tree | 搜索树层级布局 | 全排列、组合、N 皇后、数独搜索树 | 已验证 fixture + 浏览器 | 中 |
| string | 字符串按字符 cell 展示 | KMP、Rabin-Karp、Manacher、编辑距离 | 已验证 fixture + 浏览器 | 中 |
| geometry | 坐标平面点集、线段、凸包边、扫描线 | 凸包、扫描线、最近点对 | 已验证 fixture + 浏览器 | 高 |

## 确定性覆盖样例

当前测试覆盖 13 个算法族、27 个经典子形态：

| 算法族 | 已覆盖子形态 |
|---|---|
| 二分 / 双指针 / 滑动窗口 | 二分查找、双指针、滑动窗口 |
| 一维 / 二维 DP | 打家劫舍一维 DP、不同路径二维 DP |
| 哈希表 / map | Two Sum 哈希表 |
| BFS / DFS 基础图 | BFS、DFS |
| 栈 / 队列 / 单调栈 | 单调栈、队列 |
| 排序 | 快速排序分区 |
| 树 / BST / LCA | 二叉树遍历、BST 最近公共祖先 |
| 堆 / TopK / Huffman | 堆顶弹出、TopK 小顶堆、Huffman 合并 |
| Trie | 插入、前缀查询 |
| 并查集 | 合并、路径压缩 |
| 回溯 / 递归 | 调用栈、搜索树 |
| 字符串高级算法 | KMP、Rabin-Karp、Manacher |
| 几何 / 扫描线 | 凸包、扫描线线段相交 |

覆盖产物：

- `output/algolab_algorithm_family_coverage.html`
- `output/algolab_algorithm_family_coverage.json`
- `output/algolab_benchmark_coverage.html`
- `output/algolab_benchmark_coverage.json`

质量检查：

- `python -m tests.offline_regression`
- `python -m tests.benchmark_regression`
- `python -m tests.browser_smoke`
- `python scripts/run_quality_checks.py`

真实 LLM 生成评测：

- `python scripts/run_llm_benchmark.py`
- `python scripts/run_llm_benchmark.py --all-samples`

LLM benchmark 不缓存模型输出，产物保存在 `output/llm_benchmark/`。
默认运行使用 1 个解法和严格 warning 模式；多解法评测可显式传 `--solutions 2`。

## 算法覆盖判断

| 算法族 | 当前可行性 | 主要风险 |
|---|---|---|
| 二分 / 双指针 / 滑动窗口 | 高 | LLM 是否持续输出 pointer target |
| 一维/二维 DP | 高 | 大表格可读性和依赖箭头密度 |
| BFS/DFS 基础图 | 高 | 大图布局拥挤 |
| 拓扑排序 / Dijkstra / MST | 中 | 权重、松弛、边状态还需更强视觉编码 |
| 排序 | 中 | swap/move 动画目前是静态 step 展示 |
| 单调栈 / 单调队列 | 中 | 需要更明确的弹出原因和候选区间 |
| 链表 | 中 | 可用 node/edge 表示，但缺横向链表专用布局 |
| 树 / Trie / 堆 / 并查集 | 中 | 已有 fixture 级布局，需要更多真实题测试 |
| 回溯 / 递归树 | 中 | 大搜索树需要折叠/裁剪策略 |
| 字符串高级算法 | 中 | failure 指针、回文半径等可读性还需更强 pointer/arc 表示 |
| 几何 / 扫描线 | 高 | 多线段密集布局、坐标缩放和遮挡仍需截图回归 |
| 网络流 / 匹配 | 高 | 需要容量、残量图、增广路径的专用视觉编码 |

## 工作量估计

低工作量：

- 复用已有 array/matrix/graph/stack/map。
- 通常只需补 1 个 fixture 和 1 个浏览器样例。
- 不改 prompt，不改 semantic op。

中工作量：

- 需要扩展 Scene Compiler 的布局识别或 renderer 的一个通用组件。
- 需要 2-3 个 fixtures，覆盖正常/边界/高密度场景。
- 不应新增算法专用 op。

高工作量：

- 需要新的视觉几何系统，例如坐标平面、线段、多边形、残量网络。
- 需要布局阈值测试和截图回归。
- 仍然应保持 semantic op 不变，最多扩展 SceneObject meta。

## 当前结论

新架构已经把新增成本从“每个算法维护 prompt + renderer”降到“新增视觉形态时扩展 compiler/runtime”。  
同一视觉形态内继续增加算法，工作量较低；跨入新视觉形态时工作量中等到高。
