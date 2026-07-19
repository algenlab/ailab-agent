"""Audit generated teaching-interaction HTML pages with Playwright.

This script is intentionally browser-only: it does not call the LLM and does
not regenerate artifacts. It opens existing HTML files, captures screenshots,
and verifies that teaching interaction controls produce feedback and learning
log updates.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = {
    "desktop": {"width": 1365, "height": 900},
    "mobile": {"width": 390, "height": 820},
}
MAJOR_UI_SELECTORS = [
    ("title", "#title"),
    ("tabs", "#tabs"),
    ("canvas", "#canvas"),
    ("teaching-panel", "#teaching-panel"),
    ("interaction", "#interaction"),
    ("prev", "#prev"),
    ("play", "#play"),
    ("next", "#next"),
    ("range", "#range"),
    ("counter", "#counter"),
    ("timeline", "#timeline"),
]


def safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return text.strip("._") or "item"


def text_or_empty(page: Any, selector: str) -> str:
    loc = page.locator(selector)
    if loc.count() == 0:
        return ""
    return loc.first.inner_text().strip()


def visible_count(page: Any, selector: str) -> int:
    loc = page.locator(selector)
    count = loc.count()
    visible = 0
    for index in range(count):
        try:
            if loc.nth(index).is_visible():
                visible += 1
        except Exception:
            pass
    return visible


def major_overlaps(page: Any) -> list[str]:
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
        MAJOR_UI_SELECTORS,
    )


def find_interaction_frame(page: Any, max_steps: int) -> int:
    if visible_count(page, ".interaction[data-learning-checkpoint='prediction']") > 0:
        return 0
    steps = max(1, min(max_steps, 140))
    for step in range(1, steps + 1):
        if page.locator("#next").count() == 0:
            break
        page.locator("#next").click()
        page.wait_for_timeout(40)
        if visible_count(page, ".interaction[data-learning-checkpoint='prediction']") > 0:
            return step
    return -1


def exercise_interaction(page: Any) -> dict[str, Any]:
    before_log = text_or_empty(page, "#learning-log-frame")
    action = "none"
    if visible_count(page, "#interaction .checkpoint-option") > 0:
        page.locator("#interaction .checkpoint-option").first.click()
        action = "choice:first-option"
    elif visible_count(page, "#free-answer") > 0:
        page.locator("#free-answer").fill("__probe__")
        page.locator(".checkpoint-input-row button").first.click()
        action = "input:probe"
    else:
        buttons = page.locator("#interaction .checkpoint-actions button")
        labels: list[str] = []
        for index in range(buttons.count()):
            try:
                labels.append(buttons.nth(index).inner_text().strip())
            except Exception:
                labels.append("")
        clicked = False
        for label in ("正确", "错误", "提示", "查看答案"):
            for index, text in enumerate(labels):
                if label in text:
                    buttons.nth(index).click()
                    action = f"button:{label}"
                    clicked = True
                    break
            if clicked:
                break
    page.wait_for_timeout(250)
    feedback = text_or_empty(page, "#feedback")
    after_log = text_or_empty(page, "#learning-log-frame")
    log_preview = text_or_empty(page, "#learning-log-preview")
    return {
        "action": action,
        "feedback_chars": len(feedback),
        "feedback": feedback[:240],
        "learning_log_changed": before_log != after_log or bool(log_preview),
        "learning_log_frame": after_log[:180],
        "learning_log_preview_chars": len(log_preview),
    }


def audit_one(
    browser: Any,
    *,
    root: Path,
    output_dir: Path,
    row: dict[str, Any],
    viewport_name: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    case_id = str(row["case_id"])
    html_path = (root / str(row["html"])).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    page = browser.new_page(viewport=viewport)
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    screenshot_path = output_dir / f"{safe_name(case_id)}_{viewport_name}.png"
    interaction_result: dict[str, Any] = {}
    try:
        page.goto(html_path.as_uri(), wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        body_text = text_or_empty(page, "body")
        title = text_or_empty(page, "#title")
        counter_before = text_or_empty(page, "#counter")
        selectors_present = {
            "title": page.locator("#title").count() > 0,
            "canvas": page.locator("#canvas").count() > 0,
            "teaching_panel": page.locator("#teaching-panel").count() > 0,
            "interaction_panel": page.locator("#interaction").count() > 0,
            "learning_log": page.locator("#learning-log-frame").count() > 0,
        }
        missing = [name for name, ok in selectors_present.items() if not ok]
        if missing:
            errors.append("missing selectors: " + ", ".join(missing))
        if not body_text:
            errors.append("body text is empty")
        if not title:
            errors.append("title is empty")
        reached_after = find_interaction_frame(page, int(row.get("frame_count") or 0))
        has_interaction = visible_count(page, ".interaction[data-learning-checkpoint='prediction']") > 0
        checkpoint_prompt = text_or_empty(page, ".checkpoint-prompt")
        dependency_summary = text_or_empty(page, ".checkpoint-deps summary")
        if not has_interaction:
            errors.append("no visible prediction checkpoint after navigation")
        if has_interaction and not checkpoint_prompt:
            errors.append("checkpoint prompt is empty")
        if has_interaction and viewport_name == "desktop":
            interaction_result = exercise_interaction(page)
            if interaction_result.get("feedback_chars", 0) <= 0:
                errors.append("interaction feedback did not render")
            if not interaction_result.get("learning_log_changed"):
                errors.append("learning log did not update after interaction")
        overlaps = major_overlaps(page)
        if overlaps:
            warnings.extend(overlaps)
        page.screenshot(path=str(screenshot_path), full_page=True)
        if not screenshot_path.exists() or screenshot_path.stat().st_size <= 0:
            errors.append("screenshot is empty")
        return {
            "case_id": case_id,
            "viewport": viewport_name,
            "html": str(html_path.relative_to(root)),
            "screenshot": str(screenshot_path.relative_to(root)),
            "ok": not errors,
            "title": title,
            "counter_before": counter_before,
            "counter_after": text_or_empty(page, "#counter"),
            "body_chars": len(body_text),
            "selectors_present": selectors_present,
            "interaction_reached_after_next_clicks": reached_after,
            "has_interaction": has_interaction,
            "checkpoint_prompt_chars": len(checkpoint_prompt),
            "dependency_summary": dependency_summary,
            "interaction": interaction_result,
            "console_page_errors": errors,
            "layout_warnings": warnings,
            "bytes": screenshot_path.stat().st_size if screenshot_path.exists() else 0,
        }
    except Exception as exc:
        return {
            "case_id": case_id,
            "viewport": viewport_name,
            "html": str(html_path.relative_to(root)) if html_path.exists() else str(html_path),
            "screenshot": str(screenshot_path.relative_to(root)),
            "ok": False,
            "console_page_errors": [f"{type(exc).__name__}: {exc}", *errors],
            "layout_warnings": warnings,
            "interaction": interaction_result,
        }
    finally:
        page.close()


def build_manifest(
    *,
    source_manifest_path: Path,
    source_manifest: dict[str, Any],
    output_dir: Path,
    records: list[dict[str, Any]],
    strict_report_path: Path | None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "kind": "llm-current-prompt-relaxed-teaching-browser-audit",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "source_manifest": str(source_manifest_path.relative_to(ROOT)),
        "source_rows": source_manifest.get("rows") or [],
        "viewports": VIEWPORTS,
        "records": records,
        "ok": all(record.get("ok") is True for record in records),
        "desktop_interaction_ok": all(
            record.get("ok") is True and record.get("interaction", {}).get("feedback_chars", 0) > 0
            for record in records
            if record.get("viewport") == "desktop"
        ),
        "screenshot_dir": str(output_dir.relative_to(ROOT)),
    }
    if strict_report_path and strict_report_path.exists():
        strict_report = json.loads(strict_report_path.read_text(encoding="utf-8"))
        manifest.update(
            {
                "strict_llm_report": str(strict_report_path.relative_to(ROOT)),
                "strict_llm_cached": strict_report.get("cached"),
                "strict_llm_total": strict_report.get("total"),
                "strict_llm_passed": strict_report.get("passed"),
                "strict_llm_failed": strict_report.get("failed"),
                "strict_llm_pass_rate": strict_report.get("pass_rate"),
            }
        )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="relaxed teaching manifest path")
    parser.add_argument("--output-dir", type=Path, required=True, help="screenshot and audit manifest directory")
    parser.add_argument("--strict-report", type=Path, default=None, help="optional strict LLM benchmark report")
    parser.add_argument("--viewport", action="append", choices=sorted(VIEWPORTS), default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_manifest_path = (ROOT / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest
    output_dir = (ROOT / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    strict_report_path = None
    if args.strict_report:
        strict_report_path = (ROOT / args.strict_report).resolve() if not args.strict_report.is_absolute() else args.strict_report
    output_dir.mkdir(parents=True, exist_ok=True)
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    rows = list(source_manifest.get("rows") or [])
    viewports = args.viewport or ["desktop", "mobile"]
    records: list[dict[str, Any]] = []
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for row in rows:
                for viewport_name in viewports:
                    records.append(
                        audit_one(
                            browser,
                            root=ROOT,
                            output_dir=output_dir,
                            row=row,
                            viewport_name=viewport_name,
                            viewport=VIEWPORTS[viewport_name],
                        )
                    )
        finally:
            browser.close()
    manifest = build_manifest(
        source_manifest_path=source_manifest_path,
        source_manifest=source_manifest,
        output_dir=output_dir,
        records=records,
        strict_report_path=strict_report_path,
    )
    out_path = output_dir / "browser_audit_manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": manifest["ok"],
                "desktop_interaction_ok": manifest["desktop_interaction_ok"],
                "records": len(records),
                "manifest": str(out_path.relative_to(ROOT)),
                "screenshots": [record.get("screenshot") for record in records],
                "failures": [
                    {
                        "case_id": record.get("case_id"),
                        "viewport": record.get("viewport"),
                        "errors": record.get("console_page_errors"),
                    }
                    for record in records
                    if not record.get("ok")
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
