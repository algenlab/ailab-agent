# Student User Study Protocol

## Status

`pending_human_data`. 尚未招募参与者，不能报告学习效果、SUS 或认知负荷结果。

## Design

- 计划样本：24 名具有基础数据结构与算法课程经历的学生，可接受范围 20–30 名。
- 设计：被试内交叉实验，AlgoTutorGen 与 Direct HTML 以 X/Y 两个六题 block 呈现；24 人中各 12 人先完成一种条件，任务顺序按参与者轮换。
- 每人任务：12 题，每种条件 6 题；任务覆盖多种算法族和 choice/input/judge 交互。
- 主要终点：任务正确率和完成时间。
- 次要终点：提示/显示答案使用、单题认知负荷 1–7、条件级 SUS、总体偏好。

## Procedure

1. 取得机构伦理审批或书面豁免，并收集知情同意；不得在审批前采集数据。
2. 统一进行 5 分钟练习，不使用正式任务。
3. 按 `student_assignments.csv` 顺序完成任务；公开材料只显示 X/Y 和 opaque trial/page ID，实际条件映射保存在 `student_private_key.json`。
4. 每题记录正确性、完成时间、认知负荷和辅助功能使用；每个六题 block 后填写对应 X/Y 的 10 项 SUS 和条件级认知负荷，总体偏好只在第二个 block 后填写一次。
5. 数据去标识化，参与者编号与身份映射独立加密保存，不进入仓库。

数据锁定后运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/analyze_human_study.py \
  --output-dir output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols
```

脚本自动合并 trial 私钥和每位参与者的 X/Y 条件映射。若问卷填写了 10 个 SUS item，则按奇数项 `response - 1`、偶数项 `5 - response`、总和乘 2.5 计算 0–100 分；若同时填写 `sus_score`，脚本会校验两者一致。

## Analysis

- 预注册主分析采用参与者内配对：每位参与者先按条件聚合正确率和完成时间，再运行双侧 Wilcoxon，报告 signed-rank rank-biserial effect size，并对脚本输出的配对结局使用 Holm 校正。
- 条件级描述与配对结果包括 SUS、单题认知负荷、条件问卷认知负荷、提示使用率和显示答案使用率，并单独报告总体偏好。
- 混合效应模型尚未由该 Python 工具自动实现。若数据锁定后补做确认性模型，应使用 R 或 statsmodels，预先冻结参与者和任务随机截距、条件固定效应、收敛与缺失值处理规则，并与主配对分析分开报告。
- 完成时间是否 log 转换必须在查看条件差异前依据预注册的分布诊断规则决定。
- 预期中等配对效应时，24 人可提供探索性证据；论文必须明确样本量和置信区间，不把小样本结果表述为普遍学习增益。

当前空白数据运行只会产生 `pending_human_data`，不会生成学习效果、SUS 或认知负荷数字。

## Files

- `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/student_assignments.csv`
- `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/student_observations.csv`
- `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/student_questionnaires.csv`
- `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/student_private_key.json`
- `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/human_study_analysis.json`
