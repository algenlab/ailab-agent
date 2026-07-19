

先给一个\*\*判断\*\*：你们下一步不要把它说成“算法可视化 demo 升级版”，而应该重定义成：



> \*\*LLM-generated verifiable interactive algorithm learning environments\*\*  

> 从“生成视频/HTML”升级为“生成一个可执行、可验证、可交互、可教学评估的算法学习环境”。



这样才有 top conference 的论文空间。否则 reviewer 很容易说：\*\*demo 很酷，但 scientific contribution 不够清楚\*\*。



\---



\## 1. 你们现在最该抓住的核心 novelty



你们 ACL Findings 这篇 ALGOGEN 已经做了：



\- LLM 不直接写 Manim；

\- LLM 生成 tracker；

\- tracker 输出 VTA-JSON；

\- deterministic renderer 渲染；

\- 用 schema validation 和 repair 提升可靠性。



下一篇不能只是“把 renderer 从 Manim 换成 HTML”。真正的升级应该是：



> \*\*从“verifiable visualization trace”升级到“verifiable learning environment”。\*\*



也就是说，不只是 replay algorithm，而是让学生可以：



1\. 改输入；

2\. 单步执行；

3\. 预测下一步；

4\. 回答 why/how 问题；

5\. 得到 grounded hints；

6\. 被系统自动判定理解是否正确；

7\. 系统本身可以被自动验证没有 hallucination、没有错误交互、没有错误反馈。



\---



\## 2. 我建议的论文主线



可以暂定题目类似：



> \*\*AlgoTutorGen: Verifiable Generation of Interactive Algorithm Learning Environments with LLMs\*\*



或者更硬一点：



> \*\*From Traces to Tutors: Reliable LLM Generation of Verifiable Interactive Algorithm Learning Environments\*\*



核心贡献写成四点：



1\. \*\*Interactive Learning Trace IR\*\*  

&#x20;  在 VTA 之上扩展一个交互层，比如叫 \*\*ITA / IELA-JSON\*\*：不仅记录算法状态变化，还记录 learner action、quiz、hint、feedback、rubric。



2\. \*\*LLM-as-Environment-Maker\*\*  

&#x20;  LLM 不直接写任意 HTML，而是生成：

&#x20;  - algorithm tracker；

&#x20;  - learning blueprint；

&#x20;  - interaction specification；

&#x20;  - quiz/hint policy；

&#x20;  - style/layout spec。  

&#x20;  最终由 deterministic HTML runtime 编译成网页。



3\. \*\*Validator + Repair Loop\*\*  

&#x20;  不只验证 trace，还验证：

&#x20;  - 算法输出正确；

&#x20;  - 每一步状态和 reference solver 一致；

&#x20;  - quiz answer oracle 正确；

&#x20;  - hint 是否 grounded in trace；

&#x20;  - UI 是否能运行；

&#x20;  - DOM 是否重叠；

&#x20;  - 所有交互路径是否可达。



4\. \*\*AlgoLearnEnv-Bench\*\*  

&#x20;  新建一个 benchmark，衡量 LLM 生成“可交互学习环境”的成功率，而不是只衡量视频是否能渲染。



这四点加起来就不是 demo，而是一个完整研究问题。



\---



\## 3. 数据集应该怎么做



不要只靠 5 个 HTML demo。那只能做展示，不能撑论文。建议做三层数据。



\### A. Core benchmark：200–500 个算法学习环境任务



每个 task 不只是 problem description，而是一个 bundle：



```json

{

&#x20; "algorithm\_id": "dijkstra\_shortest\_path",

&#x20; "family": "graph",

&#x20; "difficulty": "medium",

&#x20; "learning\_objectives": \[

&#x20;   "understand relaxation",

&#x20;   "understand priority queue invariant"

&#x20; ],

&#x20; "input\_generator": "...",

&#x20; "reference\_solver": "...",

&#x20; "trace\_oracle": "...",

&#x20; "required\_views": \["graph", "distance\_table", "priority\_queue"],

&#x20; "interaction\_tasks": \[

&#x20;   "predict\_next\_node",

&#x20;   "choose\_relaxed\_edge",

&#x20;   "explain\_invariant",

&#x20;   "modify\_input\_and\_rerun"

&#x20; ],

&#x20; "assessment\_rubric": "..."

}

```



推荐覆盖：



| Family | Examples |

|---|---|

| Array / Two pointers | Two Sum, Merge Intervals, Sliding Window |

| Stack | Daily Temperatures, Valid Parentheses, Monotonic Stack |

| Graph | BFS, DFS, Dijkstra, Topological Sort, Course Schedule |

| DP | Unique Paths, Knapsack, Edit Distance |

| Tree | Traversal, BST insert/delete, LCA |

| Hash table | collision, frequency map, prefix sum |

| Sorting/Search | merge sort, quicksort, binary search |



你们现有 HTML 里的 Two Sum、Merge Intervals、Dijkstra、Daily Temperatures、Unique Paths 正好可以当 paper figures，但不能当主要实验。



\### B. 可公开版本：尽量用开源/自建算法任务



LeetCode-derived benchmark 可以内部评测，但公开 release 会有版权/条款风险。更稳的公开来源可以用：



\- \*\*TheAlgorithms/Python\*\*：它是面向教育的 Python 算法实现库，并标明 MIT license，适合作为 reference implementation 来源之一。(\[github.com](https://github.com/thealgorithms/python?utm\_source=openai))

\- \*\*OpenDSA\*\*：可以作为课程 taxonomy 和学习目标来源；它本身就是 Data Structures and Algorithms modules collection。(\[opendsa.org](https://opendsa.org/OpenDSA/Books/Everything/html/genindex.html?utm\_source=openai))

\- \*\*Python Tutor\*\* 可作为用户熟悉的 program visualization baseline；其官方页面说明支持多语言代码执行可视化，并允许用户前后步进查看运行状态。(\[pythontutor.com](https://pythontutor.com/visualize.html/mode?utm\_source=openai))



我的建议是：  

\*\*公开 benchmark 用 synthetic/open-source tasks；LeetCode 只做 private stress test。\*\*



\### C. Interaction benchmark：每题至少 3 个交互任务



这点非常关键。你们不是只生成动画，而是生成学习环境，所以 benchmark 必须有 interaction oracle。



比如 Dijkstra：



1\. 当前节点是 A，问学生下一步应该 pop 哪个节点；

2\. 让学生点击应该 relax 的边；

3\. 给一个错误 distance table，让学生指出哪一项错了；

4\. 改一条边权，重新生成 trace；

5\. 问为什么已经 finalized 的节点不会再变小。



这些交互必须能被自动判分。



\---



\## 4. 系统架构应该怎么升级



我建议把你们现在的 Creative Shell 改成下面这个 pipeline：



```text

Problem Spec

&#x20;  ↓

Learning Blueprint Generator

&#x20;  ↓

Reference Solver + Tracker Generator

&#x20;  ↓

VTA Trace Validator

&#x20;  ↓

Interaction Spec Generator

&#x20;  ↓

Interaction Oracle Validator

&#x20;  ↓

HTML/React Runtime Compiler

&#x20;  ↓

Browser-level Validator

&#x20;  ↓

Playable Learning Environment

```



每一层都要有 verifier。



| Module | 作用 | LLM 做什么 | Deterministic system 做什么 |

|---|---|---|---|

| Tracker | 执行算法 | 生成 Python tracker | 跑 hidden tests，验证 trace |

| Learning Blueprint | 教学设计 | 生成目标、步骤、问题 | 检查字段、难度、覆盖率 |

| Interaction Spec | 交互任务 | 生成 quiz、hint、actions | 用 oracle 判定正确性 |

| HTML Runtime | 网页环境 | 只选模板/参数 | 编译为页面，跑 Playwright |

| Tutor | 解释/提示 | 生成 grounded hint | 限制只能引用 trace/pseudocode |



这里最重要的是：\*\*不要让 LLM 直接自由写大段 HTML/JS\*\*。  

自由写网页会回到你们 ALGOGEN 反对的 end-to-end generation，失败模式会变成：



\- button 不工作；

\- state 不同步；

\- quiz 答案错；

\- DOM 重叠；

\- 改输入后 trace 不更新；

\- hint 胡说。



所以应该让 LLM 输出结构化 JSON，HTML runtime deterministic 编译。



\---



\## 5. 评估该怎么设计



建议至少回答五个 research questions。



\### RQ1：生成成功率



比较：



\- Ours: VTA + Interaction IR + HTML runtime；

\- Direct HTML：LLM 直接写一个完整 HTML；

\- Direct React：LLM 直接写 React component；

\- Video-only ALGOGEN；

\- Python Tutor/OpenDSA-style baseline，作为 learning interface reference。



指标：



\- executable environment success；

\- trace validation success；

\- browser test success；

\- interaction oracle pass rate；

\- average repair rounds；

\- generation time/tokens。



\### RQ2：算法正确性



不要只让 LLM judge。最好加 reference solver。



指标：



\- final output accuracy；

\- per-step state equivalence；

\- invariant violation count；

\- hidden input generalization；

\- long-trace robustness。



\### RQ3：交互正确性



这是新 paper 的关键。



指标：



\- quiz answer correctness；

\- action reachability；

\- invalid action handling；

\- hint groundedness；

\- counterfactual rerun correctness；

\- no dead-end UI states。



可以用 Playwright 自动测：



```text

load page → click next → click previous → change input → run →

answer quiz → request hint → export trace

```



\### RQ4：UI/可用性



不要只看 AES。HTML learning environment 应该测：



\- element overlap；

\- text readability；

\- viewport responsiveness；

\- keyboard accessibility；

\- step latency；

\- visual consistency；

\- student task completion rate。



\### RQ5：学习效果



如果投 CHI / AIED / SIGCSE，这个必须做。



设计：



\- 60–120 名 CS1/CS2 学生；

\- 三组对比：

&#x20; 1. static explanation / textbook；

&#x20; 2. video-only ALGOGEN；

&#x20; 3. interactive AlgoTutorGen；

\- pre-test / post-test / transfer test；

\- 记录 time-on-task、confidence、NASA-TLX、SUS；

\- 分析学生是否真的理解 invariant、边界情况、复杂度。



如果投 AAAI，可以把 human study 放小一点，主打 technical benchmark；如果投 CHI/AIED，human study 要做扎实。



\---



\## 6. 投哪里：我建议分三条路线



今天是 \*\*2026-06-29\*\*。几个关键 deadline 要非常现实地看。



\### 路线 A：AAAI-27，技术主线，风险高但可以冲



AAAI-27 main track 的 abstract deadline 是 \*\*2026-07-21\*\*，full paper deadline 是 \*\*2026-07-28\*\*，supplementary/code deadline 是 \*\*2026-07-31\*\*；会议是 \*\*2027-02-16 至 2027-02-23\*\*。(\[aaai.org](https://aaai.org/conference/aaai/aaai-27/))



所以如果你们现在只有若干 HTML demo，AAAI-27 很赶。除非：



\- benchmark schema 已经基本定；

\- 100+ tasks 可以在两周内跑起来；

\- baselines 已经有；

\- paper 框架已经能写。



AAAI 版本建议主打：



> \*\*verifiable LLM generation + benchmark + automatic validation + repair\*\*



不要主打“教学效果”，因为一个月内做不完严格 user study。



\### 路线 B：CHI 2027，更适合“交互学习环境”



CHI 2027 full paper deadline 是 \*\*2026-09-10\*\*，比 AAAI 多大约两个月；CHI 也有 Interactive Demos，submission due 是 \*\*2027-01-21\*\*。(\[chi2027.acm.org](https://chi2027.acm.org/papers/)) (\[chi2027.acm.org](https://chi2027.acm.org/))



如果你们愿意做用户研究，CHI 反而可能更适合：



> LLM 生成的可验证交互式算法学习环境，如何帮助学生理解算法？



CHI 需要：



\- 系统贡献；

\- 设计 rationale；

\- 用户研究；

\- learning/user experience evidence。



\### 路线 C：AIED / SIGCSE，教育主线，更稳



AIED 的定位非常贴近“AI-enabled systems as trusted teammates for learners/educators”，这和你们的“可靠交互式算法学习环境”很契合。(\[aied-conference.org](https://www.aied-conference.org/2026/call-for-paper))



SIGCSE TS 2027 是计算机教育旗舰会议，但它的 paper abstract due 是 \*\*2026-06-26\*\*，full paper due 是 \*\*2026-07-03\*\*；如果你们没有提前交 abstract，今年 paper 基本赶不上，不过 demo/poster round 是 \*\*2026-09-30\*\*。(\[2027.sigcse-ts.acm.org](https://2027.sigcse-ts.acm.org/)) (\[2027.sigcse-ts.acm.org](https://2027.sigcse-ts.acm.org/track/sigcse-ts-2027-Papers-1))



SIGCSE/AIED 更看重：



\- 是否真的适合教学；

\- 学生是否学得更好；

\- 教师是否能采用；

\- 系统是否能融入课堂。



\### 其他路线



\- \*\*ICSE/FSE\*\*：如果你们强调“LLM 生成可验证 Web app / educational software”，可以走软件工程。ICSE 2027 abstract 是 \*\*2026-06-23\*\*，submission 是 \*\*2026-06-30\*\*，今年基本来不及；但 ICSE 明确有 AI for SE、trustworthy AI for SE、LLM automation 等方向。(\[conf.researchr.org](https://conf.researchr.org/track/icse-2027/icse-2027-research-track))

\- \*\*UIST\*\*：如果你们强调新型交互技术和 authoring tool，UIST 很合适；但 UIST 2026 paper deadline 已过，demo/poster deadline 是 \*\*2026-07-10\*\*。(\[uist.acm.org](https://uist.acm.org/2026/))

\- \*\*IEEE VIS\*\*：如果强调 visualization representation / interaction，VIS 也可考虑；VIS 2026 full paper deadline 是 \*\*2026-03-31\*\*，已过，下一轮可以规划。(\[ieeevis.org](https://ieeevis.org/year/2026/info/call-participation/call-for-participation/))



\---



\## 7. 我建议你们的实际执行计划



\### 如果冲 AAAI-27



只做技术 paper，不做大用户研究。



\*\*到 2026-07-05：\*\*



\- 冻结 paper narrative；

\- 定义 IELA-JSON / Interaction IR；

\- 选 100 个 task；

\- 实现 HTML runtime；

\- 实现 Playwright validator。



\*\*到 2026-07-12：\*\*



\- 跑 200 task；

\- 至少 3 个模型；

\- 2 个 direct-generation baseline；

\- 出第一版 tables。



\*\*到 2026-07-18：\*\*



\- 完成 ablation：

&#x20; - no VTA；

&#x20; - no interaction validator；

&#x20; - no repair；

&#x20; - direct HTML；

&#x20; - direct React。

\- 完成 5 个 qualitative figures。



\*\*2026-07-21：\*\*



\- 提交 AAAI abstract。



\*\*2026-07-28：\*\*



\- full paper。



我会说实话：如果你们现在还没有自动化 benchmark 和 validator，AAAI-27 很危险；但如果你们已经有 pipeline，值得冲。



\### 如果走 CHI 2027



这是我认为更稳、更完整的路线。



\*\*7 月：\*\*



\- 系统和 benchmark 成型；

\- 200–300 个 tasks；

\- 10 个高质量 public demos。



\*\*8 月：\*\*



\- 做用户 study；

\- 找 CS1/CS2 学生；

\- pre/post/transfer test。



\*\*9 月初：\*\*



\- 完成统计分析；

\- paper 定稿；

\- 9 月 10 日提交。



\### 如果走毕业保底



可以拆出一个更窄的 paper：



> \*\*Validator-Guided JSON Repair for LLM-Generated Algorithm Visualization Traces\*\*



这个就是你截图里学生说的 “DLM JSON repair 保毕业” 那条线。  

它的好处是：



\- scope 小；

\- 实验好做；

\- 可以构造 corrupted VTA/IELA JSON；

\- 比较 LLM direct repair、schema-only repair、validator-guided repair；

\- 指标明确：repair success、semantic preservation、rounds、cost。



这个适合当保底论文；大 paper 再冲算法可视化/交互学习环境。



\---



\## 8. Demo 应该怎么改才像“学习环境”



你现在 HTML 里有：



\- 验证输出；

\- 当前解法；

\- 代码/伪代码；

\- 解法对比；

\- 播放/上一步/下一步；

\- Debug Drawer；

\- raw validation report；

\- raw state JSON；

\- artifact JSON。



这些对研究者很好，但对学生不够。建议改成两个模式：



\### Learner Mode



学生看到：



1\. \*\*我要学什么\*\*

2\. \*\*当前算法在做什么\*\*

3\. \*\*为什么这一步正确\*\*

4\. \*\*请预测下一步\*\*

5\. \*\*我答错了，给我 hint\*\*

6\. \*\*换一个输入试试\*\*

7\. \*\*学完测试\*\*



\### Developer Mode



研究者/teacher 看到：



1\. raw trace；

2\. validation report；

3\. artifact JSON；

4\. repair log；

5\. browser test log；

6\. oracle comparison。



你们现在的 Debug Drawer 应该保留，但不要放在主学习界面里。



\---



\## 9. 最终建议



我会这样定战略：



> \*\*主线：AlgoTutorGen / Trace-to-Tutor\*\*  

> 用 LLM 可靠生成可执行、可验证、可交互的算法学习环境。



投稿选择：



1\. \*\*想冲 AAAI-27\*\*：主打 technical reliability + benchmark，必须马上开始跑大规模实验。

2\. \*\*想做完整好论文\*\*：投 CHI 2027 或 AIED，补用户研究。

3\. \*\*想保毕业\*\*：拆出 JSON repair / validator-guided repair 小论文。

4\. \*\*想长期做成系统方向\*\*：后面可以扩展到 ICSE/FSE，讲 LLM-generated verifiable web apps。



一句话：  

\*\*demo 是门面，benchmark + validator + interaction oracle 才是论文。\*\*



\---

Learn more:

1\. \[GitHub - TheAlgorithms/Python: All Algorithms implemented in Python · GitHub](https://github.com/thealgorithms/python?utm\_source=openai)

2\. \[Index — OpenDSA Data Structures and Algorithms Modules Collection](https://opendsa.org/OpenDSA/Books/Everything/html/genindex.html?utm\_source=openai)

3\. \[Python Tutor code visualizer: Visualize code in Python, JavaScript, C, C++, and Java](https://pythontutor.com/visualize.html/mode?utm\_source=openai)

4\. \[AAAI-27 - AAAI](https://aaai.org/conference/aaai/aaai-27/)

5\. \[Papers - ACM CHI 2027](https://chi2027.acm.org/papers/)

6\. \[Welcome to CHI 2027 - ACM CHI 2027](https://chi2027.acm.org/)

7\. \[General Call for Paper · Call for Paper · AIED 2026](https://www.aied-conference.org/2026/call-for-paper)

8\. \[SIGCSE TS 2027](https://2027.sigcse-ts.acm.org/)

9\. \[SIGCSE TS 2027 - Papers - SIGCSE TS 2027](https://2027.sigcse-ts.acm.org/track/sigcse-ts-2027-Papers-1)

10\. \[ICSE 2027 - Research Track - ICSE 2027](https://conf.researchr.org/track/icse-2027/icse-2027-research-track)

11\. \[UIST 2026 - Home](https://uist.acm.org/2026/)

12\. \[Papers - Call For Participation | IEEE VIS 2026](https://ieeevis.org/year/2026/info/call-participation/call-for-participation/)

