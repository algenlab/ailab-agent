# AlgoLearnEnv-Bench 数据集扩充记录

本文档记录早期数据集扩充过程和阶段规模；当前 benchmark 规模与实验分母见 `benchmark/README.md` 和 `docs/EXPERIMENT_RESULTS.md`。

生成日期：2026-07-04

## 1. 扩充目标

本轮按 `plan.md` 的 AlgoLearnEnv-Bench 方向扩充数据集：任务不只包含题面和 expected answer，还要能支持可执行、可验证、可交互的算法学习环境评估。

`plan.md` 的长期目标是 200-500 个算法学习环境任务。本轮完成的是第一批公开友好的 synthetic/open-source-style 扩充：新增 30 个 deterministic `BenchmarkCase`，每题 3 个样例，共 90 个新样例。扩充后：

- deterministic benchmark：101 cases / 349 samples。
- evaluation manifest：103 cases / 351 samples，其中包含 2 个 ML demo fixture。
- public synthetic 新增分层：30 cases / 90 samples。

## 2. 实现位置

- 新增数据集模块：`benchmark/families/algo_learn_env_expansion.py`
- 汇总入口：`benchmark/cases.py`
- LLM family split：`benchmark/llm_family_sets.json`
- Manifest schema：`scripts/build_evaluation_manifest.py`
- 生成结果：`output/experiments/dataset_expansion_20260704/`

## 3. 新增任务覆盖

| family_id | 新增数 | 新增任务 |
|---|---:|---|
| array_pointer | 3 | rotate array, move zeroes, fixed window max sum |
| binary_search | 2 | lower bound, mountain peak |
| hash_map | 3 | first unique char, group anagrams, unique intersection |
| monotonic_stack | 3 | valid parentheses, next greater, stock span |
| sorting | 3 | merge sort, quickselect, counting sort |
| basic_graph | 4 | grid BFS, islands, course schedule, unweighted distances |
| dp_1d | 2 | climbing stairs, min cost climbing |
| dp_2d | 1 | grid min path sum |
| dp_core | 2 | coin change minimum coins, LIS length |
| tree_bst_lca | 3 | level order, BST validation, BST insertion |
| heap_topk_huffman | 2 | Huffman merge cost, k-way merge |
| union_find | 1 | redundant connection |
| greedy | 1 | interval scheduling |

这批任务覆盖了 `plan.md` 点名的 Array / Two pointers、Stack、Graph、DP、Tree、Hash table、Sorting/Search，并补充 Heap、Union-Find、Greedy。

## 4. Task Bundle 字段

新增 case 已在 metadata 中补齐 plan 要求的任务包字段：

| 字段 | 当前落地 |
|---|---|
| `algorithm_id` | 默认等于 case id |
| `family` / `family_id` | 复用现有 family registry |
| `difficulty` | easy / medium |
| `learning_objectives` | 每题 3 个学习目标 |
| `input_generator` | synthetic fixed samples with edge cases |
| `reference_solver` | `verifier_code.verify` |
| `trace_oracle` | semantic trace schema + solve/trace/verifier 一致性 |
| `required_views` | 从 expected layouts 映射到 manifest |
| `interaction_tasks` | `predict_next_state`, `identify_active_invariant`, `modify_input_and_rerun` |
| `assessment_rubric` | 过程预测、不变量识别、输入修改后 oracle 一致性 |

此外，每个新增 tracker 都显式包含至少 4 个 trace events，其中 3 个带 `interaction`，满足“每题至少 3 个交互任务”的最低要求。

## 5. 当前分母变化

扩充前：

- deterministic benchmark：71 cases / 259 samples。
- expansion gate layer：9 cases / 37 samples。

扩充后：

- deterministic benchmark：101 cases / 349 samples。
- expansion gate layer：39 cases / 127 samples。
- public synthetic：30 cases / 90 samples。

Manifest summary 路径：

- JSON：`output/experiments/dataset_expansion_20260704/evaluation_manifest.json`
- cases CSV：`output/experiments/dataset_expansion_20260704/evaluation_cases.csv`
- samples CSV：`output/experiments/dataset_expansion_20260704/evaluation_samples.csv`

## 6. 验证口径

本轮新增任务已做新增样例级校验：

- solve result == expected。
- solve result == verifier result。
- trace result == solve result。
- trace schema 可由 `SemanticTrace` 校验。
- 每个新增 sample 的 trace 至少 4 帧。
- 每个新增 sample 的 interaction event 数不少于 3。

后续实验可以直接基于扩充后的 manifest 做：

1. 重新抽样运行 LLM benchmark。
2. 对 public synthetic 子集单独报告 pass rate。
3. 在 direct HTML baseline 中加入同样的 30 个任务，比较共同可观测指标。

## 7. 未完成边界

本轮没有声称完成 `plan.md` 的 200-500 全量 benchmark；这是第一批可运行扩充。下一批建议优先补：

- 更多 hard difficulty：advanced DP、graph flow、string automata。
- 每个 case 的固定随机 input generator。
- 更细粒度 trace oracle：逐步状态等价，而不只是 solve/trace/verifier 结果一致。
- 与 direct HTML baseline 共享的 hidden expected 评估集。
