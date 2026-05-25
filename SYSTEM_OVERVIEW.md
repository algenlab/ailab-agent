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
python cli.py --strategy "动态规划" --solutions 2 --output output/algolab.html
```

不同路径样例：

```bash
python cli.py \
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
python scripts/build_demo_dashboard.py --output-dir output/dashboard --style both
```

直接打开：

```text
output/dashboard/index.html
```

或用本地静态服务：

```bash
python -m http.server 8000 --directory output/dashboard
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
- target 是否明显越界。
- trace input 是否等于当前 input。
- trace result 是否等于 solve result。

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
python -m tests.offline_regression
```

Benchmark 回归：

```bash
python -m tests.benchmark_regression
```

浏览器 smoke：

```bash
python -m tests.browser_smoke
```

全部本地检查：

```bash
python scripts/run_quality_checks.py
```

这些检查验证系统边界，不等价于证明任意未知题的 LLM 输出永远正确。

## 12. 常见问题

### 为什么页面里只有少数几帧？

通常不是播放器问题，而是 `trace(input_data)` 只生成了少数 events。检查：

```bash
python - <<'PY'
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
- 已覆盖算法族的关键状态转移会被 process invariant 校验。
- 通过 release gate 的 artifact 才进入 HTML。

系统不能完全保证：

- 任意未知算法题一次生成就正确。
- LLM 生成的 verifier 永远独立且无同错。
- 大规模图、几何、搜索树布局永远清晰。

因此，新的算法族上线前必须补 deterministic case 和回归测试。
