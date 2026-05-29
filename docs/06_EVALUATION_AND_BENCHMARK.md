# 评估与 Benchmark

## 1. 评估目标

AlgoLab 的评估不是只看页面是否好看，而是证明系统能把 LLM 生成的算法可视化变得更正确、更稳定、更适合学习。

核心问题：

- 最终答案是否正确。
- 过程轨迹是否符合算法不变量。
- 可视化对象是否绑定到正确语义对象。
- HTML 页面是否可运行。
- 页面是否支持有效学习交互。

V1 之后评估重心调整为算法族级正确性。单个 benchmark case 只是证据，不是最终目标。系统要证明的是：同一套视觉原语、SemanticTrace 合同、过程校验和演示门禁能覆盖经典算法族，而不是为每道题堆专用规则。

评估优先级固定为：

| 优先级 | 指标 | 说明 |
|---|---|---|
| P0 | 答案正确 | `solve`、`trace.result`、`verify`、expected 或 oracle 一致 |
| P1 | 过程正确 | algorithm family invariant、状态转移、deps、覆盖率通过 |
| P2 | 演示正确 | trace 足以讲清算法，不缺关键步骤，不误导 |
| P3 | 可运行 | SceneGraph、HTML、播放、步进、Debug Drawer 正常 |
| P4 | 视觉质量 | 布局、美观、动画和交互 polish |

当前下一阶段优先建设 P0 到 P2。视觉质量不是短期阻塞项。

## 2. Benchmark 范围

当前确定性 benchmark 见：

- `tests/benchmark_cases.py`
- `benchmark/benchmark_cases_list.md`

当前 V1.2 deterministic benchmark 已有 69 个代表 case、250 个 samples。其中 V1 baseline `family_core` 层保持 60 cases / 213 samples，P16.2 新增 `expansion` 层 9 cases / 37 samples。当前覆盖：

- 一维 DP：打家劫舍。
- 二维 DP：不同路径。
- DP 核心扩展：0/1 背包、完全背包、多重背包基础、LCS、编辑距离、区间 DP、状态压缩 DP、数位 DP。
- 数组指针：二分查找、二分答案、双指针、滑动窗口、前缀和、差分数组、快慢指针。
- 图搜索：BFS 最短层数、DFS 遍历、连通分量、拓扑排序、二分图染色。
- 最短路 / MST：Dijkstra、Bellman-Ford、Floyd-Warshall、0-1 BFS、Kruskal。
- 字符串：KMP、Rabin-Karp、Z Algorithm、Manacher、字符串滑动窗口、Trie 前缀匹配。
- 哈希表：Two Sum。
- 单调栈：每日温度。
- 排序：插入排序。
- 链表：反转链表。
- 贪心：跳跃游戏。
- 树：中序遍历、LCA、树直径、树形 DP。
- 堆：第 K 大。
- Trie：前缀计数。
- 并查集：省份数量。
- 回溯：全排列。
- 几何：凸包。
- 区间结构：线段树、树状数组、稀疏表。
- 数学与位运算：GCD、快速幂、筛法、组合数、bitmask、lowbit。
- 图高级：Tarjan SCC、割点桥、二分图匹配、Edmonds-Karp。
- Expansion 层：贪心、最短路 / MST、堆、Trie、回溯、数学与位运算、几何、链表与缓存、图高级各至少 1 个 expansion case。

第一阶段 V1 benchmark 门禁范围从 80 到 120 个 deterministic samples 起步；P13.3 后 V1.1 本地确定性门禁范围调整为 80 到 220 个 V1 baseline deterministic samples，用于容纳 DP family core 和图基础 / 最短路 / MST 扩容。P16.2 后，V1 release gate 只统计 `smoke` / `family_core` 作为 baseline 样本窗口，`expansion` 层进入 family release gate 的总量、分层和过程通过率报告。

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

## 2.1 Benchmark 分层

V1 之后 benchmark 必须分层，不再把所有样例混成一个 pass/fail 总数。

| 层级 | 作用 | 门禁要求 |
|---|---|---|
| `smoke` | 证明主 pipeline、SceneGraph、HTML、浏览器 smoke 没坏 | 必须全通过 |
| `family_core` | 证明算法族核心子模式正确 | strong family 必须全通过 |
| `expansion` | 扩大经典题覆盖面和复杂变体 | 可分阶段提高通过率，但必须准确报告 |
| `property` | 固定 seed 的随机小规模性质测试 | 不进 V1 门禁，进入 robustness report |
| `llm_eval` | 真实 LLM 生成、repair、失败分类 | 不阻塞 deterministic gate，衡量真实产品能力 |

新增 case 必须声明：

- `family_id`
- `subfamily_id`
- `gate_layer`
- `support_level`
- `process_profile`
- `oracle_type`
- `oracle_risk`
- `oracle_reference`
- `demo_required`

如果当前数据结构尚未实现这些字段，执行 AI 应先完成 roadmap P10.1 到 P10.3，再继续扩 case。

## 2.2 算法族能力等级

算法族支持强度按族统计，不按单题宣传。

| 等级 | 含义 | 报告要求 |
|---|---|---|
| `strong` | 有族级 process invariant、覆盖规则、正反例测试和 family core benchmark | family core 不允许 fallback/uncovered |
| `medium_plus` | 多数核心过程可校验，复杂变体允许明确 fallback | 必须列出 fallback 子模式 |
| `medium` | 答案和视觉表达稳定，过程校验覆盖部分结构 | 不能宣传为强过程正确 |
| `basic` | 只能依赖 schema、answer、scene gate | 必须显示 `process_fallback` 或 `process_uncovered` |
| `planned` | 文档规划中 | 不进入强能力统计 |

每次 evaluation report 必须输出 family summary：

- case 数。
- sample 数。
- answer pass rate。
- process pass rate。
- demo readiness pass rate。
- scene/html pass rate。
- failure type 分布。
- fallback/uncovered 数量。

## 2.3 Oracle 要求

最终答案正确不能依赖 LLM 自证。每个 deterministic benchmark case 必须有 verifier 或 oracle 类型。

| Oracle 类型 | 适用场景 | 要求 |
|---|---|---|
| `closed_form` | 组合数、不同路径等 | 公式实现必须独立于被测 solve |
| `independent_reference` | BFS、排序、字符串表、区间查询 | 参考实现不能复制被测实现结构 |
| `bruteforce` | 小规模 DP、回溯、图、匹配 | 固定小输入规模，可穷举 |
| `property` | 排序、堆、并查集、几何性质 | 检查性质和不变量，不只比较一个答案 |

如果 case 的 verifier 与 solve 高度相似，必须标记为 oracle 风险，不能作为 strong family 的唯一证据。

每个 deterministic benchmark case 还必须暴露：

- `oracle_risk`：`none`、`missing_verifier` 或 `verifier_matches_solve`。
- `oracle_notes`：解释 oracle 证据是否独立，以及风险边界。
- `oracle_reference`：当 verifier 结构过于接近 solve，或需要额外佐证时，指向独立参考实现或性质检查入口。

当前独立 oracle 示例放在 `tests/oracles/`。P11.1 至少提供 DP、图、字符串、排序、并查集和区间结构示例；这些示例只定义 reference / property 形态，不生成随机样例。固定 seed 的随机小样例属于 P11.2。

## 2.3.1 Property Benchmark

P11.2 的随机小样例由 `tests/property_cases.py` 定义，运行入口是：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_property_benchmark.py --output-dir output/property_benchmark
```

报告输出：

- `output/property_benchmark/property_benchmark_report.json`
- `output/property_benchmark/property_benchmark_report.md`

该层只作为 family robustness evidence，不进入 V1 release gate，也不调用 LLM、renderer 或 HTML materialization。脚本固定默认 seed，报告显式记录 `release_gate_included: false`。

第一批覆盖：

- DP：house robber、subset sum、LCS、编辑距离、0/1 knapsack。
- 图：BFS layers、DFS connected、topological sort、Dijkstra positive weights。
- 字符串：KMP、Z Algorithm、Manacher。
- 排序：insertion sort、merge sort、quickselect。
- 并查集：random union/find connectivity queries。
- 区间结构：random range sum query/update。

每条结果必须包含 `family`、`family_id`、`subfamily`、`subfamily_id`、`input`、`expected`、`actual`、`ok` 和 `failure_type`。失败类型固定使用：

- `answer_mismatch`
- `exception`
- `oracle_error`

`summary.family_robustness` 按 family 聚合 total、passed、failed、pass_rate、subfamilies 和 failure type 分布，供 family 级鲁棒性报告使用。

## 2.3.2 Boundary Case Registry

P11.3 的边界覆盖登记由 `benchmark/boundary_cases.json` 定义，检查入口是：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_boundary_cases.py
```

该层不执行 LLM、不生成 HTML、不改变 deterministic benchmark 样例，只把当前 `family_core` case 的边界覆盖状态显式登记为两类证据：

- `coverage`：指向已有 deterministic sample index，并说明覆盖的边界。
- `not_applicable`：说明该边界为何不适用于当前 case 或当前输入合同。

边界类别固定为：

- `empty`
- `single`
- `duplicate`
- `zero_or_negative`
- `extreme`
- `no_solution`
- `multiple_solutions`

检查脚本输出：

- `output/boundary_cases/boundary_cases.json`
- `output/boundary_cases/boundary_cases.md`

报告会按 case 和 family 汇总 covered / not applicable / missing categories。缺失边界不会阻塞 expansion 层继续扩样例，但会让 `strong` 的 `family_core` case 出现在 `strong_upgrade_blocked_cases` 中，阻塞 strong 等级升级。

## 2.4 演示正确性

演示正确性不是视觉 polish。它检查 trace 是否足够支撑教学页面，且不会误导学习者。

最低检查：

- 关键帧有 `op`、`targets`、`state`、`reason`。
- 状态转移有 `deps` 或明确的 before/after。
- 关键阶段没有缺失：初始化、主循环、关键转移/访问、答案。
- 解释与算法族不矛盾。
- 当前帧能回答“做什么、为什么、依赖谁、状态怎么变”。

建议失败类型：

- `demo_missing_reason`
- `demo_missing_deps`
- `demo_missing_state`
- `demo_state_jump`
- `demo_algorithm_mismatch`
- `demo_key_step_missing`

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
- `bfs`：强校验，无权图 BFS 距离不变量，并覆盖 DFS、连通分量、拓扑排序、二分图染色等基础图 `graph_contract` 子模式。
- `shortest_path_mst`：强校验，覆盖 Dijkstra、Bellman-Ford、Floyd-Warshall、0-1 BFS relax 和 Kruskal MST 选边 / union-find 不变量。
- `binary_search`：强校验，搜索窗口边界不变量。
- `monotonic_stack`：强校验，单调栈结构不变量。
- `hash`：强校验，覆盖 Two Sum 的 map 写入顺序、complement 命中前后关系和答案依赖。
- `sorting`：强校验，覆盖插入排序的有序前缀、输入多重集保持和最终升序。
- `linked_list`：强校验，覆盖链表 `family_contract`、current/prev/next 指针证据和 next 指针重连连续性。
- `greedy`：强校验，覆盖跳跃游戏 reach 局部最优更新和不可达下标判定。
- `range_structure`：强校验，覆盖线段树节点 meta、树状数组 bit 和稀疏表 st 的 query/update 路径与表值。
- `geometry`：强校验，覆盖凸包点引用和 hull 一致转向；扫描线与线段相交子模式后续扩展。
- `math_bit`：强校验，覆盖 Euclid 余数、快速幂平方表、筛法布尔表、组合数表、bitmask 和 lowbit。
- `advanced_graph`：强校验，覆盖 Tarjan dfn/low、割点桥、二分图匹配和 Edmonds-Karp flow/capacity 不变量。
- `tree`：强校验入口覆盖 BST / LCA；普通树遍历没有匹配信号时仍按基础门禁处理。
- `union_find`：强校验，并查集 parent forest 不变量。

未知算法族必须返回 `process_uncovered` 降级画像，不能标记为 `strong`，也不能在没有族级 invariant 的情况下假装通过强校验。过程错误消息进入 benchmark 时会映射到 `process_invariant`、`coverage_error`、`process_fallback` 或 `process_uncovered` 等类型。

## 7.2 算法族能力注册表

算法族能力由独立文件 `benchmark/family_capabilities.json` 声明，不能只从 `process_validator.py` 反向推断。注册表中的 `label` 必须与 `tests/benchmark_cases.py` 中的 `BenchmarkCase.family` 完全一致；`process_profile` 必须映射到已注册 profile，或显式写为 `uncovered` 并说明 fallback 边界。

当前 deterministic benchmark 注册族名：

- `一维 DP`
- `二维 DP`
- `DP 核心扩展`
- `二分`
- `BFS/DFS 基础图`
- `最短路 / MST`
- `字符串高级算法`
- `哈希表 / map`
- `栈 / 队列 / 单调栈`
- `排序`
- `链表与缓存`
- `贪心`
- `树 / BST / LCA`
- `树形 DP`
- `堆 / TopK / Huffman`
- `Trie`
- `并查集`
- `回溯 / 递归`
- `几何 / 扫描线`
- `区间结构`
- `数学与位运算`
- `图高级`

注册表一致性检查：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_capabilities.py
```

## 7.3 分层算法族发布门禁

V1 发布门禁仍由 `scripts/check_v1_release_gate.py` 维护，不改变既有 V1 deterministic 结论。V1.1 起新增独立 family release gate，用同一批 deterministic benchmark case 生成算法族级报告：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/release_gate
```

输出：

- `output/release_gate/family_release_gate.json`
- `output/release_gate/family_release_gate.md`

报告按 family 汇总：

- case 数和 sample 数。
- gate layer 的 case 数和 sample 数。
- answer pass：脚本实际执行 `solve`、`trace`、`verify`，并与 expected 比较。
- process pass：脚本实际对 trace 运行 `validate_process`。
- demo readiness：基于 `demo_required` 和 expected layouts 的确定性演示就绪统计。
- `process_fallback` / `process_uncovered` case 与 sample 数。

门禁规则：

- `current_level=strong` 的算法族如果使用 `process_fallback` 或 `process_uncovered`，family gate 必须失败。
- `medium_plus`、`medium`、`basic` 算法族可以 fallback 或 uncovered，但报告必须显式列出 failure type、case 数、sample 数和 fallback 边界。
- family gate 嵌入 V1 release gate 的结论作为证据，但不修改 V1 gate 的含义。

## 7.4 降级策略统计

复杂变体不能强校验时，系统必须显式降级，不能把基础可运行误报为强过程正确。降级不等于放宽 release gate；它是 artifact、Debug Drawer 和 evaluation report 中的结构化证据。

固定降级类型：

- `answer_only`：只有 expected、verifier 或答案侧证据可靠，过程 / scene 还不能发布为精确演示。
- `schema_scene_only`：SemanticTrace 和 SceneGraph 可用，但缺少 expected、verifier 或多解法交叉校验。
- `process_fallback`：有基础过程证据，但当前算法族没有可复用 invariant。
- `process_uncovered`：算法族未覆盖，不能标记为 strong。
- `demo_warn`：页面可演示，但缺少部分教学字段或存在 demo readiness warning。

输出位置：

- `BuildArtifact.validation.degradations`：写入当前 artifact 的降级类型、原因、来源和 affected variant；稳定 HTML 的 Debug Drawer 会显示这些条目，raw validation JSON 也保留完整字段。
- `output/release_gate/family_release_gate.json`：`summary.degradation_summary` 按 family capability registry 统计 process fallback / uncovered 的 case 与 sample 数。
- `output/evaluation/evaluation_report.json`：`degradation_summary` 同时聚合 LLM benchmark result 和 family release gate；`evaluation_degradations.csv` 输出按 source 与 degradation type 拆分的计数。

门禁规则保持不变：

- strong family 的 `smoke` / `family_core` 不允许 `process_fallback` 或 `process_uncovered`。
- `medium_plus`、`medium`、`basic` 可以降级，但必须在 report 中显示原因和 fallback boundary。
- 降级证据不得替代 process validator，也不得让 renderer 直接消费 LLM HTML。

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

当前宿主机 glibc 过旧，不能直接运行 Playwright 自带 node。浏览器 smoke 和合并前完整质量检查应在 Playwright 兼容容器中运行：

```bash
bash scripts/run_browser_smoke_container.sh
bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py
```

宿主机仍用于非浏览器分层验证，例如 offline regression、benchmark regression、family release gate。容器脚本默认使用当前机器已缓存的 `iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest`，并以宿主机 UID/GID 写入仓库，避免 root-owned 输出产物。外部 CI 可通过 `ALGOLAB_PLAYWRIGHT_IMAGE` 覆盖镜像。

容器命令要求能访问 Docker daemon。脚本会优先使用普通 `docker`，失败后自动尝试 `sudo -n docker`；若两者都不可用，应在有 Docker 权限的 CI 或容器宿主机上运行 browser gate。

LLM benchmark 单独运行，模型配置通过环境变量或本地 ignored settings 文件提供，输出模型配置、repair 轮次和失败分类：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py --output-dir output/llm_benchmark --condition algolab_full
```

P15.1 之后，LLM benchmark 使用 `benchmark/llm_family_sets.json` 做 family / subfamily 分层抽样。该配置覆盖当前 deterministic benchmark 的所有 `family_id`，并把每个 case 的 sample 0 标记为 `seen_style`，sample 1 及之后样例标记为 `unseen_style`，用于在真实 LLM 路径中观察模型对同族不同输入风格的泛化表现。常用过滤参数：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py \
  --output-dir output/llm_benchmark \
  --condition algolab_full \
  --family array_pointer \
  --gate-layer family_core \
  --limit-per-family 1
```

输出除原有 `llm_benchmark_report.json` / `.md` 外，还包含：

- `output/llm_benchmark/family_summary.json`：按 family 统计生成成功率、repair 成功率、失败类型、subfamily、gate layer 和 seen / unseen style 分布。

LLM benchmark 失败不影响 deterministic release gate；它只影响真实产品能力评分和论文实验中的模型生成能力统计。

P15.2 之后，repair context 会保留原始 `failure_type`，并额外暴露 `repair_category`、`family`、`family_guidance` 和禁止动作。repair prompt 必须区分答案错误、trace schema、trace 跳步、target / deps、process invariant、coverage 和 demo readiness，不允许要求 LLM 直接修改 HTML。

P15.3 之后，LLM benchmark 额外支持独立 unseen family case set：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py \
  --output-dir output/llm_benchmark_unseen \
  --condition algolab_full \
  --case-set unseen \
  --limit-per-family 1
```

unseen registry 位于 `benchmark/unseen_family_cases.json`，只包含题目描述、family / subfamily 元数据、样例输入和 expected output，不包含 deterministic `code`、`tracker_code` 或 `verifier_code`。运行时仍然必须通过 LLM 生成、repair、sandbox 执行、校验、SceneGraph compiler 和 renderer 链路，不能复用 deterministic tracker。LLM report 和 evaluation report 会输出 `case_set`、`case_style`、`case_set_summary` / `case_style_summary` 以及 `evaluation_case_styles.csv`，用于区分 `seen_style` 和 `unseen_style`。

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
- `output/llm_benchmark/family_summary.json`
- `output/evaluation/evaluation_case_styles.csv`

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

- V1 baseline deterministic samples（`smoke` / `family_core`）必须位于 80 到 220；`expansion` 层样例通过 family release gate 单独报告。
- `unique_paths`、`graph_bfs`、`binary_search`、`daily_temperatures` 必须进入 browser smoke。
- Debug Drawer 必须能展开查看 raw validation、release gate、raw state 和 artifact。
- evaluation report 必须能输出失败分类 CSV。
- 文档中的 Python 命令必须使用 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3`。
