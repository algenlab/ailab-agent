完全理解。你师兄的意思不是“为了显得学术，随便塞个公式”，而是要把目前的工程管线抽象成一个**有一般性的问题、一个明确的理论原则，以及可以被实验验证的结论**。

你们完全可以把故事从：

> 我们设计了 solver、trace、SceneGraph、Runtime 等几个模块，所以网页更稳定。

提升为：

> **交互式算法学习页面生成是一个多约束、强耦合的组合合成问题。端到端生成必须一次性满足算法事实、过程语义、视觉状态和教学交互等异构约束。我们提出基于可执行契约的语义解耦，将一个全局组合搜索问题分解为可局部验证、可局部修复、可组合证明的子问题。**

这个故事是成立的，而且可以写出三个真正贴合系统的定理。

---

# 一、先纠正一个很重要的说法

不要直接写：

> 将大空间拆成多个小空间，因此搜索空间变小。

因为从纯集合论上看，如果最终页面由四部分组成：

[
\Omega
======

\Omega_{\text{solver}}
\times
\Omega_{\text{trace}}
\times
\Omega_{\text{scene}}
\times
\Omega_{\text{interaction}},
]

把它写成四个子空间，并不会自动改变：

[
|\Omega|
========

\prod_i |\Omega_i|.
]

**真正使有效搜索难度降低的，不是“分模块”本身，而是：**

1. 每个中间表示具有明确契约；
2. 错误候选可以在局部提前拒绝；
3. 已经通过验证的前缀不需要重新生成；
4. 下游模块只需依赖接口，不需要理解上游全部实现；
5. 确定性编译替代一部分开放式 LLM 搜索。

这与程序合成中的 modular verification 很接近。SYNQUID 的工作明确指出，可独立验证不同子程序并提前剪枝，可以带来组合意义上的搜索空间缩减；Modular System Synthesis 也把大程序合成为一系列规模受控的子合成问题。

所以你们最准确的术语不是普通的“模块化”，而是：

> **Contract-Guided Semantic Factorization**
> 基于契约的语义因子化

或者：

> **Contract-Guided Compositional Synthesis**
> 基于契约的组合式合成

后一个更像论文术语。

---

# 二、先把问题正式定义出来

给定算法问题和具体输入 (x)，最终需要生成一个网页：

[
W = (S,T,G,P,R),
]

其中：

* (S)：solver，算法求解程序；
* (T)：SemanticTrace，算法执行轨迹；
* (G)：SceneGraph，视觉状态表示；
* (P)：教学与交互 overlay；
* (R)：Web Runtime。

最终网页不是“只要看起来像网页”就算正确，而要同时满足：

[
\Phi(W,x)
=========

\Phi_{\text{answer}}
\land
\Phi_{\text{trace}}
\land
\Phi_{\text{scene}}
\land
\Phi_{\text{interaction}}
\land
\Phi_{\text{noninterference}}.
]

分别表示：

1. 最终答案正确；
2. 轨迹与求解结果一致；
3. 场景与轨迹一致；
4. 按钮、反馈、提示、日志真正工作；
5. 教学交互不能篡改算法事实。

Direct HTML 实际上是在一次生成中搜索：

[
W^*
===

\arg\max_{W\in\Omega}
\Pr[\Phi(W,x)].
]

你们的方法则把全局约束分解成一条契约链：

[
S
\xrightarrow{C_1}
T
\xrightarrow{C_2}
G
\xrightarrow{C_3}
(P,R)
\xrightarrow{C_4}
W.
]

每个 (C_i) 都是一个局部可检查的接口契约。

这已经不再只是“工程 pipeline”，而是一个**带中间语义和局部证明义务的分阶段合成框架**。这种写法与 verified compilation 中逐层 refinement、以及 contract-based compositional verification 的思路一致：各阶段分别证明语义保持，再利用传递性得到端到端性质；契约则作为不同组件之间的“glue specification”。

---

# 三、可以写进论文的第一个核心定理

## 定理 1：局部修复的期望成本优势

这是最适合解释“为什么解耦更容易解决”的定理。

假设系统包含 (k) 个阶段。给定已经通过验证的前缀后：

* 第 (i) 阶段一次生成通过局部契约的概率为 (q_i)；
* 第 (i) 阶段一次生成的成本为 (c_i)；
* 失败后可以只重新生成当前阶段；
* 重试不会破坏此前已经验证的阶段。

### 端到端生成

如果每次失败都必须重新生成整个网页，那么一次完整生成成功的概率为：

[
q_{\text{flat}}
===============

\prod_{i=1}^{k} q_i.
]

一次完整尝试成本为：

[
C=\sum_{i=1}^{k}c_i.
]

因此获得一个有效页面的期望成本是：

[
\mathbb{E}[C_{\text{flat}}]
===========================

\frac{\sum_{i=1}^{k}c_i}
{\prod_{i=1}^{k}q_i}.
]

### 局部验证与局部重试

你们的方法在每个阶段通过后冻结结果，只重试失败阶段。其期望成本为：

[
\mathbb{E}[C_{\text{local}}]
============================

\sum_{i=1}^{k}\frac{c_i}{q_i}.
]

因为：

[
\prod_{j=1}^{k}q_j \leq q_i,
]

所以：

[
\boxed{
\mathbb{E}[C_{\text{local}}]
\leq
\mathbb{E}[C_{\text{flat}}]
}
]

只要至少两个阶段并非永远成功，而且各阶段成本为正，通常就是严格小于。

## 直观解释

端到端生成的失败是**乘法累积**：

```text
算法正确
× 轨迹正确
× 页面正确
× 交互正确
```

任何一个地方错了，整页重来。

解耦后，成本是**加法累积**：

```text
求解器平均尝试次数
+ 轨迹平均尝试次数
+ 教学层平均尝试次数
```

一句很适合放论文里的话是：

> Contract-guided factorization converts multiplicative end-to-end failure into additive local repair cost.

中文就是：

> 基于契约的因子化将端到端的乘性失败风险，转化为局部修复的加性成本。

### 注意假设

这个定理不是无条件的，需要明确：

1. 局部 validator 能识别失败；
2. 已验证中间产物可以复用；
3. 当前阶段重试不会改变上游结果；
4. 对固定有效前缀，重试分布大致稳定。

这些假设与你们的系统结构高度一致。

---

# 四、第二个核心定理：组合式端到端正确性

## 定义各层契约

### Solver 契约

[
C_S(x,S):
\qquad S(x)=\operatorname{Oracle}(x).
]

### Trace 契约

[
C_T(S,T):
\qquad
\operatorname{Final}(T(x))=S(x),
]

并且轨迹中的状态转移满足你们定义的 trace semantics。

### Scene 编译契约

令 (\pi_{\text{alg}}) 表示从 SceneGraph 中提取算法状态的投影：

[
C_G(T,G):
\qquad
\pi_{\text{alg}}(G)=T.
]

也就是 SceneGraph 可以增加坐标、布局和标记，但不能改变算法状态序列。

### Runtime 契约

对任意学生交互序列 (u)：

[
C_R(G,P,R):
\qquad
\pi_{\text{alg}}(R(G,P),u)
==========================

\pi_{\text{alg}}(G).
]

交互可以改变提示、作答状态、日志等教学状态，但不能改变算法事实。

---

## 定理 2：契约组合正确性

如果：

[
C_S(x,S)
\land C_T(S,T)
\land C_G(T,G)
\land C_R(G,P,R),
]

那么对任意学生交互序列 (u)，最终网页 (W) 满足：

[
\operatorname{Answer}(W,u)
==========================

\operatorname{Oracle}(x),
]

并且：

[
\pi_{\text{alg}}(W,u)=T.
]

换句话说：

> 只要每一层都满足与上一层的语义契约，最终网页的算法答案与算法状态就必然与已经验证的轨迹一致。

## 证明思路

由 Solver 契约：

[
S(x)=\operatorname{Oracle}(x).
]

由 Trace 契约：

[
\operatorname{Final}(T(x))=S(x).
]

由 Scene 契约：

[
\pi_{\text{alg}}(G)=T.
]

由 Runtime 契约：

[
\pi_{\text{alg}}(W,u)=\pi_{\text{alg}}(G).
]

通过等式传递性得到：

[
\operatorname{Answer}(W,u)
==========================

# \operatorname{Final}(T(x))

# S(x)

\operatorname{Oracle}(x).
]

这个证明不复杂，但它很重要，因为它将你们的系统从：

> 我们测试了网页，发现大部分能工作。

提升为：

> 我们把端到端性质分解成局部契约；只要各契约成立，最终性质可以通过组合得到。

这种逐阶段证明并通过传递性组合的形式，正是编译器语义保持和 certified abstraction layer 中常见的论证结构。

---

# 五、第三个非常漂亮的定理：教学层非干扰

这个尤其适合解释：

> 为什么 teaching enrichment 必须放在验证后的轨迹之上，而不能让它直接参与算法状态生成？

## 状态分离

把网页状态写成：

[
\sigma=(\sigma_A,\sigma_P),
]

其中：

* (\sigma_A)：算法事实状态，如数组、指针、栈、图、最终答案；
* (\sigma_P)：教学状态，如当前选择、hint 是否展开、答题结果、学习日志。

规定教学动作 (\alpha) 只能修改教学状态：

[
\delta_\alpha(\sigma_A,\sigma_P)
================================

(\sigma_A,\sigma'_P).
]

---

## 定理 3：教学非干扰定理

对任意初始状态 (\sigma^0) 和任意教学交互序列：

[
u=(\alpha_1,\ldots,\alpha_n),
]

都有：

[
\pi_A(\delta_u(\sigma^0))
=========================

\pi_A(\sigma^0).
]

也就是无论学生进行多少次回答、查看提示、显示答案或写入日志，算法事实状态保持不变。

## 证明

对交互长度做归纳即可。

* 长度为 0 时显然成立；
* 假设执行前 (n) 个教学动作后算法状态不变；
* 第 (n+1) 个动作根据定义只修改 (\sigma_P)；
* 因此算法状态仍不变。

所以对任意有限交互序列都成立。

这个定理能非常自然地解释你们系统里的设计：

> 教学层不是算法生成链路的一部分，而是对已验证算法事实的只读 augmentation。

你们现有的 `Mutation-free OK = 200/200` 可以作为实现层面的实验证据，而定理则解释了为什么这种保证可以通过状态隔离得到。

---

# 六、“大空间变成小空间”怎么正式写

可以写一个较弱的命题，不建议把它写成最重要的 theorem。

## 命题：带可扩展契约的搜索空间剪枝

设每层候选空间大小为：

[
|\Omega_i|=n_i.
]

端到端枚举完整候选的最坏规模为：

[
\prod_{i=1}^{k}n_i.
]

如果局部契约满足：

1. **必要性**：违反局部契约的前缀不可能属于任何全局有效解；
2. **可扩展性**：每个通过局部契约的前缀至少存在一个有效下游扩展；
3. **局部可判定性**：每个契约可以在不生成剩余阶段的情况下检查；

那么无回溯的分阶段搜索最多检查：

[
O\left(\sum_{i=1}^{k}n_i\right)
]

个局部候选，而平坦枚举在最坏情况下需要：

[
\Omega\left(\prod_{i=1}^{k}n_i\right).
]

这就是你师兄说的“大复杂空间变成多个小空间”的严格版本。

但一定要写清楚：

> 如果局部契约太弱，使得大量“局部合法前缀”最终无法扩展，分解可能产生大量回溯，并不保证降低搜索成本。

这个限定反而会让理论显得靠谱，而不是强行说分解永远有效。SYNQUID 的核心也是让局部规范足够强，从而提前淘汰不可能完成的子程序，而不是仅仅机械切分程序。

---

# 七、论文故事应该怎么串起来

## 1. 从现象开始

不要上来就介绍系统模块。先讲你们观察到的失败模式：

> LLM 可以生成看起来完整、甚至最终答案正确的教学网页，但最终答案正确并不意味着过程和交互正确。

你们的数据非常适合支撑这句话：

* Stage1 和 Direct 都是 200/200 可见答案正确；
* 但完整 Machine OK 是 198/200 对 98/200；
* Direct 的主要失败来自交互、双向反馈、提示、答案展示、日志和 JavaScript 行为，而不是最终答案。

这说明问题不是“LLM 不会算法”，而是：

> **多个异构正确性义务被压进了一个不可分割的 HTML 生成动作中。**

---

## 2. 定义问题：Constraint Entanglement

你们可以提出一个自己的概念：

> **Constraint Entanglement，约束纠缠**

端到端 HTML 同时承担：

* algorithmic correctness；
* process consistency；
* visualization consistency；
* browser executability；
* pedagogical interaction correctness。

这些约束：

* 由不同机制验证；
* 具有不同失败模式；
* 生命周期不同；
* 修复一个约束可能破坏另一个约束。

例如为了修按钮 JavaScript，LLM 可能重写最终答案区域；为了改善视觉，可能改变算法状态；为了增加 quiz，可能引入错误的标准答案。

---

## 3. 核心洞察

> 不应该让 LLM 在一个未约束空间中共同决定算法事实、过程语义和浏览器行为。

改为：

> 将算法事实、过程语义、视觉表示和教学交互分离，并用可执行契约连接它们。

可以用一句很像论文贡献的话：

> We factor monolithic educational webpage generation into a chain of executable semantic contracts, allowing each artifact to be independently synthesized, validated, repaired, and compositionally reused.

---

## 4. 方法

```text
Problem/Input
    ↓
Executable Solver
    ↓ result contract
Semantic Trace
    ↓ refinement contract
SceneGraph
    ↓ semantic-preserving compilation
Fixed Runtime
    ↓ non-interference contract
Teaching Overlay
```

这里的中间表示不是“为了方便工程实现”，而是：

> **proof-carrying interfaces between generative stages**

即每个阶段输出的不只是内容，也携带下游能够检查的语义证据。

---

## 5. 理论结果

论文中可以正式列出：

* **Theorem 1：Local-Repair Efficiency**
* **Theorem 2：Compositional End-to-End Correctness**
* **Theorem 3：Pedagogical Non-Interference**

然后将实验分别对应到定理。

---

# 八、还需要补哪些实验才能真正支撑理论

你们现有实验已经证明系统有效，但针对这三个定理，还需要做几项更“对题”的实验。

## 实验 A：局部修复 vs 全局重启

当前 `Full 198/200`、`No repair 193/200` 只能说明 repair 有一点帮助，还没有直接证明局部重试优势。

建议增加：

### Local Retry

某阶段失败时，只重新生成该阶段。

### Global Restart

任何阶段失败，都从 solver 开始重新生成整条链。

严格控制：

* 相同模型；
* 相同随机种子集合；
* 相同最大 token；
* 相同成功条件。

报告：

* 总调用数；
* 总 token；
* 达到通过所需尝试数；
* 最终通过率；
* 已验证产物被重复生成的次数。

这可以直接验证定理 1。

更省算力的做法是从现有日志提取每阶段的：

[
q_i,\quad c_i,
]

计算：

[
\widehat C_{\text{flat}}
========================

\frac{\sum c_i}{\prod q_i},
\qquad
\widehat C_{\text{local}}
=========================

\sum\frac{c_i}{q_i},
]

然后再用 30–50 题真实运行做校准。

---

## 实验 B：约束数量扩展曲线

构造逐步增加约束的任务：

| Level | 页面要求                             |
| ----- | -------------------------------- |
| L1    | 只展示正确答案                          |
| L2    | 答案 + 算法轨迹                        |
| L3    | 再加交互和正误反馈                        |
| L4    | 再加 hint、show answer、learning log |
| L5    | 再加视觉增强与状态不可变性                    |

分别比较 Direct 与 AlgoTutorGen 的通过率。

理论预期：

* Direct 随约束数量增加，成功率近似乘法下降；
* 分阶段方法因为局部契约和固定 Runtime，下降更慢。

这张曲线会非常有故事性：

> The reliability gap widens as the number of jointly required obligations increases.

它比单纯的 99% 对 49% 更能证明你们解决的是“复杂组合任务”。

---

## 实验 C：Teaching Overlay 非干扰压力测试

对每个页面随机执行长交互序列：

```text
答错
→ hint
→ show answer
→ 切换步骤
→ 再作答
→ reset
→ 写入日志
```

每个动作前后计算算法状态 hash：

[
h_A =
H(\text{answer},\text{frames},\text{objects},\text{trace ids}).
]

验证：

[
h_A^{\text{before}}
===================

h_A^{\text{after}}.
]

还可以故意替换三种 teaching overlay：

* 原始教学层；
* 另一个模型生成的教学层；
* 随机或 adversarial overlay。

只要符合接口契约，算法状态都应保持不变。

这能很好地支持定理 3，并体现模块的可替换性。

---

## 实验 D：修复目前契约检查的盲点

当前 fault injection 有两个明显缺口：

* event reorder：0/200 拒绝；
* missing SceneGraph reference：0/200 拒绝；
* 删除单个 event 只拒绝 45/200。

在声称“contract-guided correctness”之前，最好增加：

* reference integrity；
* dependency topological order；
* before/after state continuity；
* create-before-use；
* push/pop、enter/exit 等状态机检查。

否则理论上 (C_T) 和 (C_G) 很漂亮，但实际 validator 对这些契约只实现了一部分。

论文中要区分：

> Theorem 对完整契约成立；

和：

> 当前实现对该契约提供有限、可测量的自动近似检查。

这反而更诚实。

---

## 实验 E：两个非退化消融

你们现在的：

```text
No interaction → Machine OK 0
No SceneGraph → Machine OK 0
```

有点容易被审稿人说是“把评测所需功能删了，当然为零”。

更应该做：

### Direct-to-SceneGraph

```text
Problem → LLM 直接生成 SceneGraph → 固定 Runtime
```

保留 Runtime，但去掉 solver、trace 和验证。

它判断：

> 提升是否只是来自固定模板？

### VerifiedTrace-to-FreeHTML

```text
Verified SemanticTrace → LLM 自由生成 HTML
```

保留正确算法事实，但去掉 deterministic compiler/runtime。

它判断：

> 正确性来自 verified facts，还是来自确定性渲染？

这两个实验能将理论里的不同契约真正拆开。

---

# 九、建议论文的核心贡献改写

可以写成四项：

1. **Problem formulation**
   将交互式算法学习环境生成定义为同时满足算法、过程、展示、交互和非干扰约束的组合式 artifact synthesis 问题。

2. **Contract-guided semantic factorization**
   提出一条由 executable solver、SemanticTrace、SceneGraph 和 pedagogical overlay 构成的契约链，将开放式网页生成分解为局部可验证和可修复的子合成问题。

3. **Theoretical characterization**
   证明局部修复相较全局重启具有更低的期望生成成本，证明逐层契约可组合得到端到端正确性，并证明教学交互对算法事实状态的非干扰性。

4. **Empirical evidence**
   在 200 个任务、23 个算法族上验证：最终答案同为 100% 正确时，完整交互可靠性从 49% 提升到 99%，并通过消融、fault injection、跨输入重放和外部 baseline 研究其适用边界。

---

# 十、我最建议采用的论文主标题和一句话

## 方法名字

**Contract-Guided Compositional Synthesis**

系统仍叫 AlgoTutorGen。

## 标题

> **AlgoTutorGen: Contract-Guided Compositional Synthesis of Verifiable Interactive Algorithm Tutors**

或者更突出解耦：

> **From Monolithic HTML Generation to Verifiable Algorithm Tutors via Semantic Factorization**

## 论文中心句

> The central challenge is not generating an HTML page, but jointly satisfying heterogeneous correctness obligations in a monolithic output space. AlgoTutorGen factors these obligations through executable semantic contracts, turning globally entangled generation into locally verifiable and repairable synthesis.

这就把你们从“搭了一个比较完整的工程系统”，升级成了：

> **发现端到端教育网页生成中的约束纠缠问题，并提出一种带有组合正确性和局部修复优势的通用合成范式。**

这条故事是能立住的，而且三个定理都不是硬凑出来的。
