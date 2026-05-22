# AlgoLab 系统设计

本文档记录当前系统的实际架构、正确性门禁、渲染模式和 benchmark 状态。

## 目标

AlgoLab 的目标不是让 LLM 直接生成一个看起来正确的网页，而是：

```text
LLM 生成候选算法与轨迹
系统执行、校验、修复
只有通过 correctness gate 的 artifact 才进入渲染
```

也就是说，LLM 可以犯错；错误产物应被拦截，能修复则修复，修不好则不发布。

## 输入与输出

用户输入由 `ProblemInput` 描述，支持：

- LeetCode 风格题目
- 具体输入数据 JSON
- 可选 expected
- 可选算法思路
- 可选用户代码
- 希望生成的解法数量

系统输出：

- 构建产物 JSON：`BuildArtifact`
- 可靠模式 HTML
- 创意模式 HTML
- benchmark report

## 主流程

```text
用户输入
  -> LLM 生成 solution spec
  -> sandbox 执行 solve / trace / verify
  -> 答案一致性检查
  -> SemanticTrace schema 校验
  -> process invariant 校验
  -> SemanticTrace 编译成 SceneGraph
  -> SceneGraph 校验
  -> renderer 输出 HTML
  -> browser smoke 检查页面
```

核心文件：

- `algolab/pipeline.py`
- `algolab/generation/solution_generator.py`
- `algolab/runtime/sandbox.py`
- `algolab/runtime/executor.py`
- `algolab/verification/trace_validator.py`
- `algolab/verification/process_validator.py`
- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/export.py`
- `algolab/renderer/creative.py`
- `scripts/run_llm_benchmark.py`

## LLM 生成内容

LLM 必须输出 JSON 格式的 solution spec：

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

其中：

- `solve(input_data)` 计算答案。
- `trace(input_data)` 返回语义执行轨迹。
- `verify(input_data)` 返回独立校验答案。

LLM 不生成 HTML、CSS、JS、坐标或动画代码。

提示词位置：

- `algolab/generation/prompts/tracker_system.txt`
- `algolab/generation/prompts/repair_system.txt`

## sandbox 执行

生成代码在受限 Python sandbox 中执行：

- 禁止文件 IO
- 禁止网络
- 禁止 subprocess
- 禁止第三方库
- 禁止随机数和 sleep
- 有执行超时
- `solve / trace / verify` 必须只依赖 `input_data`

这样可以阻止外部副作用、危险调用和明显死循环产物进入后续流程。

## 正确性门禁

当前正确性评估分为四层。

### 1. 答案一致性

系统检查：

```text
solve(input_data) == trace.result
solve(input_data) == expected_result    如果用户提供 expected
solve(input_data) == verify(input_data) 如果 verifier 可执行
多个 variant 的结果一致               如果生成多个解法
```

强度排序：

```text
expected > deterministic invariant > independent verifier > 多解法一致 > schema
```

注意：`verify` 也是 LLM 生成的，所以它不是形式化证明；但它能作为独立执行路径降低同错概率。

### 2. SemanticTrace schema

`trace(input_data)` 必须符合固定 `SemanticTrace`：

- step 连续
- op 来自固定集合
- target id 可解析
- `trace.input_data` 必须等于本次输入
- `trace.result` 必须等于 `solve` 结果
- 数组、矩阵、图、树、点等 target 不能明显越界或不存在

固定 op 集合：

```text
create / set / mark / unmark / move / compare / link / unlink /
push / pop / enter / exit / explain
```

### 3. Process invariant

`process_validator` 检查 trace 中的过程状态是否满足算法不变量。它不是 renderer 规则，也不定义新 op。

当前覆盖：

- 不同路径二维 DP
- 打家劫舍一维 DP
- 0-1 背包 / 分割等和子集
- BFS 距离
- 二分窗口
- KMP 前缀函数
- 完全背包
- 区间 DP
- heap property
- 单调栈
- 并查集 forest
- 拓扑序
- Dijkstra 距离下界
- LCS
- 编辑距离
- BST
- LCA
- Tarjan lowlink 浅检查
- MST 环检查
- 凸包一致转向
- 回溯搜索树无环

详细说明见：

- `docs/process_validation.md`

### 4. Scene 与页面检查

通过算法校验后，系统将 `SemanticTrace` 编译为 `SceneGraph`。

Scene 校验包括：

- mark 指向存在对象
- edge / arrow source target 存在
- frame 可渲染

Browser smoke 使用 Playwright 打开 HTML，检查：

- 页面标题存在
- step counter 正常
- canvas / metaphor 非空
- 无 JS error
- 下一步按钮可用
- 创意模式主题切换可用

## repair loop

如果执行、答案、schema、process 或 scene 任一环节失败：

```text
原始输入 + 上一次 JSON + 错误信息
  -> repair prompt
  -> LLM 修复完整 solution spec
  -> 重新执行和校验
```

benchmark 默认开启严格 warning 模式。严格 warning 也会进入 repair，而不是最后才失败。

## 渲染模式

### 可靠模式

文件：

- `algolab/renderer/export.py`

特点：

- 传统教学页面
- 展示输入、输出、代码、状态、时间线
- 支持 array、matrix、graph、stack、queue、map、tree、heap、trie、union_find、recursion_tree、geometry
- 适合作为稳定 release 产物

### 创意模式

文件：

- `algolab/renderer/creative.py`

特点：

- 只消费已通过校验的 `BuildArtifact`
- 不参与算法正确性判定
- 支持主题切换：
  - 奇幻
  - 赛博
  - 像素
  - 白板
- 当前内置通用视觉隐喻：
  - 背包 / 容量槽
  - 图探索 / 队列
  - 单调栈 / 温度山脉
  - 几何点集 / 凸包星图
  - fallback 舞台卡片

导出脚本：

- `scripts/export_creative_demos.py`

示例产物：

- `output/creative_demos/creative_partition_bag.html`
- `output/creative_demos/creative_graph_bfs.html`
- `output/creative_demos/creative_daily_temperatures.html`
- `output/creative_demos/creative_convex_hull.html`

## Benchmark 状态

真实 LLM benchmark 不使用缓存。

最新多输入结果：

- 输出目录：`output/llm_benchmark_all_samples1`
- 模型：`gemini-3.1-pro-preview`
- 覆盖：14 类算法，35 个输入
- 结果：35/35 PASS
- warning：0
- error：0
- 平均耗时：80.53s/case
- 报告：`output/llm_benchmark_all_samples1/llm_benchmark_report.md`

HTML browser smoke：

```bash
python scripts/check_benchmark_html.py output/llm_benchmark_all_samples1 --require-count 35
```

结果：35/35 PASS。

创意模式 demo smoke：

- 4/4 PASS

本地质量检查：

```bash
python scripts/run_quality_checks.py
```

结果：PASS。

## 当前覆盖算法族

benchmark 当前覆盖：

- 二分
- 一维 DP
- 二维 DP
- 哈希表
- BFS
- KMP
- 单调栈
- 排序
- LCA
- 堆 / TopK
- Trie
- 并查集
- 回溯
- 凸包 / 几何

覆盖矩阵见：

- `docs/coverage_matrix.md`
- `docs/benchmark_cases_list.md`

## 当前边界

当前系统能强保证：

- 已通过 benchmark 的输入上，答案、trace、process、scene、HTML 均通过门禁。
- LLM 不直接写页面，renderer 只消费已验证 artifact。
- 违反已覆盖 invariant 的过程状态会被拦截。

当前还不能形式化保证：

- 任意自然语言 LeetCode 题都绝对正确。
- 所有算法族都有完整 invariant。
- LLM 生成的 verifier 天然可信。
- Tarjan、MST、Dijkstra 等高级算法的过程证明已经完备。
- 页面像素级美观、拥挤、遮挡都已自动量化。

下一步正确性方向：

- 将 verifier 升级为更确定性的 oracle / certificate checker。
- 增加 trace replay 证书，例如每个 `set` 事件声明使用的转移规则和依赖。
- 扩展高级算法 benchmark：Dijkstra、拓扑排序、完全背包、区间 DP、Tarjan、MST、复杂扫描线。

下一步视觉方向：

- 将创意模式中的自动视觉隐喻升级为 LLM 生成的 visual storyboard。
- 让 LLM 输出视觉编导意图，而不是直接输出 HTML。
- 增加截图级布局检查，检测重叠、拥挤、空白过大、文本不可读。
