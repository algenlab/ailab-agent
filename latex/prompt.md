你是一名专注于程序合成、软件工程、形式化方法、LLM Agent、教育技术和交互式系统的顶级学术论文作者。请基于我提供的项目报告，撰写一篇完整、严谨、可直接使用 `pdflatex` 编译的英文研究论文。

论文暂定题目为：

```text
AlgoTutorGen: Contract-Guided Compositional Synthesis of Verifiable Interactive Algorithm Tutors
```

也可以提出一个更好的标题，但标题必须突出以下三个关键词中的至少两个：

```text
contract-guided
compositional synthesis
verifiable interactive algorithm tutors
semantic factorization
```

最终输出必须是一篇完整论文，而不是提纲、写作建议或项目报告。

# 1. 输入材料和事实优先级

我会向你提供以下项目材料：

```text
docs/EXPERIMENT_RESULTS.md
latex/evidence-ledger.md
其他实验报告、结果 JSON、图表数据或相关工作笔记
```

事实采用以下优先级：

1. `docs/EXPERIMENT_RESULTS.md` 中的统一结果；
2. `latex/evidence-ledger.md` 中已审计的论文数字；
3. 带有明确实验路径的机器可读结果文件；
4. 其他设计、计划和历史记录只用于解释背景。

若不同报告中的数字冲突，使用更新时间较新的报告，并在 LaTeX 注释中指出冲突，但不要自行猜测。

禁止：

* 编造实验结果；
* 编造用户实验、专家标注或人工标签；
* 编造统计显著性；
* 编造引用、作者、年份、DOI 或会议；
* 把尚未完成的人工实验写成已完成；
* 把测试证据写成形式化证明；
* 把条件定理写成当前系统已经满足的无条件性质。

人工 evaluator calibration、trace 双人标注、专家实验和学生实验目前仍是 `pending_human_labels`，必须明确写为未来工作或尚未完成的外部校准。

# 2. 输出格式

请输出两个完整文件：

```text
main.tex
references.bib
```

使用以下 LaTeX 设置：

```latex
\documentclass[sigconf,review,anonymous]{acmart}
```

论文必须使用：

```text
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

成功编译。

具体要求：

1. 使用 `BibTeX`，不要使用 `biblatex` 或 `biber`。
2. 使用：

   ```latex
   \bibliographystyle{ACM-Reference-Format}
   \bibliography{references}
   ```
3. 不使用 `fontspec`、`unicode-math`、XeLaTeX 或 LuaLaTeX 专属命令。
4. 不使用 `minted`，因为它要求 `--shell-escape`；代码片段使用 `listings`、`verbatim` 或普通等宽字体。
5. 不在 `.tex` 中直接使用 Unicode 数学符号。使用：

   ```latex
   \alpha,\rightarrow,\leq,\times,\%
   ```

   等标准 LaTeX 命令。
6. 使用 ASCII 引号和连字符，避免从网页复制不可见 Unicode 字符。
7. 允许使用以下常见包：

   ```latex
   amsmath
   amssymb
   amsthm
   mathtools
   booktabs
   multirow
   graphicx
   xcolor
   tikz
   pgfplots
   algorithm
   algpseudocode
   listings
   hyperref
   cleveref
   microtype
   balance
   ```
8. 图表优先使用 TikZ、PGFPlots 或 LaTeX 表格直接生成，不依赖不存在的外部图片。
9. 所有表格必须适合双栏版式，必要时使用 `table*`。
10. 不输出 Markdown 论文正文。最终论文必须全部位于 LaTeX 代码中。
11. 不省略任何章节，不使用诸如：

    ```text
    [TODO]
    ...
    omitted for brevity
    ```

    代替正文。
12. 未知作者和单位使用匿名占位，不得编造作者身份。

在 `main.tex` 第一行附近加入编译说明注释：

```latex
% Compile with:
% pdflatex main.tex
% bibtex main
% pdflatex main.tex
% pdflatex main.tex
```

# 3. 论文定位

这篇论文的核心不是：

```text
我们搭建了一套包含很多模块的算法教学网页生成系统。
```

而是：

```text
交互式算法教学页面生成是一个多约束组合合成问题。
端到端 HTML 生成必须在一个自由输出中同时满足算法事实、
执行轨迹、视觉状态、浏览器行为、教学反馈和状态非干扰等异构义务。
这些约束在单体输出空间中发生 constraint entanglement。
AlgoTutorGen 通过可执行语义契约将这一问题分解为可检查、
可组合且部分可修复的中间表示链。
```

论文应该明确区分三种解耦：

1. **Semantic decoupling**
   将算法事实、执行轨迹、视觉状态和教学状态分开表示。

2. **Verification decoupling**
   在不同边界使用 solver、trace、scene、interaction 和 release contracts 分别检查。

3. **Computational recovery decoupling**
   失败后仅重新执行失败阶段。

当前系统已经较好实现前两种，但尚未真正实现完整的第三种。当前 Local Resume 只保留 solution spec，repair 后仍会重新 materialize 并重新调用 teaching。因此论文不能声称当前实现已经获得完整的 stage-local recovery efficiency。

论文中心论点应该是：

```text
Contract-guided semantic factorization converts an opaque,
monolithic generation task into a sequence of explicit refinement
obligations. This enables compositional semantic preservation,
contract discrimination, and pedagogical noninterference.
```

# 4. 推荐的论文结构

论文正文建议控制在约 10--12 页双栏正文，不含参考文献和附录。使用以下结构。

## 4.1 Abstract

写一个约 180--230 词的英文摘要，必须包含：

1. 问题背景；
2. 端到端 HTML 的 constraint entanglement；
3. AlgoTutorGen 的 contract-guided semantic factorization；
4. 两个主要理论性质：

   * compositional semantic preservation；
   * pedagogical noninterference；
5. 最重要实验结果；
6. 诚实说明 Local Resume 没有优于 Global Restart；
7. 不声称学习成绩提高。

摘要中优先使用以下结果：

```text
200 tasks, 23 algorithm families
AlgoTutorGen 198/200 Machine OK
Direct HTML 98/200 Machine OK
294/294 artifacts and 55,108/55,108 frames preserve semantic projections
2,198/2,198 semantic violations rejected
392/392 semantics-preserving transformations accepted
240 pages, 24,000 action sequences, 1,561,298 actions, zero noninterference violations
```

摘要不要塞入所有模型、视觉分数和长轨迹数字。

## 4.2 Introduction

Introduction 应按以下故事顺序组织。

### Paragraph 1: Observation

现代 LLM 可以生成外观完整、最终答案正确的算法教学网页，但答案正确不代表：

* 执行过程正确；
* 页面可以加载；
* 交互控件可以到达；
* 正确和错误回答得到不同反馈；
* hint、show answer 和 learning log 正常工作；
* 教学操作不会修改算法事实。

使用主实验中的关键观察：

```text
AlgoTutorGen 和 Direct HTML 都达到 200/200 visible answer match，
但完整 Machine OK 分别为 198/200 和 98/200。
```

### Paragraph 2: Diagnosis

提出并定义：

```text
Constraint Entanglement
```

解释单体 HTML 生成把以下义务纠缠在一次开放式生成中：

[
C_{\mathrm{answer}},
C_{\mathrm{trace}},
C_{\mathrm{scene}},
C_{\mathrm{runtime}},
C_{\mathrm{feedback}},
C_{\mathrm{noninterference}}.
]

修复某个部分可能破坏另一个已经正确的部分。

### Paragraph 3: Insight and method

介绍：

```text
Contract-Guided Semantic Factorization
```

系统链路：

```text
Problem and input
  -> executable solver/specification
  -> SemanticTrace
  -> validated SceneGraph
  -> deterministic Web Runtime
  -> pedagogical overlay
  -> browser-level release audit
```

强调每个中间表示承担清晰的语义职责，并通过契约连接。

### Paragraph 4: Theory

概括：

* compositional semantic preservation；
* pedagogical noninterference；
* nested contract survival；
* conditional stage-local recovery theorem。

必须明确：

```text
The local-recovery theorem is conditional.
The current implementation does not fully satisfy its checkpointability assumption.
```

### Paragraph 5: Results

概括主实验、理论定向实验、跨模型和 held-out 结果。

### Contributions

贡献建议写成四条：

1. 将交互式算法教学网页生成形式化为多约束组合 artifact synthesis 问题，并识别 constraint entanglement。
2. 提出 contract-guided semantic factorization 框架。
3. 给出 compositional semantic preservation 和 pedagogical noninterference 的形式化性质，并分析 stage-local recovery 的条件优势和实现边界。
4. 在 200 个任务、23 个算法族、多个模型、held-out 任务、语义变异和 156 万次浏览器动作上进行系统评价。

不要把“使用 DeepSeek”或“生成网页”本身列为贡献。

## 4.3 Problem Formulation

定义输入：

[
x=(q,i,e,c),
]

其中：

* (q)：算法问题；
* (i)：具体输入；
* (e)：可选 expected/oracle；
* (c)：可选参考代码或策略。

最终 artifact 定义为：

[
W=(S,T,G,P,R),
]

其中：

* (S)：solver 或 executable solution specification；
* (T)：SemanticTrace；
* (G)：SceneGraph；
* (P)：pedagogical overlay；
* (R)：Web Runtime。

定义全局正确性义务：

[
\Phi(W,x)=
\Phi_{\mathrm{result}}
\land
\Phi_{\mathrm{trace}}
\land
\Phi_{\mathrm{scene}}
\land
\Phi_{\mathrm{runtime}}
\land
\Phi_{\mathrm{feedback}}
\land
\Phi_{\mathrm{noninterference}}.
]

解释 Direct HTML 在自由空间 (\Omega_{\mathrm{HTML}}) 中一次性生成 (W)，而 AlgoTutorGen 通过中间空间和契约进行分阶段构造。

不要声称仅仅写成笛卡尔积就自动减少搜索空间。必须明确：

```text
The benefit does not follow from modularization alone.
It follows from explicit contracts, early rejection,
semantic reuse, and deterministic downstream compilation.
```

## 4.4 System Design

详细描述：

1. executable solver/spec generation；
2. TraceSession DSL；
3. sandboxed execution；
4. result、trace、process 和 scene validation；
5. deterministic SceneGraph compiler；
6. fixed Web Runtime；
7. teaching enrichment；
8. browser release audit；
9. repair/retry boundary。

给出一张完整系统图。

系统图要体现：

```text
generated/open-ended stages
deterministic stages
contract checks
immutable algorithmic state
mutable pedagogical state
```

可以使用 TikZ，并用不同线型而不是只依赖颜色区分。

必须诚实说明当前真实恢复边界：

```text
Local Resume retains the current solution specification,
but re-runs materialization and teaching after repair.
It is not a fully checkpointed five-stage recovery system.
```

## 4.5 Theoretical Analysis

这是论文的核心章节之一。数学内容必须严谨但不要假装达到机器辅助形式化证明。

### Definition 1: Canonical algorithmic projection

定义统一算法状态空间 (\mathcal{A})。

定义投影：

[
\alpha_T:T_t\rightarrow\mathcal{A},
\quad
\alpha_G:G_t\rightarrow\mathcal{A},
\quad
\alpha_R:R_t\rightarrow\mathcal{A}.
]

投影内容可包括：

```text
object identifiers
values
marks
pointers
edges
stack/queue contents
current step
final answer
```

布局坐标、CSS 和教学文本不属于算法事实投影。

### Theorem 1: Compositional Semantic Preservation

使用类似以下表述，但应根据实际实现精确润色：

```latex
\begin{theorem}[Compositional Semantic Preservation]
For an input $x$, let $S(x)$ be a verified solver result,
$T=(T_0,\ldots,T_n)$ a semantic trace,
$G=(G_0,\ldots,G_n)$ its compiled scene sequence, and
$R(G)$ the rendered runtime execution.
If
\[
\operatorname{Final}(T)=S(x),
\]
\[
\alpha_T(T_t)=\alpha_G(G_t)
\quad\text{for all }t,
\]
and
\[
\alpha_G(G_t)=\alpha_R(R_t)
\quad\text{for all reachable }t,
\]
then
\[
\alpha_T(T_t)=\alpha_R(R_t)
\quad\text{for all reachable }t,
\]
and the rendered final answer equals $S(x)$.
If additionally $S(x)=\operatorname{Oracle}(x)$, the rendered
final answer equals the oracle result.
\]
\end{theorem}
```

证明使用关系或等式传递性。

必须明确：

* 这是关于层间语义保持的定理；
* 它不自动证明初始 SemanticTrace 对真实算法的每一步都正确；
* source trace correctness 仍需 oracle、process validator 或人工审计。

### Theorem 2: Pedagogical Noninterference

状态定义为：

[
\sigma=(a,p),
]

其中 (a) 是算法事实状态，(p) 是教学状态。

区分：

1. pure pedagogical actions；
2. navigation actions。

纯教学动作包括：

```text
submit_correct
submit_wrong
hint
show_answer
clear_learning_log
```

导航动作包括：

```text
next
prev
timeline
reset
select_variant
```

推荐定理：

```latex
\begin{theorem}[Pedagogical Noninterference]
Suppose every pure pedagogical action $u$ satisfies
\[
\delta_u(a,p)=(a,p')
\]
for some pedagogical state $p'$. Then, for every finite
sequence of pure pedagogical actions $u_1,\ldots,u_m$,
\[
\pi_A(\delta_{u_m}\circ\cdots\circ\delta_{u_1}(a,p))=a.
\]
Moreover, if each navigation action only selects a state
from the verified trajectory $\mathcal{V}(T)$, then after
any mixed interaction sequence the algorithmic state remains
an element of $\mathcal{V}(T)$.
\]
\end{theorem}
```

第一部分用动作序列长度归纳证明。第二部分用不变式归纳证明。

说明该定理描述抽象 Runtime；property-based browser stress test 用于检查具体实现是否违反定理假设。

### Proposition 1: Nested Contract Survival

定义嵌套契约：

[
C_1,\ldots,C_m.
]

给出：

[
P(C_1\land\cdots\land C_m)
==========================

\prod_{i=1}^{m}
P(C_i\mid C_1,\ldots,C_{i-1}).
]

明确说明这是概率链式法则，而不是本文新发现。

本文的新经验发现是：

```text
Monolithic HTML generation loses substantial conditional survival
at runtime, interaction, and feedback boundaries, whereas
contract-guided generation keeps downstream conditional survival
close to one after semantic validation.
```

### Conditional Theorem 3: Ideal Stage-Local Recovery

可以给出条件理论：

[
E[C_{\mathrm{local}}]
=====================

\sum_{i=1}^{k}\frac{c_i}{p_i},
]

[
E[C_{\mathrm{global}}]
======================

\sum_{i=1}^{k}
\frac{c_i}{\prod_{j=i}^{k}p_j}.
]

在以下条件成立时：

* validator 精确定位失败阶段；
* 已验证阶段可以缓存；
* 失败阶段可以独立重试；
* 重试不会使已验证阶段失效；
* 已验证下游工作不被重新执行；

则：

[
E[C_{\mathrm{local}}]\le E[C_{\mathrm{global}}].
]

必须将这一结果称为：

```text
conditional characterization
```

而不是当前系统已经获得的性能保证。

紧接着说明：

```text
The present implementation violates the full checkpointability
assumption because repairing the solution specification triggers
materialization and teaching again.
```

因此该定理不是论文的首要理论贡献，也不能用于声称当前 Local Resume 更省。

## 4.6 Experimental Setup

明确说明：

* 200 tasks；
* 23 algorithm families；
* full benchmark 646 samples；
* main comparison 使用每题 sample index 0；
* DeepSeek-V4-Pro 为原主模型；
* 其他跨模型实验；
* Direct HTML 可以看到 expected；
* Direct 被明确要求生成完整教学功能；
* 两种方法允许 repair；
* Machine OK 的九项浏览器指标；
* paired McNemar、bootstrap CI、Wilcoxon 和 Holm correction；
* external baselines；
* theory-aligned experiments。

Machine OK 定义：

```text
page load
visible answer match
interaction reachable
correct feedback
wrong feedback
hint
show answer
learning log
protected-answer stability
```

强调它评价的是可执行行为完整性，不是学生学习效果。

## 4.7 Main Results

主文优先呈现以下结果。

### Main reliability

| Method                   | Machine OK |
| ------------------------ | ---------: |
| AlgoTutorGen             |    198/200 |
| Direct HTML              |     98/200 |
| WebGen-Agent             |     45/200 |
| Direct + HTMLCure strict |     40/200 |

AlgoTutorGen vs Direct：

```text
+50.0 percentage points
95% paired bootstrap CI [43.0, 57.0]
exact McNemar p = 4.06e-29
```

同时说明 AlgoTutorGen 与 Direct 都达到 200/200 visible answer match，因此差距主要来自交互行为，而不是最终答案。

### Nested contract survival

使用主图展示：

```text
AlgoTutorGen:
100 -> 100 -> 100 -> 99 -> 99 -> 99

Direct:
100 -> 94 -> 74.5 -> 54 -> 49 -> 49
```

对应：

* C1 answer；
* C2 load；
* C3 interaction；
* C4 bidirectional feedback；
* C5 teaching support；
* C6 noninterference。

同时展示或在附录展示跨 Flash、GLM、Kimi 的相同趋势。

### Semantic preservation

报告：

```text
294/294 artifacts passed
55,108/55,108 frames passed
```

细分：

```text
main 200: 9,421/9,421 frames
held-out 40: 4,568/4,568 frames
long-trace 54: 41,119/41,119 frames
```

20 个样本重复编译和渲染 10 次均得到唯一 projection/render hash。

准确表述为：

```text
executable evidence of representation-level semantic preservation
```

不要写成完整形式化认证。

### Semantic mutation

报告：

```text
2,198/2,198 tested semantic violations rejected
392/392 tested semantics-preserving transformations accepted
```

将这一结果称为：

```text
contract discrimination
```

不要称为对任意错误 100% sound and complete。

### Noninterference

报告：

```text
240 pages
24,000 random sequences
1,561,298 actions
0 violations
```

说明：

* 纯教学动作没有改变算法 state、step 或 artifact hash；
* 1,125,439 次导航类动作均落入目标 verified frame；
* 合法 overlay 保持算法状态；
* 非法算法字段被 sanitizer 消除或被契约拒绝。

准确表述：

```text
No counterexample was found in the stress-test suite.
```

不要写：

```text
The browser implementation is formally proven correct.
```

## 4.8 Negative Result: Local Resume vs Global Restart

必须把该实验作为诚实的重要结果，不得隐藏或歪曲。

结果：

| Model             | Local | Global |    McNemar |
| ----------------- | ----: | -----: | ---------: |
| DeepSeek-V4-Flash | 38/50 |  42/50 | (p=0.4545) |
| GLM-5.2           | 42/50 |  43/50 |    (p=1.0) |

成本：

```text
Flash:
Local 71,369 tokens/success
Global 62,256 tokens/success

GLM:
Local 92,385 tokens/success
Global 96,186 tokens/success
```

分析必须明确：

1. 当前实验没有显示 Local 的显著优势；
2. Flash 上 Global 数值更好；
3. GLM 上 Local token 和 time 略低，但成功率略低且不显著；
4. Local 降低了 solution-spec generation/repair 成本；
5. repair 后重新调用 teaching，抵消了部分或全部节省；
6. 当前系统只实现 specification-level repair；
7. 当前系统没有实现完整 stage-level checkpoint recovery。

建议使用以下核心表述：

```text
The negative result does not contradict the conditional recovery
theorem. Instead, it reveals that AlgoTutorGen currently achieves
semantic and verification decoupling, but not full computational
recovery decoupling.
```

不能把非显著 (p) 值解释为两种策略严格等价。

## 4.9 Additional Evaluation

根据篇幅将下列结果放正文精简表或附录。

### Cross-model primary fixed-budget

| Model             | AlgoTutorGen |  Direct |
| ----------------- | -----------: | ------: |
| DeepSeek-V4-Flash |      196/200 | 118/200 |
| GLM-5.2           |      170/200 |  35/200 |
| Kimi-K2.5         |      160/200 |  87/200 |

说明架构优势跨模型保留，但严格 gate 导致不同模型的绝对生成成功率不同。

### Held-out tasks

```text
40 new cases, 15 families
AlgoTutorGen 39/40
Direct 18/40
difference +52.5 pp
McNemar p = 9.54e-7
```

理论语义保持实验通过目标补跑获得第 40 个 artifact。必须解释主 held-out generation 仍是 39/40，不能把补跑后的 40/40 冒充首次生成结果。

### Non-degenerate ablations

```text
Direct-to-SceneGraph:
Full 49/50
Ablation 1/50

VerifiedTrace-to-LLM-HTML:
Full 49/50
Ablation 0/50
Visible answer 50/50
Interaction reachable 0/50
```

解释：

* 固定 Runtime 本身不足以替代 executable trace 和 validation；
* 正确 trace 本身也不足以保证自由 HTML 的交互实现可靠。

### Direct Browser Repair

使用预算曲线说明增加自由 HTML 改写轮数没有提高可靠性：

```text
1 call: 106/200
2 calls: 10/200
3 calls: 15/200
5 calls: 6/200
```

五轮平均 87.2k tokens，高于 Stage1 的 76.8k。结论应是：

```text
More generation budget alone does not guarantee reliability.
```

不要泛化为所有 browser repair 方法都会失败。

### Long-trace scalability

报告限制：

```text
large average:
1,636.7 frames
160.4 MB HTML
8,354 ms load
101.3 ms step latency
185.6 MB JS heap
```

极端页面：

```text
581 MB
1.08 GB
more than 60 seconds to load
```

解释当前 full-frame materialization 具有较高存储开销，未来需要：

* event-delta representation；
* frame virtualization；
* lazy loading；
* state compression。

这是一项重要限制，不要掩盖。

### Stage2 visual enhancement

将 Stage2 降为次要贡献或附录结果。

准确说明：

* overall 4.611 vs 4.596；
* 只有 instructional visual design 经 Holm 修正后显著更高；
* Direct 在 state readability 和 process clarity 上略高；
* 不声称视觉全面领先。

## 4.10 Related Work

相关工作至少分为以下类别。

### LLM-generated webpages and browser agents

讨论：

* direct HTML/code generation；
* iterative webpage generation agents；
* WebGen-Agent；
* HTMLCure；
* 教育网页生成系统；
* EduVisAgent；
* 其他真正输出交互式页面的工作。

必须使用最新、可核验的原始论文或官方仓库。

### Algorithm visualization and tutoring systems

讨论：

* Naps learner engagement taxonomy；
* TRAKLA2；
* Python Tutor；
* Algorithm Visualizer；
* 传统模板式算法可视化；
* 自动评估和交互练习。

强调传统系统通常依赖人工实现或受限模板，而本文研究自动生成任意 benchmark 任务的完整教学 artifact。

### Program synthesis and refinement

讨论：

* refinement types；
* SYNQUID；
* specification decomposition；
* abstraction refinement；
* contract-guided synthesis。

注意：SYNQUID 的规格分解与本文具有理论启发关系，但本文不是 refinement-type program synthesizer，不能声称方法等同。

### Compositional verification and semantic preservation

讨论：

* assume-guarantee contracts；
* compositional verification；
* refinement；
* verified compilation；
* CompCert。

准确说明 CompCert 使用机器辅助证明，而本文提供的是契约定理加有限 artifact 上的可执行语义检查。

### Noninterference and property-based testing

讨论：

* Goguen and Meseguer 的 noninterference；
* QuickCheck/property-based testing；
* metamorphic or mutation testing。

说明本文借用状态隔离和反例搜索思想，不是信息流安全论文。

所有引用必须：

1. 来自原始论文、正式出版页面或官方仓库；
2. 在 `references.bib` 中具有完整作者、标题、年份和 venue；
3. 不确定时宁可删除或留下 LaTeX 注释，也不能编造。

重点核验的基础文献包括：

```text
SYNQUID / Program Synthesis from Polymorphic Refinement Types
CompCert semantic preservation
Goguen and Meseguer noninterference
QuickCheck
Naps
TRAKLA2
LORI
Munzner nested model
Mayer multimedia learning
WebGen-Agent
HTMLCure
```

## 4.11 Discussion

Discussion 要回答四个问题。

### Why does the method work?

不是因为“模块越多越好”，而是因为：

* 中间表示有明确语义；
* validator 可以提前拒绝；
* deterministic compiler 不再让 LLM 自由决定核心行为；
* teaching layer 对算法状态只读；
* 层间契约允许局部解释和组合推理。

### What has actually been proven?

数学上：

* 抽象契约满足时的组合语义保持；
* 抽象教学状态机上的非干扰；
* 满足 checkpoint 假设时的条件恢复成本关系。

实验上：

* 55,108 个具体帧没有发现层间不一致；
* 156 万次动作没有发现非干扰反例；
* 定义的 mutation suite 中得到完整判别；
* nested survival 在多个模型中重复出现。

### What has not been proven?

* 任意算法轨迹逐步形式正确；
* validator 对所有可能错误 sound and complete；
* 浏览器实现对所有未来动作永远非干扰；
* 当前 Local Resume 必然优于 Global Restart；
* 学生学习成绩得到提升。

### What did the negative recovery result teach us?

明确提出：

```text
semantic factorization does not automatically imply computational
checkpointing.
```

这是论文中非常重要的设计洞见。

## 4.12 Threats to Validity and Limitations

至少包括：

1. Machine OK 测量功能完整性，不测学习效果；
2. evaluator 对固定 Runtime 的潜在偏好仍等待人工 calibration；
3. trace correctness 目前主要依赖执行一致性和 validator，人工双标仍 pending；
4. mutation operators 是有限集合；
5. noninterference stress testing 不能替代形式化验证；
6. 主实验每题只使用 sample 0；
7. 646-sample replay 仍有失败；
8. 不同方法计算预算不同；
9. 远程模型版本可能变化；
10. long-trace 页面文件过大；
11. Stage2 视觉依赖单一 VLM；
12. 尚无真实学生学习实验。

## 4.13 Conclusion

结论应简洁重申：

* 问题是 constraint-entangled artifact generation；
* 方法是 contract-guided semantic factorization；
* 最强结果是组合语义保持、交互可靠性和教学非干扰；
* 当前实现尚未获得完整的计算恢复解耦；
* 不声称真实学习收益。

# 5. 图表要求

至少生成以下图表。

## Figure 1: System architecture

使用 TikZ 展示：

```text
Problem/Input
-> Solver/Spec
-> SemanticTrace
-> SceneGraph
-> Runtime
-> Teaching Overlay
-> Browser Artifact
```

标出：

* LLM-generated；
* deterministic；
* validator；
* immutable algorithm state；
* mutable teaching state。

## Figure 2: Constraint survival

使用 PGFPlots 画累计存活率曲线：

```text
AlgoTutorGen: 100, 100, 100, 99, 99, 99
Direct:       100, 94, 74.5, 54, 49, 49
```

横轴 C1--C6，纵轴 percentage。

图注必须解释每一级契约。

## Figure 3: Theory-to-evidence map

展示：

```text
Compositional preservation
-> 55,108 frames

Contract discrimination
-> 2,198 violations + 392 equivalent transformations

Noninterference
-> 1,561,298 actions

Conditional recovery
-> Local vs Global negative result
```

## Table 1: Main reliability

包含 AlgoTutorGen、Direct、WebGen-Agent 和 HTMLCure。

## Table 2: Theory-aligned evidence

汇总语义保持、变异、非干扰和 determinism。

## Table 3: Cross-model or held-out results

根据篇幅决定正文或附录。

## Table 4: Local vs Global negative result

必须保留，不允许只在正文文字中一笔带过。

# 6. 写作风格

使用正式、克制、清晰的学术英语。

要求：

* 先讲问题，再讲模块；
* 每一节开头说明该节回答什么问题；
* 每个实验明确对应某个理论假设或研究问题；
* 不使用市场宣传语言；
* 不频繁使用 “novel”, “groundbreaking”, “revolutionary”；
* 不写 “proves in practice”；
* 不将 “no counterexample found” 写成 “formally verified”；
* 不用大量零散缩写；
* 首次出现缩写时展开；
* 定理、命题、定义、证明使用统一环境；
* 表格和图注应当脱离正文也可理解；
* 数字保留一致的小数位；
* 百分比同时尽量给出分子和分母；
* 结果与讨论分开；
* 负结果必须诚实报告。

全文应围绕一条中心故事：

```text
Monolithic generation entangles heterogeneous correctness
obligations. AlgoTutorGen separates these obligations through
executable semantic contracts, allowing local validation and
compositional reasoning. Experiments show strong semantic
preservation and pedagogical noninterference, while the failed
Local-vs-Global comparison reveals that semantic decoupling alone
does not yet provide computational checkpointing.
```

# 7. Claim 边界

允许的主张：

```text
AlgoTutorGen substantially improves executable interaction
reliability under the evaluated protocol.

The tested Trace--SceneGraph--Runtime transformations preserve
canonical algorithmic-state projections for all evaluated frames.

The concrete runtime exhibited no pedagogical noninterference
violations in 1.56 million tested actions.

The evaluated contracts discriminated all tested semantic
violations from all tested semantics-preserving transformations.

The reliability gap persists across several generation models
and held-out tasks.
```

禁止的主张：

```text
AlgoTutorGen formally verifies arbitrary algorithm traces.

The validator is universally sound and complete.

The system is proven to improve student learning.

Stage2 is visually superior in every dimension.

Local Resume is more efficient than Global Restart.

All interactions can never affect algorithm state.

The current implementation fully realizes stage-local recovery.
```

# 8. 参考文献规则

在撰写前先搜索并核验相关工作。

只使用：

* 原始论文；
* 正式会议或期刊页面；
* 作者官方 PDF；
* 官方项目仓库；
* 官方模板或标准文档。

避免使用博客作为核心学术依据。

所有 BibTeX 条目必须真实存在。每个引用都要确认：

```text
title
authors
year
venue
DOI or stable URL when available
```

若无法确认，不得编造；可以在 `.tex` 中写：

```latex
% Citation omitted because bibliographic metadata could not be verified.
```

不要输出不存在的 BibTeX key。

# 9. 最终自检

输出前检查：

1. `main.tex` 是否完整；
2. 所有 `\cite{}` 是否在 `references.bib` 中；
3. 所有 label/ref 是否存在；
4. 表格列数是否一致；
5. `%` 是否正确转义；
6. 下划线是否正确转义；
7. 没有 Unicode 数学符号；
8. 没有 `fontspec`、`unicode-math`、`minted`；
9. 没有虚构结果；
10. 没有将 pending human studies 写成 completed；
11. 没有将 Local Resume 写成优于 Global Restart；
12. 没有把测试证据写成形式证明；
13. 所有 TikZ/PGFPlots 图可以由 `pdflatex` 编译；
14. 最终输出包含完整 `main.tex` 和 `references.bib`；
15. 论文可通过四步编译命令得到 PDF。

现在请直接输出完整的：

```text
main.tex
references.bib
```

不要先给提纲，不要解释你打算怎么写，不要省略正文。
