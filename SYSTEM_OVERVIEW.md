# AlgoLab 系统说明

本文档是当前项目的主说明文档。它描述实际代码正在使用的架构、数据流、质量门禁、运行方式和维护边界。

旧的阶段设计文档已经合并到这里；需要了解系统时优先读本文档，再看源码。

## 1. 系统目标

AlgoLab 是一个可验证的算法可视化生成系统。

输入：

- LeetCode 风格题目描述。
- 一组具体 JSON 输入。
- 可选 expected output。
- 可选解法思路。
- 可选用户代码。
- 希望生成的解法数量。

输出：

- 可执行解法 `solve(input_data)`。
- 可执行语义轨迹 `trace(input_data)`。
- 独立校验器 `verify(input_data)`。
- 通过校验的 `BuildArtifact` JSON。
- 单文件中文交互式 HTML 页面。

核心原则：

- LLM 只生成算法语义候选，不生成 HTML/CSS/JS。
- 系统执行和校验 LLM 输出，错误产物不能发布。
- Renderer 只消费 `SceneGraph`，不理解具体算法题。
- 新增算法优先复用通用视觉形态和固定语义 op。
- 当前版本使用严格 `SemanticTrace` 协议，不再兼容旧式 trace 字段和旧式 map target。

### 1.1 当前系统功能状态

当前系统已经从“让 LLM 自由手写事件列表”升级为“LLM 生成算法代码，系统用统一语义协议执行、校验、编译和渲染”。

主要能力：

- Web UI 和 CLI 都走同一条 `ProblemInput -> BuildArtifact -> HTML` 管线。
- LLM 负责生成 `solve(input_data)`、`trace(input_data)`、`verify(input_data)` 和多解法 variants。
- `tracker_code` 推荐使用系统注入的 `Tracer` API 生成 trace，系统统一管理 step、targets/deps、抽样、coverage 和 `_trace_meta`。
- `trace(input_data)` 必须返回 `semantic-trace-v1` 格式，且必须显式包含与本次请求完全一致的 `input_data`。
- 系统会真实执行 `solve`、`trace`、`verify`，再经过 schema、trace、process、scene、release gate 多层校验。
- 通过校验后输出单文件 HTML 和对应 artifact JSON，renderer 只读取 `SceneGraph`，不读取 LLM 代码。
- 确定性 benchmark 覆盖 DP、图、栈队列、哈希表、树、堆、Trie、并查集、递归、字符串、几何和 ML primitive 等视觉形态。

最近移除的旧兼容：

- 不再把事件字段 `type` 自动转换成 `op`。
- 不再把事件字段 `target` 自动转换成 `targets`。
- 不再给 trace 自动补缺失的 `input_data`。
- 不再自动规范化 quoted map target，例如 `seen['2']`。
- 不再接受旧式 map target，例如 `seen:2`、`dist:A`、`map:seen`。

当前推荐 target 写法：

```text
数组/表格：nums[0]、dp[1][2]
切片：text[2:5]
哈希表：seen[2]、dist[B]、count[x]
图节点/边：node:A、edge:A->B
指针：pointer:left、pointer:mid
递归帧：frame:dfs(2)
几何点：point:3
字符串字符：text[3]、pattern[2]
```

## 2. 主入口

### Web UI

文件：`app.py`

启动：

```bash
cd /ssd1/liaokunpeng/paper/ailab-agent
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 app.py
```

默认端口：`7861`

Gradio 缓存目录固定在项目内：

```text
.gradio_cache/
```

如果在容器里启动，宿主机需要映射端口：

```bash
docker run -p 7861:7861 ...
```

### CLI

文件：`cli.py`

默认样例：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 cli.py --strategy "动态规划" --solutions 2 --output output/algolab.html
```

不同路径样例：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 cli.py \
  --problem "LeetCode 62. 不同路径。机器人每次只能向下或向右移动，返回路径数。" \
  --input '{"m":3,"n":7}' \
  --expected '28' \
  --strategy "动态规划和组合数学" \
  --solutions 2 \
  --output output/unique_paths.html
```

### 静态 Dashboard

生成：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_demo_dashboard.py --output-dir output/dashboard --style both
```

直接打开：

```text
output/dashboard/index.html
```

或用本地静态服务：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m http.server 8000 --directory output/dashboard
```

访问：

```text
http://127.0.0.1:8000/
```

## 3. 目录结构

```text
algolab/
  schemas/              # Pydantic 数据模型
  generation/           # LLM prompt、解析、修复
  runtime/              # sandbox 执行 solve / trace / verify
  verification/         # contract / trace / process / scene / release gate
  compiler/             # SemanticTrace -> SceneGraph
  renderer/             # SceneGraph -> HTML runtime

tests/                  # 离线、benchmark、浏览器 smoke 测试
scripts/                # dashboard、benchmark、质量检查脚本
output/                 # 生成产物，已 gitignore
app.py                  # Gradio Web UI
cli.py                  # CLI 入口
llm_client.py           # OpenAI-compatible LLM 客户端
SYSTEM_FLOW.html        # 系统流程可视化说明
SYSTEM_OVERVIEW.md      # 当前文档
```

## 3.1 文件级调用顺序

主路径从用户输入到 HTML 产物，文件级调用链如下：

```text
app.py / cli.py
  -> algolab/schemas/input.py
  -> algolab/pipeline.py
  -> algolab/generation/solution_generator.py
  -> llm_client.py
  -> algolab/generation/prompts/tracker_system.txt
  -> algolab/schemas/semantic_trace.py
  -> algolab/runtime/executor.py
  -> algolab/runtime/sandbox.py
  -> algolab/runtime/tracer.py
  -> algolab/verification/contract_validator.py
  -> algolab/verification/trace_validator.py
  -> algolab/verification/process_validator.py
  -> algolab/compiler/target_parser.py
  -> algolab/compiler/scene_compiler.py
  -> algolab/schemas/scene_graph.py
  -> algolab/verification/scene_validator.py
  -> algolab/verification/release_gate.py
  -> algolab/schemas/validation.py
  -> algolab/renderer/export.py
  -> algolab/renderer/targets.py
  -> algolab/renderer/panels.py
  -> algolab/renderer/runtime_shell.py
  -> algolab/renderer/spatial_runtime.py
  -> algolab/renderer/layout_registry.py
  -> output/*.html + output/*.json
```

展开说明：

1. `app.py` / `cli.py` 读取题目、输入、期望输出和解法数量。
2. `algolab/schemas/input.py` 用 `ProblemInput` 统一封装请求。
3. `algolab/pipeline.py` 的 `build_artifact()` 负责总调度。
4. `algolab/generation/solution_generator.py` 组织 prompt，并通过 `llm_client.py` 请求模型。
5. `tracker_system.txt` 约束 LLM 输出 `solve`、`tracker_code`、`verifier_code` 和 variants。
6. `solution_generator.py` 将 LLM JSON 规范化为 `SolutionVariant`。
7. `algolab/runtime/executor.py` 调用 sandbox 分别执行 `solve(input_data)` 和 `trace(input_data)`。
8. `algolab/runtime/sandbox.py` 在子进程中执行生成代码，并注入 `Tracer`。
9. `algolab/runtime/tracer.py` 在新 tracker 路径下统一生成 `SemanticTrace`、coverage meta 和抽样信息。
10. `executor.py` 只做必要的 step 重编号、budget 和 result 一致性检查；不再兼容旧字段或旧 target 格式。
11. `contract_validator.py`、`trace_validator.py`、`process_validator.py` 分别检查 contract、trace 引用和算法过程。
12. `target_parser.py` 解析 `dp[1][2]`、`node:A`、`edge:A->B`、`pointer:left` 等 target id。
13. `scene_compiler.py` 将 `SemanticTrace` 编译为 `SceneGraph`，把 state、targets、deps 转成可渲染对象、标记和箭头。
14. `scene_validator.py` 检查 scene graph 是否可渲染。
15. `release_gate.py` 汇总 artifact、trace、process、visual 等发布门禁。
16. `validation.py` 定义最终 `BuildArtifact`、`ValidationReport` 和 `ReleaseGate`。
17. `renderer/export.py` 将 `BuildArtifact` 打包为单文件 HTML，并写出 JSON 副本。
18. `renderer/targets.py`、`panels.py`、`runtime_shell.py`、`spatial_runtime.py`、`layout_registry.py` 提供页面外壳、面板结构、渲染目标和前端运行时。

一句话版本：

```text
入口 app/cli
  -> pipeline
  -> LLM generator
  -> executor / sandbox / Tracer
  -> validators
  -> scene compiler
  -> release gate
  -> renderer / export
  -> HTML
```

## 4. 核心数据结构

### ProblemInput

位置：`algolab/schemas/input.py`

表示用户请求：

- `problem`
- `input_data`
- `strategy_hint`
- `user_code`
- `expected_result`
- `solution_count`

### Solution Spec

LLM 首次输出的 JSON，不是最终产物：

```json
{
  "problem_title": "...",
  "input_contract": "...",
  "variants": [
    {
      "id": "...",
      "name": "...",
      "strategy": "...",
      "time_complexity": "O(...)",
      "space_complexity": "O(...)",
      "code": "def solve(input_data): ...",
      "tracker_code": "def trace(input_data): ..."
    }
  ],
  "verifier_code": "def verify(input_data): ..."
}
```

可选字段：

- `correctness_contract`
- `visual_plan`

### SemanticTrace

位置：`algolab/schemas/semantic_trace.py`

`trace(input_data)` 必须返回固定格式：

- `schema_version`
- `algorithm`
- `input_data`
- `result`
- `pseudocode`
- `events`

固定 op 集合：

```text
create / set / mark / unmark / move / compare / link / unlink /
push / pop / enter / exit / explain
```

事件必须包含可核对的状态快照，不能只写自然语言。

当前版本的 trace 是严格格式：

- 事件字段必须使用 `op`，不能使用旧字段 `type`。
- 事件目标必须使用 `targets: [{"id": "..."}]`，不能使用旧字段 `target`。
- `trace` 顶层必须显式包含 `input_data`，并且与本次请求输入完全一致。
- `state` 是当前帧可视化和过程校验的主要证据，内部字段如果以下划线开头会在编译 `SceneGraph` 时隐藏。
- 哈希表 / map target 使用方括号格式，例如 `seen[2]`、`dist[B]`、`count[x]`。
- 结构化前缀继续保留，例如 `node:`、`edge:`、`pointer:`、`frame:`、`point:`、`char:`。

已废弃写法：

```text
type / target       -> 改为 op / targets
seen:2              -> seen[2]
dist:A              -> dist[A]
map:seen            -> seen
seen['2']           -> seen[2]
```

## Tracer API

新 tracker 应使用系统提供的 `Tracer`，不要直接手写 `events.append({...})`。

当前状态：

- `tracker_code` 可以调用 `Tracer` 生成标准 `SemanticTrace`。
- 小规模 DP 等语义更新数不超过预算的输入会保留完整逐帧过程。
- 大输入会进入 sampled mode，并在 `_trace_meta` 中记录抽样状态。
- process validator 会基于事件重新计算 coverage，拒绝非抽样模式下覆盖不足的 trace。
- executor 对 Tracer full trace 放宽 raw event 数限制，允许 compare + set 这类多事件逐帧表达。

作用：

1. 防止跳帧。
2. 统一 trace schema。
3. 统一粒度策略。
4. 支持标准轨迹和学生轨迹对齐。
5. 输出 trace coverage 指标。
6. 大输入时明确进入 sampled mode。

已知限制：

第一版定位为科研原型，默认 generated tracker 按 Tracer API 生成 trace。`_trace_meta` 目前仍放在 trace 事件的 `state` 中，不是不可伪造的执行侧证明；恶意手写 tracker 理论上可以构造类似 meta 影响预算判断。这个限制不影响正常 Tracer 路径、逐帧展示、coverage 统计和 demo 流程。后续如果进入生产化，需要把 Tracer 输出来源做成 executor 内部可信标记，或在 budget 阶段重新计算并严格校验 meta 与事件序列的一致性。

### SceneGraph

位置：`algolab/schemas/scene_graph.py`

`SceneGraph` 是 renderer 的唯一输入。它由 `SemanticTrace` 编译得到，包含：

- frame 列表。
- frame 中的 scene object。
- marks / arrows / state / teaching / evidence。

Renderer 不直接读取题目文本和算法逻辑，只读 `SceneGraph`。

### BuildArtifact

位置：`algolab/schemas/validation.py`

最终构建产物：

- `problem_title`
- `input_data`
- `expected_result`
- `verifier_result`
- `variants`
- `scenes`
- `validation`
- `correctness_contract`
- `visual_plan`
- `render_report`

## 5. 生成和校验流程

主流程在 `algolab/pipeline.py`：

```text
ProblemInput
  -> generate_solution_spec()
  -> _try_materialize()
  -> execute_variant()
  -> validate_trace()
  -> validate_process()
  -> compile_scene()
  -> validate_scene()
  -> compute_release_gate()
  -> BuildArtifact
  -> save_html()
```

如果失败：

```text
原始输入 + 上一次 spec + 错误信息
  -> repair_solution_spec()
  -> 再次 _try_materialize()
```

默认最多修复 2 轮。

`execute_variant()` 的 trace materialization 边界：

```text
run solve(input_data)
  -> run trace(input_data)
  -> trace 必须是 dict
  -> trace 必须显式包含 input_data
  -> 重编号 events.step
  -> 检查 event budget
  -> SemanticTrace.model_validate()
  -> trace.input_data 必须等于本次 input_data
  -> solve_result 必须等于 trace.result
```

这里已经没有旧格式兼容层。也就是说，旧式 `type/target` 事件、缺失 `input_data` 的 trace、旧式 map target 都会在 Pydantic schema、trace validator 或 process validator 阶段失败，并触发 repair。

## 6. 正确性门禁

### 6.1 执行一致性

系统实际运行生成代码：

- `solve(input_data)`
- `trace(input_data)`
- `verify(input_data)`

检查：

```text
solve(input_data) == trace.result
solve(input_data) == expected_result    如果用户提供 expected
solve(input_data) == verify(input_data) 如果 verifier 可执行
多个 variant 的 result 一致            如果生成多个解法
```

### 6.2 Contract 校验

位置：`algolab/verification/contract_validator.py`

如果 LLM 输出 `correctness_contract`，系统会校验：

- input schema。
- output schema。
- postconditions。
- oracle strategy。
- test cases。
- generated oracle / expected-only oracle。

Contract 不是页面渲染规则，它用于增强答案正确性证据。

### 6.3 Trace Schema 校验

位置：`algolab/verification/trace_validator.py`

检查：

- op 是否在固定集合内。
- step 是否连续。
- target id 是否可解析。
- 是否使用了已废弃的旧式 map target。
- target 是否明显越界。
- trace input 是否等于当前 input。
- trace result 是否等于 solve result。

接受示例：

```text
seen[2]
dist[A]
count[word]
node:A
edge:A->B
pointer:mid
```

拒绝示例：

```text
seen:2
dist:A
map:seen
```

### 6.4 Process Invariant 校验

位置：`algolab/verification/process_validator.py`

这是防止“结果对但过程乱写”的核心层。它分三类：

- Core：通用过程证据，例如 `set` 必须有可观测变化、deps、before/after 或 value。
- Structure：视觉结构合法性，例如 heap、union-find forest、BST、拓扑序、凸包。
- Algorithm：算法族转移，例如不同路径 DP、BFS 距离、二分窗口、KMP 前缀函数、LCS、编辑距离。

当前重点规则：

- 小规模 DP 表更新单元不超过 80 时必须逐帧记录，不能抽样跳到最终格。
- 不同路径必须记录每个内部 `dp[i][j]` 的 `set` 事件。
- 每个 `set` 状态必须满足对应算法转移。

### 6.5 Scene 校验

位置：`algolab/verification/scene_validator.py`

检查：

- frame 非空。
- mark 指向存在对象。
- arrow source/target 存在。
- 页面至少有可渲染内容。

### 6.6 Release Gate

位置：`algolab/verification/release_gate.py`

只有以下条件满足时才发布：

- artifact ready。
- trace ready。
- process ready。
- visual ready。
- 无 blocking error。

## 7. 渲染系统

### 稳定 HTML Runtime

位置：`algolab/renderer/export.py`

输出单文件 HTML，支持：

- 时间线逐帧播放。
- 上一步 / 下一步 / 播放。
- 输入、输出、状态、代码、校验证据。
- array / matrix / graph / stack / queue / map / tree / heap / trie / union_find / recursion_tree / string / geometry / ML primitives。

### Creative Runtime

位置：`algolab/renderer/creative.py`

用途：

- 只消费已通过校验的 artifact。
- 提供更强表现形式。
- 不参与正确性判定。

### Spatial / Visual Plan

相关文件：

- `algolab/generation/prompts/visual_plan_system.txt`
- `algolab/verification/visual_plan_validator.py`
- `algolab/renderer/spatial_runtime.py`

VisualPlan 只能选择高层展示目标，不能改变 trace、状态或算法结果。

## 8. 支持的视觉形态

| 视觉形态 | 代表算法 |
|---|---|
| array + pointer | 二分、双指针、滑动窗口、排序 |
| matrix / DP table | 不同路径、背包、LCS、编辑距离 |
| graph | BFS、DFS、拓扑排序、基础最短路 |
| stack / queue / deque | 单调栈、BFS frontier、滑窗候选 |
| map / hash table | Two Sum、频次统计 |
| tree | 二叉树、BST、LCA |
| heap | TopK、堆排序、Huffman |
| trie | 前缀树插入和查询 |
| union-find | 连通分量、路径压缩 |
| recursion_tree | 全排列、组合、搜索树 |
| string | KMP、Rabin-Karp、Manacher |
| geometry | 凸包、扫描线、点线面 |
| ML primitives | 参数、梯度、loss curve、decision boundary |

## 9. LLM 配置

位置：`llm_client.py`

读取顺序：

1. 环境变量：
   - `ALGOLAB_LLM_BASE_URL`
   - `ALGOLAB_LLM_API_KEY`
   - `ALGOLAB_LLM_MODEL`
   - `ALGOLAB_LLM_TIMEOUT_S`
   - `ALGOLAB_LLM_MAX_TOKENS`
   - `ALGOLAB_LLM_JSON_RETRIES`
2. 本地配置文件：
   - `api_settings.json`
   - `api_settings.yaml`
   - `api_settings.yml`
   - `.algolab_api_settings.json`
   - `.algolab_api_settings.yaml`
   - `.algolab_api_settings.yml`

这些配置文件已加入 `.gitignore`，不要提交密钥。

## 10. Benchmark 和 Dashboard

确定性 benchmark：

- 文件：`tests/benchmark_cases.py`
- 用途：不调用 LLM，验证 pipeline、validator、compiler、renderer 稳定性。

LLM benchmark：

- 文件：`scripts/run_llm_benchmark.py`
- 用途：调用模型生成真实产物，记录成功率和失败分类。

Dashboard：

- 文件：`scripts/build_demo_dashboard.py`
- 输出：`output/dashboard/index.html`
- 用途：展示确定性 demo、校验信息、artifact 链接和 HTML 产物。

## 11. 质量检查

快速离线回归：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
```

Benchmark 回归：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

浏览器 smoke：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.browser_smoke
```

全部本地检查：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

这些检查验证系统边界，不等价于证明任意未知题的 LLM 输出永远正确。

## 12. 常见问题

### 为什么页面里只有少数几帧？

通常不是播放器问题，而是 `trace(input_data)` 只生成了少数 events。检查：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("output/algolab.json").read_text())
for v in data["variants"]:
    print(v["name"], len(v["trace"]["events"]))
PY
```

对小规模 DP，系统已要求逐单元 `set`，如果生成稀疏 trace，会被 process validator 拦截并进入 repair。

### 为什么 Gradio 报 `/tmp/gradio` 权限错误？

已在 `app.py` 中把 `GRADIO_TEMP_DIR` 固定到：

```text
.gradio_cache/
```

如果目录权限异常：

```bash
chmod -R u+rwX,g+rwX .gradio_cache
```

### 静态 dashboard 和 Gradio 页面有什么区别？

Gradio 页面是动态生成入口，会调用 LLM。

静态 dashboard 是已构建好的确定性 demo 页面，不需要 LLM，不需要 Gradio 服务。

### 什么时候扩展 renderer？

只有出现新的视觉形态时才扩展 renderer。新增同一形态内的算法，优先：

1. 复用固定 semantic op。
2. 复用已有 state key。
3. 增加 process invariant。
4. 增加 fixture / benchmark case。

## 13. 当前边界

系统能强保证：

- LLM 不直接生成页面。
- 生成代码在 sandbox 中执行。
- trace 使用当前严格 `SemanticTrace` 协议；旧字段和旧 map target 不再走兼容路径。
- 已覆盖算法族的关键状态转移会被 process invariant 校验。
- 通过 release gate 的 artifact 才进入 HTML。

系统不能完全保证：

- 任意未知算法题一次生成就正确。
- LLM 生成的 verifier 永远独立且无同错。
- 大规模图、几何、搜索树布局永远清晰。

因此，新的算法族上线前必须补 deterministic case 和回归测试。
