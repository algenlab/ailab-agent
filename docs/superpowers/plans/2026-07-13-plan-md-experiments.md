# Plan.md Experiments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 `plan/plan.md` 中所有可自动执行的实验，生成可复核产物，并为必须由真人完成的评测准备盲审材料和统计工具。

**Architecture:** 先修复会影响后续结论的 validator 盲区并重跑 clean/fault controls；再用冻结的分层样本和统一九项浏览器评测执行等预算修复 baseline、非退化消融、第二模型、held-out 与可扩展性实验。所有新结果写入 `output/experiments/algotutorgen_plan_completion_20260713/`，不覆盖既有论文证据；真人实验仅生成协议、盲化包和可复现统计程序。

**Tech Stack:** Python 3.10、Pydantic、pytest、Playwright、Docker、现有 AlgoTutorGen pipeline 与交互语义评测器。

---

### Task 1: Validator Referential Integrity And Causal Ordering

**Files:**
- Modify: `algolab/verification/scene_validator.py`
- Modify: `algolab/verification/process_validator.py`
- Test: `tests/regression/experiment_completion.py`

- [ ] 写 SceneGraph dangling mark/source/target/parent 的失败测试，并用聚焦 pytest 确认 RED。
- [ ] 将所有 SceneGraph 对象引用完整性违规升级为阻断错误，保留错误中的 frame、对象和引用 ID。
- [ ] 写 trace 反序、create-after-use、before/after 状态不连续和 enter/exit 不平衡的失败测试，并确认 RED。
- [ ] 实现保守的因果顺序检查：初始化前置、状态快照连续、显式 before/after 对齐、依赖可解析、阶段栈平衡。
- [ ] 运行聚焦测试和现有 200 clean artifact replay，确认 validator 不引入 clean false rejection。

### Task 2: Full Fault-Injection Rerun

**Files:**
- Modify: `scripts/run_gate_fault_injection.py`
- Create: `output/experiments/algotutorgen_plan_completion_20260713/validator_fault_rerun/*`
- Modify: `docs/EXPERIMENT_RESULTS.md`

- [ ] 增加覆盖 parent/source/target、dependency order 和 event deletion 的受控 fault 类型及回归测试。
- [ ] 对冻结的 full-200 artifact 运行 200 clean controls 和全量 faults。
- [ ] 汇总 rejection、false accept、clean false reject，并与旧 2,400 faults 配对比较。
- [ ] 将新 validator 能力边界与数字写入论文报告，旧结果保留为修复前审计。

### Task 3: Machine Evaluator Human Calibration Package

**Files:**
- Create: `scripts/prepare_evaluator_calibration.py`
- Create: `scripts/analyze_evaluator_calibration.py`
- Test: `tests/regression/experiment_evaluation.py`
- Create: `output/experiments/algotutorgen_plan_completion_20260713/evaluator_calibration/*`

- [ ] 用确定性分层算法选取 30 tasks，覆盖 23 families、choice/input/judge、四方法 pass/fail。
- [ ] 复制/链接 120 个页面到随机 blind IDs，生成不含方法名称的 manifest 和九项标注 CSV。
- [ ] 实现双标合并、precision/recall/F1、FPR/FNR、Cohen kappa 和分方法统计，缺失真人标签时明确返回 pending。
- [ ] 写测试验证抽样唯一性、盲化映射隔离、混淆矩阵和 agreement 计算。
- [ ] 生成标注协议、codebook、空白 annotator-A/B 表和仅研究负责人可见的 key。

### Task 4: Independent Trace Correctness Audit Package

**Files:**
- Create: `scripts/prepare_trace_correctness_audit.py`
- Create: `scripts/analyze_trace_correctness_audit.py`
- Test: `tests/regression/experiment_evaluation.py`
- Create: `output/experiments/algotutorgen_plan_completion_20260713/trace_correctness_audit/*`

- [ ] 分层抽取 40 tasks，每题冻结初始、关键中间和终止 frame 及 trace evidence。
- [ ] 生成双人盲审表，覆盖结果、状态转移、依赖、讲解一致性和 critical error。
- [ ] 实现 critical semantic error rate、分 family 统计和标注者一致性分析。
- [ ] 生成待真人填写的审核包，绝不预填或推断人工标签。

### Task 5: Direct-BrowserRepair-5

**Files:**
- Create: `scripts/run_direct_browser_repair_baseline.py`
- Create: `scripts/build_browser_repair_feedback.py`
- Test: `tests/regression/experiment_completion.py`
- Create: `output/experiments/algotutorgen_plan_completion_20260713/direct_browser_repair_5/*`

- [ ] 冻结 full-200 sample-0 输入、模型、temperature、最多 5 calls 和约 80k token 上限。
- [ ] 首次复用 Direct HTML prompt；每轮只暴露 console/pageerror、可见 DOM 摘要、截图描述和通用 smoke 结果，不暴露隐藏 selector/九项失败指标。
- [ ] 每轮执行 self-contained 检查并阻断外部资源，保存 prompt hash、response、HTML、浏览器反馈、tokens、latency。
- [ ] 以最多 8 并发完成 200 cases，支持断点续跑、逐 case 超时和无重复合并。
- [ ] 对 call budgets 1/2/3/5 分别运行同一九项评测，生成 Machine OK、token、时间预算曲线和配对检验。

### Task 6: Non-Degenerate Ablations

**Files:**
- Create: `scripts/run_direct_to_scenegraph_ablation.py`
- Create: `scripts/run_verified_trace_to_html_ablation.py`
- Test: `tests/regression/experiment_completion.py`
- Create: `output/experiments/algotutorgen_plan_completion_20260713/nondegenerate_ablations/*`

- [ ] 冻结覆盖 23 families 的 50-task 分层集合。
- [ ] 实现 Direct-to-SceneGraph：LLM 从题目直接生成合法 SceneGraph，再用固定 Runtime 输出 HTML。
- [ ] 实现 VerifiedTrace-to-LLM-HTML：向 LLM 提供已验证 SemanticTrace，由其自由生成 self-contained HTML。
- [ ] 完成生成、统一九项浏览器审计、结果/中间状态/反馈语义审计和 paired bootstrap/McNemar。

### Task 7: Cross-Model Generation

**Files:**
- Create: `scripts/run_cross_model_generation_experiment.py`
- Create: `output/experiments/algotutorgen_plan_completion_20260713/cross_model_50/*`

- [ ] 自动发现已配置且可调用的第二代码模型，并记录 endpoint/model/version；若不可用，保留可复现 probe 证据。
- [ ] 在同一 50-task 分层集合上运行 AlgoTutorGen 与 Direct HTML。
- [ ] 用统一九项评测报告 Machine OK、Stage1-Direct 差值、repair、tokens、latency 和配对置信区间。

### Task 8: Held-Out Task Generalization

**Files:**
- Create: `benchmark/heldout_cases_v1.json`
- Create: `scripts/freeze_heldout_benchmark.py`
- Create: `output/experiments/algotutorgen_plan_completion_20260713/heldout_40/*`

- [ ] 从未用于系统开发的独立题源构建 40 个新 case template，去重题意和 case ID。
- [ ] 用独立 oracle 冻结 input/expected/hash/source 元数据，并通过 schema 与 oracle 自检。
- [ ] 仅运行 AlgoTutorGen 和 Direct HTML，执行统一九项评测并报告 paired 结果。

### Task 9: Long-Trace Scalability

**Files:**
- Create: `scripts/run_long_trace_scalability.py`
- Test: `tests/regression/experiment_evaluation.py`
- Create: `output/experiments/algotutorgen_plan_completion_20260713/long_trace_scalability/*`

- [ ] 选取 18 个有自然规模参数的任务，每题生成 small/medium/large 输入并冻结 expected。
- [ ] 记录 trace events、frames、HTML bytes、load、TTI、step latency、JS heap 和视觉拥挤代理指标。
- [ ] 执行浏览器测量、汇总规模趋势和失败阈值，保存逐样本原始记录。

### Task 10: Human Expert And Student Study Protocols

**Files:**
- Create: `docs/31_HUMAN_EXPERT_REVIEW_PROTOCOL.md`
- Create: `docs/32_STUDENT_USER_STUDY_PROTOCOL.md`
- Create: `scripts/analyze_human_study.py`
- Create: `output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols/*`

- [ ] 准备 3 位专家 × 30 配对任务的随机化协议、量表、盲化页面和统计计划。
- [ ] 准备 20–30 名学生 AlgoTutorGen vs Direct 的研究方案、随机化、任务、SUS/认知负荷表和功效/统计计划。
- [ ] 实现空表校验与统计脚本；没有真实参与者数据时仅标记 pending，不生成结果数字。

### Task 11: Final Integration And Verification

**Files:**
- Modify: `docs/EXPERIMENT_RESULTS.md`
- Modify: `docs/EXPERIMENT_RESULTS.md`
- Create: `docs/EXPERIMENT_RESULTS.md`

- [ ] 对所有生成结果做 ID 完整性、重复、hash、外部资源、预算和评测口径检查。
- [ ] 运行 Python 编译、Shell 语法、聚焦 pytest 和论文数值一致性检查。
- [ ] 将自动实验结果、pending 真人输入、限制和复现命令写入最终报告。
- [ ] 逐项重读 `plan/plan.md`，明确 complete、pending-human 或 blocked-external 状态，不把协议准备误报为真人实验完成。
