# 真实题型 Benchmark

目标：验证系统骨架和 LLM 生成链路能稳定处理真实算法题，而不是只验证手写视觉 fixture。

## Deterministic Benchmark

这层不调用 LLM，用于本地稳定回归。每个 case 都提供：

- 题目与输入契约
- 多组输入与 expected output
- 可执行 `solve(input_data)`
- 可执行 `trace(input_data)`
- 独立 `verify(input_data)`
- 期望视觉 layout

每组输入都会经过：

`ProblemInput -> _try_materialize -> solve -> trace -> verifier/expected -> trace validator -> scene compiler -> scene validator -> release gate`

## 当前覆盖

| 题目 | 算法族 | 输入组数 | 视觉形态 |
|---|---|---:|---|
| 打家劫舍 | 一维 DP | 3 | array |
| 二分查找 | 二分 | 3 | array + pointer |
| 不同路径 | 二维 DP | 3 | matrix |
| 图 BFS 最短层数 | BFS/DFS 基础图 | 2 | graph + queue |
| KMP 字符串匹配 | 字符串高级算法 | 3 | string + array |
| 两数之和 | 哈希表 / map | 3 | array + map |
| 每日温度 | 栈 / 队列 / 单调栈 | 3 | array + stack |
| 插入排序 | 排序 | 3 | array |
| 二叉树最近公共祖先 | 树 / BST / LCA | 2 | tree |
| 数组中的第 K 个最大元素 | 堆 / TopK / Huffman | 2 | array + heap |
| Trie 前缀计数 | Trie | 2 | trie |
| 省份数量 | 并查集 | 2 | matrix + union_find |
| 全排列 | 回溯 / 递归 | 2 | array + recursion_tree |
| 凸包 | 几何 / 扫描线 | 2 | geometry |

当前 deterministic benchmark 共 14 个真实题型、35 组输入。

## 输出产物

- `output/algolab_benchmark_coverage.html`
- `output/algolab_benchmark_coverage.json`
- `output/algolab_benchmark_coverage.png`

## 质量检查

- `python -m tests.benchmark_regression`
- `python scripts/run_quality_checks.py`

## 边界

这层 benchmark 证明的是 deterministic pipeline 的稳定性，不证明 LLM 对任意题都能一次生成合格 trace。
## LLM Benchmark

这层调用真实 LLM 生成，不使用缓存，产物必须来自当前模型输出。

运行：

```bash
python scripts/run_llm_benchmark.py
```

默认每道题只跑第一个输入、每题生成 1 个解法，单样例 timeout 为 1200 秒。跑全部输入：

```bash
python scripts/run_llm_benchmark.py --all-samples
```

需要评估多解法生成：

```bash
python scripts/run_llm_benchmark.py --solutions 2
```

只跑单题：

```bash
python scripts/run_llm_benchmark.py --case binary_search
```

只跑某个输入：

```bash
python scripts/run_llm_benchmark.py --case binary_search --sample 1
```

对本次通过的 HTML 产物做浏览器 smoke：

```bash
python scripts/run_llm_benchmark.py --case binary_search --sample 1 --browser-smoke
```

每个样例结束后，runner 默认立即刷新报告，避免长 benchmark 中途失败时丢失已经完成的结果。需要关闭时：

```bash
python scripts/run_llm_benchmark.py --no-write-each
```

输出：

- `output/llm_benchmark/llm_<case_id>_<sample_index>.html`
- `output/llm_benchmark/llm_<case_id>_<sample_index>.json`
- `output/llm_benchmark/llm_benchmark_report.json`
- `output/llm_benchmark/llm_benchmark_report.md`

报告包含：

- 本次运行配置
- 当前模型名
- 开始/结束时间
- 平均耗时 `avg_duration_s`
- 每个样例的 `phase_timings` 和 `last_phase`
- 阶段耗时汇总 `phase_summary`
- 通过率
- 失败分类：`timeout`、`visual_warning`、`process_invariant`、`visual_scene`、`correctness`、`execution`、`trace_schema`、`browser`、`generation`
- 可选浏览器 smoke 结果

LLM benchmark 每个样例都会走：

`ProblemInput -> build_artifact -> generate_solution_spec -> _try_materialize -> repair_solution_spec -> release gate -> renderer`

当前阶段名：

- `generate`：首次 LLM 生成 JSON。
- `materialize_round_n`：执行 solve/trace/verifier、trace/process/scene 校验。
- `repair_round_n`：LLM 修复上一轮 JSON。
- `render`：导出 HTML/JSON。

它复用同一组题目、输入和 expected，但不会复用 deterministic benchmark 里的手写 `solve/trace/verifier`。

默认 LLM benchmark 开启严格 warning 模式：只要结果正确但视觉 target 不可渲染，也会判失败。
当前兼容的常见 LLM target 写法包括：

- map 项：`dist:B` 和 `dist[B]`
- 字符串/数组切片：`text[2:5]`
- 标量 target：自动 materialize 为 label
- 机械 step 编号错误：执行器会按事件顺序归一化

最近一次默认 LLM 运行结果：

- 命令：`python scripts/run_llm_benchmark.py --timeout-s 420`
- 结果：5/5 PASS
- 缓存：未使用
- warning：0
- report：`output/llm_benchmark/llm_benchmark_report.json`

注意：这条历史结果来自扩充到 14 题之前。扩充后应优先跑小批量抽样，例如：

```bash
python scripts/run_llm_benchmark.py --case two_sum --case daily_temperatures --case kth_largest --timeout-s 420
```

再跑全量首样本：

```bash
python scripts/run_llm_benchmark.py --timeout-s 420
```

## 边界

Deterministic benchmark 证明 pipeline 稳定性。LLM benchmark 证明当前模型在这些题型上的实时生成成功率。
两者都不是“任意算法 100% 正确”的证明；后续需要扩大题库、记录失败原因、加入截图评分和多轮统计。
