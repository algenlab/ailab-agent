## 总体判断

这套实验**已经足以支撑一篇以“系统可靠性、可验证生成、交互功能”为主线的论文**。你现在已经有：

* 200 题主实验和配对显著性；
* Direct、WebGen-Agent、HTMLCure 外部 baseline；
* 5 个 full-200 消融；
* 2,400 个 fault injection；
* 646-sample 重放；
* 2 个 judge × 2 种顺序稳健性；
* 视觉、成本和传统系统能力边界。

所以不需要再无止境增加通用网页 Agent 或传统可视化器。现在真正值得补的是几个**会影响核心结论可信度的实验缺口**。

---

# 一、投稿前最建议补的 4 项

## 1. 校准你们的黑盒评测器

### 为什么这是当前最大风险之一

Stage1 使用固定 Runtime，按钮、答案、日志和反馈结构高度统一；Direct、WebGen-Agent 和 HTMLCure 的 UI 结构则更加自由。

审稿人很可能质疑：

> AlgoTutorGen 的 99% 是否部分来自评测器更容易识别自己的固定 Runtime，而外部系统虽然实现了等价功能，却因为按钮命名、DOM 结构或交互路径不同而被判失败？

MiniAppBench 明确指出，固定 click script 对开放式网页可能覆盖不足，因为多个不同 UI 都可能正确实现同一个需求；I-WebGenBench 则通过语义动作与 DOM mutation 区分“成功加载”和“真正发生交互”。([arXiv][1])

### 最小实验

抽取 **30 个分层任务**，覆盖：

* 23 个算法族；
* 四种方法：Stage1、Direct、WebGen-Agent、HTMLCure；
* 每种方法的 pass 和 fail；
* 不同交互类型：choice、input、judge。

总计约：

```text
30 tasks × 4 methods = 120 pages
```

由两名不知道方法名称的标注者手动执行九项功能，判断：

* 页面实际是否存在对应功能；
* 自动评测是否误判；
* 功能是否只是换了一种 UI 表达方式。

最后报告：

```text
Machine evaluator precision / recall / F1
False-positive rate
False-negative rate
Inter-rater agreement
按方法分别统计
```

这个实验很便宜，但对外部 baseline 的可信度提升非常大。

---

## 2. 增加真正等预算的 Direct + 浏览器反馈修复

### 当前问题

Stage1 最终平均每题约：

```text
5.33 calls
76.8k tokens
```

Direct 只有：

```text
1.11 calls
21.9k tokens
```

虽然已经加入 WebGen-Agent 和 HTMLCure，但它们同时改变了：

* Agent 框架；
* 修复策略；
* 输入格式；
* 运行环境；
* 外部依赖约束。

因此它们不能完全回答最直接的问题：

> 给 Direct HTML 与 Stage1 一样多的模型调用和 token，再让它根据浏览器错误不断修，能否接近 99%？

### 推荐 baseline

设置一个：

```text
Direct-BrowserRepair-5
```

流程为：

```text
首次 Direct HTML
→ Playwright 加载
→ 收集 console/pageerror、截图、DOM 摘要
→ LLM 修复
→ 最多重复 4 次
```

控制条件：

* 与 Stage1 使用同一个生成模型；
* 最多 5 次调用；
* token 上限约 80k；
* 严格禁止外部依赖；
* 修复器只能看到通用浏览器反馈；
* 不能看到最终测试 selector 或具体哪项隐藏指标失败。

最好同时画一条预算曲线：

```text
1 call → 2 calls → 3 calls → 5 calls
```

纵轴为 Machine OK，横轴为 calls、tokens 或生成时间。

这是最强的公平性实验。即使该 baseline 从 49% 提高到 75%，只要仍明显低于 99%，论文的架构结论会更硬。

---

## 3. 增加“保持最终功能不变”的非退化消融

目前这些消融：

```text
No interaction → 0/200
No SceneGraph compiler → 0/200
```

能够证明这些组件是完整 contract 的必要组成，但**不能很好地隔离它们的独立贡献**。因为评价指标本身要求交互网页；把交互或网页编译器直接删除后得 0，几乎是定义决定的结果。

建议至少增加下面两个中的一个，最好两个都做。

### 消融 A：Direct-to-SceneGraph

```text
Problem
→ LLM 直接生成 SceneGraph
→ 固定 Runtime
```

去掉：

* 可执行 solver；
* SemanticTrace 程序；
* result/trace/process gate；
* 多候选交叉校验。

但保留：

* 相同固定 Runtime；
* 相同最终 HTML 功能；
* 相同 Machine OK 评测。

它回答：

> 99% 是否主要来自固定 Runtime，而不是可执行语义轨迹和验证？

重点除了 Machine OK，还要检查：

* 最终答案一致性；
* 中间状态正确性；
* 反馈答案是否与算法状态一致。

### 消融 B：Verified Trace-to-LLM HTML

```text
已验证的 SemanticTrace
→ LLM 自由生成完整 HTML
```

保留验证过的算法事实，但移除：

* 确定性 SceneGraph compiler；
* 固定 Web Runtime。

它回答：

> 已验证的正确数据已经给到了，可靠性提升究竟来自数据正确，还是来自确定性渲染和固定交互实现？

这两个消融比“直接删掉 compiler”更有解释力。资源有限时，可以先在分层的 50 题上运行。

---

## 4. 修复 fault injection 暴露的明显盲区

当前 fault injection 很有价值，但这两个结果很扎眼：

```text
Event reorder：0/200 被拒绝
Missing SceneGraph reference：0/200 被拒绝
删除一个 event：仅 45/200 被拒绝
```

这很容易成为“verifiable”主张的攻击点。

### 建议先修两个便宜的确定性检查

#### Referential integrity

检查：

* SceneGraph 引用的 trace event 必须存在；
* interaction checkpoint 引用的 frame/event 必须存在；
* target、dependency、object ID 必须可解析；
* 不允许悬空引用。

#### Dependency-aware event ordering

不要简单要求事件永远不能换序，而是检查：

* step 连续性；
* `deps` 的拓扑顺序；
* `before` 必须对应前序状态；
* create 必须早于 set/move/link；
* push/pop、enter/exit 等操作满足基本状态机约束。

修复后重新跑：

```text
200 clean controls
2,400 fault injections
```

最好再增加一个小型的**独立 trace correctness audit**：

* 分层选择 30–50 个任务；
* 由独立参考实现或两名算法人员检查关键帧；
* 每题抽查初始帧、中间关键帧和终止帧；
* 统计 critical semantic error rate。

因为现有 gate 主要证明内部一致性，不等于逐步算法轨迹经过了独立证明。

---

# 二、很推荐，但可以根据算力决定

## 5. 第二生成模型实验

现在第二个模型只用于 judge 稳健性，主页面生成仍只有 DeepSeek-V4-Pro。

建议用第二个代码能力较强的模型，在分层的 **50 个任务**上运行：

| 方法           | 模型 A | 模型 B |
| ------------ | ---: | ---: |
| AlgoTutorGen |   已有 |   新增 |
| Direct HTML  |   已有 |   新增 |

主要看：

```text
架构增益是否跨模型保留
Stage1 - Direct 的差值
主运行成功率
repair 次数
Machine OK
tokens
```

不一定需要再跑完整 200。50 题覆盖 23 个算法族，已经能回答“是不是只对 DeepSeek prompt 特别有效”。

---

## 6. 真正的 held-out task 泛化

646-sample replay 很有必要，但它测试的是：

> 同一个已生成 solver/tracker，在同一道题的其他输入上能否工作。

它不是：

> 系统能否为从未见过的新题生成可靠环境。

建议另外准备约 **30–50 道未参与系统开发的新任务**：

* 不与原 200 题共享 case template；
* 最好来自独立来源；
* 至少包含部分原 benchmark 中较少见的算法结构；
* 在运行前冻结题目、输入和 expected。

只需要比较 Stage1 和 Direct，不必把全部外部 baseline 再跑一次。

这一项对“benchmark 是否针对系统定制”的质疑很有效。

---

## 7. 长轨迹与大输入的可扩展性实验

现在 646-sample replay 报告了结果正确率，但没有展示页面随轨迹变长时是否仍然可用。

建议选 15–20 个有自然规模参数的任务，例如：

* 排序；
* 图遍历；
* 动态规划；
* 字符串匹配；
* 树操作；
* 最短路。

每题构造：

```text
small / medium / large
```

报告：

* trace event 数；
* SceneGraph frame 数；
* HTML 文件大小；
* 页面加载时间；
* 首次可交互时间；
* 单步切换延迟；
* 浏览器内存；
* 是否发生视觉拥挤或不可读。

LongWebBench 的近期结果也强调，网页变长后结构质量和多步交互可靠性会下降，不能只看单截图或短页面。([arXiv][2])

---

# 三、人类评测是否必须

## 偏系统、NLP、软件工程投稿

不必立即做学生学习实验。

但建议至少做一个：

```text
3 位算法或教育技术评审者
× 30 个配对任务
```

评价：

* 中间步骤事实正确性；
* 讲解是否与当前状态一致；
* hint 是否有效；
* 错误反馈是否具有教学意义；
* 页面是否容易操作。

你现在虽然完成了两个模型和换序评审，但 WebDevJudge 的结果表明，网页质量上的 LLM judge 与人类专家仍存在明显差距；EduIllustrate 也通过 20 位专家发现，LLM 对客观维度较可靠，但主观视觉评价仍有限。([arXiv][3])

## 偏 AIED、EDM、CHI、教育技术投稿

至少需要一个小型用户实验，否则“学习环境”的贡献会显得只停留在功能层面。

最小可以是：

```text
20–30 名有基础编程经验的学生
AlgoTutorGen vs Direct
任务完成率
完成时间
预测题正确率
SUS 或易用性问卷
主观认知负荷
```

没有学生实验也能投稿，但标题、摘要和 claim 必须继续保持现在这种边界，不写“改善学习效果”。

---

# 四、HTMLCure 结果建议重新呈现

当前 HTMLCure strict 为 40/200，但 126 次接受改写中有 125 次引入 Google Fonts。这个结果主要混合了两类失败：

1. 教学网页功能失败；
2. 不符合 self-contained packaging 要求。

因此不建议只在主表中突出：

```text
HTMLCure = 20%
```

更公平的展示是拆成两列：

| 方法       | Functional Machine OK | Self-contained compliance | Strict joint pass |
| -------- | --------------------: | ------------------------: | ----------------: |
| HTMLCure |                     … |                         … |            40/200 |

或者再跑一版：

```text
HTMLCure-NoExternal
```

在 prompt 中明确禁止 CDN、Google Fonts、外部 JS/CSS，或者确定性删除外部字体引用后再审计。

你们现在的 external-blocked sensitivity 为 91/200，并且相对 Direct 的变化不显著，这实际上是更稳妥的结论：

> HTMLCure 没有稳定改善 Direct，而不是简单地说 HTMLCure 只有 20%。

---

# 五、不建议继续花时间的实验

这些现在可以停了：

* **继续找更多通用网页 Agent**：匹配完整 tutoring contract 的公开系统已经很少，再增加只会带来适配争议。
* **继续增加传统可视化器**：它们是人工模板和窄能力系统，不适合 full-200 排名。
* **继续增加 LLM judge 数量**：你已有 2 模型 × 2 顺序，边际价值很低。
* **继续增加 Naps/TRAKLA2 派生指标**：它们来自同一批机器行为，不会提供独立证据。
* **为了 0.05 强行扩大 no-repair 实验**：`p=0.0625` 如实报告即可，没必要为了显著性追样本。

---

# 最终优先顺序

投稿时间紧时，按这个顺序做：

1. **机器评测器的人类校准**
2. **同模型、同预算的 Direct-BrowserRepair-5**
3. **Direct-to-SceneGraph 或 VerifiedTrace-to-LLM-HTML 非退化消融**
4. **修复 dangling reference 和 dependency order，并重跑 fault injection**
5. 第二生成模型的 50 题实验
6. held-out 新任务
7. 长轨迹性能和人类教育评测

前四项完成后，实验链条就相当完整了：既证明不是评测器偏置，也不是计算预算优势，还能真正拆分“验证、结构化 IR、确定性 Runtime”各自的作用。

[1]: https://arxiv.org/html/2603.09652v3 "MiniAppBench: Evaluating the Shift from Text to Interactive HTML Responses in LLM-Powered Assistants"
[2]: https://arxiv.org/abs/2606.17727 "[2606.17727] LongWebBench: Evaluating Structural and Functional Webpage Generation in Long-Horizon Settings"
[3]: https://arxiv.org/html/2510.18560v3 "WebDevJudge: Evaluating (M)LLMs as Critiques for Web Development Quality"
