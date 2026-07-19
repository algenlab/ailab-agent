# AI 编码指南

## 1. 每轮开始必须阅读

任何 AI 开发任务开始前，必须先阅读：

- `docs/00_PRODUCT_NORTH_STAR.md`
- `docs/01_FINAL_PAGE_SPEC.md`
- `docs/02_SYSTEM_ARCHITECTURE.md`
- `docs/03_AI_CODING_GUIDE.md`
- `docs/07_ROADMAP_AND_TASKS.md`
- 当前任务相关源码和测试

如果任务涉及 trace、target、SceneGraph 或 renderer，还必须阅读：

- `docs/04_TRACE_AND_SCHEMA_CONTRACT.md`
- `docs/05_VISUAL_PRIMITIVES_AND_PATTERNS.md`
- `SYSTEM_OVERVIEW.md`

## 2. 硬规则

以下规则不得违反：

1. 不允许让 LLM 直接生成 HTML/CSS/JS 页面。
2. Renderer 只能消费 SceneGraph 和 BuildArtifact。
3. `tracker_code` 必须优先使用系统注入的 `TraceSession` DSL；`Tracer` 仅用于历史兼容。
4. `trace(input_data)` 必须返回 `semantic-trace-v1`。
5. trace 顶层必须显式包含与本次请求完全一致的 `input_data`。
6. 事件字段必须使用 `op` 和 `targets`。
7. 不允许恢复旧字段兼容，例如 `type`、`target`、缺失 `input_data` 自动补齐。
8. 不允许恢复旧式 map target，例如 `seen:2`、`dist:A`、`map:seen`。
9. 新算法优先复用已有 SemanticOp 和视觉原语。
10. 不允许跨多个 Phase 一次性大改。
11. 每次改动必须增加或更新相关测试，除非任务仅修改说明文档。
12. 每次任务必须运行相关测试或明确说明无法运行的原因。

## 3. 修改边界

允许修改：

- 当前任务明确涉及的源码。
- 当前任务相关测试。
- 当前任务相关文档。
- 为满足验收标准必需的小范围辅助代码。

不允许修改：

- 无关架构层。
- 与任务无关的生成产物。
- 用户未要求的 benchmark 结果。
- 安全边界或校验严格性，除非任务明确要求且有测试证明。

如果必须跨层修改，先写清楚：

- 为什么单层修改无法完成。
- 涉及哪些文件。
- 新增哪些测试。
- 风险是什么。

## 4. 开发顺序

推荐顺序：

1. 找到 `docs/07_ROADMAP_AND_TASKS.md` 中最靠前的相关小任务。
2. 阅读涉及文件和验收标准。
3. 阅读现有测试。
4. 先补或调整测试。
5. 做最小实现。
6. 运行相关测试。
7. 检查是否违反产品、架构、trace、renderer 边界。
8. 汇报修改文件、测试结果、风险和下一步。

## 5. Trace 相关任务规则

新增或修改 tracker 时：

- 优先使用 `sess = TraceSession(algorithm, input_data, pseudocode=[...])`。
- 保留完整必要过程，不要因为帧数主动省略真实算法步骤。
- 系统不再按事件数采样或限制 `max_events`；只控制单步 `state` 不要过大。
- DSL 写操作应能产生足够的 `value`、`deps`、`state`、`reason` 证据；必要时用 `reason=...` 或 `sess.note(...)` 补充教学意图。
- DP 转移类事件必须能被 process validator 复核。
- `state` 应包含当前帧重建页面所需的关键变量。
- 返回前必须补齐每个关键事件的 `code_line`，行号指向同一 variant 的 `code` / `solve(input_data)`。

禁止写法：

```python
events.append({"type": "set", "target": "dp[1][2]"})
```

正确方向：

```python
sess = TraceSession("不同路径", input_data, pseudocode=["初始化 DP", "按行列转移"])
dp = sess.table("dp", [[1] * n for _ in range(m)])
dp[1, 2] = 3
sess.result(dp[m - 1, n - 1])
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

## 6. Renderer 相关任务规则

Renderer 可以改善页面体验，但不能改变语义。

必须遵守：

- 只从 BuildArtifact / SceneGraph / validation report 读取信息。
- 如果需要新 UI 信息，优先扩展 SceneGraph 或 teaching 字段，而不是让 renderer 猜算法。
- Debug 信息默认折叠。
- 学生主视图优先展示教学解释。
- 所有新增交互必须有稳定降级路径。

禁止：

- 在 renderer 中写具体算法判断，例如直接识别不同路径公式后修改状态。
- 通过前端代码修正错误 trace。
- 让 HTML runtime 重新计算算法答案作为发布依据。

## 7. Validator 相关任务规则

新增 validator 规则时：

- 先定义失败类型和错误消息。
- 使用小样例写正例和反例。
- blocking error 只用于会导致错误发布的问题。
- warning 用于教学质量不足、覆盖不充分、可视化弱等问题。

不得为了通过页面发布而放宽 validator。

## 8. Benchmark 相关任务规则

新增 benchmark case 时必须包含：

- 题目 id。
- 题目描述。
- 算法族。
- input contract。
- 至少 2 个样例输入，常见题尽量 3 个。
- expected output。
- solve / trace / verifier。
- expected visual layouts。

优先覆盖：

- 正常样例。
- 边界样例。
- 容易触发过程错误的样例。

## 9. 必须运行的命令

运行 Python 文件必须使用：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3
```

常用检查：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

`tests.benchmark_regression` 现在是轻量兼容入口，聚焦当前 teaching / interaction contract。浏览器证据的默认执行环境是已缓存的 Ubuntu 22 / Playwright 兼容容器，不是当前宿主机。当前宿主机 glibc 过旧，不能直接运行 Playwright 自带 node。涉及 renderer、HTML runtime 或 dashboard 浏览器交互时，执行 AI 必须使用：

```bash
bash scripts/run_browser_smoke_container.sh
```

容器内 Python 使用镜像自带解释器；宿主机上的所有 Python 命令仍必须使用 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3`。容器脚本默认使用宿主机当前 UID/GID 写入挂载目录，避免再次生成 root-owned 输出文件。

默认镜像为 `iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest`，该镜像在当前机器已有缓存并包含 Playwright/Chromium。外部 CI 可以用 `ALGOLAB_PLAYWRIGHT_IMAGE=mcr.microsoft.com/playwright/python:v1.59.0-noble ALGOLAB_CONTAINER_INSTALL_DEPS=1` 覆盖为官方 Playwright 镜像。

运行容器命令前必须确认当前用户可以访问 Docker daemon。脚本会优先使用普通 `docker`，失败后自动尝试 `sudo -n docker`。若两者都失败，这是执行环境权限问题，需要把当前用户加入 `docker` 组、配置免密 `sudo docker`，或切到有 Docker 权限的 CI / 容器宿主机；不要把它当作代码失败。

Phase 17 的 renderer / HTML runtime / 交互改动还必须生成真实浏览器截图证据：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/capture_phase17_screenshots.py --output-dir output/phase17_screenshots
```

完成汇报必须写出截图 manifest 路径、覆盖的 demo id、desktop/mobile 视口，以及人工查看结论。

如果遇到网络问题，可以先清理代理环境变量，再按项目根目录 AGENTS.md 设置代理。

## 10. 完成汇报格式

每次任务结束必须汇报：

- 改了什么。
- 为什么改。
- 修改文件。
- 跑了哪些测试，结果是什么。
- 还有什么风险。
- 下一步建议。

不能只说“已完成”。
