"""Capture static screenshots for the five non-WebGen English artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_METHODS = (
    "algotutorgen_stage1",
    "algotutorgen_stage2",
    "direct_html",
    "htmlcure_strict",
    "browser_repair_1call",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _by_case(path: Path) -> dict[str, dict[str, Any]]:
    data = _load(path)
    rows = data.get("results") or data.get("records") or []
    return {str(row.get("case_id") or ""): row for row in rows if str(row.get("case_id") or "")}


def _root_path(value: Any) -> Path:
    path = Path(str(value or ""))
    return path if path.is_absolute() else ROOT / path


def merge_screenshot_rows(
    existing: list[dict[str, Any]],
    generated: list[dict[str, Any]],
    *,
    selected_methods: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Replace selected method rows while preserving prior rows for other methods."""

    selected = set(selected_methods)
    rows = [row for row in existing if str(row.get("method") or "") not in selected]
    rows.extend(generated)
    order = {method: index for index, method in enumerate(SCREENSHOT_METHODS)}
    return sorted(
        rows,
        key=lambda row: (order.get(str(row.get("method") or ""), len(order)), str(row.get("case_id") or "")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "benchmark/english_method_samples.json")
    parser.add_argument("--stage1-report", type=Path, required=True)
    parser.add_argument("--stage2-report", type=Path, required=True)
    parser.add_argument("--direct-report", type=Path, required=True)
    parser.add_argument("--htmlcure-report", type=Path, required=True)
    parser.add_argument("--browser-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--wait-ms", type=int, default=700)
    parser.add_argument("--method", action="append", choices=SCREENSHOT_METHODS, default=[])
    args = parser.parse_args()
    for field in (
        "cases",
        "stage1_report",
        "stage2_report",
        "direct_report",
        "htmlcure_report",
        "browser_report",
        "output_dir",
    ):
        value = getattr(args, field)
        setattr(args, field, value if value.is_absolute() else ROOT / value)

    case_ids = [str(row["id"]) for row in (_load(args.cases).get("cases") or [])]
    reports = {
        "algotutorgen_stage1": _by_case(args.stage1_report),
        "algotutorgen_stage2": _by_case(args.stage2_report),
        "direct_html": _by_case(args.direct_report),
        "htmlcure_strict": _by_case(args.htmlcure_report),
        "browser_repair_1call": _by_case(args.browser_report),
    }
    selected_methods = tuple(args.method) if args.method else SCREENSHOT_METHODS
    executable = str(os.environ.get("ALGOLAB_CHROMIUM_EXECUTABLE") or "").strip()
    launch = {"headless": True, "args": ["--no-sandbox"]}
    if executable:
        launch["executable_path"] = executable
    rows: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch)
        try:
            for method in selected_methods:
                report = reports[method]
                method_dir = args.output_dir / method
                method_dir.mkdir(parents=True, exist_ok=True)
                for case_id in case_ids:
                    html = _root_path(report[case_id]["html"])
                    screenshot = method_dir / f"{case_id}.png"
                    page = browser.new_page(viewport={"width": 1365, "height": 900})
                    page.set_default_timeout(30_000)
                    page.route(
                        "**/*",
                        lambda route: route.abort()
                        if route.request.url.startswith(("http://", "https://"))
                        else route.continue_(),
                    )
                    error = ""
                    try:
                        page.goto(html.resolve().as_uri(), wait_until="domcontentloaded", timeout=30_000)
                        page.wait_for_timeout(max(0, int(args.wait_ms)))
                        try:
                            page.screenshot(path=str(screenshot), full_page=True)
                        except Exception:
                            page.screenshot(path=str(screenshot), full_page=False)
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                    finally:
                        page.close()
                    rows.append({"method": method, "case_id": case_id, "screenshot": str(screenshot), "ok": not error, "error": error})
                    print(f"SCREENSHOT {method} {case_id} ok={not error}", flush=True)
        finally:
            browser.close()
    report_path = args.output_dir / "screenshot_report.json"
    existing_rows: list[dict[str, Any]] = []
    if report_path.is_file():
        existing_rows = [
            row
            for row in (_load(report_path).get("results") or [])
            if isinstance(row, dict)
        ]
    merged_rows = merge_screenshot_rows(existing_rows, rows, selected_methods=selected_methods)
    report_path.write_text(json.dumps({"results": merged_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(row["ok"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
