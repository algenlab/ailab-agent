"""Capture real browser screenshots for Phase 17 renderer changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.renderer.export import save_html
from scripts.build_demo_dashboard import build_dashboard
from tests.fixtures import golden_visual_artifact


DEFAULT_PHASE17_CASES = (
    "unique_paths",
    "binary_search",
    "dijkstra_shortest_path",
    "kmp",
    "lca",
    "permutations",
    "segment_tree_range_sum",
    "edmonds_karp",
)
VIEWPORTS = {
    "desktop": {"width": 1365, "height": 900},
    "mobile": {"width": 390, "height": 820},
}


def capture_phase17_screenshots(
    *,
    output_dir: Path,
    dashboard_dir: Path,
    demo_ids: tuple[str, ...],
) -> Path:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    dashboard_index = build_dashboard(dashboard_dir, demo_ids=demo_ids, style="stable")
    dashboard = json.loads((dashboard_index.parent / "dashboard.json").read_text(encoding="utf-8"))
    html_targets = [("dashboard_index", dashboard_index)]
    for demo in dashboard.get("demos", []):
        stable_html = str(demo.get("stable_html") or "")
        if stable_html:
            html_targets.append((str(demo.get("id") or "demo"), dashboard_index.parent / stable_html))

    records: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for target_id, html_path in html_targets:
            for viewport_name, viewport in VIEWPORTS.items():
                records.append(
                    _capture_one(
                        browser,
                        target_id=target_id,
                        html_path=html_path,
                        viewport_name=viewport_name,
                        viewport=viewport,
                        output_dir=output_dir,
                    )
                )
        interaction_html = save_html(golden_visual_artifact(), output_dir / "phase17_interaction_learning.html")
        records.extend(_capture_interaction_sequence(browser, interaction_html, output_dir))
        browser.close()

    manifest = {
        "schema_version": "phase17-screenshot-manifest-v1",
        "dashboard": str(dashboard_index),
        "demo_ids": list(demo_ids),
        "viewports": VIEWPORTS,
        "screenshots": records,
        "interaction_screenshots": [record for record in records if record.get("kind") == "interaction"],
        "ok": all(record["ok"] for record in records),
    }
    manifest_path = output_dir / "phase17_screenshots.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if not manifest["ok"]:
        failures = [record for record in records if not record["ok"]]
        raise SystemExit("Phase 17 screenshot capture failed: " + json.dumps(failures, ensure_ascii=False))
    return manifest_path


def _capture_one(
    browser: Any,
    *,
    target_id: str,
    html_path: Path,
    viewport_name: str,
    viewport: dict[str, int],
    output_dir: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    page = browser.new_page(viewport=viewport)
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    screenshot_path = output_dir / f"{_safe_name(target_id)}_{viewport_name}.png"
    try:
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(500)
        body_text = page.locator("body").inner_text().strip()
        if page.locator("#canvas").count():
            canvas_text = page.locator("#canvas").inner_text().strip()
            if not canvas_text:
                errors.append("#canvas is empty")
        page.screenshot(path=str(screenshot_path), full_page=True)
        size = screenshot_path.stat().st_size if screenshot_path.exists() else 0
        if not body_text:
            errors.append("body text is empty")
        if size <= 0:
            errors.append("screenshot file is empty")
        return {
            "kind": "page",
            "target_id": target_id,
            "html": str(html_path),
            "viewport": viewport_name,
            "screenshot": str(screenshot_path),
            "bytes": size,
            "ok": not errors,
            "errors": errors,
        }
    except Exception as exc:
        return {
            "kind": "page",
            "target_id": target_id,
            "html": str(html_path),
            "viewport": viewport_name,
            "screenshot": str(screenshot_path),
            "bytes": 0,
            "ok": False,
            "errors": [f"{type(exc).__name__}: {exc}", *errors],
        }
    finally:
        page.close()


def _capture_interaction_sequence(
    browser: Any,
    interaction_html: Path,
    output_dir: Path,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    records.extend(_capture_formula_and_regenerate_sequence(browser, interaction_html, output_dir))
    records.append(_capture_wrong_option_feedback(browser, interaction_html, output_dir))
    return records


def _capture_formula_and_regenerate_sequence(browser: Any, html_path: Path, output_dir: Path) -> list[dict[str, Any]]:
    errors: list[str] = []
    page = browser.new_page(viewport=VIEWPORTS["desktop"])
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    records: list[dict[str, Any]] = []
    try:
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(500)
        if page.locator("#tabs .tab").filter(has_text="不同路径").count():
            page.locator("#tabs .tab").filter(has_text="不同路径").first.click()
            page.wait_for_timeout(100)
        formula_index = page.evaluate(
            "() => frames().findIndex(f => f.teaching && f.teaching.formula && (f.evidence?.targets || []).length)"
        )
        if int(formula_index) < 0:
            errors.append("no formula expansion frame")
        else:
            page.evaluate("(i) => go(i)", formula_index)
            page.wait_for_timeout(120)
        records.append(
            _record_screenshot(
                page,
                output_dir / "phase17_interaction_before_formula_desktop.png",
                target_id="interaction_formula_before",
                html_path=html_path,
                phase="before",
                errors=list(errors),
            )
        )
        if page.locator("#teaching .formula-expander summary").count():
            page.locator("#teaching .formula-expander summary").first.click()
            page.wait_for_timeout(120)
            if "只读当前 trace" not in page.locator("#teaching .formula-expander").first.inner_text():
                errors.append("formula expansion source text missing")
        else:
            errors.append("formula expander missing")
        records.append(
            _record_screenshot(
                page,
                output_dir / "phase17_interaction_formula_expanded_desktop.png",
                target_id="interaction_formula_expanded",
                html_path=html_path,
                phase="after_click",
                errors=list(errors),
            )
        )
        if page.locator("#input-editor").count():
            page.locator("#input-editor").fill('{"phase17":"modified_input","m":4,"n":4}')
            page.locator("#regenerate").click()
            page.wait_for_timeout(120)
            status = page.locator("#regenerate-status").inner_text()
            payload = page.locator("#regenerate-payload").inner_text()
            if "ProblemInput -> BuildArtifact -> HTML" not in payload:
                errors.append("regenerate payload does not reference main pipeline")
            if "静态 HTML 无法在线调用后端" not in status:
                errors.append("regenerate static fallback missing")
        else:
            errors.append("input editor missing")
        records.append(
            _record_screenshot(
                page,
                output_dir / "phase17_interaction_regenerate_payload_desktop.png",
                target_id="interaction_regenerate_payload",
                html_path=html_path,
                phase="after_input",
                errors=list(errors),
            )
        )
    except Exception as exc:
        records.append(
            {
                "kind": "interaction",
                "target_id": "interaction_formula_sequence",
                "html": str(html_path),
                "viewport": "desktop",
                "phase": "exception",
                "screenshot": "",
                "bytes": 0,
                "ok": False,
                "errors": [f"{type(exc).__name__}: {exc}", *errors],
            }
        )
    finally:
        page.close()
    return records


def _capture_wrong_option_feedback(browser: Any, html_path: Path, output_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    page = browser.new_page(viewport=VIEWPORTS["desktop"])
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    try:
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(500)
        if page.locator("#tabs .tab").filter(has_text="二分查找").count():
            page.locator("#tabs .tab").filter(has_text="二分查找").first.click()
            page.wait_for_timeout(100)
        choice = page.evaluate(
            """() => {
                const index = frames().findIndex(f => {
                    const interaction = f.interaction || {};
                    return interaction.type === 'choice'
                        && interaction.option_explanations
                        && Object.keys(interaction.option_explanations).length;
                });
                if (index < 0) return { index };
                const interaction = frames()[index].interaction;
                const wrong = (interaction.options || []).find(option => String(option) !== String(interaction.answer));
                return { index, wrong, explanation: interaction.option_explanations[String(wrong)] || '' };
            }"""
        )
        if int(choice.get("index", -1)) < 0 or not choice.get("wrong"):
            errors.append("no choice interaction with option explanation")
        else:
            page.evaluate("(i) => go(i)", choice["index"])
            page.wait_for_timeout(100)
            page.locator("#interaction button").filter(has_text=str(choice["wrong"])).first.click()
            page.wait_for_timeout(120)
            feedback = page.locator("#feedback").inner_text()
            source = page.locator("#feedback").get_attribute("data-source")
            if "错误选项解释" not in feedback:
                errors.append("wrong option feedback missing")
            if str(choice.get("explanation") or "") not in feedback:
                errors.append("option explanation text missing")
            if source != "interaction.option_explanations":
                errors.append(f"wrong feedback source: {source}")
        return _record_screenshot(
            page,
            output_dir / "phase17_interaction_wrong_feedback_desktop.png",
            target_id="interaction_wrong_feedback",
            html_path=html_path,
            phase="error_feedback",
            errors=errors,
        )
    except Exception as exc:
        return {
            "kind": "interaction",
            "target_id": "interaction_wrong_feedback",
            "html": str(html_path),
            "viewport": "desktop",
            "phase": "exception",
            "screenshot": "",
            "bytes": 0,
            "ok": False,
            "errors": [f"{type(exc).__name__}: {exc}", *errors],
        }
    finally:
        page.close()


def _record_screenshot(
    page: Any,
    screenshot_path: Path,
    *,
    target_id: str,
    html_path: Path,
    phase: str,
    errors: list[str],
) -> dict[str, Any]:
    page.screenshot(path=str(screenshot_path), full_page=True)
    size = screenshot_path.stat().st_size if screenshot_path.exists() else 0
    body_text = page.locator("body").inner_text().strip()
    record_errors = list(errors)
    if not body_text:
        record_errors.append("body text is empty")
    if size <= 0:
        record_errors.append("screenshot file is empty")
    return {
        "kind": "interaction",
        "target_id": target_id,
        "html": str(html_path),
        "viewport": "desktop",
        "phase": phase,
        "screenshot": str(screenshot_path),
        "bytes": size,
        "ok": not record_errors,
        "errors": record_errors,
    }


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "page"


def main() -> int:
    parser = argparse.ArgumentParser(description="为 Phase 17 renderer 变更生成真实浏览器截图")
    parser.add_argument("--output-dir", type=Path, default=Path("output/phase17_screenshots"))
    parser.add_argument("--dashboard-dir", type=Path, default=Path("output/phase17_dashboard"))
    parser.add_argument("--case", action="append", default=[], help="指定 demo case id，可重复传入")
    args = parser.parse_args()

    demo_ids = tuple(args.case or DEFAULT_PHASE17_CASES)
    manifest_path = capture_phase17_screenshots(
        output_dir=args.output_dir,
        dashboard_dir=args.dashboard_dir,
        demo_ids=demo_ids,
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
