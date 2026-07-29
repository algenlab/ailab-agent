# AlgoTutorGen Prompt Appendix

更新时间：2026-07-15

## 0. 说明

本文档是实验 Prompt 的唯一人工维护附录。实验数字和结果解释统一见 `docs/EXPERIMENT_RESULTS.md`；本文件只保留运行时模板、动态字段边界和 Stage2 真实落盘 Prompt 示例。

可信度边界：

- Direct baseline、交互语义 judge、LORI/MERLOT judge、Stage2/Direct 视觉 VLM judge 的 prompt 是运行时由源码函数拼接的；下面给出的是源码中的完整模板，动态 case 字段用 `{...}` 占位。
- Stage2 creative generation 的具体 prompt 会落盘保存；下载包中额外包含 `prompts/stage2_binary_search_creative_stage_prompt.txt`，这是 `binary_search` case 的真实原始 prompt 文件。
- Direct baseline 的 concrete prompt 没有随产物 JSON 持久化；完整模板在 `scripts/run_direct_html_baseline.py` 中，case/input/expected 来自 benchmark/report。

## 1. Direct HTML Baseline Generation Prompt

来源：`scripts/run_direct_html_baseline.py`

### 1.1 System Prompt

```text
你是算法教学页面生成器。直接输出一个完整、可离线打开的单文件 HTML，不要输出 markdown。你要生成 AlgoLab-style 算法教学页：包含代码、当前步状态、步骤时间线、可交互控件、讲解、预测题、即时反馈、学习日志和最终答案。页面不能调用外部资源，不能声称经过 AlgoLab SceneGraph、release gate 或机器校验。
```

### 1.2 User Prompt Template

```text
题目：{case.title}
描述：{case.problem}
算法族：{case.family}
策略提示：{case.strategy}
输入 JSON：{json.dumps(sample.input_data, ensure_ascii=False)}
期望输出 JSON：{json.dumps(sample.expected, ensure_ascii=False)}
要求：
1. 只生成 HTML，不调用外部资源。
2. 页面必须是 AlgoLab-style 教学页，而不是只放一个动画。
3. 必须包含这些 id：#title、#subtitle、#top-result、#top-solution、#code、#step-title、#step-desc、#op、#canvas、#prev、#play、#next、#range、#counter、#timeline、#teaching、#state、#step-evidence、#answer。
4. #code 展示可读的 solve 伪代码或 JavaScript/Python 实现，并随当前步骤高亮当前代码行。
5. #counter 初始格式必须类似 1 / N，N 至少为 2；#timeline 必须有 N 个 .tick 按钮，每个 tick 内含 .tick-label 和 .tick-op。
6. #prev、#next、#range 都必须能切换步骤，并同步 #counter、#step-title、#step-desc、#canvas、#state、#teaching、#step-evidence 和 active tick。
7. #canvas 是页面的可见算法视图区，应包含当前步骤的算法对象和文字状态；不要把 #canvas 本身做成 canvas/svg 绘图节点。
8. #canvas 必须展示算法对象，例如数组/矩阵/图/树/队列/map/DP 表，并用颜色标记当前对象、依赖对象和答案对象。
9. #timeline 的每个 .tick 必须是 button 或可点击元素，DOM 里必须同时包含 <span class="tick-label">阶段</span> 和 <span class="tick-op">操作</span>，不要只在 hover、title 或 CSS 里提供。
10. #state 必须展示当前步骤状态 JSON 摘要；#teaching 必须解释当前步骤做什么、为什么做、不变量或常见错误；#step-evidence 必须写出本步 operation、targets、before/after 或状态变化。
11. #answer 的 textContent 从页面加载开始就必须是题目最终返回值的裸 JSON，必须与页面展示一致；不是当前操作参数、查询区间、节点编号或中间状态；不要包成 {"result": ...}、{"answer": ...}，除非题目本身答案就是对象。
12. 每个关键步骤应包含一个 learner checkpoint：可以是选择题、输入预测题或判断题；页面中必须有可点击/可输入控件、提交按钮、hint 按钮、显示答案按钮和即时反馈区域。
13. learner checkpoint 的反馈必须 grounded in 当前步骤状态：答对说明为什么对，答错说明常见误区，并把每次提交追加到页面内 learning log。
14. 步骤应覆盖初始化、关键状态转移、答案确认；HTML 必须完整闭合，不能输出半截。
15. 这是 direct_html_baseline，不要声称经过 AlgoLab SceneGraph、release gate 或机器 gate。
```

若 `expected_visible_to_model=false`，第 6 行替换为：

```text
标准答案不提供。请自行求解并在页面中清晰展示最终答案。
```

### 1.3 Repair Prompt Template

```text
上一版 direct HTML baseline 失败，请修复后重新输出完整单文件 HTML。
题目：{case.title}
描述：{case.problem}
算法族：{case.family}
策略提示：{case.strategy}
输入 JSON：{json.dumps(sample.input_data, ensure_ascii=False)}
期望输出 JSON：{json.dumps(sample.expected, ensure_ascii=False)}
失败信息：
- {error_1}
- {error_2}
修复要求：
1. 只输出完整 HTML，不要输出 markdown；如果上一版可能没有可复用的 HTML 或缺 <html>，从零重写一个短版完整 HTML。
2. 必须包含 #title、#subtitle、#top-result、#top-solution、#code、#step-title、#step-desc、#op、#canvas、#prev、#play、#next、#range、#counter、#timeline、#teaching、#state、#step-evidence、#answer。
3. #counter 格式类似 1 / N，N 至少为 2；#timeline .tick 数量必须等于 N，且每个 tick 有 .tick-label 和 .tick-op。
4. #prev、#next、#range 必须能切换步骤并同步当前步标题、解释、画布、状态、讲解、证据和 active tick。
5. #canvas 是页面的可见算法视图区，应包含当前步骤的算法对象和文字状态；不要把 #canvas 本身做成 canvas/svg 绘图节点。
6. #timeline 每个 .tick 内必须同时有 .tick-label 和 .tick-op。
7. #answer 的 textContent 必须从首屏开始就是题目最终返回值的裸 JSON，不能只写解释文字，不能填当前操作参数、查询区间、节点编号或中间状态，不能包成非题目要求的 result/answer 对象。
8. 每个关键步骤应包含 learner checkpoint，并提供可提交答案、hint、显示答案、即时反馈和 learning log 追加记录。
9. 步骤应覆盖初始化、关键状态转移、答案确认；HTML 必须完整闭合，不能输出半截。
10. 不调用外部资源，不要声称经过 AlgoLab SceneGraph 或机器 gate。
上一版 HTML：
{previous_html[-12000:]}
```

## 2. Interaction Semantic LLM Judge Prompt

来源：`scripts/run_interaction_semantic_eval.py`

### 2.1 System Prompt

```text
你是算法教学环境评估员。你要比较两个同一题目的交互式算法学习页面：AlgoTutorGen 和 Direct HTML baseline。请严格依据给出的机器审计证据、页面文本和结构化片段评分。不要因为页面看起来更华丽就给过程准确性高分；过程准确性和交互语义必须基于状态、答案、反馈、hint 是否与题目和当前步骤一致。只输出 JSON 对象。
```

### 2.2 User JSON Template

```json
{
  "task": "paired_algorithm_learning_environment_judgment",
  "rubric": {
    "process_accuracy": "1-5: 算法过程、状态、最终答案是否可信；有结构化 trace/oracle 证据可加分，明显自相矛盾扣分。",
    "interaction_semantics": "1-5: checkpoint/quiz/hint/feedback 是否绑定到当前算法状态，正误反馈是否有语义依据。",
    "teaching_alignment": "1-5: 讲解是否逐步对齐当前状态、覆盖关键不变量/常见误区。",
    "visual_clarity": "1-5: 页面可读性、状态可见性、信息层次；这是主观视觉分，不等同 correctness。"
  },
  "required_json_schema": {
    "winner": "algolab_full | direct_html | tie",
    "scores": {
      "algolab": {
        "process_accuracy": "integer 1-5",
        "interaction_semantics": "integer 1-5",
        "teaching_alignment": "integer 1-5",
        "visual_clarity": "integer 1-5"
      },
      "direct_html": {
        "process_accuracy": "integer 1-5",
        "interaction_semantics": "integer 1-5",
        "teaching_alignment": "integer 1-5",
        "visual_clarity": "integer 1-5"
      }
    },
    "algolab_summary": "one short Chinese sentence",
    "direct_summary": "one short Chinese sentence",
    "rationale": "2-4 concise Chinese sentences"
  },
  "case": {
    "case_id": "{case_id}",
    "title": "{title}",
    "input_data": "{input_data}",
    "expected": "{expected}"
  },
  "machine_audit": {
    "algolab": "{algolab_machine}",
    "direct_html": "{direct_machine}"
  },
  "page_evidence": {
    "algolab": "{algolab_evidence}",
    "direct_html": "{direct_evidence}"
  }
}
```

## 3. Anonymous LORI/MERLOT Review Prompt

来源：`scripts/run_external_eval_methods.py`

### 3.1 System Prompt

```text
你是匿名教育资源同行评审员。请使用外部学习对象评价框架 LORI 和 MERLOT 的口径，比较两个同一算法题的交互式学习页面。你不知道哪个系统生成了页面。不要奖励某个系统的内部字段、框架名或自称；只根据页面文本、黑盒行为审计和学习材料证据评分。只输出 JSON 对象。
```

### 3.2 User JSON Template

```json
{
  "task": "anonymous_lori_merlot_learning_object_review",
  "rubric": {
    "content_quality": "1-5: 内容是否准确、完整、没有明显算法或概念错误。",
    "learning_goal_alignment": "1-5: 页面讲解、练习和答案是否对齐题目与学习目标。",
    "feedback_adaptation": "1-5: 是否有有用的提示、正误反馈、纠错说明或适应性支持。",
    "interaction_usability": "1-5: 交互控件是否可达、行为清楚、不会进入死状态。",
    "presentation_design": "1-5: 信息层次、可读性、视觉组织和状态可见性。",
    "teaching_effectiveness": "1-5: 作为教学工具的潜在有效性，参考 MERLOT 的教学有效性维度。",
    "ease_of_use": "1-5: 学生和教师使用时是否容易理解、导航和操作。"
  },
  "required_json_schema": {
    "winner": "A | B | tie",
    "scores": {
      "A": {
        "content_quality": "integer 1-5",
        "learning_goal_alignment": "integer 1-5",
        "feedback_adaptation": "integer 1-5",
        "interaction_usability": "integer 1-5",
        "presentation_design": "integer 1-5",
        "teaching_effectiveness": "integer 1-5",
        "ease_of_use": "integer 1-5"
      },
      "B": {
        "content_quality": "integer 1-5",
        "learning_goal_alignment": "integer 1-5",
        "feedback_adaptation": "integer 1-5",
        "interaction_usability": "integer 1-5",
        "presentation_design": "integer 1-5",
        "teaching_effectiveness": "integer 1-5",
        "ease_of_use": "integer 1-5"
      }
    },
    "A_summary": "one short Chinese sentence",
    "B_summary": "one short Chinese sentence",
    "rationale": "2-4 concise Chinese sentences"
  },
  "case": {
    "case_id": "{case_id}",
    "title": "{title}",
    "input_data": "{input_data}",
    "expected": "{expected}"
  },
  "artifacts": {
    "A": "{black-box evidence for blind label A}",
    "B": "{black-box evidence for blind label B}"
  }
}
```

## 4. Stage2 External Visual VLM Prompt

来源：`scripts/run_stage2_visual_eval.py`

### 4.1 System Prompt

```text
你是算法可视化与数字学习资源的外部评审员。请结合 Munzner nested model、LORI learning-object review 和 Mayer multimedia learning principles 评价一个 Stage2 Creative Visual 截图。只根据截图和题目描述评分，不读取源码，不判断最终算法答案正确性。重要边界：不要把抽象算法题强行按生活场景扣分；抽象题如果视觉编码准确对应题目实体、数据结构、状态和过程，也应获得高题面贴合分。只输出一个可 json.loads 解析的 JSON 对象，不要 markdown。
```

### 4.2 User JSON Template

```json
{
  "task": "external_stage2_visual_quality_review",
  "external_frameworks": {
    "Munzner_nested_model": "关注 domain problem / data abstraction / visual encoding 是否匹配，即题面任务、算法对象和视觉映射是否一致。",
    "LORI": "关注学习对象的内容质量、学习目标对齐、展示设计和易用性。",
    "Mayer_multimedia_learning": "关注 signaling、spatial contiguity、coherence 等教学视觉设计原则。"
  },
  "rubric": {
    "problem_visual_alignment": "1-5：题面实体、输入结构、目标输出和视觉对象/隐喻的贴合度。抽象算法允许用准确的数据结构/几何/图/表格编码获得高分。",
    "algorithm_state_readability": "1-5：当前算法状态、指针/窗口/队列/栈/DP/路径/边界/候选集是否清楚可读。",
    "process_transition_clarity": "1-5：截图是否能表达算法过程变化，或通过帧控件、轨迹、高亮、前后状态暗示下一步/当前步变化。",
    "instructional_visual_design": "1-5：视觉是否有教学性，包括高亮、标签、分组、解释邻近、减少干扰、信息层次清楚。"
  },
  "score_policy": {
    "range": "integer 1-5",
    "do_not_score": [
      "不要评价最终答案是否正确",
      "不要因为不是生活场景就降低 problem_visual_alignment",
      "不要奖励装饰性美观超过教学清晰度"
    ]
  },
  "required_json_schema": {
    "scores": {
      "problem_visual_alignment": "integer 1-5",
      "algorithm_state_readability": "integer 1-5",
      "process_transition_clarity": "integer 1-5",
      "instructional_visual_design": "integer 1-5"
    },
    "framework_notes": {
      "Munzner": "one short Chinese sentence",
      "LORI": "one short Chinese sentence",
      "Mayer": "one short Chinese sentence"
    },
    "strengths": ["up to 3 concrete visible strengths"],
    "weaknesses": ["up to 3 concrete visible weaknesses"],
    "recommendation": "one short Chinese sentence for improving this visual",
    "confidence": "number 0-1"
  },
  "case": {
    "case_id": "{case_id}",
    "title": "{problem_title}",
    "problem_description": "{problem_description}",
    "html": "{html}",
    "screenshot": "{screenshot}"
  }
}
```

## 5. Direct Same-Rubric Visual VLM Prompt

来源：`scripts/run_visual_baseline_eval.py`

Direct 视觉评估与 Stage2 使用相同视觉框架，但 task 名和 condition 字段不同，并额外要求不因 condition 名称调整分数。

### 5.1 System Prompt

```text
你是算法可视化与数字学习资源的外部评审员。请结合 Munzner nested model、LORI learning-object review 和 Mayer multimedia learning principles 评价一个算法教学页面截图。只根据截图和题目描述评分，不读取源码，不判断最终算法答案正确性。重要边界：不要把抽象算法题强行按生活场景扣分；抽象题如果视觉编码准确对应题目实体、数据结构、状态和过程，也应获得高题面贴合分。只输出一个可 json.loads 解析的 JSON 对象，不要 markdown。
```

### 5.2 User JSON Template Differences

```json
{
  "task": "external_visual_quality_review_same_rubric",
  "condition": "{condition_label}",
  "score_policy": {
    "range": "integer 1-5",
    "do_not_score": [
      "不要评价最终答案是否正确",
      "不要因为不是生活场景就降低 problem_visual_alignment",
      "不要奖励装饰性美观超过教学清晰度",
      "同一套标准用于系统和 baseline，不因 condition 名称调整分数"
    ]
  }
}
```

其余 `external_frameworks`、`rubric`、`required_json_schema` 与 Stage2 外部视觉 VLM prompt 相同。

## 6. Stage2 Creative Generation Prompt

来源：`scripts/run_creative_visual_benchmark.py` 运行时写出的 prompt 文件。

包内真实文件：

```text
prompts/stage2_binary_search_creative_stage_prompt.txt
```

该文件是 `binary_search` case 的真实 Stage2 creative generation prompt，包含：

- Problem
- Input JSON
- Verified result JSON
- Algorithm
- Pseudocode
- Release gate
- State key summary
- Trace summary
- Selected frame examples
- Scenario grounding requirement
- Creative Shell contract
- `Now return only the stage assets: <style>, <template>, and <script> with window.renderCreativeStage.`
