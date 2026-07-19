# Experiment Metric Annotations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `docs/EXPERIMENT_RESULTS.md` 中容易误读的实验、统计和教育评价指标补充简体中文解释，不修改任何结果数字。

**Architecture:** 在第 1 节建立统一术语表，减少重复；在关键表格后增加局部“怎么读”注释，解释该表独有的分母、方向和边界。验证通过关键数字快照、路径检查和现有文档质量检查完成。

**Tech Stack:** Markdown、rg、Git diff 校验。

---

### Task 1: 增加全局术语速查

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] 在 Machine OK 定义后增加术语表，解释浏览器子指标、实验阶段词和统计词。
- [ ] 明确 `p` 值、CI、rank-biserial 和 kappa 的读法及不能推出的结论。

### Task 2: 增加表格局部注释

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] 为教学/视觉评价表解释量表范围、分数方向和代理评价边界。
- [ ] 为传统系统、消融、fault injection 和跨模型表解释条件名称及分母。
- [ ] 为 long-trace、语义保持、mutation、noninterference、恢复、成本和 judge 表解释指标含义。

### Task 3: 验证注释不改变结果

**Files:**
- Verify: `docs/EXPERIMENT_RESULTS.md`

- [ ] 检查关键数字仍存在且未改变。
- [ ] 检查新增术语覆盖主要缩写和歧义项。
- [ ] 运行 `git diff --check` 和 `scripts/run_quality_checks.py`。

