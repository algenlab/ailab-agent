# Experiment Results Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将分散的 AlgoTutorGen 实验结果统一为 `docs/EXPERIMENT_RESULTS.md`，删除旧结果报告，并修复全仓引用和报告生成路径。

**Architecture:** 以 `latex/evidence-ledger.md`、最新理论报告和主论文报告为审计来源，按主题重组而非直接拼接。实验设计、协议、Prompt、数据集说明和原始 `output/` 产物保持独立；所有汇总数字只在统一结果文档中维护。

**Tech Stack:** Markdown、LaTeX 引用文本、Python 报告脚本、Git/rg 校验。

---

### Task 1: 建立唯一结果文档

**Files:**
- Create: `docs/EXPERIMENT_RESULTS.md`
- Read: `latex/evidence-ledger.md`
- Read: execution-start legacy result reports, subsequently consolidated and deleted
- Read: frozen machine reports under `output/experiments/` and `output/external_baselines/`

- [ ] **Step 1:** 提取统一 benchmark、比较条件、统计方法和分母口径。
- [ ] **Step 2:** 合并主实验、外部 baseline、内部消融和视觉/教学结果表格。
- [ ] **Step 3:** 合并跨输入、跨模型、held-out、long-trace、预算和成本结果。
- [ ] **Step 4:** 合并语义保持、mutation、nested survival、noninterference 和恢复负结果。
- [ ] **Step 5:** 合并 pending-human 边界、claim 边界、原始 artifact 与复现索引。
- [ ] **Step 6:** 对照 `latex/evidence-ledger.md` 逐项核验 200/646/40/294/55,108/2,198/392/1,561,298 等关键分母与数字。

### Task 2: 删除旧结果报告

**Files:**
- Delete: legacy result-only reports superseded by `docs/EXPERIMENT_RESULTS.md`

- [ ] **Step 1:** 确认每个旧报告的独有结果、边界和产物路径已进入统一文档。
- [ ] **Step 2:** 使用补丁删除上述旧结果报告，不删除原始 JSON、HTML、截图或实验目录。

### Task 3: 更新文档与 LaTeX 引用

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/20_ALGOTUTORGEN_PROMPT_APPENDIX.md`
- Modify: `docs/22_EXTERNAL_HTML_BASELINE_SURVEY.md`
- Modify: `latex/evidence-ledger.md`
- Modify: `latex/prompt.md`
- Modify: `docs/superpowers/specs/*.md`
- Modify: `docs/superpowers/plans/*.md`
- Modify: any other Markdown/TeX file returned by stale-reference search

- [ ] **Step 1:** 将推荐阅读入口改为 `docs/EXPERIMENT_RESULTS.md`。
- [ ] **Step 2:** 将所有旧结果报告路径替换为统一文档和对应章节描述。
- [ ] **Step 3:** 保留原始 `output/` 证据路径，使统一文档和 evidence ledger 可以直接追溯机器结果。
- [ ] **Step 4:** 运行 `rg`，确认 Markdown、TeX 和 Python 中不存在已删除结果报告路径。

### Task 4: 防止脚本重新生成旧 docs 报告

**Files:**
- Modify: `scripts/summarize_webgen_agent_baseline.py`
- Modify: any script returned by `rg 'docs/.*(REPORT|SUMMARY|CHECKLIST)' scripts`
- Test: relevant regression module if the output path is covered

- [ ] **Step 1:** 将 WebGen-Agent 的人类可读报告输出改到实验输出目录中的 `report.md`。
- [ ] **Step 2:** 保持 JSON 报告字段和统计逻辑不变，仅迁移人类可读报告路径。
- [ ] **Step 3:** 使用固定 Python 解释器执行 `py_compile` 或相关测试，确认路径调整不破坏脚本加载。

### Task 5: 最终一致性验证

**Files:**
- Verify: `docs/EXPERIMENT_RESULTS.md`
- Verify: all modified Markdown, TeX and Python files

- [ ] **Step 1:** 运行 stale-reference 搜索，预期无旧结果报告引用。
- [ ] **Step 2:** 运行标题和结果文档搜索，确认 docs 中只有 `EXPERIMENT_RESULTS.md` 承担实验结果汇总职责。
- [ ] **Step 3:** 运行 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile scripts/summarize_webgen_agent_baseline.py`。
- [ ] **Step 4:** 运行 `git diff --check`。
- [ ] **Step 5:** 检查 `git diff --stat` 和删除清单，确认未触及原始实验产物及无关用户改动。
