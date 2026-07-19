# AlgoTutorGen 的理论推导与定向实验

本文根据 [plan/plan1.md](../plan/plan1.md) 的理论设计，以及 [EXPERIMENT_RESULTS.md](./EXPERIMENT_RESULTS.md) 第 6 节的最终结果，说明论文引入了什么理论、公式如何得到、实验如何对应理论，以及最终观察到什么结果。

需要先区分两类证据：

- **数学推导**：在明确假设下证明理论命题成立。
- **定向实验**：检查真实系统是否满足这些假设、理论预测是否符合实测，并搜索实现中的反例。有限实验不能代替对所有输入和执行的形式化证明。

## 1. 理论与实验总览

| 理论主张 | 核心含义 | 对应实验 | 主要结果 |
| --- | --- | --- | --- |
| 定理 1：理想局部恢复的期望成本不高于全局重启 | 某阶段失败后只重做该阶段，理想情况下比整条链全部重来更省 | Local Resume vs Global Restart | 当前 Local 没有取得成功率优势，说明实现尚不满足完整 checkpoint recovery 假设 |
| 定理 2：局部契约可以组合成端到端语义保持 | Trace、SceneGraph 和 Runtime 逐层保持同一算法状态，最终网页也保持该状态 | Trace→Scene→Runtime 逐帧比较 | 294/294 个 artifact、55,108/55,108 帧一致 |
| 定理 3：教学层对算法事实非干扰 | 提示、作答和学习日志可以变化，但不能改写算法事实 | Overlay 替换与随机动作压力测试 | 1,561,298 次动作中观察到 0 次状态污染 |
| 命题 4：多项约束的联合存活率按条件概率相乘 | 页面承担的义务越多，各层损失会累积到最终完整通过率 | C1—C6 Nested contract survival | AlgoTutorGen 基本保持；Direct、WebGen 和 BrowserRepair 在交互、反馈等层继续下降 |
| 配套审计：契约应区分错误变化和无害变化 | 验证器既要拒绝语义破坏，也要接受不改变语义的变化 | Semantic mutation | 2,198/2,198 个语义破坏被拒绝，392/392 个语义保持变化被接受 |

## 2. 定理 1：局部恢复的期望成本优势

### 2.1 定义与成立条件

设生成链包含 \(k\) 个可验证阶段。第 \(i\) 个阶段在已有合法前缀的条件下：

- 单次成功概率为 \(p_i\)，其中 \(0<p_i\le 1\)；
- 单次执行成本为 \(c_i>0\)，成本可以表示 token、调用次数或时间。

定理依赖三个关键条件：已经通过的阶段可以被可靠保存；当前阶段失败不会破坏合法前缀；局部恢复只重试失败阶段，不会重新计算已验证的下游内容。

### 2.2 公式推导

局部恢复时，第 \(i\) 阶段直到成功所需的尝试次数服从成功概率为 \(p_i\) 的几何分布，因此：

$$
\mathbb{E}[N_i]=\frac{1}{p_i}.
$$

把各阶段成本相加，得到局部恢复直到整条链成功的期望成本：

$$
\mathbb{E}[C_{\mathrm{local}}]
=\sum_{i=1}^{k}c_i\mathbb{E}[N_i]
=\sum_{i=1}^{k}\frac{c_i}{p_i}.
$$

全局重启时，一次尝试只有在前 \(i-1\) 个阶段都成功后才会执行第 \(i\) 阶段，所以单次尝试的期望成本为：

$$
A=c_1+p_1c_2+p_1p_2c_3+\cdots+
\left(\prod_{j=1}^{k-1}p_j\right)c_k.
$$

一次尝试完整成功的概率为：

$$
q=\prod_{i=1}^{k}p_i.
$$

设 \(E_g\) 是全局重启直到成功的期望成本。一次尝试后，以概率 \(1-q\) 重新开始，因此：

$$
E_g=A+(1-q)E_g,
$$

从而：

$$
\mathbb{E}[C_{\mathrm{global}}]
=E_g
=\frac{A}{q}
=\sum_{i=1}^{k}\frac{c_i}{\prod_{j=i}^{k}p_j}.
$$

由于所有 \(p_j\le 1\)，有：

$$
\prod_{j=i}^{k}p_j\le p_i.
$$

因此逐项比较可得：

$$
\boxed{
\mathbb{E}[C_{\mathrm{local}}]
\le
\mathbb{E}[C_{\mathrm{global}}]
}.
$$

如果某个阶段之后仍存在失败概率大于 0 的阶段，且相应成本非零，通常得到严格不等式。这个结论证明的是满足完整 checkpoint 条件时的理想系统，而不是无条件保证任意名为“Local”的实现都更好。

### 2.3 实验如何检查该理论

实验在相同的 50 个任务、相同生成模型、相同结构化输出空间和每题最多 3 次策略决策下比较：

- **Local Resume**：保留当前 solution spec，失败后调用 repair。
- **Global Restart**：丢弃当前 spec，从生成阶段重新开始。

实验先由实际运行估计各阶段的成功率和单次成本：

$$
\hat p_i=\frac{\text{stage successes}}{\text{stage attempts}},
\qquad
\hat c_i=\text{mean cost per attempt},
$$

再将 \(\hat p_i\) 和 \(\hat c_i\) 代入理论模型，与有限预算下的实测结果比较。该实验不是重新证明上面的不等式，而是检查当前实现是否满足不等式所需的恢复条件。

| 模型 | 策略 | 最终成功 | Token/成功页 | Calls/成功页 | 平均 time-to-valid |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V4-Flash | Local Resume | 38/50（76.0%） | 71,369 | 6.63 | 172.9 s |
| DeepSeek-V4-Flash | Global Restart | 42/50（84.0%） | 62,256 | 5.50 | 194.2 s |
| GLM-5.2 | Local Resume | 42/50（84.0%） | 92,385 | 6.69 | 533.8 s |
| GLM-5.2 | Global Restart | 43/50（86.0%） | 96,186 | 6.65 | 558.2 s |

`Token/成功页` 和 `Calls/成功页` 的分子包含最终失败任务消耗；`time-to-valid` 只对成功任务统计首次获得有效 artifact 的时间。

有限预算模型与实测成功率接近。这里使用同一批运行估计参数并完成拟合，属于解释性拟合，不是独立测试集上的预测：

| 模型 | 策略 | 理论拟合预测 | 实测成功率 | 绝对误差 |
| --- | --- | --- | --- | --- |
| Flash | Local | 76.89% | 76.00% | 0.89 pp |
| Flash | Global | 85.72% | 84.00% | 1.72 pp |
| GLM | Local | 83.15% | 84.00% | 0.85 pp |
| GLM | Global | 87.06% | 86.00% | 1.06 pp |

**实验结论：** Local 在两个模型上都降低了 spec generation/repair 成本，但当前实现仍会重新 materialize，并重新生成 teaching 内容。Flash 上这些重算成本超过了 spec 节省量；GLM 上总 token 略低，但成功率仍少 1 题。因此这是一个负结果：理论模型能解释观测结果，但当前实现并不满足完整阶段 checkpoint 的关键假设，不能据此声称 Local 已经优于 Global。

## 3. 定理 2：局部契约的组合语义保持

### 3.1 定义与推导

把系统链路写成：

$$
S\longrightarrow T\longrightarrow G\longrightarrow R\longrightarrow W,
$$

其中 \(S\) 是 solver，\(T\) 是 SemanticTrace，\(G\) 是 SceneGraph，\(R\) 是确定性 Runtime，\(W\) 是最终网页。令 \(\pi_A(\cdot)\) 表示只提取数组值、图结构、指针、栈、队列和最终答案等“算法事实状态”，忽略布局、颜色和教学文字。

局部契约定义为：

$$
C_{ST}:\quad \operatorname{Final}(T)=S(x),
$$

$$
C_{TG}:\quad \pi_A(G_t)=\pi_A(T_t),\quad \forall t,
$$

$$
C_{GR}:\quad \pi_A(R(G)_t)=\pi_A(G_t),\quad \forall t,
$$

$$
C_P:\quad \pi_A(W,u)=\pi_A(R(G)),
$$

其中 \(u\) 是任意合法教学交互序列。由等式的传递性：

$$
\pi_A(W,u)
=\pi_A(R(G))
=\pi_A(G)
=\pi_A(T).
$$

最终答案是算法状态投影中的一个分量，因此：

$$
\operatorname{Answer}(W,u)=\operatorname{Final}(T)=S(x).
$$

若 solver 本身满足：

$$
S(x)=\operatorname{Oracle}(x),
$$

则得到端到端结论：

$$
\boxed{
\operatorname{Answer}(W,u)=\operatorname{Oracle}(x)
}.
$$

这就是组合验证的核心：每一层只需证明自己的输出保持上一层的算法状态，局部等式即可沿链路传递为全局性质。

### 3.2 实验如何检查该理论

实验为每一帧定义统一的 canonical algorithm state：

$$
z_t=(\text{objects},\text{values},\text{marks},\text{pointers},
\text{edges},\text{stack/queue},\text{answer}).
$$

分别从 Trace、SceneGraph 和浏览器 Runtime 提取状态，并检查：

$$
z_t^T=z_t^G=z_t^R,\quad \forall t.
$$

| 数据集 | Artifact 全帧通过 | 等价帧 | Frame equivalence |
| --- | --- | --- | --- |
| Main 200 | 200/200 | 9,421/9,421 | 100.0% |
| Held-out representation audit | 40/40 | 4,568/4,568 | 100.0% |
| Long-trace 54 | 54/54 | 41,119/41,119 | 100.0% |
| **总计** | **294/294** | **55,108/55,108** | **100.0%** |

实验还对 20 个 artifact 分别重复编译和渲染 10 次。若 \(H\) 表示 canonical render/projection hash，则检查：

$$
H_1=H_2=\cdots=H_{10}.
$$

每个 artifact 最终只产生一个 render hash 和一个 projection hash。

**实验结论：** 在已经评估的 294 个 artifact 和 55,108 帧上，没有发现 Trace→SceneGraph→Runtime 的状态投影不一致，也没有发现重复编译和渲染的非确定性。该结果支持实现满足上述局部保持契约，但不独立证明源 SemanticTrace 的每一步都符合算法语义，也不属于像素级形式验证。

## 4. 定理 3：教学层非干扰

### 4.1 状态划分与归纳推导

将网页状态划分为：

$$
\sigma=(\sigma_A,\sigma_P),
$$

其中 \(\sigma_A\) 是受保护的算法事实，\(\sigma_P\) 是学习者作答、提示展开、答案展示和学习日志等教学状态。

对任意纯教学动作 \(\alpha\)，非干扰契约要求：

$$
\delta_\alpha(\sigma_A,\sigma_P)
=(\sigma_A,\sigma'_P).
$$

也就是说，动作可以改变教学状态，但算法状态必须保持不变。对动作序列

$$
u=(\alpha_1,\ldots,\alpha_n),
$$

可以对序列长度做归纳证明：

1. 当 \(n=0\) 时没有执行动作，显然 \(\pi_A(\delta_u(\sigma))=\sigma_A\)。
2. 假设长度为 \(n\) 的序列执行后算法状态仍为 \(\sigma_A\)。再执行一个满足局部契约的教学动作 \(\alpha_{n+1}\)，该动作仍不能改变算法状态。

因此对任意有限教学动作序列都有：

$$
\boxed{
\pi_A(\delta_u(\sigma))=\sigma_A
}.
$$

### 4.2 实验如何检查该理论

第一组实验替换同一 SceneGraph 上的 teaching overlay，并比较替换前后的算法 state hash：

| Overlay 条件 | 规模 | 结果 |
| --- | --- | --- |
| 冻结 overlay 重放 | 372 | 372/372 state hash 保持 |
| Concise 合法 overlay | 372 | 372/372 保持 |
| Detailed 合法 overlay | 372 | 372/372 保持 |
| Schema-valid random-text overlay | 372 | 372/372 保持 |
| 非法 `final_answer` / `state` 写入 | 372 | 372/372 被清洗，state hash 保持 |
| GLM cross-model overlay | 369 个可映射 scene | 369/369 state hash 保持；169 个完整应用，200 个因 step 差异部分应用 |

第二组实验在 240 个页面上自动生成随机动作序列。纯教学动作要求 artifact hash、当前算法 state hash 和 step 均不变；导航和 variant 切换可以改变当前帧，但只能落到目标 verified frame，且完整 artifact hash 必须保持不变。

| 覆盖量 | 实验结果 |
| --- | --- |
| 页面 | 240/240 通过 |
| 随机动作序列 | 24,000 |
| 总动作 | 1,561,298 |
| 其中纯教学动作 | 435,859 |
| 导航/variant 动作 | 1,125,439 |
| 观察到的状态污染违规 | 0 |

**实验结论：** Overlay 替换、跨模型教学内容复用和 1,561,298 次随机浏览器动作都没有暴露算法事实被教学层改写的反例。这与非干扰定理的实现预测一致，但仍属于大规模反例搜索，不能推出所有未来页面和动作序列都必然无违规。

## 5. 命题 4：约束纠缠与联合存活率衰减

### 5.1 概率公式如何得到

设页面依次增加六项基本义务 \(B_1,\ldots,B_6\)：

- \(B_1\)：答案正确；
- \(B_2\)：页面加载；
- \(B_3\)：交互可达；
- \(B_4\)：正确和错误答案都有正确反馈；
- \(B_5\)：具备 hint、show-answer 和 learning log；
- \(B_6\)：教学操作不干扰算法状态。

定义累计合同：

$$
C_i=\bigwedge_{j=1}^{i}B_j.
$$

再定义每一层的条件存活率：

$$
\alpha_1=P(B_1),
$$

$$
\alpha_i=P(B_i\mid C_{i-1}),\quad i\ge 2.
$$

由条件概率公式：

$$
P(C_i)=P(B_i\mid C_{i-1})P(C_{i-1}).
$$

逐层展开即可得到：

$$
\boxed{
P(C_m)=P\left(\bigwedge_{i=1}^{m}B_i\right)
=\prod_{i=1}^{m}\alpha_i
}.
$$

这个推导是概率链式法则，不要求六项义务相互独立。“约束纠缠”的含义是：当多项异构义务共享同一份自由 HTML/JavaScript 状态时，某一层的实现错误可能让页面无法进入后续合格集合，最终完整通过率就表现为逐层累积下降。

### 5.2 实验如何验证理论解释

实验对每种方法计算从 C1 到 C6 的累计存活率：

| 方法 | C1 | C2 | C3 | C4 | C5 | C6 |
| --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen main | 100.0% | 100.0% | 100.0% | 99.0% | 99.0% | 99.0% |
| Direct HTML main | 100.0% | 94.0% | 74.5% | 54.0% | 49.0% | 49.0% |
| WebGen-Agent | 84.5% | 84.5% | 67.5% | 27.5% | 22.5% | 22.5% |
| Direct-BrowserRepair-5 | 95.5% | 92.5% | 14.0% | 6.0% | 3.0% | 3.0% |

以 Direct HTML 为例，实测条件存活率为：

$$
(\alpha_1,\ldots,\alpha_6)
=(1.000,0.940,0.793,0.725,0.907,1.000).
$$

代入乘积公式：

$$
1.000\times0.940\times0.793\times0.725\times0.907\times1.000
\approx0.490,
$$

与最终 C6 的 49.0% 一致。AlgoTutorGen 的对应乘积约为：

$$
1.000\times1.000\times1.000\times0.990\times1.000\times1.000
=0.990.
$$

**实验结论：** Direct HTML 的答案最初为 100%，但在加载、交互、双向反馈和完整教学支持逐层加入后下降到 49%；WebGen-Agent 和 BrowserRepair-5 的下降更明显。AlgoTutorGen 的主要损失只出现在极少数双向反馈边界，后续条件存活率接近 1。条件率乘积与最终累计率一致是链式法则的一致性检查，不是独立的定理证明；这项实验真正提供的新信息，是不同方法具体在哪一层开始损失，并由此支持“自由页面中的多义务纠缠”这一解释。

## 6. 配套实验：契约是否具有语义辨别力

只会拒绝变化的验证器没有实际意义，因为无害的文字或视觉变化也可能被误杀。因此把变异分为两类：

- \(M_{\mathrm{bad}}\)：明确破坏算法语义，期望拒绝；
- \(M_{\mathrm{good}}\)：保持算法语义，期望接受。

对应指标为：

$$
R_{\mathrm{bad}}
=\frac{\#\text{ rejected semantic violations}}{|M_{\mathrm{bad}}|},
$$

$$
A_{\mathrm{good}}
=\frac{\#\text{ accepted preserving changes}}{|M_{\mathrm{good}}|}.
$$

| 变换类别 | 期望 | 结果 |
| --- | --- | --- |
| 已定义的 semantic violations | Reject | 2,198/2,198 |
| Teaching-text rewrites | Accept | 195/195 |
| Visual-metadata changes | Accept | 195/195 |
| Equivalent unordered-result reorderings | Accept | 2/2 |
| **Semantics-preserving total** | **Accept** | **392/392** |

2,198 个违规样本只包含由 oracle 明确定义为语义破坏的变异，不把语义不确定的 trace-event deletion 强行计为错误。

**实验结论：** 当前契约在已定义的 mutation suite 上同时实现了 100% 的语义违规拒绝率和 100% 的语义保持接受率，说明它不是简单地“拒绝一切变化”。该结果只说明当前变异集合上的辨别力，不代表验证器对所有未来错误都具有完备性。

## 7. 总结

1. **理论 1 给出理想上界，但当前实现尚未满足关键假设。** Local Resume 的负结果准确限定了系统目前能主张的恢复能力。
2. **理论 2 的证据最直接。** 55,108 帧逐层一致，支持 Trace、SceneGraph 与 Runtime 之间的组合语义保持。
3. **理论 3 得到大规模反例搜索支持。** Overlay 变换和 1,561,298 次动作中均未发现教学状态污染算法事实。
4. **命题 4 解释了方法差距出现在哪里。** Direct 等方法并非主要输在最终答案，而是在加载、交互、反馈和教学义务叠加时逐层损失。
5. **所有实验都应表述为对实现假设和理论预测的验证。** 它们不能替代对任意输入、任意页面和任意执行的形式化证明。
