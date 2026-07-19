# AlgoTutorGen 实验下一步实施计划

> **给后续 agentic workers：** 执行本文档时，必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项推进。本文使用 checkbox（`- [ ]`）记录执行状态。

**目标：** 不重做系统架构，把当前 AlgoLab 系统推进到可写论文实验结果的阶段：补齐交互指标、benchmark 运行、baseline、ablation、浏览器交互证据和论文表格。

**系统判断：** 当前系统已经基本满足 `plan.md` 对“interactive learning environment”的要求。下一步的重点不是再做一轮大 UI/架构改造，而是重新生成当前版本 artifact，量化交互覆盖，跑实验对比，并把结果组织成论文证据。

**技术栈：** Python 统一使用 `/ssd1/liaokunpeng/agent-py310-cu/bin/python3`；核心对象是 Pydantic `BuildArtifact` / `SceneGraph`；主实验脚本包括 `scripts/run_llm_benchmark.py`、direct HTML baseline、process validator / SceneGraph ablation、`scripts/audit_llm_teaching_pages.py`、报告合并和 reproducibility package 脚本；浏览器审计通过 `scripts/run_browser_smoke_container.sh` 跑。

---

## 1. 当前结论

当前系统应该按下面这个方向描述：

> Verifiable LLM generation of interactive algorithm learning environments.

不要把它写成“算法可视化 demo”。`plan.md` 的核心升级是从可验证 trace / visualization 进入可验证 learning environment；当前系统的主链路已经对得上：

- LLM 生成结构化的 solve / trace / verifier / teaching 数据。
- 沙箱执行和 validator 负责把输出变成可检查的 `BuildArtifact`。
- `SceneGraph` 把算法 trace 编译成前端可消费的场景。
- 固定 HTML runtime 渲染学习页面和交互检查点。
- 交互反馈、hint、answer reveal、learning log 来自结构化数据，而不是前端临时编造。

当前系统已经比 `plan.md` 的最低交互要求更强：

- 已支持 `choice`、`input`、`judge` 三类 prediction checkpoint。
- 已支持即时正确/错误反馈、wrong-answer explanation、hint、reveal answer。
- 已支持 learning log 和 learning-log export。
- 当前 `teaching_enricher.py` 的目标不是“每题随便 3 个交互”，而是覆盖关键学习帧：通常至少 3 个，最多关注 8 个高价值关键帧。

真正缺口是实验证据，而不是能力本身：

- 旧保存结果 `output/component_ablation_teaching_15cases/full` 中，15 个 artifact 总交互帧为 35，平均 2.33 个/题。
- 按当前 `teaching_enricher.py` 的 key-frame 目标，同一批 15 题大约需要 104 个交互帧。
- 因此不能直接用旧 artifact 证明当前系统交互能力；需要用当前 prompt / pipeline 重新生成，并做交互覆盖统计。

论文贡献建议写成三类：

- **系统贡献：** verified trace-to-tutor pipeline。
- **benchmark 贡献：** interaction-oriented AlgoTutorGen benchmark。
- **评估贡献：** generation success、interaction coverage、browser interaction reachability、baseline 和 ablation。

---

## 2. 实验指标

下一步实验至少报告三层交互指标：

| 层级 | 通过标准 | 理由 |
|---|---:|---|
| `plan.md` baseline | 每个 release case 至少 3 个 interaction checkpoints | 对齐 `plan.md` 第 3.C 节的交互要求 |
| 当前系统目标 | 每个 release case 至少 `max(3, min(key_learning_frames, 8))` 个关键交互 | 对齐当前 `TEACHING_SYSTEM_PROMPT`，证明系统强于 plan 的最低要求 |
| 浏览器交互目标 | desktop 审计能到达 checkpoint、提交答案、显示 feedback、更新 learning log、导出证据；mobile 不出现明显布局破坏 | 证明交互是真实可用的，不只是 JSON 字段存在 |

第一张论文实验表建议包含：

- total cases
- passed cases
- final answer accuracy
- strict release gate pass rate
- average interaction checkpoints per case
- percentage of cases with at least 3 interactions
- key learning interaction coverage
- answer-frame checkpoint rate
- browser interaction pass rate
- average repair rounds
- token / time cost

---

## 3. 任务 1：固定论文叙事和证据范围

**相关文件：**

- 阅读：`plan.md`
- 阅读：`README.md`
- 阅读：`docs/00_PRODUCT_NORTH_STAR.md`
- 阅读：`docs/01_FINAL_PAGE_SPEC.md`
- 阅读：`docs/06_EVALUATION_AND_BENCHMARK.md`
- 阅读：`docs/05_VISUAL_PRIMITIVES_AND_PATTERNS.md`
- 输出：`output/experiments/algotutorgen_next/narrative_scope.md`

- [ ] **步骤 1：写入一句话论文定位**

创建 `output/experiments/algotutorgen_next/narrative_scope.md`：

```markdown
# AlgoTutorGen Narrative Scope

AlgoTutorGen 研究如何用 LLM 生成可验证的交互式算法学习环境。LLM 负责生成结构化算法语义、执行轨迹和教学检查点；确定性的执行、验证、SceneGraph 编译和固定 HTML runtime 负责产出可运行、可检查、可交互的学习页面。当前系统已经支持交互检查点、grounded feedback、hints 和 learning logs；下一阶段的核心任务是在 benchmark 规模上评估这些能力。
```

- [ ] **步骤 2：运行当前轻量质量门禁**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

期望输出包含：

```text
quality_checks: PASS
```

- [ ] **步骤 3：记录当前 benchmark 规模**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY'
from collections import Counter
from benchmark.cases import benchmark_cases

cases = benchmark_cases()
print("cases", len(cases))
print("samples", sum(len(c.samples) for c in cases))
print("gate_layers", dict(Counter(c.gate_layer for c in cases)))
print("families", len(Counter(c.family_id for c in cases)))
PY
```

当前预期形态：

```text
cases 71
samples 259
gate_layers {'family_core': 62, 'expansion': 9}
families 23
```

**理由：** 先把论文叙事固定住，避免后续又退回“可视化 demo 很酷但研究问题不清楚”的表达。当前 benchmark 已经足够支撑第一轮技术实验，不必先把数据集扩到 200-500。

---

## 4. 任务 2：重新生成 15 题交互增强 pilot

**相关文件：**

- 输入：`benchmark/cases.py`
- 输出目录：`output/experiments/algotutorgen_pilot_15/algolab_full`
- 主报告：`output/experiments/algotutorgen_pilot_15/algolab_full/llm_benchmark_report.json`
- 交互统计：`output/experiments/algotutorgen_pilot_15/algolab_full/interaction_coverage_summary.json`

- [ ] **步骤 1：用当前 teaching enrichment 重跑 15 题**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py \
  --output-dir output/experiments/algotutorgen_pilot_15/algolab_full \
  --condition algolab_full \
  --case house_robber \
  --case binary_search \
  --case two_pointer_pair_sum \
  --case unique_paths \
  --case lcs_length \
  --case graph_bfs \
  --case dijkstra_shortest_path \
  --case kmp \
  --case trie_prefix_match_string \
  --case two_sum \
  --case insertion_sort \
  --case reverse_linked_list \
  --case merge_intervals \
  --case daily_temperatures \
  --case binary_tree_inorder \
  --sample 0 \
  --solutions 1 \
  --max-rounds 2 \
  --max-candidates 1 \
  --strict-warnings \
  --teaching-enrichment \
  --write-each \
  --concurrency 3 \
  --no-browser-smoke
```

期望产物：

```text
output/experiments/algotutorgen_pilot_15/algolab_full/llm_benchmark_report.json
output/experiments/algotutorgen_pilot_15/algolab_full/llm_<case>_0.json
output/experiments/algotutorgen_pilot_15/algolab_full/llm_<case>_0.html
```

- [ ] **步骤 2：统计生成 artifact 的交互覆盖**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY'
from pathlib import Path
import json
from algolab.schemas.validation import BuildArtifact
from algolab.generation.teaching_enricher import compute_interaction_coverage

root = Path("output/experiments/algotutorgen_pilot_15/algolab_full")
rows = []
for path in sorted(root.glob("llm_*.json")):
    if path.name == "llm_benchmark_report.json":
        continue
    artifact = BuildArtifact.model_validate_json(path.read_text(encoding="utf-8"))
    for variant in artifact.variants:
        scene = artifact.scenes[variant.id]
        cov = compute_interaction_coverage(variant.trace, scene)
        target = max(3, min(cov["key_learning_frames"], 8))
        rows.append({
            "case": path.stem,
            "variant": variant.id,
            "frames": cov["total_frames"],
            "interaction_frames": cov["interaction_frames"],
            "key_learning_frames": cov["key_learning_frames"],
            "key_learning_interaction_frames": cov["key_learning_interaction_frames"],
            "target_interactions": target,
            "plan_baseline_pass": cov["interaction_frames"] >= 3,
            "current_target_pass": cov["key_learning_interaction_frames"] >= target,
            "answer_frame_interaction_present": cov["answer_frame_interaction_present"],
        })

summary = {
    "total": len(rows),
    "plan_baseline_passed": sum(1 for row in rows if row["plan_baseline_pass"]),
    "current_target_passed": sum(1 for row in rows if row["current_target_pass"]),
    "total_interaction_frames": sum(row["interaction_frames"] for row in rows),
    "total_target_interactions": sum(row["target_interactions"] for row in rows),
    "answer_frame_interaction_cases": sum(1 for row in rows if row["answer_frame_interaction_present"]),
    "rows": rows,
}
out = root / "interaction_coverage_summary.json"
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY
```

最低验收：

```text
plan_baseline_passed == total
current_target_passed >= 12  # 15-case pilot 中至少 12 题达到当前系统目标
```

如果 `plan_baseline_passed < total`，先不要扩数据集；优先定位失败 case，再对失败 case 用 `--max-candidates 3` 重跑。

**理由：** 这一步直接验证你的判断：系统已经差不多了，缺的是当前版本实验结果。它也能区分“旧 artifact 交互不足”和“当前系统能力不足”。

---

## 5. 任务 3：运行浏览器交互审计

**相关文件：**

- 输入 manifest：`output/experiments/algotutorgen_pilot_15/browser_audit_manifest_input.json`
- 输出目录：`output/experiments/algotutorgen_pilot_15/browser_audit`
- 输出报告：`output/experiments/algotutorgen_pilot_15/browser_audit/browser_audit_manifest.json`
- 脚本：`scripts/audit_llm_teaching_pages.py`

- [ ] **步骤 1：构造浏览器审计 manifest**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY'
from pathlib import Path
import json
from algolab.schemas.validation import BuildArtifact

root = Path("output/experiments/algotutorgen_pilot_15/algolab_full")
rows = []
for path in sorted(root.glob("llm_*.json")):
    if path.name == "llm_benchmark_report.json":
        continue
    artifact = BuildArtifact.model_validate_json(path.read_text(encoding="utf-8"))
    frame_count = max(len(scene.frames) for scene in artifact.scenes.values())
    rows.append({
        "case_id": path.stem.removeprefix("llm_").removesuffix("_0"),
        "html": str(path.with_suffix(".html")),
        "json": str(path),
        "frame_count": frame_count,
    })

manifest = {"kind": "algotutorgen-browser-audit-input", "rows": rows}
out = Path("output/experiments/algotutorgen_pilot_15/browser_audit_manifest_input.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(out)
print("rows", len(rows))
PY
```

期望输出：

```text
output/experiments/algotutorgen_pilot_15/browser_audit_manifest_input.json
rows 15
```

- [ ] **步骤 2：通过容器跑 Playwright 审计**

```bash
bash scripts/run_browser_smoke_container.sh \
  python scripts/audit_llm_teaching_pages.py \
  --manifest output/experiments/algotutorgen_pilot_15/browser_audit_manifest_input.json \
  --output-dir output/experiments/algotutorgen_pilot_15/browser_audit \
  --strict-report output/experiments/algotutorgen_pilot_15/algolab_full/llm_benchmark_report.json
```

期望输出 JSON 包含：

```json
{
  "ok": true,
  "desktop_interaction_ok": true
}
```

期望文件：

```text
output/experiments/algotutorgen_pilot_15/browser_audit/browser_audit_manifest.json
```

**理由：** 论文不能只说 JSON 里有 interaction 字段，必须证明浏览器用户真的能看到 checkpoint、提交答案、得到反馈并留下 learning log。

---

## 6. 任务 4：从 pilot 扩到主技术 benchmark

**相关文件：**

- 输入：`benchmark/cases.py`
- 输入：`benchmark/unseen_family_cases.json`
- 输出目录：`output/experiments/algotutorgen_main`

- [ ] **步骤 1：在 family core 上每个 family 跑 1 题**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py \
  --output-dir output/experiments/algotutorgen_main/algolab_full_family_core \
  --condition algolab_full \
  --gate-layer family_core \
  --limit-per-family 1 \
  --sample 0 \
  --solutions 1 \
  --max-rounds 2 \
  --max-candidates 1 \
  --strict-warnings \
  --teaching-enrichment \
  --write-each \
  --concurrency 4 \
  --no-browser-smoke
```

验收标准：

```text
至少尝试 20 个 family-level cases。
第一次完整运行 strict release-ready pass rate 至少达到 70%。
```

- [ ] **步骤 2：运行 unseen-family evaluation**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py \
  --output-dir output/experiments/algotutorgen_main/algolab_full_unseen \
  --condition algolab_full \
  --case-set unseen \
  --limit-per-family 1 \
  --sample 0 \
  --solutions 1 \
  --max-rounds 2 \
  --max-candidates 1 \
  --strict-warnings \
  --teaching-enrichment \
  --write-each \
  --concurrency 4 \
  --no-browser-smoke
```

期望文件：

```text
output/experiments/algotutorgen_main/algolab_full_unseen/llm_benchmark_report.json
```

**理由：** `plan.md` 里建议长期构建 200-500 个任务，但眼下第一张论文结果表可以先基于当前 71-case benchmark、family-core 和 unseen case 做出来。是否扩数据集应该由第一轮结果决定。

---

## 7. 任务 5：运行 baseline 和 ablation

**相关文件：**

- 输出目录：`output/experiments/algotutorgen_baselines`
- 脚本：
  - `scripts/run_direct_html_baseline.py`
  - `scripts/run_no_process_validator_ablation.py`
  - `scripts/run_no_scenegraph_compiler_ablation.py`
  - `scripts/export_component_ablation_artifacts.py`

- [ ] **步骤 1：在 15 题 pilot 上跑 direct HTML baseline**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_direct_html_baseline.py \
  --output-dir output/experiments/algotutorgen_baselines/direct_html_pilot_15 \
  --case house_robber \
  --case binary_search \
  --case two_pointer_pair_sum \
  --case unique_paths \
  --case lcs_length \
  --case graph_bfs \
  --case dijkstra_shortest_path \
  --case kmp \
  --case trie_prefix_match_string \
  --case two_sum \
  --case insertion_sort \
  --case reverse_linked_list \
  --case merge_intervals \
  --case daily_temperatures \
  --case binary_tree_inorder \
  --sample 0 \
  --max-rounds 2 \
  --write-each \
  --concurrency 3 \
  --no-browser-smoke
```

期望文件：

```text
output/experiments/algotutorgen_baselines/direct_html_pilot_15/llm_benchmark_report.json
```

- [ ] **步骤 2：运行 no-process-validator ablation**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_no_process_validator_ablation.py \
  --output-dir output/experiments/algotutorgen_baselines/no_process_validator_pilot_15 \
  --case house_robber \
  --case binary_search \
  --case two_pointer_pair_sum \
  --case unique_paths \
  --case lcs_length \
  --case graph_bfs \
  --case dijkstra_shortest_path \
  --case kmp \
  --case trie_prefix_match_string \
  --case two_sum \
  --case insertion_sort \
  --case reverse_linked_list \
  --case merge_intervals \
  --case daily_temperatures \
  --case binary_tree_inorder \
  --sample 0 \
  --max-rounds 2 \
  --write-each \
  --concurrency 3 \
  --no-browser-smoke
```

期望文件：

```text
output/experiments/algotutorgen_baselines/no_process_validator_pilot_15/llm_benchmark_report.json
```

- [ ] **步骤 3：运行 no-SceneGraph-compiler ablation**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_no_scenegraph_compiler_ablation.py \
  --output-dir output/experiments/algotutorgen_baselines/no_scenegraph_compiler_pilot_15 \
  --case house_robber \
  --case binary_search \
  --case two_pointer_pair_sum \
  --case unique_paths \
  --case lcs_length \
  --case graph_bfs \
  --case dijkstra_shortest_path \
  --case kmp \
  --case trie_prefix_match_string \
  --case two_sum \
  --case insertion_sort \
  --case reverse_linked_list \
  --case merge_intervals \
  --case daily_temperatures \
  --case binary_tree_inorder \
  --sample 0 \
  --max-rounds 2 \
  --write-each \
  --concurrency 3 \
  --no-browser-smoke
```

期望文件：

```text
output/experiments/algotutorgen_baselines/no_scenegraph_compiler_pilot_15/llm_benchmark_report.json
```

- [ ] **步骤 4：从成功 AlgoLab artifact 导出 no-interaction component ablation**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/export_component_ablation_artifacts.py \
  --artifact-dir output/experiments/algotutorgen_pilot_15/algolab_full \
  --glob 'llm_*.json' \
  --output-dir output/experiments/algotutorgen_baselines/component_ablation_pilot_15 \
  --variant full \
  --variant no_interaction \
  --html
```

期望文件：

```text
output/experiments/algotutorgen_baselines/component_ablation_pilot_15/component_ablation_manifest.json
```

**理由：** 这一步回答 reviewer 最可能问的问题：为什么需要结构化 trace、validator、SceneGraph 和固定 runtime？主对比不是再做 UI，而是证明结构化可验证生成优于直接生成 HTML，且关键组件移除后会下降。

---

## 8. 任务 6：合并报告并生成论文表格

**相关文件：**

- 输出目录：`output/experiments/algotutorgen_tables`
- 脚本：
  - `scripts/merge_llm_reports.py`
  - `scripts/build_evaluation_manifest.py`
  - `scripts/build_evaluation_report.py`
  - `scripts/build_reproducibility_package.py`

- [ ] **步骤 1：合并主要 LLM reports**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/merge_llm_reports.py \
  --report algolab_full=output/experiments/algotutorgen_pilot_15/algolab_full/llm_benchmark_report.json \
  --report direct_html_baseline=output/experiments/algotutorgen_baselines/direct_html_pilot_15/llm_benchmark_report.json \
  --report no_process_validator=output/experiments/algotutorgen_baselines/no_process_validator_pilot_15/llm_benchmark_report.json \
  --report no_scenegraph_compiler=output/experiments/algotutorgen_baselines/no_scenegraph_compiler_pilot_15/llm_benchmark_report.json \
  --output-dir output/experiments/algotutorgen_tables/merged_reports
```

期望文件：

```text
output/experiments/algotutorgen_tables/merged_reports/llm_benchmark_report.json
```

- [ ] **步骤 2：构建 evaluation manifest**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_manifest.py \
  --output-dir output/experiments/algotutorgen_tables/evaluation
```

期望文件：

```text
output/experiments/algotutorgen_tables/evaluation/evaluation_manifest.json
```

- [ ] **步骤 3：构建 family release gate 报告**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/check_family_release_gate.py \
  --output-dir output/experiments/algotutorgen_tables/release_gate
```

期望文件：

```text
output/experiments/algotutorgen_tables/release_gate/family_release_gate.json
```

- [ ] **步骤 4：构建最终 evaluation report**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_evaluation_report.py \
  --output-dir output/experiments/algotutorgen_tables/evaluation \
  --manifest output/experiments/algotutorgen_tables/evaluation/evaluation_manifest.json \
  --llm-report output/experiments/algotutorgen_tables/merged_reports/llm_benchmark_report.json \
  --family-gate output/experiments/algotutorgen_tables/release_gate/family_release_gate.json
```

期望文件：

```text
output/experiments/algotutorgen_tables/evaluation/evaluation_report.json
output/experiments/algotutorgen_tables/evaluation/evaluation_report.md
output/experiments/algotutorgen_tables/evaluation/evaluation_condition_summary.csv
output/experiments/algotutorgen_tables/evaluation/evaluation_failure_types.csv
```

- [ ] **步骤 5：构建 reproducibility package**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_reproducibility_package.py \
  --output-dir output/experiments/algotutorgen_tables/reproducibility
```

期望文件：

```text
output/experiments/algotutorgen_tables/reproducibility/reproducibility_manifest.json
```

**理由：** `plan.md` 的重点是“benchmark + validator + interaction oracle 支撑论文”，这一步把实验输出整理成论文可引用的表格和报告。

---

## 9. 任务 7：根据结果决定是否扩充数据集

**相关文件：**

- 输入：`benchmark/cases.py`
- 输入：`benchmark/unseen_family_cases.json`
- 可能新增：`benchmark/algotutorgen_public_tasks.json`

- [ ] **步骤 1：检查 pilot 和 family-core 的结果缺口**

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("output/experiments/algotutorgen_tables/evaluation/evaluation_report.json").read_text(encoding="utf-8"))
print("dataset_summary", json.dumps(report.get("dataset_summary", {}), ensure_ascii=False, indent=2))
print("condition_summary", json.dumps(report.get("condition_summary", []), ensure_ascii=False, indent=2))
print("failure_type_summary", json.dumps(report.get("failure_type_summary", {}), ensure_ascii=False, indent=2))
PY
```

决策规则：

```text
如果 algolab_full 已经在至少 20 个 family 上有稳定结果，并且浏览器交互审计通过，先写第一版论文结果表，不急着扩数据。
如果某些 family 没有任何成功样例，则先给这些 family 各补 1-2 个 case，再声明 broad family coverage。
```

- [ ] **步骤 2：只扩缺失或薄弱 family**

扩充目标：

```text
只有当现有 71-case benchmark 无法支撑目标表格时，才新增 20-30 个 public/synthetic tasks。
内部实验可以使用 LeetCode-style tasks；公开 release 优先使用 synthetic/open-source 描述，避免版权和复现问题。
```

**理由：** 在第一张实验表出来前，不要把时间投入到 200-500 题大扩充。当前系统最需要的是证明“交互式学习环境生成”这条链路在现有 benchmark 上稳定成立。

---

## 10. 本阶段不做什么

- 不从头重写 HTML runtime。
- 不为了“interactive environment”这个措辞另起一个 React app。
- 不让 LLM 直接生成任意 HTML 进入主 AlgoLab release path。
- 不夸大当前 `process_validator.py` 的能力；如果它仍是轻量 placeholder，就不要声称已经有强 process-invariant validation。
- 不在技术 benchmark 表格出来前优先做人类用户研究。
- 不先扩到 200-500 题再开始跑结果。

---

## 11. 完成标准

本阶段完成时，至少应该有这些文件：

```text
output/experiments/algotutorgen_pilot_15/algolab_full/llm_benchmark_report.json
output/experiments/algotutorgen_pilot_15/algolab_full/interaction_coverage_summary.json
output/experiments/algotutorgen_pilot_15/browser_audit/browser_audit_manifest.json
output/experiments/algotutorgen_tables/merged_reports/llm_benchmark_report.json
output/experiments/algotutorgen_tables/evaluation/evaluation_report.json
output/experiments/algotutorgen_tables/evaluation/evaluation_report.md
```

最终总结需要能支撑下面这句话：

```text
AlgoLab 已经支持交互式算法学习环境。重新生成的 benchmark artifacts 满足 plan.md 中每题至少 3 个交互 checkpoint 的 baseline；浏览器审计确认用户可以提交答案、获得反馈并写入 learning log；baseline 和 ablation 量化了结构化 trace-to-SceneGraph 生成相对于 direct HTML 和组件移除的价值。
```

下一步执行顺序建议：

```text
任务 1 -> 任务 2 -> 任务 3 -> 任务 5 -> 任务 6 -> 任务 7
```

其中任务 4（family-core / unseen 主 benchmark）可以在 15-case pilot 和浏览器审计通过后并行推进。
