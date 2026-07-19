#!/usr/bin/env python3
"""Audit WebGen-Agent projects with the existing nine black-box metrics."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from scripts.run_interaction_semantic_eval import (
    MACHINE_BOOL_KEYS,
    _answer_match_from_dom,
    _exercise_direct,
    _find_checkpoint,
    _install_alert_capture,
    _text,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_NAME = "WebGenAgent_external_baseline_all200_sample0_webgen_DeepSeek-V4-Pro_iter5_all200_sample0_budget5"


def wait_for_url(log_path: Path, timeout: int = 45) -> str:
    pattern = re.compile(r"http://(?:localhost|127\.0\.0\.1):\d+/?")
    deadline = time.time() + timeout
    while time.time() < deadline:
        text = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
        match = pattern.search(text)
        if match:
            return match.group(0)
        time.sleep(0.5)
    raise TimeoutError("dev server URL did not appear")


def visible_body(page: Any) -> str:
    return str(page.locator("body").inner_text() or "")


def click_semantic_button(page: Any, pattern: str) -> bool:
    regex = re.compile(pattern, re.IGNORECASE)
    buttons = page.locator("button")
    for index in range(buttons.count()):
        button = buttons.nth(index)
        try:
            label = " ".join(filter(None, [button.inner_text(), button.get_attribute("title") or ""]))
            if button.is_visible() and button.is_enabled() and regex.search(label):
                button.click()
                page.wait_for_timeout(250)
                return True
        except Exception:
            continue
    return False


def generic_find_interaction(page: Any) -> bool:
    for _ in range(20):
        controls = page.locator(
            "input:not([type='range']):not([type='hidden']), textarea, "
            "[class*='checkpoint'] button, [class*='quiz'] button, [class*='prediction'] button"
        )
        if any(controls.nth(i).is_visible() for i in range(controls.count())):
            return True
        if not click_semantic_button(page, r"下一步|继续|next|step forward"):
            break
    return False


def generic_exercise(page: Any, url: str) -> dict[str, Any]:
    def reload() -> None:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        _install_alert_capture(page)
        generic_find_interaction(page)

    initial_body = visible_body(page)
    log_selector = "[class*='activity-log'], [class*='learning-log'], [class*='log-list'], #learning-log, #log"
    log_before = _text(page, log_selector)

    before = visible_body(page)
    hint_clicked = click_semantic_button(page, r"提示|hint")
    hint_ok = hint_clicked and visible_body(page) != before

    reload()
    before = visible_body(page)
    show_clicked = click_semantic_button(page, r"查看.*答案|显示.*答案|最终答案|show.*answer|reveal.*answer")
    shown_body = visible_body(page)
    show_answer_ok = show_clicked and shown_body != before
    answer_value = ""
    answer_input = page.locator("input:not([type='range']):not([type='hidden']), textarea")
    for index in range(answer_input.count()):
        try:
            if answer_input.nth(index).is_visible():
                answer_value = answer_input.nth(index).input_value()
                if answer_value:
                    break
        except Exception:
            pass

    reload()
    wrong_before = visible_body(page)
    inputs = page.locator("input:not([type='range']):not([type='hidden']), textarea")
    wrong_ok = False
    correct_ok = False
    if inputs.count():
        for index in range(inputs.count()):
            try:
                if inputs.nth(index).is_visible():
                    inputs.nth(index).fill("x")
                    break
            except Exception:
                pass
        if click_semantic_button(page, r"提交|检查|验证|回答|submit|check|verify"):
            wrong_after = visible_body(page)
            wrong_ok = wrong_after != wrong_before and bool(re.search(r"错误|不正确|再试|incorrect|wrong|try again", wrong_after, re.I))

    if not (correct_ok or wrong_ok):
        option_selector = "[class*='option'] button, button[class*='option'], [class*='choice'] button"
        option_count = page.locator(option_selector).count()
        for option_index in range(min(option_count, 8)):
            reload()
            options = page.locator(option_selector)
            if option_index >= options.count():
                break
            try:
                if not options.nth(option_index).is_visible():
                    continue
                before_option = visible_body(page)
                options.nth(option_index).click()
                click_semantic_button(page, r"提交|检查|验证|回答|submit|check|verify")
                after_option = visible_body(page)
                if after_option == before_option:
                    continue
                if re.search(r"错误|不正确|再试|incorrect|wrong|try again|❌", after_option, re.I):
                    wrong_ok = True
                if re.search(r"正确|答对|很好|correct|great|well done|✅", after_option, re.I):
                    correct_ok = True
                if correct_ok and wrong_ok:
                    break
            except Exception:
                continue

    if answer_value:
        reload()
        correct_before = visible_body(page)
        inputs = page.locator("input:not([type='range']):not([type='hidden']), textarea")
        for index in range(inputs.count()):
            try:
                if inputs.nth(index).is_visible():
                    inputs.nth(index).fill(answer_value)
                    break
            except Exception:
                pass
        if click_semantic_button(page, r"提交|检查|验证|回答|submit|check|verify"):
            correct_after = visible_body(page)
            correct_ok = correct_after != correct_before and bool(re.search(r"正确|答对|很好|correct|great|well done", correct_after, re.I))

    log_after = _text(page, log_selector)
    return {
        "correct_feedback_ok": correct_ok,
        "wrong_feedback_ok": wrong_ok,
        "hint_ok": hint_ok,
        "show_answer_ok": show_answer_ok,
        "learning_log_ok": bool(log_after) and log_after != log_before,
        "mutation_free_ok": all(token in visible_body(page) for token in re.findall(r"\S+", initial_body)[:3]),
        "feedback_preview": {"log": log_after[:240]},
    }


def run_one(case: dict[str, Any], workspace_root: Path, output_dir: Path) -> dict[str, Any]:
    case_id = case["case_id"]
    workspace = workspace_root / case_id
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    service_log = case_dir / "service.log"
    result: dict[str, Any] = {"condition": "webgen_agent", **case}
    process = None
    try:
        install = subprocess.run(
            [
                "npm", "install", "--no-audit", "--no-fund",
                "--registry", "https://registry.npmjs.org",
                "--fetch-retries", "4", "--fetch-retry-maxtimeout", "60000",
                "--cache", str(ROOT / "output/external_baselines/webgen/npm-cache"),
            ],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=600,
        )
        if install.returncode != 0:
            raise RuntimeError("npm install failed: " + (install.stderr or install.stdout)[-1200:])
        log_handle = service_log.open("w", encoding="utf-8")
        process = subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "0"],
            cwd=workspace,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        url = wait_for_url(service_log)
        errors: list[str] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.environ.get("ALGOLAB_CHROMIUM_EXECUTABLE") or None,
                headless=True,
                args=["--no-sandbox"],
            )
            page = browser.new_page(viewport={"width": 1365, "height": 900})
            page.set_default_timeout(2500)
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(800)
            _install_alert_capture(page)
            page_load_ok = bool(_text(page, "body")) and not errors
            visible_answer_match = _answer_match_from_dom(page, case.get("expected"))
            interaction_reachable = _find_checkpoint(page, max_steps=80) or generic_find_interaction(page)
            exercise = _exercise_direct(page) if interaction_reachable else {
                "correct_feedback_ok": False,
                "wrong_feedback_ok": False,
                "hint_ok": False,
                "show_answer_ok": False,
                "learning_log_ok": False,
                "mutation_free_ok": False,
                "feedback_preview": {},
            }
            if interaction_reachable:
                generic = generic_exercise(page, url)
                for key in (
                    "correct_feedback_ok", "wrong_feedback_ok", "hint_ok",
                    "show_answer_ok", "learning_log_ok", "mutation_free_ok",
                ):
                    exercise[key] = bool(exercise.get(key) or generic.get(key))
                if generic.get("feedback_preview"):
                    exercise["feedback_preview"] = generic["feedback_preview"]
            screenshot = case_dir / "final.png"
            page.screenshot(path=str(screenshot), full_page=True)
            browser.close()
        result.update({
            "url": url,
            "page_load_ok": page_load_ok,
            "visible_answer_match": visible_answer_match,
            "interaction_reachable": interaction_reachable,
            **exercise,
            "console_page_errors": errors,
            "screenshot": str(screenshot.relative_to(ROOT)),
        })
    except Exception as exc:
        result.update({key: False for key in MACHINE_BOOL_KEYS})
        result["console_page_errors"] = [f"{type(exc).__name__}: {exc}"]
    finally:
        if process is not None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except Exception:
                    pass
        shutil.rmtree(workspace / "node_modules", ignore_errors=True)
    result["machine_ok"] = all(result.get(key) is True for key in MACHINE_BOOL_KEYS)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "benchmark/external_baseline_all200_sample0.json")
    parser.add_argument("--workspace-root", type=Path, default=ROOT / "output/external_baselines/webgen/workspaces" / RUN_NAME)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/external_baselines/webgen/audit_all200_sample0")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = args.output_dir / "results.jsonl"
    done = set()
    if output_jsonl.exists():
        for line in output_jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["case_id"])
    cases = json.loads(args.manifest.read_text(encoding="utf-8"))["cases"]
    if args.case:
        cases = [case for case in cases if case["case_id"] in set(args.case)]
    cases = [case for case in cases if case["case_id"] not in done]
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {executor.submit(run_one, case, args.workspace_root, args.output_dir): case for case in cases}
        for future in as_completed(futures):
            record = future.result()
            with output_jsonl.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(record["case_id"], record["machine_ok"], flush=True)
    rows = [json.loads(line) for line in output_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = {"total": len(rows)}
    for key in ["machine_ok", *MACHINE_BOOL_KEYS]:
        summary[key] = sum(row.get(key) is True for row in rows)
        summary[f"{key}_rate"] = summary[key] / len(rows) if rows else 0.0
    (args.output_dir / "report.json").write_text(
        json.dumps({"summary": summary, "results": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
