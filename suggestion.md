根据 2026-06-08 的系统说明和我刚检索的相关工作，我的结论是：**你现在最应该做的不是继续证明“还能覆盖更多算法”，而是把“100% 正确”变成 AAAI 审稿人能相信的、可复现的、分层验收实验。** 论文主线应从“算法可视化工具”提升为：**LLM 生成可执行算法与可验证语义轨迹，再由确定性编译器生成交互式算法可视化的可靠生成框架**。你的系统确实已经具备这个主线：LLM 不直接生成主链路 HTML，而是生成 `solve` 和 DSL `trace`，系统执行后得到 `SemanticTrace`，再编译成 `SceneGraph` 和 HTML；teaching overlay 也只允许补充讲解/交互，不能改 trace、状态、答案或依赖。 

**投稿时间上，如果你说的是 AAAI-27，窗口很紧。** AAAI-27 官网显示：OpenReview 注册 2026-06-17 开始，投稿 2026-06-24 开始，摘要截止 2026-07-21，全文截止 2026-07-28，补充材料和代码截止 2026-07-31。([AAAI][1]) AAAI-26 的投稿说明还明确要求 reproducibility checklist，并说明审稿人会评估实验可复现性；补充材料可以包含技术附录、多媒体、代码与数据 ZIP，但主文必须自洽，不能把关键证据都放补充材料里。([AAAI][2]) ([AAAI][3])

### 调研判断

这个方向不是完全没人做了，但你的系统仍有差异化空间。经典算法可视化平台如 JHAVÉ 和 VisuAlgo 主要是人工构建/固定算法库，强调学生控制动画、回答弹窗问题、自定义输入等交互，但不是从题目描述自动生成可验证可视化。JHAVÉ 自称提供算法可视化材料并支持学生控制动画和回答问题；VisuAlgo 当前页面也显示它是多算法可视化平台，拥有约 24 个 visualization pages，并支持用户输入与 quiz/training。([Jhave][4]) ([VisuAlgo][5])

近两年真正相关的是 LLM 教育可视化/视频生成。TheoremExplainAgent 用 agentic Manim 生成 5 分钟以上 theorem explanation videos，并提出 240 个定理的 benchmark 和自动评估指标；但其结果也承认多数视频仍有轻微布局问题。Code2Video 则把教育视频生成建模为 Planner–Coder–Critic 的 Manim code pipeline，并使用效率、美学、TeachQuiz 等指标评估。([ACL Anthology][6]) ([arXiv][7])

最接近你的是 **ALGOGEN: Tool-Generated Verifiable Traces for Reliable Algorithm Visualization**。它明确提出把算法执行和渲染解耦，让 LLM 生成 Python tracker 输出 schema-validated trace，再由确定性 renderer 生成 Manim/LaTeX/TikZ/Three.js；它在 200 个 LeetCode AV benchmark 上报告了比端到端方法更高的成功率和正确性。([arXiv][8]) ([arXiv][8]) 如果这是你们自己的预印本/旧版本，那么 AAAI 版本必须突出**新系统相对 ALGOGEN 的增量**：DSL-era `TraceSession`、`SemanticTrace -> SceneGraph -> interactive HTML`、release gate、browser/interactivity smoke、teaching overlay 只改教学不改事实、direct HTML no-expected 公平基线、以及更强的交互式系统评测。若不是你们的工作，就必须把它作为最强相关工作或强基线直接比较。

### 最重要的结论

你不能在 AAAI 论文里泛泛写“保证所有经典算法 100% 正确”。更安全、也更有说服力的写法是：

> On a frozen benchmark of N algorithm-visualization tasks, AlgoLab achieves 100% release-ready generation, 100% answer correctness under independent oracles, 100% schema-valid semantic traces, and 100% browser-smoke-valid interactive demos.

也就是说，**100% 必须限定在 benchmark、oracle、release gate 和实验协议内**。你的系统说明本身也写得很清楚：DSL 保证事件结构和 state snapshot，不等于数学正确性自动证明；当前 `process_validator` 已经是 DSL-era 轻量 sanity 层，不再是旧版每个算法族手写 invariant 重算；browser smoke 只证明页面可运行，不证明答案正确。  这点在论文里要主动承认，否则审稿人一抓“100% correctness guarantee”会很危险。

### 你下一步应该跑的主实验

第一组是**主 benchmark 实验**。建议冻结一个 300–500 题的 test set，按算法族分层：数组/双指针/滑窗、排序与二分、DP、图、树、栈队列、哈希、堆、Trie/字符串、并查集、区间结构、数学/位运算、几何。每题至少有一个小规模可视化输入、一个 expected output、若干隐藏 oracle test cases。小输入用于 HTML 可视化，大输入只用于 `solve`/oracle/stress correctness，不强制可视化。

主表不要只报一个 “success rate”，而要报分层 gate：

| 指标                     | 含义                                               | 论文里怎么写  |
| ---------------------- | ------------------------------------------------ | ------- |
| Parse/Spec Success     | LLM 输出合法 solution spec                           | 生成阶段可靠性 |
| Execution Success      | `solve/trace/verify` 沙箱执行成功                      | 工具生成可靠性 |
| Answer Correctness     | `solve == expected/oracle/verifier`              | 答案正确性   |
| Trace Validity         | `SemanticTrace` schema、step、target、deps 合法       | 过程结构正确性 |
| Process/Demo Readiness | 有 init/transition/answer，关键事件有 state/reason/deps | 可教学演示性  |
| Scene Validity         | `SceneGraph` frames/object/marks/edges 合法        | 渲染语义正确性 |
| Browser Smoke          | HTML 打开、canvas/counter/controls 无错误              | 页面可运行性  |
| Interaction Validity   | next/play/reset/quiz/solution tabs 不破坏 trace     | 交互正确性   |
| Cost                   | tokens、latency、repair rounds、HTML size、frames    | 工程可用性   |

第二组是**公平 baseline 实验**。你已有 direct HTML baseline，并且系统说明中已经区分了 `direct_html_baseline` 和 `direct_html_no_expected`：前者给模型 expected，有答案泄漏；后者隐藏 expected，才适合作为答案正确性口径。 所以论文主 baseline 应该至少包括：

| Baseline                      | 用途                                   | 是否公平             |
| ----------------------------- | ------------------------------------ | ---------------- |
| Direct HTML, expected hidden  | 主公平基线：LLM 直接写交互 HTML                 | 是                |
| Direct HTML, expected visible | 只说明“给答案后能否展示”，不能算 correctness        | 否，标注 leaked      |
| Direct event JSON             | LLM 直接写事件 JSON，不用 DSL 执行             | 是，验证 DSL 价值      |
| Direct SceneGraph             | LLM 直接写渲染语义，不走 trace compiler        | 是，验证 compiler 价值 |
| No repair                     | 验证 repair/retry 对成功率的贡献              | 是                |
| No teaching enrichment        | 验证讲解/交互增强是否提升教学质量                    | 是                |
| Full trace vs selected frames | 验证全量 trace teaching 的质量/成本 trade-off | 是                |

第三组是**ablation 实验**。你的消融应该围绕“为什么可靠”展开，而不是围绕 UI 花哨程度展开：

| Condition                                           | 预期回答的问题              |
| --------------------------------------------------- | -------------------- |
| Full AlgoLab                                        | 完整系统表现               |
| No DSL / LLM writes raw events                      | DSL 是否减少 trace 错误    |
| No sandbox execution                                | 真实执行是否必要             |
| No expected/verifier/multi-solution check           | answer gate 是否必要     |
| No SceneGraph compiler / direct HTML                | 中间表示是否必要             |
| No release gate                                     | 错误 artifact 是否会流入发布  |
| No teaching enrichment                              | 教学 overlay 是否提升解释/交互 |
| Teaching full trace vs 6 frames vs 3-frame fallback | 成本、覆盖率、质量如何权衡        |

第四组是**过程正确性审计**。这是你最需要补强的地方。因为你现在的 process validator 已不是旧版 family-specific invariant，所以论文中若要说“过程正确”，必须增加独立证据。建议三层：

1. **机器 replay consistency**：从 trace events 重放 state diff，检查每步 `before/after/target/deps` 与 state snapshot 一致。
2. **independent oracle trace audit**：对 50–100 个代表性经典算法，用手写 reference tracer 或 deterministic fixture 生成关键状态序列，比较关键步骤、最终答案、关键变量。
3. **专家盲审**：随机抽样每个算法族若干 case，每个 case 抽 5–10 帧，让两名算法背景标注者判断：步骤是否符合算法、highlight 是否指向正确对象、解释是否忠实、最终答案是否可见。报告 agreement 和 disagreement cases。

第五组是**视觉/交互质量评估**。Code2Video 和 TheoremExplainAgent 都说明现在该领域已经习惯用多维自动/半自动指标，而不是只看能不能生成。Code2Video 使用效率、美学、TeachQuiz 等维度；TEA 也用多指标 benchmark 评估长视频解释。([arXiv][7]) ([ACL Anthology][6]) 你可以改成适合 HTML interactive AV 的五维 rubric：

| 维度                       | 自动化实现                             |
| ------------------------ | --------------------------------- |
| Layout                   | 截图中元素重叠、canvas 可读性、对象数量           |
| Temporal Consistency     | 相邻帧对象 id 是否稳定、跳动是否异常              |
| Semantic Highlight       | 当前 target/deps 是否在画面中被高亮          |
| Explanation Faithfulness | teaching 文本是否只解释 trace 已有事实       |
| Interaction Quality      | quiz 有选项/答案/解释，点击不改变 trace/result |

第六组是**小规模用户/专家评估**。如果论文 claim 是“可靠生成系统”，用户实验可以是辅助；如果 claim 是“提升学习效果”，就必须有用户实验。更稳妥的 AAAI 主线是先不重押 learning outcome，而是做一个小规模 within-subject study：静态题解、direct HTML、AlgoLab 三种材料；测 post-test 正确率、完成时间、主观可用性、解释清晰度。没有足够 IRB/参与者时，至少做专家评分，不要把“学习效果显著提升”作为主 claim。

### 数据表应当怎么落盘

你的每个 case 都应该导出一行机器可审计记录：

```text
case_id
family
subfamily
difficulty
input_size
expected_result
model
condition
repair_rounds
solve_ok
trace_ok
answer_match
verifier_match
multi_solution_match
process_ready
demo_ready
scene_valid
browser_smoke
interaction_valid
release_ready
num_events
num_frames
teaching_frames
interaction_frames
latency_generate_s
latency_execute_s
latency_render_s
latency_teaching_s
prompt_tokens
completion_tokens
html_size_kb
artifact_size_kb
failure_phase
failure_type
warning_count
```

主结果表报告 mean 和 per-family；所有 100% 指标都给分母，例如 `300/300`、`500/500`。如果你跑 200 个全通过，统计上只能说观察到 100%，95% Wilson 下界大约是 98.1%；500 个全通过下界约 99.24%。所以如果你想让“接近绝对可靠”更有说服力，分母越大越好，但论文措辞仍应是 “on our benchmark”。

### 可以直接用你现有脚本组织实验

你系统里已经有需要的实验入口：`run_llm_benchmark.py` 记录 release gate、warnings/errors、timing、model calls、browser smoke；direct HTML baseline 支持 `--hide-expected`；还有 direct HTML answer audit、no process validator、no scenegraph compiler 等消融脚本。

最小可投稿实验组合是：

```bash
# 1. Full system
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py ...

# 2. Fair direct HTML baseline: expected hidden
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_direct_html_baseline.py \
  --hide-expected \
  --output-dir output/direct_html_no_expected

# 3. Direct HTML answer audit
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/audit_direct_html_answer.py ...

# 4. Ablations
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_no_process_validator_ablation.py ...
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_no_scenegraph_compiler_ablation.py ...

# 5. Browser/interactivity checks
bash scripts/run_browser_smoke_container.sh
```

### 论文里最该打的三句话

第一句：**End-to-end LLM visualizers entangle algorithm execution, visual layout, and pedagogy, causing hallucinated states and unstable demos.**

第二句：**AlgoLab decouples these concerns: LLMs generate executable solvers and DSL traces; deterministic validators and compilers transform verified traces into interactive visualizations.**

第三句：**Correctness is not judged from pixels or browser success; it is enforced by answer oracles, executable traces, schema validation, release gates, and artifact-level evidence.**

### 最终建议

现在立刻冻结一版系统和 prompt，建立 frozen benchmark，不再一边调系统一边往 test set 上跑。先跑 **Full vs Direct HTML no-expected vs Ablations**，拿到一张强主表；再补 process audit 和 visual/interaction audit；最后再做小规模人评。AAAI 审稿人最想看到的不是“我能生成很多漂亮页面”，而是：**为什么这个 LLM 系统比端到端生成更可靠，以及这些正确性证据为什么不是自说自话。**

[1]: https://aaai.org/conference/aaai/aaai-27/ "AAAI-27 - AAAI"
[2]: https://aaai.org/conference/aaai/aaai-26/submission-instructions/ "AAAI-26 Submission Instructions - AAAI"
[3]: https://aaai.org/conference/aaai/aaai-26/supplementary-material/ "AAAI-26 Supplementary Material - AAAI"
[4]: https://jhave.org/ "JHAVE: Home Page"
[5]: https://visualgo.net/ "visualising data structures and algorithms through animation - VisuAlgo"
[6]: https://aclanthology.org/2025.acl-long.332/ "TheoremExplainAgent: Towards Video-based Multimodal Explanations for LLM Theorem Understanding - ACL Anthology"
[7]: https://arxiv.org/html/2510.01174v1 "Code2Video: A Code-centric Paradigm for Educational Video Generation"
[8]: https://arxiv.org/html/2605.12159v1 "ALGOGEN: Tool-Generated Verifiable Traces for Reliable Algorithm Visualization"
