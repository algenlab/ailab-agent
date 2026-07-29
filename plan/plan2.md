实验怎么做
建议按以下顺序执行。
P0-1：Full-200 服务组合审计
不调用模型，直接分析冻结的 200 个 selected-final artifact。
统计：
每题、每个 variant 使用的不同服务数。
每个服务覆盖的任务、算法族和宏观算法组。
服务共现矩阵。
多服务任务比例。
是否出现目录外服务。
code_line=1 比例、单行支配比例和 answer-event 返回行匹配率。
输出：
service_usage_per_case.csv
service_reuse_matrix.csv
service_cooccurrence.csv
source_line_diagnostics.csv
service_usage_summary.json
比较有说服力的结果是：绝大多数成功任务不需要新增服务实现，并且至少 5–6 个服务能跨多个算法组复用。
P0-2：提示词配对消融
拉取：https://github.com/algenlab/ALGOGEN-lab.git。这是之前的工作，需要获取这个工作的提示词做消融实验
当前 run_llm_benchmark.py 的 --condition 只记录标签，并不会真正改变提示词，不能直接拿它做消融。实验前需要增加一个很小的 --prompt-profile 选择器：
hybrid_current：当前提示词。
service_only：保留完整服务 API、输出 schema 和中性组合示例，删除高频算法族模板和数位 DP 特例。
family_routed：可选；在相同提示词长度下加入当前任务对应的一个算法族模板。
先跑 60 题分层 pilot，再跑 Full-200。所有条件固定：
DeepSeek-V4-Pro。
temperature 0.2。
sample index 0。
2 solution variants。
2 candidates。
每个 candidate 最多 2 repair rounds。
32,768 output tokens。
相同题目顺序、oracle、timeout 和并发设置。
不允许只对某个条件做额外最终补跑。
指标：
first-pass specification validity。
final generation pass。
九项 Machine OK。
unknown DSL call。
服务数量与跨族复用。
calls、tokens、latency。
source-line collapse。
统计使用 paired bootstrap、exact McNemar，并对多项比较做 Holm 校正。核心判据是：
service_only − hybrid_current 的 Machine OK 95% CI 下界不低于 −3 个百分点。

若通过，可以较强地说服务接口不依赖显式算法族模板也能保持可靠性；若下降超过 3 pp，则保留“服务组合接口”贡献，但不能声称算法族指导不重要。
P0-3：PVCR ownership audit
针对全部 200 对 Verified View / Creative View，在相同 variant、frame 和教学操作状态下比较：
code panel
timeline
explanation
interaction
feedback
answer
learning log
canonical artifact state
比较时排除 creative-stage-host 子树。预期只有该子树可以不同。
再选择 20 个 artifact，分别注入：
page-level HTML
reserved shell ID
external URL
renderer exception
非法模板/script 结构
检查是否全部被 sanitizer 拒绝或回退到 Verified View。理想结果是：
200/200 页的 shell projection 完全一致。
所有非法资产均被拒绝或安全回退。
这项实验最直接回应“PVCR 主要依靠提示词”的疑问，同时又不把系统包装成安全沙箱。
P0-4：Source-to-trace 对齐审计
当前 23 案例中，35% 事件使用 code_line=1，且有 8 个 variant 全部映射到第一行，因此这项不能跳过。
建议：
自动审计全部 200 题。
分层抽取 40 题。
两位评审者独立判断关键事件属于：exact
semantically adjacent
wrong
no source counterpart

报告正确率、关键错误率和评审一致性。只有在 exact+adjacent 的置信区间下界达到约 90%、关键错误不超过 5% 时，才使用较强的“source-aligned trace”表述。
P1：人工校准视觉评价
从五种方法中抽取 30 题，共 150 个匿名页面，由两名评审者按照当前四维 rubric 打分。报告：
人类与 VLM 分数相关性。
All ≥ 3 阈值一致率。
PVCR 与各基线的配对偏好。
评审者间一致性。
如果暂时没有人力，这项可以继续留在 limitation，不阻塞前四项。
你完成后发给我的结果
优先给我以下文件：
service_usage_summary.json
两个或三个 prompt profile 的 llm_benchmark_report.json
prompt_ablation_paired_statistics.json
shell_ownership_audit.json
source_line_diagnostics.csv
人工标注文件（如果完成）