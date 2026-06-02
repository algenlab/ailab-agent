# AlgoLab 评估指标备忘

目标不是只评估“网页能不能打开”，而是评估算法教学页面是否正确、可信、可用，并且系统是否能拒绝错误产物。

## 一、核心评估维度

| 维度 | 指标名 | 评价问题 | 推荐评估方式 |
|---|---|---|---|
| 答案正确 | `answer_correctness` / `answer_pass_rate` | 最终输出是否等于 expected 或 oracle？ | deterministic oracle、verifier、expected comparison |
| 步骤正确 | `step_correctness` / `process_pass_rate` | 每一步状态转移是否符合算法规则？ | family process validator、trace invariant |
| 过程解释可信 | `process_faithfulness` | 解释、公式、依赖、变量变化是否和真实 trace 对齐？ | process validator、demo readiness、人工/VLM 辅助评审 |
| 可视化效果 | `visual_quality` | 布局是否清晰，关键状态是否可见，桌面/移动端是否可读？ | 真实浏览器截图、VLM rubric、人工复核 |
| 交互性 | `interaction_quality` | next/prev、公式展开、输入重跑、错误反馈等交互是否有效？ | browser smoke、Playwright 交互截图、人工复核 |

## 二、建议增加的评估维度

| 维度 | 指标名 | 评价问题 | 推荐评估方式 |
|---|---|---|---|
| 可验证性 | `verifiability` | 页面背后是否有机器可检查的 trace、deps、targets、invariant evidence？ | Schema check、trace validator、process validator |
| 可视化-过程对齐 | `visual_trace_alignment` | 当前高亮的数组格、节点、边、DP 单元格是否对应当前 trace step？ | SceneGraph validation、截图审计、VLM 辅助 |
| 解释完整度 | `explanation_completeness` | 是否说明当前为什么这样做、用了哪个 invariant、下一步为什么合法？ | demo readiness、VLM rubric、人工评分 |
| 边界输入鲁棒性 | `input_robustness` | 换成空数组、单元素、重复值、不可达图、退化树等输入后是否仍正确？ | unseen cases、property cases、input regeneration |
| 泛化能力 | `unseen_generalization` | 未见过的算法族/题型是否仍能生成正确可信页面？ | unseen family evaluation |
| 错误检出能力 | `error_detection` | 系统能否拒绝答案错、步骤错、解释错但看起来正常的页面？ | injected bad traces、negative cases、baseline audit |
| Repair 效果 | `repair_effectiveness` | repair 能救回多少失败？是否引入新错误？ | repair attempt/success rate、failure transition |
| 浏览器真实可用性 | `browser_usability` | HTML 是否加载、JS 是否报错、交互是否响应、截图是否非空？ | browser smoke、desktop/mobile screenshot |
| 成本与延迟 | `cost_latency` | 每个成功 case 花了多少 token、API 调用和时间？ | model usage、duration、token per success |
| 人类学习价值 | `human_learning_value` | 用户看完是否能理解 invariant、预测下一步、答对类似题？ | human study 或人工评分；没有人工数据时必须标为 missing |

## 三、最小论文指标集

主实验报告至少应包含：

- `answer_pass_rate`：答案正确率。
- `process_pass_rate`：过程 invariant 通过率。
- `demo_readiness_pass_rate`：教学演示完整性通过率。
- `scene_pass_rate`：SceneGraph 编译/验证通过率。
- `browser_smoke_pass_rate`：真实浏览器加载和基础交互通过率。
- `interaction_pass_rate`：关键交互截图或 Playwright 检查通过率。
- `final_release_pass_rate`：答案、过程、demo、SceneGraph、browser 全部通过的比例。
- `repair_attempt_rate`：进入 repair 的比例。
- `repair_success_rate`：进入 repair 后最终通过的比例。
- `unseen_pass_rate`：unseen family 上的最终通过率。
- `vlm_teaching_quality`：VLM 对截图教学质量的辅助评分。
- `human_teaching_quality`：人工教学质量评分；没有人工评分时必须明确 `missing`，不能用 VLM 冒充人工。
- `token_per_case`：每个 case 的平均 token。
- `token_per_success`：每个成功 case 的平均 token。
- `generation_time_per_case`：每个 case 的平均生成耗时。
- `failure_type_distribution`：失败类型分布。

## 四、Baseline 必须公平拆解

`direct_html_baseline` 不能只用 browser smoke 评价。后续必须把它拆成：

- `direct_html_browser_pass_rate`：网页是否能打开。
- `direct_html_answer_correctness`：页面给出的最终答案是否正确。
- `direct_html_step_correctness`：页面步骤是否符合算法规则。
- `direct_html_process_faithfulness`：解释是否和真实算法过程一致。
- `direct_html_visual_quality`：截图视觉质量。
- `direct_html_interaction_quality`：交互是否有效。

如果 direct HTML 只是“能打开、看起来好”，但答案或步骤经常错，那么 AlgoLab 的价值是严格验证和拒绝错误页面。

如果 direct HTML 在答案、步骤、解释、交互上也全面更好，则当前 AlgoLab full pipeline 还不足以支撑“优于 baseline”的主张，需要回到生成和 repair 侧改进。

## 五、VLM 与人工评分边界

- VLM 只能作为视觉教学质量辅助评审。
- VLM 不应判断最终答案是否正确。
- VLM 不应替代 answer oracle、process validator、demo readiness 或 browser smoke。
- VLM 分数必须和机器 gate pass/fail 分开展示。
- 人工评分缺失时，报告中应写 `human_teaching_quality=status: missing`。

## 六、当前结果应谨慎表述

可以表述：

- AlgoLab 能提供严格、可审计的算法过程验证。
- Process validator 能发现大量 direct HTML/browser smoke 无法发现的过程错误。
- Repair 明显提升通过率，但仍不是稳定解决方案。
- SceneGraph compiler 对教学可视化质量有明显贡献。
- 通过 gate 的页面在真实浏览器中较稳定。

不能表述：

- 不能说当前 full system 全面优于 direct HTML baseline。
- 不能把 `direct_html_baseline` 的 browser pass 当成算法正确性。
- 不能把 VLM 分数当成人工评分。
- 不能只用“网页能打开”证明系统达到科研级教学正确性。
