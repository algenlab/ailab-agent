# LLM Direct Visual Renderer 设计方案

## 1. 文档定位

本文档设计一个新增展示层：`LLM Direct Visual Renderer`，也可以称为 `Creative View`。

它的目标是解决当前 deterministic renderer 的一个核心限制：现有 renderer 能稳定、可验证地展示 trace，但视觉表达偏通用、偏规则化，很难根据任意算法题目的自然语言语义生成贴题画面。

典型例子：

```text
给定 n 个非负整数表示每个宽度为 1 的柱子的高度图，计算下雨之后能接多少雨水。
```

理想画面不应只是数组格子，而应是：

- 柱状高度图。
- 蓝色雨水填充。
- 左右边界或最大水位线。
- 当前处理位置。
- 当前格子蓄水量和累计答案。

如果为每类题都手写 renderer 规则，会退化成不断维护算法/视觉规则库。本文档选择另一条路线：保持当前 verified pipeline 不变，在其后新增一个 prompt-driven 的自由展示层。

## 2. 核心结论

新增双轨展示：

```text
Verified View:
  当前 SemanticTrace -> SceneGraph -> deterministic HTML renderer。
  负责 correctness、release gate、稳定可复现。

Creative View:
  Verified artifact -> LLM 生成专属 HTML/CSS/JS 可视化页面。
  负责根据题目语义生成更贴题、更灵活的界面。
```

关键边界：

```text
LLM Direct Visual Renderer 不负责算法正确性。
它只负责展示方式。
```

算法答案、trace、state、result、release gate 仍来自当前系统。

## 3. 为什么不是继续扩展 renderer 规则

当前系统已经有 `visual_pattern`、family renderer、SceneGraph validator、browser audit。这条路线适合做稳定的 certified view，但不适合追求无限题目语义的视觉自由。

如果继续手写 pattern，会遇到：

- 接雨水需要柱子和水。
- 最大矩形需要柱子、矩形面积、单调栈。
- N 皇后需要棋盘。
- 编辑距离需要二维网格和路径。
- 股票题需要价格曲线。
- 迷宫题需要网格路径。
- 拓扑排序需要 DAG 和入度。
- 凸包需要几何点集。

这些题目描述是开放集合，手写规则会不断膨胀。

因此 Creative View 不要求 renderer 预先知道所有视觉隐喻，而是让 LLM 基于题目描述和已验证 trace 自由生成展示代码。

## 4. “支持任意算法”的准确含义

同一套 prompt 理论上可以对任意算法题生成 Creative View，但这里必须区分三个层级：

```text
attempt:
  系统会对任意 verified artifact 尝试生成 Creative View。

creative_ok:
  LLM 生成的页面通过 browser smoke、截图非空、帧切换、trace 不变等展示层 audit。

guaranteed_correct_visualization:
  证明视觉中的每个像素/形状都和算法语义严格一致。
```

本方案追求的是：

```text
任意 verified artifact 都可以 attempt。
creative_ok 由 audit 判断。
失败自动 fallback 到 Verified View。
```

本方案不承诺：

```text
任意算法题都 guaranteed 生成完美 Creative View。
```

原因很简单：一旦允许 LLM 自由写视觉 HTML/CSS/JS，就不可能再用固定 validator 证明所有视觉隐喻都完全正确。否则又会回到规则库路线。

## 5. 为什么先做 5-10 个代表题

这里的 5-10 个代表题不是“能力只支持 5-10 题”，也不是为这些题写规则。

它只是工程 pilot / smoke stage：

```text
目的：
  验证同一套 prompt、同一套 sandbox、同一套 audit、同一套 fallback 是否跑得通。

不是目的：
  为每个代表题写专门规则。
```

推荐先选 5-10 个题，是因为这个模块有新的风险面：

- LLM 是否能稳定输出完整单文件 HTML。
- 页面是否有 JS error。
- 是否真的读取 trace frame。
- 是否能切换帧。
- 是否会把 trace/result 改掉。
- 是否能产生非空主画面。
- 是否比 Verified View 更贴题。
- 失败时 fallback 是否可靠。

pilot 通过后，直接用同一套 prompt 跑当前 71-case benchmark。

所以“先 5-10，再 71”不是扩展规则，而是分阶段验证：

```text
Phase A: 5-10 representative cases 验证机制。
Phase B: 71-case deterministic benchmark 评估成功率和 fallback rate。
```

最终实验口径应该是 71-case，而不是只报告 5-10 个 demo。

## 6. 总体架构

现有链路：

```text
ProblemInput
  -> build_artifact()
  -> BuildArtifact
  -> save_html()
  -> Verified View
```

新增链路：

```text
ProblemInput
  -> build_artifact()
  -> BuildArtifact with release_ready
  -> build_direct_visual_prompt(artifact)
  -> LLM generates creative HTML
  -> inject read-only artifact data
  -> sandbox browser audit
  -> Creative View or fallback Verified View
```

最终每个 case 可以有两个页面：

```text
llm_<case_id>_<sample>.html
llm_<case_id>_<sample>_creative.html
```

UI 上可以做两个 tab：

```text
Creative View
Verified View
```

默认策略：

```text
creative_ok == true:
  默认展示 Creative View，并保留 Verified View 切换。

creative_ok == false:
  默认展示 Verified View，并在 report 中记录 Creative View 失败原因。
```

## 7. 输入数据

LLM Direct Visual Renderer 的输入必须来自已验证 artifact。

允许输入：

```text
problem_title
problem_description
input_data
expected_result
result
algorithm
pseudocode
verified trace events summary
selected frames
state key summary
scene summary
release_gate
validation summary
```

不建议把完整巨大 trace 全部放进 prompt。更好的做法是：

```text
Prompt:
  给 LLM 题目、摘要、关键帧、state key、数据结构说明。

Runtime:
  把完整 artifact JSON 注入到生成页面中，让 renderFrame(index) 运行时读取。
```

这样可以避免长 trace prompt 爆炸，同时页面仍能按完整帧数播放。

## 8. Artifact 数据注入

Creative HTML 中嵌入只读数据：

```html
<script type="application/json" id="algolab-artifact">
  {...BuildArtifact JSON...}
</script>
```

LLM 生成的 JS 必须从该节点读取：

```javascript
function readArtifact() {
  const node = document.getElementById("algolab-artifact");
  return JSON.parse(node.textContent || "{}");
}

const ARTIFACT = Object.freeze(readArtifact());
```

页面必须实现：

```javascript
renderFrame(index)
goFrame(index)
nextFrame()
prevFrame()
```

页面必须包含：

```text
#app
#stage
#timeline or #range
#counter
#explanation
```

## 9. Prompt 设计

系统提示词核心：

```text
你是 AlgoLab 的 LLM Direct Visual Renderer。

你会收到一个已经通过验证的算法 artifact 摘要。
算法答案、trace、state、result、release gate 已经由系统验证。
你的任务只是在浏览器中生成一个贴合题目语义的可视化界面。

你必须输出完整单文件 HTML。
不要输出 markdown。
不要解释。

硬性限制：
1. 不要重新求解算法。
2. 不要修改、覆盖、伪造 result、trace、state、frames。
3. 所有动画步骤必须来自 artifact frames 或 trace events。
4. 可以根据题目语义自由选择视觉隐喻，例如雨水、棋盘、路径、柱状图、时间轴、图节点边。
5. 如果你派生展示元素，例如 rain water layer、area rectangle、price profit line，必须只用于展示，并在 DOM 或 JS metadata 中标记 derived_visual_only。
6. 不要调用网络。
7. 不要加载外部库。
8. 不要使用 localStorage、sessionStorage、cookie、fetch、XMLHttpRequest、WebSocket。
9. 页面必须有 prev/next/range 帧切换。
10. 页面必须能在没有任何外部资源的环境中运行。

输出要求：
- HTML 内必须有 <style> 和 <script>。
- 主视图必须非空。
- 每一帧必须调用 renderFrame(index) 渲染。
- 视觉元素必须尽量引用 frame.state、frame.evidence.targets、frame.evidence.deps、frame.operation、frame.description。
- 页面上必须显示 result，但不能把 result 当作新的计算结果。
```

用户 prompt 结构：

```text
Problem:
<problem title and description>

Input:
<compact input_data>

Result:
<verified result>

Algorithm:
<algorithm>

Pseudocode:
<pseudocode>

State keys:
<state key summary>

Trace summary:
total_events = ...
selected_frames = ...

Selected frame examples:
<first / middle / answer / high-change frames>

Artifact runtime contract:
The final HTML will contain a JSON script tag with id="algolab-artifact".
Your JS must parse it and render frames from it.

Now generate a complete single-file HTML creative visualization.
```

## 10. 输出格式

LLM 输出是完整 HTML：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>...</title>
  <style>...</style>
</head>
<body>
  <main id="app">
    ...
  </main>
  <script type="application/json" id="algolab-artifact">{...}</script>
  <script>
    ...
  </script>
</body>
</html>
```

系统需要做基本 sanitize：

```text
禁止外链 script/link/img/font。
禁止 fetch/XMLHttpRequest/WebSocket。
禁止 localStorage/sessionStorage/cookie。
禁止 iframe。
禁止 form submit。
禁止 window.open。
```

如果 sanitize 失败：

```text
creative_ok = false
fallback_used = true
```

## 11. 安全与隔离

Creative View 必须和主系统隔离。

推荐方式：

```html
<iframe sandbox="allow-scripts" src="...creative.html"></iframe>
```

不建议：

```text
sandbox="allow-same-origin"
```

本地文件实验阶段至少需要：

- 不允许外部网络。
- 不允许外链资源。
- 不允许访问 cookie/storage。
- 不允许修改 artifact JSON。
- Playwright 检查 frame 切换前后 artifact data 是否不变。

## 12. Audit 与验收

Creative View 不进入 correctness gate，只进入 visual/interaction quality gate。

case-level 指标：

```text
creative_attempted
creative_ok
fallback_used
sanitize_ok
page_load_ok
console_error_count
page_error_count
visual_non_empty
frame_switch_ok
range_control_ok
uses_trace_data
trace_mutation_detected
result_visible
main_area_not_blank
screenshot_non_empty
topic_alignment_score
failure_type
failure_reason
```

自动检查：

```text
1. HTML 文件存在。
2. 浏览器打开成功。
3. console/page error 为 0。
4. #stage 或 canvas/svg/main visual DOM 非空。
5. #counter 显示当前帧和总帧数。
6. next/prev/range 可切换帧。
7. 切换前后 artifact JSON 不变。
8. 页面至少读取了 frame.state 或 frame.evidence。
9. result 可见。
10. 截图不是空白。
```

可选 VLM 检查：

```text
1. 画面是否贴合题目语义。
2. 是否比 Verified View 更像题目本身。
3. 是否存在明显错误隐喻。
4. 是否存在严重重叠、遮挡、空白。
```

VLM 不能判断算法 correctness，不能进入 release gate。

## 13. Fallback 策略

Fallback 必须简单、确定：

```text
if creative_ok:
  publish creative view and verified view
else:
  publish verified view only
  keep creative report and failure screenshot
```

失败不能影响当前 artifact release：

```text
artifact.validation.release_gate.release_ready 不因 Creative View 失败而改变。
```

因为 Creative View 是展示增强层，不是 correctness 层。

## 14. 与现有 teaching enrichment 的关系

Teaching enrichment：

```text
LLM 只补 frame.teaching / frame.interaction。
不改 trace。
仍由 deterministic renderer 展示。
```

LLM Direct Visual Renderer：

```text
LLM 生成完整展示页面。
不改 trace。
不改 answer。
展示更自由。
可信度低于 deterministic renderer。
```

两者可以同时存在：

```text
Verified View:
  deterministic renderer + teaching enrichment

Creative View:
  direct visual renderer
```

Creative prompt 可以消费已有 teaching 文案，但不能把 teaching 文案当作新的事实来源。事实来源仍是 trace/state/result。

## 15. 代码落点

建议新增：

```text
algolab/generation/direct_visual_renderer.py
algolab/generation/prompts/direct_visual_renderer_system.txt
algolab/renderer/creative_direct.py
scripts/run_creative_visual_benchmark.py
scripts/audit_creative_visual_renderer.py
tests/regression/direct_visual_renderer.py
```

职责：

```text
direct_visual_renderer.py
  构造 prompt，调用 LLM，保存 raw output 和 sanitized HTML。

direct_visual_renderer_system.txt
  系统提示词。

creative_direct.py
  注入 artifact JSON，sanitize HTML，写出 creative page。

run_creative_visual_benchmark.py
  对已生成 artifact 批量生成 Creative View。

audit_creative_visual_renderer.py
  Playwright 打开页面，做 smoke、frame switch、trace immutability、截图检查。

direct_visual_renderer.py tests
  检查 prompt contract、sanitize、fallback、report schema。
```

不要把该功能塞进 `scene_compiler.py`。它不是 deterministic SceneGraph compiler 的一部分。

## 16. 输出目录

建议：

```text
output/repro_aaai_r9_creative_visual/
  creative_benchmark_report.json
  creative_benchmark_report.md
  case_metrics.csv
  html/
    llm_<case_id>_<sample>_creative.html
  screenshots/
    llm_<case_id>_<sample>_creative.png
  raw_llm/
    llm_<case_id>_<sample>_creative_raw.txt
  audit/
    llm_<case_id>_<sample>_creative_report.json
```

如果接入当前 AAAI 收口计划，也可以把 R9 改名为独立 optional experiment，避免影响 docs/12 的 correctness 收口。

## 17. 实验阶段

### C0：Prompt 与 sandbox 原型

目标：

- 单 case 手动生成 Creative View。
- 验证 HTML sanitize 和 Playwright smoke。
- 验证 fallback 不影响 Verified View。

推荐 case：

```text
trapping_rain_water
```

说明：这里只是原型验证，不是为该题写规则。

### C1：代表题 pilot

目标：

- 用同一套 prompt 跑 5-10 个视觉差异明显的 case。
- 不写 case-specific rule。
- 检查 prompt 是否能覆盖不同视觉隐喻。

推荐覆盖：

```text
array/histogram
matrix/grid
graph
tree
interval/timeline
stack/queue
geometry
```

这一步不是能力上限，而是风险控制。通过后进入 C2。

### C2：71-case full creative benchmark

目标：

- 对当前 71-case deterministic benchmark 全量 attempt Creative View。
- 报告 `creative_ok / fallback_used / visual_non_empty / frame_switch_ok / topic_alignment`。

输出：

```text
71-case creative_attempted = 71/71
creative_ok = x/71
fallback_used = y/71
```

这才是最终实验口径。

### C3：论文或系统展示

系统展示：

```text
Creative View 默认展示，如果 creative_ok。
Verified View 始终可切换。
```

论文叙述：

```text
Correctness evidence comes from Verified View.
Creative View demonstrates prompt-driven adaptive visualization over verified traces.
```

## 18. 论文表述边界

可以写：

```text
AlgoLab can attach an LLM Direct Visual Renderer after verified trace generation,
allowing problem-specific creative visualizations while preserving the certified
trace/result pipeline as the source of correctness.
```

可以写：

```text
On the 71-case benchmark, Creative View was attempted for all verified artifacts;
x/71 passed browser and visual audits, and the remaining cases fell back to the
deterministic Verified View.
```

不能写：

```text
Creative View proves algorithm correctness.
LLM direct HTML is fully reliable for arbitrary algorithms.
The system guarantees perfect visualization for any algorithm description.
```

## 19. 最小实现版本

最小可行实现：

```text
1. 输入一个现有 BuildArtifact JSON。
2. 构造 direct visual prompt。
3. LLM 输出 single-file HTML body/style/script。
4. 系统注入 artifact JSON。
5. 保存 creative.html。
6. Playwright audit。
7. 失败 fallback 到 verified.html。
```

第一版不需要：

```text
VLM audit
多模型投票
复杂 HTML sanitizer
UI tab 集成
全量 71-case 并发
```

第一版必须有：

```text
prompt contract
artifact injection
no external resources
browser smoke
frame switching
trace immutability check
fallback report
```

## 20. 最终判断

这个方案可以满足“根据题目描述生成对应算法可视化界面”的目标，同时不破坏当前系统已经建立的 100% verified pipeline。

它不是让 deterministic renderer 变成全能规则库，而是在 verified artifact 之后增加一个自由的、prompt-driven 的展示层。

它对任意算法的支持方式是：

```text
同一套 prompt 对所有 verified artifact 尝试生成 Creative View。
成功则展示。
失败则 fallback。
```

这比“为每个算法写规则”更符合开放题目集合，也比 direct HTML baseline 更可靠，因为算法事实仍然来自已验证 trace/result。
