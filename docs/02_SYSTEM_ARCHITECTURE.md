# 系统架构

## 1. 系统总图

AlgoLab 当前主链路：

```text
ProblemInput
  -> LLM 生成 solve / trace / verify
  -> sandbox 执行
  -> SemanticTrace
  -> validators
  -> SceneGraph
  -> renderer
  -> HTML + artifact JSON
```

文件级调用顺序以 `SYSTEM_OVERVIEW.md` 为准。本文档只记录 AI 开发时最需要遵守的架构边界。

## 2. 核心模块职责

### ProblemInput

位置：`algolab/schemas/input.py`

输入：

- 题目描述。
- JSON 输入。
- 可选 expected output。
- 可选解法提示。
- 可选用户代码。
- 解法数量。

输出：

- 标准化用户请求。

不能做：

- 不负责生成代码。
- 不负责校验算法正确性。
- 不负责页面布局。

### LLM Generator

位置：

- `algolab/generation/solution_generator.py`
- `algolab/generation/prompts/`
- `llm_client.py`

输入：

- ProblemInput。
- 生成 / repair prompt。

输出：

- `solve(input_data)`。
- `trace(input_data)`。
- `verify(input_data)`。
- 多个 SolutionVariant。
- 可选 correctness contract 和 visual plan。

不能做：

- 不能生成 HTML/CSS/JS 页面。
- 不能绕过 SemanticTrace。
- 不能假设未执行代码已经正确。

### Runtime / Sandbox

位置：

- `algolab/runtime/executor.py`
- `algolab/runtime/sandbox.py`
- `algolab/runtime/tracer.py`

输入：

- LLM 生成的 solve / trace / verify 代码。
- 当前 input_data。

输出：

- solve result。
- SemanticTrace dict。
- verifier result。

不能做：

- 不兼容旧 trace 字段。
- 不自动补缺失 input_data。
- 不自动把旧 target 改成新 target。
- 不理解前端布局。

### Validators

位置：`algolab/verification/`

输入：

- SemanticTrace。
- solve / trace / verify 结果。
- SceneGraph。
- correctness contract。

输出：

- trace validation。
- process validation。
- scene validation。
- release gate。

不能做：

- 不修复错误产物。
- 不渲染页面。
- 不替 LLM 猜测缺失步骤。

### Scene Compiler

位置：

- `algolab/compiler/target_parser.py`
- `algolab/compiler/scene_compiler.py`

输入：

- 通过基本校验的 SemanticTrace。

输出：

- SceneGraph。

不能做：

- 不执行算法。
- 不改变 trace result。
- 不读取 LLM 生成的 HTML。
- 不把旧格式 trace 当作合法输入。

### Renderer

位置：`algolab/renderer/`

输入：

- BuildArtifact。
- SceneGraph。

输出：

- 单文件中文 HTML。

不能做：

- 不理解具体算法题。
- 不执行 LLM 代码。
- 不修复算法错误。
- 不消费 SemanticTrace 以外的自由页面代码。

## 3. 数据流

主数据流：

```text
ProblemInput
  -> Solution Spec
  -> SolutionVariant
  -> SemanticTrace
  -> ValidationReport
  -> SceneGraph
  -> BuildArtifact
  -> HTML
```

关键原则：

- `SemanticTrace` 是算法过程的可信中间表示。
- `SceneGraph` 是 renderer 的唯一输入。
- `BuildArtifact` 是页面发布和 benchmark 记录的最终证据。

## 4. 运行时流程

正常路径：

```text
app.py / cli.py
  -> build_artifact()
  -> generate_solution_spec()
  -> execute_variant()
  -> validate_trace()
  -> validate_process()
  -> compile_scene()
  -> validate_scene()
  -> compute_release_gate()
  -> save_html()
```

失败修复路径：

```text
错误信息 + 原始输入 + 上一次 spec
  -> repair_solution_spec()
  -> 重新 materialize
  -> 再次执行和校验
```

默认 repair 最多 2 轮。超过修复轮次仍失败时，不发布页面。

## 5. 正确性门禁

发布前必须满足：

- `solve(input_data)` 可执行。
- `trace(input_data)` 可执行。
- `verify(input_data)` 可执行或给出明确失败信息。
- `trace.input_data == input_data`。
- `solve_result == trace.result`。
- 如果提供 expected，则 `solve_result == expected`。
- 如果 verifier 可执行，则 `solve_result == verifier_result`。
- trace schema 合法。
- process validator 无 blocking error。
- scene validator 无 blocking error。
- release gate 通过。

## 6. 渲染边界

Renderer 只负责把 SceneGraph 呈现成稳定页面。

Renderer 可以改：

- 面板布局。
- 时间线交互。
- 视觉样式。
- SceneObject 到 DOM 的映射。
- Debug Drawer 展示方式。

Renderer 不可以改：

- 算法结果。
- trace 事件顺序。
- validation 结论。
- target 语义。
- solve / trace / verify 代码。

## 7. 当前限制

当前系统是科研原型，存在以下边界：

- LLM tracker 对未知题目的算法正确性不能只靠本地测试完全证明。
- `_trace_meta` 仍放在 trace 事件 state 中，不是不可伪造的执行侧证明。
- 复杂图、递归树、线段树、几何等页面仍需更强布局。
- 页面美学和移动端适配需要截图回归。
- benchmark 仍需扩展到更多题目、更多输入和更多失败分类。

这些限制不允许通过放宽校验或让 LLM 直接写页面来绕过。

## 8. 质量目标

系统优化优先级：

1. 正确性：错误结果和错误过程不能发布。
2. 可验证性：失败原因可定位、可复跑。
3. 教学性：页面能解释当前步骤为什么正确。
4. 稳定性：同一 artifact 的 HTML 渲染可重复。
5. 可扩展性：新算法优先复用固定 op 和视觉原语。

