# Plan2 最终实验结果交付包

整理日期：2026-07-23。

本目录只包含最终有效结果，不包含 pilot、diagnostic、smoke、invalid run 或过时的 P0-3 审计。

## 优先文件

| 用户请求 | 文件 |
| --- | --- |
| 服务复用汇总 | `p0_1_service_audit/service_usage_summary.json` |
| Source-line 明细 | `p0_1_service_audit/source_line_diagnostics.csv` |
| Hybrid prompt profile | `p0_2_prompt_ablation/hybrid_current/llm_benchmark_report.json` |
| Service-only prompt profile | `p0_2_prompt_ablation/service_only/llm_benchmark_report.json` |
| Prompt 配对统计 | `p0_2_prompt_ablation/prompt_ablation_paired_statistics.json` |
| 修复后的 PVCR ownership 审计 | `p0_3_shell_ownership/shell_ownership_audit.json` |

## 补充文件

- `p0_2_prompt_ablation/service_audits/`：两个 prompt profile 各自的服务复用与 source-line 审计。
- `docs/PLAN2_EXPERIMENT_RESULTS.md`：通俗版完整结果说明。
- `human_annotation_status/`：人工实验状态文件。

## 核心结果

- P0-1：187/200 个任务组合至少两个目录内服务，目录外服务调用为 0。
- P0-2 Hybrid：generation 192/200，Machine OK 187/200。
- P0-2 Service-only：generation 181/200，Machine OK 181/200。
- Service-only − Hybrid 的 Machine OK 为 -3.0 个百分点，95% bootstrap CI 为 [-7.5, +1.5] 个百分点，未通过 -3 个百分点不劣界限。
- P0-3：200/200 artifact 一致，12,709/12,709 个状态通过核心语义 ownership。

## 人工标注状态

P0-4 Source-to-trace 和 P1 视觉校准均为 `pending_human_labels`。现有 reviewer CSV 只有任务和空白评分字段，不属于已完成的人工结果，因此未收入本包；私有盲化 key 也未收入。

`CHECKSUMS.sha256` 可用于校验包内文件是否完整。
