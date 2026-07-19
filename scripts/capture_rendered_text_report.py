"""Capture rendered browser text for evaluation records.

The external LORI/MERLOT review should inspect the page a learner actually sees
after the runtime has booted, not just the static HTML source. This utility
reuses an existing machine report and adds ``rendered_text`` to each record.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _replacement_rows(report_path: Path | None, *, condition: str) -> dict[str, dict[str, Any]]:
    if report_path is None:
        return {}
    report = _load_report(report_path)
    rows: dict[str, dict[str, Any]] = {}
    for row in report.get("results") or []:
        case_id = str(row.get("case_id") or "")
        if case_id:
            rows[case_id] = {
                "condition": condition,
                "case_id": case_id,
                "html": row.get("html"),
                "json": row.get("json"),
                "student_mode_rerender": row.get("student_mode_rerender"),
                "source_html": row.get("source_html"),
                "source_json": row.get("source_json"),
            }
    return rows


def _apply_replacements(records: list[dict[str, Any]], replacements: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    updated = []
    for record in records:
        item = dict(record)
        if item.get("condition") == "algolab_full" and item.get("case_id") in replacements:
            replacement = replacements[str(item.get("case_id"))]
            item.update({key: value for key, value in replacement.items() if value is not None})
            item["condition"] = "algolab_full"
        updated.append(item)
    return updated


def capture_rendered_text(records: list[dict[str, Any]], *, wait_ms: int) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    output: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for record in records:
                row = dict(record)
                errors: list[str] = []
                page = browser.new_page(viewport={"width": 1365, "height": 900})
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.on(
                    "console",
                    lambda msg: errors.append(msg.text)
                    if msg.type in {"error", "warning"} and "favicon" not in msg.text.lower()
                    else None,
                )
                html_path = _repo_path(str(row.get("html") or ""))
                print(f"RENDERED_TEXT {row.get('case_id')} {row.get('condition')}", flush=True)
                try:
                    if html_path.exists():
                        page.goto(html_path.resolve().as_uri())
                        page.wait_for_timeout(wait_ms)
                        row["rendered_text"] = page.locator("body").inner_text(timeout=3000)
                        row["rendered_text_ok"] = True
                    else:
                        row["rendered_text"] = ""
                        row["rendered_text_ok"] = False
                        errors.append(f"missing html: {html_path}")
                except Exception as exc:
                    row["rendered_text"] = ""
                    row["rendered_text_ok"] = False
                    errors.append(f"{type(exc).__name__}: {exc}")
                finally:
                    row["rendered_text_errors"] = errors[:10]
                    page.close()
                output.append(row)
        finally:
            browser.close()
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine-report", type=Path, required=True)
    parser.add_argument("--algolab-report", type=Path, default=None, help="Optional report whose algolab HTML paths replace the source machine report paths.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wait-ms", type=int, default=800)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    machine_report_path = _repo_path(args.machine_report)
    report = _load_report(machine_report_path)
    records = [dict(row) for row in report.get("records") or []]
    replacements = _replacement_rows(_repo_path(args.algolab_report) if args.algolab_report else None, condition="algolab_full")
    records = _apply_replacements(records, replacements)
    records = capture_rendered_text(records, wait_ms=max(0, int(args.wait_ms)))
    report = dict(report)
    report["created_at"] = datetime.now().replace(microsecond=0).isoformat()
    report["source_machine_report"] = str(machine_report_path.relative_to(ROOT))
    report["rendered_text_capture"] = {
        "algolab_replacement_report": str(_repo_path(args.algolab_report).relative_to(ROOT)) if args.algolab_report else "",
        "records": len(records),
        "ok": sum(1 for row in records if row.get("rendered_text_ok")),
    }
    report["records"] = records
    output = _repo_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output.relative_to(ROOT)),
                "records": len(records),
                "ok": report["rendered_text_capture"]["ok"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
