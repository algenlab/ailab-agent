# LLM-Simulated Expert Trace Audit Preview

> **SYNTHETIC_LLM_PREVIEW：这不是人工专家评估结果。**

本目录只用于预演 `Expert Audit of Algorithmic Trace Fidelity` 的数据结构、统计表和论文呈现方式。数据由固定 seed 模拟生成，不得写成“专家发现”“人工审计证明”或与真实人工标签合并。

- `simulated_task_results.csv`：60 个模拟 task-level 结果；
- `simulated_variant_results.csv`：120 个模拟 variant-level 结果；
- `simulated_reviewer_labels.csv`：两位模拟 LLM reviewer 的 variant 标签；
- `simulation_summary.json`：汇总指标和门禁；
- `simulation_report.md`：可读结果说明。

真实论文证据必须由两位算法专家独立完成完整 trace 审计后另行生成。
