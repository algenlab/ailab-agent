# 实验指标注释设计

## 目标

让不熟悉软件实验、教育评价和配对统计的读者能够独立读懂 `docs/EXPERIMENT_RESULTS.md`，同时保持现有实验数字、分母、显著性和 claim 边界不变。

## 方案

采用“全局术语速查 + 表格局部注释”的两层结构：

1. 在第 1 节增加指标、实验阶段和统计量速查表，解释 Machine OK 子项、generation、primary、selected-final、CI、McNemar、Holm、rank-biserial、kappa、self-contained 等高频词。
2. 在视觉评价、外部系统能力、消融、fault injection、跨模型、long-trace、语义保持、noninterference、Local/Global、成本和 judge 表下增加简短“怎么读”注释。
3. 注释优先回答“测什么、数值高低怎么解释、不能推出什么”，不重复结果结论。

## 边界

- 不修改任何实验数值、统计检验、原始路径或 claim。
- 不把 LLM/VLM 代理指标解释成真人学习效果。
- 不把零违规、100% mutation rejection 或 frame equality 写成形式化证明。
- 不为每个明显字段添加冗余脚注，避免文档膨胀。

## 验证

- 对比修改前后的关键数字集合，确保完全一致。
- 检查新增注释覆盖主要缩写和歧义项。
- 运行 `git diff --check` 和现有轻量质量检查。

