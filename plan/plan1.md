对，**现在不该继续横向堆模型、baseline 和普通消融了，而应该转成“理论命题—假设—定向实验”闭环**。

但有个关键区别：

> **定理由数学证明成立；实验不能“证明定理”，只能验证定理的假设在真实系统里是否近似成立，以及理论预测是否具有实际解释力。**

你们现在的工程证据已经相当齐全：跨四类生成模型、held-out 任务、等预算浏览器修复、非退化消融、修复后的 fault injection、长轨迹压力测试都做了。尤其等预算 Direct repair 越修越坏、Direct-to-SceneGraph 和 VerifiedTrace-to-FreeHTML 几乎全部失败，已经很好地排除了“只是模型调用多”“只是固定模板”“只要给正确数据就行”等解释。

下面应该只围绕理论补 **4 组实验**。

---

# 一、先把论文理论收敛成三条定理和一个命题

## 定理 1：局部重试的期望成本优势

设生成链有 (k) 个可验证阶段。第 (i) 阶段在已有合法前缀下：

* 单次成功概率为 (p_i)；
* 单次成本为 (c_i)。

### 局部重试

每个阶段失败只重试当前阶段：

[
\mathbb E[C_{\mathrm{local}}]
=============================

\sum_{i=1}^{k}\frac{c_i}{p_i}.
]

### 全局重启

任何阶段失败都从第一阶段重新生成。考虑失败后会提前停止，一次尝试的期望成本为：

[
c_1+p_1c_2+p_1p_2c_3+\cdots+
\left(\prod_{j=1}^{k-1}p_j\right)c_k.
]

完整成功概率为：

[
\prod_{i=1}^{k}p_i.
]

因此直到成功的期望成本为：

[
\mathbb E[C_{\mathrm{global}}]
==============================

\sum_{i=1}^{k}
\frac{c_i}{\prod_{j=i}^{k}p_j}.
]

由于：

[
\prod_{j=i}^{k}p_j\le p_i,
]

所以：

[
\boxed{
\mathbb E[C_{\mathrm{local}}]
\le
\mathbb E[C_{\mathrm{global}}]
}
]

只要某个后续阶段存在非零失败概率，通常就是严格不等式。

这比之前粗略使用的：

[
\frac{\sum c_i}{\prod p_i}
]

更准确，因为它考虑了全局尝试在中间失败时会提前终止。

---

## 定理 2：契约的组合正确性

把链路写成：

[
S\xrightarrow{C_{ST}}T
\xrightarrow{C_{TG}}G
\xrightarrow{C_{GR}}R
\xrightarrow{C_P}W,
]

其中：

* (S)：solver；
* (T)：SemanticTrace；
* (G)：SceneGraph；
* (R)：确定性 Runtime；
* (W)：最终网页。

定义：

[
C_{ST}:\quad
\operatorname{Final}(T)=S(x)
]

[
C_{TG}:\quad
\pi_A(G)=T
]

[
C_{GR}:\quad
\pi_A(R(G))=\pi_A(G)
]

[
C_P:\quad
\pi_A(W,u)=\pi_A(R(G))
]

其中 (\pi_A) 是提取“算法事实状态”的投影，(u) 是任意教学交互序列。

若每个局部契约成立，那么：

[
\operatorname{Answer}(W,u)
==========================

# S(x)

\operatorname{Oracle}(x).
]

这就是标准的 assume–guarantee / refinement 思路：每个组件的保证满足下一个组件的假设，局部契约可以组合成全局性质。契约式组合验证和语义保持编译都是成熟的形式化方法范式。([ScienceDirect][1])

---

## 定理 3：教学层非干扰

将网页状态分为：

[
\sigma=(\sigma_A,\sigma_P),
]

其中：

* (\sigma_A)：算法事实，如 trace、数组、图、指针和最终答案；
* (\sigma_P)：教学状态，如作答、提示、答案展开和学习日志。

若任意教学动作 (\alpha) 都满足：

[
\delta_\alpha(\sigma_A,\sigma_P)
================================

(\sigma_A,\sigma'_P),
]

那么对任意教学动作序列：

[
u=(\alpha_1,\ldots,\alpha_n),
]

都有：

[
\boxed{
\pi_A(\delta_u(\sigma))=\sigma_A
}
]

证明对交互序列长度做归纳即可。

“某类动作不会影响另一个观察域”正是 noninterference 的核心形式。([普渡大学计算机科学系][2])

---

## 命题 4：约束纠缠导致可靠性乘法衰减

设页面需要依次满足嵌套义务：

[
C_1,C_2,\ldots,C_m.
]

定义条件存活率：

[
\alpha_i
========

P(C_i\mid C_1\land\cdots\land C_{i-1}).
]

则根据概率链式法则：

[
\boxed{
P\left(\bigwedge_{i=1}^{m}C_i\right)
====================================

\prod_{i=1}^{m}\alpha_i
}
]

这里不需要假设各约束相互独立。

它解释了你们最核心的观察：

* Direct 的最终答案可以是 100%；
* 但加入加载、交互、双向反馈、提示、日志和不变性后，最终只剩 49%；
* AlgoTutorGen 通过固定实现和局部契约，让后续条件存活率接近 1。

---

# 二、实验 1：真正验证“局部重试优于全局重启”

这是目前**最缺、也最贴合定理 1**的实验。

现有 `No repair` 193/200 和 `Direct-BrowserRepair` 曲线并不是这个实验：

* `No repair` 只比较有没有 repair；
* Direct repair 是自由 HTML 重写；
* 它们没有比较同一结构化系统内的“局部恢复”和“全部重来”。

## 实验条件

使用完全相同的：

* 模型；
* prompt；
* 最大 candidate 数；
* repair 轮数；
* token/call 总预算；
* 任务顺序；
* 最好使用同一组采样种子或预生成候选池。

设置三种策略。

### A. Local Resume

当前系统：

```text
语义候选通过后冻结
→ teaching 失败只重做 teaching
→ scene/runtime 检查失败只处理对应阶段
```

### B. Global Restart

任何阶段失败都丢弃所有中间结果：

```text
任意 gate 失败
→ 从语义候选重新开始
```

### C. Flat Final-Only

中间 gate 不阻断，完成后只在最终网页做一次总检查。这个条件可以只做 50 题，用来展示缺乏中间契约时错误无法局部归因。

## 建议规模

先用：

```text
50 个分层任务 × 2 个生成模型
```

模型选：

* DeepSeek-V4-Flash；
* GLM-5.2 或 Kimi-K2.5。

不需要再做 200 × 4。

## 必须记录

对每个阶段 (i) 记录：

[
\hat p_i
========

\frac{\text{stage successes}}
{\text{stage attempts}}
]

[
\hat c_i
========

\text{mean calls/tokens/time per attempt}.
]

然后计算理论预测：

[
\widehat C_{\mathrm{local}}
===========================

\sum_i\frac{\hat c_i}{\hat p_i}
]

[
\widehat C_{\mathrm{global}}
============================

\sum_i
\frac{\hat c_i}
{\prod_{j=i}^{k}\hat p_j}.
]

再与真实运行成本对比。

## 主指标

* 成功一个页面的平均 token；
* 成功一个页面的平均调用数；
* time-to-first-valid-artifact；
* 固定预算下成功率；
* 已验证工作被重复计算的成本；
* 理论预测与实测成本误差；
* 每个失败能否定位到正确契约阶段。

## 最重要的图

横轴是 token 或 calls，纵轴是累计成功率：

```text
Local Resume
Global Restart
Flat Final-Only
```

如果 Local Resume 曲线始终位于上方，定理 1 就不仅是一个数学观察，而且有实证意义。

---

# 三、实验 2：逐层语义保持，而不是只看最终 Machine OK

当前 `Machine OK=198/200` 证明最终网页工作，但还没有直接验证：

[
T \equiv G \equiv DOM
]

也就是 SemanticTrace、SceneGraph 和浏览器状态是否逐帧语义一致。

这项实验直接对应定理 2。

## 为每一层定义统一的算法状态投影

例如：

[
z_t =
(
\text{objects},
\text{values},
\text{marks},
\text{pointers},
\text{edges},
\text{stack/queue},
\text{answer}
).
]

分别提取：

[
z_t^T=\pi_A(T_t)
]

[
z_t^G=\pi_A(G_t)
]

[
z_t^{DOM}=\pi_A(\operatorname{Render}(G_t)).
]

检查：

[
z_t^T=z_t^G=z_t^{DOM}.
]

不要直接比较 JSON 文本，因为布局坐标、对象顺序和额外视觉字段可能不同；要先 canonicalize。

## 建议样本

优先跑：

* 200 个 sample-0 页面；
* 40 个 held-out 页面；
* 18 个 long-trace 任务的 small/medium/large。

646 个输入可以视运行成本再决定，不是硬性要求。

## 输出指标

| 边界                 | 检查             |
| ------------------ | -------------- |
| Solver → Trace     | 最终结果、输入和关键状态一致 |
| Trace → SceneGraph | 每帧算法状态投影一致     |
| SceneGraph → DOM   | 渲染后的可见/内部状态一致  |
| DOM → interaction  | 交互前后算法状态是否保持   |

报告：

* frame-level equivalence rate；
* artifact-level all-frame pass；
* 首个不一致所在边界；
* 不同算法族的 mismatch；
* long-trace 下是否仍保持一致。

## 再加入编译器确定性

同一 `BuildArtifact` 重复编译和渲染 10 次：

[
H(\operatorname{CanonicalDOM}_1)
================================

# \cdots

H(\operatorname{CanonicalDOM}_{10}).
]

CompCert 类工作的核心不是“编译结果看起来对”，而是证明源语言到目标语言的语义保持；你们不需要做到 Coq 级形式证明，但应该将实验组织成明确的 refinement checking。([CompCert][3])

---

# 四、实验 3：教学非干扰的 property-based stress test

当前 `Mutation-free OK=200/200` 主要检查最终答案区域没有被学生操作修改。

这只验证了：

[
\operatorname{Answer}_{\mathrm{before}}
=======================================

\operatorname{Answer}_{\mathrm{after}}.
]

但定理 3 要求更强：

[
\operatorname{AlgorithmState}_{\mathrm{before}}
===============================================

\operatorname{AlgorithmState}_{\mathrm{after}}.
]

## 测试设计

对每个页面随机生成可达动作序列，包括：

* 下一步、上一步；
* 正确作答；
* 错误作答；
* 多次重复提交；
* hint；
* show answer；
* reset；
* 跳转时间线；
* learning log；
* 选择不同 checkpoint。

建议：

```text
240 pages
× 100 条序列
× 每条 30–100 个动作
```

240 页面可以是 200 主任务加 40 held-out。

在每个动作前后计算：

[
h_A
===

H(
\text{trace},
\text{frames},
\text{algorithm objects},
\text{final answer}
).
]

要求对所有纯教学动作：

[
h_A^{t+1}=h_A^t.
]

Property-based testing 的标准做法就是把性质写成可执行谓词，再自动生成大量输入并搜索反例。

## 再做 overlay 替换实验

对同一个验证后的 SceneGraph，生成：

* 原 teaching overlay；
* 简洁 overlay；
* 详细 overlay；
* 另一模型生成的 overlay；
* 随机但 schema 合法的 overlay。

验证：

[
\pi_A(W_{P_1})
==============

# \pi_A(W_{P_2})

\cdots
]

同时加入非法 overlay：

* 尝试改 final answer；
* 尝试改 frame object value；
* 引用不存在的 frame；
* 写入算法状态字段。

非法 overlay 应在接口或 release gate 被拒绝。

## 论文如何描述

* 非干扰定理通过状态转移定义和归纳证明；
* property-based 实验用于搜索实现是否违反了理论假设；
* 没找到反例不能等于形式证明。

Metamorphic/property testing 可以发现性质被违反的反例，但一般不能证明性质对全部输入永远成立。([i.cs.hku.hk][4])

---

# 五、实验 4：约束增长曲线，直接展示“约束纠缠”

这个实验大部分**不需要重新生成页面**，可以直接利用现有逐项结果。

## 定义嵌套 contract

建议固定为：

### (C_1)：事实

```text
Visible answer match
```

### (C_2)：可执行

```text
C1 + page load
```

### (C_3)：可交互

```text
C2 + interaction reachable
```

### (C_4)：双向反馈

```text
C3 + correct feedback + wrong feedback
```

### (C_5)：教学支持

```text
C4 + hint + show answer + learning log
```

### (C_6)：非干扰

```text
C5 + mutation-free
```

对每个方法计算：

[
P(C_1),
P(C_1\land C_2),
\ldots,
P\left(\bigwedge_{i=1}^{6}C_i\right).
]

以及条件存活率：

[
\alpha_i
========

P(C_i\mid C_1\land\cdots\land C_{i-1}).
]

## 使用哪些结果

至少画：

* AlgoTutorGen；
* Direct；
* WebGen-Agent；
* Direct-BrowserRepair；
* 三个新增生成模型下的 AlgoTutorGen/Direct。

## 预期故事

Direct 很可能是：

```text
答案几乎全对
→ 加交互后明显掉
→ 加双向反馈再掉
→ 加完整教学 contract 再掉
```

AlgoTutorGen 则应当接近：

```text
100% → 100% → 100% → 99% → 99% → 99%
```

这张图会非常直观地展示：

> 差异不是来自答案生成，而是来自异构义务在单一 HTML 中发生乘性累积。

## 可选的小规模重新生成

只有当审稿人可能质疑“你只是事后改变评价门槛”，才补：

```text
50 tasks × 2 methods × 5 requirement levels
```

逐级增加 prompt 要求。

但我建议先做零成本的 cumulative-contract 分析，通常已经足够。

---

# 六、把 fault injection 改成“语义变异测试”

你们现在将 fault rejection 从：

[
1843/2400
]

提升到：

[
2246/2400,
]

并解决了 event reorder 与悬空 SceneGraph reference，这很好。

但还需要重新解释那 152 个“删除 event 后仍接受”的案例。

删除一个 event 不一定真的破坏语义：

* 可能删的是冗余 explain；
* 可能删的是重复 mark；
* 可能删掉的状态没有影响后续；
* 两个独立事件也可能安全交换。

因此不要把所有 syntactic mutation 都称为“真实 fault”。

## 重新分两组

### 必须拒绝的语义破坏

* 错误最终结果；
* before/after 不连续；
* use-before-create；
* 依赖逆序；
* trace-scene state mismatch；
* 错误 checkpoint answer；
* 对算法状态的 teaching write；
* 删除唯一产生关键状态的事件。

### 应当接受的语义保持变换

* 删除纯冗余 explain；
* 交换互不依赖的事件；
* 重命名内部 object ID 后同步修改引用；
* 改变视觉布局但不改变算法状态；
* 修改 teaching 文案但不改变事实。

然后报告：

[
\text{semantic violation rejection rate}
]

以及：

[
\text{semantics-preserving acceptance rate}.
]

这会比单一“93.58% fault rejection”更有理论味道，因为它真正测试的是契约语义，而不是 JSON 形式。

Synquid 的相关工作也强调，真正带来组合搜索优势的是**足够强且可分解的规格**，而不是单纯把程序机械拆成几个文件。([arXiv][5])

---

# 七、已有实验如何放进理论故事

你们现有结果不需要丢掉，而是重新映射。

| 理论主张                    | 已有证据                               | 尚缺证据         |
| ----------------------- | ---------------------------------- | ------------ |
| 解耦不是模型特例                | 4 个生成模型、held-out 39/40             | 已基本完成        |
| 更多调用不能替代结构化约束           | Direct repair 1→5 calls 从 106 降至 6 | 已基本完成        |
| 固定 Runtime 不是唯一原因       | Direct-to-SceneGraph 1/50          | 已完成          |
| 正确 trace 不能保证自由 HTML 可靠 | VerifiedTrace-to-LLM-HTML 0/50     | 已完成          |
| 局部修复优于全局重启              | 当前尚无直接比较                           | **必须补实验 1**  |
| 局部契约组合成端到端语义            | fault injection、最终 Machine OK      | **必须补实验 2**  |
| Teaching 不影响算法事实        | mutation-free 200/200              | **必须补实验 3**  |
| 约束纠缠导致可靠性衰减             | 答案 100%、Machine OK 49%             | **补实验 4 曲线** |

---

# 八、人工实验接下来怎么办

你们已经准备了：

* 120 个盲页的机器评测器校准；
* 40-task trace correctness 双标包；
* 3 experts × 30 pairs；
* 24 students × 12 trials。

其中最应该先收的是前两个：

## 必做

1. **机器评测器校准**
   证明外部网页不是因为 UI 形式不同而被自动脚本误杀。

2. **Trace correctness 双人标注**
   证明 SemanticTrace 不只是内部一致，而是关键算法步骤确实合理。

## 视投稿方向决定

* 投软件工程、系统或 NLP：可以不做学生实验；
* 投 AIED、EDM、CHI 或教育技术：最好做 24 人实验。

这部分是外部效度，不是理论证明，但很可能比继续增加第五码模型更有价值。

---

# 九、长轨迹问题单独处理

当前 large 平均：

* 1,636.7 frames；
* 160.4 MB HTML；
* 8.35 秒加载；
* 最大达到 1.08 GB；
* 两个任务超过 60 秒。

这是明确的系统限制，但**不要把它塞进解耦定理的实验里**。

论文中诚实写：

> 当前确定性逐帧物化保证了易审计性，但产生了 (O(F\cdot |S|)) 的存储开销。

可以补一个很小的 prototype：

```text
full-frame snapshots
vs
initial state + event deltas
```

报告 HTML 大小和加载时间即可。没有时间就作为 future work，不影响核心理论线。

---

# 十、接下来最合理的执行顺序

## 第一阶段：先写理论，不先跑实验

先冻结：

1. 三条定理的正式定义；
2. 每条定理的假设；
3. 系统实际对应哪些阶段；
4. 每个契约究竟检查什么；
5. 哪些性质是数学证明，哪些只是自动检查。

尤其不要把概念模块写成独立生成子空间，除非代码确实能够独立重试。理论必须忠于实现。

## 第二阶段：完成四个理论实验

优先级：

1. **Local Resume vs Global Restart**
2. **Trace–SceneGraph–DOM 逐帧语义保持**
3. **Teaching noninterference property testing**
4. **Nested contract survival curve**

## 第三阶段：收人工标签

先做：

* evaluator calibration；
* trace correctness audit。

学生学习实验根据投稿方向决定。

---

## 最终建议

接下来不要再问：

> 还能不能再加一个模型、一个 baseline、一个普通消融？

而要围绕下面四个问题组织整篇论文：

1. **为什么端到端生成会失败？**
   因为多个异构义务在一个输出中发生约束纠缠和乘性失败累积。

2. **为什么解耦有效？**
   因为契约允许提前拒绝、局部重试、语义复用和确定性编译。

3. **为什么最终页面仍然正确？**
   因为每个转换阶段满足可组合的语义保持契约。

4. **为什么教学功能不会破坏算法事实？**
   因为算法状态和教学状态被隔离，并满足非干扰性质。

你们现有实验已经把“这个系统有效”证明得差不多了。下一步要做的是把它变成：

> **理论解释为什么有效，定向实验验证理论假设在真实系统中成立。**

[1]: https://www.sciencedirect.com/science/article/pii/S0167642314000057 "Compositional assume–guarantee reasoning for input/output component theories - ScienceDirect"
[2]: https://www.cs.purdue.edu/homes/ninghui/readings/AccessControl/goguen_meseguer_82.pdf "Security Policies and Security Models"
[3]: https://compcert.org/compcert_bib.html "compcert.bib"
[4]: https://i.cs.hku.hk/~tse/Papers/2020s/tybyndTR.pdf "New Visions on Metamorphic Testing after a Quarter of a Century of Inception"
[5]: https://arxiv.org/abs/1510.08419 "[1510.08419] Program Synthesis from Polymorphic Refinement Types"
