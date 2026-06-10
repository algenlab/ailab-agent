# AlgoLab 系统说明

本文档描述当前代码实际运行的系统架构、数据流、产物、质量门禁和实验口径。需要理解项目时优先读本文档，再看源码和各阶段历史文档。

当前实现已经进入 DSL-era：LLM 不再直接生成 HTML，也不再手写完整事件 JSON；LLM 生成可执行 Python `solve(input_data)` 和使用 `TraceSession` DSL 的 `trace(input_data)`，系统在沙箱中执行代码，得到 `SemanticTrace`，再编译为 `SceneGraph` 和单文件 HTML。

当前主链路还支持一个独立的 LLM teaching enrichment 阶段：在 `SemanticTrace`、process readiness 和 demo readiness 通过后，系统先用确定性编译器生成 `SceneGraph`，再把已经验证的 trace 摘要交给 LLM 只补充 `frame.teaching` 和 `frame.interaction`。这个阶段不允许修改 trace 事实、算法状态、答案、targets、deps 或 code_line。

## 1. 系统目标

AlgoLab 是一个可验证的算法可视化生成系统。

输入：

- LeetCode 风格题目描述。
- 本次可视化使用的具体 JSON 输入。
- 可选 expected output。
- 可选解法思路。
- 可选用户代码。
- 希望生成的解法数量。

输出：

- 可执行解法 `solve(input_data)`。
- 可执行追踪函数 `trace(input_data)`。
- 可选独立校验器 `verify(input_data)`。
- 机器可验的 `BuildArtifact` JSON。
- 单文件中文交互式 HTML 页面。

核心原则：

- LLM 不生成 AlgoLab 主链路 HTML/CSS/JS；它只在受控 JSON 阶段生成 solution spec，以及可选 teaching overlay。
- 系统真实执行 LLM 输出，错误产物不能发布。
- `SemanticTrace` 是算法过程语义层，`SceneGraph` 是渲染语义层。
- teaching overlay 只能增强 `SceneGraph` 的讲解和交互，不能改变 `SemanticTrace` 事实。
- Renderer 只消费 `BuildArtifact` / `SceneGraph`，不重新理解具体算法。
- direct HTML baseline 是外部实验，不进入 AlgoLab release gate。

## 2. 当前系统状态

主要能力：

- Web UI、CLI、LLM benchmark 共享 `ProblemInput -> BuildArtifact -> HTML` 主链路。
- `tracker_system.txt` 要求 LLM 输出 JSON：`problem_title`、`input_contract`、`verifier_code`、`variants`。
- 每个 variant 包含 `code` 和 `tracker_code`；`code` 定义 `solve(input_data)`，`tracker_code` 定义 `trace(input_data)`。
- `trace(input_data)` 使用沙箱注入的 `TraceSession` DSL，例如 `sess.array()`、`sess.table()`、`sess.graph()`、`arr[i] = x`、`sess.result(answer)`、`sess.to_trace()`。
- 沙箱会执行 `solve`、`trace`、可选 `verify`，并检查答案一致性。
- `TraceSession` 自动生成 `semantic-trace-v1`，包括 step、op、targets、deps、state、reason、teaching、interaction 等字段。
- `compile_scene()` 将 `SemanticTrace` 编译为 `scene-graph-v1`，生成 frame、object、mark、teaching 和 evidence。
- 可选 `enrich_scene_teaching()` 会在 `SceneGraph` 上叠加 LLM 生成的讲解和交互题；CLI 和 Web UI 默认开启，底层 `ProblemInput` 默认关闭，便于测试和批处理显式控制。
- `save_html()` 输出单文件 HTML，并同时写出完整 artifact JSON。
- benchmark 和 evaluation 脚本会记录 condition、failure type、phase timing、model calls、browser smoke、release gate 等证据。

最近架构变化：

- `algolab/runtime/dsl.py` 是当前主追踪 API。
- `algolab/runtime/tracer.py` 旧 `Tracer` 仍存在，但 prompt 明确要求优先使用 `TraceSession`，不要回退到旧 API。
- `algolab/verification/process_families/*` 已删除。
- `process_validator.py` 保留外部 API，但当前是 DSL-era 轻量 sanity 层；算法族级 5500+ 行手写 invariant 不再维护。
- family/process 报告仍保留 strong/fallback/uncovered 等 registry 口径，用于报告边界和降级说明。
- direct HTML baseline 新增 `--hide-expected` 公平模式和 `audit_direct_html_answer.py` 答案审计。
- 系统不再设置 trace 总帧数 / `max_events` 限制；`TraceSession` 和兼容 `Tracer` 都完整保留事件序列。当前只保留单步 `state` 大小保护，避免单帧携带超大对象。
- teaching enrichment 默认最多把 30 个关键 trace frames 给 LLM；完整 trace 仍保存在 artifact 中用于审计。首轮 enrichment 失败时会自动用 3 帧摘要降级重试，并以 warning 形式记录，不阻塞核心 artifact 生成。

## 3. 主链路总览

```text
BenchmarkCase / Web / CLI
  -> ProblemInput
  -> generate_solution_spec()
  -> LLM solution spec
  -> parse_variants()
  -> execute_variant()
       -> solve(input_data)
       -> DSL static guard
       -> trace(input_data)
  -> SemanticTrace
  -> validate_trace()
  -> validate_process()
  -> validate_variant_demo_readiness()
  -> compile_scene()
  -> enrich_scene_teaching()  [optional]
  -> validate_scene()
  -> contract tests / multi-solution checks
  -> compute_release_gate()
  -> BuildArtifact
  -> save_html()
  -> HTML + artifact JSON
  -> browser smoke
  -> benchmark / evaluation / release report
```

一句话版本：

```text
LLM 写可执行算法和 DSL trace
  -> 系统执行并生成 SemanticTrace
  -> 系统校验 trace / demo / scene / answer evidence
  -> 编译为 SceneGraph
  -> 可选 LLM 只补充讲解和交互
  -> 导出 HTML
  -> browser smoke 只检查页面可运行性
```

## 4. 入口

### Web UI

文件：`app.py`

启动：

```bash
cd /ssd1/liaokunpeng/paper/ailab-agent
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 app.py
```

默认端口：`7861`

Web UI 读取题目、输入、expected、解法数量，构造 `ProblemInput`，调用 `build_artifact()`，再用 `save_html()` 写出 `output/algolab.html` 和 `output/algolab.json`。

当前 Web UI 固定设置：

```text
teaching_enrichment = true
```

因此 Web UI 生成的页面会在 trace 校验后调用 LLM teaching enrichment；如果该阶段失败，主 artifact 仍会继续走 `validate_scene()` 和 release gate，只在 validation warnings 中记录教学增强失败原因。

### CLI

文件：`cli.py`

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 cli.py \
  --problem "LeetCode 62. 不同路径。机器人每次只能向下或向右移动，返回路径数。" \
  --input '{"m":3,"n":7}' \
  --expected '28' \
  --strategy "动态规划和组合数学" \
  --solutions 2 \
  --output output/unique_paths.html
```

CLI 和 Web UI 使用同一条 `build_artifact()` 主链路。

CLI 默认开启 teaching enrichment，可以用下面参数关闭：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 cli.py --no-teaching-enrichment ...
```

### LLM Benchmark

文件：`scripts/run_llm_benchmark.py`

用途：调用真实模型，跑 benchmark cases，输出 `llm_benchmark_report.json/md`。

关键字段：

- `ok`：由 `artifact.validation.release_gate.release_ready` 和 strict warning 决定。
- `release_gate`：每条样例的机器发布门。
- `checks` / `warnings` / `errors`：构建过程证据。
- `phase_timings`：generate、materialize、repair、render 等阶段耗时。
- `model_calls`：模型调用与 token 信息。
- `html` / `json`：导出的 HTML 和 artifact JSON。

### Direct HTML Baseline

文件：`scripts/run_direct_html_baseline.py`

这是外部 baseline，不经过 `SemanticTrace`、`SceneGraph`、process validator 或 release gate。它直接让 LLM 输出单文件 HTML。

默认模式：

```text
condition = direct_html_baseline
expected_visible_to_model = true
```

公平模式：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_direct_html_baseline.py \
  --hide-expected \
  --output-dir output/direct_html_no_expected
```

`--hide-expected` 后：

```text
condition = direct_html_no_expected
baseline = direct_html_no_expected
expected_visible_to_model = false
```

direct HTML prompt 要求页面包含 `#title`、`#counter`、`#canvas`、`#next`、`#answer`。静态 `validate_direct_html()` 当前只检查 `<html>`、`#title`、`#counter`、`#canvas`；browser smoke 检查页面能打开和核心 DOM 可见；最终答案正确性必须用 answer audit 单独统计。

## 5. 文件级调用顺序

```text
app.py / cli.py / scripts/run_llm_benchmark.py
  -> algolab/schemas/input.py
  -> algolab/pipeline.py
  -> algolab/generation/solution_generator.py
  -> llm_client.py
  -> algolab/generation/prompts/tracker_system.txt
  -> algolab/schemas/semantic_trace.py
  -> algolab/runtime/dsl.py
  -> algolab/runtime/dsl_guard.py
  -> algolab/runtime/executor.py
  -> algolab/runtime/sandbox.py
  -> algolab/verification/contract_validator.py
  -> algolab/verification/trace_validator.py
  -> algolab/verification/process_validator.py
  -> algolab/verification/demo_readiness.py
  -> algolab/compiler/object_resolver.py
  -> algolab/compiler/target_parser.py
  -> algolab/compiler/scene_compiler.py
  -> algolab/generation/teaching_enricher.py
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

## 6. 核心产物

### 6.1 ProblemInput

位置：`algolab/schemas/input.py`

用户级请求：

- `problem`
- `input_data`
- `strategy_hint`
- `user_code`
- `expected_result`
- `solution_count`
- `teaching_enrichment`
- `case_id` / `family_id` / `subfamily_id`

它回答：“这次要生成哪个题、哪个输入、几个解法？”

说明：

- `teaching_enrichment` 控制是否在 trace 校验后调用 LLM 生成讲解和交互增强。schema 默认值是 `False`，避免底层测试或离线批处理意外调用真实模型。
- Web UI、CLI 和 `scripts/run_llm_benchmark.py` 在构造 `ProblemInput` 时默认设置为 `True`；CLI / benchmark 支持 `--no-teaching-enrichment` 关闭。
- `case_id`、`family_id`、`subfamily_id` 是内部评测和结果等价归一化字段，不暴露给 LLM prompt。

### 6.2 LLM Solution Spec

位置：`algolab/generation/solution_generator.py`、`algolab/generation/prompts/tracker_system.txt`

LLM 输出 JSON，不是最终 artifact：

```json
{
  "problem_title": "...",
  "input_contract": "...",
  "verifier_code": "def verify(input_data): ...",
  "variants": [
    {
      "id": "v1",
      "name": "...",
      "strategy": "...",
      "time_complexity": "O(...)",
      "space_complexity": "O(...)",
      "code": "def solve(input_data): ...",
      "tracker_code": "def trace(input_data): ..."
    }
  ]
}
```

硬约束：

- 顶层只允许 `problem_title`、`input_contract`、`verifier_code`、`variants`。
- variant 只允许 `id`、`name`、`strategy`、`time_complexity`、`space_complexity`、`code`、`tracker_code`。
- 禁止输出 HTML、SceneGraph、events、metadata 等额外字段。
- `trace(input_data)` 内使用 `sess = TraceSession(...)`，基于 `sess.to_trace()` 返回，并在返回前补齐事件 `code_line`。

它回答：“模型给出的算法实现和可视化追踪实现是什么？”

### 6.3 SolutionVariant

位置：`algolab/schemas/semantic_trace.py`

单个解法：

- `code`：定义 `solve(input_data)`。
- `tracker_code`：定义 `trace(input_data)`。
- `result`：执行后填入。
- `trace`：执行后填入 `SemanticTrace`。

它回答：“这个解法执行后得到什么答案和什么过程轨迹？”

### 6.4 SemanticTrace

位置：`algolab/schemas/semantic_trace.py`

`trace(input_data)` 返回的机器语义轨迹：

- `schema_version = semantic-trace-v1`
- `algorithm`
- `input_data`
- `result`
- `pseudocode`
- `events`

每个 event 包含：

- `step`
- `op`
- `targets`
- `value` / `before` / `after`
- `deps`
- `role`
- `reason`
- `state`
- `code_line`
- `interaction`
- `teaching`

固定 op：

```text
create / set / mark / unmark / move / compare / link / unlink /
push / pop / enter / exit / explain
```

`SemanticTrace` 不描述布局，它描述算法过程。

它回答：“算法每一步做了什么、修改了什么、依赖了什么、为什么这么做？”

### 6.5 SceneGraph

位置：`algolab/schemas/scene_graph.py`

`compile_scene(trace)` 输出的渲染语义层：

- `schema_version = scene-graph-v1`
- `algorithm`
- `input_data`
- `result`
- `pseudocode`
- `frames`
- `compile_scene()` 保留完整 `frames`，但 `evidence.timeline.keyframe` 最多标记 50 个关键帧；超出的帧仍可播放，只在时间线/对比统计中作为普通帧。

每个 frame 包含：

- `step`
- `title`
- `description`
- `operation`
- `code_line`
- `objects`
- `marks`
- `state`
- `interaction`
- `teaching`
- `evidence`

常见 object 类型：

```text
container / cell / node / edge / pointer / label / arrow / callout /
tensor / batch / parameter / loss_curve / gradient_vector /
decision_boundary / training_epoch / prediction
```

`SceneGraph` 是 renderer 的主要输入。它回答：“每一步应该画哪些对象、哪些对象高亮、显示哪些教学与证据？”

### 6.6 LLM Teaching Enrichment

位置：`algolab/generation/teaching_enricher.py`

这是一个 SceneGraph overlay 阶段，不是 trace 生成阶段。它的目标是把“系统可发布但偏模板化的讲解”升级为“针对当前题目和当前步骤的讲解与交互题”。

调用位置：

```text
compile_scene(materialized.trace)
  -> enrich_scene_teaching(scene, materialized.trace, problem=request.problem, code=materialized.code, enabled=request.teaching_enrichment)
  -> validate_scene(scene)
```

核心约束：

- `SemanticTrace` 仍是事实来源。
- LLM 只允许输出 `{"frames":[...]}`。
- 每个输出 frame 顶层只允许 `step`、`teaching`、`interaction`。
- `teaching` 只允许 `what`、`why`、`formula`、`invariant`、`common_mistake`、`hint`。
- `interaction` 只允许 `type`、`prompt`、`options`、`answer`、`explanation`、`wrong_explanation`、`option_explanations`。
- LLM 不允许修改、复述或发明 `op`、`targets`、`deps`、`state`、`result`、`code_line`。
- overlay 应用时只写入 `SceneFrame.teaching` 和 `SceneFrame.interaction`，不会修改 trace、scene object、marks、evidence、state、operation 或答案。

prompt 位置：

```text
TEACHING_SYSTEM_PROMPT in algolab/generation/teaching_enricher.py
```

#### Trace digest

`build_trace_digest()` 会把已验证 trace 转成给 LLM 的紧凑摘要：

- `problem`
- `algorithm`
- `input_data`
- `result`
- `pseudocode`
- `code`
- `trace_summary.total_events`
- `trace_summary.selected_events`
- `frames`

每个 digest frame 包含：

- `step`
- `op`
- `targets`
- `deps`
- `role`
- `reason`
- `value` / `before` / `after`
- `code_line`
- `state`
- `state_diff`
- `prev_summary`
- `next_summary`

`state` 和大对象会被 `_compact_value()` 压缩，避免单个 prompt frame 携带过长内容；这只是 prompt 压缩，不会改变原始 trace 或 artifact。

#### 默认 30 关键帧行为

当前默认值：

```text
MAX_TEACHING_FRAMES = 30
```

含义：

- 默认 `select_teaching_events(trace)` 按事件打分选择最多 30 个关键帧。
- 默认 `build_trace_digest(trace)` 只把这 30 个关键帧放入 `digest["frames"]`。
- 如果当前 trace 本身少于 30 帧，则仍会完整发送这些帧。
- 完整 trace 不会被截断，仍保存在 `BuildArtifact.variants[].trace.events` 和 `SceneGraph.frames` 中。

显式传入 `max_frames` 时，可以覆盖默认预算：

```python
build_trace_digest(trace, max_frames=8)
enrich_scene_teaching(scene, trace, max_frames=6)
```

显式截断时的打分逻辑仍保留，用于压缩失败重试或特殊实验：

- 第 0 步加高分。
- 最后一步加高分。
- `role == "answer"`、target 类似 `answer`、state 里有 `answer` 的帧加高分。
- 重要 target，如 `answer`、`ans`、`result`、`dist`、`dp`、`parent`、`visited`、`path` 加分。
- 有 `before` / `after`、有 `deps`、op 是 `set/move/compare/link/unlink/push/pop` 的帧加分。
- 最终仍按原始 step 顺序返回，避免讲解顺序乱掉。

#### 失败降级

`enrich_scene_teaching()` 是 best-effort：

- `enabled=False` 时直接跳过。
- 默认首轮使用最多 30 个关键帧的 trace digest。
- 如果首轮 LLM 调用、JSON 解析或 schema 校验失败，会自动用 `RETRY_TEACHING_FRAMES = 3` 生成小摘要重试。
- 如果重试成功，只应用重试结果。
- 如果全部失败，返回 warning，例如 `teaching enrichment skipped: 30 frames: ... | 3 frames: ...`。
- pipeline 会把 warning 写入 `artifact.validation.warnings`，但不会把 teaching enrichment 失败作为核心 release gate 阻塞条件。

这意味着 AlgoLab 的 correctness/release 证据仍来自 solve/trace/scene/verifier 等确定性链路；LLM teaching enrichment 是可降级的教学增强层。

#### Sanitizer

LLM 输出进入 `TeachingOverlay` schema 前会被 sanitizer 处理：

- 丢弃 LLM 回显的 `op`、`targets`、`state`、`code_line` 等非 overlay 字段。
- 丢弃未知 teaching / interaction 字段。
- 如果 `option_explanations` 不是 dict，修复为空 dict。
- 如果 `interaction.type == "choice"` 且模型把 `answer` 写成数字下标，例如 `1`，并且 options 存在，则转换为对应 option 原文。
- 如果 choice interaction 没有 options，则不应用该 interaction，并返回 warning。

这个 sanitizer 的目的不是让 LLM 修改事实，而是把常见格式瑕疵修正到 renderer 可稳定消费的 overlay 形态。

#### Renderer 影响

Renderer 当前会优先使用 enriched teaching：

- `frameTitle(f)` 优先显示 `f.teaching.what`，没有时退回 `f.title`。
- `frameDescription(f)` 优先显示 `f.teaching.why`，没有时退回 `f.description`。
- `renderTeaching(f)` 展示当前步骤、为什么、公式/规则、常见错误、提示和状态变化摘要。
- `renderInteraction(f.interaction)` 展示 choice / judge / input 等交互题。

为了避免答案帧重复显示无意义的 `answer` 标记，`renderSemanticAnchorBand()` 在已有 answer badge 或 answer state 时会过滤 answer-like target；因此主视图左上角不会同时出现 answer badge 和“当前对象 answer”重复锚点。

#### 实验观察

早期全量 trace 模式下，`permutations` benchmark 首个样例有 38 个 trace events，完整发送给 LLM 后成功生成：

```text
frames = 38
teaching_frames = 38
interaction_frames = 7
```

该实验也暴露了全量 trace 的成本：LLM 调用耗时和 token 都会明显上升。因此当前默认改为最多 30 个关键帧；保留显式 `max_frames` 和 3 帧降级重试作为工程兜底。

### 6.7 ValidationReport

位置：`algolab/schemas/validation.py`

校验报告：

- `errors`
- `warnings`
- `checks`
- `degradations`
- `contract_validation`
- `contract_test_results`
- `demo_readiness`
- `release_gate`

它回答：“这次构建有哪些通过证据、失败原因、警告和降级边界？”

### 6.8 ReleaseGate

位置：`algolab/verification/release_gate.py`

字段：

- `artifact_ready`
- `process_ready`
- `trace_ready`
- `visual_ready`
- `multi_solution_ready`
- `release_ready`
- `blocking_reasons`

当前规则：

- `artifact_ready`：至少一个 good variant，且 scene 数等于 variant 数。
- `trace_ready`：至少一个 good variant。
- `process_ready`：有 expected、verifier 或多解法交叉校验。
- `visual_ready`：每个 good variant 都有 SceneGraph。
- `release_ready`：上述满足且没有 errors。

它回答：“这个 artifact 是否可作为主系统产物发布？”

### 6.9 BuildArtifact

位置：`algolab/schemas/validation.py`

最终机器证据包：

- `schema_version = algolab-build-v1`
- `problem_title`
- `input_contract`
- `input_data`
- `expected_result`
- `verifier_result`
- `variants`
- `scenes`
- `validation`
- `correctness_contract`
- `visual_plan`
- `render_report`

HTML 不是 correctness 的来源；HTML 是 `BuildArtifact` 的浏览器投影。真正的答案、trace、scene、校验和 release gate 证据都在 artifact JSON 中。

## 7. DSL Trace 机制

位置：`algolab/runtime/dsl.py`

`TraceSession` 让 LLM 写接近普通 Python 的算法代码，同时自动记录语义事件。

典型模板：

```python
def trace(input_data):
    sess = TraceSession(
        algorithm="不同路径",
        input_data=input_data,
        pseudocode=["初始化 DP 表", "逐格转移", "返回右下角"],
    )
    dp = sess.table("dp", [[0] * input_data["n"] for _ in range(input_data["m"])])
    # 赋值会自动 emit set 事件
    dp[0, 0] = 1
    # ...
    sess.result(answer)
    trace = sess.to_trace()
    for event in trace["events"]:
        if event.get("role") == "answer":
            event["code_line"] = 8
        elif event.get("op") == "set":
            event["code_line"] = 6
        else:
            event["code_line"] = 3
    return trace
```

核心对象：

- `ArrayObj`：一维数组。
- `StringObj`：字符串。
- `TableObj`：二维表 / DP 表。
- `ScalarObj`：标量变量。
- `MapObj` / `CounterObj`：映射和计数器。
- `PointerObj`：数组或结构上的指针。
- `HeapObj`、`StackObj`、`QueueObj`、`DequeObj`。
- `UnionFindObj`、`LinkedListObj`、`TrieObj`。
- `GraphObj`、`TreeObj`、`PointsObj`。
- `FenwickObj`、`SegmentTreeObj`、`FlowNetworkObj`、`IntervalObj`。

`TraceSession.to_trace()` 会：

- 如果没有 create 事件，补一个输入初始化事件。
- 如果设置了 `sess.result(answer)` 但没有 answer 事件，补一个 answer mark 事件。
- 重编号 `step`。
- 返回 `semantic-trace-v1` dict。

当前边界：

- DSL 保证事件结构和 state snapshot 由 API 产生，不等于数学正确性自动证明。
- `trace` 仍是模型生成代码，正常路径依赖沙箱执行和一致性校验；恶意代码不是生产级安全模型。
- 系统不再按总事件数压缩或采样；大 trace 会完整保留。可读性主要由 LLM 生成的事件密度和输入规模决定。
- SceneGraph 总帧数不截断，但时间线关键帧标记最多 50 个，避免长 trace 页面被关键帧标签淹没。
- `code_line` 不由 DSL 自动推断；tracker 必须按 `solve(input_data)` 的真实行号在返回前补齐，否则页面代码高亮只能降级显示。

## 8. Sandbox / Executor

位置：

- `algolab/runtime/sandbox.py`
- `algolab/runtime/executor.py`
- `algolab/runtime/dsl_guard.py`

沙箱执行流程：

```text
validate_code_safety(code)
  -> build_namespace()
  -> exec(code, restricted namespace)
  -> call solve / trace / verify
```

沙箱限制：

- 只允许白名单模块：`bisect`、`collections`、`copy`、`functools`、`heapq`、`itertools`、`json`、`math`。
- 拒绝危险 dunder 访问和构造。
- 注入 `TraceSession`、旧 `Tracer` 和 DSL 对象。
- 在子进程中执行生成代码。
- 单次 `solve` / `trace` / `verify` 执行默认 30s 超时。
- 执行前会用 `patch_trace_session_aliases()` 修复部分 `session` / `sess` 别名误用。

DSL static guard：

- `validate_dsl_method_usage()` 在执行 `tracker_code` 前运行。
- 它只分析由 `TraceSession(...)` 和 `sess.array()`、`sess.graph()` 等工厂方法产生的 DSL 对象。
- 如果模型调用了 DSL 白名单之外的方法或属性，会提前给出明确错误，而不是等沙箱执行触发普通 `AttributeError`。
- 普通 Python `list` / `dict` / 局部变量不受这个 guard 限制。

`execute_variant()` 检查：

```text
solve(input_data) 可执行
tracker_code 通过 DSL 静态方法检查
trace(input_data) 可执行且返回 dict
单步 state 大小合法
SemanticTrace.model_validate(raw_trace)
trace.input_data == input_data
solve_result == trace.result
```

执行细节：

- `trace` 缺失 `input_data` 时，executor 会补成本次输入后再校验。
- executor 会重编号 trace event 的 `step`。
- `_validate_trace_budget()` 名称沿用，但现在只检查单步 `state` 字符串长度是否超过 20000，不再检查事件数量。

pipeline 额外检查：

```text
solve_result == expected_result    如果 expected 存在
solve_result == verifier_result    如果 verifier 可执行且 expected 不冲突
多个 variant result 一致          如果有多个解法
```

## 9. 校验层

### 9.1 Contract Validator

位置：`algolab/verification/contract_validator.py`

如果 LLM 输出 `correctness_contract`，系统会校验 schema、postconditions、oracle strategy、test cases，并可对 good variants 运行 contract tests。

当前主 prompt 不强制输出 correctness contract；该能力保留为扩展正确性证据。

### 9.2 Trace Validator

位置：`algolab/verification/trace_validator.py`

检查：

- `schema_version` 必须是 `semantic-trace-v1`。
- event step 连续。
- target/deps 可解析。
- indexed/slice/map target 必须能从 state/input 推导到已知对象。
- 旧式 map target 被拒绝，例如 `seen:2`、`map:seen`。
- choice interaction 必须有 options。
- 没有 reason 会 warning。

推荐 target：

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

### 9.3 Process Validator

位置：`algolab/verification/process_validator.py`

当前是 DSL-era 轻量实现：

- 保留 `validate_process()`、`process_validation_registry()` 等 public API，兼容 pipeline、degradation、reports。
- 对已经通过 `SemanticTrace.model_validate()` 的 trace 返回 `([], [])`。
- registry 将主要算法族登记为 strong，用于报告和 family gate 口径。
- 这里的 strong 表示“统一由 DSL 执行约束覆盖”，不是旧版逐算法族重算 invariant。
- 不再维护旧版 `process_families/*` 的算法族重算 validator。

这意味着当前 process 层的实际强约束主要来自：

- DSL 对象自动记录 state mutation。
- runtime 的 solve/trace/result/expected/verifier 一致性。
- trace validator 的 target/reference 检查。
- scene compiler 的 evidence 和 scene validator。
- demo readiness 的通用阶段/状态/答案检查。

文档和论文里应避免把当前 `process_ready` 描述成“每个算法族均有手写 invariant 重算证明”。更准确的说法是：DSL-era 的 process API 仍保留，但 family-specific invariant 已折叠为 DSL 执行约束和通用语义检查。

### 9.4 Demo Readiness

位置：`algolab/verification/demo_readiness.py`

检查教学 demo 是否可用：

- 是否有 initialization / transition / answer 阶段。
- key event 是否有 reason。
- 非 enter/exit/explain 的关键事件是否有 state。
- 需要 deps 的事件是否提供 deps。
- 当前 family-specific demo checks 已简化，避免旧启发式误判 DSL trace。

### 9.5 Scene Validator

位置：`algolab/verification/scene_validator.py`

检查：

- `scene-graph-v1`。
- frames 非空。
- 每帧有可见 object。
- mark 指向的 object 是否存在。
- edge/arrow 的 source/target 是否存在。
- state 中节点与 scene object 是否明显不一致。

### 9.6 Degradation

位置：`algolab/verification/degradation.py`

降级类型：

- `answer_only`
- `schema_scene_only`
- `process_fallback`
- `process_uncovered`
- `demo_warn`

这些不会都自动阻塞；它们用于 report/debug evidence 中明确说明“这条证据链到哪一层为止”。

## 10. Scene 编译和渲染

### 10.1 Scene Compiler

位置：

- `algolab/compiler/object_resolver.py`
- `algolab/compiler/target_parser.py`
- `algolab/compiler/scene_compiler.py`

流程：

```text
SemanticEvent.state
  -> resolve state objects
  -> parse targets/deps
  -> create marks/arrows/callouts
  -> infer teaching fallback
  -> compute evidence/process summary/timeline
  -> SceneFrame
```

`object_resolver.py` 把常见 state 转成 object：

- list -> array / stack / queue / heap
- list[list] -> matrix
- dict -> map
- scalar -> label

`scene_compiler.py` 还会从 event 推导：

- title / description / operation。
- marks：current、answer、dependency 等。
- evidence：operation、targets、deps、before/after、changes、timeline、process。
- teaching：如果 event 没有 teaching，就从 reason/targets/deps 生成 fallback。

注意：`compile_scene()` 只使用 `SemanticTrace` 的确定性事实和系统 fallback 规则。LLM teaching enrichment 不在这里发生，而是在 pipeline 中 `compile_scene()` 返回之后，对已生成的 `SceneGraph` 做 overlay。

如果 enrichment 开启且成功：

- frame 原有系统 fallback teaching 会和 LLM teaching 合并，LLM 非空字段覆盖/补充对应键。
- frame interaction 会被 LLM interaction 替换或补充。
- frame 的 object、mark、state、evidence、operation、code_line 不会被 enrichment 修改。

### 10.2 Renderer / Export

位置：`algolab/renderer/export.py`

`save_html(artifact, output_path)` 输出：

```text
output_path.html
output_path.json
```

HTML 是单文件离线页面，嵌入 public artifact payload 和前端 runtime。页面包含：

- 标题和 summary。
- 解法 tab。
- 代码面板。
- 当前帧画布。
- 状态面板。
- 教学解释。
- 交互题。
- timeline / next / play 控件。
- debug / evidence drawer。
- release gate、contract tests、pipeline checks。

Renderer 支持稳定 2D runtime，也保留 spatial/creative 相关能力。VisualPlan 只能选择高层表现策略，不能改变算法结果、trace、state 或校验结论。

当前 renderer 对 teaching enrichment 的实际消费规则：

- 主标题 `#step-title` 使用 `frame.teaching.what`，没有时退回 `frame.title`。
- 主描述 `#step-desc` 使用 `frame.teaching.why`，没有时退回 `frame.description`。
- 右侧讲解栏直接读取 `frame.teaching`，不再重新调用 LLM。
- 右侧交互栏直接读取 `frame.interaction`。
- answer-like target 已有 answer badge 或 answer state 时，语义锚点区会过滤 `answer` / `ans` / `result`，避免主视图重复显示“当前对象 answer”。

## 11. Browser Smoke

位置：

- `scripts/run_llm_benchmark.py`
- `tests/browser_smoke.py`
- `scripts/run_browser_smoke_container.sh`

benchmark 内置的 `browser_smoke_html_paths()` 做轻量检查：

- HTML 能被 Chromium 打开。
- `#title` 有内容。
- `#counter` 包含 `/`。
- `#canvas` 有可见文本。
- 页面没有 console/page error。

完整 `tests/browser_smoke.py` 会检查更多 UI 行为，例如 frame 切换、SceneGraph 读取、debug evidence、交互不修改 trace 等。

注意：browser smoke 只证明页面可运行，不证明答案正确。主链路答案证据来自 `BuildArtifact.validation`，direct HTML baseline 的答案证据来自单独 answer audit。

## 12. Benchmark / Evaluation / Paper Artifacts

### 12.1 Deterministic Benchmark

位置：

- `tests/benchmark_cases.py`
- `tests/benchmark_families/*`
- `tests/offline_regression.py`
- `tests/benchmark_regression.py`

用途：

- 不调用 LLM。
- 验证 fixture、trace、scene、renderer、release/evaluation scripts。
- 覆盖 DP、图、栈队列、哈希、树、堆、Trie、并查集、递归、字符串、几何、range structure、数学位运算等形态。

### 12.2 LLM Benchmark

位置：`scripts/run_llm_benchmark.py`

用途：

- 调用真实模型生成 `BuildArtifact`。
- 支持 deterministic / unseen case sets。
- 支持 repair rounds。
- 支持 strict warnings、browser smoke、concurrency、family/gate layer 过滤。
- 输出 `llm_benchmark_report.json/md` 和 `family_summary.json`。

### 12.3 Baseline / Ablation

相关脚本：

- `scripts/run_direct_html_baseline.py`
- `scripts/run_no_process_validator_ablation.py`
- `scripts/run_no_scenegraph_compiler_ablation.py`
- `scripts/export_component_ablation_artifacts.py`
- `scripts/baseline_experiment_utils.py`

典型 conditions：

- `algolab_full`
- `direct_html_baseline`
- `direct_html_no_expected`
- `no_process_validator`
- `no_scenegraph_compiler`
- `full / no_teaching / no_interaction / no_teaching_interaction`

从已成功的 `BuildArtifact` 派生 teaching / interaction 开关产物，不重新调用 LLM：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/export_component_ablation_artifacts.py \
  --artifact-dir output/stage1_verified_20cases_deepseek \
  --output-dir output/component_ablation_artifacts
```
- `no_repair`

`build_evaluation_report.py` 会把 direct HTML 识别为 baseline，并将其排除在严格机器 correctness gate 聚合之外。

### 12.4 Direct HTML Answer Audit

位置：`scripts/audit_direct_html_answer.py`

用途：审计 direct HTML baseline 里“可见最终答案”是否与 expected 匹配。

流程：

```text
llm_benchmark_report.json
  -> 只取 ok=True 且有 html 的 result
  -> 读取 HTML
  -> 抽取 body 文本和 script 字符串
  -> 找“最终答案/输出/结果/final answer/result”等标签
  -> 解析 JSON/list/object/number/bool/string 候选答案
  -> canonical 对比 expected
  -> 输出 json/csv/md
```

状态：

- `answer_match`
- `answer_missing`
- `answer_mismatch`
- `html_missing`

指标：

- `total_results`：原 benchmark report 总条数。
- `browser_passed`：原 report 中 `ok=True` 条数。
- `audited_html`：实际审计的 HTML 数。
- `visible_answer_found_rate`：能找到可见答案的比例。
- `visible_answer_match_rate`：`answer_match / audited_html`。

旧 `direct_html_baseline` prompt 暴露 expected，所以它的 answer audit 只能说明“页面是否展示了与 expected 一致的答案”。公平 correctness 口径应使用 `direct_html_no_expected` 全量报告。

## 13. LLM 配置

位置：`llm_client.py`

`llm_client.py` 是 OpenAI-compatible API wrapper，当前被两类 LLM 阶段复用：

- `kind="generation"`：生成 solution spec / repair spec。
- `kind="teaching"`：根据已验证 trace digest 生成 teaching overlay。

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

运行时行为：

- `chat_json()` 要求模型返回 JSON object，并通过 `parse_json_content()` 解析。
- 如果返回 markdown fenced JSON 或文本中包含 JSON span，解析器会尝试提取。
- 如果 JSON 解析失败，会按 `ALGOLAB_LLM_JSON_RETRIES` 进行重试。
- API 层对 408/429/5xx、网关、rate limit 等错误按 `ALGOLAB_LLM_API_RETRIES` 重试。
- `record_model_call()` 会记录 kind、model、耗时和 token usage；benchmark / 实验脚本可用这些信息统计生成成本。

默认值：

```text
DEFAULT_MODEL = deepseek-v4-pro
DEFAULT_TIMEOUT_S = 900
DEFAULT_MAX_TOKENS = 32768
DEFAULT_JSON_RETRIES = 4
DEFAULT_API_RETRIES = 2
```

## 14. 常用命令

所有 Python 命令使用项目指定解释器：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3
```

快速回归：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
```

Benchmark 回归：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
```

Direct HTML answer audit 回归：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.direct_html_answer_audit
```

Baseline 回归：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.baseline_experiments
```

Teaching enrichment 回归：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest tests/regression/teaching_enricher.py -q
```

全部本地检查：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

浏览器 smoke 容器：

```bash
bash scripts/run_browser_smoke_container.sh
```

宿主机 glibc 2.17 不能直接运行 Playwright 自带 node 时，使用容器：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py
```

容器命令要求能访问 Docker daemon；脚本会优先使用普通 `docker`，失败后尝试 `sudo -n docker`。

Teaching enrichment 实验产物常见位置：

```text
output/teaching_overlay_visual_check/multi_case_llm/*.html
output/teaching_overlay_visual_check/multi_case_llm/*.json
output/teaching_overlay_visual_check/multi_case_llm/llm_teaching_report*.json
output/teaching_overlay_visual_check/multi_case_llm/screenshots/*.png
```

例如早期 full trace teaching enrichment 的 `permutations` 结果：

```text
output/teaching_overlay_visual_check/multi_case_llm/permutations.html
output/teaching_overlay_visual_check/multi_case_llm/permutations.json
output/teaching_overlay_visual_check/multi_case_llm/llm_teaching_report_permutations_all_frames.json
```

## 15. 常见问题

### 为什么页面只有少数几帧？

通常不是播放器问题。系统现在不按 `max_events` 压缩或采样 trace；如果页面只有少数帧，说明 `trace(input_data)` / tracker 本身只生成了少量事件，或 LLM 只记录了关键步骤。

检查 artifact：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("output/algolab.json").read_text())
for v in data["variants"]:
    print(v["name"], len(v["trace"]["events"]))
PY
```

### 为什么 LLM 讲解/交互没有覆盖所有步骤？

先区分两个层次：

- `SceneGraph` 每帧通常都会有系统 fallback teaching。
- LLM teaching enrichment 是 overlay，只会覆盖或补充模型返回的那些 `step`。

当前 prompt 要求 LLM 尽量为所有 frame 补充 teaching，但真实模型可能因为输出预算、JSON 完整性或题目复杂度只返回部分 frame。系统会应用返回的有效 overlay，未返回的 frame 保留 `compile_scene()` 的 fallback teaching。

如果要检查 LLM 实际返回/应用效果，看 artifact JSON：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("output/teaching_overlay_visual_check/multi_case_llm/permutations.json").read_text())
variant = data["variants"][0]
scene = data["scenes"][variant["id"]]
print("frames", len(scene["frames"]))
print("teaching_frames", sum(1 for f in scene["frames"] if (f.get("teaching") or {}).get("what") and (f.get("teaching") or {}).get("why")))
print("interaction_frames", sum(1 for f in scene["frames"] if f.get("interaction")))
PY
```

### 现在给 LLM 的关键帧最多是多少？

默认最多 30 个。`MAX_TEACHING_FRAMES = 30`，所以默认给 LLM 的 frame 数为：

```text
llm_teaching_frames = min(30, len(trace.events))
```

如果调用方显式传入 `max_frames`，会按该值选择最多 `max_frames` 个关键帧。默认 30 帧调用失败时，系统会用 3 帧摘要降级重试。

### 为什么全量 trace teaching enrichment 很慢？

全量 trace 会显著增加 prompt token 和模型输出 token。早期 `permutations` 首个样例 38 帧全量发送后可以成功，但真实调用耗时约 512 秒，且 token 用量明显高于摘要模式。

这是设计取舍：

- 30 个关键帧给 LLM 较完整的阶段上下文，同时避免大规模输入时 prompt 无上限增长。
- 代价是超长 trace 中未入选的普通帧只能使用系统默认讲解。
- 代码保留显式 `max_frames` 和 3 帧降级重试，便于后续在质量和成本之间重新调整。

### LLM teaching enrichment 失败会不会让 artifact 失败？

默认不会。它是 best-effort 教学增强层：

- 如果 enrichment 成功，pipeline checks 会出现“教学讲解/交互增强已应用”。
- 如果 enrichment 失败，会进入 validation warnings。
- release gate 的核心 correctness 仍由 solve/trace/expected/verifier/SceneGraph validator 等确定性证据决定。

### 为什么 browser pass 不能当 correctness？

browser smoke 检查 HTML 可运行和核心 DOM 可见。它不重新执行算法，不审计最终答案，也不证明教学过程语义正确。

主链路 correctness 要看 artifact 的 answer/verifier/trace/scene/release gate 证据。direct HTML baseline 没有这些中间产物，只能额外跑 `audit_direct_html_answer.py`。

### 为什么 direct HTML 需要 `--hide-expected`？

旧 `direct_html_baseline` prompt 把 expected 直接给了模型，存在答案泄漏。它可以用于观察“直接写 HTML 能否打开”，但不能作为公平答案正确性口径。`--hide-expected` 让模型自行求解，condition 变成 `direct_html_no_expected`，才适合做 direct HTML answer correctness。

### 什么时候扩展 renderer？

只有出现新的视觉形态时才扩展 renderer。新增同一形态内算法，优先：

1. 复用 `TraceSession` DSL 对象。
2. 复用固定 semantic op。
3. 复用已有 state key 和 object resolver。
4. 增加 deterministic case / benchmark case。
5. 必要时再扩展 scene compiler 或 renderer。

## 16. 当前边界

系统能较强保证：

- LLM 不直接生成 AlgoLab 主链路页面。
- 生成代码在受限沙箱中执行。
- `solve`、`trace.result`、expected、verifier、多解法交叉的一致性会被检查。
- `SemanticTrace` 和 `SceneGraph` 有结构化 schema 与 validator。
- LLM teaching enrichment 只能写 SceneGraph 的 teaching/interaction overlay，不能改 trace 事实或答案。
- teaching enrichment 失败会降级为 warning，不会破坏核心 artifact 生成链路。
- 通过 release gate 的 artifact 才进入主链路 HTML 发布口径。
- direct HTML baseline 与 AlgoLab full pipeline 在 report 中保持不同 condition。

系统不能完全保证：

- 任意未知算法题一次生成就正确。
- LLM 生成的 verifier 永远独立且无同错。
- 当前 DSL-era `process_validator` 不再做旧版每算法族重算 invariant。
- 系统可以完整保留 tracker 已生成的事件，但不能凭空补出 tracker 没记录的内部步骤。
- LLM teaching enrichment 可以改善讲解和交互，但不能证明讲解文字绝对教学最优，也不能替代 trace/verifier correctness。
- 默认 30-keyframe teaching enrichment 可限制 LLM prompt 增长；如果显式运行 full trace 压力消融，延迟和 token 成本仍可能很高，长 trace 下仍可能触发模型空返回、截断或降级重试。
- `code_line` 准确性主要依赖 LLM 按提示词在 tracker 返回前补齐；renderer 只能对缺失或越界行降级显示。
- browser smoke 或 VLM screenshot 分数能替代答案 correctness。
- direct HTML baseline 的 browser pass 能代表答案正确。

新的算法族上线前，需要补 deterministic case、DSL 使用样例、trace/scene/browser 回归，以及必要的 evaluation/report 口径。
