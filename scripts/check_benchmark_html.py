"""Run browser smoke checks for an existing LLM benchmark output directory."""

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

DEFAULT_REQUIRED_CASES = ("unique_paths", "graph_bfs", "binary_search", "daily_temperatures")
MAJOR_UI_SELECTORS = (
    ("title", "#title"),
    ("tabs", "#tabs"),
    ("canvas", "#canvas"),
    ("teaching-panel", "#teaching-panel"),
    ("prev", "#prev"),
    ("play", "#play"),
    ("next", "#next"),
    ("range", "#range"),
    ("counter", "#counter"),
    ("timeline", "#timeline"),
)


def html_paths_from_report(report_path: Path) -> list[Path]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    paths: list[Path] = []
    for item in report.get("results") or []:
        if item.get("ok") and item.get("html"):
            paths.append(Path(item["html"]))
    return paths


def resolve_required_case_htmls(
    report_path: Path,
    *,
    required_cases: tuple[str, ...] | list[str] = DEFAULT_REQUIRED_CASES,
) -> list[Path]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    by_case: dict[str, Path] = {}
    for item in report.get("results") or []:
        case_id = str(item.get("case_id") or "")
        if case_id and item.get("ok") and item.get("html") and case_id not in by_case:
            by_case[case_id] = Path(item["html"])

    missing = [case_id for case_id in required_cases if case_id not in by_case]
    if missing:
        raise ValueError(f"缺少 P8.2 必选 benchmark HTML: {', '.join(missing)}")
    return [by_case[case_id] for case_id in required_cases]


def check_html_paths(
    html_paths: list[Path],
    *,
    screenshot_dir: Path | None = None,
    check_overlap: bool = True,
) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    if screenshot_dir is not None:
        screenshot_dir.mkdir(parents=True, exist_ok=True)

    checked: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for index, path in enumerate(html_paths):
            checked.append(
                _check_html_path(
                    browser,
                    path,
                    index=index,
                    screenshot_dir=screenshot_dir,
                    check_overlap=check_overlap,
                )
            )
        browser.close()
    return checked


def _check_html_path(
    browser: Any,
    path: Path,
    *,
    index: int,
    screenshot_dir: Path | None,
    check_overlap: bool,
) -> dict[str, Any]:
    errors: list[str] = []
    page = browser.new_page(viewport={"width": 1365, "height": 900})
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    screenshot_path: Path | None = None
    try:
        page.goto(path.resolve().as_uri())
        page.wait_for_timeout(500)
        title = page.locator("#title").inner_text().strip()
        counter = page.locator("#counter").inner_text().strip()
        canvas_text = page.locator("#canvas").inner_text().strip()
        if screenshot_dir is not None:
            screenshot_path = screenshot_dir / _screenshot_name(index, path)
            page.screenshot(path=str(screenshot_path), full_page=True)
        overlaps = _major_overlaps(page) if check_overlap else []
        ok = bool(title and "/" in counter and canvas_text and not errors and not overlaps)
        return {
            "html": str(path),
            "ok": ok,
            "title": title,
            "counter": counter,
            "canvas_chars": len(canvas_text),
            "errors": errors,
            "screenshot": str(screenshot_path) if screenshot_path else "",
            "overlaps": overlaps,
        }
    except Exception as exc:
        return {
            "html": str(path),
            "ok": False,
            "errors": [f"{type(exc).__name__}: {exc}", *errors],
            "screenshot": str(screenshot_path) if screenshot_path else "",
            "overlaps": [],
        }
    finally:
        page.close()


def _screenshot_name(index: int, path: Path) -> str:
    parent = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.parent.name) or "page"
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem) or "html"
    return f"{index:02d}_{parent}_{stem}.png"


def _major_overlaps(page: Any) -> list[str]:
    return page.evaluate(
        """(selectorPairs) => {
            const visible = [];
            for (const [name, selector] of selectorPairs) {
                const el = document.querySelector(selector);
                if (!el) continue;
                const style = window.getComputedStyle(el);
                if (style.visibility === 'hidden' || style.display === 'none') continue;
                const rect = el.getBoundingClientRect();
                if (rect.width < 4 || rect.height < 4) continue;
                visible.push({
                    name,
                    selector,
                    el,
                    rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
                });
            }

            const contains = (a, b) =>
                a.x <= b.x + 1 &&
                a.y <= b.y + 1 &&
                a.x + a.width >= b.x + b.width - 1 &&
                a.y + a.height >= b.y + b.height - 1;

            const overlaps = [];
            for (let i = 0; i < visible.length; i++) {
                for (let j = i + 1; j < visible.length; j++) {
                    const a = visible[i];
                    const b = visible[j];
                    if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
                    const left = Math.max(a.rect.x, b.rect.x);
                    const top = Math.max(a.rect.y, b.rect.y);
                    const right = Math.min(a.rect.x + a.rect.width, b.rect.x + b.rect.width);
                    const bottom = Math.min(a.rect.y + a.rect.height, b.rect.y + b.rect.height);
                    const width = right - left;
                    const height = bottom - top;
                    if (width <= 0 || height <= 0) continue;
                    if (contains(a.rect, b.rect) || contains(b.rect, a.rect)) continue;
                    const area = width * height;
                    const smaller = Math.min(a.rect.width * a.rect.height, b.rect.width * b.rect.height);
                    if (area > 8 && area / smaller > 0.25) {
                        overlaps.push(`${a.name} overlaps ${b.name}: ${Math.round(area)}px2`);
                    }
                }
            }
            return overlaps;
        }""",
        list(MAJOR_UI_SELECTORS),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="检查已有 benchmark HTML，不调用 LLM")
    parser.add_argument("output_dir", type=Path, help="包含 llm_benchmark_report.json 的输出目录")
    parser.add_argument("--require-count", type=int, default=0, help="要求检查到的 HTML 数量")
    parser.add_argument(
        "--required-case",
        action="append",
        default=[],
        help="只检查指定 case_id，可重复；缺失会失败",
    )
    parser.add_argument(
        "--phase8-required",
        action="store_true",
        help="检查 P8.2 必选样例：unique_paths、graph_bfs、binary_search、daily_temperatures",
    )
    parser.add_argument("--screenshot-dir", type=Path, default=None, help="保存浏览器截图的目录")
    parser.add_argument("--no-overlap-check", action="store_true", help="跳过主要文本和控件重叠检查")
    args = parser.parse_args()

    report_path = args.output_dir / "llm_benchmark_report.json"
    if not report_path.exists():
        raise SystemExit(f"找不到报告文件：{report_path}")

    required_cases = list(args.required_case)
    if args.phase8_required:
        required_cases.extend(case_id for case_id in DEFAULT_REQUIRED_CASES if case_id not in required_cases)

    html_paths = (
        resolve_required_case_htmls(report_path, required_cases=required_cases)
        if required_cases
        else html_paths_from_report(report_path)
    )
    if args.require_count and len(html_paths) != args.require_count:
        raise SystemExit(f"HTML 数量不匹配：期望 {args.require_count}，实际 {len(html_paths)}")

    checks = check_html_paths(
        html_paths,
        screenshot_dir=args.screenshot_dir,
        check_overlap=not args.no_overlap_check,
    )
    passed = sum(1 for item in checks if item.get("ok"))
    for item in checks:
        status = "PASS" if item.get("ok") else "FAIL"
        screenshot = f" screenshot={item.get('screenshot')}" if item.get("screenshot") else ""
        print(
            f"{status} {item.get('html')} counter={item.get('counter', '')} "
            f"canvas_chars={item.get('canvas_chars', 0)}{screenshot}"
        )
        if item.get("errors"):
            print("; ".join(item["errors"]))
        if item.get("overlaps"):
            print("; ".join(item["overlaps"]))
    print(f"benchmark_html_smoke: {passed}/{len(checks)} PASS")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
