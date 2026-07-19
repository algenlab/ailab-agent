# 实验结果文档统一设计

## 目标

将仓库中分散的实验结果、实验完成报告、外部 baseline 报告、消融报告、预算分析和理论定向结果合并为唯一权威文档 `docs/EXPERIMENT_RESULTS.md`。实验设计、评估协议、Prompt、数据集说明和真人研究协议继续独立保留。

## 权威来源顺序

发生数字或口径冲突时按以下顺序处理：

1. `output/` 中主实验、专项实验和理论定向实验的冻结机器结果。
2. `latex/evidence-ledger.md` 中已审计的数字、边界和原始产物路径。
3. 新统一结果文档中的解释和章节组织。
4. 专项报告中的详细结果和工程说明。
5. 旧总结中的历史描述仅用于补充背景，不覆盖较新结果。

## 唯一结果文档结构

`docs/EXPERIMENT_RESULTS.md` 采用以下结构：

1. 文档定位、冻结时间、结果口径和来源优先级。
2. Benchmark、比较条件、Machine OK 与统计方法。
3. 主实验、外部 baseline、内部消融。
4. 跨输入、跨模型、held-out 与 long-trace。
5. 语义保持、mutation、nested contract、noninterference 与恢复实验。
6. 视觉/教学评价、成本与预算分析。
7. 人工标注和真人研究的 pending 边界。
8. 可支持与禁止使用的 claim。
9. 原始结果文件、复现入口和最终验证索引。

文档保留完整关键表格、分母、置信区间、显著性、失败边界和原始 artifact 路径，但不重复收录完整 Prompt、系统架构说明或实验计划正文。

## 旧文档处理

删除只承担结果汇报、结果审计或实验完成记录职责的文档，包括 18、19、21、23--30、33--36 系列结果报告。`docs/20_ALGOTUTORGEN_PROMPT_APPENDIX.md`、`docs/22_EXTERNAL_HTML_BASELINE_SURVEY.md`、`docs/31_HUMAN_EXPERT_REVIEW_PROTOCOL.md`、`docs/32_STUDENT_USER_STUDY_PROTOCOL.md` 等非结果文档保留，并改为引用统一结果文档。

## 引用与生成器处理

- 更新 `docs/README.md` 和其他活跃文档的结果入口。
- 将 LaTeX evidence ledger、写作 prompt、spec/plan 中的旧结果报告引用统一指向新文档及对应章节。
- 修改会重新写入旧结果报告路径的脚本，使机器生成报告落到 `output/`，不再恢复被删除的 docs 文件。
- 原始 JSON、HTML、截图和统计产物不移动、不删除。

## 验证

1. 搜索仓库，确认不存在指向已删除结果报告的活跃引用。
2. 检查统一文档中的主分母和关键数字与 evidence ledger 一致。
3. 检查 Markdown 链接目标和原始 artifact 路径。
4. 运行 `git diff --check`；涉及 Python 生成脚本时运行相应轻量测试或编译检查。
