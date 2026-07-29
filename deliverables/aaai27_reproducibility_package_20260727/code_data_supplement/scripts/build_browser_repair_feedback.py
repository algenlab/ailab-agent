"""Collect generic browser feedback for the Direct-BrowserRepair baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fingerprint(page: Any) -> str:
    value = page.evaluate(
        """() => JSON.stringify({
            text: (document.body && document.body.innerText || '').slice(0, 12000),
            htmlLength: document.documentElement ? document.documentElement.outerHTML.length : 0,
            active: document.activeElement ? document.activeElement.tagName : ''
        })"""
    )
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _visible_dom_summary(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => {
            const visible = (el) => {
                const style = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' &&
                    Number(style.opacity || 1) > 0 && rect.width > 0 && rect.height > 0;
            };
            const all = [...document.querySelectorAll('body *')];
            const buttons = [...document.querySelectorAll('button,[role="button"]')]
                .filter(visible)
                .slice(0, 30)
                .map((el) => (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 100));
            const headings = [...document.querySelectorAll('h1,h2,h3')]
                .filter(visible)
                .slice(0, 20)
                .map((el) => (el.innerText || '').trim().slice(0, 160));
            return {
                document_title: document.title || '',
                visible_elements: all.filter(visible).length,
                buttons: buttons.length,
                inputs: [...document.querySelectorAll('input,textarea,select')].filter(visible).length,
                ranges: [...document.querySelectorAll('input[type="range"]')].filter(visible).length,
                headings,
                button_labels: buttons,
                body_text_excerpt: (document.body && document.body.innerText || '').trim().slice(0, 2400),
                html_chars: document.documentElement ? document.documentElement.outerHTML.length : 0,
                scroll_height: document.documentElement ? document.documentElement.scrollHeight : 0
            };
        }"""
    )


def _generic_interaction_smoke(page: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    buttons = page.locator("button:visible, [role=button]:visible")
    for index in range(min(buttons.count(), 6)):
        item = buttons.nth(index)
        try:
            label = (item.inner_text() or item.get_attribute("aria-label") or "").strip()[:100]
            before = _fingerprint(page)
            item.click(timeout=1500)
            page.wait_for_timeout(120)
            after = _fingerprint(page)
            results.append({"kind": "button", "label": label, "changed": before != after})
        except Exception as exc:
            results.append({"kind": "button", "label": f"button-{index + 1}", "changed": False, "error": str(exc)[:240]})

    ranges = page.locator('input[type="range"]:visible')
    if ranges.count():
        try:
            item = ranges.first
            before = _fingerprint(page)
            item.evaluate(
                """el => {
                    const min = Number(el.min || 0);
                    const max = Number(el.max || 100);
                    el.value = String(max > min ? Math.min(max, min + 1) : min);
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }"""
            )
            page.wait_for_timeout(120)
            results.append({"kind": "range", "changed": before != _fingerprint(page)})
        except Exception as exc:
            results.append({"kind": "range", "changed": False, "error": str(exc)[:240]})
    return results


def collect_browser_feedback(
    html_path: Path,
    *,
    screenshot_path: Path,
    timeout_ms: int = 15000,
) -> dict[str, Any]:
    """Load one page with network blocked and return evaluator-agnostic feedback."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        executable = __import__("os").environ.get("ALGOLAB_CHROMIUM_EXECUTABLE", "")
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=executable if executable and Path(executable).exists() else None,
            args=["--no-sandbox"],
        )
        try:
            return collect_browser_feedback_with_browser(
                browser,
                html_path,
                screenshot_path=screenshot_path,
                timeout_ms=timeout_ms,
            )
        finally:
            browser.close()


def collect_browser_feedback_with_browser(
    browser: Any,
    html_path: Path,
    *,
    screenshot_path: Path,
    timeout_ms: int = 15000,
) -> dict[str, Any]:
    """Collect generic feedback using a caller-owned browser instance."""

    console_errors: list[str] = []
    page_errors: list[str] = []
    external_requests: list[str] = []
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    feedback: dict[str, Any] = {
        "page_load_ok": False,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "external_requests": external_requests,
        "dom_summary": {},
        "interaction_smoke": [],
        "screenshot": str(screenshot_path),
    }

    page = browser.new_page(viewport={"width": 1365, "height": 900})
    page.set_default_timeout(timeout_ms)
    page.on("console", lambda msg: console_errors.append(msg.text[:1000]) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)[:1000]))

    def route_request(route: Any) -> None:
        url = str(route.request.url)
        if url.startswith(("http://", "https://", "//")):
            external_requests.append(url)
            route.abort()
        else:
            route.continue_()

    page.route("**/*", route_request)
    try:
        page.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(350)
        feedback["page_load_ok"] = True
        feedback["dom_summary"] = _visible_dom_summary(page)
        feedback["interaction_smoke"] = _generic_interaction_smoke(page)
        page.screenshot(path=str(screenshot_path), full_page=True, timeout=timeout_ms)
        feedback["screenshot_bytes"] = screenshot_path.stat().st_size if screenshot_path.exists() else 0
    except Exception as exc:
        feedback["load_error"] = f"{type(exc).__name__}: {exc}"
        try:
            page.screenshot(path=str(screenshot_path), full_page=False, timeout=timeout_ms)
        except Exception:
            pass
    finally:
        page.close()

    feedback["external_requests"] = sorted(set(external_requests))
    return feedback


def main() -> int:
    parser = argparse.ArgumentParser(description="为单文件 HTML 收集通用浏览器修复反馈")
    parser.add_argument("html", type=Path)
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args()
    feedback = collect_browser_feedback(args.html, screenshot_path=args.screenshot, timeout_ms=args.timeout_ms)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(feedback, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
