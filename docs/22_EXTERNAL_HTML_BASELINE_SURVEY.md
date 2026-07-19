# AlgoTutorGen 外部 Web/HTML Baseline 调研

**调研日期：** 2026-07-12  
**目标：** 寻找能够作为 AlgoTutorGen 外部 baseline、并可通过浏览器纳入现有 HTML 评测链路的同类工作。

本文档只保留候选系统调研、纳入标准和接入分析。已执行 baseline 在主论证中的作用见 `docs/EXPERIMENT_RESULTS.md` 第 2 节，WebGen-Agent、HTMLCure、EduVisAgent 与传统系统 overlap 的详细边界见第 11.3 节。

## 1. 结论摘要

当前没有发现一个同时满足下列全部条件的公开系统：

1. 输入任意算法题描述和样例；
2. 自动生成新的交互式算法教学 HTML；
3. 包含预测、正误反馈、hint、答案和学习日志；
4. 有公开代码或批量 API；
5. 能直接覆盖当前 200-task benchmark。

现有系统主要分成三类：

- **通用程序执行可视化器**：接受代码并逐步显示运行状态，例如 Python Tutor；
- **人工预制算法可视化/练习库**：例如 Algorithm Visualizer、OpenDSA/JSAV、VisuAlgo；
- **课程与对话式教学平台**：例如 VisualCodeMOOC，能动态呈现部分算法，但视觉模板仍是预制的。

因此，最合理的论文实验不是用某一个外部系统强行替换 Direct HTML 的 200-task 全量 baseline，而是增加一个单独的 **External Web Systems Study**：

1. **Algorithm Visualizer**：推荐，作为主要外部算法可视化 baseline，在严格匹配的重叠算法子集上评测；
2. **Python Tutor**：推荐，作为通用代码执行可视化 baseline，可在更大的可执行 Python 子集上评测；
3. **OpenDSA/JSAV**：可选，作为成熟交互式算法教学/自动练习系统参考；
4. **VisualCodeMOOC**：可选，作为近期对话式算法教学平台参考，但模板覆盖较小；
5. **VisuAlgo**：只建议做定性或小规模参考，不建议依赖线上服务完成核心可复现实验。

现有 **Direct HTML baseline 必须保留**。它仍是唯一与 AlgoTutorGen 在“针对任意新题自动生成页面”这一任务定义上完全对齐的 baseline。

---

## 2. 纳入标准

候选系统按以下标准评估：

| 维度 | 问题 |
|---|---|
| Task fit | 是否接受新题、代码或输入，而不是只能播放固定案例？ |
| Web output | 是否可以在浏览器中操作，并能进入 Playwright 评测？ |
| Coverage | 与当前 200 个 benchmark task 有多少算法重叠？ |
| Interactivity | 是否支持步进、修改输入、练习、反馈或对话？ |
| Reproducibility | 是否开源、可本地部署、可固定版本？ |
| Automation | 是否存在 API、可注入输入，或可稳定通过 DOM 自动化？ |
| Fair metrics | 与 Stage1 有哪些真正共同、可比较的指标？ |

一个外部系统即使很成熟，如果只能展示人工制作的固定算法，也不能进入“200 个新题自动生成成功率”的同一分母。它可以回答展示质量或成熟教学交互问题，但不能回答自动生成能力问题。

---

## 3. 候选系统总表

| 系统 | 类型 | Web/HTML | 新题自动生成 | 可本地部署 | 预估重叠 | 建议 |
|---|---|---:|---:|---:|---:|---|
| Algorithm Visualizer | 代码插桩式算法可视化平台 | 是 | 否；需 tracer 插桩 | 是，MIT Web app | 约 20 个严格算法 | **推荐，重叠子集主 baseline** |
| Python Tutor | 通用代码执行可视化 | 是 | 接受任意受支持代码 | 可使用旧开源版本；当前线上版需单独固定 | 很大，但非算法专属视图 | **推荐，通用执行可视化 baseline** |
| OpenDSA/JSAV | 电子教材、可视化与自动练习 | 是 | 否；人工制作 AV/exercise | 是，MIT | 中等，需逐项映射 | 可选，成熟教学系统参考 |
| VisualCodeMOOC | 对话代理 + 动态可视化课程平台 | 是 | 对话动态，但视觉模板预制 | 是，MIT | 约 6–10 个模板主题 | 可选，小子集近期 baseline |
| VisuAlgo | 统一算法可视化网站 | 是 | 否；固定模块 | 在线可访问；复现和许可不如开源候选清晰 | 中等 | 只做定性/小规模参考 |
| Mornar et al. 2014 | 伪代码解释生成算法可视化 | 论文系统 | 是，有限伪代码语言 | 未发现可用公开实现 | 未知 | Related work，不宜执行比较 |
| VisualCodeChat/VisualCodeMOOC | 动态教学对话 | 是 | 部分动态 | 是 | 小 | 与 VisualCodeMOOC 合并考虑 |
| TheoremExplainAgent | LLM 生成 Manim 数学证明视频 | 否，输出视频 | 是 | 是，MIT | 任务不匹配 | Related work，不是 HTML baseline |
| CODE2VIDEO | 代码教育视频生成 | 否，输出视频 | 是 | 未确认官方可运行实现 | 任务/输出不匹配 | Related work，不是 HTML baseline |

“预估重叠”必须在真正运行前由显式 mapping manifest 固定。不能通过模糊关键词把不同问题算作同一算法。

---

## 4. 重点候选分析

### 4.1 Algorithm Visualizer

**项目：** https://github.com/algorithm-visualizer/algorithm-visualizer  
**算法库：** https://github.com/algorithm-visualizer/algorithms  
**在线页面：** https://algorithm-visualizer.org/  
**许可：** Web app 为 MIT；算法库的具体许可文件需在冻结版本时再次核对。

Algorithm Visualizer 是最适合加入当前实验的外部 Web baseline。其 Web app 使用 React/Node，代码通过各语言 tracer 库产生视觉命令，前端解释这些命令并展示数组、图、日志等状态。该架构与 AlgoTutorGen 的“程序产生语义命令，再由固定 Runtime 呈现”具有可比较性，但 Algorithm Visualizer 的算法通常由人类提前插桩，不是从任意题目自动生成。

公开 JavaScript 算法库当前包含约 61 个 `code.js` 实现。与本项目明确重叠的候选包括：

- Bubble/Insertion/Counting Sort；
- Dijkstra、Bellman–Ford、Floyd–Warshall、Kruskal；
- Topological Sort、Bipartiteness、Tarjan SCC；
- KMP、Rabin–Karp、Z Algorithm；
- LCS、Edit Distance、Maximum Subarray、Knapsack；
- Sieve of Eratosthenes、GCD；
- Lowest Common Ancestor、Cycle Detection；
- Sliding Window 等。

#### 可比较内容

- 页面能否加载且无 JavaScript/page error；
- 是否存在可操作的 step/play/reset；
- 是否能够看到算法状态；
- 代码与当前状态是否同步；
- 页面视觉可读性；
- 同一算法、同一输入下最终状态是否与 oracle 一致；
- 时间线/步数和输入修改能力（若该页面支持）。

#### 不应比较

- 200-task generation success：Algorithm Visualizer 没有对 200 个题逐题生成页面；
- hint、show-answer、learning log：它的任务目标不是生成 tutoring checkpoint；
- repair success 和 token cost：它不是 LLM 生成系统；
- 将预制专家页面视为与自动生成页面同等成本。

#### 推荐定位

> Human-authored, tracer-based external algorithm visualization baseline on an exact-overlap subset.

它可以作为展示质量与运行稳定性的“专家制作上界/参考”，不能替代 Direct HTML 生成 baseline。

### 4.2 Python Tutor

**论文：** Philip J. Guo. *Online Python Tutor: Embeddable Web-Based Program Visualization for CS Education*. SIGCSE 2013. DOI: `10.1145/2445196.2445368`  
**网站：** https://pythontutor.com/visualize.html  
**历史代码：** https://github.com/hcientist/OnlinePythonTutor

Python Tutor 接受 Python、JavaScript、C、C++ 和 Java 等代码，在 Web 中逐步展示栈帧、变量、对象引用和输出。它不是算法专属教学页面，但能够处理比预制算法库更广泛的 benchmark solver。

#### 接入方式

从 benchmark 的 `solve(input_data)` 生成一个固定 wrapper：

```python
input_data = {...}
result = solve(input_data)
print(result)
```

将代码与输入送入固定版本的 Python Tutor trace generator，再使用其 embeddable frontend 或本地 Web 页面渲染。评测必须冻结代码版本，不能依赖会持续更新的线上服务作为唯一结果来源。

#### 优点

- 输入是实际代码，任务覆盖可能远大于预制算法平台；
- 逐步执行状态来自解释器，运行过程具有较强客观性；
- 是程序可视化教育领域的经典 baseline；
- Web UI 可以用 Playwright 操作和截图。

#### 局限

- 展示的是语言级内存和调用栈，不是算法语义视图；
- 不理解题目、学习目标、算法依赖或不变量；
- 没有与当前页面同构的预测题、hint、双向反馈和学习日志；
- 某些 benchmark solver 依赖受限导入、复杂对象或长 trace，需要设置最大步数和兼容性规则；
- 历史开源仓库较旧，当前网站实现与旧代码可能不完全一致，需明确采用哪个版本。

#### 推荐定位

> General-purpose execution visualization baseline using the same executable solver and input.

Python Tutor 适合比较 page load、step navigation、state visibility、code synchronization 和视觉/认知负担，不适合参与 Stage1 的 tutoring-specific Machine OK 综合分。

### 4.3 OpenDSA / JSAV

**OpenDSA：** https://github.com/OpenDSA/OpenDSA  
**JSAV：** https://github.com/vkaravir/JSAV  
**许可：** MIT  
**JSAV 论文：** Ville Karavirta and Clifford A. Shaffer. *JSAV: The JavaScript Algorithm Visualization Library*. ITiCSE 2013. DOI: `10.1145/2462476.2462487`  
**相关论文：** *Creating Engaging Online Learning Material with the JSAV JavaScript Algorithm Visualization Library*. IEEE TLT, DOI: `10.1109/TLT.2015.2490673`。

OpenDSA 是开源电子教材平台，目标是把教材内容、算法可视化和自动评测练习深度整合。仓库包含大量 HTML/JavaScript AV 和 proficiency exercise，例如 binary search、sorting、heap、BST、linked list 等。

#### 优点

- 成熟、学术来源明确；
- 具有真实自动练习与学习交互，不只是播放器；
- 可通过 Docker 本地构建并用浏览器评测；
- JSAV/OpenDSA 使用 MIT 许可，复现条件较好。

#### 局限

- 页面是人类为固定知识点制作，不接受任意 benchmark problem；
- 题目粒度和输入格式与 AlgoTutorGen 不同；
- 某些练习依赖 OpenDSA 课程构建、服务端或登录基础设施；
- 将 OpenDSA 的 proficiency exercise 映射为本项目的 expected/result 需要逐题 adapter。

#### 推荐定位

仅在 10–20 个严格重叠算法上做 **expert-authored interactive learning environment reference**。它适合回答：“自动生成页面距离成熟人工教学内容有多远？”不适合回答自动生成成功率。

### 4.4 VisualCodeMOOC

**论文：** Mingyuan Li et al. *VisualCodeMOOC: A Course Platform for Algorithms and Data Structures Integrating a Conversational Agent for Enhanced Learning through Dynamic Visualizations*. SoftwareX 30 (2025), 102072. DOI: `10.1016/j.softx.2025.102072`  
**代码：** https://github.com/XJTLU-AIED/VisualCodeMOOC  
**Demo：** https://duuan.github.io/visualcodemooc/  
**许可：** MIT

VisualCodeMOOC 是近期且任务相关度较高的系统：它将课程、对话代理 VisualCodeChat、动态可视化和练习结合。README 声称对话中可基于随机例子生成实时可视化，并提供解释、代码学习和练习。

但其代码显示可视化层依赖预定义 React 模板。当前明确可见的模板包括 binary search、bubble sort、insertion sort、selection sort、数组查找/最大值、graph connectivity 和 graph cycle 等，新增算法仍需要人工创建新的 visual 文件并接入路由。

#### 推荐定位

可以作为 6–10 个主题的小规模 contemporary conversational-learning baseline，比较：

- 对话与页面结合方式；
- 练习可达性；
- 动态例子；
- 反馈、解释与视觉协调；
- 浏览器稳定性和 VLM/人工评价。

它不应进入 200-task generation denominator，也不能假设任意 benchmark task 都能自动选择正确视觉模板。运行其对话代理还需要配置 OpenAI-compatible API，并冻结 prompt、模型和随机例子。

### 4.5 VisuAlgo

**论文：** Steven Halim et al. *Learning Algorithms with Unified and Interactive Web-Based Visualization*. Olympiads in Informatics 6 (2012), 53–68.  
**网站：** https://visualgo.net/

VisuAlgo 是经典且成熟的算法可视化平台，适合作为相关工作和定性参考。部分模块允许用户修改输入并播放算法步骤。

不建议把它作为核心可复现 baseline，原因是：

- 主要是线上服务和人工预制模块；
- 模块与 benchmark task 不是逐题对应；
- 本地冻结、批量自动化和许可边界不如上述开源候选清晰；
- 页面结构随线上版本变化会损害复现性。

若采用，应只评测少量明确重叠算法，并记录访问日期、输入、URL、截图和 DOM adapter。

### 4.6 2014 伪代码解释生成系统

**论文：** Jure Mornar, Andrina Granić, and Saša Mladenović. *System for Automatic Generation of Algorithm Visualizations Based on Pseudocode Interpretation*. ITiCSE 2014, pp. 27–32. DOI: `10.1145/2591708.2591743`。

这是检索到的最直接传统同类工作之一：从受支持的伪代码解释生成算法可视化。它应进入 Related Work，并用于说明自动 AV 生成在 LLM 之前已有研究。

但目前没有找到可直接下载、批量运行并适配当前 200-task benchmark 的官方公开实现。因此，除非联系作者获得系统或代码，否则不能作为可执行 baseline。论文中不能用自行重实现后仍称为原系统结果；若重实现，只能标为 `reimplementation inspired by Mornar et al.`。

---

## 5. 不适合作为 HTML Baseline 的相关工作

### TheoremExplainAgent

ACL 2025 oral，生成数学定理解释的 Manim 视频，官方代码 MIT。任务是数学证明且输出为视频，不是算法学习 HTML。适合作为 LLM 教育视频 related work，不适合当前共同浏览器交互指标。

### CODE2VIDEO

生成代码教育视频，输出模态、交互能力和任务输入与本项目不同。若官方实现和数据可用，可作为视频生成领域参考，但不能参与 hint、feedback、learning-log 等 HTML 行为指标。

### LLM 数据可视化系统

LIDA、NVAgent 等从数据或自然语言生成 chart/spec。它们解决数据分析可视化，不模拟算法执行过程，也不生成算法教学交互，不应作为主要 baseline。

---

## 6. 推荐实验设计

### 6.1 保留现有全量主实验

继续使用 200-task：

```text
AlgoTutorGen Stage1 vs strong Direct HTML generation
```

这是唯一公平回答“对任意新题自动生成完整学习页面”能力的主实验。

### 6.2 新增 Exact-Overlap External Web 子集

构造 `external_web_overlap_manifest.json`，每一行至少包含：

```json
{
  "case_id": "dijkstra_shortest_path",
  "canonical_algorithm": "dijkstra",
  "input": {"graph": {}, "start": "A"},
  "expected": {},
  "systems": {
    "algotutorgen_stage1": {"artifact": "..."},
    "direct_html": {"artifact": "..."},
    "algorithm_visualizer": {"algorithm_path": "...", "adapter": "..."},
    "python_tutor": {"solver_wrapper": "..."},
    "opendsa": {"exercise_path": "...", "adapter": "..."}
  }
}
```

推荐先做约 15–20 个严格重叠算法，覆盖：

- sorting/search；
- graph shortest path/MST/connectivity；
- dynamic programming；
- string matching；
- tree/recursion；
- math。

禁止为了扩大 N，把算法名称近似但任务、输入或目标不同的页面算作相同 case。

### 6.3 共同指标

外部系统只比较所有参与方法都具备的功能：

| 指标 | 自动化方式 |
|---|---|
| page_load_ok | Playwright body/console/pageerror |
| step_navigation_ok | next/prev/play/timeline 后状态变化 |
| algorithm_state_visible | DOM + screenshot/VLM |
| code_state_sync | 当前代码行与状态转移是否同步 |
| final_result_match | 可抽取时与统一 oracle 比较 |
| custom_input_supported | 是否能注入统一输入并重新运行 |
| visual_readability | 相同截图协议下的盲评/VLM |
| process_clarity | 多帧或统一关键帧评价 |
| interaction_latency | 页面加载与步进响应时间 |

### 6.4 分层指标

不要把系统缺少其任务范围之外的功能直接判为失败：

- `Common Web Visualization`：所有系统共同指标；
- `Tutoring Capability`：只对声称提供练习/教学反馈的系统比较；
- `Generative Scalability`：只对能够针对新题生成产物的 Stage1 与 Direct 比较；
- `Verification Evidence`：报告系统是否提供结构化 correctness evidence，不把“没有私有 SceneGraph”作为页面错误。

### 6.5 输入公平性

理想情况使用同一 case 和同一输入。若外部平台无法接受自定义输入，应标记 `fixed_example_only`，并把它从 result correctness 的配对统计中排除，只保留系统级视觉/交互参考。

Python Tutor 使用 benchmark 的同一 solver 和 input，因此最容易做输入配对。Algorithm Visualizer/OpenDSA 的输入 adapter 需要逐题检查，不能只修改页面展示文本而不改变真实执行状态。

### 6.6 人工制作成本

外部预制系统的页面是人工长期开发结果。论文中应明确：

- 它们是 expert-authored references，不是零成本自动生成器；
- 不比较 generation token cost；
- 可以作为页面质量上界，但不能作为 generative scalability baseline；
- adapter 只负责输入格式和自动化，不允许为其补写缺失教学功能。

---

## 7. 推荐优先级与工作量

### P0：Algorithm Visualizer，15–20 case

这是最值得补的外部 baseline。开源、Web、算法重叠较多、视觉形态相近，审稿人容易理解。

需要完成：

1. 冻结 Web app 和 algorithms commit；
2. 构建本地容器或静态服务；
3. 建立严格算法 mapping；
4. 为每个页面编写 Playwright adapter；
5. 尽可能注入相同输入；
6. 运行共同机器指标和同口径截图评价。

预计主要成本在逐算法 adapter，而不是模型调用。

### P1：Python Tutor，20–50 case

选取能在固定 Python Tutor 版本执行且 trace 长度合理的 solver。统一 wrapper 可以减少逐题 adapter 成本。它能回答“通用 execution visualization 与 algorithm-semantic learning environment 有何差异”。

### P2：OpenDSA 或 VisualCodeMOOC，8–15 case

二选一即可：

- 若强调自动评测练习和经典教育系统，选 OpenDSA；
- 若强调近期 LLM 对话与动态教学，选 VisualCodeMOOC。

不建议同时投入大量工程成本，因为二者都不能覆盖 200 个新题。

### 不推荐作为当前投稿阻塞项

- 联系 2014 系统作者并等待私有代码；
- 对 VisuAlgo 做大规模线上爬取；
- 把视频生成系统转成 HTML；
- 自行复刻外部系统后将其写成原方法官方结果。

---

## 8. 对论文实验结构的建议

正文可以组织为：

1. **Main generative comparison (N=200)**  
   AlgoTutorGen vs Direct HTML，回答生成可靠性和教学交互。

2. **External Web systems study (N≈15–20 exact overlap)**  
   AlgoTutorGen、Direct、Algorithm Visualizer、Python Tutor；可选加入 OpenDSA/VisualCodeMOOC。

3. **Presentation enhancement study (N=200)**  
   Stage2 vs Direct，同口径视觉评价。

4. **Gate soundness and ablations**  
   fault injection 与组件消融。

这种结构比把外部预制系统硬并入 200-task 主表更严谨。它既补充了审稿人可能要求的外部系统比较，也保留了任务定义和分母的公平性。

---

## 9. 最终建议

**建议补外部 baseline，但不要替换现有 Direct HTML。**

最优方案是：

```text
Full 200-task generative study:
  AlgoTutorGen vs Direct HTML

Exact-overlap external Web study:
  AlgoTutorGen vs Direct HTML vs Algorithm Visualizer vs Python Tutor

Optional small educational-system reference:
  OpenDSA or VisualCodeMOOC
```

如果投稿时间只允许增加一个系统，选择 **Algorithm Visualizer**。如果允许增加第二个，选择 **Python Tutor**。这两个系统分别代表算法专属 tracer 可视化和通用程序执行可视化，能与 AlgoTutorGen 形成清晰的方法谱系。

当前未发现能对 200 个新题自动生成完整教学 HTML 的公开同类系统。这不是实验缺陷，但必须在论文中明确说明 external systems 只能在 exact-overlap subset 上比较，而 Direct HTML 是全量生成任务的主要 baseline。
