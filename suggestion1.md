你说得对。**Direct Trace / Direct SceneGraph / No SceneGraph / No sanitizer 这些不能叫外部 baseline，最多叫 ablation。** 如果主实验全是这些，确实会显得像“我搭了一套系统，然后把自己拆开打自己”。AAAI 里真正需要的是：**外部生成系统对比 + 传统人工系统参照 + 内部 ablation** 三层分开写。

你现在的实验设计应该改成下面这样。

## 结论先说

主文里的 comparison 应该有三类：

| 类别                                | 放在论文哪里        | 作用                |
| --------------------------------- | ------------- | ----------------- |
| **External generation baselines** | 主结果表          | 证明不是只赢 direct LLM |
| **External reference systems**    | 人评/子集对比/相关工作表 | 证明你不是闭门造车         |
| **Internal ablations**            | 消融表           | 证明系统各模块有必要        |

你担心的“自娱自乐”主要来自把第三类当成第一类。正确写法是：**主对比必须有外部方法；内部 ablation 只用来解释为什么有效。**

---

## 一、真正能作为外部 baseline 的方法

### 1. Code2Video-style baseline

这是你最应该放的外部生成 baseline。Code2Video 是 code-centric educational video generation，它用 Planner/Coder/Critic 通过可执行 Manim 代码生成教育视频，并且原文就是拿 direct code generation 做对比。([arXiv][1])

你的实现方式：

> 给 Code2Video-style baseline 同样的 problem description、input、expected hidden，让它生成 Manim/Python 教育动画或视频脚本；然后用你们的评测器抽取 answer、执行成功率、渲染成功率、过程一致性、视觉错误率。

它不是交互页面，但这正好有利于你：你可以证明**视频生成范式无法覆盖 interactive correctness**，比如 reset、scrub、next、quiz、状态不变性。

主表里可以写：

| Method           | Artifact         | Auto-generated | Answer correctness | Process fidelity | Render success | Interactive validity |
| ---------------- | ---------------- | -------------: | -----------------: | ---------------: | -------------: | -------------------: |
| Direct HTML      | Interactive HTML |              ✓ |                  x |                x |              x |                    x |
| Code2Video-style | Video/Manim      |              ✓ |                  x |                x |              x |                  N/A |
| ALGOGEN          | Passive AV/video |              ✓ |                  x |                x |              x |                  N/A |
| Ours             | Interactive HTML |              ✓ |                  x |                x |              x |                    x |

这样就不是只和 direct HTML 比了。

---

### 2. TheoremExplainAgent / Manim-agent baseline

TheoremExplainAgent 是 agentic Manim 长视频解释系统，构建了 TheoremExplainBench，包含 240 个 STEM theorem，并报告 agentic planning 对长视频解释很关键。([arXiv][2]) 它不是算法可视化专用，但它代表了“LLM agent + Manim 视觉解释”的一类外部方法。

你的做法不是完整复现 theorem benchmark，而是设一个 **Manim-agent baseline**：

> 用 agentic prompt，让模型规划算法讲解步骤，再生成 Manim/Python 动画代码；执行 Manim，评估能否渲染、答案是否正确、状态是否忠实。

这个 baseline 的价值是：它比 direct HTML 强，因为它也用可执行视觉后端；但它通常没有你的 `solve/trace/result/SceneGraph/release gate` 证据链。

---

### 3. Learner-Customized Algorithm Visualization Using Generative AI

这篇 ACM 2026 的工作题目非常接近，摘要说它提出了 generative AI–based visualization system，并且 independent of specific algorithms。([ACM数字图书馆][3]) 这篇必须写进 related work。如果有代码，就直接作为外部 baseline；如果没有代码，也要做 qualitative comparison，并尝试复现其高层 prompt 流程作为 “GenAI-AV baseline”。

你的论文里可以这样处理：

> Since prior GenAI-based AV systems do not always release executable pipelines, we compare against an implementation-level approximation following their task setting: LLM-generated learner-customized AV without executable semantic trace grounding.

这比只放 direct HTML 好很多。

---

### 4. ALGOGEN 作为 external prior，不是 internal ablation

虽然 ALGOGEN 是你们之前的工作，但它在这篇新论文里应该作为 **strong prior system baseline**，而不是消融。ALGOGEN 已经提出 tool-generated verifiable traces，把算法执行和渲染解耦，并在 200 个 LeetCode AV benchmark 上报告了高于 end-to-end 方法的成功率。([arXiv][4])

你可以把它作为：

> Passive verifiable AV baseline.

它回答的问题是：

> 从可验证视频/被动可视化升级到交互式操作页面，到底带来了什么新问题？

你要报告 ALGOGEN 没法评估或天然不支持的指标：

| 指标                                    | ALGOGEN | 新系统 |
| ------------------------------------- | ------: | --: |
| Answer correctness                    |       ✓ |   ✓ |
| Trace validity                        |       ✓ |   ✓ |
| Passive render success                |       ✓ |   ✓ |
| User-controlled replay                |     N/A |   ✓ |
| Random frame jump consistency         |     N/A |   ✓ |
| Reset/play/next correctness           |     N/A |   ✓ |
| Quiz does not alter state             |     N/A |   ✓ |
| Teaching overlay factual immutability |     N/A |   ✓ |

这能把“新系统不是换 renderer”讲清楚。

---

## 二、传统工具不能当主 baseline，但可以当 external reference

这些系统不是自动生成任意 LeetCode 题目的，所以不能和你在 generation success 上直接比。但是它们可以做 **reference comparison**，用来回应“你是不是只在自己系统内评估”。

### 1. VisuAlgo

VisuAlgo 是人工构建的交互式数据结构与算法学习平台，目标是帮助学生 self-paced interactive learning。([VisuAlgo][5]) 它适合当 **human-authored reference**。

你可以选 10–20 个它支持的算法，比如 BFS、DFS、Dijkstra、MST、sorting、binary heap、segment tree，然后做：

| 比较项                      | VisuAlgo | Ours |
| ------------------------ | -------- | ---- |
| 是否人工制作                   | 是        | 否    |
| 是否支持任意 LeetCode-style 题目 | 否        | 是    |
| 是否支持用户给定输入               | 部分支持     | 是    |
| 是否有 answer oracle        | 固定算法场景   | 是    |
| 是否能自动生成新题页面              | 否        | 是    |
| 交互质量人评                   | x        | x    |
| 解释清晰度人评                  | x        | x    |

这不是“我比 VisuAlgo 强”，而是：

> Our generated artifacts approach the interaction quality of human-authored AV tools while supporting automatic generation for unseen tasks.

这个 claim 合理。

---

### 2. OpenDSA / JSAV

OpenDSA 是面向数据结构、算法等课程的开源在线教材/基础设施；JSAV 是用于构建算法可视化的 JavaScript library，并且是 OpenDSA 项目的一部分。([OpenDSA][6]) ([GitHub][7])

这类工具可以作为 **authoring-effort baseline**：

| System       | New algorithm authoring effort | Needs developer? | Auto-generate from problem? | Interactive exercises |
| ------------ | -----------------------------: | ---------------: | --------------------------: | --------------------: |
| JSAV/OpenDSA |                              高 |                是 |                           否 |                     是 |
| AlgoLab      |                           低/自动 |              否或弱 |                           是 |                     是 |

这里最好补一个实验：让一个熟悉 JSAV 的人手写 3 个算法页面，记录时间；你们系统生成同样页面，记录时间和质量。这个实验会很有杀伤力。

---

### 3. Python Tutor / Jeliot

Python Tutor 是程序执行可视化工具，可以在浏览器中逐步查看代码运行时变量状态。([Python Tutor][8]) Jeliot 3 也是经典 program visualization 工具，用于帮助初学者学习过程式和面向对象编程。([ACM数字图书馆][9])

它们适合作为 **program visualization baseline**：

> 给同一个 `solve` 代码，Python Tutor/Jeliot 展示的是程序运行状态；AlgoLab 展示的是算法语义状态。

这组对比很重要，因为审稿人可能问：你为什么不用现有代码可视化器？

你可以设计一个小实验：

| Method             | Input           | Output                                 | Strength           | Weakness                                |
| ------------------ | --------------- | -------------------------------------- | ------------------ | --------------------------------------- |
| Python Tutor-style | Code            | Variable-level trace                   | faithful execution | no algorithm-level teaching abstraction |
| AlgoLab            | Problem + input | Algorithm semantic trace + interaction | semantic teaching  | depends on generated tracker            |

然后让人评比较：

* 哪个更容易看懂算法思想？
* 哪个更容易找到关键转移？
* 哪个更适合教学？
* 哪个状态更忠实？

---

### 4. dpvis / iFlow

dpvis 是动态规划可视化工具，可以通过对标准 Python DP 实现做少量修改生成 frame-by-frame animation，并支持询问下一步操作。([arXiv][10]) iFlow 是 Max-Flow/Min-Cut 的交互式可视化工具，支持用户手动执行算法步骤、错误反馈和自动补全。([arXiv][11])

这两个非常适合做 **domain-specific external reference**：

| Domain              | External tool | Your comparison  |
| ------------------- | ------------- | ---------------- |
| Dynamic Programming | dpvis         | DP 子集质量、人评、交互题质量 |
| Max-flow            | iFlow         | 专用工具 vs 自动生成泛化系统 |

这类比较要谨慎写：

> We do not claim to outperform domain-specific hand-engineered tools. Instead, we evaluate whether automatically generated interactive demos can approach their pedagogical utility on overlapping tasks.

这句话很重要，避免被审稿人攻击。

---

## 三、推荐你最终的实验结构

主文最好放四张表。

### Table 1：Main external generation comparison

这张表只放真正的自动生成 baseline：

| Method           | Type                      | Input           | Output           | Auto generation | Answer correctness | Process fidelity | Render success | Interaction validity |
| ---------------- | ------------------------- | --------------- | ---------------- | --------------: | -----------------: | ---------------: | -------------: | -------------------: |
| Direct HTML      | End-to-end LLM            | Problem + input | HTML             |               ✓ |                    |                  |                |                      |
| Direct JS/Canvas | End-to-end code           | Problem + input | JS app           |               ✓ |                    |                  |                |                      |
| Code2Video-style | Agentic Manim             | Problem + input | Video            |               ✓ |                    |                  |                |                  N/A |
| ALGOGEN          | Verifiable passive AV     | Problem + input | Video/passive AV |               ✓ |                    |                  |                |                  N/A |
| Ours             | Verifiable interactive AV | Problem + input | Interactive HTML |               ✓ |                    |                  |                |                      |

这里才是“对比”。

---

### Table 2：External reference comparison on overlapping algorithms

这张表放 VisuAlgo、OpenDSA/JSAV、Python Tutor、dpvis、iFlow：

| System       | Task type                 | Auto-generate unseen problem? | Arbitrary input? | Algorithm-level trace? | Interactive exercise? | Verifiable answer? |
| ------------ | ------------------------- | ----------------------------: | ---------------: | ---------------------: | --------------------: | -----------------: |
| VisuAlgo     | hand-authored AV          |                             ✗ |               部分 |                      ✓ |                     ✓ |               固定场景 |
| OpenDSA/JSAV | hand-authored course AV   |                             ✗ |               部分 |                      ✓ |                     ✓ |               固定练习 |
| Python Tutor | program visualization     |                             ✗ |       code-level |       ✗/variable-level |          step-through |    execution-level |
| dpvis        | DP-specific visualization |  ✗/requires code modification |                ✓ |            DP-specific |                     ✓ |    domain-specific |
| iFlow        | max-flow-specific tool    |                             ✗ |                ✓ |      max-flow-specific |                     ✓ |    domain-specific |
| Ours         | generated interactive AV  |                             ✓ |                ✓ |                      ✓ |                     ✓ |                  ✓ |

这不是主性能表，而是定位表。

---

### Table 3：Human/expert evaluation

这是最能消除“自娱自乐”的实验。选 12–20 个 overlapping cases：

* sorting / heap / graph shortest path / BFS / DFS / DP / union-find / segment tree
* 对每个 case，准备：

  * AlgoLab 生成页面
  * VisuAlgo/OpenDSA/Python Tutor/dpvis/iFlow 中最接近的页面或结果
  * Direct HTML baseline 页面
  * Code2Video/ALGOGEN 视频

让算法老师、TA、研究生或学生盲评：

| Metric                 | Direct HTML | Code2Video | ALGOGEN | Human-authored AV | Ours |
| ---------------------- | ----------: | ---------: | ------: | ----------------: | ---: |
| Algorithm correctness  |             |            |         |                   |      |
| Process faithfulness   |             |            |         |                   |      |
| Interaction usefulness |             |        N/A |     N/A |                   |      |
| Explanation clarity    |             |            |         |                   |      |
| Overall preference     |             |            |         |                   |      |

这个表非常关键。哪怕你机器指标 100%，审稿人还是会怀疑“页面是否真的有教学价值”。人评能补上。

---

### Table 4：Internal ablation

最后才放你们自己的模块消融：

| Variant               | Answer correctness | Trace validity | Scene validity | Browser pass | Interaction validity | Release ready |
| --------------------- | -----------------: | -------------: | -------------: | -----------: | -------------------: | ------------: |
| Full                  |                    |                |                |              |                      |               |
| No DSL                |                    |                |                |              |                      |               |
| Direct Trace JSON     |                    |                |                |              |                      |               |
| Direct SceneGraph     |                    |                |                |              |                      |               |
| No interaction gate   |                    |                |                |              |                      |               |
| No teaching sanitizer |                    |                |                |              |                      |               |
| No repair             |                    |                |                |              |                      |               |

这张表的作用是解释机制，不是外部对比。

---

## 四、最小可执行版本

如果时间不够，不要全做。最小但有说服力的版本是：

1. **主自动生成对比**

   * Direct HTML no-expected
   * Direct JS/Canvas
   * Code2Video-style Manim baseline
   * ALGOGEN passive baseline
   * Ours

2. **外部人工系统子集对比**

   * VisuAlgo/OpenDSA/Python Tutor/dpvis/iFlow 选 2–3 个即可
   * 只在 overlapping algorithms 上做人评，不强行跑全 benchmark

3. **内部消融**

   * No DSL / Direct Trace JSON
   * Direct SceneGraph
   * No interaction gate
   * No teaching sanitizer

这样就不会显得自娱自乐。

---

## 五、论文叙事应该这样写

不要写：

> We compare with direct LLM generation and ablations.

这太弱。

应该写：

> We evaluate AlgoLab against three classes of baselines: external generative baselines for automated educational visualization, prior verifiable passive AV generation, and human-authored interactive AV systems on overlapping algorithms. Internal ablations are reported separately to isolate the contribution of executable tracing, semantic compilation, interaction validation, and teaching-overlay constraints.

中文意思是：

> 我们不是只和 direct LLM 比，而是和自动生成系统、前作被动可视化系统、人工交互式算法可视化系统分别比较；内部消融只用于解释模块贡献。

---

## 最终判断

你这个担心完全正确。**如果主表只有 Direct HTML + 一堆 internal ablation，AAAI 审稿人很可能会觉得 baseline 弱。**

改法是：

* **Direct HTML / Direct JS**：作为通用 LLM app generation baseline。
* **Code2Video / Manim-agent**：作为外部教育视频生成 baseline。
* **ALGOGEN**：作为你们自己的 prior passive AV baseline。
* **VisuAlgo / OpenDSA / Python Tutor / dpvis / iFlow**：作为外部 reference systems，在重叠任务上做人评或质量对比。
* **Direct Trace / Direct SceneGraph / No sanitizer / No gate**：只放 ablation，不要包装成外部 baseline。

这样实验结构会从“自己和自己比”变成：

> 我们和现有自动生成方法比可靠性，和前作比交互能力，和人工系统比教学可用性，再用消融解释为什么有效。

[1]: https://arxiv.org/abs/2510.01174?utm_source=chatgpt.com "Code2Video: A Code-centric Paradigm for Educational Video Generation"
[2]: https://arxiv.org/abs/2502.19400?utm_source=chatgpt.com "TheoremExplainAgent: Towards Multimodal Explanations for LLM Theorem Understanding"
[3]: https://dl.acm.org/doi/10.1145/3789595.3789607?utm_source=chatgpt.com "Learner-Customized Algorithm Visualization Using ..."
[4]: https://arxiv.org/abs/2605.12159?utm_source=chatgpt.com "ALGOGEN: Tool-Generated Verifiable Traces for Reliable Algorithm Visualization"
[5]: https://visualgo.net/?utm_source=chatgpt.com "VisuAlgo: visualising data structures and algorithms through ..."
[6]: https://opendsa-server.cs.vt.edu/?utm_source=chatgpt.com "OpenDSA"
[7]: https://github.com/vkaravir/JSAV?utm_source=chatgpt.com "vkaravir/JSAV: JavaScript Algorithm Visualization library"
[8]: https://pythontutor.com/?utm_source=chatgpt.com "Python Tutor - Python Online Compiler with Visual AI Help"
[9]: https://dl.acm.org/doi/10.1145/989863.989928?utm_source=chatgpt.com "Visualizing programs with Jeliot 3 | Proceedings of the ..."
[10]: https://arxiv.org/abs/2411.07705?utm_source=chatgpt.com "dpvis: A Visual and Interactive Learning Tool for Dynamic Programming"
[11]: https://arxiv.org/abs/2411.10484?utm_source=chatgpt.com "iFlow: An Interactive Max-Flow/Min-Cut Algorithms Visualizer"
