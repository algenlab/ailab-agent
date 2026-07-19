"""Run the direct-HTML LLM baseline as an external experiment."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import _model_name, chat_text_with_metadata, clear_model_calls, consume_model_calls
from scripts.baseline_experiment_utils import add_common_args, run_benchmark
from scripts.run_llm_benchmark import (
    BenchmarkCase,
    BenchmarkInput,
    UnseenBenchmarkCase,
    benchmark_condition,
    browser_smoke_html_paths,
    classify_failure,
    result_metadata,
)


def _system_prompt() -> str:
    return (
        "你是算法教学页面生成器。直接输出一个完整、可离线打开的单文件 HTML，不要输出 markdown。"
        "你要生成 AlgoLab-style 算法教学页：包含代码、当前步状态、步骤时间线、可交互控件、讲解、预测题、即时反馈、学习日志和最终答案。"
        "页面不能调用外部资源，不能声称经过 AlgoLab SceneGraph、release gate 或机器校验。"
    )


def _user_prompt(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    *,
    expected_visible_to_model: bool = True,
) -> str:
    lines = [
        f"题目：{case.title}",
        f"描述：{case.problem}",
        f"算法族：{case.family}",
        f"策略提示：{case.strategy}",
        f"输入 JSON：{json.dumps(sample.input_data, ensure_ascii=False)}",
    ]
    if expected_visible_to_model:
        lines.append(f"期望输出 JSON：{json.dumps(sample.expected, ensure_ascii=False)}")
    else:
        lines.append("标准答案不提供。请自行求解并在页面中清晰展示最终答案。")
    lines.extend(
        [
            "要求：",
            "1. 只生成 HTML，不调用外部资源。",
            "2. 页面必须是 AlgoLab-style 教学页，而不是只放一个动画。",
            "3. 必须包含这些 id：#title、#subtitle、#top-result、#top-solution、#code、#step-title、#step-desc、#op、#canvas、#prev、#play、#next、#range、#counter、#timeline、#teaching、#state、#step-evidence、#answer。",
            "4. #code 展示可读的 solve 伪代码或 JavaScript/Python 实现，并随当前步骤高亮当前代码行。",
            "5. #counter 初始格式必须类似 1 / N，N 至少为 2；#timeline 必须有 N 个 .tick 按钮，每个 tick 内含 .tick-label 和 .tick-op。",
            "6. #prev、#next、#range 都必须能切换步骤，并同步 #counter、#step-title、#step-desc、#canvas、#state、#teaching、#step-evidence 和 active tick。",
            "7. #canvas 是页面的可见算法视图区，应包含当前步骤的算法对象和文字状态；不要把 #canvas 本身做成 canvas/svg 绘图节点。",
            "8. #canvas 必须展示算法对象，例如数组/矩阵/图/树/队列/map/DP 表，并用颜色标记当前对象、依赖对象和答案对象。",
            "9. #timeline 的每个 .tick 必须是 button 或可点击元素，DOM 里必须同时包含 <span class=\"tick-label\">阶段</span> 和 <span class=\"tick-op\">操作</span>，不要只在 hover、title 或 CSS 里提供。",
            "10. #state 必须展示当前步骤状态 JSON 摘要；#teaching 必须解释当前步骤做什么、为什么做、不变量或常见错误；#step-evidence 必须写出本步 operation、targets、before/after 或状态变化。",
            "11. #answer 的 textContent 从页面加载开始就必须是题目最终返回值的裸 JSON，必须与页面展示一致；不是当前操作参数、查询区间、节点编号或中间状态；不要包成 {\"result\": ...}、{\"answer\": ...}，除非题目本身答案就是对象。",
            "12. 每个关键步骤应包含一个 learner checkpoint：可以是选择题、输入预测题或判断题；页面中必须有可点击/可输入控件、提交按钮、hint 按钮、显示答案按钮和即时反馈区域。",
            "13. learner checkpoint 的反馈必须 grounded in 当前步骤状态：答对说明为什么对，答错说明常见误区，并把每次提交追加到页面内 learning log。",
            "14. 步骤应覆盖初始化、关键状态转移、答案确认；HTML 必须完整闭合，不能输出半截。",
            "15. 这是 direct_html_baseline，不要声称经过 AlgoLab SceneGraph、release gate 或机器 gate。",
        ]
    )
    return "\n".join(lines)


def _repair_prompt(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    *,
    previous_html: str,
    errors: list[str],
    expected_visible_to_model: bool,
) -> str:
    lines = [
        "上一版 direct HTML baseline 失败，请修复后重新输出完整单文件 HTML。",
        f"题目：{case.title}",
        f"描述：{case.problem}",
        f"算法族：{case.family}",
        f"策略提示：{case.strategy}",
        f"输入 JSON：{json.dumps(sample.input_data, ensure_ascii=False)}",
    ]
    if expected_visible_to_model:
        lines.append(f"期望输出 JSON：{json.dumps(sample.expected, ensure_ascii=False)}")
    else:
        lines.append("标准答案不提供。请自行求解并在页面中清晰展示最终答案。")
    lines.extend(
        [
            "失败信息：",
            *[f"- {error}" for error in errors],
            "修复要求：",
            "1. 只输出完整 HTML，不要输出 markdown；如果上一版可能没有可复用的 HTML 或缺 <html>，从零重写一个短版完整 HTML。",
            "2. 必须包含 #title、#subtitle、#top-result、#top-solution、#code、#step-title、#step-desc、#op、#canvas、#prev、#play、#next、#range、#counter、#timeline、#teaching、#state、#step-evidence、#answer。",
            "3. #counter 格式类似 1 / N，N 至少为 2；#timeline .tick 数量必须等于 N，且每个 tick 有 .tick-label 和 .tick-op。",
            "4. #prev、#next、#range 必须能切换步骤并同步当前步标题、解释、画布、状态、讲解、证据和 active tick。",
            "5. #canvas 是页面的可见算法视图区，应包含当前步骤的算法对象和文字状态；不要把 #canvas 本身做成 canvas/svg 绘图节点。",
            "6. #timeline 每个 .tick 内必须同时有 .tick-label 和 .tick-op。",
            "7. #answer 的 textContent 必须从首屏开始就是题目最终返回值的裸 JSON，不能只写解释文字，不能填当前操作参数、查询区间、节点编号或中间状态，不能包成非题目要求的 result/answer 对象。",
            "8. 每个关键步骤应包含 learner checkpoint，并提供可提交答案、hint、显示答案、即时反馈和 learning log 追加记录。",
            "9. 步骤应覆盖初始化、关键状态转移、答案确认；HTML 必须完整闭合，不能输出半截。",
            "10. 不调用外部资源，不要声称经过 AlgoLab SceneGraph 或机器 gate。",
            "上一版 HTML：",
            previous_html[-12000:],
        ]
    )
    return "\n".join(lines)


def extract_html(content: str) -> str:
    text = (content or "").strip()
    fenced = re.search(r"```(?:html)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    start_candidates = [idx for idx in (text.lower().find("<!doctype"), text.lower().find("<html")) if idx >= 0]
    if start_candidates:
        text = text[min(start_candidates) :].strip()
    elif "<" not in text or ">" not in text:
        return ""
    return text


def _has_id(html_lower: str, node_id: str) -> bool:
    for required in (f'id="{node_id}"', f"id='{node_id}'", f"id={node_id}"):
        if required in html_lower:
            return True
    return False


REQUIRED_ALGOLAB_STYLE_IDS = (
    "title",
    "subtitle",
    "top-result",
    "top-solution",
    "code",
    "step-title",
    "step-desc",
    "op",
    "canvas",
    "prev",
    "play",
    "next",
    "range",
    "counter",
    "timeline",
    "teaching",
    "state",
    "step-evidence",
    "answer",
)


class _DirectHtmlStructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.classes: set[str] = set()
        self.tags_by_id: dict[str, str] = {}
        self.current_ids: list[str] = []
        self.text_by_id: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node_id = ""
        for name, value in attrs:
            if name.lower() == "id" and value:
                node_id = value
                self.ids.add(value)
                self.tags_by_id[value] = tag.lower()
                self.text_by_id.setdefault(value, [])
            elif name.lower() == "class" and value:
                self.classes.update(part for part in value.split() if part)
        self.current_ids.append(node_id)

    def handle_endtag(self, tag: str) -> None:
        if self.current_ids:
            self.current_ids.pop()

    def handle_data(self, data: str) -> None:
        if not data.strip():
            return
        for node_id in self.current_ids:
            if node_id:
                self.text_by_id.setdefault(node_id, []).append(data)

    def text_for(self, node_id: str) -> str:
        return " ".join(self.text_by_id.get(node_id) or []).strip()


def _parse_direct_html(html: str) -> _DirectHtmlStructureParser:
    parser = _DirectHtmlStructureParser()
    try:
        parser.feed(html or "")
    except Exception:
        return parser
    return parser


def _looks_like_json(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    try:
        json.loads(stripped)
        return True
    except json.JSONDecodeError:
        return False


def validate_direct_html(html: str) -> list[str]:
    errors: list[str] = []
    lower = html.lower()
    if "<html" not in lower:
        errors.append("html_error: missing <html>")
    parsed = _parse_direct_html(html)
    for node_id in REQUIRED_ALGOLAB_STYLE_IDS:
        if node_id not in parsed.ids and not _has_id(lower, node_id):
            errors.append(f"html_error: missing #{node_id}")
    canvas_tag = parsed.tags_by_id.get("canvas", "")
    if canvas_tag in {"canvas", "svg"}:
        errors.append(f"html_error: #canvas must be an HTMLElement text container, not <{canvas_tag}>")
    if "answer" in parsed.ids and not _looks_like_json(parsed.text_for("answer")):
        errors.append("html_error: #answer textContent must be final answer bare JSON on initial load")
    return errors


def _write_failed_direct_html_artifact(
    output_stem: str,
    output_dir: Path,
    html: str,
    *,
    errors: list[str],
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample_index: int,
    args: argparse.Namespace,
    repair_rounds: int,
) -> tuple[Path, Path] | tuple[None, None]:
    if not html:
        return None, None
    output_dir.mkdir(parents=True, exist_ok=True)
    failed_html = output_dir / f"{output_stem}.failed.html"
    failed_json = output_dir / f"{output_stem}.failed.json"
    failed_html.write_text(html, encoding="utf-8")
    failed_json.write_text(
        json.dumps(
            {
                "kind": "direct_html_baseline_failed_artifact",
                "case_id": case.id,
                "sample_index": sample_index,
                "condition": benchmark_condition(args),
                "html": str(failed_html),
                "html_chars": len(html),
                "errors": errors,
                "direct_html_repair_rounds": repair_rounds,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return failed_html, failed_json


def _write_raw_direct_html_response_artifact(
    output_stem: str,
    output_dir: Path,
    content: str,
    *,
    errors: list[str],
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample_index: int,
    args: argparse.Namespace,
    repair_rounds: int,
) -> tuple[Path, Path] | tuple[None, None]:
    if not content:
        return None, None
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_text = output_dir / f"{output_stem}.raw.txt"
    raw_json = output_dir / f"{output_stem}.raw.json"
    raw_text.write_text(content, encoding="utf-8")
    raw_json.write_text(
        json.dumps(
            {
                "kind": "direct_html_baseline_raw_response",
                "case_id": case.id,
                "sample_index": sample_index,
                "condition": benchmark_condition(args),
                "raw_response": str(raw_text),
                "raw_chars": len(content),
                "errors": errors,
                "direct_html_repair_rounds": repair_rounds,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return raw_text, raw_json


@contextmanager
def _direct_llm_max_tokens(args: argparse.Namespace):
    raw_value = int(getattr(args, "llm_max_tokens", 0) or 0)
    if raw_value <= 0:
        yield
        return
    previous = os.environ.get("ALGOLAB_LLM_MAX_TOKENS")
    os.environ["ALGOLAB_LLM_MAX_TOKENS"] = str(raw_value)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("ALGOLAB_LLM_MAX_TOKENS", None)
        else:
            os.environ["ALGOLAB_LLM_MAX_TOKENS"] = previous


def direct_html_browser_check(output_html: Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1365, "height": 900})
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.goto(output_html.resolve().as_uri())
            page.wait_for_timeout(300)
            for node_id in REQUIRED_ALGOLAB_STYLE_IDS:
                if page.locator(f"#{node_id}").count() < 1:
                    errors.append(f"missing #{node_id}")
            title = _safe_inner_text(page, "#title")
            counter = _safe_inner_text(page, "#counter")
            canvas = _safe_inner_text(page, "#canvas")
            canvas_tag = _safe_tag_name(page, "#canvas")
            if canvas_tag in {"CANVAS", "SVG"}:
                errors.append("#canvas must be an HTMLElement text container; put drawing canvas/svg inside #canvas instead of using id=canvas on it")
            if not title:
                errors.append("empty #title")
            if "/" not in counter:
                errors.append(f"invalid #counter: {counter}")
            if not canvas:
                errors.append("empty #canvas")
            total = _counter_total(counter)
            ticks = page.locator("#timeline .tick")
            tick_count = ticks.count()
            if total < 2:
                errors.append(f"#counter total must be >=2: {counter}")
            if tick_count != total:
                errors.append(f"#timeline .tick count {tick_count} != counter total {total}")
            if total and page.locator("#timeline .tick-label").count() != total:
                errors.append("timeline ticks must include .tick-label")
            if total and page.locator("#timeline .tick-op").count() != total:
                errors.append("timeline ticks must include .tick-op")
            for selector in ("#code", "#state", "#teaching", "#step-evidence", "#step-title", "#step-desc"):
                if not _safe_inner_text(page, selector):
                    errors.append(f"empty {selector}")
            answer_text = _safe_inner_text(page, "#answer")
            try:
                json.loads(answer_text)
            except json.JSONDecodeError:
                errors.append("#answer textContent is not bare JSON on initial load")
            if total > 1 and page.locator("#next").count():
                page.locator("#next").click()
                page.wait_for_timeout(100)
                next_counter = _safe_inner_text(page, "#counter")
                if next_counter == counter or not next_counter.startswith("2 /"):
                    errors.append("#next did not advance #counter to step 2")
                if page.locator("#range").count():
                    range_value = page.locator("#range").evaluate("el => String(el.value)")
                    if range_value != "1":
                        errors.append("#next did not sync #range to 1")
                    page.locator("#range").evaluate("(el) => { el.value = 0; el.dispatchEvent(new Event('input', { bubbles: true })); }")
                    page.wait_for_timeout(80)
                    if not _safe_inner_text(page, "#counter").startswith("1 /"):
                        errors.append("#range did not reset #counter to step 1")
                if tick_count > 1:
                    ticks.nth(1).click()
                    page.wait_for_timeout(80)
                    if not _safe_inner_text(page, "#counter").startswith("2 /"):
                        errors.append("timeline tick click did not sync #counter")
            return {
                "html": str(output_html),
                "ok": not errors,
                "title": title,
                "counter": counter,
                "canvas_chars": len(canvas),
                "errors": errors,
            }
        except Exception as exc:
            return {"html": str(output_html), "ok": False, "errors": [f"{type(exc).__name__}: {exc}", *errors]}
        finally:
            page.close()
            browser.close()


def _safe_inner_text(page: Any, selector: str) -> str:
    try:
        if page.locator(selector).count() < 1:
            return ""
        return page.locator(selector).first.inner_text().strip()
    except Exception:
        return ""


def _safe_tag_name(page: Any, selector: str) -> str:
    try:
        if page.locator(selector).count() < 1:
            return ""
        return str(page.locator(selector).first.evaluate("el => el.tagName") or "").upper()
    except Exception:
        return ""


def _counter_total(counter: str) -> int:
    if "/" not in counter:
        return 0
    raw = counter.split("/", 1)[1].strip()
    try:
        return int(raw)
    except ValueError:
        return 0


def _browser_validation_errors(output_html: Path) -> list[str]:
    checks = browser_smoke_html_paths([output_html])
    errors: list[str] = []
    if not checks or checks[0].get("ok") is not True:
        check = checks[0] if checks else {"errors": ["browser smoke failed"]}
        errors.extend(str(error) for error in (check.get("errors") or ["browser smoke failed"]))
    direct_check = direct_html_browser_check(output_html)
    if direct_check.get("ok") is not True:
        errors.extend(str(error) for error in (direct_check.get("errors") or ["direct HTML structure browser check failed"]))
    return [f"browser_error: {error}" for error in errors]


def _failure_type_from_errors(errors: list[str]) -> str:
    message = "; ".join(errors)
    if "browser_error" in message:
        return "browser"
    if "html_error" in message or "missing #" in message:
        return "html_error"
    return classify_failure(message)


def run_one_direct_html(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    started = time.time()
    clear_model_calls()
    output_stem = f"direct_html_{case.id}_{sample_index}"
    output_html = args.output_dir / f"{output_stem}.html"
    metadata = result_metadata(case, sample_index, args)
    expected_visible = bool(getattr(args, "expected_visible_to_model", True))
    baseline = str(getattr(args, "baseline", "direct_html_baseline"))
    max_rounds = max(0, int(getattr(args, "max_rounds", 0) or 0))
    browser_repair_enabled = bool(getattr(args, "browser_smoke", False) and max_rounds > 0)
    previous_html = ""
    failed_html: Path | None = None
    failed_json: Path | None = None
    raw_response: Path | None = None
    raw_response_json: Path | None = None
    last_errors: list[str] = []
    repair_rounds = 0
    phase_timings: list[dict[str, Any]] = []
    try:
        for attempt in range(max_rounds + 1):
            attempt_started = time.time()
            if attempt == 0:
                user_prompt = _user_prompt(case, sample, expected_visible_to_model=expected_visible)
                kind = "direct_html"
            else:
                repair_rounds += 1
                user_prompt = _repair_prompt(
                    case,
                    sample,
                    previous_html=previous_html,
                    errors=last_errors,
                    expected_visible_to_model=expected_visible,
                )
                kind = "direct_html_repair"
            with _direct_llm_max_tokens(args):
                response = chat_text_with_metadata(_system_prompt(), user_prompt, kind=kind)
            content = str(response.get("content") or "")
            html = extract_html(content)
            previous_html = html
            errors = validate_direct_html(html)
            if not errors:
                output_html.parent.mkdir(parents=True, exist_ok=True)
                output_html.write_text(html, encoding="utf-8")
                if browser_repair_enabled:
                    errors = _browser_validation_errors(output_html)
            last_errors = errors
            if errors and html:
                failed_html, failed_json = _write_failed_direct_html_artifact(
                    output_stem,
                    args.output_dir,
                    html,
                    errors=errors,
                    case=case,
                    sample_index=sample_index,
                    args=args,
                    repair_rounds=repair_rounds,
                )
            if errors and content and not html:
                raw_response, raw_response_json = _write_raw_direct_html_response_artifact(
                    output_stem,
                    args.output_dir,
                    content,
                    errors=errors,
                    case=case,
                    sample_index=sample_index,
                    args=args,
                    repair_rounds=repair_rounds,
                )
            if attempt > 0:
                phase_timings.append(
                    {
                        "phase": f"repair_round_{attempt}",
                        "duration_s": round(time.time() - attempt_started, 3),
                        "errors": errors,
                    }
                )
            if not errors:
                output_html.with_suffix(".json").write_text(
                    json.dumps(
                        {
                            "kind": "direct_html_baseline_artifact",
                            "case_id": case.id,
                            "sample_index": sample_index,
                            "condition": benchmark_condition(args),
                            "html": str(output_html),
                            "html_chars": len(html),
                            "direct_html_repair_rounds": repair_rounds,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return {
                    "case_id": case.id,
                    "title": case.title,
                    "family": case.family,
                    **metadata,
                    "sample_index": sample_index,
                    "input_data": sample.input_data,
                    "expected": sample.expected,
                    "model": _model_name(),
                    "condition": benchmark_condition(args),
                    "baseline": baseline,
                    "expected_visible_to_model": expected_visible,
                    "direct_html_repair_enabled": max_rounds > 0,
                    "direct_html_browser_repair_enabled": browser_repair_enabled,
                    "direct_html_repair_attempted": repair_rounds > 0,
                    "direct_html_repair_rounds": repair_rounds,
                    "ok": True,
                    "html": str(output_html),
                    "json": str(output_html.with_suffix(".json")),
                    "duration_s": round(time.time() - started, 3),
                    "failure_type": "",
                    "phase_timings": phase_timings,
                    "model_calls": consume_model_calls(),
                }
        raise ValueError("; ".join(last_errors or ["direct_html generation failed"]))
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        failure_type = _failure_type_from_errors(last_errors) if last_errors else (
            "html_error" if "html_error" in message or "missing #" in message else classify_failure(message)
        )
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            **metadata,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "condition": benchmark_condition(args),
            "baseline": str(getattr(args, "baseline", "direct_html_baseline")),
            "expected_visible_to_model": bool(getattr(args, "expected_visible_to_model", True)),
            "direct_html_repair_enabled": max_rounds > 0,
            "direct_html_browser_repair_enabled": browser_repair_enabled,
            "direct_html_repair_attempted": repair_rounds > 0,
            "direct_html_repair_rounds": repair_rounds,
            "ok": False,
            "error": message,
            "failure_type": failure_type,
            "failed_html": str(failed_html) if failed_html else "",
            "failed_json": str(failed_json) if failed_json else "",
            "raw_response": str(raw_response) if raw_response else "",
            "raw_response_json": str(raw_response_json) if raw_response_json else "",
            "repair_failure_types": [failure_type] if repair_rounds > 0 else [],
            "phase_timings": phase_timings,
            "duration_s": round(time.time() - started, 3),
            "model_calls": consume_model_calls(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 direct HTML baseline，不进入 AlgoLab 主发布链路")
    add_common_args(parser, condition="direct_html_baseline")
    parser.add_argument(
        "--hide-expected",
        action="store_false",
        dest="expected_visible_to_model",
        default=True,
        help="不把 expected output 暴露给 direct HTML baseline；用于公平 answer correctness 条件。",
    )
    parser.add_argument(
        "--llm-max-tokens",
        type=int,
        default=0,
        help="仅 direct HTML 调用期间覆盖 ALGOLAB_LLM_MAX_TOKENS；0 表示沿用环境/默认值。",
    )
    args = parser.parse_args()
    if not args.expected_visible_to_model:
        args.condition = "direct_html_no_expected"
    args.baseline = "direct_html_baseline" if args.expected_visible_to_model else "direct_html_no_expected"
    args.direct_html_baseline = True
    args.direct_html_repair_enabled = args.max_rounds > 0
    args.direct_html_browser_repair_enabled = bool(args.browser_smoke and args.max_rounds > 0)
    args.direct_html_llm_max_tokens = args.llm_max_tokens
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = False
    args.trace_only_renderer_enabled = False
    return run_benchmark(args, run_one_direct_html)


if __name__ == "__main__":
    raise SystemExit(main())
