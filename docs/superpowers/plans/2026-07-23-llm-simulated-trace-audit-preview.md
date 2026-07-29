# LLM-Simulated Trace Audit Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一套明确标记为非人工证据的 60-task、120-variant LLM 模拟预评估数据，用于预演 Expert Audit of Algorithmic Trace Fidelity 的表格和分析流程。

**Architecture:** 从冻结 Full-200 报告读取真实 case/family/variant 元数据，按 23 个算法族分层选择 60 题；使用固定 seed 生成保守、可复现的模拟双评审标签，输出逐题、逐 variant、汇总 JSON 和 Markdown。所有文件使用 `SYNTHETIC_LLM_PREVIEW` 标记，且不写入真实人工标注目录。

**Tech Stack:** Python 3.10 标准库、CSV、JSON、Markdown；运行时固定使用 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3`。

---

### Task 1: 模拟数据生成器

**Files:**
- Create: `scripts/generate_llm_simulated_trace_audit_preview.py`
- Test: `tests/regression/test_llm_simulated_trace_audit_preview.py`

- [ ] **Step 1: 写失败测试**

测试固定 seed 输出 60 tasks、23 families、120 variants，且所有记录包含 `evidence_status=SYNTHETIC_LLM_PREVIEW`；检查至少存在一个模拟问题，防止生成全满分结果。

- [ ] **Step 2: 运行测试确认失败**

Run: `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest tests/regression/test_llm_simulated_trace_audit_preview.py -q`

Expected: FAIL，因为生成器尚不存在。

- [ ] **Step 3: 实现最小生成器**

生成器读取 `llm_benchmark_report.json`，按每族至少两题再按剩余规模补足 60 题，输出双评审与裁决后的 variant/task 标签；模拟结果保留 1 个关键错误 task、少量非关键问题和有限评审分歧。

- [ ] **Step 4: 运行测试确认通过**

Run: `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest tests/regression/test_llm_simulated_trace_audit_preview.py -q`

Expected: PASS。

### Task 2: 生成交付数据并核验

**Files:**
- Create: `deliverables/plan2_final_results_20260723/llm_simulated_expert_trace_audit/README.md`
- Create: `deliverables/plan2_final_results_20260723/llm_simulated_expert_trace_audit/simulated_task_results.csv`
- Create: `deliverables/plan2_final_results_20260723/llm_simulated_expert_trace_audit/simulated_variant_results.csv`
- Create: `deliverables/plan2_final_results_20260723/llm_simulated_expert_trace_audit/simulated_reviewer_labels.csv`
- Create: `deliverables/plan2_final_results_20260723/llm_simulated_expert_trace_audit/simulation_summary.json`
- Create: `deliverables/plan2_final_results_20260723/llm_simulated_expert_trace_audit/simulation_report.md`

- [ ] **Step 1: 运行生成器**

Run: `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/generate_llm_simulated_trace_audit_preview.py --output-dir deliverables/plan2_final_results_20260723/llm_simulated_expert_trace_audit`

Expected: 输出 60 tasks、120 variants 和双评审模拟标签。

- [ ] **Step 2: 校验研究边界**

确认每个文件均包含 synthetic 标记，README 明确禁止作为真人专家证据，且未修改 `output/experiments/plan2_20260722/p0_4_source_trace/human_review`。

- [ ] **Step 3: 校验汇总一致性**

重新从 CSV 统计 task/variant 数、关键错误数、trace-perfect 数与 family 覆盖，要求与 `simulation_summary.json` 完全一致。
