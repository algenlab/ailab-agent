# 系统架构

## 1. 文档定位

本文档记录当前代码真实运行的 AlgoLab 架构，不描述尚未实现的理想系统。

当前系统仍处在实验驱动优化阶段。短期目标不是把所有算法题都做成最终产品，而是在公平实验口径下提升并证明以下指标：

- 答案正确：`solve`、`trace.result`、`verify`、expected / oracle 一致。
- 步骤正确：trace 的状态转移、依赖、覆盖率和算法族不变量通过校验。
- 过程解释可信：reason、teaching、deps、state、code_line 能支撑“这一步为什么正确”。
- 可视化效果：SceneGraph 能把语义对象稳定映射到页面对象、标记、依赖箭头和布局。
- 交互性：页面至少支持步进、播放、语义时间线、交互题、输入重生成 payload、解法切换和证据查看。

因此，本文档既是架构说明，也是后续优化和评估方法调整时的边界文件。

## 2. 当前主链路

真实主链路如下：

```text
app.py / cli.py
  -> ProblemInput
  -> build_artifact()
  -> generate_solution_spec()
  -> _try_materialize()
  -> execute_variant() / run_verifier()
  -> validate_trace()
  -> validate_process()
  -> validate_variant_demo_readiness()
  -> compile_scene()
  -> validate_scene()
  -> compute_release_gate()
  -> save_html()
  -> HTML + BuildArtifact JSON
```

失败修复路径如下：

```text
materialize errors
  -> build_repair_context()
  -> repair_solution_spec()
  -> _try_materialize()
  -> 最多重复 max_rounds 次
```

默认 benchmark 路径中 `max_rounds=2`。超过修复轮次仍失败时，主 pipeline 不发布正式页面。

## 3. 关键文件

入口：

- `app.py`：Gradio Web UI。
- `cli.py`：命令行入口。

数据结构：

- `algolab/schemas/input.py`：`ProblemInput`。
- `algolab/schemas/semantic_trace.py`：`SemanticTrace`、`SemanticEvent`、`SolutionVariant`。
- `algolab/schemas/scene_graph.py`：`SceneGraph`、`SceneFrame`、`SceneObject`。
- `algolab/schemas/validation.py`：`BuildArtifact`、`ValidationReport`、`ReleaseGate`。

生成与修复：

- `algolab/generation/solution_generator.py`：生成、修复、normalize、parse variants。
- `algolab/generation/prompts/tracker_system.txt`：主生成约束。
- `algolab/generation/prompts/repair_system.txt`：修复约束。
- `llm_client.py`：OpenAI-compatible LLM / VLM 调用与 usage 记录。

执行：

- `algolab/runtime/executor.py`：执行 solve / trace / verifier，做结果一致性校验和 trace materialization。
- `algolab/runtime/sandbox.py`：子进程沙箱执行生成代码。
- `algolab/runtime/tracer.py`：注入给 LLM tracker 使用的 `Tracer` API。

校验：

- `algolab/verification/trace_validator.py`：schema 之外的 target / deps / legacy 格式检查。
- `algolab/verification/process_validator.py`：算法族过程不变量入口。
- `algolab/verification/process_families/`：DP、图、字符串、树、区间、数学等族级规则。
- `algolab/verification/demo_readiness.py`：教学演示完整性检查。
- `algolab/verification/scene_validator.py`：SceneGraph 可渲染检查。
- `algolab/verification/release_gate.py`：发布门禁。

编译和渲染：

- `algolab/compiler/target_parser.py`：target id 解析。
- `algolab/compiler/scene_compiler.py`：SemanticTrace -> SceneGraph。
- `algolab/renderer/export.py`：单文件 HTML 生成。
- `algolab/renderer/panels.py`：页面固定面板结构。
- `algolab/renderer/layout_registry.py`：layout -> renderer 映射。
- `algolab/renderer/capabilities.py`：runtime 能力声明。

实验与报告：

- `scripts/run_llm_benchmark.py`：真实 LLM 生成实验。
- `scripts/run_direct_html_baseline.py`：LLM 直接生成 HTML baseline。
- `scripts/run_no_process_validator_ablation.py`：关闭 process validator 的消融。
- `scripts/run_no_scenegraph_compiler_ablation.py`：trace-only renderer 消融。
- `scripts/run_vlm_screenshot_eval.py`：VLM 截图评审。
- `scripts/build_evaluation_report.py`：综合评估报告。

## 4. 数据模型

### 4.1 ProblemInput

`ProblemInput` 是用户请求边界，包含：

- `problem`
- `input_data`
- `strategy_hint`
- `user_code`
- `expected_result`
- `solution_count`

它不生成代码、不校验算法、不参与页面布局。

### 4.2 Solution Spec

`generate_solution_spec()` 返回的是 LLM 原始候选的规范化 dict，不是最终产物。顶层主要字段：

```json
{
  "problem_title": "...",
  "input_contract": "...",
  "variants": [
    {
      "id": "...",
      "name": "...",
      "strategy": "...",
      "time_complexity": "...",
      "space_complexity": "...",
      "code": "def solve(input_data): ...",
      "tracker_code": "def trace(input_data): ..."
    }
  ],
  "verifier_code": "def verify(input_data): ..."
}
```

`normalize_solution_spec()` 只做轻量规范化：

- 顶层必须是 JSON object，list 会被包装成 `{"variants": list}`。
- `variants` 中只保留 dict。
- 缺省 `problem_title`、`input_contract`、`verifier_code` 会补为空值。

它不证明代码正确，也不保证 variant 数量一定等于请求数量。真正的正确性来自后续执行和校验。

### 4.3 SemanticTrace

`SemanticTrace` 是当前系统的核心中间表示，schema 在 `algolab/schemas/semantic_trace.py`。

顶层字段：

- `schema_version`，必须是 `semantic-trace-v1`。
- `algorithm`
- `input_data`
- `result`
- `pseudocode`
- `events`

事件字段：

- `step`
- `op`
- `targets`
- `value`
- `before`
- `after`
- `deps`
- `role`
- `reason`
- `state`
- `code_line`
- `interaction`
- `teaching`

当前 `SemanticEvent` 使用 Pydantic `extra="forbid"`，因此旧字段不会被吞掉或自动转换。特别是：

- 不接受旧字段 `type` 代替 `op`。
- 不接受旧字段 `target` 代替 `targets`。
- 不接受裸字符串 target，`targets` 和 `deps` 必须是 `{"id": "..."}`。
- 不自动补缺失的 `input_data`。
- 不自动修正旧式 map target，例如 `dist:A`、`seen:2`。

### 4.4 Tracer API

`Tracer` 是推荐 tracker 路径。LLM 生成的 `trace(input_data)` 应使用：

- `tracer.create()`
- `tracer.set()`
- `tracer.mark()`
- `tracer.unmark()`
- `tracer.move()`
- `tracer.compare()`
- `tracer.link()`
- `tracer.unlink()`
- `tracer.push()`
- `tracer.pop()`
- `tracer.enter()`
- `tracer.exit()`
- `tracer.explain()`
- `tracer.result()`
- `tracer.to_trace()`

`Tracer` 做的真实工作：

- 把 target / deps 字符串统一转成 `{"id": ...}`。
- 自动维护连续 step。
- 记录每类 target 的 update 数。
- 根据 `max_events` 和 `policy` 做抽样。
- 在最后一个事件的 state 中附加 `_trace_meta`，包括 raw event count、sampled、expected updates、recorded updates、coverage。

重要限制：

- `_trace_meta` 是 tracker 生成的元信息，不是不可伪造的形式化证明。
- `Tracer` 只能降低 schema 错误概率，不能替代 process validator。
- 大输入抽样会提高可读性，但可能损失步骤完整性；小规模关键过程仍应 full trace。

### 4.5 SceneGraph

`SceneGraph` 是 renderer-facing IR。当前 frame 字段包括：

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

`SceneGraph` 不执行算法，也不改变答案。它把 trace 中的 state、targets、deps、reason、teaching 编译成页面可以稳定消费的对象和证据。

### 4.6 BuildArtifact

`BuildArtifact` 是发布和实验报告的最终证据，包含：

- problem / input / expected / verifier result。
- materialized variants。
- 每个 variant 对应的 SceneGraph。
- validation report。
- 可选 correctness contract。
- 可选 visual plan / render report。

`save_html()` 会同时写：

- `*.html`
- 同名 `*.json` artifact

## 5. Materialization 顺序

`algolab/pipeline.py::_try_materialize()` 的真实顺序如下：

1. 如果 spec 有 `correctness_contract`，先做 contract schema / rule 校验。
2. 如果有 `verifier_code`，执行 `verify(input_data)`。
3. 对每个 `SolutionVariant`：
   - 执行 `solve(input_data)`。
   - 执行 `trace(input_data)`。
   - 校验 solve result、trace result、expected、verifier result 的一致性。
   - 校验 trace schema 和 target / deps。
   - 执行 process validator。
   - 执行 demo readiness。
   - 编译 SceneGraph。
   - 校验 SceneGraph。
   - 通过的 variant 放入 `good_variants`。
4. 如果多个 good variants，检查多解法结果一致。
5. 如果有 correctness contract 且已有 good variants，运行 contract test cases。
6. 汇总 demo readiness。
7. 计算 release gate。
8. 返回 `BuildArtifact` 和 errors。

这意味着当前系统的“发布”不是 LLM 生成成功就发布，而是只有 materialized variant 同时通过执行、校验、编译和 release gate 才能发布。

## 6. Release Gate 真实含义

`compute_release_gate()` 当前门禁逻辑：

- `artifact_ready`：至少有一个 good variant，且 scene 数量等于 variant 数量。
- `trace_ready`：至少有一个 good variant。
- `process_ready`：存在 verifier、expected，或多解法交叉校验条件。
- `visual_ready`：scene 数量等于 variant 数量，且大于 0。
- `multi_solution_ready`：variant 数量大于 1。
- `release_ready`：以上关键条件满足且没有 blocking errors。

注意：

- `process_ready` 这个字段名容易误解。它表示存在可用于结果交叉验证的证据，并不等同于所有算法族 process invariant 都强覆盖。
- 族级过程正确性主要来自 `validate_process()` 和 `process_families/`。
- 教学完整性来自 `validate_variant_demo_readiness()`。
- HTML 浏览器可打开性在 benchmark 的 browser smoke 中检查，不属于 `compute_release_gate()` 自身。

## 7. Target 与 State 边界

`target_parser.py` 当前支持：

- 一维 / 二维索引：`nums[3]`、`dp[1][2]`
- 切片：`nums[1:4]`
- map bracket：`dist[A]`、`seen[x]`
- 图节点 / 边：`node:A`、`edge:A->B`
- 指针：`pointer:left`
- 递归帧：`frame:dfs(2)`
- 几何点：`point:3`
- 字符：`char:x`
- 容器：`stack`、`queue`、`deque`、`heap`、`tree`、`trie`、`frames`、`points`、`string`
- 其它符号：作为 label / scalar symbol 处理

target 必须能被 state 或 input graph/tree/points 支撑。典型规则：

- `nums[3]` 要求 state 中有 `nums` 且长度覆盖 index 3。
- `dp[1][2]` 要求 state 中有二维 `dp`。
- `dist[A]` 要求 state 中有 dict `dist` 且 key 能匹配。
- `node:A` 最好来自 state 的 `graph`、`tree`、`trie`、`union_find`、`geometry`，或 input graph。
- `edge:A->B` 必须能解析 source / target。

当前不建议引入新前缀，例如 `range:`、`number:`、`interval:`。如果确实需要，必须同步扩展 parser、trace validator、scene compiler、renderer 和测试。

## 8. Scene Compiler 真实职责

`scene_compiler.py` 主要做四类事情。

第一，从 `event.state` 生成对象：

- list -> array / stack / queue / deque / heap。
- matrix -> matrix cells。
- dict graph -> graph nodes / edges。
- dict map -> key-value labels。
- tree / segment_tree -> tree layout。
- recursion_tree / call_tree / search_tree -> recursion_tree layout。
- trie -> trie layout。
- union_find / dsu -> union_find forest。
- points / geometry -> geometry layout。
- text / pattern / s / t / string -> string layout。
- ML-like state -> ml layout。
- scalar -> label。

第二，从 event targets / deps 补充对象：

- node、edge、pointer、frame、point、char、slice、map、container、symbol。

第三，从 deps 到 targets 生成 dependency arrows：

- 普通依赖箭头。
- DP matrix 依赖会附加 `dp_dependency` / `formula_substitution`。
- 图节点 / 边相关依赖会附加 `graph_relax`。

第四，生成 frame evidence：

- 当前 operation。
- targets / deps / value / before / after。
- state diff / target diff。
- timeline phase / keyframe。
- process evidence。
- visual pattern summary。

这些 evidence 是页面“过程解释可信”的核心来源，但它们仍然是从 trace 和 state 推导出来的证据，不是额外执行算法。

## 9. Renderer 真实页面结构

当前单文件 HTML 不是自由页面，而是固定 runtime。`panels.py` 和 `export.py` 真实包含：

- 顶部标题、当前输出、当前解法、可信度 badge。
- 左侧题目描述、当前输入、输入编辑器、expected、解法列表、解法对比、输入重新生成 payload。
- 中间主画布、step title、operation、prev / play / next、range、counter、语义时间线。
- 右侧讲解、系统校验、本步证据、当前状态、交互、代码同步。
- Debug Drawer：raw validation report、raw state JSON、release gate、artifact JSON 下载。

交互现状：

- 支持步骤切换和播放。
- 支持 variant 切换和对比展示。
- 支持 choice / input / judge 三类 interaction。
- 支持 formula 展开和反馈来源展示。
- 支持静态 HTML 生成“重新走 pipeline 的 payload”，但不会在前端伪造新 trace。

renderer 不能做：

- 不能修改算法结果。
- 不能执行 LLM 代码。
- 不能修复 trace。
- 不能把 validation fail 的产物包装成 release-ready。

## 10. 实验脚本与当前口径问题

当前已有实验入口覆盖：

- full pipeline：`scripts/run_llm_benchmark.py`
- direct HTML baseline：`scripts/run_direct_html_baseline.py`
- no process validator：`scripts/run_no_process_validator_ablation.py`
- no SceneGraph compiler：`scripts/run_no_scenegraph_compiler_ablation.py`
- no repair：通过 `run_llm_benchmark.py --max-rounds 0`
- unseen cases：`--case-set unseen`
- VLM screenshots：`scripts/run_vlm_screenshot_eval.py`

需要注意当前口径差异：

- `direct_html_baseline` 目前主要检查 HTML 结构和浏览器 smoke，不具备与 full pipeline 等价的 answer/process/demo gate。
- `no_process_validator` 和 `no_scenegraph_compiler` 当前会重新调用 LLM，不是严格 paired ablation。
- VLM 分数只能作为视觉教学质量辅助，不能替代 expected / oracle / process validator。
- `browser_smoke_pass_rate` 不能等价于 `verified_release_pass_rate`。

因此后续报告必须拆开：

- `answer_pass_rate`
- `process_pass_rate`
- `demo_readiness_pass_rate`
- `scene_pass_rate`
- `browser_smoke_pass_rate`
- `interaction_pass_rate`
- `final_release_pass_rate`
- `vlm_teaching_quality`
- `token_per_success`
- `duration_per_success`

## 11. 不可破坏边界

无论后续如何优化，都不应破坏以下边界：

- LLM 不直接进入主发布页面生成 HTML/CSS/JS。
- Renderer 只消费 `BuildArtifact` / `SceneGraph`。
- SemanticTrace 不恢复旧字段兼容。
- 不为提高 pass rate 放宽 validator。
- 不删除失败 case 或隐藏 failure type。
- 不把 VLM 评分当作算法正确性。
- 不把 browser smoke 当作 final release correctness。

当前系统的价值在于可审计、可拒绝错误、可复现实验。后续优化应提高这些能力下的通过率，而不是绕开这些能力。
