# AlgoLab 系统说明

本文档描述 `paper/ailab-agent` 当前代码实际运行的系统架构、数据流、产物、质量门禁和实验口径。需要理解项目时优先读本文档，再看源码、阶段文档和历史实验记录。

当前实现已经进入 DSL-era：AlgoLab 主链路不让 LLM 直接生成 HTML，也不要求 LLM 手写完整事件 JSON。LLM 的主职责是生成可执行 Python `solve(input_data)` 和使用 `TraceSession` DSL 的 `trace(input_data)`；系统在受限沙箱中执行二者，得到 `SemanticTrace`，再由确定性 compiler 编译为 `SceneGraph`，最后由固定中文 Web Runtime 导出单文件 HTML。

主链路还支持一个独立的 LLM teaching enrichment 阶段：在 solver、trace、process、demo 和 SceneGraph 编译通过后，系统把已验证 trace 的摘要交给 LLM，只允许补充 `SceneFrame.teaching` 和 `SceneFrame.interaction`。这个阶段不允许修改 trace 事实、算法状态、答案、targets、deps、object、mark、evidence 或 code_line；失败时只进入 warning，不作为核心 correctness gate。

当前代码还包含 Stage2 `Creative View` 展示层：它读取已经通过 release gate 的 `BuildArtifact`，由 LLM 只生成主视图 stage 资产，固定 Creative Shell 继续复用 Stage1 的代码、伪代码、讲解、证据、交互和状态面板。Stage2 可以用 Playwright 和可选 VLM 做视觉质量门禁与修复，但它仍是展示质量实验，不是算法 correctness 来源。

一句话概括：

```text
LLM 生成可执行算法与 DSL 追踪代码
  -> 系统执行并校验答案和 trace
  -> 确定性编译为 SceneGraph
  -> 可选 LLM 只补教学 overlay
  -> 固定 renderer 输出交互页面
  -> benchmark / browser / audit 记录证据
```

本文档只描述当前代码事实。实验性 `Direct Visual Renderer / Creative View` 会在专门章节说明，它是 verified artifact 之后的展示层，不是 AlgoLab 主 release gate 的 correctness 来源。

## 0. 快速阅读路线

如果只想理解系统，按这个顺序读代码：

1. `app.py` / `cli.py`：用户入口如何构造 `ProblemInput`。
2. `algolab/pipeline.py`：主构建链路、repair loop、release gate 的真实顺序。
3. `algolab/generation/prompts/tracker_system.txt`：LLM solution spec 的硬约束。
4. `algolab/runtime/dsl.py`、`algolab/runtime/executor.py`、`algolab/runtime/sandbox.py`：生成代码如何被执行并 materialize 为 trace。
5. `algolab/verification/*`：trace、process、demo、scene、contract、release gate 的边界。
6. `algolab/compiler/scene_compiler.py`：`SemanticTrace -> SceneGraph`。
7. `algolab/renderer/export.py`：`BuildArtifact -> HTML + JSON`。
8. `scripts/run_llm_benchmark.py` 和 `scripts/run_direct_html_baseline.py`：论文实验的真实执行入口。
9. `algolab/generation/direct_visual_renderer.py`、`algolab/renderer/creative_direct.py`、`scripts/run_creative_visual_benchmark.py`、`scripts/creative_quality_gate.py`：Stage2 Creative View 生成、shell 组装、浏览器/VLM 质量门禁和 repair loop。

最重要的边界：

- `SemanticTrace` 是算法过程事实层。
- `SceneGraph` 是渲染语义层。
- HTML 是 `BuildArtifact` 的浏览器投影，不是 correctness 来源。
- direct HTML baseline 和 Creative View 是外部对照/展示层，不进入 AlgoLab 主 release gate。

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
- LLM benchmark 支持 repair rounds、candidate regeneration、strict warning、browser smoke、family/gate-layer 过滤、deterministic/unseen case set。
- benchmark 和 evaluation 脚本会记录 condition、failure type、phase timing、candidate summary、model calls、token usage、browser smoke、release gate 等证据。
- direct HTML baseline、no-process-validator ablation、no-SceneGraph-compiler ablation、component teaching/interaction ablation 都有独立脚本；这些脚本的 condition 不能与 `algolab_full` 混用。
- Stage2 direct / creative visual renderer 是 verified artifact 后的实验性展示层。当前默认 `stage_shell` 模式：系统生成完整 Creative Shell，LLM 只生成 `<style>`、可选 `<template>` 和 `window.renderCreativeStage(ctx)`。shell 负责代码、伪代码、讲解、证据、交互、timeline、状态和答案面板，因此 Stage2 不重新生成 teaching / interaction。
- Stage2 Creative View 可以启用统一 Creative Quality gate：Playwright 检查页面加载、主视图非空、切帧、trace/result 未被修改、overlap/clipping/text occlusion；可选 VLM 结合截图和题目描述评估场景显著性、算法状态可读性和是否为通用算法图。失败时仅影响 creative report / fallback，不影响主 `algolab_full` release gate。

最近架构变化：

- `algolab/runtime/dsl.py` 是当前主追踪 API。
- `algolab/runtime/tracer.py` 旧 `Tracer` 仍存在，但 prompt 明确要求优先使用 `TraceSession`，不要回退到旧 API。
- `algolab/verification/process_families/*` 已删除。
- `process_validator.py` 保留外部 API，但当前是 DSL-era 轻量 sanity 层；算法族级 5500+ 行手写 invariant 不再维护。
- family/process 报告仍保留 strong/fallback/uncovered 等 registry 口径，用于报告边界和降级说明。
- direct HTML baseline 新增 `--hide-expected` 公平模式和 `audit_direct_html_answer.py` 答案审计。
- 系统不再设置 trace 总帧数 / `max_events` 限制；`TraceSession` 和兼容 `Tracer` 都完整保留事件序列。当前只保留单步 `state` 大小保护，避免单帧携带超大对象。
- teaching enrichment 默认最多把 30 个关键 trace frames 给 LLM；完整 trace 仍保存在 artifact 中用于审计。首轮 enrichment 失败时会自动用 3 帧摘要降级重试，并以 warning 形式记录，不阻塞核心 artifact 生成。
- `correctness_contract` 相关 schema 和 validator 已存在，但当前主 prompt 不要求 solution spec 输出该字段；它是额外 correctness 证据扩展，不是主链路必需条件。
- `VisualPlan` / creative renderer 相关代码仍保留，但主 `save_html()` 的稳定页面由 deterministic renderer 生成；Stage2 Creative View 由独立 benchmark 脚本在 verified artifact 之后运行。

## 3. 主链路总览

```text
BenchmarkCase / Web / CLI
  -> ProblemInput
  -> generate_solution_spec()
  -> LLM solution spec
  -> normalize_solution_spec()
  -> optional validate_contract()
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
  -> 系统校验 answer / verifier / trace / demo / scene evidence
  -> 编译为 SceneGraph
  -> 可选 LLM 只补充讲解和交互
  -> 导出 HTML
  -> browser smoke 只检查页面可运行性
```

主链路失败时有两种修复层：

```text
pipeline.build_artifact()
  -> max_rounds 内调用 repair_solution_spec()

scripts/run_llm_benchmark.py
  -> build_artifact_timed()
  -> max_candidates 个独立候选
  -> 每个候选各自执行 max_rounds 轮 repair
  -> 记录 first_try / repair / regen_first_try / regen_repair
```

因此论文或 report 中的“repair 成功率”应以 benchmark report 的 `candidate_selection` 和 `repair_failure_summary` 为准，而不是只看 `pipeline.build_artifact()` 的默认行为。

## 4. 入口

### Web UI

文件：`app.py`

启动：

```bash
cd .
python3 app.py
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
python3 cli.py \
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
python3 cli.py --no-teaching-enrichment ...
```

### LLM Benchmark

文件：`scripts/run_llm_benchmark.py`

用途：调用真实模型，跑 benchmark cases，输出 `llm_benchmark_report.json/md`。

它不缓存模型输出。每个 task 都会重新调用 `generate_solution_spec()`，再进入 materialize/repair/export/report。

关键字段：

- `ok`：由 `artifact.validation.release_gate.release_ready` 和 strict warning 决定。
- `release_gate`：每条样例的机器发布门。
- `checks` / `warnings` / `errors`：构建过程证据。
- `phase_timings`：generate、materialize、repair、render 等阶段耗时。
- `model_calls`：模型调用与 token 信息。
- `candidate_summary`：first try、repair、regeneration、materialize attempts 等候选选择信息。
- `repair_failure_types`：进入 repair 的失败类型。
- `html` / `json`：导出的 HTML 和 artifact JSON。

常用参数：

```text
--case / --family / --gate-layer
--case-set deterministic|unseen
--sample / --all-samples
--solutions
--max-rounds
--max-candidates
--timeout-s
--strict-warnings / --no-strict-warnings
--browser-smoke
--teaching-enrichment / --no-teaching-enrichment
--concurrency
```

`strict_warnings=True` 时，任何 artifact warning 都会被 benchmark 判为失败，即使 `release_gate.release_ready=True`。这用于论文级严格口径；调试时可以关闭。

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
python3 scripts/run_direct_html_baseline.py \
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

模块责任边界：

| 层 | 主要文件 | 责任 | 不负责 |
|---|---|---|---|
| 请求层 | `app.py`, `cli.py`, `scripts/run_llm_benchmark.py` | 读取题目、输入、expected、实验参数，构造 `ProblemInput` | 算法正确性和渲染逻辑 |
| 生成层 | `solution_generator.py`, `tracker_system.txt`, `repair_system.txt` | 调用 LLM 生成/修复 solver 和 tracker spec | 发布产物、页面、最终 correctness 结论 |
| 执行层 | `executor.py`, `sandbox.py`, `dsl_guard.py`, `dsl.py` | 执行 `solve/trace/verify`，生成 `SemanticTrace`，检查结果一致性 | 视觉布局和教学评分 |
| 校验层 | `trace_validator.py`, `process_validator.py`, `demo_readiness.py`, `scene_validator.py`, `release_gate.py` | 将错误转成可审计 gate、warning、failure type | 让错误产物通过 |
| 编译层 | `scene_compiler.py`, `object_resolver.py`, `target_parser.py` | 把 trace state/targets/deps 编译成 SceneGraph 对象、标记、证据 | 重新理解或改写算法 |
| 教学增强 | `teaching_enricher.py` | 只读 trace 摘要，补充 frame teaching/interaction overlay | 修改 trace、state、answer、object、evidence |
| 渲染层 | `renderer/export.py`, `panels.py`, `runtime_shell.py`, `spatial_runtime.py` | 输出固定单文件中文 HTML 和 artifact JSON | 判断答案正确 |
| 实验层 | `scripts/*benchmark*.py`, `scripts/*audit*.py`, `tests/*` | 跑 deterministic / LLM / baseline / ablation / browser / VLM 证据 | 改 benchmark expected 或隐藏失败 |

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

实现细节：

- 上述“只允许字段”是 `tracker_system.txt` 对 LLM 的 prompt 契约。
- `normalize_solution_spec()` 负责容错规范化：顶层必须是 JSON object，list 会被包装为 `{"variants": list}`；`variants` 中只保留 dict；缺失的 `problem_title`、`input_contract`、`verifier_code` 会补默认值。
- `normalize_solution_spec()` 不会证明字段数量、variant 数量或代码正确性；真正阻塞失败的是后续 `parse_variants()`、sandbox execution、expected/verifier equivalence、trace/schema/demo/scene/release gate。
- `parse_variants()` 兼容旧字段 `trace_code`，会把它作为 `tracker_code` fallback；但 prompt 明确禁止新输出使用 `trace_code`。

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

### 6.10 CorrectnessContract

位置：

- `algolab/schemas/correctness.py`
- `algolab/verification/contract_validator.py`
- `algolab/generation/prompts/contract_system.txt`
- `algolab/generation/prompts/contract_repair_system.txt`

`CorrectnessContract` 是可选增强证据，不是当前主 prompt 的必需输出。它可以描述：

- `input_schema`
- `output_schema`
- `preconditions`
- `postconditions`
- `oracle_strategy`
- `oracle_code`
- `test_cases`
- `metamorphic_relations`
- `process_invariants`

如果 solution spec 中包含 `correctness_contract`，`pipeline._try_materialize()` 会先调用 `validate_contract()`，并在 good variants 生成后对 contract test cases 调用 `solve()` 重新执行测试。contract 错误会进入 `ValidationReport.errors`，从而阻塞 release gate。

当前论文实验应把它写成“可选 contract evidence”，不要写成所有 case 都依赖 contract。

### 6.11 VisualPlan / RenderReport

位置：

- `algolab/schemas/visual_plan.py`
- `algolab/schemas/render_report.py`
- `algolab/generation/solution_generator.py`
- `algolab/renderer/capabilities.py`

`VisualPlan` 用于表达高层视觉偏好，例如 mode、stage、camera、animation、teaching、layout preferences、baseline target。当前稳定主页面不依赖 LLM visual plan；`BuildArtifact.visual_plan` 和 `BuildArtifact.render_report` 是扩展字段，主要服务后续 creative / direct visual renderer 实验和 report。

主链路 renderer 仍以 `SceneGraph` 为输入，不能让 visual plan 修改答案、trace、state、release gate 或 validator 结论。

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
- `no_repair`
- `full / no_teaching / no_interaction / no_teaching_interaction`

`no_repair` 的实现方式是在 `scripts/run_llm_benchmark.py` 中使用 `--condition no_repair --max-rounds 0`，即主 pipeline 不做修复轮。注意 `--condition` 自身只写 report 标签；真实不同执行路径来自 `--max-rounds 0`。

`no_process_validator` 和 `no_scenegraph_compiler` 是独立脚本：

- `run_no_process_validator_ablation.py` 会 monkey patch `pipeline.validate_process` 和 `pipeline.process_degradation_for_trace`，保留其余主链路。
- `run_no_scenegraph_compiler_ablation.py` 会执行 solve/trace/verifier/trace/process/demo，但不调用 `compile_scene()`，而是输出 trace-only HTML。

从已成功的 `BuildArtifact` 派生 teaching / interaction 开关产物，不重新调用 LLM：

```bash
python3 scripts/export_component_ablation_artifacts.py \
  --artifact-dir output/stage1_verified_20cases_deepseek \
  --output-dir output/component_ablation_artifacts
```

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

### 12.5 Direct / Creative Visual Renderer

位置：

- `algolab/generation/direct_visual_renderer.py`
- `algolab/generation/prompts/direct_visual_stage_system.txt`
- `algolab/generation/prompts/direct_visual_stage_repair_system.txt`
- `algolab/renderer/creative_direct.py`
- `scripts/run_creative_visual_benchmark.py`
- `scripts/creative_quality_gate.py`
- `scripts/audit_creative_visual_renderer.py`
- `docs/13_LLM_DIRECT_VISUAL_RENDERER_DESIGN.md`

这是 verified artifact 后的展示层实验，不是主 correctness pipeline。

输入：

- 已经生成并通过主链路 release gate 的 `BuildArtifact` JSON。
- problem description、input、verified result、algorithm、pseudocode、trace summary、selected frames、state key summary、release gate。

`scripts/run_creative_visual_benchmark.py` 通过 `load_problem_map()` 优先从 `tests.benchmark_cases.benchmark_cases()` 读取 benchmark 原题描述；如果提供 `--problem-report`，会用 report 中的 `problem_description` / `problem` 补充或覆盖；仍然取不到时才退回 `artifact.problem_title`。因此 Stage2 prompt 中的 `Problem:` 字段可能是完整题目描述，也可能只是标题。当前 system prompt 明确要求：如果题目描述缺失或只有标题，LLM 必须基于题目标题、`ctx.input`、算法名、伪代码和 trace 自行选择合适的视觉隐喻；如果题目描述包含具体应用场景，主视图必须优先场景化，而不是只画通用数组、表格、时间轴或图结构。

两种生成模式：

- `full_html`：旧模式，LLM 生成完整 creative HTML，系统注入只读 artifact JSON。
- `stage_shell`：当前默认模式，系统提供确定性 Creative Shell，LLM 只输出 stage 资产：`<style id="creative-stage-style">`、可选 `<template id="creative-stage-template">`、以及定义 `window.renderCreativeStage(ctx)` 的 `<script>`。

`stage_shell` 的运行时边界：

- shell 由 `algolab/renderer/creative_direct.py` 生成，负责完整页面外壳。
- LLM stage 只能向 `ctx.host` 绘制主视图。
- `ctx` 提供只读 `artifact`、`variant`、`scene`、`frame`、`frames`、`frameIndex`、`input`、`result`、`state`、`evidence`、`esc()`、`compact()` 和 `template`。
- 题目输入只读 `ctx.input`，验证答案只读 `ctx.result`。
- Stage2 不允许重新求解、修改 artifact、覆盖 trace/result/state/frames，也不允许生成 shell 面板。
- 代码、伪代码、讲解、本步证据、交互、当前状态、timeline、播放控件、答案和 release gate badge 均由 shell 从 verified artifact 渲染。
- 因此 Stage2 的 teaching / interaction 应复用 Stage1 artifact 中的 `SceneFrame.teaching` 和 `SceneFrame.interaction`；LLM creative stage 不重新生成这些内容。

关键边界：

- creative 页面只能读取注入的 verified artifact。
- sanitizer 会检查空 HTML、缺少 `<html>` / `<style>` / `<script>`、stage asset 合法性等基础结构。
- browser/layout audit 检查页面是否可打开、主画面是否非空、帧切换是否工作、trace/result 是否被修改。
- creative failure 使用 fallback，不影响主 `algolab_full` release gate。

Stage2 prompt 的场景化要求：

- `Problem` 被当作视觉设计规格，不只是标题。
- 如果 `Problem` 有具体应用故事，主视图必须可见地实例化该故事。
- 主视图至少出现 3 个来自题目描述的领域对象、标签或动作，并用 `data-scenario-role` 标记核心对象。
- 只在标题或角落写一个业务词不合格。
- 通用算法结构只能作为底层布局，必须映射到业务对象、空间、设备、角色或动作。
- 当前 prompt 内置典型映射：仓库 DP -> 货架通道/机器人/充电点/打包站；订单 two-sum -> 货位/拣货箱/订单缺口；会议 interval merge -> 会议室占用窗口；温室 daily temperatures -> 温室/温度预报/通风或遮阳策略；应急 Dijkstra -> 城市路口/道路耗时/救援车辆/调度队列。

Creative Quality gate：

- 入口：`scripts/creative_quality_gate.py`。
- Playwright 部分复用 `scripts/audit_creative_visual_renderer.py`，检查 page load、console/page errors、主视图非空、截图非空、range/切帧、trace mutation、stage overlap、permitted overlap、clipping 和 text occlusion。
- 可选 VLM 部分通过 `chat_vision_with_metadata()` 对截图和题目描述一起评估，不只看截图，也不只按美观评分。
- VLM 固定输出字段包括 `scenario_salience_score`、`algorithm_readability_score`、`is_generic_algorithm_visual`、`algorithm_state_visible`、`scenario_objects_visible`、`issues`、`repair_advice` 和 `confidence`。
- 默认阈值：`scenario_salience_score >= 3.5`，`algorithm_readability_score >= 3.0`；低于阈值或被判为 generic algorithm visual 会进入 soft failures。
- Playwright hard failures 和可选 VLM failures 合并为 `creative_quality_ok`，并计算 `creative_quality_score`，用于 repair loop 中选择更好的候选。

Repair loop：

- `--require-stage-visual-quality` 启用仅浏览器布局 gate；`--layout-repair-retries` 控制 stage-only 布局修复轮数。
- `--require-creative-quality` 启用统一 Creative Quality gate；`--creative-quality-vlm` 启用 VLM 场景评估；`--creative-quality-repair-retries` 控制统一质量修复轮数。
- repair prompt 会携带 compact failure report、上一版 stage assets、题目描述、input、verified result、trace summary、state key summary 和 selected frames。
- repair 仍然只允许输出 stage assets，不允许输出完整 HTML 或修改 artifact。
- 当前 repair 是 stage 级重生成，不是 AST/DOM patch；它可能提升场景感或布局分数，但不能保证每轮都精准修改失败 bbox。

产物：

- `html/`：生成或修复后的 creative HTML。
- `raw_llm/`：LLM 原始输出。
- `prompts/`：每个 case 的 Stage2 prompt。
- `audit/`：generation report、layout gate、creative quality gate、browser screenshots、VLM 结果。
- `creative_benchmark_report.json`：批次总报告，包含 `generation_model`、`render_mode`、creative/browser/strict/quality 汇总、repair attempts、token/latency 和逐 case errors。
- `case_metrics.csv` 与 `creative_benchmark_report.md`：便于表格化检查的摘要。

模型选择：

- `--model` 显式指定 Stage2 文本 LLM。
- 如果未指定，`resolve_generation_model()` 会优先从 `--problem-report` 或 `artifact_dir/llm_benchmark_report.json` 推断 Stage1 generation model，使 Stage2 默认与 Stage1 文本 LLM 对齐。
- VLM 默认模型来自 `llm_client.py` 的 `gemini-3-flash-preview`，也可用 `--vlm-model` 或 `ALGOLAB_VLM_MODEL` 覆盖。

论文中应把它写成“展示质量/视觉自由度实验”，不能把 creative view 的 browser pass 当成算法 correctness。

## 13. LLM 配置

位置：`llm_client.py`

`llm_client.py` 是 OpenAI-compatible API wrapper，当前被两类 LLM 阶段复用：

- `kind="generation"`：生成 solution spec / repair spec。
- `kind="teaching"`：根据已验证 trace digest 生成 teaching overlay。
- `kind="direct_visual"` / `kind="direct_visual_stage"`：Stage2 direct/creative visual 生成。
- `kind="direct_visual_repair"` / `kind="direct_visual_stage_repair"`：Stage2 creative repair。
- `kind="vlm_eval"`：Stage2 Creative Quality gate 的截图评审。

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

VLM 配置：

```text
VISION_MODEL = gemini-3-flash-preview
VISION_TIMEOUT_S = 600
VISION_MAX_TOKENS = 4096
```

VLM 使用同一套 `ALGOLAB_LLM_BASE_URL` / `ALGOLAB_LLM_API_KEY` 读取逻辑，并额外支持：

- `ALGOLAB_VLM_MODEL`
- `ALGOLAB_VLM_TIMEOUT_S`
- `ALGOLAB_VLM_MAX_TOKENS`

`chat_vision_with_metadata()` 对非 Gemini 模型走 OpenAI-compatible chat completion multimodal payload；如果模型名包含 `gemini`，当前代码会把 base URL 从 `/v1` 转成 `/v1beta`，调用 `models/{model}:generateContent` 原生 Gemini endpoint，并把图片作为 `inlineData` 发送。返回的 `usageMetadata` 会被转换为统一的 `prompt_tokens`、`completion_tokens`、`total_tokens` 字段，供 benchmark report 汇总。

## 14. 常用命令

所有 Python 命令使用项目指定解释器：

```bash
python3
```

快速回归：

```bash
python3 -m tests.offline_regression
```

Benchmark 回归：

```bash
python3 -m tests.benchmark_regression
```

Direct HTML answer audit 回归：

```bash
python3 -m tests.regression.direct_html_answer_audit
```

Baseline 回归：

```bash
python3 -m tests.regression.baseline_experiments
```

Teaching enrichment 回归：

```bash
python3 -m pytest tests/regression/teaching_enricher.py -q
```

全部本地检查：

```bash
python3 scripts/run_quality_checks.py
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
python3 - <<'PY'
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
python3 - <<'PY'
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

## 16. 论文实验口径

当前代码支持的论文主 claim 应写成有边界的机器可审计声明：

```text
AlgoLab decouples LLM generation, executable semantic tracing,
deterministic SceneGraph compilation, and browser rendering.
Correctness is enforced by answer/verifier equivalence, executable traces,
schema validators, demo/scene gates, and artifact-level release evidence.
```

推荐主实验条件：

- `algolab_full`：主系统，真实 LLM 生成 solver/tracker/verifier，经过完整 materialize、repair、SceneGraph、HTML、browser smoke。
- `algolab_full_no_teaching`：关闭 teaching enrichment，衡量 correctness 与教学 overlay 的分离。
- `algolab_full_teaching_30_keyframes`：默认 teaching overlay，统计 teaching frames、interaction frames、token、latency。
- `direct_html_no_expected`：公平 direct HTML baseline，expected 不给模型，只跑 browser smoke 和 answer audit。
- `stage2_creative_view` / `creative_stage_shell`：verified artifact 之后的展示增强条件，只评价 creative visual / scenario grounding / layout quality，不进入 answer correctness 或 release gate 分母。
- `no_repair`：`--max-rounds 0`，衡量 repair 的贡献。
- `no_process_validator`：关闭 process validator API，衡量 process 层 report/gate 贡献。
- `no_scenegraph_compiler`：trace-only HTML，衡量 SceneGraph compiler 和 fixed runtime 的贡献。

报告必须分层展示：

- generation / spec parse。
- solve execution。
- answer correctness。
- verifier consistency。
- trace schema。
- process/demo readiness。
- SceneGraph validity。
- browser smoke。
- teaching/interaction quality。
- Stage2 creative quality：browser layout、scenario salience、algorithm readability、generic visual flag、repair attempts。
- model calls、token、latency。
- failure phase / failure type。

禁止写法：

- 用 browser pass 代表算法 correctness。
- 用 VLM screenshot score 代表 correctness。
- 用 direct HTML answer audit 代表 trace/process/SceneGraph gate。
- 用 Stage2 Creative View 的 `creative_ok` / `creative_quality_ok` 代表算法 correctness。
- 把当前 DSL-era `process_validator` 写成每个算法族都有手写 invariant proof。
- 把 frozen benchmark 的 100% 通过率写成任意算法题 100% 保证。

## 17. 当前边界

系统能较强保证：

- LLM 不直接生成 AlgoLab 主链路页面。
- 生成代码在受限沙箱中执行。
- `solve`、`trace.result`、expected、verifier、多解法交叉的一致性会被检查。
- `SemanticTrace` 和 `SceneGraph` 有结构化 schema 与 validator。
- LLM teaching enrichment 只能写 SceneGraph 的 teaching/interaction overlay，不能改 trace 事实或答案。
- teaching enrichment 失败会降级为 warning，不会破坏核心 artifact 生成链路。
- 通过 release gate 的 artifact 才进入主链路 HTML 发布口径。
- direct HTML baseline 与 AlgoLab full pipeline 在 report 中保持不同 condition。
- Stage2 Creative View 只能在 verified artifact 之后运行；它可以提升题面场景化展示，并通过 Playwright/VLM 记录 visual quality 证据，但不改变 Stage1 artifact 的 correctness 状态。

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
- Stage2 repair loop 不能保证每轮都精准修复 browser audit 的具体 bbox；当前实现是 stage 资产级重生成，只能通过后续 gate 选择更优候选。

新的算法族上线前，需要补 deterministic case、DSL 使用样例、trace/scene/browser 回归，以及必要的 evaluation/report 口径。
