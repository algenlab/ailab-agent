"""Browser smoke tests for generated HTML artifacts."""

from __future__ import annotations

from pathlib import Path

from algolab.renderer.export import save_html
from scripts.build_demo_dashboard import build_dashboard
from tests.benchmark_regression import benchmark_coverage_artifact
from tests.fixtures import algorithm_family_coverage_artifact, classic_coverage_artifact, fixture_artifact


def _check_page(page, path: Path):
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
    if page.locator("#evidence").count():
        evidence_text = page.locator("#evidence").inner_text()
        step_evidence_text = page.locator("#step-evidence").inner_text()
        assert "Release gate" in evidence_text, f"{path}: 校验证据面板为空"
        assert "本步语义" in step_evidence_text, f"{path}: 步骤证据面板为空"
    assert not errors, f"{path}: JS errors: {errors}"
    page.locator("#next").click()
    page.wait_for_timeout(100)
    assert page.locator("#counter").inner_text() != counter or counter.startswith("1 / 1")
    if page.locator("#step-evidence").count():
        assert "状态变化" in page.locator("#step-evidence").inner_text(), f"{path}: 步骤证据未更新"


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
            page.locator("#interaction button").first.click()
            page.wait_for_timeout(50)
            assert page.locator("#feedback").inner_text().strip(), f"{path}: choice 无反馈"
            found.add("choice")
        elif interaction_type == "input":
            answer = page.evaluate("() => String(frame().interaction.answer ?? '')")
            page.locator("#free-answer").fill(answer)
            page.locator("#interaction button").last.click()
            page.wait_for_timeout(50)
            assert "正确" in page.locator("#feedback").inner_text(), f"{path}: input 反馈异常"
            found.add("input")
        elif interaction_type == "judge":
            expected = page.evaluate("() => frame().interaction.answer === true || String(frame().interaction.answer).toLowerCase() === 'true' || String(frame().interaction.answer) === '正确'")
            page.locator("#interaction button").nth(0 if expected else 1).click()
            page.wait_for_timeout(50)
            assert "正确" in page.locator("#feedback").inner_text(), f"{path}: judge 反馈异常"
            found.add("judge")
        if step < total - 1:
            page.locator("#next").click()
            page.wait_for_timeout(50)
    assert found, f"{path}: 未发现交互题"
    assert not errors, f"{path}: interaction JS errors: {errors}"


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
        spatial_family = algorithm_family_coverage_artifact().model_copy(deep=True)
        from algolab.schemas.render_report import RenderReport

        spatial_family.render_report = RenderReport(
            requested_target="spatial_3d",
            actual_target="spatial_3d",
            release_ready=True,
        )
        spatial_family_path = save_html(spatial_family, Path(d) / "algorithm_family_spatial.html")
        dashboard_index = build_dashboard(Path(d) / "dashboard", style="all")
        paths.append(fixture_path)
        paths.append(coverage_path)
        paths.append(family_path)
        paths.append(benchmark_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for html in paths:
                if not html.exists():
                    continue
                page = browser.new_page(viewport={"width": 1365, "height": 900})
                if html.name == "algorithm_family_coverage.html":
                    _check_algorithm_family_page(page, html)
                else:
                    _check_page(page, html)
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


if __name__ == "__main__":
    run_all()
    print("browser_smoke: PASS")
