这三个实验正好形成一条完整证据链：

> 原子服务边界是否带来可靠性 → 在相近模型成本下优势是否仍存在 → 这种可靠性究竟保证什么、不保证什么。

| 实验 | 核心问题 | 新增成本 | 论文优先级 |
|---|---|---:|---:|
| Same-shell atomic-service ablation | 可靠性是否来自“状态更新与事件记录原子绑定” | 高，约 30M tokens 量级 | 最高 |
| Total token cost–reliability | 整页修复增加到相近成本后，能否追上 AlgoTutorGen | 低，优先复用日志 | 高 |
| Wrong-but-self-consistent solver audit | 忠实记录错误执行时，系统能否明确拒绝 | 很低，不需要 LLM | 中高 |

**实验一：Same-Shell Atomic-Service Ablation**

目的不是证明“交互更好”，而是隔离论文最关键的技术设计：服务调用同时完成状态更新和语义事件生成，是否比模型分别维护二者更可靠。现有 Service-only 消融测试的是提示指导，不是这个问题，[supplement.tex](/Users/liaokunpeng/Documents/algorithm/ailab-agent/latex/supplement.tex:414)。

两个条件：

- `Atomic`：当前 `TraceSession`。一次服务调用同时更新 canonical state 并产生 typed event。
- `Decoupled`：提供受控的两个接口，模型先调用状态更新，再显式调用事件记录。仍禁止任意修改受保护状态。

两边必须完全冻结：200 个任务及输入、DeepSeek-V4-Pro、温度、oracle 信息、family/strategy guidance、两个候选和两个修复轮次、编译器、SceneGraph、固定 shell、教学层、浏览器审计。

执行方式：

1. 先选每个算法家族一个任务，共 23 个任务做工程预试。
2. 预试只修接口错误，不根据结果调整假设。
3. 冻结代码、提示词和判定标准后，两个条件交错运行 Full-200。
4. 同时报告 Full-200 和排除预试任务后的敏感性结果。

主指标是 `Machine OK`。机制指标包括 final generation pass、state/event mismatch、unlogged mutation、prefix replay failure、修复次数、tokens/valid tutor 和 time-to-valid。事件数量只能描述，统计单位必须是任务，避免把同一任务的多个事件当成独立样本。

统计采用精确 McNemar 检验、10,000 次配对 bootstrap 置信区间；多个次要二元指标使用 Holm 校正。可以沿用论文已有的 `-3 pp` 非劣界限。

结果解释必须提前锁定：

- Atomic 的 `Machine OK` 更高且 mismatch 更少：支持原子耦合对可靠性的因果贡献。
- 最终可靠性非劣，但 Atomic 使用更少修复和 tokens：只能支持接口效率。
- 两者没有明显差异：不能把 atomic coupling 包装成主要贡献，应退回“validated execution record + fixed shell”的系统贡献。

**实验二：Total Token Cost–Reliability Curve**

目的是真正回答审稿人可能提出的问题：Direct HTML 失败，是因为结构不可靠，还是仅仅因为给它的模型预算更少？

对每个任务建立完整账本：

```text
TotalTokens(i, r)
= InitialDirectTokens(i)
+ RepairTokens(i, 1...r)
```

tokens 必须采用同一 API 口径，包括输入和输出；调用数、API latency 和本地编译时间分开报告。根据已保存的逐轮结果，重放不同 token cap，画出：

```text
x：总模型 tokens/task
y：Machine OK
```

AlgoTutorGen 应同时标两个点：

- selected-final：76.8k tokens/task；
- operational all-attempt：16.87M / 200，约 84.4k tokens/task。

公平性主比较建议用 84.4k，因为被丢弃的候选和失败尝试也是实际消耗。然后在 76.8k 做敏感性比较。

当前修复表只统计 repair tokens，[supplement.tex](/Users/liaokunpeng/Documents/algorithm/ailab-agent/latex/supplement.tex:955)。而且 BrowserRepair 的初始集是 106/200，不是主 Direct 的 98/200，所以不能直接把主 Direct 的 21.9k 与修复 tokens 拼接。必须找到同一批 106/200 初始页面的 API usage 日志。

如果精确日志存在，不需要任何新调用；如果只有提示词和响应，可以统一重新计数并标为 estimated；如果同批初始成本无法恢复，则必须重跑完整的 Direct + Repair 链路，不能把新初始调用与旧修复结果拼接。

统计上预先指定 84.4k 为主预算点，使用配对 bootstrap 和 McNemar；其他预算点作为曲线描述，不逐点做显著性检验。

结果解释：

- 相近甚至更高成本下仍明显低于 198/200：支持结构化链路在测试预算范围内更可靠。
- 更高成本才能追上：支持 token efficiency，但不是绝对能力优势。
- 相同或更低成本即可追上：不能再包装成本—可靠性优势，只能强调审计性和所有权边界。
- 即使成本匹配，也不能称为严格因果实验，因为两种方法承担的生成职责和工程组件不同。

**实验三：Wrong-but-Self-Consistent Solver Audit**

现有 fault injection 是在正确记录生成后篡改事件，因此会被 replay 检测。新实验要制造一种更难的情况：算法本身执行错了，但它对错误过程的记录完全一致。这正好验证论文所说的“trace fidelity 不等于 algorithm correctness”，见 [supplement.tex](/Users/liaokunpeng/Documents/algorithm/ailab-agent/latex/supplement.tex:653)。

选约 30 个任务，覆盖全部 23 个家族。每个任务注入两个确定性的源代码错误，目标得到约 60 个 applicable mutants：

- 将关键边界或比较符号改错；
- 省略一次 relaxation、更新或交换；
- 返回错误对象、索引或目标状态。

错误 solver 仍必须正常使用服务，不能直接篡改 trace。只保留在指定输入上确实改变 trusted oracle 输出、且程序能够正常执行的 mutation。应保存所有尝试及不适用数量，不能只报告筛选后的成功案例。

预期判定矩阵：

| 检查 | 原始 solver | 错误但自洽 solver |
|---|---:|---:|
| Same-execution binding | Pass | Pass |
| Prefix/final replay | Pass | Pass |
| Deterministic replay | Pass | Pass |
| Oracle agreement | Pass | Fail |
| Final ReleaseGate | Pass | Reject |

主要报告 applicable mutants 中的内部一致性通过率、oracle mismatch 率和 release rejection 率，并给出 Wilson 95% 区间。理想结果是三项均为 `60/60`；如果错误 solver 通过最终 release，应视为 correctness gate 缺陷和论文提交前的阻断问题。

这个实验只能证明：系统会忠实记录错误执行，并在存在 trusted oracle 时阻止发布。它不能证明系统能够发现所有算法错误，也不能覆盖没有 oracle 的开放任务。

建议实际执行顺序是：先做实验三，因为便宜且能快速检查 correctness gate；再整理实验二的历史日志；最后先跑实验一的 23-task pilot，再决定是否投入 Full-200。论文中则按实验一、实验二、实验三的逻辑顺序呈现。