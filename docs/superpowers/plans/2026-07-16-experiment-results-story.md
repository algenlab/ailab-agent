# Experiment Results Story Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 LaTeX 论文的论证顺序，将 `docs/EXPERIMENT_RESULTS.md` 重写为可连续阅读的研究故事，同时保留完整数字、边界和证据路径。

**Architecture:** 主体按“矛盾—诊断—机制—边界—泛化—负结果”组织，每节遵循问题、证据、解释、限制四段式。细节性指标、外部系统、预算和 artifact 索引集中到后半部分，避免打断主论证。

**Tech Stack:** Markdown、LaTeX evidence ledger、rg、Git diff 校验。

---

### Task 1: 重建开篇与故事骨架

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] 写出一句话结论、核心悖论和六步阅读路线。
- [ ] 将 benchmark 和指标说明压缩为读懂主结果所需的最小背景。

### Task 2: 重写主证据链

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] 用主实验说明正确答案不等于可执行 tutor。
- [ ] 用 nested survival 和外部 baseline 定位约束纠缠发生的位置。
- [ ] 用非退化消融说明完整分解链的必要性。
- [ ] 用 projection、mutation、overlay 和 noninterference 说明边界证据。
- [ ] 用跨输入、跨模型和 held-out 说明有限泛化。
- [ ] 用 Local/Global 负结果、成本和 long-trace 收紧主张。

### Task 3: 重组补充查阅材料

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] 保留教学/视觉代理指标、详细外部 baseline、完整消融和预算表。
- [ ] 保留指标速查、人工数据边界、claim boundary 和 artifact 索引。
- [ ] 删除重复解释和逐表复述，使同一数字只在推动叙事或查阅表中出现。

### Task 4: 数字与结构验证

**Files:**
- Verify: `docs/EXPERIMENT_RESULTS.md`
- Read: `latex/evidence-ledger.md`

- [ ] 核对主结果、表示保持、mutation、noninterference、跨模型、held-out、负结果和成本数字。
- [ ] 检查所有本地证据路径存在。
- [ ] 运行 `git diff --check`、轻量质量检查和显式回归。

