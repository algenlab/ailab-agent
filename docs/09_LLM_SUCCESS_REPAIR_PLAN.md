# LLM 成功率修复包、失败归因与执行计划

本文档保留早期 69-case 修复阶段的历史记录；当前 full-200、跨模型和最终质量结果统一见 `docs/EXPERIMENT_RESULTS.md`。

本文档是 `docs/08_AAAI_EXPERIMENT_PLAN.md` 之后的下一轮执行计划。目标不是继续扩大 benchmark，而是在不放宽实验口径的前提下，把真实 LLM `algolab_full` 在固定 69 个 deterministic case 上的严格发布成功率尽可能拉到 100%。

当时阶段结论：

- `algolab_full` 当前为 27 / 69，`pass_rate=0.391304347826087`。
- `direct_html_baseline` 当前为 63 / 69，`pass_rate=0.9130434782608695`，但该通过率主要表示直接 HTML 能通过 browser smoke，不等价于 answer / process / demo / SceneGraph release gate。
- `no_process_validator` 当前为 40 / 69，`pass_rate=0.5797101449275363`，说明去掉过程校验会放出更多页面，但其中包含真实过程缺陷，不能作为主系统目标。
- 下一轮优化必须区分三类问题：真实算法或 trace 错、validator / compiler 接受范围过窄、LLM 生成和 repair 没对齐 trace 合同。

## 1. 执行原则

执行 AI 必须遵守：

- 每轮只执行本文档中最靠前的 `状态：待执行。` 阶段。
- 阶段完成后，把该阶段状态改为 `状态：已完成。`，并补充完成证据。
- 如果阶段因为环境、模型服务或不可复现问题无法继续，把状态改为 `状态：阻塞。`，写明阻塞命令、错误和恢复条件。
- 不要做 Git，不提交不推送。
- Python 固定使用 `python3`。
- 浏览器命令固定走 `bash scripts/run_browser_smoke_container.sh`。
- 可以修可复现 bug，但必须最小修复、加 regression 测试、复跑失败命令。

禁止：

- 修改 benchmark expected output。
- 删除、跳过或隐藏失败 case。
- 关闭 process validator、demo readiness、SceneGraph validator 或 browser smoke 来提高通过率。
- 把 `--condition direct_html_baseline` 或 `--condition no_process_validator` 的结果冒充 `algolab_full`。
- 把 VLM 分数当作机器 gate 通过证据。
- 为追求 100% 把真实算法错误改成 warning。
- 对所有 family 做全局宽松放行；只允许在有正反例测试证明时做 submode-specific 的接受范围修正。

允许：

- 强化 prompt、repair context 和 family guidance。
- 修复 failure type 分类不准的问题。
- 修复 SceneGraph compiler / scene validator 的对象绑定 bug。
- 修复 process validator 过泛化或过窄的 family / submode 规则。
- 增加针对失败模式的 regression 测试。
- 增加失败归因脚本和 report。

## 2. 成功定义

### 2.1 主目标

固定 deterministic 69 case 上：

```text
condition=algolab_full
case_set=deterministic
total=69
passed=69
failed=0
pass_rate=1.0
browser_total=69
browser_ok=69
browser_failed=0
```

该目标必须通过完整主 pipeline：

```text
LLM generate / repair
  -> sandbox execute solve / trace / verifier
  -> answer / expected / verifier consistency
  -> trace schema
  -> process validator
  -> demo readiness
  -> SceneGraph compiler
  -> scene validator
  -> HTML renderer
  -> browser smoke
```

### 2.2 论文对 baseline 的目标口径

不能用一个混合 `pass_rate` 直接说超过 baseline。最终报告至少拆成三种口径：

| 口径 | AlgoLab full | direct HTML baseline | 目标 |
|---|---:|---:|---|
| 严格机器 release gate | 当前 27 / 69 | 不具备同等 gate | AlgoLab 证明可验证正确性 |
| browser smoke coverage | 当前 27 / 69 成功产物均 ok | 当前 63 / 69 | R7 后按用户确认的 66 / 69 收口 |
| 成功页面 VLM 教学质量 | 当前 overall 4.7037 | 当前 overall 4.8889 | 后续再优化 AlgoLab 成功页展示 |

本文档只处理第一轮：严格 LLM 端到端成功率。

## 3. 当前失败归因

规划 AI 基于 `output/aaai_llm_algolab_full/llm_benchmark_report.json` 对 42 个失败做了根因重分类。该分类用于指导修复优先级，不替代执行 AI 后续脚本化归因。

| 根因类别 | 数量 | 代表 case | 判断 |
|---|---:|---|---|
| `missing_key_events_or_coverage` | 11 | `dijkstra_shortest_path`、`kruskal_mst_weight`、`tarjan_scc`、`edmonds_karp_expansion` | 多数是真 trace 缺关键教学/过程事件，不能简单放宽 |
| `legacy_schema_or_target_format` | 9 | `binary_answer_sqrt`、`unique_paths`、`graph_topological_sort`、`binary_tree_inorder`、`fast_power_mod` | 不是 invariant 太严，是 LLM / repair 没遵守新 SemanticTrace 合同 |
| `missing_evidence_or_deps` | 6 | `graph_dfs_traversal`、`graph_bipartite_coloring`、`tree_diameter`、`reverse_linked_list_expansion` | 可通过 prompt / repair 补 deps、value、state；少数规则可更灵活 |
| `actual_algorithm_state_mismatch` | 5 | `complete_knapsack_coin_change`、`trie_prefix`、`sparse_table_range_min`、`jump_game_expansion`、`edmonds_karp` | 真算法或 trace 状态错误，必须修生成，不允许放宽 |
| `runtime_api_or_generated_code_error` | 4 | `two_pointer_pair_sum`、`zero_one_bfs_shortest_path`、`lca`、`permutations_expansion` | 生成代码/API 调用错，和 invariant 严格性无关 |
| `scene_object_binding_warning` | 3 | `bellman_ford_shortest_path`、`reverse_linked_list`、`bipartite_matching` | 可能是 SceneGraph 对 edge/node 绑定口径不一致，应优先查 compiler/validator |
| `string_contract_overgeneralized` | 3 | `rabin_karp`、`manacher`、`z_algorithm` | 很可能是 string family contract 过泛化，需要按 submode 细化 |
| `unknown` | 1 | `daily_temperatures` | 单调栈 pop 后答案贡献写入缺失，偏 demo / trace coverage |

按 family 聚合：

| family | 失败数 | 主要根因 |
|---|---:|---|
| 最短路 / MST | 6 | 缺 relax / union_find / scene edge / 0-1 BFS runtime |
| 图高级 | 5 | Tarjan / flow / scene edge / legacy schema |
| BFS/DFS 基础图 | 4 | legacy schema、缺 deps |
| 字符串高级算法 | 4 | string contract 过泛化、Trie prefix 证据缺失 |
| DP 核心扩展 | 3 | 完全背包转移错、状态压缩/数位 DP coverage |
| 树 / BST / LCA | 3 | legacy schema、Tracer API 错、树递归证据缺失 |
| 区间结构 | 3 | legacy schema、递归 frame 缺失、稀疏表状态错 |
| 其他 family | 14 | 分散在 array、Trie、链表、回溯、几何、数学、贪心、单调栈 |

## 4. 修复策略

优先级固定为：

1. 先修不伤正确性的系统性问题：schema / target / Tracer API / repair 分类。
2. 再修明确过泛化的 validator：字符串 submode、SceneGraph edge/node 绑定。
3. 再修 family-specific 关键事件生成：图、DP、Trie、回溯、网络流。
4. 最后处理真实算法状态错误：背包、稀疏表、Trie 计数、跳跃游戏、网络流守恒。

任何 validator 调整都必须同时满足：

- deterministic family release gate 仍为 69 cases / 250 samples，全通过。
- 对应 family 的负例测试仍失败。
- 调整是 submode-specific，不是全局跳过 process invariant。
- 调整后的 LLM 失败如果仍是真过程错误，必须保留 `process_invariant` 或更具体 failure type。

## 5. 推荐指标看板

执行 AI 每个阶段结束后都要更新以下指标：

| 指标 | 当前值 | 阶段目标 |
|---|---:|---:|
| `algolab_full.pass_rate` | 27 / 69 = 39.13% | 每阶段至少净增 3 个通过，除非阶段是纯归因或阻塞 |
| `legacy_schema_or_target_format` | 9 | R1 后降到 2 以下 |
| `runtime_api_or_generated_code_error` | 4 | R1 后降到 1 以下 |
| `string_contract_overgeneralized` | 3 | R2 后降到 0 |
| `scene_object_binding_warning` | 3 | R3 后降到 0 |
| `missing_key_events_or_coverage` | 11 | R4 / R5 后逐步降到 3 以下 |
| `actual_algorithm_state_mismatch` | 5 | R6 后降到 0 |
| `browser_smoke_failed_for_passed_html` | 0 | 始终保持 0 |

## 6. 通用验收命令

非浏览器测试：

```bash
python3 -m tests.benchmark_regression
python3 -m tests.offline_regression
python3 scripts/check_family_release_gate.py --output-dir output/repair_release_gate
```

浏览器完整质量检查：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_quality_checks.py
```

单 case live LLM 复跑模板：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_llm_smoke \
  --condition algolab_full \
  --case CASE_ID \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 1
```

全量 live LLM 复跑模板：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_llm_algolab_full \
  --condition algolab_full \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 2
```

全量报告验收脚本：

```bash
python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("output/repair_llm_algolab_full/llm_benchmark_report.json").read_text(encoding="utf-8"))
assert report["total"] == 69
assert all((item.get("ok") or item.get("failure_type")) for item in report["results"])
print("total", report["total"])
print("passed", report["passed"])
print("failed", report["failed"])
print("pass_rate", report["pass_rate"])
print("failure_summary", report.get("failure_summary"))
print("model_usage", report.get("model_usage"))
browser = report.get("browser_smoke") or []
print("browser_total", len(browser))
print("browser_ok", sum(1 for item in browser if item.get("ok")))
PY
```

## 7. 执行阶段

### R1 schema / target / Tracer API 修复包

状态：已完成。

目标：

- 修复 `legacy_schema_or_target_format` 和 `runtime_api_or_generated_code_error` 两类高收益问题。
- 不修改 validator 放行逻辑。
- 让 repair 更稳定地把旧式 `type/target`、裸字符串 target、缺 `input_data`、错误 `Tracer()` 调用、错误 `tracer.choose()` 这类问题转回 Tracer API。

当前目标 case：

- `binary_answer_sqrt`
- `unique_paths`
- `graph_connected_components`
- `graph_topological_sort`
- `binary_tree_inorder`
- `convex_hull`
- `fenwick_tree_prefix_sum`
- `fast_power_mod`
- `articulation_bridges`
- `two_pointer_pair_sum`
- `zero_one_bfs_shortest_path`
- `lca`
- `permutations_expansion`

建议修改文件：

- `algolab/generation/prompts/tracker_system.txt`
  - 进一步强调所有 tracker 必须使用 `Tracer(input_data, ...)`，禁止直接手写 `events.append`。
  - 对旧字段错误给出更短、更强的负例：禁止 `type`、`target`、裸字符串 targets、缺 `input_data`。
  - 明确不存在 `tracer.choose()`，回溯选择必须用 `tracer.push()`、`tracer.mark()`、`tracer.enter()`。
- `algolab/generation/prompts/repair_system.txt`
  - 当错误出现 Pydantic `Field required`、`model_type`、`extra_forbidden` 时，要求整体重写 tracker 为 Tracer API。
  - 当错误出现 `Tracer.__init__()` 时，必须改为 `Tracer(input_data, algorithm=..., pseudocode=...)`。
  - 当错误出现 `object has no attribute 'choose'` 时，必须用现有 op 表达 choose / undo。
- `algolab/verification/repair_context.py`
  - 把 Pydantic `model_type`、`extra_forbidden`、`Input should be a valid dictionary or instance of TargetRef` 稳定归类为 `schema_error` 或 `target_error`。
  - 把 `Tracer.__init__`、`object has no attribute 'choose'`、`unhashable type: 'list'` 稳定归类为 `execution_error`。
  - 对 `trace_schema` 和 `execution` 增加更具体的 `repair_instruction`。
- `algolab/generation/repair.py`
  - 如果 repair context 中包含 `trace_schema` 或 `target_or_deps`，在 prompt 中追加一个短 checklist：`Tracer(input_data)`、`op/targets`、`deps` 为 `{"id": ...}` 由 Tracer 自动生成、不要手写旧 events。

建议新增测试：

- `tests/regression/repair_prompt_contracts.py`

测试必须覆盖：

- 旧字段 `type/target` 错误会进入 `trace_schema` / `target_or_deps` 修复分类。
- 裸字符串 targets 的 Pydantic `model_type` 错误会进入 schema / target 分类。
- `Tracer.__init__() missing 1 required positional argument: 'input_data'` 会进入 execution 分类。
- `Tracer object has no attribute choose` 的 repair prompt 包含 `push`、`mark`、`enter`、`exit`，且不包含要求使用 `choose()`。
- repair prompt 中明确禁止 HTML / CSS / JS。

阶段测试命令：

```bash
python3 -m tests.regression.repair_prompt_contracts
python3 -m tests.benchmark_regression
```

阶段 live smoke：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_r1_schema_smoke \
  --condition algolab_full \
  --case binary_answer_sqrt \
  --case unique_paths \
  --case graph_topological_sort \
  --case fast_power_mod \
  --case lca \
  --case permutations_expansion \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 1
```

验收：

- regression 测试通过。
- deterministic gate 不回退。
- smoke 中失败项如果仍失败，不能再出现旧字段 `type/target`、裸字符串 targets、缺 `input_data`、`Tracer.__init__` 或 `tracer.choose()`。
- 不允许通过关闭 strict warnings、process validator 或 demo readiness 来通过。

阶段完成证据必须记录：

- 修改文件。
- 新增测试。
- regression 测试结果。
- live smoke 的 total / passed / failed / failure_summary。
- 是否仍存在 schema / Tracer API 类错误。

完成证据（2026-05-31）：

- 修改文件：
  - `algolab/generation/prompts/tracker_system.txt`
  - `algolab/generation/prompts/repair_system.txt`
  - `algolab/generation/repair.py`
  - `algolab/verification/repair_context.py`
- 新增测试：
  - `tests/regression/repair_prompt_contracts.py`
- 修复内容：
  - Pydantic `Field required`、`model_type`、`extra_forbidden`、`TargetRef` 裸字符串 targets 稳定进入 `schema_error` / `target_error` 与 `trace_schema` / `target_or_deps` 修复分类。
  - `Tracer.__init__`、缺 `input_data`、`object has no attribute 'choose'`、`unhashable type: 'list'` 稳定进入 `execution_error`。
  - repair prompt 追加 R1 checklist：`Tracer(input_data)`、`op/targets`、`deps` 为 `{"id": ...}` 由 Tracer 生成、禁止旧 events / renderer 代码。
  - prompt 明确禁止 `tracer.choose()`，回溯选择用 `push` / `mark` / `enter`，撤销用 `pop` / `unmark` / `exit`。
  - 追加 map target 引号规则：使用 `indegree[A]`、`dist[B]`，不要使用 `indegree['A']`、`dist["B"]`。
- regression 测试结果：
  - `python3 -m tests.regression.repair_prompt_contracts`：PASS。
  - `python3 -m tests.benchmark_regression`：PASS。
- deterministic gate：
  - `python3 scripts/check_family_release_gate.py --output-dir output/repair_r1_release_gate`：`overall_ready=true`，`case_count=69`，`sample_count=250`，`answer_pass_rate=1.0`，`process_pass_rate=1.0`，`demo_readiness_pass_rate=1.0`。
- live smoke：
  - `output/repair_r1_schema_smoke2/llm_benchmark_report.json`：`total=6`，`passed=3`，`failed=3`，`pass_rate=0.5`，`failure_summary={"demo_state_jump": 1, "process_invariant": 2}`，`browser_total=3`，`browser_ok=3`。
  - 失败项为 `binary_answer_sqrt` 的二分 demo 比较证据跳变、`graph_topological_sort` 的拓扑入队原因缺失、`permutations_expansion` 的回溯 `recursion_tree/search_tree` 与 `record` 事件缺失。
  - 针对上一轮 `graph_topological_sort` 的 `indegree['A']` map target 失败，已补充引号规则并单独重跑到 `output/repair_r1_graph_topo_retry/llm_benchmark_report.json`；失败根因已变为 `Graph contract topological_sort 缺少 indegree 变化事件`。
- schema / Tracer API 类错误结论：
  - 当前 smoke 报告中未再出现旧字段 `type/target`、裸字符串 targets 的 Pydantic `model_type`、缺 `input_data`、`Tracer.__init__` 或 `tracer.choose()`。
  - 剩余失败属于 demo / graph / backtracking coverage，进入后续 R4 / R5 范围。

### R2 string family contract submode 修复包

状态：已完成。

目标：

- 消除 `string_contract_overgeneralized`。
- 保留 KMP、Rabin-Karp、Z Algorithm、Manacher、string sliding window、Trie prefix match 的强校验，但按 submode 接受不同结构。

当前目标 case：

- `rabin_karp`
- `manacher`
- `z_algorithm`

判断：

- Rabin-Karp 需要 `text`、`pattern`、`window_hash` / `window_hashes` / `pattern_hash`。
- Z Algorithm 对单串 `s` 或组合串可以不需要 `pattern[j]`，但必须有 `text` 或 `s`、`z` 表、扩展/回退原因和字符 target。
- Manacher 对单串 `s` 可以不需要 `pattern`，但必须有 `text`、`radius` / `p` 表、中心扩展状态和字符 target。

建议修改文件：

- `algolab/verification/process_families/contracts.py`
  - 将 `_validate_family_contract_string()` 拆成 submode-specific checks。
  - `kmp` 和 `rabin_karp` 可以要求 text/pattern pointer pair。
  - `z_algorithm` 和 `manacher` 不应强制 pattern pointer。
  - `trie_prefix_match` 不应走普通 text/pattern 表结构要求，应要求 trie / prefix_count / prefix path。
- `algolab/verification/process_families/string.py`
  - 保持 `_validate_rabin_karp_hashes()`、`_validate_z_algorithm()`、`_validate_manacher_radius()` 的算法值校验。
  - 如果 submode 缺失但算法名明显包含 z/manacher/rabin，可给出更具体错误，不要用泛化 `Family contract string 缺少表结构`。
- `algolab/generation/prompts/tracker_system.txt`
  - 为 Z Algorithm / Manacher 明确 family_contract 样例。
- `algolab/generation/prompts/repair_system.txt`
  - 对 `Family contract string 缺少 text/pattern 指针` 错误要求先判断 submode，不能机械添加不存在的 pattern。

建议新增或修改测试：

- 修改 `tests/regression/trace_contracts.py`，新增三个正例：
  - Z Algorithm 单串 trace：有 `family_contract={"family":"string","submode":"z_algorithm","expected_tables":["z"]}`，不提供 pattern，必须通过。
  - Manacher 单串 trace：有 `family_contract={"family":"string","submode":"manacher","expected_tables":["radius"]}`，不提供 pattern，必须通过。
  - Rabin-Karp trace：有 text / pattern / hash，必须通过。
- 新增三个负例：
  - Z Algorithm 缺 `z` 表必须失败。
  - Manacher 缺 radius / p 表必须失败。
  - Rabin-Karp 有 pattern 但 hash 错必须失败。

阶段测试命令：

```bash
python3 -m tests.regression.trace_contracts
python3 -m tests.benchmark_regression
python3 scripts/check_family_release_gate.py --output-dir output/repair_r2_release_gate
```

阶段 live smoke：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_r2_string_smoke \
  --condition algolab_full \
  --case rabin_karp \
  --case manacher \
  --case z_algorithm \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 1
```

验收：

- 三个 string case 若仍失败，不得再因为 `Family contract string 缺少 text/pattern 指针` 或泛化表结构错误失败。
- deterministic family release gate 仍为 69 cases / 250 samples，全通过。
- 负例仍能证明不是无条件放行。

完成证据（2026-05-31）：

- 修改文件：
  - `algolab/verification/process_families/contracts.py`
  - `algolab/verification/demo_readiness.py`
  - `algolab/generation/prompts/tracker_system.txt`
  - `algolab/generation/prompts/repair_system.txt`
  - `algolab/verification/repair_context.py`
  - `algolab/generation/repair.py`
- 修改测试：
  - `tests/regression/trace_contracts.py`
  - `tests/regression/reports_and_gates.py`
  - `tests/regression/repair_prompt_contracts.py`
  - `tests/benchmark_regression.py`
- 修复内容：
  - `_validate_family_contract_string()` 已拆分为 KMP、Rabin-Karp、Z Algorithm、Manacher、Trie prefix 和默认 string 合同。
  - `z_algorithm` / `manacher` 单串 trace 不再强制 `pattern` 指针；分别要求 `z`、`radius` / `p` 表、扩展原因和 `text[i]` / `s[i]` 字符 target。
  - `rabin_karp` 仍要求 text / pattern、`pattern_hash`、`window_hash` / `window_hashes` 和字符确认，hash 错误负例仍失败。
  - `trie_prefix_match` 不再走普通 text/pattern 表结构要求，改要求 trie / prefix / prefix_count / Trie 路径证据。
  - demo readiness 对 Z / Manacher / Rabin-Karp 输出 submode-specific 缺口；Rabin-Karp 的 `window_hash` / `window_hashes` 可作为窗口聚合状态。
  - prompt 增加 Rabin-Karp、Z Algorithm、Manacher 的 family_contract 样例；repair prompt 遇到 `Family contract string 缺少 text/pattern 指针` 时先判断 submode，不机械添加 pattern。
  - 额外补充 `Tracer.compare([...])` API repair 指令，修复 R2 live retry 中暴露的 `Tracer.compare() missing targets`。
- regression 测试结果：
  - `python3 -m tests.regression.trace_contracts`：PASS。
  - `python3 -m tests.regression.repair_prompt_contracts`：PASS。
  - `python3 -m tests.benchmark_regression`：PASS。
- deterministic gate：
  - `python3 scripts/check_family_release_gate.py --output-dir output/repair_r2_release_gate`：`overall_ready=true`，`case_count=69`，`sample_count=250`，`answer_pass_rate=1.0`，`process_pass_rate=1.0`，`demo_readiness_pass_rate=1.0`。
- live smoke：
  - `output/repair_r2_string_smoke2/llm_benchmark_report.json`：`total=3`，`passed=2`，`failed=1`，`pass_rate=0.6666666666666666`，`failure_summary={"generation": 1}`，`browser_total=2`，`browser_ok=2`。
  - `z_algorithm` 和 `manacher` 通过完整 algolab_full + browser smoke。
  - `rabin_karp` 在 smoke2 中失败为 `generation` / `target_error`，未出现 `Family contract string 缺少 text/pattern 指针` 或泛化表结构错误。
  - 针对 `rabin_karp` 的 `Tracer.compare()` API 问题补充 repair 指令后，单 case retry `output/repair_r2_rabin_retry2/llm_benchmark_report.json`：`total=1`，`passed=1`，`failed=0`，`pass_rate=1.0`，`browser_total=1`，`browser_ok=1`。
- R2 验收结论：
  - 当前 R2 smoke / retry 报告未再出现 `Family contract string 缺少 text/pattern 指针`、泛化 `Family contract string 缺少表结构` 或泛化 `字符串演示缺少表项、哈希、半径或前缀计数状态`。
  - 负例覆盖 Z 缺 `z`、Manacher 缺 `radius` / `p`、Rabin-Karp hash 错误，证明不是无条件放行。

### R3 SceneGraph edge / node 绑定修复包

状态：已完成。

目标：

- 消除已通过 process 但被 strict visual warning 拦住的 edge/node 绑定问题。
- 不降低 SceneGraph validator 对不存在对象的拦截能力。

当前目标 case：

- `bellman_ford_shortest_path`
- `reverse_linked_list`
- `bipartite_matching`

判断：

- 错误形态集中在 `edge source 不在对象集合：node:*` 和 `edge target 不在对象集合：node:*`。
- 如果 state 中有 graph / linked_list / tree / union_find / trie 等结构，SceneGraph compiler 应稳定生成对应 node 对象，edge 才能引用。
- 如果 edge 引用了不存在的 node，仍应失败。

建议修改文件：

- `algolab/compiler/scene_compiler.py`
  - 检查 graph / linked_list / bipartite graph / tree state 到 node object 的生成逻辑。
  - 对 `edge:A->B`、`edge:A-B`、linked list edge、bipartite left/right node 做统一 node id 归一。
- `algolab/compiler/target_parser.py`
  - 如果存在 edge 格式解析差异，只做兼容解析，不允许旧式 map target 复活。
- `algolab/verification/scene_validator.py`
  - 保持 strict warning，但错误消息要区分“compiler 未生成已有 state node”和“trace 真引用不存在 node”。

建议新增测试：

- `tests/regression/scene_edge_binding.py`

测试必须覆盖：

- graph state 有 `A -> B` 且 event 引用 `edge:A->B` 时，scene validator 不报 node 缺失。
- linked_list state 有 nodes / edges 且 event 引用 linked edge 时，scene validator 不报 node 缺失。
- bipartite matching state 有 left/right nodes 且 event 引用 edge 时，scene validator 不报 node 缺失。
- event 引用 state 中不存在的 `node:Z` 时仍然报错。

阶段测试命令：

```bash
python3 -m tests.regression.scene_edge_binding
python3 -m tests.benchmark_regression
bash scripts/run_browser_smoke_container.sh python3 scripts/run_quality_checks.py
```

阶段 live smoke：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_r3_scene_smoke \
  --condition algolab_full \
  --case bellman_ford_shortest_path \
  --case reverse_linked_list \
  --case bipartite_matching \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 1
```

验收：

- 目标 case 不再因 `edge source/target 不在对象集合` 失败。
- 如果目标 case 仍失败，failure type 应暴露新的真实根因。
- 完整质量检查通过。

完成证据（2026-05-31）：

- 修改文件：
  - `algolab/compiler/scene_compiler.py`
  - `algolab/compiler/target_parser.py`
  - `algolab/verification/scene_validator.py`
  - `algolab/verification/repair_context.py`
  - `algolab/generation/prompts/repair_system.txt`
- 新增 / 修改测试：
  - `tests/regression/scene_edge_binding.py`
  - `tests/regression/repair_prompt_contracts.py`
  - `tests/benchmark_regression.py`
- 修复内容：
  - `edge:A-B` 已按 edge target 解析，和 `edge:A->B` 统一生成 source / target。
  - SceneGraph compiler 对 graph dict、edge list / weighted edges、linked_list、bipartite left/right nodes 生成稳定 node / edge object。
  - Scene validator 增加 state-aware node id 提取；已有 state node 不再被误报为 scene object 缺失，同时 `node:Z` 这类不存在对象仍会报 warning。
  - repair context / repair prompt 增加 `Tracer.link() takes 2 positional arguments but 3 were given` 的 API 修复指令，要求使用 `deps=[...]` 关键字。
- regression 测试结果：
  - `python3 -m tests.regression.scene_edge_binding`：PASS。
  - `python3 -m tests.regression.repair_prompt_contracts`：PASS。
  - `python3 -m tests.benchmark_regression`：PASS。
  - `bash scripts/run_browser_smoke_container.sh python3 scripts/run_quality_checks.py`：`quality_checks: PASS`。
- live smoke：
  - `output/repair_r3_scene_smoke2/llm_benchmark_report.json`：`total=3`，`passed=2`，`failed=1`，`failure_summary={"execution": 1}`；`bellman_ford_shortest_path` 和 `reverse_linked_list` 通过，`bipartite_matching` 当时失败为 `Tracer.link() takes 2 positional arguments but 3 were given`。
  - `output/repair_r3_bellman_retry/llm_benchmark_report.json`：`total=1`，`passed=1`，`failed=0`。
  - 补充 `Tracer.link()` repair 指令后，`output/repair_r3_bipartite_retry/llm_benchmark_report.json`：`total=1`，`passed=0`，`failed=1`，`failure_summary={"process_invariant": 1}`；失败根因变为 `Graph contract 未支持的 submode：directed`。
- R3 验收结论：
  - 当前 R3 smoke / retry 报告未再出现 `edge source 不在对象集合` 或 `edge target 不在对象集合`。
  - 剩余 bipartite failure 已暴露为 graph contract submode / process invariant 问题，进入 R4 范围。

### R4 graph / shortest path / advanced graph 关键事件修复包

状态：已完成。

目标：

- 补齐图类 family 的关键过程事件，使 LLM repair 能生成 validator 接受的可教学 trace。
- 不放宽 Dijkstra、Kruskal、Tarjan、Edmonds-Karp 的核心不变量。

当前目标 case：

- `dijkstra_shortest_path`
- `dijkstra_shortest_path_expansion`
- `kruskal_mst_weight`
- `tarjan_scc`
- `edmonds_karp`
- `edmonds_karp_expansion`
- `graph_bipartite_coloring`
- `graph_dfs_traversal`
- `floyd_warshall_all_pairs`

建议修改文件：

- `algolab/verification/repair_context.py`
  - 将 graph guidance 从通用图提示拆成 submode guidance。
  - Dijkstra：必须记录 heap/frontier、每条关键 `edge:u->v` relax、`old_dist`、`new_dist`、parent。
  - Kruskal：必须记录 edge sorted order、选/弃原因、union_find parent/rank。
  - Tarjan：必须记录 dfn、low、stack/on_stack、low==dfn 时 component 弹栈。
  - Network flow：必须记录 augmenting_path、bottleneck、capacity/cap、flow 和每条增广边更新。
  - Floyd-Warshall：必须使用 DP set 事件记录 dist[i][j] 转移。
- `algolab/generation/prompts/tracker_system.txt`
  - 增加图 family 的短模板，不要长篇自然语言。
- `algolab/generation/prompts/repair_system.txt`
  - 对图类 `process_invariant` 明确禁止只改 final result，必须补关键事件。
- `algolab/verification/process_families/graph.py`
  - 只允许做诊断改善或 submode-specific 的合理接受范围修正。
  - 如果 validator 要求的信息在 prompt 中没有明确定义，先补 prompt 和 tests，再考虑调整 validator。
- `algolab/verification/process_families/tree_range_math.py`
  - Tarjan、bipartite matching、flow 相关校验如果错误信息过泛，增加具体 step / missing field。

建议新增测试：

- `tests/regression/graph_repair_guidance.py`

测试必须覆盖：

- `build_repair_context()` 对 Dijkstra 缺 relax 输出包含 `old_dist`、`new_dist`、`edge:u->v`。
- 对 Kruskal 缺 union-find 输出包含 `union_find`、`parent`、`rank` 或 `size`。
- 对 Tarjan 缺 component 弹栈输出包含 `dfn`、`low`、`stack`、`component`。
- 对 Edmonds-Karp 缺 flow/capacity 输出包含 `augmenting_path`、`bottleneck`、`flow`、`capacity`。

阶段测试命令：

```bash
python3 -m tests.regression.graph_repair_guidance
python3 -m tests.regression.trace_contracts
python3 -m tests.benchmark_regression
```

阶段 live smoke：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_r4_graph_smoke \
  --condition algolab_full \
  --case dijkstra_shortest_path \
  --case dijkstra_shortest_path_expansion \
  --case kruskal_mst_weight \
  --case tarjan_scc \
  --case edmonds_karp \
  --case edmonds_karp_expansion \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 1
```

验收：

- 目标 case 的失败不再是“缺 relax / 缺 union-find / 缺 component 弹栈 / 缺 flow/capacity 更新”。
- 如果仍失败，必须记录新的根因分类。
- 不允许删除 graph validator 的核心不变量。

完成证据（2026-05-31）：

- 修改文件：
  - `algolab/verification/repair_context.py`
  - `algolab/generation/prompts/tracker_system.txt`
  - `algolab/generation/prompts/repair_system.txt`
  - `algolab/compiler/scene_compiler.py`
  - `algolab/verification/scene_validator.py`
  - `algolab/verification/trace_validator.py`
- 新增 / 修改测试：
  - `tests/regression/graph_repair_guidance.py`
  - `tests/regression/scene_edge_binding.py`
  - `tests/benchmark_regression.py`
- 修复内容：
  - `build_repair_context()` 对 graph family 增加 submode-specific guidance：BFS/DFS、Dijkstra、Bellman-Ford、Floyd-Warshall、0-1 BFS、topological sort、Kruskal/MST、Tarjan、network flow。
  - Dijkstra guidance 明确 `heap/frontier`、`edge:u->v` relax、`old_dist`、`new_dist`、`edge_weight`、`parent/predecessor` 和 deps。
  - Kruskal guidance 明确 `sorted_edges` / `edge_order`、select/skip reason、`union_find.parent` 以及 `rank` 或 `size`。
  - Tarjan guidance 明确 `dfn`、`low`、`stack`、`on_stack`、`low==dfn` 时的 `component` 弹栈。
  - Network flow guidance 明确 `augmenting_path`、`bottleneck`、`capacity/cap`、`flow[u->v]` 更新、`cap[u->v]` deps；同时要求每个发布的 `state.flow` 满足中间节点流守恒，反向残量边放入 `residual` / `residual_capacity`，不写入 `flow`。
  - tracker / repair system prompt 增加图 submode 短模板和 graph `process_invariant` 修复规则；不放宽 graph validator。
  - 补充 `weighted_graph` 的 trace / SceneGraph 绑定：`input_data.weighted_graph` 可生成 node / edge object，weighted neighbor `["B", w]` 归一为 `node:B` / `edge:A->B`。
- regression 测试结果：
  - `python3 -m tests.regression.graph_repair_guidance`：PASS。
  - `python3 -m tests.regression.scene_edge_binding`：PASS。
  - `python3 -m tests.regression.trace_contracts`：PASS。
  - `python3 -m tests.regression.repair_prompt_contracts`：PASS。
  - `python3 -m tests.benchmark_regression`：PASS。
  - `bash scripts/run_browser_smoke_container.sh python3 scripts/run_quality_checks.py`：`quality_checks: PASS`。
- live smoke：
  - `output/repair_r4_graph_smoke2/llm_benchmark_report.json`：`total=6`，`passed=5`，`failed=1`，`pass_rate=0.8333333333333334`，`failure_summary={"process_invariant": 1}`。
  - smoke2 中 `dijkstra_shortest_path`、`dijkstra_shortest_path_expansion`、`kruskal_mst_weight`、`tarjan_scc`、`edmonds_karp_expansion` 通过；唯一失败为 `edmonds_karp` 缺 `flow/capacity` 更新事件。
  - 针对 `dijkstra_shortest_path_expansion` 的 weighted graph 绑定问题，单 case retry `output/repair_r4_dijkstra_expansion_retry/llm_benchmark_report.json`：`total=1`，`passed=1`，`failed=0`。
  - 针对 `edmonds_karp` 的 network flow guidance 逐步补充后，最终单 case retry `output/repair_r4_edmonds_retry4/llm_benchmark_report.json`：`total=1`，`passed=1`，`failed=0`。
  - 中间 retry 暴露并已修复的 prompt 合同缺口：`before 与上一状态不一致`、中间节点 `flow` 不守恒、反向残量边被写入 `flow` 导致负流量。
- R4 验收结论：
  - 最新 full smoke2 加 targeted retry 中，目标 case 已不再停留在“缺 relax / 缺 union-find / 缺 component 弹栈 / 缺 flow/capacity 更新”。
  - 未删除或放宽 Dijkstra、Kruskal、Tarjan、Edmonds-Karp 的核心 graph / flow validator 不变量。

### R5 DP / data structure / demo coverage 修复包

状态：已完成。

目标：

- 修复缺关键 DP / data structure 教学帧的问题。
- 修复 demo readiness 和 process validator 对 trace coverage 的对齐问题。

当前目标 case：

- `complete_knapsack_coin_change`
- `state_compression_tsp`
- `digit_dp_no_seven`
- `floyd_warshall_all_pairs`
- `segment_tree_range_sum`
- `sparse_table_range_min`
- `trie_prefix_match_string`
- `trie_prefix`
- `trie_prefix_expansion`
- `daily_temperatures`
- `permutations`
- `reverse_linked_list_expansion`

建议修改文件：

- `algolab/generation/prompts/tracker_system.txt`
  - 对 DP 和 data structure 强调：小规模样例不允许只给最终表；必须逐个关键 set。
  - 对 Trie prefix_count 给出 query 时 `prefix_count` 的状态语义，避免把插入累计 count 当成答案 count。
  - 对单调栈强调 pop 后必须写入对应答案 target。
  - 对回溯强调 choose / record / undo 三段。
- `algolab/generation/prompts/repair_system.txt`
  - 对 `demo_key_step_missing`、`demo_algorithm_mismatch`、`coverage_error` 明确要求补事件，不允许删除合同或改 final answer。
- `algolab/verification/repair_context.py`
  - 对 DP / Trie / monotonic stack / backtracking / linked_list 给出 submode guidance。
- `algolab/verification/process_families/dp.py`
  - 对完全背包、状态压缩、数位 DP 的错误信息增加“期望 deps / formula / loop key”。
- `algolab/verification/process_families/contracts.py`
  - 如果 Trie / backtracking 的 expected_events 诊断不够具体，增加明确错误。
- `algolab/verification/process_families/hash_sort_linked_greedy.py`
  - 单调栈 / 链表 guidance 和 validator 错误保持一致。

建议新增测试：

- `tests/regression/data_structure_repair_guidance.py`

测试必须覆盖：

- `demo_key_step_missing` 对 DP 输出“补 set 事件、deps、formula、answer_position”。
- Trie prefix_count 错误输出“query prefix count 与插入节点 count 区分”。
- 单调栈 `demo_algorithm_mismatch` 输出“pop 后写 answer target”。
- 回溯缺 choose / undo 输出“push/mark/enter 和 pop/unmark/exit”。

阶段测试命令：

```bash
python3 -m tests.regression.data_structure_repair_guidance
python3 -m tests.regression.trace_contracts
python3 -m tests.benchmark_regression
```

阶段 live smoke：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_r5_data_smoke \
  --condition algolab_full \
  --case complete_knapsack_coin_change \
  --case state_compression_tsp \
  --case digit_dp_no_seven \
  --case sparse_table_range_min \
  --case trie_prefix \
  --case daily_temperatures \
  --case permutations \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 1
```

验收：

- 目标 case 不再因为缺关键 set、缺 answer write、缺 choose/undo 或 prefix_count 语义混乱失败。
- 真实算法状态错误不能被降级为 warning。

完成证据（2026-05-31）：

- 修改文件：
  - `algolab/verification/repair_context.py`
  - `algolab/generation/prompts/tracker_system.txt`
  - `algolab/generation/prompts/repair_system.txt`
- 新增 / 修改测试：
  - `tests/regression/data_structure_repair_guidance.py`
  - `tests/benchmark_regression.py`
- 修复内容：
  - DP repair guidance 增加 `answer_position` 强约束：最终 `role=answer` 事件必须引用 `dp[answer_position]`，例如 `dp[11]`。
  - 完全背包 guidance 增加标准最少硬币转移：`j` 从 `coin` 到 `amount` 正序，`dp[j] = min(dp[j], dp[j-coin] + 1)`，每个 `set dp` 事件必须有 `state.formula` 或 `teaching.formula`。
  - 状态压缩 DP guidance 增加 `dp[next_mask][next] = min(dp[next_mask][next], dp[mask][last] + cost[last][next])` 和 `expected_targets` 不可省略要求。
  - Trie prefix guidance 明确 query prefix count 与插入节点 count 区分；计数 / 终止标记挂在 `node:<id>` 的 meta 或 `state.prefix_count`，不使用孤立 `count[i]` / `is_end[i]` target。
  - 单调栈 guidance 明确 `tracer.pop` 事件本身和后续 answer set 都必须带 `temperatures[popped_index]` 与 `temperatures[current_index]` deps。
  - 回溯 guidance 明确 `choose / record / undo`、`tracer.enter` / `tracer.exit`、每个事件 state 保留 `recursion_tree` / `search_tree`，且 `expected_events` 不使用不可满足的 `answer` token。
  - Sparse table guidance 明确逐个 `set st[k][i]`，值按 `st[0][i]=nums[i]`、`st[k][i] = min(st[k-1][i], st[k-1][i+2^(k-1)])` 生成，query 记录两个重叠区间和 answer target。
- regression 测试结果：
  - `python3 -m tests.regression.data_structure_repair_guidance`：PASS。
  - `python3 -m tests.regression.trace_contracts`：PASS。
  - `python3 -m tests.regression.repair_prompt_contracts`：PASS。
  - `python3 -m tests.benchmark_regression`：PASS。
  - `bash scripts/run_browser_smoke_container.sh python3 scripts/run_quality_checks.py`：`quality_checks: PASS`。
- live smoke：
  - `output/repair_r5_data_smoke/llm_benchmark_report.json`：`total=7`，`passed=1`，`failed=6`，`failure_summary={"process_invariant": 2, "generation": 2, "demo_missing_deps": 1, "demo_key_step_missing": 1}`；暴露 DP answer_position、Trie target、单调栈 deps、回溯 record/tree、sparse table 写入帧等缺口。
  - 补第一轮 guidance 后，`output/repair_r5_data_smoke2/llm_benchmark_report.json`：`total=7`，`passed=2`，`failed=5`，`failure_summary={"process_invariant": 3, "demo_missing_deps": 1, "demo_key_step_missing": 1}`；`digit_dp_no_seven` 与 `trie_prefix` 通过，剩余缺口收敛到 DP 转移 / formula、单调栈 pop deps、回溯 enter/undo、sparse table 数值。
  - 继续补 targeted guidance 后，`output/repair_r5_data_retry/llm_benchmark_report.json`：`total=5`，`passed=3`，`failed=2`；`state_compression_tsp`、`daily_temperatures`、`sparse_table_range_min` 通过，剩余为 `complete_knapsack_coin_change` 和 `permutations`。
  - 最终 targeted retry `output/repair_r5_final_retry2/llm_benchmark_report.json`：`total=2`，`passed=2`，`failed=0`；`complete_knapsack_coin_change` 与 `permutations` 均通过。
- R5 验收结论：
  - 最新 R5 smoke / targeted retry 中，目标 case 已不再停留在缺关键 set、缺 answer write、缺 choose/undo 或 prefix_count 语义混乱。
  - 完全背包、稀疏表等真实算法状态错误仍由 process validator 拦截；本阶段通过补 prompt / repair guidance 让生成结果修正算法状态，没有把错误降级为 warning。

### R6 全量 live LLM 回归与失败归因报告

状态：已完成。

目标：

- 在 R1 到 R5 之后全量复跑 `algolab_full`。
- 输出结构化失败归因报告，确认剩余失败是否还能按修复包处理。

允许新增：

- `scripts/analyze_llm_failures.py`
- `tests/regression/failure_attribution.py`

脚本要求：

- 输入一个 `llm_benchmark_report.json`。
- 输出：
  - `failure_attribution.json`
  - `failure_attribution.md`
  - `failure_attribution_by_family.csv`
  - `failure_attribution_by_root_cause.csv`
- 固定 root cause 枚举：
  - `legacy_schema_or_target_format`
  - `runtime_api_or_generated_code_error`
  - `missing_key_events_or_coverage`
  - `missing_evidence_or_deps`
  - `actual_algorithm_state_mismatch`
  - `scene_object_binding_warning`
  - `string_contract_overgeneralized`
  - `validator_acceptance_bug`
  - `unknown`
- 每个失败 result 必须保留原始 `failure_type`、`case_id`、`family`、`subfamily_id`、`error` 摘要和 root cause。

阶段测试命令：

```bash
python3 -m tests.regression.failure_attribution
```

全量复跑命令：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_llm_algolab_full \
  --condition algolab_full \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 2
```

归因报告命令：

```bash
python3 scripts/analyze_llm_failures.py \
  --report output/repair_llm_algolab_full/llm_benchmark_report.json \
  --output-dir output/repair_llm_algolab_full/failure_attribution
```

验收：

- `llm_benchmark_report.json` 存在，`total=69`。
- 每个失败项有 `failure_type`。
- browser smoke 对所有通过 HTML 执行。
- attribution 输出四个文件。
- 如果 `passed < 69`，必须在本文档中新增或更新下一轮修复阶段，不能把剩余失败吞掉。

阶段完成证据必须记录：

- total / passed / failed / pass_rate。
- failure_summary。
- root cause summary。
- browser_total / browser_ok / browser_failed。
- model_usage call_count / total_tokens / usage_available_rate。

完成证据（2026-05-31）：

- 新增 `scripts/analyze_llm_failures.py` 与 `tests/regression/failure_attribution.py`，并接入 `tests/benchmark_regression.py`。
- TDD 红测：
  - 首次运行 `python3 -m tests.regression.failure_attribution` 失败于 `ModuleNotFoundError: No module named 'scripts.analyze_llm_failures'`。
  - live 报告暴露 `failure_type=generation` 不能一律归为 runtime 后，补充红测并确认断言失败，再收紧分类规则。
  - live 报告暴露 `fast_slow_cycle` 的“窗口指针跳变”落入 `unknown` 后，补充红测并确认断言失败，再归入 `actual_algorithm_state_mismatch`。
- 阶段测试：
  - `python3 -m tests.regression.failure_attribution`：PASS。
  - `python3 -m tests.benchmark_regression`：PASS。
  - `bash scripts/run_browser_smoke_container.sh python3 scripts/run_quality_checks.py`：`quality_checks: PASS`。
- 全量 live 命令：
  - `bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py --output-dir output/repair_llm_algolab_full --condition algolab_full --max-rounds 2 --timeout-s 600 --browser-smoke --concurrency 2`
  - 进程退出码为 1，因为仍有失败项；报告已写入 `output/repair_llm_algolab_full/llm_benchmark_report.json`。
- 全量结果：
  - `total=69`，`passed=36`，`failed=33`，`pass_rate=0.5217391304347826`。
  - `failure_summary={"demo_state_jump": 1, "process_invariant": 19, "generation": 5, "correctness": 3, "visual_warning": 1, "demo_key_step_missing": 2, "demo_missing_reason": 1, "timeout": 1}`。
  - `browser_total=36`，`browser_ok=36`，`browser_failed=0`。
  - `model_usage.call_count=191`，`model_usage.total_tokens=2598418`，`model_usage.usage_available_rate=1`。
  - 失败项缺失 `failure_type` 数量为 0。
- 归因报告命令：
  - `python3 scripts/analyze_llm_failures.py --report output/repair_llm_algolab_full/llm_benchmark_report.json --output-dir output/repair_llm_algolab_full/failure_attribution`
- 归因输出：
  - `output/repair_llm_algolab_full/failure_attribution/failure_attribution.json`
  - `output/repair_llm_algolab_full/failure_attribution/failure_attribution.md`
  - `output/repair_llm_algolab_full/failure_attribution/failure_attribution_by_family.csv`
  - `output/repair_llm_algolab_full/failure_attribution/failure_attribution_by_root_cause.csv`
  - 每个失败记录均包含 `failure_type`、`case_id`、`family`、`subfamily_id`、`error_summary`、`root_cause`。
- `root_cause_summary={"legacy_schema_or_target_format": 2, "runtime_api_or_generated_code_error": 6, "missing_key_events_or_coverage": 6, "missing_evidence_or_deps": 12, "actual_algorithm_state_mismatch": 4, "scene_object_binding_warning": 1, "string_contract_overgeneralized": 0, "validator_acceptance_bug": 2, "unknown": 0}`。
- R6 结论：
  - R1-R5 后 deterministic full 尚未达到 69/69，不能进入 unseen 复核作为下一步。
  - 剩余失败可按修复包处理，下一阶段已更新为 R7 deterministic residual 修复包。

### R7 deterministic residual 修复包

状态：已完成（2026-06-01，用户确认 R7 按 `66/69` 口径通过）。

目标：

- 基于 `output/repair_llm_algolab_full/failure_attribution/` 的 33 个失败归因，修复 deterministic `algolab_full` 剩余失败。
- R7 原目标为 `total=69`、`passed=69`、`failed=0`；2026-06-01 用户将本阶段验收口径调整为 `total=69`、`passed>=66`。
- 保持 browser smoke 对所有通过 HTML 执行，且 browser smoke 不允许失败。

优先修复包：

- `missing_evidence_or_deps`（12 个）：
  - `binary_answer_sqrt`、`binary_search`：数组指针 / 二分 submode 与比较证据。
  - `knapsack_01_subset_sum`、`bounded_knapsack_max_value`：DP 循环变量、关键更新 deps、capacity state。
  - `graph_connected_components`：DFS stack / recursion frame frontier。
  - `reverse_linked_list`：链表节点 deps 必须出现在 state。
  - `lca`：tree current、子树返回值 / 聚合结果。
  - `trie_prefix`、`trie_prefix_expansion`：字符路径、count / prefix_count、create_node。
  - `fenwick_tree_prefix_sum`：reason 中提到的 `nums` 必须有 targets / deps / state 依据。
  - `dijkstra_shortest_path_expansion`：关键步骤 reason。
- `runtime_api_or_generated_code_error`（6 个）：
  - 禁止生成 `Tracer.to_trace(result=...)` 与 `Tracer._add(stage=...)`。
  - 覆盖 `prefix_sum_range`、`string_sliding_window_unique`、`gcd_euclid_expansion`。
  - 处理 `graph_topological_sort`、`articulation_bridges` 的非法 / 空 JSON。
  - 处理 `reverse_linked_list_expansion` trace 执行超时。
- `missing_key_events_or_coverage`（6 个）：
  - `sliding_window_min_len`、`difference_array_range_add`：数组关键更新。
  - `digit_dp_no_seven`：`dp[0]` 关键更新。
  - `floyd_warshall_all_pairs`：状态转移写入帧。
  - `kruskal_mst_weight`：边检查帧。
  - `kth_largest_expansion`：heap pop 事件。
- `actual_algorithm_state_mismatch`（4 个）：
  - `fast_slow_cycle`：窗口 / 快慢指针状态跳变。
  - `dijkstra_shortest_path`：dist 松弛状态。
  - `tree_max_independent_set`：树形 DP `dp_take`。
  - `jump_game_expansion`：reach 更新。
- `legacy_schema_or_target_format`（2 个）：
  - `permutations`：不能引用不存在的 `nums[i]` target。
  - `bitmask_subsets`：不能引用不存在的 `result[i]` target。
- `scene_object_binding_warning`（1 个）：
  - `bellman_ford_shortest_path`：edge source / target 必须绑定到对象集合中的 node。
- `validator_acceptance_bug`（2 个）：
  - `provinces`：补 `union_find` family contract 支持。
  - `segment_tree_range_sum`：补 range/data_structure family contract 路由，不应停在“未支持的 family”。

建议新增或更新测试：

- `tests/regression/r7_residual_repair_guidance.py`
- 必须先写红测覆盖至少：
  - runtime API 禁止 `to_trace(result=...)` / `_add(stage=...)`。
  - array pointer submode、关键更新、comparison deps。
  - tree/trie/heap/union_find/range family contract 支持。
  - 非法 target `nums[i]` / `result[i]` 的修复 guidance。

建议 targeted live smoke：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_r7_residual_smoke \
  --condition algolab_full \
  --case binary_search \
  --case binary_answer_sqrt \
  --case prefix_sum_range \
  --case knapsack_01_subset_sum \
  --case bounded_knapsack_max_value \
  --case graph_connected_components \
  --case dijkstra_shortest_path \
  --case trie_prefix \
  --case provinces \
  --case segment_tree_range_sum \
  --case bitmask_subsets \
  --case reverse_linked_list_expansion \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 2
```

最终验收命令：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_llm_algolab_full \
  --condition algolab_full \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 2
```

验收：

- R7 调整后验收报告存在，`total=69`，`passed>=66`。
- 对所有通过产物执行 browser smoke，且全部 `ok=true`。
- R7 完成后再进入 unseen 复核与 metric 口径清理。

完成证据（2026-06-01）：

- 本地回归通过：
  - `python3 -m tests.regression.r7_residual_repair_guidance`：PASS。
  - `python3 -m tests.regression.repair_prompt_contracts`：PASS。
  - `python3 -m tests.regression.trace_contracts`：PASS。
  - `python3 -m tests.regression.scene_edge_binding`：PASS。
  - `python3 -m tests.regression.reports_and_gates`：PASS。
  - `python3 -m tests.benchmark_regression`：PASS。
- 完整 live full：
  - `bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py --output-dir output/repair_llm_algolab_full_r7_smoke109 --condition algolab_full --max-rounds 2 --timeout-s 1200 --browser-smoke --concurrency 8`
  - 报告：`output/repair_llm_algolab_full_r7_smoke109/llm_benchmark_report.json`。
  - `total=69`，`passed=66`，`failed=3`，`pass_rate=0.9565217391304348`。
  - `browser_total=66`，`browser_ok=66`，`browser_failed=0`。
  - 失败项为 `z_algorithm`、`trie_prefix`、`sparse_table_range_min`，均为 process / target 约束问题。
- 针对 full 残留 3 项的定向 live：
  - `bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py --output-dir output/repair_r7_z_trie_sparse_smoke110 --condition algolab_full --case z_algorithm --case trie_prefix --case sparse_table_range_min --max-rounds 2 --timeout-s 1200 --browser-smoke --concurrency 8`
  - 报告：`output/repair_r7_z_trie_sparse_smoke110/llm_benchmark_report.json`。
  - `total=3`，`passed=3`，`failed=0`，`browser_total=3`，`browser_ok=3`，`browser_failed=0`。
- 2026-06-01 用户明确将 R7 验收口径降为 `66/69`，因此本阶段按 `smoke109` full 证据标记完成；不声明 R7 已达到 `69/69`。

### R8 unseen 复核与 metric 口径清理

状态：已完成（2026-06-02）。

目标：

- 确认对 69 deterministic case 的修复没有明显过拟合。
- 清理 evaluation report 中容易误导的 metric 命名，避免把 direct HTML browser pass 当成 correctness pass。

建议修改文件：

- `scripts/build_evaluation_report.py`
  - 将 merged report 中混合 condition 的 `correctness_gate_pass_rate` 拆成 condition-specific 指标。
  - 对 `direct_html_baseline` 标记 `machine_correctness_gate_available=false`。
  - VLM condition summary 明确命名为 `vlm_quality_on_successful_screenshots`。
- `scripts/merge_llm_reports.py`
  - 保留每个 source report 的 config / model info，避免 `Model: N/A`。
- `docs/06_EVALUATION_AND_BENCHMARK.md`
  - 补充 direct HTML baseline 只能比较 browser / VLM 截图质量，不能比较 AlgoLab release gate。
- `docs/08_AAAI_EXPERIMENT_PLAN.md`
  - 如需要，只追加一小段“09 修复后口径说明”，不要改历史完成证据。

建议新增测试：

- `tests/regression/evaluation_metric_semantics.py`

测试必须覆盖：

- merged report 中 `direct_html_baseline` 不进入 strict correctness gate 聚合。
- `algolab_full` strict pass rate 单独输出。
- VLM 平均分字段名称包含 successful screenshots 或 equivalent 说明。
- merged model config 不再显示 `Model: N/A`，至少保留 source report 的模型列表。

unseen 复跑命令：

```bash
bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py \
  --output-dir output/repair_llm_unseen \
  --condition algolab_full \
  --case-set unseen \
  --max-rounds 2 \
  --timeout-s 600 \
  --browser-smoke \
  --concurrency 2
```

evaluation 重建命令：

```bash
python3 scripts/merge_llm_reports.py \
  --output-dir output/repair_evaluation \
  --report algolab_full=output/repair_llm_algolab_full/llm_benchmark_report.json \
  --report unseen_algolab_full=output/repair_llm_unseen/llm_benchmark_report.json \
  --report direct_html_baseline=output/aaai_llm_direct_html/llm_benchmark_report.json \
  --report no_process_validator=output/aaai_llm_no_process_validator/llm_benchmark_report.json \
  --report no_scenegraph_compiler=output/aaai_llm_no_scenegraph_compiler/llm_benchmark_report.json \
  --report no_repair=output/aaai_llm_no_repair/llm_benchmark_report.json

python3 scripts/build_evaluation_report.py \
  --output-dir output/repair_evaluation \
  --llm-report output/repair_evaluation/merged_llm_benchmark_report.json \
  --vlm-report output/aaai_vlm_conditions/vlm_condition_scores.json \
  --family-gate output/aaai_release_gate/family_release_gate.json \
  --dashboard output/aaai_dashboard_all/dashboard.json
```

验收：

- unseen report 存在，`case_set=unseen`，失败项都有 `failure_type`。
- evaluation report 不再把 direct HTML baseline 的 browser-only pass 写成 strict correctness gate。
- Markdown 明确区分 strict release gate、browser smoke、VLM-on-successful-screenshots。

完成证据（2026-06-02）：

- 代码与文档更新：
  - `scripts/merge_llm_reports.py`：merged report 保留 `config.source_reports` 与 `config.models`，每个 source report 记录 condition、source condition、path、model、config、summary 和 model usage。
  - `scripts/build_evaluation_report.py`：`direct_html_baseline` 不进入 strict correctness gate 聚合；新增 `algolab_full_strict_release_gate_pass_rate`；condition summary 输出 `machine_correctness_gate_available`；VLM 平均分字段明确为 successful screenshots 上的质量；merged model config 不再输出 `Model: N/A`。
  - `tests/regression/evaluation_metric_semantics.py`：覆盖 direct HTML baseline 排除、algolab_full strict 指标、VLM successful screenshots 字段和 merged model config。
  - `docs/06_EVALUATION_AND_BENCHMARK.md`、`docs/08_AAAI_EXPERIMENT_PLAN.md`：补充 strict release gate、browser smoke、VLM-on-successful-screenshots 的边界说明。
- 本地回归通过：
  - `python3 -m tests.regression.evaluation_metric_semantics`：PASS。
  - `python3 -m tests.regression.vlm_conditions`：PASS。
  - `python3 -m tests.regression.reports_and_gates`：PASS。
  - `python3 -m tests.benchmark_regression`：PASS。
  - `git diff --check -- scripts/merge_llm_reports.py scripts/build_evaluation_report.py tests/regression/evaluation_metric_semantics.py tests/benchmark_regression.py docs/06_EVALUATION_AND_BENCHMARK.md docs/08_AAAI_EXPERIMENT_PLAN.md docs/09_LLM_SUCCESS_REPAIR_PLAN.md`：PASS。
- unseen live 复核：
  - `bash scripts/run_browser_smoke_container.sh python3 scripts/run_llm_benchmark.py --output-dir output/repair_llm_unseen --condition algolab_full --case-set unseen --max-rounds 2 --timeout-s 1200 --browser-smoke --concurrency 8`
  - 报告：`output/repair_llm_unseen/llm_benchmark_report.json`。
  - `case_set=unseen`，`total=15`，`passed=14`，`failed=1`，`pass_rate=0.9333333333333333`。
  - `browser_total=14`，`browser_ok=14`，`browser_failed=0`。
  - 失败项：`unseen_longest_palindromic_substring_length`，`failure_type=process_invariant`，`gate_layer=llm_eval`，错误为 string family contract 缺少 `text/pattern` 指针与失配/扩展或窗口移动原因。
  - 失败项 `missing_failure_type=[]`，满足 R8 unseen 失败归因验收。
- evaluation 重建：
  - `python3 scripts/merge_llm_reports.py --output-dir output/repair_evaluation --report algolab_full=output/repair_llm_algolab_full_r7_smoke109/llm_benchmark_report.json --report unseen_algolab_full=output/repair_llm_unseen/llm_benchmark_report.json --report direct_html_baseline=output/aaai_llm_direct_html/llm_benchmark_report.json --report no_process_validator=output/aaai_llm_no_process_validator/llm_benchmark_report.json --report no_scenegraph_compiler=output/aaai_llm_no_scenegraph_compiler/llm_benchmark_report.json --report no_repair=output/aaai_llm_no_repair/llm_benchmark_report.json`
  - `python3 scripts/build_evaluation_report.py --output-dir output/repair_evaluation --llm-report output/repair_evaluation/merged_llm_benchmark_report.json --vlm-report output/aaai_vlm_conditions/vlm_condition_scores.json --family-gate output/aaai_release_gate/family_release_gate.json --dashboard output/aaai_dashboard_all/dashboard.json`
  - 输出：`output/repair_evaluation/merged_llm_benchmark_report.json`、`output/repair_evaluation/evaluation_report.json`、`output/repair_evaluation/evaluation_report.md`、`output/repair_evaluation/evaluation_vlm_condition_summary.csv`。
  - `correctness_gate_pass_rate=80/84=0.952381`，说明 direct HTML baseline 已排除出 strict correctness gate 聚合。
  - `algolab_full_strict_release_gate_pass_rate=66/69=0.956522`，使用 R7 已确认的 `output/repair_llm_algolab_full_r7_smoke109/llm_benchmark_report.json` 作为 full 证据。
  - `direct_html_baseline.machine_correctness_gate_available=false`。
  - `model_config.models=["gemini-3.1-pro-preview"]`，Markdown 显示 `Model: gemini-3.1-pro-preview`，不再显示 `Model: N/A`。
  - `vlm_summary.vlm_quality_on_successful_screenshots` 存在，`evaluation_vlm_condition_summary.csv` 包含 `avg_overall_teaching_quality_on_successful_screenshots`。

### R9 最终收口

状态：已完成（2026-06-02）。

目标：

- 按 2026-06-01 用户确认的 `66/69` deterministic strict release gate 口径完成最终质量检查和文档收口。
- 使用 R7 已确认的 `output/repair_llm_algolab_full_r7_smoke109/llm_benchmark_report.json` 作为 full live 证据，不再继续追 `69/69`。

最终测试命令：

```bash
python3 -m tests.benchmark_regression
python3 -m tests.offline_regression
python3 scripts/check_family_release_gate.py --output-dir output/repair_release_gate
python3 -m tests.regression.repair_prompt_contracts
python3 -m tests.regression.trace_contracts
python3 -m tests.regression.scene_edge_binding
python3 -m tests.regression.graph_repair_guidance
python3 -m tests.regression.data_structure_repair_guidance
python3 -m tests.regression.failure_attribution
python3 -m tests.regression.evaluation_metric_semantics
bash scripts/run_browser_smoke_container.sh python3 scripts/run_quality_checks.py
```

最终验收脚本：

```bash
python3 - <<'PY'
import json
from pathlib import Path

full = json.loads(Path("output/repair_llm_algolab_full_r7_smoke109/llm_benchmark_report.json").read_text(encoding="utf-8"))
assert full["total"] == 69
assert full["passed"] >= 66
assert full["failed"] == full["total"] - full["passed"]
assert full["pass_rate"] >= 66 / 69
assert not [item["case_id"] for item in full["results"] if (not item.get("ok")) and not item.get("failure_type")]
browser = full.get("browser_smoke") or []
assert len(browser) == full["passed"]
assert all(item.get("ok") for item in browser)
assert all(item.get("model_calls") for item in full["results"])
print(f"algolab_full deterministic live LLM: {full['passed']}/69, accepted threshold >=66/69")

family_gate = json.loads(Path("output/repair_release_gate/family_release_gate.json").read_text(encoding="utf-8"))
assert family_gate["overall_ready"] is True
summary = family_gate["summary"]
assert summary["case_count"] == 69
assert summary["sample_count"] == 250
assert summary["answer_pass_rate"] == 1.0
assert summary["process_pass_rate"] == 1.0
assert summary["demo_readiness_pass_rate"] == 1.0
assert summary["process_fallback_cases"] == 0
assert summary["process_uncovered_cases"] == 0
print("family gate deterministic: 69 cases / 250 samples all ready")
PY
```

最终文档更新：

- 更新本文档每个阶段的完成证据。
- 如 `docs/08_AAAI_EXPERIMENT_PLAN.md` 的最终指标引用旧 AAAI 输出路径，不直接覆盖历史证据；新增“09 修复后结果”小节或另建 artifact README。
- 在 `output/repair_evaluation/evaluation_report.md` 中确认 baseline 表述不混淆。

完成证据（2026-06-02）：

- R9 口径收口：
  - 2026-06-01 用户已明确将 R7 deterministic strict release gate 验收口径调整为 `66/69`，R9 因此使用 `output/repair_llm_algolab_full_r7_smoke109/llm_benchmark_report.json` 作为最终 full live 证据，不再继续追 `69/69`。
  - 本文档 R9 目标、最终验收脚本和执行 AI 启动提示词已同步到 `66/69` 当前口径。
  - 未改 expected，未关闭 validator / gate，未跳 case，未混用 direct HTML baseline。
- 最终测试命令通过：
  - `python3 -m tests.benchmark_regression`：PASS。
  - `python3 -m tests.offline_regression`：PASS。
  - `python3 scripts/check_family_release_gate.py --output-dir output/repair_release_gate`：生成 `output/repair_release_gate/family_release_gate.json`。
  - `python3 -m tests.regression.repair_prompt_contracts`：PASS。
  - `python3 -m tests.regression.trace_contracts`：PASS。
  - `python3 -m tests.regression.scene_edge_binding`：PASS。
  - `python3 -m tests.regression.graph_repair_guidance`：PASS。
  - `python3 -m tests.regression.data_structure_repair_guidance`：PASS。
  - `python3 -m tests.regression.failure_attribution`：PASS。
  - `python3 -m tests.regression.evaluation_metric_semantics`：PASS。
  - `bash scripts/run_browser_smoke_container.sh python3 scripts/run_quality_checks.py`：`quality_checks: PASS`。
- 最终验收脚本通过：
  - `output/repair_llm_algolab_full_r7_smoke109/llm_benchmark_report.json`：`total=69`，`passed=66`，`failed=3`，`pass_rate=0.9565217391304348`。
  - `browser_total=66`，`browser_ok=66`，`browser_failed=0`。
  - `failure_summary={"process_invariant": 3}`，失败项均有 `failure_type`。
  - `model=gemini-3.1-pro-preview`，`model_usage.call_count=138`，`duration_s=8201.432`，`total_tokens=2846685`，`usage_available_rate=1.0`。
  - 所有 69 个 result 均有 `model_calls`。
  - `output/repair_release_gate/family_release_gate.json`：`overall_ready=true`，`case_count=69`，`sample_count=250`，`answer_pass_rate=1.0`，`process_pass_rate=1.0`，`demo_readiness_pass_rate=1.0`，`process_fallback_cases=0`，`process_uncovered_cases=0`。
- R8 产物沿用为最终 evaluation 收口：
  - `output/repair_evaluation/merged_llm_benchmark_report.json`。
  - `output/repair_evaluation/evaluation_report.json`。
  - `output/repair_evaluation/evaluation_report.md`。
  - `output/repair_evaluation/evaluation_vlm_condition_summary.csv`。
  - `correctness_gate_pass_rate=80/84=0.952381`，`direct_html_baseline.machine_correctness_gate_available=false`，`algolab_full_strict_release_gate_pass_rate=66/69=0.956522`，Markdown 显示 `Model: gemini-3.1-pro-preview`，VLM 字段明确为 successful screenshots 口径。

## 8. 执行 AI 汇报格式

执行 AI 每轮完成后必须按以下格式汇报：

1. 本轮执行了哪个阶段。
2. 修改了哪些文件。
3. 新增或修改了哪些测试。
4. 运行了哪些命令。
5. 每条命令结果如何。
6. live LLM smoke 或 full run 的 total / passed / failed / pass_rate。
7. failure_summary 和 root cause summary。
8. 是否改动 validator；如果改了，说明为什么不是放宽真实错误。
9. deterministic gate 是否仍通过。
10. 是否还有遗留问题和下一阶段建议。

必须列出：

- 所有实验命令。
- 所有 output 路径。
- LLM 实际模型。
- model_usage call_count、duration_s、total_tokens、usage_available_rate。
- bugfix 的失败命令、最小修复和复跑证据。

## 9. 给执行 AI 的启动提示词

```text
你是执行 AI，在 .。阅读 docs/09_LLM_SUCCESS_REPAIR_PLAN.md，只做最靠前的“状态：待执行。”阶段，完成后把该阶段改成“状态：已完成。”并写完成证据。不要做 Git，不提交不推送。Python 固定用 python3，浏览器命令走 bash scripts/run_browser_smoke_container.sh。可以修可复现 bug，但必须最小修复、加测试、复跑失败命令。不要改 expected，不要放宽 gate，不要跳 case。R7 已由用户确认按 deterministic strict release gate `66/69` 口径通过；后续最终收口使用 `output/repair_llm_algolab_full_r7_smoke109/llm_benchmark_report.json` 作为 full live 证据，而不是继续追 `69/69`。按 docs/09 的汇报格式汇报。
```
