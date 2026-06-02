# AAAI 实验设计、Benchmark 与评分标准

本文档定义 P0 到 P17 收口后的全套实验。目标不是继续堆功能，而是用可复现 benchmark、真实浏览器截图、真实 LLM 生成、VLM 截图评审和 baseline / ablation 证明系统能力。

当前重点：

- 先确认当前系统 69 个 deterministic 算法页面在真实浏览器中没有明显问题。
- 再跑真实 LLM 生成能力实验。
- 再跑 unseen、baseline、ablation 和 VLM 评审。
- 实验过程中允许修复可复现 bug，但不能改变实验口径。

当前事实：

- 已有 deterministic benchmark：69 cases / 250 samples。
- 已有真实浏览器截图入口：`scripts/capture_phase17_screenshots.py`。
- 已有真实 LLM benchmark 入口：`scripts/run_llm_benchmark.py`。
- 已有多模态调用入口：`llm_client.chat_vision()`。
- 还没有完整 VLM 截图评分脚本、VLM rubric report、VLM merge 到 evaluation report 的实现。
- 目前真实 LLM 主要参与 solve / trace / verifier 生成和 repair；VLM 只应作为离线评审者，不进入主发布链路。
- 当前默认生成 LLM 是 `llm_client.DEFAULT_MODEL = "gemini-3.1-pro-preview"`，可由 `ALGOLAB_LLM_MODEL` 覆盖。
- 当前默认 VLM 是 `llm_client.VISION_MODEL = "gemini-3-flash-preview"`，执行 AI 必须在 VLM report 中记录实际使用模型，必要时支持参数覆盖。
- 当前 LLM benchmark 已记录 model、started_at、ended_at、duration_s 和 phase_summary，但 token usage 记录还不完整。执行 AI 必须补齐模型调用级 token、耗时和成本估算字段。

## 1. 研究问题

本轮实验回答五个问题。

RQ1：机器可验证正确性  
AlgoLab 能否在 deterministic benchmark 上稳定通过 answer oracle、family process validator、demo readiness、SceneGraph、renderer 和 browser gate？

RQ2：真实浏览器可用性  
AlgoLab 生成的页面是否能在真实浏览器中加载、步进、交互、截图，并在 desktop / mobile 下保持可读？

RQ3：真实 LLM 生成能力  
真实 LLM 生成 solve / trace / verifier 后，完整 AlgoLab pipeline 能否校验、repair、编译并渲染成可用教学页面？

RQ4：教学视觉质量  
在不让 VLM 判断算法正确性的前提下，VLM 对截图的布局、状态可见性、解释质量、交互可发现性和证据对齐度评分如何？

RQ5：系统模块贡献  
相对 direct HTML、no process validator、no SceneGraph compiler、no repair 等对照，完整系统的通过率、失败类型和 VLM 教学质量是否更好？

## 2. LLM 与 VLM 职责边界

LLM 参与：

- `algolab_full`：LLM 生成 solve / trace / verifier 候选。
- repair：LLM 根据结构化 failure context 修复候选。
- direct HTML baseline：LLM 直接生成 HTML，只作为外部 baseline。
- pure LLM judge baseline：LLM 判断输出是否好，只作为外部对照。

VLM 参与：

- 读取真实浏览器截图和 metadata。
- 评价教学/视觉质量。
- 不读取源码。
- 不执行算法。
- 不判断 final answer 是否正确。
- 不替代 answer oracle、process validator、demo readiness 或 browser smoke。

模型记录要求：

- 每个 LLM / VLM report 必须记录 `model`、`base_url`、`api_key_configured`、`api_key_source`、`timeout_s`、`max_tokens`。
- 每次模型调用必须尽量记录 `prompt_tokens`、`completion_tokens`、`total_tokens`、`duration_s`、`started_at`、`ended_at`。
- 如果 OpenAI-compatible endpoint 没有返回 usage，必须显式写 `usage_available=false`，不能静默缺失。
- 如果 usage 可用，summary 必须聚合 token 总量、平均 token、平均耗时和每个 condition 的 token 总量。
- 成本字段可以先记录为 `estimated_cost=null`，但必须保留 `pricing_source` 和 `cost_estimation_available=false`。

禁止：

- 用 VLM 分数替代机器 gate。
- 用 direct HTML baseline 进入 AlgoLab 主发布路径。
- 用 `--condition direct_html_baseline` 这种标签冒充真实 baseline。
- 为提高通过率修改 benchmark expected output。
- 放宽 validator、oracle、demo readiness 或 browser smoke。
- 删除失败 case、隐藏失败记录或跳过失败 family。

## 3. Benchmark 设计

### B0 deterministic machine gate

数据：

- `tests/benchmark_cases.py`
- 69 cases / 250 samples
- gate layers：`family_core=60 cases / 213 samples`，`expansion=9 cases / 37 samples`

验证：

- answer oracle
- process validator
- demo readiness
- SceneGraph compiler
- renderer
- browser smoke

用途：

- 证明系统基本正确性和可复现性。
- 不调用真实 LLM。

### B1 deterministic screenshot benchmark

数据：

- 69 个 deterministic case。
- 每个 case 生成 desktop 和 mobile 截图。
- dashboard 生成 desktop 和 mobile 截图。
- 交互截图 4 张：公式展开前、公式展开后、输入重新生成 payload、错误反馈。

预期数量：

- 页面截图：140 张。
- 交互截图：4 张。
- 总截图：144 张。

用途：

- 证明页面真实可加载、可见、可交互。
- 为 VLM 评分和论文图准备素材。

### B2 deterministic VLM screenshot benchmark

数据：

- B1 的 144 张截图。

评分：

- VLM 对每张截图按固定 rubric 打分。
- condition 固定为 `deterministic`。

用途：

- 评估当前系统页面视觉教学质量。
- 发现文字重叠、移动端不可读、状态不明显、交互不明显等问题。

### B3 live LLM deterministic benchmark

数据：

- 与 deterministic benchmark 同一 69 case 集合。
- primary setting：每个 case 跑 sample 0。
- secondary setting：预算允许时跑 `--all-samples`。

condition：

- `algolab_full`

用途：

- 评估真实 LLM 在已有算法族和已知风格上的生成能力。
- 记录生成失败、repair 成功、答案错误、trace schema 错、process invariant 错、demo readiness 错、scene/html 错。

### B4 unseen family benchmark

数据：

- `benchmark/unseen_family_cases.json`
- 只含题目描述、family / subfamily 元数据、sample input 和 expected output。
- 不含 deterministic `code`、`tracker_code` 或 `verifier_code`。

condition：

- `algolab_full`

用途：

- 评估 strong family 的真实泛化能力。
- 区分 seen-style 和 unseen-style。

### B5 baseline / ablation benchmark

必须包含：

- `direct_html_baseline`：LLM 直接生成单文件 HTML，真实浏览器加载。
- `no_process_validator`：不执行 family process invariant，观察错误是否逃过过程门禁。
- `no_scenegraph_compiler`：不经过 SceneGraph compiler，观察 scene/html/interaction 失败。
- `no_repair`：完整 pipeline，但 `max_rounds=0`。

可选：

- `pure_llm_judge`：LLM 只做 judge，不执行机器 gate，用于比较 judge 和 oracle/validator 的分歧。

用途：

- 证明系统模块贡献。
- 不允许只改 condition 标签。每个 condition 必须有真实不同执行路径或明确外部 report。

### B6 condition VLM benchmark

数据：

- `algolab_full`、unseen、direct HTML baseline、no process validator、no SceneGraph compiler、no repair 的真实浏览器截图。

用途：

- 比较不同 condition 的视觉教学质量。
- VLM 评分必须与机器通过率分开展示。

## 4. 指标设计

### 4.1 机器正确性指标

- `answer_pass_rate`：expected 与 actual / oracle 通过比例。
- `process_pass_rate`：family process validator 通过比例。
- `demo_readiness_pass_rate`：演示完整性通过比例。
- `scene_pass_rate`：SceneGraph 可编译和可验证比例。
- `html_smoke_pass_rate`：真实浏览器加载和基础交互通过比例。
- `overall_release_ready`：answer、process、demo、scene、HTML 全部通过。

### 4.2 LLM 生成指标

- `generation_success_rate`：LLM 输出可解析 spec 的比例。
- `materialization_success_rate`：spec 能执行并产出 artifact 的比例。
- `repair_attempt_rate`：进入 repair 的比例。
- `repair_success_rate`：repair 后最终通过的比例。
- `final_pass_rate`：完整 pipeline 最终通过比例。
- `timeout_rate`：超时比例。
- `avg_duration_s`：平均耗时。
- `total_prompt_tokens`：所有 LLM 生成和 repair 调用的 prompt token 总量；usage 不可用时为 `null`。
- `total_completion_tokens`：所有 LLM 生成和 repair 调用的 completion token 总量；usage 不可用时为 `null`。
- `total_tokens`：所有 LLM 调用 token 总量；usage 不可用时为 `null`。
- `usage_available_rate`：返回 token usage 的调用比例。
- `avg_tokens_per_case`：平均每个 case 的 token 使用量；usage 不可用时为 `null`。
- `estimated_cost`：按配置价格估算的成本；没有价格配置时为 `null`。

### 4.2.1 模型调用统计字段

执行 AI 必须完善 LLM 和 VLM report 的模型调用统计。report summary 至少包含：

```json
{
  "model_usage": {
    "usage_available": true,
    "call_count": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "duration_s": 0.0,
    "avg_duration_s": 0.0,
    "avg_total_tokens": 0.0,
    "estimated_cost": null,
    "cost_estimation_available": false,
    "pricing_source": ""
  }
}
```

每个 result 至少包含：

```json
{
  "model_calls": [
    {
      "kind": "generation|repair|vlm_eval|direct_html|judge",
      "model": "gemini-3.1-pro-preview",
      "started_at": "2026-05-30T00:00:00",
      "ended_at": "2026-05-30T00:00:05",
      "duration_s": 5.0,
      "usage_available": true,
      "prompt_tokens": 0,
      "completion_tokens": 0,
      "total_tokens": 0
    }
  ]
}
```

如果底层 `llm_client.chat_json()` / `chat_text()` / `chat_vision()` 当前不返回 usage，执行 AI 应优先新增非破坏性 wrapper 或扩展返回 metadata 的函数，例如：

- `chat_json_with_metadata()`
- `chat_text_with_metadata()`
- `chat_vision_with_metadata()`

不能破坏既有调用者。新增函数必须有测试，覆盖 usage 存在和 usage 缺失两种响应。

### 4.3 失败类型

固定 failure type：

- `generation`
- `json_parse`
- `answer_mismatch`
- `trace_schema`
- `trace_step`
- `target_error`
- `dependency_error`
- `process_invariant`
- `coverage_error`
- `demo_readiness`
- `scene_error`
- `html_error`
- `browser_error`
- `timeout`
- `vlm_eval_error`
- `unknown`

每个失败 result 必须有 `failure_type`，不能只写失败文本。

### 4.4 浏览器截图指标

- `screenshot_count`
- `desktop_count`
- `mobile_count`
- `interaction_screenshot_count`
- `console_error_count`
- `page_error_count`
- `empty_body_count`
- `empty_canvas_count`
- `zero_byte_screenshot_count`
- `manifest_ok`

### 4.5 VLM 评分指标

每张截图按 1 到 5 分：

- `layout_readability`
- `algorithm_state_visibility`
- `teaching_explanation`
- `interaction_affordance`
- `evidence_alignment`
- `overall_teaching_quality`

汇总：

- 每个 condition 的平均分。
- 每个算法族的平均分。
- desktop / mobile 分开平均。
- 低分截图列表：任一维度小于等于 2。
- 高置信问题列表：`confidence >= 0.7` 且存在 issues。

VLM 分数只作为教学质量辅助指标，不影响机器 gate pass/fail。

## 5. VLM 评分标准

### layout_readability

5 分：

- 页面布局清晰。
- 主要内容在首屏或合理滚动范围内。
- 文字没有重叠、截断、溢出。
- desktop 和 mobile 都可读。

3 分：

- 基本可读，但存在局部拥挤、滚动过长、字号偏小或次要文本难读。

1 分：

- 页面空白、严重重叠、关键文本被遮挡、移动端几乎不可读。

### algorithm_state_visibility

5 分：

- 当前数据结构、当前目标、关键状态、已处理/未处理部分清楚可见。
- 依赖关系或路径/指针/区间覆盖能被识别。

3 分：

- 能看出算法状态，但关键对象不够突出，依赖或变化需要读很多文字才能理解。

1 分：

- 看不出当前算法状态，关键数据结构缺失或不可辨认。

### teaching_explanation

5 分：

- 当前步骤解释具体。
- 公式、状态变化、before/after、原因都能支持学习。
- 对错误或边界条件有清晰提示。

3 分：

- 有解释，但偏模板化，缺少本步为什么这样做。

1 分：

- 解释缺失、泛泛而谈，或与截图状态不匹配。

### interaction_affordance

5 分：

- 播放、步进、预测、输入、judge、公式展开或依赖点击等交互入口清楚。
- 交互反馈明确。

3 分：

- 有交互，但入口不明显或反馈较弱。

1 分：

- 交互缺失、不可发现、点击后无反馈，或反馈和操作不一致。

### evidence_alignment

5 分：

- 截图内容与 visible evidence、targets、deps、formula、validation summary 对齐。
- 没有明显“页面展示和证据不一致”的问题。

3 分：

- 大体一致，但 evidence 信息过弱或需要推断。

1 分：

- 展示内容与证据明显不一致，或 evidence 缺失导致无法判断。

### overall_teaching_quality

5 分：

- 适合作为论文案例图或教学 demo。
- 学习者能从截图理解当前算法步骤。

3 分：

- 可用但不够清晰，需要补充说明。

1 分：

- 不适合展示，无法支撑教学。

## 6. VLM Prompt 设计要求

规划 AI 不在本文档中固定最终 VLM 提示词。执行 AI 必须基于第 5 节评分标准认真设计 VLM prompt，并把 prompt 作为实验产物保存和测试。

执行 AI 必须新增或生成：

- `benchmark/vlm_screenshot_rubric.json`
- `algolab/generation/prompts/vlm_screenshot_judge_system.txt` 或等价 prompt 文件
- `algolab/generation/prompts/vlm_screenshot_judge_user.txt` 或等价 prompt 模板
- `tests/regression/vlm_evaluation.py`

Prompt 设计必须满足：

- 明确 VLM 只评价截图教学/视觉质量。
- 明确 VLM 不判断算法答案正确性。
- 明确 VLM 不能读取源码或推断截图外内容。
- 明确低分条件：文字重叠、内容截断、空白 canvas、移动端不可读、关键状态不可见、交互反馈不清晰。
- 明确输出严格 JSON。
- 明确每个维度 1 到 5 分。
- 明确 `confidence`、`issues`、`suggested_caption` 的格式。
- 明确 dashboard、普通算法页面、interaction screenshot 三类截图的不同关注点。

执行 AI 必须自己审计 prompt，至少检查：

- prompt 中没有要求 VLM 判断 final answer 正确性。
- prompt 中没有要求 VLM 给 release/pass/fail 结论。
- prompt 中没有鼓励根据美观程度替代教学清晰度。
- prompt 中包含移动端可读性要求。
- prompt 中包含“只看截图可见内容”的约束。

Prompt 版本必须记录：

- `prompt_version`
- `prompt_hash`
- `rubric_version`
- `rubric_hash`
- `judge_model`
- `created_at`

执行 AI 可以调整 prompt，但每次调整都必须说明原因，并保留最终 prompt 文件路径。

VLM 返回 JSON 必须满足：

```json
{
  "case_id": "...",
  "condition": "...",
  "screenshot": "...",
  "viewport": "desktop|mobile",
  "scores": {
    "layout_readability": 1,
    "algorithm_state_visibility": 1,
    "teaching_explanation": 1,
    "interaction_affordance": 1,
    "evidence_alignment": 1,
    "overall_teaching_quality": 1
  },
  "confidence": 0.0,
  "issues": [
    {
      "severity": "low|medium|high",
      "category": "layout|state|explanation|interaction|evidence|other",
      "message": "short concrete issue"
    }
  ],
  "suggested_caption": "one short paper-friendly caption",
  "judge_model": "model name",
  "model_call": {
    "duration_s": 0.0,
    "usage_available": false,
    "prompt_tokens": null,
    "completion_tokens": null,
    "total_tokens": null
  }
}
```

### VLM 输出约束

- JSON 必须可被 `json.loads` 解析。
- 每个 score 必须是 1 到 5 的整数。
- `confidence` 必须在 0 到 1。
- `issues` 可以为空数组。
- `suggested_caption` 不超过 30 个英文词或 50 个中文字符。
- 如果 VLM 输出非法 JSON，记录 `vlm_eval_error`，不要中断整个 batch。
- VLM 输出和 report 必须记录 token usage 和耗时；如果 usage 不可用，显式写 `usage_available=false`。

## 7. 实验执行步骤

执行 AI 必须按顺序做。每轮只选择最靠前的 `状态：待执行。` 阶段完成，不允许跳到后面的阶段。

阶段完成后，执行 AI 必须把该阶段状态改为 `状态：已完成。`，并在该阶段下补充本轮完成证据：

- 修改文件。
- 新增或修改的测试。
- 实际运行命令。
- 关键输出路径。
- 测试结果。
- 若修复 bug，记录失败命令、最小修复和复跑证据。

如果阶段因环境或外部服务无法继续，执行 AI 必须把状态改为 `状态：阻塞。`，写明阻塞命令、错误信息和恢复条件。

### E1 deterministic gate

状态：已完成。

命令：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_v1_release_gate.py --output-dir output/aaai_release_gate
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/aaai_release_gate
bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py
```

验收：

- `quality_checks: PASS`
- family gate 为 69 cases / 250 samples。
- answer、process、demo readiness 都为 1.0。
- fallback / uncovered / degradation 均为 0。

完成证据（2026-05-30）：

- 修改文件：仅更新 `docs/08_AAAI_EXPERIMENT_PLAN.md` 中 E1 状态和完成证据。
- 新增或修改的测试：无，本阶段只执行既有 deterministic gate。
- 实际运行命令：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_v1_release_gate.py --output-dir output/aaai_release_gate`
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py --output-dir output/aaai_release_gate`
  - `bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py`
- 关键输出路径：
  - `output/aaai_release_gate/v1_release_gate.json`
  - `output/aaai_release_gate/v1_release_gate.md`
  - `output/aaai_release_gate/family_release_gate.json`
  - `output/aaai_release_gate/family_release_gate.md`
- 测试结果：
  - `quality_checks: PASS`
  - family gate：69 cases / 250 samples。
  - gate layers：family_core 60 cases / 213 samples，expansion 9 cases / 37 samples。
  - answer_pass_rate=1.0，process_pass_rate=1.0，demo_readiness_pass_rate=1.0。
  - process_fallback_cases=0，process_uncovered_cases=0，degraded_family_count=0。
  - degradation_summary 中 answer_only、demo_warn、process_fallback、process_uncovered、schema_scene_only 的 cases/samples 均为 0。
- Bugfix：无；未修改 expected，未放宽 gate，未跳过 case。

### E2 全量真实浏览器截图

状态：已完成。

命令：

```bash
CASE_ARGS=$(/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY'
from tests.benchmark_cases import benchmark_cases
print(" ".join(f"--case {case.id}" for case in benchmark_cases()))
PY
)

bash scripts/run_browser_smoke_container.sh python scripts/capture_phase17_screenshots.py \
  --output-dir output/aaai_screenshots_all \
  --dashboard-dir output/aaai_dashboard_all \
  $CASE_ARGS
```

验收脚本：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("output/aaai_screenshots_all/phase17_screenshots.json").read_text(encoding="utf-8"))
page_records = [r for r in data["screenshots"] if r.get("kind") == "page"]
interaction_records = data["interaction_screenshots"]
assert data["ok"] is True
assert len(data["demo_ids"]) == 69
assert len(page_records) == 140
assert len(interaction_records) == 4
assert all(r["bytes"] > 0 for r in data["screenshots"])
assert all(not r["errors"] for r in data["screenshots"])
for record in data["screenshots"]:
    assert Path(record["screenshot"]).exists(), record["screenshot"]
PY
```

完成证据（2026-05-30）：

- 修改文件：仅更新 `docs/08_AAAI_EXPERIMENT_PLAN.md` 中 E2 状态和完成证据。
- 新增或修改的测试：无，本阶段只执行既有截图采集与验收脚本。
- 实际运行命令：
  - `CASE_ARGS=$(/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... PY)`
  - `bash scripts/run_browser_smoke_container.sh python scripts/capture_phase17_screenshots.py --output-dir output/aaai_screenshots_all --dashboard-dir output/aaai_dashboard_all $CASE_ARGS`
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... PY`（执行本阶段验收脚本）
- 关键输出路径：
  - `output/aaai_screenshots_all/phase17_screenshots.json`
  - `output/aaai_dashboard_all/dashboard.json`
  - `output/aaai_dashboard_all/index.html`
  - `output/aaai_dashboard_all/dashboard_core_table.csv`
- 测试结果：
  - `phase17_screenshots.json` 中 `ok=true`。
  - `demo_ids=69`。
  - `screenshots=144`，其中 `page_records=140`，`interaction_records=4`。
  - `viewport_counts={"desktop": 74, "mobile": 70}`。
  - `kind_counts={"page": 140, "interaction": 4}`。
  - `zero_byte_records=0`，`records_with_errors=0`，`missing_files=0`。
  - 截图字节范围：`min_bytes=233739`，`max_bytes=5481944`。
- Bugfix：无；未修改 expected，未放宽 gate，未跳过 case。

### E3 VLM deterministic screenshot scoring

状态：已完成。

当前需要执行 AI 补实验基础设施。

允许新增：

- `scripts/run_vlm_screenshot_eval.py`
- `tests/regression/vlm_evaluation.py`
- `benchmark/vlm_screenshot_rubric.json`
- VLM prompt 文件

脚本参数：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_vlm_screenshot_eval.py \
  --manifest output/aaai_screenshots_all/phase17_screenshots.json \
  --condition deterministic \
  --output-dir output/aaai_vlm_deterministic
```

输出：

- `output/aaai_vlm_deterministic/vlm_screenshot_scores.json`
- `output/aaai_vlm_deterministic/vlm_screenshot_scores.csv`
- `output/aaai_vlm_deterministic/vlm_screenshot_summary.csv`

测试：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.vlm_evaluation
```

测试必须覆盖：

- fake VLM 合法 JSON。
- fake VLM 非法 JSON。
- 分数范围校验。
- batch 中单个 VLM 失败不影响其他截图。
- condition / case_id / viewport / screenshot 字段不丢失。
- token usage 可用时写入 prompt/completion/total tokens。
- token usage 不可用时写入 `usage_available=false`。
- prompt version/hash 和 rubric version/hash 进入 report。

完成证据（2026-05-30）：

- 修改文件：
  - `llm_client.py`
  - `scripts/run_vlm_screenshot_eval.py`
  - `tests/regression/vlm_evaluation.py`
  - `benchmark/vlm_screenshot_rubric.json`
  - `algolab/generation/prompts/vlm_screenshot_judge_system.txt`
  - `algolab/generation/prompts/vlm_screenshot_judge_user.txt`
  - `docs/08_AAAI_EXPERIMENT_PLAN.md`
- 新增或修改的测试：
  - 新增 `tests/regression/vlm_evaluation.py`。
  - 覆盖 fake VLM 合法 JSON、非法 JSON、异常不中断 batch、分数范围校验、字段保留、usage 可用/不可用、prompt/rubric 版本哈希、空响应重试、caption 长度规则、VLM timeout/max_tokens 配置。
- 实际运行命令：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.vlm_evaluation`
  - `ALGOLAB_VLM_TIMEOUT_S=60 /ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... PY`（1x1 PNG VLM 探测，返回上游 500）
  - `ALGOLAB_VLM_TIMEOUT_S=60 ALGOLAB_VLM_MAX_TOKENS=128 /ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... PY`（64x64 PNG VLM 探测，成功返回 JSON，duration_s=3.9，total_tokens=1213）
  - `ALGOLAB_VLM_MAX_TOKENS=128 /ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... PY`（真实 dashboard 截图探测，调用成功但 content 为空，completion_tokens=124）
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... PY`（真实 dashboard 截图默认 1024 token 探测，成功返回 JSON，duration_s=5.613，total_tokens=1462）
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_vlm_screenshot_eval.py --manifest output/aaai_screenshots_all/phase17_screenshots.json --condition deterministic --output-dir output/aaai_vlm_deterministic`（初跑 1024 token：144 total，14 passed，130 failed，failure_types={"vlm_eval_error":130}）
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_vlm_screenshot_eval.py --manifest output/aaai_screenshots_all/phase17_screenshots.json --condition deterministic --output-dir output/aaai_vlm_deterministic`（加异常容错、caption 修复和 1 次重试后复跑：144 total，51 passed，93 failed，failure_types={"vlm_eval_error":93}）
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY' ... PY`（4096 token 单张 dashboard 完整 prompt 探测，成功返回 JSON，duration_s=13.638，total_tokens=4640）
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_vlm_screenshot_eval.py --manifest output/aaai_screenshots_all/phase17_screenshots.json --condition deterministic --output-dir output/aaai_vlm_deterministic`（最终 4096 token 全量复跑）
- 关键输出路径：
  - `output/aaai_vlm_deterministic/vlm_screenshot_scores.json`
  - `output/aaai_vlm_deterministic/vlm_screenshot_scores.csv`
  - `output/aaai_vlm_deterministic/vlm_screenshot_summary.csv`
- 测试结果：
  - `vlm_evaluation: PASS`
  - final report：`schema_version=vlm-screenshot-scores-v1`，`condition=deterministic`。
  - final VLM model：`gemini-3-flash-preview`，`base_url=http://yy.dbh.baidu-int.com/v1`，`api_key_configured=true`，`api_key_source=api_settings.yaml`，`timeout_s=600`，`max_tokens=4096`。
  - prompt metadata：`prompt_version=vlm-screenshot-judge-2026-05-30`，`prompt_hash` 长度 64；`rubric_version=2026-05-30`，`rubric_hash` 长度 64。
  - final condition summary：total=144，passed=144，failed=0，pass_rate=1.0，failure_types={}。
  - final model_usage：call_count=148，duration_s=1751.201，avg_duration_s=11.83243918918919，prompt_tokens=426239，completion_tokens=224370，total_tokens=650609，usage_available=true，usage_available_rate=1.0，estimated_cost=null，cost_estimation_available=false，pricing_source=""。
  - final score averages：layout_readability=4.701388888888889，algorithm_state_visibility=4.458333333333333，teaching_explanation=4.743055555555555，interaction_affordance=4.972222222222222，evidence_alignment=4.895833333333333，overall_teaching_quality=4.659722222222222。
  - low_score_count=4，high_confidence_issue_count=75。
  - low score screenshots：`dashboard_index` mobile，`binary_tree_inorder` mobile，`lca` mobile，`tree_max_independent_set` mobile。
  - CSV 验证：`vlm_screenshot_scores.csv` 为 145 行（含 header），`vlm_screenshot_summary.csv` 为 7 行（含 header）。
- Bugfix：
  - 失败命令：初次全量 E3 命令在 1024 token 下出现 130 个 `vlm_eval_error`；重试和 caption 修复后仍有 93 个空内容失败，且失败调用 `completion_tokens=1020`，接近 1024 上限。
  - 最小修复：VLM 默认 timeout 提高到 600；默认 max_tokens 提高到 4096；单张 VLM API 异常记录为 `vlm_eval_error` 不阻断 batch；保留失败调用 usage；CLI 增加进度输出；caption 按 30 个英文词或 50 个中文字符校验；空/非法响应默认重试 1 次。
  - 复跑证据：`/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.vlm_evaluation` 通过；最终 E3 全量复跑 144/144 成功，failure_types={}。
  - 未修改 expected，未放宽 gate，未跳过 case；VLM 仅作为离线截图教学/视觉评审，不替代机器 gate。

### E4 live LLM `algolab_full`

状态：已完成。

先跑 smoke：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/run_llm_benchmark.py \
  --output-dir output/aaai_llm_algolab_full_smoke \
  --condition algolab_full \
  --case unique_paths \
  --max-rounds 2 \
  --timeout-s 180 \
  --browser-smoke \
  --concurrency 1
```

再跑全量：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/run_llm_benchmark.py \
  --output-dir output/aaai_llm_algolab_full \
  --condition algolab_full \
  --max-rounds 2 \
  --timeout-s 180 \
  --browser-smoke \
  --concurrency 2
```

验收：

- `llm_benchmark_report.json` 存在。
- `total=69`。
- 每个失败项有 `failure_type`。
- 真实 LLM case 失败不阻塞后续实验。

完成证据（2026-05-30）：

- Smoke 命令：
  - `bash scripts/run_browser_smoke_container.sh python scripts/run_llm_benchmark.py --output-dir output/aaai_llm_algolab_full_smoke --condition algolab_full --case unique_paths --max-rounds 2 --timeout-s 180 --browser-smoke --concurrency 1`
  - 结果：`output/aaai_llm_algolab_full_smoke/llm_benchmark_report.json`，total=1，passed=1，failed=0；model=`gemini-3.1-pro-preview`，model_usage.call_count=2，total_tokens=19483，usage_available=true。
- 全量命令：
  - 初始按计划使用 `--timeout-s 180` 全量运行时出现大量 case timeout，无法形成完整 69-case 证据。
  - 按真实 LLM 生成和 repair 耗时，将单 case 外层 timeout 提高到 600 秒后复跑：`bash scripts/run_browser_smoke_container.sh python scripts/run_llm_benchmark.py --output-dir output/aaai_llm_algolab_full --condition algolab_full --max-rounds 2 --timeout-s 600 --browser-smoke --concurrency 2`
- 关键输出路径：
  - `output/aaai_llm_algolab_full/llm_benchmark_report.json`
  - `output/aaai_llm_algolab_full/family_summary.json`
  - `output/aaai_llm_algolab_full/llm_benchmark_report.md`
- 最终 report：condition=`algolab_full`，case_set=`deterministic`，total=69，passed=27，failed=42，pass_rate=0.391304347826087，started_at=`2026-05-30T14:33:01`，ended_at=`2026-05-30T16:11:36`，avg_duration_s=169.4。
- 失败项完整性：失败项缺失 `failure_type` 数量为 0；所有 result 均包含 `model_calls`。
- failure_summary：`process_invariant=26`，`execution=2`，`demo_key_step_missing=4`，`generation=3`，`trace_schema=3`，`visual_warning=3`，`demo_algorithm_mismatch=1`。
- browser smoke：对 27 个通过 HTML 产物执行，browser_total=27，browser_ok=27，browser_failed=0。
- LLM 配置与 usage：model=`gemini-3.1-pro-preview`，base_url=`http://yy.dbh.baidu-int.com/v1`，api_key_source=`api_settings.yaml`，LLM API timeout_s=240，max_tokens=16384，json_retries=1；model_usage.call_count=195，usage_available=true，usage_available_rate=1.0，prompt_tokens=853759，completion_tokens=1397106，total_tokens=2250865，duration_s=11670.853，avg_duration_s=59.8505282051282，estimated_cost=null，cost_estimation_available=false，pricing_source=""。
- 约束：未修改 expected，未放宽 gate，未跳 case；真实 LLM case 失败作为实验结果保留，不阻塞后续 E5。

### E5 unseen family evaluation

状态：已完成。

命令：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/run_llm_benchmark.py \
  --output-dir output/aaai_llm_unseen \
  --condition algolab_full \
  --case-set unseen \
  --max-rounds 2 \
  --timeout-s 180 \
  --browser-smoke \
  --concurrency 2
```

验收：

- `case_set=unseen`。
- 每个失败项有 `failure_type`。
- 不复用 deterministic tracker/code。

完成证据（2026-05-30）：

- 配置检查：`benchmark/unseen_family_cases.json` 为 `schema_version=unseen-family-cases-v1`，case_count=15；检查 `code`、`tracker_code`、`verifier_code` 字段，forbidden_code_fields=[]。
- 实际命令：
  - 按 E4 实测耗时和真实 LLM repair 成本，将计划中的 `--timeout-s 180` 提高到 `--timeout-s 600`，避免 unseen case 被过低外层 timeout 人为截断。
  - `bash scripts/run_browser_smoke_container.sh python scripts/run_llm_benchmark.py --output-dir output/aaai_llm_unseen --condition algolab_full --case-set unseen --max-rounds 2 --timeout-s 600 --browser-smoke --concurrency 2`
- 关键输出路径：
  - `output/aaai_llm_unseen/llm_benchmark_report.json`
  - `output/aaai_llm_unseen/family_summary.json`
  - `output/aaai_llm_unseen/llm_benchmark_report.md`
- 最终 report：condition=`algolab_full`，case_set=`unseen`，total=15，passed=6，failed=9，pass_rate=0.4，started_at=`2026-05-30T16:13:42`，ended_at=`2026-05-30T16:36:03`，avg_duration_s=172.152。
- 失败项完整性：失败项缺失 `failure_type` 数量为 0；所有 result 均包含 `model_calls`。
- failure_summary：`process_invariant=6`，`coverage_error=1`，`demo_missing_deps=1`，`execution=1`。
- browser smoke：对 6 个通过 HTML 产物执行，browser_total=6，browser_ok=6，browser_failed=0。
- LLM 配置与 usage：model=`gemini-3.1-pro-preview`，base_url=`http://yy.dbh.baidu-int.com/v1`，api_key_source=`api_settings.yaml`，LLM API timeout_s=240，max_tokens=16384，json_retries=1；model_usage.call_count=42，usage_available=true，usage_available_rate=1.0，prompt_tokens=183661，completion_tokens=319570，total_tokens=503231，duration_s=2578.694，avg_duration_s=61.39747619047619，estimated_cost=null，cost_estimation_available=false，pricing_source=""。
- 约束：未复用 deterministic tracker/code/verifier，未修改 expected，未放宽 gate，未跳 case；真实 LLM unseen 失败作为泛化实验结果保留。

### E6 baseline / ablation infrastructure

状态：已完成。

先审计：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py --help
rg -n "benchmark_condition|direct_html_baseline|no_process_validator|no_scenegraph_compiler" scripts tests docs -S
```

如果 `--condition` 只是 metadata，必须补真实 baseline runner。

允许新增：

- `scripts/run_direct_html_baseline.py`
- `scripts/run_no_process_validator_ablation.py`
- `scripts/run_no_scenegraph_compiler_ablation.py`
- `tests/regression/baseline_experiments.py`

测试必须覆盖：

- direct HTML 输出真实 HTML 并跑 browser smoke。
- no process validator report 写 `process_validator_enabled=false`。
- no SceneGraph compiler report 写 `scenegraph_compiler_enabled=false`。
- 失败类型进入 report。
- 不能修改主 pipeline 默认行为。

完成证据（2026-05-30）：

- 审计命令：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py --help`
  - `rg -n "benchmark_condition|direct_html_baseline|no_process_validator|no_scenegraph_compiler|no_repair|process_validator_enabled|scenegraph_compiler_enabled" scripts tests docs algolab -S`
- 审计结论：`scripts/run_llm_benchmark.py --condition` 原说明为“写入 report 的实验条件标签；不改变主 pipeline 行为”，因此不能用标签冒充 baseline / ablation。
- 新增/修改基础设施：
  - `scripts/baseline_experiment_utils.py`：共享 case 选择、并发、单 case timeout、逐条写 report、browser smoke 和 browser 失败回填。
  - `scripts/run_direct_html_baseline.py`：LLM 直接输出单文件 HTML，condition=`direct_html_baseline`，不进入 AlgoLab BuildArtifact / SceneGraph 主发布路径。
  - `scripts/run_no_process_validator_ablation.py`：只在该脚本的 materialize 调用中临时禁用 process validator，并在 finally 中恢复主 pipeline 函数；report 记录 `process_validator_enabled=false`。
  - `scripts/run_no_scenegraph_compiler_ablation.py`：保留 solve / trace / process / demo 校验，不调用 SceneGraph compiler，输出 trace-only HTML 外部消融页面；report 记录 `scenegraph_compiler_enabled=false` 和 `trace_only_renderer_enabled=true`。
  - `scripts/run_llm_benchmark.py`：`write_report()` 支持把 baseline / ablation 配置标志写入 report.config。
  - `tests/regression/baseline_experiments.py`：覆盖 direct HTML 真实 HTML + browser smoke、no process validator config 标志、no SceneGraph compiler config 标志、failure type summary、主 pipeline 函数恢复。
- CLI 验证：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_direct_html_baseline.py --help`
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_no_process_validator_ablation.py --help`
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_no_scenegraph_compiler_ablation.py --help`
- 测试结果：
  - 宿主机直接运行 browser smoke 测试时，Playwright driver 因系统 `glibc/libstdc++` 版本不满足而无法启动；按项目约束改用浏览器容器执行。
  - `bash scripts/run_browser_smoke_container.sh python -m tests.regression.baseline_experiments` 通过，输出 `baseline_experiments: PASS`。
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression` 通过，输出 `benchmark_regression: PASS`。
- 约束：未修改 expected，未放宽 gate，未跳 case；baseline / ablation 均为独立 runner 或独立外部 report 路径，不修改主 pipeline 默认行为。

### E7 run baselines and ablations

状态：已完成。

必须跑：

- `direct_html_baseline`
- `no_process_validator`
- `no_scenegraph_compiler`
- `no_repair`

每个 condition：

- total 应为 69。
- 失败项必须有 failure type。
- 输出目录使用 `output/aaai_llm_*`。
- browser smoke 开启。

`no_repair` 可以直接运行：

```bash
bash scripts/run_browser_smoke_container.sh python scripts/run_llm_benchmark.py \
  --output-dir output/aaai_llm_no_repair \
  --condition algolab_full \
  --max-rounds 0 \
  --timeout-s 180 \
  --browser-smoke \
  --concurrency 2
```

汇总时必须标记为 `condition=no_repair`，不能混进 `algolab_full`。

完成证据：

- `direct_html_baseline`：
  - 命令：`bash scripts/run_browser_smoke_container.sh python scripts/run_direct_html_baseline.py --output-dir output/aaai_llm_direct_html --timeout-s 600 --browser-smoke --concurrency 2`
  - 报告：`output/aaai_llm_direct_html/llm_benchmark_report.json`
  - 结果：total=69, passed=63, failed=6, pass_rate=0.9130。
  - config：`benchmark_condition=direct_html_baseline`, `baseline=direct_html_baseline`, `timeout_s=600`, `browser_smoke=true`, `concurrency=2`。
  - failure type 缺失数：0；failure_summary=`{"browser": 6}`。
  - browser smoke：total=69, ok=63, failed=6。
  - model_usage：call_count=69, total_tokens=570126, usage_available=true。
- `no_process_validator`：
  - 命令：`bash scripts/run_browser_smoke_container.sh python scripts/run_no_process_validator_ablation.py --output-dir output/aaai_llm_no_process_validator --max-rounds 2 --timeout-s 600 --browser-smoke --concurrency 2`
  - 报告：`output/aaai_llm_no_process_validator/llm_benchmark_report.json`
  - 结果：total=69, passed=40, failed=29, pass_rate=0.5797。
  - config：`benchmark_condition=no_process_validator`, `ablation=no_process_validator`, `timeout_s=600`, `browser_smoke=true`, `concurrency=2`。
  - failure type 缺失数：0；timeout 失败数=0；rate-limit-like 失败数=0。
  - failure_summary=`{"process_invariant": 11, "trace_schema": 5, "demo_missing_deps": 2, "visual_warning": 5, "demo_key_step_missing": 3, "generation": 2, "demo_algorithm_mismatch": 1}`。
  - browser smoke：total=40, ok=40, failed=0。
  - model_usage：call_count=157, total_tokens=1882801, usage_available=true。
- `no_scenegraph_compiler`：
  - 命令：`bash scripts/run_browser_smoke_container.sh python scripts/run_no_scenegraph_compiler_ablation.py --output-dir output/aaai_llm_no_scenegraph_compiler --max-rounds 2 --timeout-s 600 --browser-smoke --concurrency 2`
  - 报告：`output/aaai_llm_no_scenegraph_compiler/llm_benchmark_report.json`
  - 结果：total=69, passed=23, failed=46, pass_rate=0.3333。
  - config：`benchmark_condition=no_scenegraph_compiler`, `ablation=no_scenegraph_compiler`, `timeout_s=600`, `browser_smoke=true`, `concurrency=2`。
  - failure type 缺失数：0；timeout 失败数=0；rate-limit-like 失败数=0。
  - failure_summary=`{"coverage_error": 2, "process_invariant": 28, "visual_scene": 7, "demo_key_step_missing": 3, "generation": 1, "demo_algorithm_mismatch": 4, "demo_missing_reason": 1}`。
  - browser smoke：total=23, ok=23, failed=0。
  - model_usage：call_count=193, total_tokens=2366805, usage_available=true。
- `no_repair`：
  - 命令：`bash scripts/run_browser_smoke_container.sh python scripts/run_llm_benchmark.py --output-dir output/aaai_llm_no_repair --condition no_repair --max-rounds 0 --timeout-s 600 --browser-smoke --concurrency 2`
  - 报告：`output/aaai_llm_no_repair/llm_benchmark_report.json`
  - 结果：total=69, passed=6, failed=63, pass_rate=0.0870。
  - config：`benchmark_condition=no_repair`, `max_rounds=0`, `timeout_s=600`, `browser_smoke=true`, `concurrency=2`。
  - failure type 缺失数：0；timeout 失败数=0；rate-limit-like 失败数=0。
  - failure_summary=`{"coverage_error": 3, "execution": 15, "process_invariant": 39, "generation": 4, "demo_key_step_missing": 1, "demo_algorithm_mismatch": 1}`。
  - browser smoke：total=6, ok=6, failed=0。
  - model_usage：call_count=70, total_tokens=742477, usage_available=true。
- 超时设置说明：E4/E5/E7 全量真实 LLM 运行中存在 80-90 秒级慢 case；E4 180 秒全量曾出现大量 timeout，因此 E7 四个 condition 统一使用 `--timeout-s 600`。本阶段验收统计中 E7 四个 condition 的 timeout 失败数均为 0。
- 约束：未修改 expected，未放宽 gate，未跳 case；`no_repair` 使用 `--condition no_repair`，未混入 `algolab_full`。

### E8 VLM condition comparison

状态：已完成。

目标：对 LLM 和 baseline 生成的 HTML 截图做 VLM 对照评分。

如果现有 report 没有截图，允许新增：

- `scripts/capture_report_html_screenshots.py`
- 或扩展 `scripts/run_vlm_screenshot_eval.py --llm-report`

输出：

- `output/aaai_vlm_conditions/vlm_condition_scores.json`
- `output/aaai_vlm_conditions/vlm_condition_scores.csv`
- `output/aaai_vlm_conditions/vlm_condition_summary.csv`

必须包含 condition：

- `deterministic`
- `algolab_full`
- `unseen_algolab_full`
- `direct_html_baseline`
- `no_process_validator`
- `no_scenegraph_compiler`
- `no_repair`

完成证据：

- 新增脚本：
  - `scripts/capture_report_html_screenshots.py`：从 LLM benchmark report 的成功 HTML 产物捕获真实浏览器截图，输出总 manifest 和按 condition 拆分的 manifest。
  - `scripts/merge_vlm_condition_reports.py`：合并多个单 condition VLM report，输出本阶段要求的 condition comparison JSON/CSV。
- 新增测试：
  - `tests/regression/vlm_conditions.py`：覆盖 report 成功 HTML 过滤、condition override、condition manifest 计数、VLM condition report 合并和三类输出文件。
- 测试结果：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.vlm_conditions` 通过，输出 `vlm_conditions: PASS`。
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.vlm_evaluation` 通过，输出 `vlm_evaluation: PASS`。
- 截图捕获：
  - 命令：`bash scripts/run_browser_smoke_container.sh python scripts/capture_report_html_screenshots.py --output-dir output/aaai_vlm_conditions/screenshots --viewport desktop --report algolab_full=output/aaai_llm_algolab_full/llm_benchmark_report.json --report unseen_algolab_full=output/aaai_llm_unseen/llm_benchmark_report.json --report direct_html_baseline=output/aaai_llm_direct_html/llm_benchmark_report.json --report no_process_validator=output/aaai_llm_no_process_validator/llm_benchmark_report.json --report no_scenegraph_compiler=output/aaai_llm_no_scenegraph_compiler/llm_benchmark_report.json --report no_repair=output/aaai_llm_no_repair/llm_benchmark_report.json`
  - manifest：`output/aaai_vlm_conditions/screenshots/report_html_screenshots.json`
  - 截图统计：total=165, failures=0, zero_bytes=0。
  - condition_counts=`{"algolab_full": 27, "unseen_algolab_full": 6, "direct_html_baseline": 63, "no_process_validator": 40, "no_scenegraph_compiler": 23, "no_repair": 6}`。
  - 说明：LLM/baseline 条件使用每个成功 HTML 的 desktop full-page 截图；`deterministic` 复用 E3 已完成的 `output/aaai_vlm_deterministic/vlm_screenshot_scores.json`。
- VLM 接口 smoke：
  - 命令：`ALGOLAB_VLM_TIMEOUT_S=600 /ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_vlm_screenshot_eval.py --manifest output/aaai_vlm_conditions/vlm_smoke_manifest.json --condition no_repair --output-dir output/aaai_vlm_conditions/vlm_smoke --retries 1`
  - 结果：total=1, passed=1, failed=0；usage_available=true；duration_s=23.236。
  - 结论：VLM 接口可稳定返回合法 JSON；本阶段保持 `ALGOLAB_VLM_TIMEOUT_S=600`，未再提高超时。
- VLM condition runs：
  - `algolab_full`：`output/aaai_vlm_conditions/runs/algolab_full/vlm_screenshot_scores.json`，total=27, passed=27, failed=0, call_count=29, total_tokens=135213, avg_overall_teaching_quality=4.7037。
  - `unseen_algolab_full`：`output/aaai_vlm_conditions/runs/unseen_algolab_full/vlm_screenshot_scores.json`，total=6, passed=6, failed=0, call_count=8, total_tokens=38598, avg_overall_teaching_quality=4.3333。
  - `direct_html_baseline`：`output/aaai_vlm_conditions/runs/direct_html_baseline/vlm_screenshot_scores.json`，total=63, passed=63, failed=0, call_count=63, total_tokens=236646, avg_overall_teaching_quality=4.8889。
  - `no_process_validator`：`output/aaai_vlm_conditions/runs/no_process_validator/vlm_screenshot_scores.json`，total=40, passed=40, failed=0, call_count=44, total_tokens=211400, avg_overall_teaching_quality=4.6500。
  - `no_scenegraph_compiler`：`output/aaai_vlm_conditions/runs/no_scenegraph_compiler/vlm_screenshot_scores.json`，total=23, passed=23, failed=0, call_count=23, total_tokens=105900, avg_overall_teaching_quality=1.4348。
  - `no_repair`：`output/aaai_vlm_conditions/runs/no_repair/vlm_screenshot_scores.json`，total=6, passed=6, failed=0, call_count=6, total_tokens=31035, avg_overall_teaching_quality=4.3333。
- 合并命令：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/merge_vlm_condition_reports.py --output-dir output/aaai_vlm_conditions --report output/aaai_vlm_deterministic/vlm_screenshot_scores.json --report output/aaai_vlm_conditions/runs/algolab_full/vlm_screenshot_scores.json --report output/aaai_vlm_conditions/runs/unseen_algolab_full/vlm_screenshot_scores.json --report output/aaai_vlm_conditions/runs/direct_html_baseline/vlm_screenshot_scores.json --report output/aaai_vlm_conditions/runs/no_process_validator/vlm_screenshot_scores.json --report output/aaai_vlm_conditions/runs/no_scenegraph_compiler/vlm_screenshot_scores.json --report output/aaai_vlm_conditions/runs/no_repair/vlm_screenshot_scores.json`
- 最终产物：
  - `output/aaai_vlm_conditions/vlm_condition_scores.json`
  - `output/aaai_vlm_conditions/vlm_condition_scores.csv`
  - `output/aaai_vlm_conditions/vlm_condition_summary.csv`
- 最终验收：
  - `schema_version=vlm-condition-scores-v1`。
  - conditions=`["algolab_full", "deterministic", "direct_html_baseline", "no_process_validator", "no_repair", "no_scenegraph_compiler", "unseen_algolab_full"]`；要求的 7 个 condition 无缺失。
  - merged results total=309, VLM failures=0。
  - deterministic：total=144, passed=144, failed=0, call_count=148, total_tokens=650609, avg_overall_teaching_quality=4.6597。
  - `vlm_condition_scores.csv` 为 310 行（含 header）；`vlm_condition_summary.csv` 为 25 行（含 header）。
  - usage：全部 condition 的 `usage_available=true`。

### E9 merge evaluation report

状态：已完成。

如果现有 `build_evaluation_report.py` 只支持一个 LLM report，必须补：

- `scripts/merge_llm_reports.py`
- 或 `build_evaluation_report.py` 支持多个 `--llm-report`

如果 evaluation report 不支持 VLM report，必须补：

- `--vlm-report`
- VLM summary CSV 输出

最终命令形态：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_report.py \
  --output-dir output/aaai_evaluation \
  --llm-report output/aaai_evaluation/merged_llm_benchmark_report.json \
  --vlm-report output/aaai_vlm_conditions/vlm_condition_scores.json \
  --family-gate output/aaai_release_gate/family_release_gate.json \
  --dashboard output/aaai_dashboard_all/dashboard.json
```

必须产物：

- `evaluation_report.json`
- `evaluation_report.md`
- `evaluation_condition_summary.csv`
- `evaluation_failure_types.csv`
- `evaluation_family_summary.csv`
- `evaluation_case_styles.csv`
- `evaluation_degradations.csv`
- `evaluation_vlm_scores.csv`
- `evaluation_vlm_condition_summary.csv`

完成证据：

- 新增脚本：
  - `scripts/merge_llm_reports.py`：按 `CONDITION=PATH` 合并多个 LLM benchmark report，并覆盖/保留 condition 来源，输出 `merged_llm_benchmark_report.json`。
- 修改脚本：
  - `scripts/build_evaluation_report.py`：新增 `--vlm-report`；evaluation JSON 记录 `vlm_summary`；新增 `evaluation_vlm_scores.csv` 和 `evaluation_vlm_condition_summary.csv`；Markdown 新增 `VLM Condition Summary`。
- 测试结果：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.vlm_conditions` 通过，输出 `vlm_conditions: PASS`。
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.vlm_evaluation` 通过，输出 `vlm_evaluation: PASS`。
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression` 通过，输出 `benchmark_regression: PASS`。
- LLM report 合并命令：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/merge_llm_reports.py --output-dir output/aaai_evaluation --report algolab_full=output/aaai_llm_algolab_full/llm_benchmark_report.json --report unseen_algolab_full=output/aaai_llm_unseen/llm_benchmark_report.json --report direct_html_baseline=output/aaai_llm_direct_html/llm_benchmark_report.json --report no_process_validator=output/aaai_llm_no_process_validator/llm_benchmark_report.json --report no_scenegraph_compiler=output/aaai_llm_no_scenegraph_compiler/llm_benchmark_report.json --report no_repair=output/aaai_llm_no_repair/llm_benchmark_report.json`
  - 输出：`output/aaai_evaluation/merged_llm_benchmark_report.json`
  - 结果：total=360, passed=165, failed=195。
  - condition summary：`algolab_full` 27/69 pass；`unseen_algolab_full` 6/15 pass；`direct_html_baseline` 63/69 pass；`no_process_validator` 40/69 pass；`no_scenegraph_compiler` 23/69 pass；`no_repair` 6/69 pass。
- evaluation report 命令：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_report.py --output-dir output/aaai_evaluation --llm-report output/aaai_evaluation/merged_llm_benchmark_report.json --vlm-report output/aaai_vlm_conditions/vlm_condition_scores.json --family-gate output/aaai_release_gate/family_release_gate.json --dashboard output/aaai_dashboard_all/dashboard.json`
- 最终产物：
  - `output/aaai_evaluation/evaluation_report.json`
  - `output/aaai_evaluation/evaluation_report.md`
  - `output/aaai_evaluation/evaluation_condition_summary.csv`
  - `output/aaai_evaluation/evaluation_failure_types.csv`
  - `output/aaai_evaluation/evaluation_family_summary.csv`
  - `output/aaai_evaluation/evaluation_case_styles.csv`
  - `output/aaai_evaluation/evaluation_degradations.csv`
  - `output/aaai_evaluation/evaluation_vlm_scores.csv`
  - `output/aaai_evaluation/evaluation_vlm_condition_summary.csv`
- 最终验收：
  - `evaluation_report.json`：`schema_version=evaluation-report-v1`，`inputs.vlm_report=output/aaai_vlm_conditions/vlm_condition_scores.json`。
  - `evaluation_condition_summary.csv` 为 7 行（含 header），覆盖 6 个 LLM condition。
  - `evaluation_vlm_scores.csv` 为 310 行（含 header），对应 E8 merged VLM results=309。
  - `evaluation_vlm_condition_summary.csv` 为 8 行（含 header），覆盖 7 个 VLM condition。
  - `evaluation_report.md` 包含 `Baseline And Ablation Summary`、`VLM Condition Summary`、`Seen / Unseen Style Summary`。
  - 约束：未修改 expected，未放宽 gate，未跳 case。

### E10 paper artifacts

状态：已完成。

目录：

- `output/aaai_paper_artifacts/README.md`
- `output/aaai_paper_artifacts/tables/`
- `output/aaai_paper_artifacts/figures/`
- `output/aaai_paper_artifacts/failure_cases.md`

表格：

- Table 1：deterministic gate summary。
- Table 2：browser screenshot summary。
- Table 3：LLM condition summary。
- Table 4：unseen family summary。
- Table 5：failure type distribution。
- Table 6：ablation comparison。
- Table 7：VLM teaching quality by condition。

图：

- dashboard 总览。
- DP 公式展开。
- 图算法 relax / path。
- 字符串匹配。
- 错误选项反馈。
- direct HTML baseline 失败图。
- VLM 低分案例图。

失败案例：

- case id。
- family id。
- condition。
- sample index。
- expected / actual。
- failure type。
- repair 是否发生。
- artifact path。
- screenshot path。
- VLM issues。
- 一句话原因。

完成证据：

- 新增脚本：
  - `scripts/build_paper_artifacts.py`：从 E1-E9 产物生成 paper-facing tables、figures、failure case notes 和 README。
- 修改脚本：
  - `scripts/capture_report_html_screenshots.py`：新增 `--include-failed` / `--only-failed`，用于捕获 direct HTML baseline 失败产物截图；默认行为不变。
- 新增测试：
  - `tests/regression/paper_artifacts.py`：覆盖 deterministic gate 表、unseen family 表、ablation delta、failure case notes、最低 VLM 分截图选择和 README 输出。
- 测试结果：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.paper_artifacts` 通过，输出 `paper_artifacts: PASS`。
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.vlm_conditions` 通过，输出 `vlm_conditions: PASS`。
- direct HTML baseline 失败截图捕获：
  - 命令：`bash scripts/run_browser_smoke_container.sh python scripts/capture_report_html_screenshots.py --output-dir output/aaai_paper_artifacts/direct_html_failure_screenshots --viewport desktop --only-failed --report direct_html_baseline=output/aaai_llm_direct_html/llm_benchmark_report.json`
  - manifest：`output/aaai_paper_artifacts/direct_html_failure_screenshots/report_html_screenshots.json`
  - 结果：condition_counts=`{"direct_html_baseline": 6}`，screenshots=6，zero_bytes=0。
- paper artifacts 生成命令：
  - `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_paper_artifacts.py --output-dir output/aaai_paper_artifacts --evaluation-dir output/aaai_evaluation --deterministic-screenshot-manifest output/aaai_screenshots_all/phase17_screenshots.json --condition-screenshot-manifest output/aaai_vlm_conditions/screenshots/report_html_screenshots.json --direct-failure-manifest output/aaai_paper_artifacts/direct_html_failure_screenshots/report_html_screenshots.json --dashboard output/aaai_dashboard_all/dashboard.json --family-gate output/aaai_release_gate/family_release_gate.json --merged-llm-report output/aaai_evaluation/merged_llm_benchmark_report.json --vlm-report output/aaai_vlm_conditions/vlm_condition_scores.json`
- 最终目录：
  - `output/aaai_paper_artifacts/README.md`
  - `output/aaai_paper_artifacts/tables/`
  - `output/aaai_paper_artifacts/figures/`
  - `output/aaai_paper_artifacts/failure_cases.md`
- 表格产物：
  - `tables/table1_deterministic_gate_summary.csv`，5 行（含 header）。
  - `tables/table2_browser_screenshot_summary.csv`，9 行（含 header）。
  - `tables/table3_llm_condition_summary.csv`，7 行（含 header）。
  - `tables/table4_unseen_family_summary.csv`，16 行（含 header）。
  - `tables/table5_failure_type_distribution.csv`，13 行（含 header）。
  - `tables/table6_ablation_comparison.csv`，6 行（含 header）。
  - `tables/table7_vlm_teaching_quality_by_condition.csv`，8 行（含 header）。
- 图产物：
  - `figures/figure1_dashboard_overview.png`
  - `figures/figure2_dp_formula_expanded.png`
  - `figures/figure3_graph_relax_path.png`
  - `figures/figure4_string_matching.png`
  - `figures/figure5_wrong_option_feedback.png`
  - `figures/figure6_direct_html_baseline_failure.png`
  - `figures/figure7_vlm_low_score_case.png`
  - 7 张图均存在且非零字节。
- 失败案例：
  - `output/aaai_paper_artifacts/failure_cases.md` 为 199 行，包含 195 条 failed LLM condition item。
  - 字段覆盖：case、family、condition、sample、expected、actual/error、failure type、repair、artifact、screenshot、VLM issues、reason。
  - 已覆盖 `direct_html_baseline`、`no_process_validator`、`no_scenegraph_compiler`、`no_repair`、`unseen_algolab_full` 等条件。
- 约束：未修改 expected，未放宽 gate，未跳 case；新增内容均为实验产物生成和截图采集基础设施。

## 8. 系统完善规则

做实验中可以完善系统，但必须是可复现 bugfix 或实验基础设施。

允许：

- 新增实验脚本。
- 新增 report merge。
- 新增 VLM scoring。
- 新增截图采集。
- 修复真实浏览器截图暴露的页面 bug。
- 修复真实 LLM report 暴露的 pipeline bug。

要求：

- 每个新增脚本必须有 regression 测试。
- 每个 bugfix 必须有失败命令和复跑证据。
- 主系统修复必须最小化。

禁止：

- 改 expected output。
- 放宽 validator。
- 放宽 browser gate。
- 修改 report 让失败看起来通过。
- 删除失败样例。

## 9. 最终测试

全部实验和必要修复完成后必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.benchmark_regression
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.offline_regression
bash scripts/run_browser_smoke_container.sh python scripts/run_quality_checks.py
```

如果新增 VLM 或 baseline 测试，也必须运行：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.vlm_evaluation
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m tests.regression.baseline_experiments
```

## 10. 执行 AI 汇报格式

执行 AI 完成后必须按以下格式汇报：

1. 本轮完成了什么。
2. 修改了哪些文件。
3. 新增或修改了哪些测试。
4. 运行了哪些测试命令。
5. 测试结果如何。
6. 是否还有遗留问题。
7. 下一步建议。

必须列出：

- 所有实验命令。
- 所有 output 路径。
- 每个 condition 的 total / passed / failed / pass_rate。
- 每个 condition 的 failure type 分布。
- LLM 和 VLM 实际使用模型。
- LLM 和 VLM 调用次数、耗时、token usage；如果 usage 不可用，必须说明 `usage_available=false`。
- VLM 平均分和低分案例数量。
- 是否做了 bugfix。
- bugfix 的测试和复跑证据。

## 11. 给执行 AI 的启动提示词

```text
你是执行 AI，在 /ssd1/liaokunpeng/paper/ailab-agent。阅读 docs/08_AAAI_EXPERIMENT_PLAN.md，只做最靠前的“状态：待执行。”阶段，完成后把该阶段改成“状态：已完成。”并写完成证据。不要做 Git，不提交不推送。Python 固定用 /ssd1/liaokunpeng/agent-py310-cu/bin/python3，浏览器命令走 bash scripts/run_browser_smoke_container.sh。可以修可复现 bug，但必须最小修复、加测试、复跑失败命令。不要改 expected，不要放宽 gate，不要跳 case。按 1-7 格式汇报。
```

## 12. docs/09 修复后口径说明

后续 `docs/09_LLM_SUCCESS_REPAIR_PLAN.md` 的 R8 清理将 evaluation report 的混合指标拆开：`direct_html_baseline` 仍保留 browser smoke 与 VLM 截图质量比较，但不进入 strict machine correctness gate；`algolab_full_strict_release_gate_pass_rate` 单独报告完整系统 release gate，通过的 VLM 平均分字段明确命名为 successful screenshots 上的教学质量。
