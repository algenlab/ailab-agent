"""Browser smoke tests for generated HTML artifacts."""

from __future__ import annotations

from pathlib import Path

from algolab.renderer.export import save_html
from algolab.schemas.validation import BuildArtifact
from scripts.check_benchmark_html import check_html_paths
from scripts.build_demo_dashboard import build_dashboard
from tests.benchmark_regression import benchmark_coverage_artifact
from tests.fixtures import (
    algorithm_family_coverage_artifact,
    classic_coverage_artifact,
    fixture_artifact,
    golden_visual_artifact,
    golden_visual_matrix,
    phase17_visual_pattern_artifact,
    phase17_visual_pattern_matrix,
)


PHASE8_REQUIRED_DEMOS = ("unique_paths", "graph_bfs", "binary_search", "daily_temperatures")


def _check_page(page, path: Path, *, require_p1_layout: bool = True):
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(500)
    title = page.locator("#title").inner_text()
    counter = page.locator("#counter").inner_text()
    canvas_text = page.locator("#canvas").inner_text()
    assert title.strip(), f"{path}: title 为空"
    assert "/" in counter, f"{path}: counter 异常: {counter}"
    assert len(canvas_text.strip()) > 0, f"{path}: canvas 为空"
    if require_p1_layout:
        badges_text = page.locator("#badges").inner_text()
        for label in ("代码执行通过", "轨迹覆盖完整", "过程转移通过校验", "可视化对象绑定正确"):
            assert label in badges_text, f"{path}: 顶部可信度缺少人话标签 {label}: {badges_text}"
        for raw_label in ("artifact_ready", "trace_ready", "visual_ready", "release_ready"):
            assert raw_label not in badges_text, f"{path}: 顶部可信度泄露工程字段 {raw_label}"
        assert page.locator("#top-result").inner_text().strip(), f"{path}: 顶部输出为空"
        assert page.locator("#top-solution").inner_text().strip(), f"{path}: 顶部解法为空"
        assert page.locator("#problem-description").inner_text().strip(), f"{path}: 左侧题目描述为空"
        assert page.locator("#teaching-panel").count() == 1, f"{path}: 右侧讲解区缺失"
        assert page.locator("#teaching").inner_text().strip(), f"{path}: 主讲解区不应依赖 Debug Drawer"
        assert page.locator("#debug-drawer").count() == 1, f"{path}: Debug Drawer 缺失"
        assert not page.locator("#debug-drawer").evaluate("el => el.open"), f"{path}: Debug Drawer 应默认折叠"
        timeline = page.locator("#timeline")
        total = int(counter.split("/", 1)[1].strip())
        ticks = page.locator("#timeline .tick")
        assert timeline.get_attribute("aria-label") == "语义时间线", f"{path}: 语义时间线缺少 aria-label"
        assert ticks.count() == total, f"{path}: 时间线 tick 数量异常: {ticks.count()} != {total}"
        assert page.locator("#timeline .tick-label").count() == total, f"{path}: 时间线缺少阶段/关键帧标签"
        assert page.locator("#timeline .tick-op").count() == total, f"{path}: 时间线缺少操作降级标签"
        phase_count = ticks.evaluate_all("nodes => nodes.filter(node => node.dataset.phase && node.dataset.phase.trim()).length")
        assert phase_count == total, f"{path}: 时间线缺少稳定阶段标签: {phase_count} != {total}"
        first_tick_text = ticks.first.inner_text().strip()
        assert first_tick_text and not first_tick_text.isdigit(), f"{path}: 时间线不应只显示帧编号"
        if total > 1:
            ticks.nth(1).click()
            page.wait_for_timeout(80)
            assert page.locator("#counter").inner_text().startswith("2 /"), f"{path}: timeline 点击未同步 counter"
            assert page.locator("#range").evaluate("el => el.value") == "1", f"{path}: timeline 点击未同步 range"
            assert ticks.nth(1).evaluate("el => el.classList.contains('active')"), f"{path}: timeline 点击未同步 active tick"
            page.locator("#range").evaluate("(el) => { el.value = 0; el.dispatchEvent(new Event('input', { bubbles: true })); }")
            page.wait_for_timeout(80)
            assert page.locator("#counter").inner_text().startswith("1 /"), f"{path}: range 复位未同步 counter"
            assert ticks.first.evaluate("el => el.classList.contains('active')"), f"{path}: range 复位未同步 active tick"
        page.locator("#debug-drawer summary").click()
        page.wait_for_timeout(50)
        validation_text = page.locator("#debug-validation-json").inner_text()
        release_text = page.locator("#debug-release").inner_text()
        assert page.locator("#debug-evidence").inner_text().strip(), f"{path}: Debug Drawer 缺少 raw validation"
        assert '"checks"' in validation_text, f"{path}: Debug Drawer raw validation 缺少 checks JSON"
        assert '"release_gate"' in validation_text, f"{path}: Debug Drawer raw validation 缺少 release_gate JSON"
        assert '"release_ready"' in release_text, f"{path}: Debug Drawer 缺少 release gate JSON"
        assert page.locator("#debug-state").inner_text().strip(), f"{path}: Debug Drawer 缺少 raw state"
        assert page.locator("#debug-artifact").inner_text().strip(), f"{path}: Debug Drawer 缺少 artifact"
        page.locator("#debug-drawer summary").click()
        page.wait_for_timeout(50)
    if page.locator("#evidence").count():
        evidence_text = page.locator("#evidence").inner_text()
        step_evidence_text = page.locator("#step-evidence").inner_text()
        if require_p1_layout:
            assert "答案交叉检查" in evidence_text, f"{path}: 校验证据摘要为空"
            assert "过程转移通过校验" in evidence_text, f"{path}: 校验证据摘要缺少人话校验"
        else:
            assert evidence_text.strip(), f"{path}: 校验证据面板为空"
        assert "本步语义" in step_evidence_text, f"{path}: 步骤证据面板为空"
    _check_compound_scene_if_present(page, path)
    _check_dependency_flow_if_present(page, path)
    assert not errors, f"{path}: JS errors: {errors}"
    page.locator("#next").click()
    page.wait_for_timeout(100)
    assert page.locator("#counter").inner_text() != counter or counter.startswith("1 / 1")
    if page.locator("#step-evidence").count():
        assert "状态变化" in page.locator("#step-evidence").inner_text(), f"{path}: 步骤证据未更新"
    page.set_viewport_size({"width": 390, "height": 820})
    page.wait_for_timeout(100)
    overflow = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
    assert not overflow, f"{path}: 窄屏出现水平溢出"


def _check_compound_scene_if_present(page, path: Path):
    info = page.evaluate(
        """() => {
            if (typeof RUNTIME_TARGET === 'string' && RUNTIME_TARGET !== 'teaching_2d') {
                return { current: 0, index: -1, count: 0 };
            }
            const allFrames = typeof frames === 'function' ? frames() : [];
            const current = typeof stepIndex === 'number' ? stepIndex : 0;
            const index = allFrames.findIndex(f => (f.objects || []).filter(o => o.type === 'container').length > 1);
            const count = index >= 0 ? (allFrames[index].objects || []).filter(o => o.type === 'container').length : 0;
            return { current, index, count };
        }"""
    )
    if info["index"] < 0:
        return

    page.evaluate("(i) => go(i)", info["index"])
    page.wait_for_timeout(80)
    scene = page.locator("#canvas .compound-scene")
    assert scene.count() >= 1, f"{path}: 多原语帧缺少 compound-scene"
    panels = page.locator("#canvas .primitive-panel")
    assert panels.count() >= info["count"], f"{path}: primitive-panel 数量不足: {panels.count()} < {info['count']}"
    for index in range(min(panels.count(), info["count"])):
        assert panels.nth(index).get_attribute("data-layout"), f"{path}: primitive-panel 缺少 data-layout"
    page.evaluate("(i) => go(i)", info["current"])
    page.wait_for_timeout(80)


def _check_dependency_flow_if_present(page, path: Path):
    info = page.evaluate(
        """() => {
            const allFrames = typeof frames === 'function' ? frames() : [];
            const current = typeof stepIndex === 'number' ? stepIndex : 0;
            const index = allFrames.findIndex(f => (f.objects || []).some(o => o.type === 'arrow'));
            return { current, index };
        }"""
    )
    if info["index"] < 0:
        return

    page.evaluate("(i) => go(i)", info["index"])
    page.wait_for_timeout(80)
    flow = page.locator("#canvas .dependency-flow")
    assert flow.count() >= 1, f"{path}: 有 arrow 的帧缺少 dependency-flow"
    flow_text = flow.first.inner_text().strip()
    assert "→" in flow_text, f"{path}: dependency-flow 缺少方向说明: {flow_text}"
    edges = page.locator("#canvas .dependency-edge")
    assert edges.count() >= 1, f"{path}: dependency-flow 缺少 dependency-edge"
    first_edge = edges.first
    assert first_edge.get_attribute("data-source"), f"{path}: dependency-edge 缺少 data-source"
    assert first_edge.get_attribute("data-target"), f"{path}: dependency-edge 缺少 data-target"
    page.evaluate("(i) => go(i)", info["current"])
    page.wait_for_timeout(80)


def _check_dependency_click_details(page, path: Path):
    required = {
        "unique_paths": {"kind": "matrix", "target": "dp[1][1]", "dep": "dp[0][1]"},
        "bfs": {"kind": "graph", "target": "node:B", "dep": "node:A"},
        "monotonic_stack": {"kind": "array_stack", "target": "answer[0]", "dep": "temperatures[1]"},
    }
    seen: set[str] = set()

    for example in golden_visual_matrix():
        example_id = str(example["id"])
        if example_id not in required:
            continue
        spec = required[example_id]
        page.locator("#tabs .tab").filter(has_text=example["name"]).first.click()
        page.wait_for_timeout(100)
        frame_index = page.evaluate(
            """({target, dep}) => {
                const allFrames = typeof frames === 'function' ? frames() : [];
                return allFrames.findIndex(f => {
                    const edges = (f.objects || []).filter(o => o.type === 'arrow').map(o => [o.source, o.target]);
                    const evidence = f.evidence || {};
                    const deps = Array.isArray(evidence.deps) ? evidence.deps : [];
                    const targets = Array.isArray(evidence.targets) ? evidence.targets : [];
                    return edges.some(([source, dest]) => source === dep && dest === target)
                        || (deps.includes(dep) && targets.includes(target));
                });
            }""",
            {"target": spec["target"], "dep": spec["dep"]},
        )
        assert frame_index >= 0, f"{path}: {example_id} 找不到依赖帧 {spec}"
        page.evaluate("(i) => go(i)", frame_index)
        page.wait_for_timeout(100)

        target_node = page.locator(f'#canvas [data-object-id="{spec["target"]}"]').first
        assert target_node.count() == 1, f"{path}: {example_id} 目标对象不可点击 {spec['target']}"
        target_node.click()
        page.wait_for_timeout(80)
        detail_text = page.locator("#dependency-detail").inner_text()
        assert spec["target"] in detail_text, f"{path}: {example_id} 目标详情缺少对象 id: {detail_text}"
        assert "依赖对象" in detail_text, f"{path}: {example_id} 目标详情缺少依赖对象: {detail_text}"
        assert spec["dep"] in detail_text, f"{path}: {example_id} 目标详情缺少依赖来源: {detail_text}"
        assert "SceneGraph" in detail_text and "evidence" in detail_text, (
            f"{path}: {example_id} 目标详情未说明数据来源: {detail_text}"
        )

        dep_node = page.locator(f'#canvas [data-object-id="{spec["dep"]}"]').first
        assert dep_node.count() == 1, f"{path}: {example_id} 依赖对象不可点击 {spec['dep']}"
        dep_node.click()
        page.wait_for_timeout(80)
        dep_text = page.locator("#dependency-detail").inner_text()
        assert spec["dep"] in dep_text, f"{path}: {example_id} 依赖详情缺少对象 id: {dep_text}"
        assert "影响对象" in dep_text, f"{path}: {example_id} 依赖详情缺少影响对象: {dep_text}"
        assert spec["target"] in dep_text, f"{path}: {example_id} 依赖详情缺少影响目标: {dep_text}"
        seen.add(str(spec["kind"]))

    assert seen == {"matrix", "graph", "array_stack"}, f"{path}: 依赖点击覆盖不足: {seen}"


def _check_regeneration_and_variant_entry(page, path: Path):
    page.set_viewport_size({"width": 1365, "height": 900})
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(500)

    input_text = page.locator("#input").inner_text()
    assert '"fixture": "golden_visual_matrix"' in input_text, f"{path}: 当前输入没有展示 artifact input_data"
    assert page.locator("#input-editor").count() == 1, f"{path}: 缺少可编辑输入入口"
    assert '"fixture": "golden_visual_matrix"' in page.locator("#input-editor").input_value(), (
        f"{path}: 输入编辑器没有加载当前输入"
    )
    tabs = page.locator("#tabs .tab")
    assert tabs.count() >= 4, f"{path}: variant 列表不足: {tabs.count()}"

    panel_text = page.locator("#regeneration-panel").inner_text()
    for phrase in ("ProblemInput -> BuildArtifact -> HTML", "静态 HTML 无法在线调用后端", "artifact 输入"):
        assert phrase in panel_text, f"{path}: 重新生成入口缺少说明 {phrase}: {panel_text}"
    regenerate = page.locator("#regenerate")
    assert regenerate.count() == 1 and not regenerate.is_disabled(), f"{path}: 重新生成入口不可点击"

    before_frames = page.evaluate("() => JSON.stringify(frames())")
    before_artifact = page.evaluate("() => JSON.stringify(ARTIFACT)")
    page.locator("#input-editor").fill('{"fixture":"modified","m":4}')
    regenerate.click()
    page.wait_for_timeout(80)
    status_text = page.locator("#regenerate-status").inner_text()
    payload_text = page.locator("#regenerate-payload").inner_text()
    assert "静态 HTML 无法在线调用后端" in status_text, f"{path}: 缺少静态降级提示: {status_text}"
    assert "ProblemInput -> BuildArtifact -> HTML" in payload_text, f"{path}: artifact 输入缺少主 pipeline: {payload_text}"
    assert '"fixture": "modified"' in payload_text, f"{path}: artifact 输入没有包含修改后的输入: {payload_text}"
    assert page.evaluate("() => JSON.stringify(frames())") == before_frames, f"{path}: 重新生成入口修改了当前 trace"
    assert page.evaluate("() => JSON.stringify(ARTIFACT)") == before_artifact, f"{path}: 重新生成入口修改了 artifact"

    expected_scene_markers = {
        "unique_paths": {"must": {"dp"}, "must_not": {"node:A", "temperatures", "nums"}},
        "bfs": {"must": {"node:A", "queue"}, "must_not": {"dp", "temperatures", "nums"}},
        "binary_search": {"must": {"nums", "pointer:left"}, "must_not": {"dp", "node:A", "temperatures"}},
        "monotonic_stack": {"must": {"temperatures", "stack"}, "must_not": {"dp", "node:A", "nums"}},
    }
    for example in golden_visual_matrix():
        example_id = str(example["id"])
        page.locator("#tabs .tab").filter(has_text=example["name"]).first.click()
        page.wait_for_timeout(80)
        info = page.evaluate(
            """() => {
                const objectIds = new Set(frames().flatMap(f => (f.objects || []).map(o => o.id)));
                return {
                    variantId: variant().id,
                    sceneMatchesVariant: scene() === ARTIFACT.scenes[variant().id],
                    framesMatchScene: frames() === ARTIFACT.scenes[variant().id].frames,
                    counter: document.getElementById('counter').textContent,
                    range: document.getElementById('range').value,
                    objectIds: Array.from(objectIds),
                };
            }"""
        )
        assert info["variantId"] == example_id, f"{path}: 点击 tab 后 variant id 异常: {info}"
        assert info["sceneMatchesVariant"], f"{path}: {example_id} scene() 未绑定当前 variant"
        assert info["framesMatchScene"], f"{path}: {example_id} frames() 未读取当前 SceneGraph"
        assert str(info["range"]) == "0" and str(info["counter"]).startswith("1 /"), (
            f"{path}: {example_id} 切换 variant 未重置步进状态: {info}"
        )
        object_ids = set(info["objectIds"])
        markers = expected_scene_markers[example_id]
        missing = markers["must"] - object_ids
        leaked = markers["must_not"] & object_ids
        assert not missing, f"{path}: {example_id} 当前 SceneGraph 缺少对象 {missing}: {object_ids}"
        assert not leaked, f"{path}: {example_id} 混入其他 variant 对象 {leaked}: {object_ids}"


def _check_variant_comparison_entry(page, path: Path):
    page.set_viewport_size({"width": 1365, "height": 900})
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(500)

    panel = page.locator("#variant-compare-panel")
    assert panel.count() == 1, f"{path}: 缺少解法对比入口"
    panel_text = panel.inner_text()
    for phrase in ("解法对比", "复杂度", "关键步骤数", "结果一致"):
        assert phrase in panel_text, f"{path}: 解法对比缺少 {phrase}: {panel_text}"

    rows = page.locator("#variant-compare-panel .variant-compare-card")
    assert rows.count() >= 2, f"{path}: 解法对比至少需要两个 variant: {rows.count()}"
    assert page.locator("#variant-compare-panel .variant-compare-card[data-variant-id='unique_paths']").count() == 1, (
        f"{path}: 解法对比缺少 unique_paths"
    )
    assert page.locator("#variant-compare-panel .variant-compare-card[data-variant-id='bfs']").count() == 1, (
        f"{path}: 解法对比缺少 bfs"
    )

    compare_data = page.evaluate(
        """() => {
            return Array.from(document.querySelectorAll('#variant-compare-panel .variant-compare-card')).map(card => ({
                variantId: card.dataset.variantId,
                sceneId: card.dataset.sceneId,
                stepCount: Number(card.dataset.stepCount || 0),
                keyStepCount: Number(card.dataset.keyStepCount || 0),
                text: card.textContent,
            }));
        }"""
    )
    for item in compare_data:
        assert item["sceneId"] == item["variantId"], f"{path}: 对比项 scene id 未绑定 variant: {item}"
        assert item["stepCount"] > 0, f"{path}: 对比项缺少步骤数: {item}"
        assert item["keyStepCount"] > 0, f"{path}: 对比项缺少关键步骤数: {item}"
        assert "fixture" in item["text"], f"{path}: 对比项缺少复杂度: {item}"

    before_artifact = page.evaluate("() => JSON.stringify(ARTIFACT)")
    page.locator("#variant-compare-panel .variant-compare-card[data-variant-id='bfs'] button").click()
    page.wait_for_timeout(80)
    bfs_info = page.evaluate(
        """() => ({
            variantId: variant().id,
            sceneMatchesVariant: scene() === ARTIFACT.scenes[variant().id],
            framesMatchScene: frames() === ARTIFACT.scenes[variant().id].frames,
            objectIds: Array.from(new Set(frames().flatMap(f => (f.objects || []).map(o => o.id)))),
            counter: document.getElementById('counter').textContent,
        })"""
    )
    assert bfs_info["variantId"] == "bfs", f"{path}: 对比切换未进入 bfs: {bfs_info}"
    assert bfs_info["sceneMatchesVariant"] and bfs_info["framesMatchScene"], f"{path}: bfs 对比切换混用 SceneGraph: {bfs_info}"
    assert "node:A" in set(bfs_info["objectIds"]) and "dp" not in set(bfs_info["objectIds"]), (
        f"{path}: bfs 对比切换混入其他解法对象: {bfs_info}"
    )
    assert str(bfs_info["counter"]).startswith("1 /"), f"{path}: 对比切换未重置步骤: {bfs_info}"

    page.locator("#variant-compare-panel .variant-compare-card[data-variant-id='unique_paths'] button").click()
    page.wait_for_timeout(80)
    dp_info = page.evaluate(
        """() => ({
            variantId: variant().id,
            sceneMatchesVariant: scene() === ARTIFACT.scenes[variant().id],
            framesMatchScene: frames() === ARTIFACT.scenes[variant().id].frames,
            objectIds: Array.from(new Set(frames().flatMap(f => (f.objects || []).map(o => o.id)))),
        })"""
    )
    assert dp_info["variantId"] == "unique_paths", f"{path}: 对比切换未进入 unique_paths: {dp_info}"
    assert dp_info["sceneMatchesVariant"] and dp_info["framesMatchScene"], (
        f"{path}: unique_paths 对比切换混用 SceneGraph: {dp_info}"
    )
    assert "dp" in set(dp_info["objectIds"]) and "node:A" not in set(dp_info["objectIds"]), (
        f"{path}: unique_paths 对比切换混入其他解法对象: {dp_info}"
    )
    assert page.evaluate("() => JSON.stringify(ARTIFACT)") == before_artifact, f"{path}: 对比入口修改了 artifact"


def _check_golden_visual_matrix_page(page, path: Path):
    _check_page(page, path)
    _check_dependency_click_details(page, path)
    _check_regeneration_and_variant_entry(page, path)
    _check_variant_comparison_entry(page, path)
    _check_phase17_interaction_learning_enhancements(page, path)
    for example in golden_visual_matrix():
        page.locator("#tabs .tab").filter(has_text=example["name"]).first.click()
        page.wait_for_timeout(120)
        assert page.locator("#canvas").inner_text().strip(), f"{path}: {example['id']} 主画布为空"
        assert page.locator("#step-evidence").inner_text().strip(), f"{path}: {example['id']} 本步证据为空"
        for object_id in example["key_objects"]:
            frame_index = page.evaluate(
                """(objectId) => {
                    const allFrames = typeof frames === 'function' ? frames() : [];
                    return allFrames.findIndex(f => (f.objects || []).some(o => o.id === objectId));
                }""",
                object_id,
            )
            assert frame_index >= 0, f"{path}: {example['id']} 缺少关键对象 {object_id}"
            page.evaluate("(i) => go(i)", frame_index)
            page.wait_for_timeout(60)
            assert page.locator("#canvas").inner_text().strip(), f"{path}: {example['id']} 关键对象 {object_id} 所在帧画布为空"
        page.evaluate("() => go(0)")
        page.wait_for_timeout(60)
        total = int(page.locator("#counter").inner_text().split("/", 1)[1].strip())
        if total > 1:
            page.locator("#next").click()
            page.wait_for_timeout(80)
            assert page.locator("#counter").inner_text().startswith("2 /"), f"{path}: {example['id']} next 控制失败"
            assert page.locator("#canvas").inner_text().strip(), f"{path}: {example['id']} 切换后主画布为空"
            page.locator("#range").evaluate("(el) => { el.value = 0; el.dispatchEvent(new Event('input', { bubbles: true })); }")
            page.wait_for_timeout(80)


def _check_phase17_interaction_learning_enhancements(page, path: Path):
    page.set_viewport_size({"width": 1365, "height": 900})
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(500)

    page.locator("#tabs .tab").filter(has_text="不同路径").first.click()
    page.wait_for_timeout(80)
    formula_index = page.evaluate(
        """() => frames().findIndex(f => f.teaching && f.teaching.formula && (f.evidence?.deps || []).length)"""
    )
    assert formula_index >= 0, f"{path}: 找不到可展开公式帧"
    before_trace = page.evaluate("() => JSON.stringify(frames())")
    page.evaluate("(i) => go(i)", formula_index)
    page.wait_for_timeout(80)
    details = page.locator("#teaching .formula-expander").first
    assert details.count() == 1, f"{path}: 缺少公式展开控件"
    assert details.get_attribute("data-source") == "teaching/evidence/SceneGraph", f"{path}: 公式展开来源标记异常"
    details.locator("summary").click()
    page.wait_for_timeout(80)
    formula_text = details.inner_text()
    for phrase in ("公式", "目标", "依赖", "来源", "只读当前 trace"):
        assert phrase in formula_text, f"{path}: 公式展开缺少 {phrase}: {formula_text}"
    assert page.evaluate("() => JSON.stringify(frames())") == before_trace, f"{path}: 公式展开修改了 trace"

    page.locator("#tabs .tab").filter(has_text="二分查找").first.click()
    page.wait_for_timeout(80)
    choice_info = page.evaluate(
        """() => {
            const index = frames().findIndex(f => {
                const interaction = f.interaction || {};
                return interaction.type === 'choice'
                    && interaction.option_explanations
                    && Object.keys(interaction.option_explanations).length;
            });
            const interaction = frames()[index].interaction;
            const wrong = (interaction.options || []).find(option => String(option) !== String(interaction.answer));
            return { index, wrong, text: interaction.option_explanations[String(wrong)] };
        }"""
    )
    assert choice_info["index"] >= 0 and choice_info["wrong"], f"{path}: 找不到带错误选项解释的 choice"
    before_choice_trace = page.evaluate("() => JSON.stringify(frames())")
    page.evaluate("(i) => go(i)", choice_info["index"])
    page.wait_for_timeout(80)
    page.locator("#interaction button").filter(has_text=choice_info["wrong"]).first.click()
    page.wait_for_timeout(80)
    feedback = page.locator("#feedback")
    feedback_text = feedback.inner_text()
    assert "错误选项解释" in feedback_text, f"{path}: 错误反馈没有明确错误选项解释: {feedback_text}"
    assert str(choice_info["text"]) in feedback_text, f"{path}: 错误反馈未使用 trace 中的 option_explanations: {feedback_text}"
    assert feedback.get_attribute("data-source") == "interaction.option_explanations", (
        f"{path}: 错误反馈来源不是 interaction.option_explanations"
    )
    assert feedback.get_attribute("data-correct") == "false", f"{path}: 错误反馈未标记 data-correct=false"
    assert page.evaluate("() => JSON.stringify(frames())") == before_choice_trace, f"{path}: 错误选项反馈修改了 trace"


def _check_phase17_visual_pattern_page(page, path: Path):
    _check_page(page, path)
    page.set_viewport_size({"width": 1365, "height": 900})
    page.wait_for_timeout(80)
    required_selectors = {
        "dp_formula": (".dp-formula-substitution", ".dependency-flow"),
        "graph_relax": (".graph-visual-pattern", ".edge-label"),
        "string_alignment": (".string-alignment-card", ".string-row", ".visual-char.window"),
        "tree_return": (".tree-return-pattern", ".return-bubble"),
        "backtracking_choice": (".backtracking-pattern",),
        "range_structure": (".range-structure-pattern",),
        "network_flow": (".network-flow-pattern", ".edge-label"),
    }
    for item in phase17_visual_pattern_matrix():
        variant_id = str(item["id"])
        page.locator("#tabs .tab").filter(has_text=str(item["name"])).first.click()
        page.wait_for_timeout(100)
        lookup_patterns = [pattern for pattern in item["patterns"] if pattern != "range_structure"] or list(item["patterns"])
        frame_index = page.evaluate(
            """(patterns) => {
                const wanted = new Set(patterns);
                const allFrames = typeof frames === 'function' ? frames() : [];
                return allFrames.findIndex(frame => (frame.objects || []).some(obj => {
                    const meta = obj.meta || {};
                    const raw = Array.isArray(meta.visual_patterns) ? meta.visual_patterns : (meta.visual_patterns ? [meta.visual_patterns] : []);
                    if (meta.visual_pattern) raw.push(meta.visual_pattern);
                    return raw.some(item => wanted.has(String(item)));
                }));
            }""",
            lookup_patterns,
        )
        assert frame_index >= 0, f"{path}: {variant_id} 找不到视觉模式帧"
        page.evaluate("(i) => go(i)", frame_index)
        page.wait_for_timeout(100)
        assert page.locator("#canvas .visual-patterns").count() >= 1, f"{path}: {variant_id} 缺少族级视觉模式面板"
        for selector in required_selectors[variant_id]:
            assert page.locator(f"#canvas {selector}").count() >= 1, f"{path}: {variant_id} 缺少 {selector}"
        if variant_id == "string_alignment":
            assert page.locator("#canvas .string-row").count() >= 2, f"{path}: 字符串双行对齐行数不足"


def _check_algorithm_family_page(page, path: Path):
    _check_page(page, path)
    tabs = page.locator("#tabs .tab")
    count = tabs.count()
    assert count >= 27, f"{path}: 覆盖 variant 数不足: {count}"
    for index in range(count):
        tabs.nth(index).click()
        page.wait_for_timeout(50)
        total_text = page.locator("#counter").inner_text().strip()
        assert "/" in total_text, f"{path}: 第 {index} 个 variant counter 异常: {total_text}"
        total = int(total_text.split("/", 1)[1].strip())
        for step in range(total):
            if step:
                page.locator("#next").click()
                page.wait_for_timeout(40)
            title = page.locator("#step-title").inner_text().strip()
            counter = page.locator("#counter").inner_text().strip()
            canvas_text = page.locator("#canvas").inner_text().strip()
            assert title, f"{path}: 第 {index} 个 variant 第 {step} 帧标题为空"
            assert counter.startswith(f"{step + 1} /"), f"{path}: 第 {index} 个 variant 第 {step} 帧 counter 异常: {counter}"
            assert canvas_text, f"{path}: 第 {index} 个 variant 第 {step} 帧 canvas 为空"


def _check_static_page_has_no_errors(page, path: Path):
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(300)
    assert not errors, f"{path}: JS errors: {errors}"


def _spatial_signature(page) -> dict[str, object]:
    return page.evaluate(
        """() => {
            const canvas = document.getElementById('spatial-canvas');
            if (!canvas) return { present: false };
            const blank = document.createElement('canvas');
            blank.width = canvas.width;
            blank.height = canvas.height;
            return {
                present: true,
                width: canvas.width,
                height: canvas.height,
                dataUrl: canvas.toDataURL('image/png'),
                blankUrl: blank.toDataURL('image/png'),
                runtime: window.AlgoLabSpatialRuntime && window.AlgoLabSpatialRuntime.source,
                primitives: window.SPATIAL_STATE && window.SPATIAL_STATE.primitives || {},
                layouts: window.SPATIAL_STATE && window.SPATIAL_STATE.layouts || [],
                label: document.getElementById('spatial-label')?.textContent || '',
            };
        }"""
    )


def _check_spatial_page(page, path: Path, required_primitives: set[str] | None = None):
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(500)
    first = _spatial_signature(page)
    assert first["present"], f"{path}: spatial canvas 缺失"
    assert int(first["width"]) >= 360 and int(first["height"]) >= 330, f"{path}: spatial canvas 尺寸异常: {first}"
    assert first["runtime"], f"{path}: Three.js runtime 未初始化"
    assert "Three.js WebGL" in str(first["label"]), f"{path}: spatial label 异常: {first['label']}"
    assert first["dataUrl"] != first["blankUrl"], f"{path}: spatial canvas 为空"
    counter = page.locator("#counter").inner_text()
    total = int(counter.split("/", 1)[1].strip())
    if total > 1:
        page.locator("#next").click()
        page.wait_for_timeout(80)
        assert page.locator("#counter").inner_text().startswith("2 /"), f"{path}: next 控制无效"
        page.locator("#prev").click()
        page.wait_for_timeout(80)
        assert page.locator("#counter").inner_text().startswith("1 /"), f"{path}: prev 控制无效"
        page.locator("#range").evaluate("(el, value) => { el.value = value; el.dispatchEvent(new Event('input', { bubbles: true })); }", total - 1)
        page.wait_for_timeout(80)
        assert page.locator("#counter").inner_text().startswith(f"{total} /"), f"{path}: range 控制无效"
        page.locator("#prev").click()
        page.wait_for_timeout(80)
        page.locator("#play").click()
        page.wait_for_timeout(950)
        assert page.locator("#counter").inner_text() != f"{total - 1} / {total}", f"{path}: play 控制无效"
        page.locator("#play").click()
        page.locator("#range").evaluate("(el) => { el.value = 0; el.dispatchEvent(new Event('input', { bubbles: true })); }")
        page.wait_for_timeout(80)
    primitive_counts = dict(first["primitives"])
    data_urls = {first["dataUrl"]}
    second = first
    for _ in range(1, total):
        page.locator("#next").click()
        page.wait_for_timeout(80)
        second = _spatial_signature(page)
        data_urls.add(second["dataUrl"])
        for primitive, count in second["primitives"].items():
            primitive_counts[primitive] = primitive_counts.get(primitive, 0) + count
    assert len(data_urls) > 1 or counter.startswith("1 / 1"), f"{path}: step 切换后 canvas 未变化"
    for primitive in required_primitives or set():
        assert primitive_counts.get(primitive, 0) > 0, f"{path}: 未使用 spatial primitive {primitive}: {primitive_counts}"
    assert not errors, f"{path}: JS errors: {errors}"


def _check_spatial_page_mobile(page, path: Path):
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(400)
    first = _spatial_signature(page)
    assert first["present"], f"{path}: mobile spatial canvas 缺失"
    assert first["dataUrl"] != first["blankUrl"], f"{path}: mobile spatial canvas 为空"
    assert not errors, f"{path}: mobile JS errors: {errors}"


def _check_demo_dashboard_pages(page, dashboard_root: Path):
    import json

    index = dashboard_root / "index.html"
    _check_static_page_has_no_errors(page, index)
    report = json.loads((dashboard_root / "dashboard.json").read_text(encoding="utf-8"))
    assert report["total"] == 8
    _check_demo_dashboard_filtering_and_links(page, index, report)
    for demo in report["demos"]:
        stable = demo.get("stable_html")
        if stable:
            _check_page(page, dashboard_root / stable)
        creative = demo.get("creative_html")
        if creative:
            _check_static_page_has_no_errors(page, dashboard_root / creative)
        spatial = demo.get("spatial_html")
        if spatial:
            required = spatial_requirements_for_demo(demo["id"])
            _check_spatial_page(page, dashboard_root / spatial, required)

    spatial_pages = [dashboard_root / demo["spatial_html"] for demo in report["demos"] if demo.get("spatial_html")]
    assert len(spatial_pages) >= 5, f"dashboard spatial 页面不足: {len(spatial_pages)}"
    page.set_viewport_size({"width": 390, "height": 820})
    _check_spatial_page_mobile(page, spatial_pages[0])


def _check_demo_dashboard_filtering_and_links(page, index: Path, report: dict):
    page.goto(index.resolve().as_uri())
    page.wait_for_timeout(300)
    assert page.locator("#family-coverage").count() == 1, f"{index}: 缺少算法族覆盖区"
    coverage_text = page.locator("#family-coverage").inner_text()
    for phrase in (
        "算法族能力等级",
        "Answer",
        "Process",
        "Demo",
        "Scene",
        "HTML",
        "Fallback / uncovered",
        "artifact 链接",
    ):
        assert phrase in coverage_text, f"{index}: 算法族覆盖区缺少 {phrase}: {coverage_text}"
    assert page.locator("#support-level").count() == 1, f"{index}: 缺少 support level 过滤器"
    assert report.get("family_coverage"), f"{index}: dashboard.json 缺少 family_coverage"

    target_family = report["demos"][0]["family"]
    expected_visible = sum(1 for demo in report["demos"] if demo["family"] == target_family)
    page.select_option("#family", target_family)
    page.wait_for_timeout(100)
    visible = page.locator(".demo").evaluate_all(
        """cards => cards
            .filter(card => getComputedStyle(card).display !== 'none')
            .map(card => ({
                family: card.dataset.family,
                artifactLinks: Array.from(card.querySelectorAll('a'))
                    .filter(link => link.getAttribute('href')?.endsWith('artifact.json')).length
            }))"""
    )
    assert len(visible) == expected_visible, f"{index}: 算法族筛选数量异常 {visible}"
    assert all(item["family"] == target_family for item in visible), f"{index}: 算法族筛选泄漏其他卡片 {visible}"
    assert all(item["artifactLinks"] >= 1 for item in visible), f"{index}: 可见卡片缺少 artifact 链接 {visible}"

    page.select_option("#family", "")
    page.wait_for_timeout(100)
    target_support_level = report["demos"][0]["support_level"]
    expected_support_visible = sum(1 for demo in report["demos"] if demo["support_level"] == target_support_level)
    page.select_option("#support-level", target_support_level)
    page.wait_for_timeout(100)
    support_visible = page.locator(".demo").evaluate_all(
        """cards => cards
            .filter(card => getComputedStyle(card).display !== 'none')
            .map(card => ({
                supportLevel: card.dataset.supportLevel,
                links: Array.from(card.querySelectorAll('a')).map(link => link.getAttribute('href') || '')
            }))"""
    )
    assert len(support_visible) == expected_support_visible, f"{index}: support level 筛选数量异常 {support_visible}"
    assert all(item["supportLevel"] == target_support_level for item in support_visible), (
        f"{index}: support level 筛选泄漏其他卡片 {support_visible}"
    )
    for item in support_visible:
        links = item["links"]
        assert any(link.endswith("artifact.json") for link in links), f"{index}: 缺少 artifact.json 链接 {links}"
        assert any(link.endswith("validation_report.json") for link in links), f"{index}: 缺少 validation_report.json 链接 {links}"
        assert any(link.endswith("demo_readiness_report.json") for link in links), (
            f"{index}: 缺少 demo_readiness_report.json 链接 {links}"
        )

    page.select_option("#support-level", "")
    page.wait_for_timeout(100)
    visible_count = page.locator(".demo").evaluate_all(
        "cards => cards.filter(card => getComputedStyle(card).display !== 'none').length"
    )
    assert visible_count == report["total"], f"{index}: 清空算法族筛选后未恢复全部卡片"


def spatial_requirements_for_demo(demo_id: str) -> set[str]:
    if demo_id == "graph_bfs":
        return {"node", "edge", "queue_dock", "camera_focus"}
    if demo_id == "permutations":
        return {"node", "edge", "cell_block", "path_trail", "camera_focus"}
    if demo_id == "provinces":
        return {"node", "edge", "cell_block", "matrix_plane", "camera_focus"}
    if demo_id == "convex_hull":
        return {"node", "edge", "matrix_plane", "camera_focus"}
    return {"node", "camera_focus"}


def _check_spatial_fixture_primitives(page, path: Path):
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(500)
    requirements = {
        "二分查找": {"cell_block", "pointer_beam", "camera_focus"},
        "BFS 基础图": {"node", "edge", "queue_dock"},
        "单调栈": {"cell_block", "stack_tower"},
        "回溯搜索树": {"node", "edge", "path_trail"},
    }
    for tab_name, primitives in requirements.items():
        page.locator("#tabs .tab").filter(has_text=tab_name).first.click()
        page.wait_for_timeout(160)
        signature = _spatial_signature(page)
        assert signature["present"], f"{path}: {tab_name} spatial canvas 缺失"
        counter = page.locator("#counter").inner_text()
        total = int(counter.split("/", 1)[1].strip())
        counts = dict(signature["primitives"])
        for _ in range(1, total):
            page.locator("#next").click()
            page.wait_for_timeout(60)
            signature = _spatial_signature(page)
            for primitive, count in signature["primitives"].items():
                counts[primitive] = counts.get(primitive, 0) + count
        for primitive in primitives:
            assert counts.get(primitive, 0) > 0, f"{path}: {tab_name} 未使用 {primitive}: {counts}"
    assert not errors, f"{path}: fixture spatial JS errors: {errors}"


def _check_interaction_feedback(page, path: Path):
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(500)
    found: set[str] = set()
    total_text = page.locator("#counter").inner_text().strip()
    total = int(total_text.split("/", 1)[1].strip())
    for step in range(total):
        interaction_type = page.evaluate("() => frame().interaction && frame().interaction.type")
        if interaction_type == "choice":
            before_trace = page.evaluate("() => JSON.stringify(frames())")
            page.locator("#interaction button").first.click()
            page.wait_for_timeout(50)
            assert page.locator("#feedback").inner_text().strip(), f"{path}: choice 无反馈"
            after_trace = page.evaluate("() => JSON.stringify(frames())")
            assert after_trace == before_trace, f"{path}: choice 交互修改了 trace"
            found.add("choice")
        elif interaction_type == "input":
            before_trace = page.evaluate("() => JSON.stringify(frames())")
            answer = page.evaluate("() => String(frame().interaction.answer ?? '')")
            page.locator("#free-answer").fill(answer)
            page.locator("#interaction button").last.click()
            page.wait_for_timeout(50)
            assert "正确" in page.locator("#feedback").inner_text(), f"{path}: input 反馈异常"
            after_trace = page.evaluate("() => JSON.stringify(frames())")
            assert after_trace == before_trace, f"{path}: input 交互修改了 trace"
            found.add("input")
        elif interaction_type == "judge":
            before_trace = page.evaluate("() => JSON.stringify(frames())")
            expected = page.evaluate("() => frame().interaction.answer === true || String(frame().interaction.answer).toLowerCase() === 'true' || String(frame().interaction.answer) === '正确'")
            page.locator("#interaction button").nth(0 if expected else 1).click()
            page.wait_for_timeout(50)
            assert "正确" in page.locator("#feedback").inner_text(), f"{path}: judge 反馈异常"
            after_trace = page.evaluate("() => JSON.stringify(frames())")
            assert after_trace == before_trace, f"{path}: judge 交互修改了 trace"
            found.add("judge")
        if step < total - 1:
            page.locator("#next").click()
            page.wait_for_timeout(50)
    assert found, f"{path}: 未发现交互题"
    assert not errors, f"{path}: interaction JS errors: {errors}"


def _check_golden_prediction_interactions(page, path: Path):
    _check_interaction_feedback(page, path)
    found_by_variant: dict[str, set[str]] = {}
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(500)
    for example in golden_visual_matrix():
        page.locator("#tabs .tab").filter(has_text=example["name"]).first.click()
        page.wait_for_timeout(80)
        total_text = page.locator("#counter").inner_text().strip()
        total = int(total_text.split("/", 1)[1].strip())
        found: set[str] = set()
        for step in range(total):
            interaction_type = page.evaluate("() => frame().interaction && frame().interaction.type")
            if interaction_type:
                found.add(interaction_type)
                assert page.locator("#interaction [data-trace-step]").count() == 1, (
                    f"{path}: {example['id']} 第 {step} 帧交互缺少 data-trace-step"
                )
            if step < total - 1:
                page.locator("#next").click()
                page.wait_for_timeout(40)
        found_by_variant[str(example["id"])] = found
    assert found_by_variant["unique_paths"] >= {"input"}, found_by_variant
    assert found_by_variant["bfs"] >= {"choice"}, found_by_variant
    assert found_by_variant["binary_search"] >= {"choice"}, found_by_variant
    assert found_by_variant["monotonic_stack"] >= {"judge"}, found_by_variant


def _rerender_static_artifact_if_available(path: Path, output_dir: Path) -> Path:
    artifact_path = path.with_suffix(".json")
    if not artifact_path.exists():
        return path
    artifact = BuildArtifact.model_validate_json(artifact_path.read_text(encoding="utf-8"))
    return save_html(artifact, output_dir / path.name)


def _check_phase8_screenshot_regression(dashboard_root: Path, screenshot_dir: Path):
    html_paths = [dashboard_root / "demos" / demo_id / "stable.html" for demo_id in PHASE8_REQUIRED_DEMOS]
    for html in html_paths:
        assert html.exists(), f"P8.2 必选页面缺失: {html}"
    checks = check_html_paths(html_paths, screenshot_dir=screenshot_dir, check_overlap=True)
    assert len(checks) == len(PHASE8_REQUIRED_DEMOS), f"P8.2 检查数量异常: {checks}"
    for demo_id, item in zip(PHASE8_REQUIRED_DEMOS, checks):
        assert item.get("ok"), f"P8.2 {demo_id} 截图回归失败: {item}"
        screenshot = Path(str(item.get("screenshot") or ""))
        assert screenshot.exists() and screenshot.stat().st_size > 0, f"P8.2 {demo_id} 截图未生成: {item}"


def run_all():
    from playwright.sync_api import sync_playwright
    import tempfile

    paths = [
        Path("output/algolab_house_robber.html"),
        Path("output/algolab_unique_paths.html"),
        Path("output/algolab_bfs.html"),
        Path("output/algolab_binary_search.html"),
    ]
    with tempfile.TemporaryDirectory() as d:
        fixture_path = save_html(fixture_artifact(), Path(d) / "fixture.html")
        coverage_path = save_html(classic_coverage_artifact(), Path(d) / "classic_coverage.html")
        family_path = save_html(algorithm_family_coverage_artifact(), Path(d) / "algorithm_family_coverage.html")
        benchmark_path = save_html(benchmark_coverage_artifact(), Path(d) / "benchmark_coverage.html")
        golden_path = save_html(golden_visual_artifact(), Path(d) / "golden_visual_matrix.html")
        phase17_path = save_html(phase17_visual_pattern_artifact(), Path(d) / "phase17_visual_patterns.html")
        spatial_family = algorithm_family_coverage_artifact().model_copy(deep=True)
        from algolab.schemas.render_report import RenderReport

        spatial_family.render_report = RenderReport(
            requested_target="spatial_3d",
            actual_target="spatial_3d",
            release_ready=True,
        )
        spatial_family_path = save_html(spatial_family, Path(d) / "algorithm_family_spatial.html")
        dashboard_index = build_dashboard(Path(d) / "dashboard", style="all")
        phase8_dashboard_index = build_dashboard(
            Path(d) / "phase8_dashboard",
            demo_ids=PHASE8_REQUIRED_DEMOS,
            style="stable",
        )
        paths.append(fixture_path)
        paths.append(coverage_path)
        paths.append(family_path)
        paths.append(benchmark_path)
        paths.append(golden_path)
        paths.append(phase17_path)
        rerendered_static_dir = Path(d) / "rerendered_static"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for html in paths:
                if not html.exists():
                    continue
                check_html = _rerender_static_artifact_if_available(html, rerendered_static_dir)
                page = browser.new_page(viewport={"width": 1365, "height": 900})
                if html.name == "algorithm_family_coverage.html":
                    _check_algorithm_family_page(page, check_html)
                elif html.name == "golden_visual_matrix.html":
                    _check_golden_visual_matrix_page(page, check_html)
                    _check_golden_prediction_interactions(page, check_html)
                elif html.name == "phase17_visual_patterns.html":
                    _check_phase17_visual_pattern_page(page, check_html)
                else:
                    _check_page(page, check_html, require_p1_layout=html.parent != Path("output"))
                page.close()
            page = browser.new_page(viewport={"width": 1365, "height": 900})
            _check_demo_dashboard_pages(page, dashboard_index.parent)
            page.close()
            page = browser.new_page(viewport={"width": 1365, "height": 900})
            _check_interaction_feedback(page, dashboard_index.parent / "demos/binary_search/stable.html")
            page.close()
            page = browser.new_page(viewport={"width": 1365, "height": 900})
            _check_interaction_feedback(page, dashboard_index.parent / "demos/graph_bfs/stable.html")
            page.close()
            page = browser.new_page(viewport={"width": 1365, "height": 900})
            _check_spatial_fixture_primitives(page, spatial_family_path)
            page.close()
            browser.close()
        _check_phase8_screenshot_regression(phase8_dashboard_index.parent, Path(d) / "phase8_screenshots")


if __name__ == "__main__":
    run_all()
    print("browser_smoke: PASS")
