# AAAI 实验指标评估方案审查与缺口清单

本文档是历史方法论审查，不是当前结果报告；已完成实验及已关闭缺口统一见 `docs/EXPERIMENT_RESULTS.md`。

## 0. 文档定位

本文档是对 `docs/14_AAAI_EXPERIMENT_METRICS_AND_PROTOCOL.md`（以下简称 doc14）的**方法论审查**，目标是回答一个问题：

> doc14 定义的指标与评估协议，作为一篇 correctness 论文的证据体系，是否站得住？

它**不替代** doc14，而是给 doc14 打补丁。结论与改法发生冲突时，本文档作为 doc14 的修订意见，最终需回写进 doc14 对应章节。

审查基于对真实产物的核对，而非纸面：

- `output/aaai/stage1_final/reports/llm_benchmark_report_effective_71_71.json` 与未合并的 `llm_benchmark_report.json`
- `output/aaai/stage1_final/effective_71_artifacts/*.json`（71 份逐 case artifact）
- `benchmark/unseen_family_cases.json`
- `tests/`、`scripts/` 全量扫描（确认是否存在某类测试）
- `SYSTEM_OVERVIEW.md` 的系统边界声明

所有「我查到」均指上述真实文件，下文标注证据。

## 1. 一句话判断

指标**框架**合理（机器 gate 优先级、Stage1/Stage2 分离、裁判不进 correctness gate、强制分子分母都对），但**作为 correctness 论文存在两个会被审稿人直接打穿的洞**：

1. 整个体系只测「系统通过率」，从不测「gate 会不会拒绝错误产物」（soundness 缺失）——而这条 doc14 的 R1–R5 风险清单里**没有**。
2. `answer_correctness_ok` 把「自一致」证据和「独立验证」证据混在一个合取里，让自一致冒充了答案正确性的独立证据。

这两条不补，`71/71` 在审稿人眼里仍是「自建 benchmark 自己盖章」。其余为指标定义循环、测量工具粒度不足、Stage2 指标 override 等高/中危问题。

## 2. 严重度总表

| 编号 | 问题 | 严重度 | 性质 | doc14 是否已覆盖 |
|---|---|---|---|---|
| #1 | 只测 pass rate，不测 gate soundness（误接受率） | 致命 | 缺失实验 | 否 |
| #2 | `answer_correctness_ok` 混淆自一致与独立验证 | 致命 | 指标定义 | 部分（§17 提了独立性，但指标未拆） |
| #3 | `trace_replay_ok` 可能是循环验证 | 高 | 指标定义 | 否（§5.4 未澄清独立重执行） |
| #4 | 细粒度指标定义了但报告没产出到该粒度 | 高 | 测量工具缺口 | 否 |
| #5 | Stage2 strict 指标被人工 100% override | 高 | 指标诚信 | 部分（§4.2 写了人工复审，但未当分类器报） |
| #6 | unseen split 名不副实（全是 seen family 子集） | 高 | claim 与数据不符 | 否（§8 暗示 family 级泛化） |
| #7 | `multi_solution_match` 进公式却从未触发 | 中 | 死指标 | 否 |
| #8 | 统计检验打在饱和的 final release 上会退化 | 中 | 统计方法 | 部分（§11 未区分饱和指标） |

---

## 3. 致命级问题

### #1 整个指标体系只测「系统通过率」，从不测「gate 的可靠性」

这是最大的洞。

**问题**：doc14 §5 的所有核心指标——`answer_correctness_ok`、`trace_replay_ok`、`final_release_pass_rate`、各层 pass_rate——全部是「pass rate」（系统接受了多少）。但 `71/71` 有两种互斥解释，现有证据无法区分：

- (A) gate 严格 + LLM 强 → 真结论
- (B) gate 宽松，几乎什么都盖章放行 → 假结论

**证据**：扫描 `tests/` 和 `scripts/` 全量，**没有任何 fault-injection / mutation 测试**证明「喂一个故意错误的 solver/trace，gate 会拒绝它」。release_gate 在 71/71 上全是 `release_ready=true, blocking_reasons=[]`，但没有任何「应当为 false」的对照样本。

**审稿人必问**：你的 gate 的误接受率（false-accept rate）是多少？一个永远返回 pass 的 gate 也能拿到 71/71。

**改法**：新增一节「Gate Soundness / 受控错误注入」实验。

- 从已通过的 71 个 artifact 出发，注入受控错误，构造**应当被拒绝**的负样本：
  - 篡改 `solve` 返回值（答案错）。
  - 篡改 `trace.result`，使其与 solve 不一致。
  - 删除关键依赖步 / 错位 `before`/`after`/`state`。
  - 让 trace 末值与 expected 不符。
- 指标：`gate_rejection_rate = 被拒绝的负样本数 / 注入的负样本数`，按错误类型分桶（answer-level / trace-level / structural）。
- 解释：注入 N 个错误、gate 拦住 N−k 个，这个 `k`（漏网数）就是 gate 可信度的硬数字。

**优先级**：高于跨模型与 unseen。这是把 100% 从「可疑」变成「可信」的唯一硬证据，应作为 P0。

### #2 `answer_correctness_ok` 把「自一致」与「独立验证」混进同一个合取

**问题**：doc14 §5.3 的公式

```text
answer_correctness_ok =
  solve_ok AND answer_match AND trace_result_match
  AND (verifier_available == false OR verifier_match)
  AND (multi_solution_applicable == false OR multi_solution_match)
```

看着很严，但各合取项**对生成端的独立性差异巨大**，混在一起会让弱证据冒充强证据：

- `answer_match` = solve 结果 vs `expected`。`expected` 是 frozen benchmark 外部固定的，**这是唯一真正独立于生成端的证据**。证据：71/71 都有非空 expected。
- `trace_result_match` = trace.result vs solve result。两者**都是同一个 LLM variant 写的**，可以一起错。它证明 trace 忠实于 solve，**不证明答案正确**，却被放进 correctness 合取。
- `verifier_match` = LLM 生成的 verifier。证据：71 份 artifact 中**只有 61 份有 `verifier_result`**；且 verifier 与 solver 同源，可能同错（SYSTEM_OVERVIEW §17 自己承认无法保证 verifier 独立）。

**改法**：§5.3 必须把指标显式分两类标注：

- **independent-of-generation**（强）：`answer_match`（vs 外部 expected）。
- **self-consistency**（弱，证明忠实/无内部矛盾）：`trace_result_match`、LLM `verifier_match`。

论文 correctness 主叙事应表述为「与外部固定 expected 一致 + 多层自一致交叉校验」，**不得**让 `trace_result_match` 假装提供答案正确性的独立证据。

**附带发现（等价判定口径）**：`articulation_bridges` case 的 expected bridges 是 `[["D","E"],["A","B"]]`、verifier 是 `[["A","B"],["D","E"]]`，顺序不同仍判通过 → 说明 `results_equivalent`（`algolab/verification/result_normalizer.py`）做了无序/集合归一化。这个归一化口径必须在论文里写清楚，否则审稿人会质疑「等价」的定义边界（例如多解题里把不同合法解判为等价，是否掩盖了错误）。

## 4. 高危级问题

### #3 `trace_replay_ok` 被捧成 RQ2 核心，但可能是循环验证

**问题**：doc14 §5.4 把 `trace_replay_ok` 升级为 RQ2「过程正确性」主证据。但 executor（`algolab/runtime/executor.py`）在生成阶段**已经**检查了 `solve_result == trace.result`、schema 合法、step 连续、target 可解析。如果 replay 只是重新核对 trace 内部的 before/after/state 一致性，那是在**拿 DSL 自动生成的字段去对它自己**——没有引入任何新信息，是循环验证。

**改法**：要让 replay 成为强 RQ2 证据，它必须**独立重跑算法**，用一次全新执行得到的真实状态序列去比对 trace 声称的每步 `state`/`before`/`after`，而非只做 trace 内部一致性。doc14 §5.4 的检查列表（event.step==index、targets/deps 可解析、before/after 与上一状态一致……）大部分仍是「trace 内部自洽」，要明确补「独立重执行 + 逐步真实状态比对」。

否则 RQ2 的「过程忠实」结论只到「schema 合法 + 内部自洽 + 末值匹配」这个弱层级，指标命名与论文措辞都要相应降级（不能写成 process faithfulness proof）。

### #4 §5 定义了约 25 个细粒度指标，但报告没有产出到该粒度

**问题**：Table 1 有 11 行（generation / solve / answer / trace validity / trace replay / process / demo / scene / browser / first-try / final）。但核对 effective 报告，每个 case 的实际证据只有一句中文 `checks`（如 `"双指针：solve/trace/process/scene 均通过"`）加一个 5 字段的 `release_gate`（artifact/process/trace/visual/multi_solution _ready）。**细粒度指标目前是「定义了但没产出到那个粒度」**。

**后果**：Table 1 现在填不满。更危险的是，如果不先补测量工具就去跑 P1/P2 的跨模型、unseen、3 次重复，跑完仍然只有粗粒度 pass/fail，大实验等于白跑。

**改法**：在跑任何大实验**之前**，先验证 `scripts/build_evaluation_report.py` 能否从 artifact JSON 把这 11 层逐 case 拆出（artifact 里有 `validation.checks`、`validation.demo_readiness`、`scenes`、`release_gate`，理论上可拆）。若拆不出，这是必须先补的测量工具缺口。产出 `case_metrics.csv/json`，每行一个 case、每列一个层级的布尔/数值，才能支撑 Table 1 与 family-level 分析。

### #5 Stage2「strict 59/71，人工把 12 个全判误报」是指标诚信风险

**问题**：现状链路是——建了 strict auditor → 它报 12 个 fail → 作者人工复审把 12/12 全推翻 → 报「manual acceptable 71/71」。审稿人看到的逻辑是：**你建了一个指标，不喜欢它的结论，于是 100% override 了它**。证据：`output/aaai/aaai_run_summary.md` 明确写「The strict failures are primarily evaluator false positives... Human-acceptable Stage2 outcome: 71/71」。

**改法**：不要写「人工通过了 12 个」。把 strict auditor 当作一个**有测量误差的分类器**来报：

- 在一个 labeled 子集上报告 auditor 的 precision / recall（人工标注为 ground truth）。
- 主表写 `strict audit pass = 59/71` 并附 `auditor precision = X`，让读者自己判断 strict 与人工的差。
- 可辩护：`59/71 strict + auditor 校准报告`。不可辩护：`我们手工放行了全部 flagged`。

这与 doc14 §9.2-4「裁判可靠性自检」是同一原则，要落到 Stage2 auditor 上。

### #6 unseen split 名不副实——已确认 15 个 family 全是 seen 子集

**问题**：`benchmark/unseen_family_cases.json` 含 15 个 case、15 个 family，核对后**全部与 seen 的 23 个 family 重叠**，无一新族（unseen-only families = 空集）。所以它实际是「已知族内的留出新题（held-out tasks）」，**不是**跨族/跨结构泛化。但 doc14 §8 的指标叫 `family_generalization_pass_rate`、Table 4 暗示 family 级泛化。

**改法**：

- claim 如实改成「generalizes to unseen *tasks* within supported families」。
- 指标 `family_generalization_pass_rate` 改名 `held_out_task_pass_rate`，避免误导。
- 若要支撑更强的 family 级泛化结论，需另构造 seen 完全没有的算法族；但那可能要扩 renderer/DSL，成本单列评估，不要把同族新题包装成跨族。

## 5. 中危级问题

### #7 `multi_solution_match` 进了公式却从未被触发

71 个 case 全是 `solutions=1`，`multi_solution_ready` 全为 false，公式中 `(multi_solution_applicable == false OR multi_solution_match)` 恒真。它让公式看起来更严，实际是死代码。**改法**：要么跑一个多解 condition 真正触发它，要么论文显式标 N/A，不要让它假装提供了额外 rigor。

### #8 统计计划（3 次重复 + McNemar）打在饱和的 final release 上会退化

**问题**：doc14 §11 要求主条件重复 3 次报 `mean±std` 并用 McNemar 做条件比较。但若 full 每次都 71/71，方差恒为 0，`mean±std` 写成 `71±0`，McNemar 对两个都触顶的二元结果也无意义。

**改法**：把统计检验打在**真正有方差的量**上——`first_try_pass_rate`（已确认 61/71 = 85.9%，未饱和）和 token / duration 成本（用 Wilcoxon）。`final_release_pass_rate` 饱和时如实说明「饱和，方差为 0」，不要强行套统计检验制造严谨假象。

## 6. doc14 已经做对的部分（不要改动）

- 机器 gate > browser smoke > VLM 分数 的优先级；Stage1 correctness 与 Stage2 visual 严格分离；LLM/VLM 裁判永不进 correctness gate——三条都对，是本方案最扎实的地基。
- 强制分子分母、`--hide-expected` 公平 baseline、裁判与生成模型解耦——都对。
- R1–R5 风险自检写得好，方法论意识在线；唯一遗漏是本文档 #1（gate soundness）。

## 7. 落地优先级建议

P0（决定 correctness claim 能否成立，先做）：

1. #1 Gate soundness 受控错误注入实验（叙事命门）。
2. #4 验证并补 `build_evaluation_report.py` 的 11 层逐 case 产出（决定后续实验是否值得跑）。
3. #2 重写 §5.3，拆分 independent vs self-consistency 指标，写清等价归一化口径。

P1：

4. #3 明确 replay 为独立重执行，否则降级 RQ2 措辞。
5. #6 unseen 改名与如实重述。
6. #8 统计检验改打 first-try 率与成本。

P2：

7. #5 Stage2 auditor 当分类器报 precision/recall。
8. #7 multi_solution 触发或标 N/A。

## 8. 待用户确认的开放问题

- #1 错误注入实验的注入粒度与样本量（每类错误注入多少个）。
- #6 是否额外构造真正跨族 unseen（涉及 renderer/DSL 成本）。
- 整体推进范围（仅修文档 / P0 / P0+P1 / 全量），决定算力与 token 预算。
