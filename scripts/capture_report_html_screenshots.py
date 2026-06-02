"""Capture screenshots for successful HTML artifacts in LLM benchmark reports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


VIEWPORTS = {
    "desktop": {"width": 1365, "height": 900},
    "mobile": {"width": 390, "height": 820},
}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return text.strip("._") or "item"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_report_spec(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("--report must use CONDITION=PATH")
    condition, path = raw.split("=", 1)
    condition = condition.strip()
    if not condition:
        raise argparse.ArgumentTypeError("--report condition cannot be empty")
    return condition, Path(path.strip())


def html_records_from_report(
    report_path: Path,
    condition: str,
    *,
    include_failed: bool = False,
    only_failed: bool = False,
) -> list[dict[str, Any]]:
    report = load_json(report_path)
    results = report.get("results")
    if not isinstance(results, list):
        raise ValueError(f"{report_path} missing results list")
    records: list[dict[str, Any]] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        ok = result.get("ok") is True
        if only_failed and ok:
            continue
        if not include_failed and not only_failed and not ok:
            continue
        html = str(result.get("html") or "").strip()
        if not html:
            continue
        html_path = Path(html)
        if not html_path.exists():
            raise FileNotFoundError(f"{report_path}: generated HTML does not exist: {html}")
        case_id = str(result.get("case_id") or Path(html).stem)
        sample_index = result.get("sample_index")
        records.append(
            {
                "condition": condition,
                "source_condition": str(result.get("condition") or ""),
                "source_ok": ok,
                "failure_type": str(result.get("failure_type") or ""),
                "case_id": case_id,
                "target_id": f"{condition}:{case_id}:{sample_index if sample_index is not None else 0}",
                "title": str(result.get("title") or ""),
                "case_set": str(result.get("case_set") or ""),
                "case_style": str(result.get("case_style") or ""),
                "family": str(result.get("family") or ""),
                "html": str(html_path),
                "report": str(report_path),
                "sample_index": sample_index if sample_index is not None else 0,
            }
        )
    return records


def collect_html_records(report_specs: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for condition, report_path in report_specs:
        records.extend(html_records_from_report(report_path, condition))
    return records


def collect_html_records_with_options(
    report_specs: list[tuple[str, Path]],
    *,
    include_failed: bool = False,
    only_failed: bool = False,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for condition, report_path in report_specs:
        records.extend(
            html_records_from_report(
                report_path,
                condition,
                include_failed=include_failed,
                only_failed=only_failed,
            )
        )
    return records


def capture_records(
    records: list[dict[str, Any]],
    *,
    output_dir: Path,
    viewport_names: list[str],
    wait_ms: int,
) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_records: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for record in records:
                html_path = Path(str(record["html"]))
                for viewport_name in viewport_names:
                    screenshot_records.append(
                        capture_one(
                            browser,
                            record=record,
                            html_path=html_path,
                            viewport_name=viewport_name,
                            viewport=VIEWPORTS[viewport_name],
                            output_dir=output_dir,
                            wait_ms=wait_ms,
                        )
                    )
        finally:
            browser.close()
    return screenshot_records


def capture_one(
    browser: Any,
    *,
    record: dict[str, Any],
    html_path: Path,
    viewport_name: str,
    viewport: dict[str, int],
    output_dir: Path,
    wait_ms: int,
) -> dict[str, Any]:
    errors: list[str] = []
    page = browser.new_page(viewport=viewport)
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    screenshot_path = output_dir / (
        f"{safe_name(str(record['condition']))}_{safe_name(str(record['case_id']))}_"
        f"{safe_name(str(record.get('sample_index', 0)))}_{viewport_name}.png"
    )
    try:
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(wait_ms)
        body_text = page.locator("body").inner_text().strip()
        if not body_text:
            errors.append("body text is empty")
        page.screenshot(path=str(screenshot_path), full_page=True)
        size = screenshot_path.stat().st_size if screenshot_path.exists() else 0
        if size <= 0:
            errors.append("screenshot file is empty")
        return {
            **record,
            "kind": "page",
            "viewport": viewport_name,
            "screenshot": str(screenshot_path),
            "bytes": size,
            "ok": not errors,
            "errors": errors,
        }
    except Exception as exc:
        return {
            **record,
            "kind": "page",
            "viewport": viewport_name,
            "screenshot": str(screenshot_path),
            "bytes": 0,
            "ok": False,
            "errors": [f"{type(exc).__name__}: {exc}", *errors],
        }
    finally:
        page.close()


def build_manifest(
    *,
    report_specs: list[tuple[str, Path]],
    viewports: list[str],
    records: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    condition_counts: dict[str, int] = {}
    for record in records:
        condition = str(record.get("condition") or "")
        condition_counts[condition] = condition_counts.get(condition, 0) + 1
    return {
        "schema_version": "report-html-screenshot-manifest-v1",
        "created_at": now_iso(),
        "reports": [{"condition": condition, "path": str(path)} for condition, path in report_specs],
        "viewports": {name: VIEWPORTS[name] for name in viewports},
        "condition_counts": condition_counts,
        "screenshots": records,
        "condition_manifests": {
            condition: str(output_dir / f"{safe_name(condition)}_screenshots.json")
            for condition in sorted(condition_counts)
        },
        "ok": all(record.get("ok") is True for record in records),
    }


def write_manifests(manifest: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots = manifest["screenshots"]
    main_path = output_dir / "report_html_screenshots.json"
    main_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for condition, path_text in manifest["condition_manifests"].items():
        condition_records = [record for record in screenshots if record.get("condition") == condition]
        condition_manifest = {
            **manifest,
            "screenshots": condition_records,
            "condition_counts": {condition: len(condition_records)},
            "condition_manifests": {},
        }
        Path(path_text).write_text(json.dumps(condition_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return main_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=parse_report_spec, required=True, help="CONDITION=llm_benchmark_report.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--viewport", action="append", choices=sorted(VIEWPORTS), default=None)
    parser.add_argument("--wait-ms", type=int, default=500)
    parser.add_argument("--include-failed", action="store_true", help="同时捕获 report 中失败但有 HTML 的产物")
    parser.add_argument("--only-failed", action="store_true", help="只捕获 report 中失败但有 HTML 的产物")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    viewports = args.viewport or ["desktop"]
    html_records = collect_html_records_with_options(
        args.report,
        include_failed=args.include_failed,
        only_failed=args.only_failed,
    )
    screenshot_records = capture_records(
        html_records,
        output_dir=args.output_dir,
        viewport_names=viewports,
        wait_ms=args.wait_ms,
    )
    manifest = build_manifest(
        report_specs=args.report,
        viewports=viewports,
        records=screenshot_records,
        output_dir=args.output_dir,
    )
    path = write_manifests(manifest, args.output_dir)
    print(path)
    if not manifest["ok"]:
        failures = [record for record in screenshot_records if not record.get("ok")]
        raise SystemExit("report HTML screenshot capture failed: " + json.dumps(failures[:5], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
