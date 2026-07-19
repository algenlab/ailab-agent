# Human Expert Review Protocol

## Status

`pending_human_data`. 本文件只规定研究流程，不包含或推断专家评价结果。

## Design

- 评审者：3 名具有算法教学、算法竞赛或计算机教育经验的独立专家。
- 材料：30 个分层任务，每题比较 AlgoTutorGen 与 Direct HTML，共 90 个专家-任务配对。
- 盲化：页面使用不含方法名的 opaque ID；每位专家的 A/B 顺序按任务独立随机化。
- 主要维度：过程正确性、教学清晰度、交互质量、视觉清晰度，均为 1–5 分。
- 额外字段：总体偏好、置信度、critical semantic error 和自由备注。

## Procedure

1. 负责人保存 `expert_private_key.json`，不得交给评审者。
2. 专家按 `expert_assignments.csv` 顺序打开 A/B 页面，使用同一输入完成导航、预测、错误反馈、提示和显示答案流程。
3. 专家独立填写 `expert_ratings.csv`，不得讨论评分。
4. 数据锁定后运行下述命令；脚本自动从同一目录读取并合并 `expert_private_key.json`，私钥不得进入给评审者的材料。
5. 对 critical error 分歧保留原始意见，必要时由第四名专家裁决；不得自动改写原始评分。

```bash
python3 scripts/analyze_human_study.py \
  --output-dir output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols
```

## Analysis

- 每方法报告四维均值和固定 seed 的 95% bootstrap CI，并报告 AlgoTutorGen - Direct 的配对均值差 bootstrap CI。
- 以专家-任务为配对单位运行双侧 Wilcoxon signed-rank；rank-biserial effect size 使用非零差值的平均秩正负秩和计算，不使用原始差值幅度。
- 四个主要评分维度的 Wilcoxon p 值使用 Holm 校正；同时保留原始 p 值、正负秩和与非零配对数。
- 报告每位专家和每个算法族的均值与配对检验敏感性分析；`family_id` 只保存在 private key 中。
- 评分前冻结排除规则，仅允许页面无法加载、专家未完成或协议偏离三类排除，并逐条披露。

当前空白数据运行只会产生 `pending_human_data`，不会推断或填充任何专家结果。

## Files

- `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/expert_assignments.csv`
- `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/expert_ratings.csv`
- `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/expert_private_key.json`
- `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/human_study_analysis.json`
