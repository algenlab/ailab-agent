# Plan2 P0-3 Minimal Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Stage2 多解法帧选择，复用已有模型输出重封装产物，并用公平的语义指标重跑 P0-3 负向结果。

**Architecture:** 保留现有 artifact 与 Creative Stage 生成资产，只修正 Creative Shell 的 variant→scene/frame 数据流。旧产物不覆盖；新 manifest 指向本地重封装页面。审计主门禁比较语义状态和可观察行为，DOM/文字差异降级为诊断。

**Tech Stack:** Python 3.10、pytest、静态单文件 HTML/JavaScript、Docker Playwright、JSON 审计报告。

---

### Task 1: 多解法帧选择回归

**Files:**
- Modify: `tests/regression/test_plan2_shell_ownership.py`
- Modify: `algolab/renderer/creative_direct.py`

- [ ] 添加双解法回归测试，断言生成 shell 不得优先使用顶层首解法 `scene/frames`。
- [ ] 运行目标测试并确认旧实现按预期失败。
- [ ] 最小修改 `scene()` 与 `frames()`，保留顶层兼容别名。
- [ ] 重跑目标测试和相关 renderer/P0-3 回归测试并确认通过。

### Task 2: 本地重封装 200 个 Stage2 页面

**Files:**
- Create: `scripts/rebuild_plan2_stage2_after_variant_fix.py`
- Create: `output/experiments/plan2_20260722/p0_3_stage2_variant_fix/`

- [ ] 从旧 manifest 读取 200 个最终 generation report。
- [ ] 将 `/work/...` 路径映射回当前仓库，并验证 artifact/raw_output 全部存在。
- [ ] 调用 `render_direct_visual_stage_shell_html()` 生成新 HTML，不调用 API。
- [ ] 写出新 manifest、来源 SHA256 与重封装摘要。
- [ ] 核对 200/200 完整性和 artifact SHA256 不变。

### Task 3: 修订并重跑 P0-3 负向指标

**Files:**
- Modify: `scripts/audit_plan2_shell_ownership.py`
- Modify: `tests/regression/test_plan2_shell_ownership.py`
- Create: `output/experiments/plan2_20260722/p0_3_shell_ownership_variant_fix/`

- [ ] 为语义判据与故障分类添加失败测试。
- [ ] 将精确文字 hash/DOM skeleton 从主门禁移到诊断字段。
- [ ] 增加 artifact、variant、frame、state、code line、timeline、interaction 和 answer 的语义统计。
- [ ] 将 generic fallback、Verified fallback、外部请求和 shell 完整性分开统计。
- [ ] 在 Docker 中只对修复后页面重跑 P0-3 浏览器审计。

### Task 4: 文档、P0-2 监控与最终验证

**Files:**
- Modify: `docs/PLAN2_EXPERIMENT_RESULTS.md`
- Modify: `docs/EXPERIMENT_RESULTS.md`（仅当 P0-3/P0-2 形成最终结果）

- [ ] 将旧 P0-3 标为错误审计记录，不再报告“明确负结果”。
- [ ] 写入修复后 P0-3 的最终语义结果和故障分类。
- [ ] 持续检查 P0-2 两侧进程、完成数、invalid runs 和基础设施失败。
- [ ] P0-2 完成后继续既定 Machine/服务/配对统计，不单侧补跑。
- [ ] 运行目标回归、综合回归、质量检查和 `git diff --check`。
