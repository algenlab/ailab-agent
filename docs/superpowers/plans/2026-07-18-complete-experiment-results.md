# Complete Experiment Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将所有已完成实验整理进唯一结果文档，并建立独立、完整、可读的理论定向实验章节。

**Architecture:** 以当前 `docs/EXPERIMENT_RESULTS.md` 的核心表和通俗注释为展示骨架，以冻结机器 JSON、`latex/evidence-ledger.md` 和历史统一报告为数据源。正式结果、先导结果和 pending-human 状态分层展示，避免重复 shard 与补跑记录污染实验单位。

**Tech Stack:** Markdown、JSON、`rg`、`jq`、固定 Python 3.10 校验脚本、Git diff。

---

### Task 1: 建立实验覆盖清单

**Files:**
- Read: `docs/EXPERIMENT_RESULTS.md`
- Read: `latex/evidence-ledger.md`
- Read: `output/experiments/**`
- Read: `output/external_baselines/**`

- [x] **Step 1:** 列出主实验、先导实验、外部 baseline、消融、稳健性、跨模型、理论、教学视觉和人工状态实验族。
- [x] **Step 2:** 将 shard、resume、debug probe 归并到所属实验，不作为独立结果行。
- [x] **Step 3:** 对每个实验记录冻结来源、样本规模、直接结果和解释边界。

### Task 2: 重组统一结果文档

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [x] **Step 1:** 保留第 0 节核心表与第 1 节通俗指标说明。
- [x] **Step 2:** 增加 Benchmark 构建、先导实验和历史冻结实验表。
- [x] **Step 3:** 补齐主实验、外部方法、消融、稳健性、跨模型、预算、成本和教学视觉表格。
- [x] **Step 4:** 将理论相关内容从其他章节归并到独立理论专章。
- [x] **Step 5:** 为每张主要表增加指标注释、结果直读和必要的解释边界。

### Task 3: 补全理论定向实验

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`
- Read: `output/experiments/theory_aligned_20260714/*.json`

- [x] **Step 1:** 写入理论主张与实验对应关系表。
- [x] **Step 2:** 写入 Local/Global 的四组直接结果表和实现边界。
- [x] **Step 3:** 写入语义保持、确定性、semantic mutation、overlay 和 noninterference 表。
- [x] **Step 4:** 写入 11 条 cumulative nested-contract survival 和 11 条 conditional survival。
- [x] **Step 5:** 明确 Flat Final-Only 未作为同构第三策略执行。

### Task 4: 内容与路径核验

**Files:**
- Verify: `docs/EXPERIMENT_RESULTS.md`

- [x] **Step 1:** 运行固定 Python 校验脚本，检查关键数字、理论实验方法数和章节覆盖。
- [x] **Step 2:** 检查 Markdown 表格列数、反引号、标题层级和本地路径。
- [x] **Step 3:** 运行 `git diff --check`。
- [x] **Step 4:** 检查 `git diff -- docs/EXPERIMENT_RESULTS.md`，确认没有覆盖无关用户改动。

### Task 5: 最终交付

**Files:**
- Verify: `docs/EXPERIMENT_RESULTS.md`
- Verify: `docs/superpowers/specs/2026-07-18-complete-experiment-results-design.md`
- Verify: `docs/superpowers/plans/2026-07-18-complete-experiment-results.md`

- [x] **Step 1:** 汇报新增的实验覆盖范围、理论专章内容和明确保留的 pending-human 边界。
- [x] **Step 2:** 不提交或推送当前脏工作区；仅交付本轮文件修改和验证结果。
