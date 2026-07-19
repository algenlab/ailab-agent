# AlgoLab

基于“语义轨迹 + Scene Graph + 固定中文 Web Runtime”的算法可视化生成系统。

## 目标

输入：

- LeetCode 风格题目
- 具体 JSON 输入
- 可选：解法思路
- 可选：用户代码
- 可选：期望输出

输出：

- 可验证的算法执行语义轨迹
- 多解法交互式可视化页面
- 构建 JSON artifact

## 新架构

```text
题目 / 输入 / 可选思路 / 可选代码
        |
        v
LLM 生成 solve / trace / verify
        |
        v
沙箱执行与结果门禁
        |
        v
SemanticTrace
        |
        v
Scene Compiler
        |
        v
SceneGraph
        |
        v
固定中文 Web Runtime
```

核心边界：

- LLM 不生成页面、不写布局、不写坐标。
- Trace 只使用少量通用语义操作。
- Renderer 只消费 SceneGraph，不理解具体算法。

## 通用语义操作

`create`、`set`、`mark`、`unmark`、`move`、`compare`、`link`、`unlink`、`push`、`pop`、`enter`、`exit`、`explain`

新增算法时通常不需要新增操作。只有出现新的视觉形态时，才扩展 Scene Compiler 或 Web Runtime。

## 运行 CLI

默认样例：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 cli.py --strategy "动态规划" --solutions 2 --output output/algolab.html
```

自定义题目：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 cli.py \
  --problem "LeetCode 62. 不同路径。机器人每次只能向下或向右移动，返回路径数。" \
  --input '{"m":3,"n":7}' \
  --expected '28' \
  --strategy "动态规划和组合数学" \
  --solutions 2 \
  --output output/unique_paths.html
```

## 运行 Web UI

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 app.py
```

默认端口：`7861`

## 本地质量检查

不调用 LLM 的轻量检查：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

当前默认检查聚焦 active pipeline 的 Python 编译、教学层 contract 和交互渲染入口。浏览器证据不再默认跑；需要截图或真实浏览器验证时显式使用容器：

```bash
bash scripts/run_browser_smoke_container.sh
```

当前宿主机 glibc 过旧，不能直接运行 Playwright 自带 node。宿主机上的 Python 命令仍使用 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3`；容器内命令使用镜像自带 Python。

默认镜像为当前机器已缓存的 `iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest`。外部 CI 可通过 `ALGOLAB_PLAYWRIGHT_IMAGE` 覆盖为官方 Playwright 镜像。

运行容器命令需要 Docker daemon 权限。脚本会优先使用普通 `docker`，失败后自动尝试 `sudo -n docker`；如果两者都不可用，需要把用户加入 `docker` 组、配置免密 `sudo docker`，或在有 Docker 权限的 CI 环境运行。

这些检查覆盖 schema 严格性、trace validator、scene compiler、沙箱超时、renderer HTML 输出和 Playwright 页面加载。它们不证明 LLM 对所有题目都正确，只证明系统的确定性边界和已有样例可重复通过。

## 当前信心边界

事实支持：

- LLM 不直接生成页面。
- renderer 只消费 SceneGraph。
- SemanticTrace 的 op 集合是固定枚举。
- 子进程沙箱能阻止非法 import 和死循环。
- 已有样例页面可加载、可步进、无 JS error。

仍需继续强化：

- LLM 生成的 tracker 对未知题目的算法正确性不能靠本地测试完全证明。
- 需要更多自动生成边界用例和多输入回归。
- 复杂图、递归树、线段树、几何类问题还需要扩展 scene compiler 的视觉形态。
- 页面美学还需要 Playwright 截图回归和布局阈值检查。

## 系统说明

完整架构、流程、门禁、覆盖范围和排查方式见：

- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)
- [SYSTEM_FLOW.html](SYSTEM_FLOW.html)

## 主要目录

```text
algolab/
  schemas/              # ProblemInput / SemanticTrace / SceneGraph / Validation
  generation/           # 中文 prompt 与 LLM 生成
  runtime/              # 沙箱执行 solve / trace / verify
  verification/         # trace 校验与 release gate
  compiler/             # SemanticTrace -> SceneGraph
  renderer/             # SceneGraph -> 单文件中文 HTML

cli.py                  # 命令行入口
app.py                  # Gradio 入口
llm_client.py           # OpenAI-compatible LLM 客户端
output/                 # 生成产物
```

## 旧架构状态

旧的 `modules/`、`renderers/`、`simulators/` 属于历史 pipeline，不再作为主入口。新系统从 `cli.py` / `app.py` 进入。
