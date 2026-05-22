"""Browser smoke tests for generated HTML artifacts."""

from __future__ import annotations

from pathlib import Path

from algolab.renderer.export import save_html
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
    assert not errors, f"{path}: JS errors: {errors}"
    page.locator("#next").click()
    page.wait_for_timeout(100)
    assert page.locator("#counter").inner_text() != counter or counter.startswith("1 / 1")


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
            browser.close()


if __name__ == "__main__":
    run_all()
    print("browser_smoke: PASS")
