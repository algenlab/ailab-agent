# 评估与 Benchmark

## 1. 评估目标

AlgoLab 的评估不是只看页面是否好看，而是证明系统能把 LLM 生成的算法可视化变得更正确、更稳定、更适合学习。

核心问题：

- 最终答案是否正确。
- 过程轨迹是否符合算法不变量。
- 可视化对象是否绑定到正确语义对象。
- HTML 页面是否可运行。
- 页面是否支持有效学习交互。

## 2. Benchmark 范围

当前确定性 benchmark 见：

- `tests/benchmark_cases.py`
- `benchmark/benchmark_cases_list.md`

已有 14 个代表题，覆盖：

- 一维 DP：打家劫舍。
- 二维 DP：不同路径。
- 数组指针：二分查找。
- 图搜索：BFS 最短层数。
- 字符串：KMP。
- 哈希表：Two Sum。
- 单调栈：每日温度。
- 排序：插入排序。
- 树：LCA。
- 堆：第 K 大。
- Trie：前缀计数。
- 并查集：省份数量。
- 回溯：全排列。
- 几何：凸包。

第一阶段 V1 benchmark 目标扩展到 80 到 120 个题目样例。

完整 V1 的算法族覆盖目标应更广，逐步加入：

- 数组基础、前缀和、差分、二分答案、滑动窗口。
- 排序、快速选择、计数 / 桶 / 基数排序。
- 链表、栈、队列、单调栈、单调队列。
- 哈希表、集合、前缀和计数。
- 字符串匹配、Trie、KMP、Rabin-Karp、Z Algorithm、Manacher。
- 一维 DP、二维 DP、背包、区间 DP、树形 DP、状态压缩 DP、数位 DP。
- 贪心、区间调度、Huffman。
- BFS、DFS、拓扑排序、连通分量、二分图、SCC、割点、桥。
- Dijkstra、Bellman-Ford、Floyd-Warshall、0-1 BFS、A* 基础演示。
- Kruskal、Prim、并查集。
- 二分图匹配、Edmonds-Karp 网络流教学版。
- 二叉树、BST、LCA、树直径、树遍历。
- 堆、优先队列、TopK、数据流中位数。
- 回溯、排列组合、N 皇后、数独、递归树。
- 位运算、快速幂、筛法、组合数、GCD。
- 凸包、扫描线、方向判断、线段相交。
- 线段树、树状数组、稀疏表。

扩展 benchmark 时，每个算法族先选代表题和代表输入，不要求一开始覆盖所有变体。

完整 V1 可以逐步扩展到 200 到 300 个经典样例。该数字是长期覆盖目标，不是下一轮实施必须一次完成的任务。

## 3. 指标定义

系统正确性指标：

- 最终答案正确率：`solve(input_data)` 是否等于 expected。
- solve / trace 一致率：`solve_result == trace.result`。
- verifier 一致率：`solve_result == verify(input_data)`。
- trace schema 通过率：是否符合 `semantic-trace-v1`。
- 过程转移正确率：process validator 是否通过。
- 关键步骤覆盖率：小规模样例是否逐帧记录关键更新。
- SceneGraph 可渲染率：scene validator 是否通过。
- HTML 可运行率：页面加载、步进、播放是否无 JS error。

教学体验指标：

- 当前步骤解释完整度。
- 转移公式可见率。
- 依赖对象可见率。
- 不变量展示率。
- 交互完整性。
- 人工教学质量评分。

## 4. Baseline

论文实验建议 baseline：

- LLM 直接生成 HTML。
- LLM 生成 trace，但无 process validator。
- LLM 生成 trace，但无 SceneGraph compiler。
- 完整 AlgoLab。

可选模型 baseline：

- GPT 系列直接 HTML。
- Claude 系列直接 HTML。
- OpenAI-compatible 本地或远程模型。

评估必须固定题目、输入、prompt、模型版本和失败分类。

正式报告使用 `condition` 区分实验口径。完整系统记为 `algolab_full`；直接 HTML baseline 记为 `direct_html_baseline`。直接 HTML baseline 只能作为外部实验结果进入 `llm_benchmark_report.json`，不进入 AlgoLab 主发布路径，也不能绕过 Renderer 只能消费 SceneGraph / BuildArtifact 的约束。

## 5. Ablation

建议消融：

- 无 SemanticTrace：直接让 LLM 生成页面。
- 无 Tracer API：LLM 手写 events。
- 无 process invariant：只检查最终答案和 schema。
- 无 repair loop：失败不修复。
- 无 SceneGraph compiler：trace 直接驱动前端自由渲染。
- 完整系统。

关注每个模块移除后：

- 错误率是否上升。
- 失败是否更难定位。
- HTML 可运行率是否下降。
- 教学步骤是否变弱。

报告层保留两个核心消融标签：

- `no_process_validator`：不执行族级 process invariant / coverage rule，仅统计最终答案、schema 和可渲染性，用于衡量过程校验对错误发布风险和失败定位的贡献。
- `no_scenegraph_compiler`：不经过 SceneGraph compiler 结构化约束，仅作为外部消融结果进入 report，用于衡量视觉结构约束对 HTML 可运行率、交互覆盖和失败定位的贡献。

`scripts/build_evaluation_report.py` 会从 LLM benchmark report 的 `condition`、`experiment_condition`、`benchmark_condition`、`baseline` 或 `ablation` 字段聚合 `condition_summary`，并输出 `evaluation_condition_summary.csv`。每个 condition 必须记录 `total`、`passed`、`failed`、`pass_rate` 和 `failure_types`。

## 6. 人工评价 Rubric

每个生成页面可按 1 到 5 分评价：

- 算法讲解清晰度。
- 当前步骤可理解性。
- 依赖关系可见性。
- 交互学习价值。
- 视觉布局稳定性。
- 校验证据可读性。

人工评价时应隐藏系统名称，避免偏见。

## 7. 失败类型分类

生成失败应归类：

- `answer_mismatch`：最终答案错误。
- `trace_result_mismatch`：trace result 与 solve 不一致。
- `schema_error`：SemanticTrace 不合法。
- `target_error`：target id 不可解析或越界。
- `process_error`：过程不满足不变量。
- `coverage_error`：关键步骤缺失。
- `scene_error`：SceneGraph 不可渲染。
- `html_error`：HTML 加载或交互失败。
- `teaching_error`：解释不足、公式缺失、依赖不可见。

失败分类必须进入 benchmark report，不能只记录成功 / 失败。

评估报告还会输出跨 condition 的 `failure_type_summary` 和 `evaluation_failure_types.csv`，用于比较完整系统、直接 HTML baseline、无 process validator、无 SceneGraph compiler 等口径下的失败分布。

## 7.1 过程校验注册表

过程校验能力由 `algolab/verification/process_validator.py` 中的注册表声明。每个算法族必须明确：

- `status`：`strong` 表示存在可复用 process invariant；`fallback` 表示只走基础 schema / scene / answer gate，不声明强过程校验。
- `coverage_rule`：说明该族的关键步骤覆盖规则或降级边界。
- `failure_type`：benchmark report 中使用的失败类型。
- `checks`：强校验族对应的 validator 入口名称。

当前注册入口：

- `dp`：强校验，覆盖 unique paths、house robber、subset sum、LCS、编辑距离、背包和区间 DP 等 matcher-gated 规则。
- `bfs`：强校验，无权图 BFS 距离不变量。
- `binary_search`：强校验，搜索窗口边界不变量。
- `monotonic_stack`：强校验，单调栈结构不变量。
- `hash`：明确降级，只执行基础 schema / scene / answer gate 和可观测过程证据检查。
- `tree`：强校验入口覆盖 BST / LCA；普通树遍历没有匹配信号时仍按基础门禁处理。
- `union_find`：强校验，并查集 parent forest 不变量。

未知算法族必须返回 `process_uncovered` 降级画像，不能标记为 `strong`，也不能在没有族级 invariant 的情况下假装通过强校验。过程错误消息进入 benchmark 时会映射到 `process_invariant`、`coverage_error`、`process_fallback` 或 `process_uncovered` 等类型。

## 8. 必须保留的产物

每次正式评估应保存：

- 输入题目和样例。
- 模型配置。
- 原始 LLM 输出。
- repair 轮次和错误信息。
- BuildArtifact JSON。
- HTML 产物。
- validation report。
- 截图或浏览器 smoke 结果。
- 失败分类。

这些产物用于论文复现和回归排查。

## 9. 可复现包

P9.2 的可复现包由固定脚本生成：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_reproducibility_package.py --output-dir output/reproducibility
```

输出：

- `output/reproducibility/reproducibility_package.json`：结构化记录环境、模型配置入口、样例输入、运行命令和输出路径。
- `output/reproducibility/README.md`：给研究复现者阅读的简明说明。
- `output/reproducibility/commands.sh`：可直接查看或逐条执行的命令清单。

确定性质量检查只走本地 fixtures、deterministic benchmark 和浏览器 smoke，不调用 LLM：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

LLM benchmark 单独运行，模型配置通过环境变量或本地 ignored settings 文件提供，输出模型配置、repair 轮次和失败分类：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py --output-dir output/llm_benchmark --condition algolab_full
```

两条路径必须分开理解：

- deterministic benchmark：来源是 `tests/benchmark_cases.py`，用于证明主 pipeline、validator、SceneGraph compiler、renderer 和浏览器 smoke 的稳定性。
- LLM benchmark：来源是 `scripts/run_llm_benchmark.py`，用于评估真实模型生成、repair 和失败分类，不作为确定性质量检查的前置条件。

常用输出路径：

- `output/dashboard/dashboard.json`
- `output/dashboard/index.html`
- `output/evaluation/evaluation_manifest.json`
- `output/evaluation/evaluation_report.json`
- `output/llm_benchmark/llm_benchmark_report.json`
- `output/llm_benchmark/llm_benchmark_report.md`

## 10. V1 发布门禁

P9.3 的 V1 发布门禁由确定性证据报告和完整质量检查共同证明：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_v1_release_gate.py --output-dir output/release_gate
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

输出：

- `output/release_gate/v1_release_gate.json`：记录第一阶段 benchmark 样例数、黄金样例 browser smoke 覆盖、Debug Drawer 证据、失败分类输出和固定 Python 文档检查。
- `output/release_gate/v1_release_gate.md`：面向发布审阅的简明门禁表。

门禁要求：

- deterministic benchmark 样例数必须位于 80 到 120。
- `unique_paths`、`graph_bfs`、`binary_search`、`daily_temperatures` 必须进入 browser smoke。
- Debug Drawer 必须能展开查看 raw validation、release gate、raw state 和 artifact。
- evaluation report 必须能输出失败分类 CSV。
- 文档中的 Python 命令必须使用 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3`。
