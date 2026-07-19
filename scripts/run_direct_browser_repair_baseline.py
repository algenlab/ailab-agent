"""Run the equal-call Direct HTML baseline with generic browser feedback."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.cases import BenchmarkCase, BenchmarkInput, benchmark_cases
from llm_client import _model_name, chat_text_with_metadata, llm_config
from scripts.build_browser_repair_feedback import collect_browser_feedback
from scripts.run_direct_html_baseline import _system_prompt, _user_prompt, extract_html


DEFAULT_SOURCE_REPORT = ROOT / "output/experiments/algotutorgen_full_200_20260706/direct_html_expected_visible/llm_benchmark_report.json"
DEFAULT_OUTPUT_DIR = ROOT / "output/experiments/algotutorgen_plan_completion_20260713/direct_browser_repair_5"
FEEDBACK_FIELDS = {
    "page_load_ok",
    "console_errors",
    "page_errors",
    "external_requests",
    "external_resource_urls",
    "dom_summary",
    "interactive_elements",
    "input_elements",
    "button_labels",
    "interaction_smoke",
    "screenshot",
    "screenshot_bytes",
    "load_error",
    "html_chars",
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


_CSS_URL_RE = re.compile(r"(?is)(?:url\(\s*|@import\s+)(['\"]?)(?P<url>(?:https?:)?//[^\s'\"\)]+)\1")


def _network_url(value: str) -> str:
    candidate = value.strip()
    if candidate.startswith("//"):
        return "https:" + candidate
    return candidate if candidate.lower().startswith(("http://", "https://")) else ""


class _ExternalResourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: set[str] = set()
        self._in_style = False

    def _add(self, value: str) -> None:
        url = _network_url(value)
        if url:
            self.urls.add(url)

    def _add_css(self, value: str) -> None:
        for match in _CSS_URL_RE.finditer(value):
            self._add(match.group("url"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self._in_style = tag == "style"
        for raw_name, raw_value in attrs:
            if not raw_value:
                continue
            name = raw_name.lower()
            if name == "style":
                self._add_css(raw_value)
            elif name == "srcset":
                for candidate in raw_value.split(","):
                    self._add(candidate.strip().split()[0])
            elif name in {"src", "poster", "data"} or (name == "href" and tag in {"link", "use", "image"}):
                self._add(raw_value)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self._in_style = False

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._add_css(data)


def external_resource_urls(html: str) -> list[str]:
    """Return network-backed resources, excluding plain text and XML namespaces."""
    parser = _ExternalResourceParser()
    parser.feed(html or "")
    parser.close()
    return sorted(parser.urls)


def _resource_urls_for_row(row: dict[str, Any]) -> list[str]:
    html_path = _repo_path(str(row.get("html") or ""))
    if html_path.is_file():
        return external_resource_urls(html_path.read_text(encoding="utf-8"))
    return list(row.get("external_resource_urls") or [])


def _observed_external_requests(row: dict[str, Any]) -> list[str]:
    feedback_value = str(row.get("feedback") or "")
    feedback_path = _repo_path(feedback_value) if feedback_value else Path()
    if feedback_value and feedback_path.is_file():
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        return sorted(set(feedback.get("external_requests") or []))
    return sorted(set(row.get("observed_external_requests") or []))


def refresh_external_resource_annotations(report: dict[str, Any]) -> dict[str, Any]:
    """Recompute cached resource URLs from the referenced HTML artifacts."""
    refreshed = copy.deepcopy(report)
    has_attempts = False
    for row in refreshed.get("results") or []:
        attempts = row.get("attempts") or []
        if attempts:
            has_attempts = True
            for attempt in attempts:
                attempt["external_resource_urls"] = _resource_urls_for_row(attempt)
                attempt["observed_external_requests"] = _observed_external_requests(attempt)
            row["external_resource_urls"] = list(attempts[-1]["external_resource_urls"])
            row["observed_external_requests"] = list(attempts[-1]["observed_external_requests"])
        else:
            row["external_resource_urls"] = _resource_urls_for_row(row)
            row["observed_external_requests"] = _observed_external_requests(row)
    count = sum(
        1
        for row in refreshed.get("results") or []
        if row.get("external_resource_urls") or row.get("observed_external_requests")
    )
    if has_attempts:
        refreshed["external_resource_cases_final"] = count
    else:
        refreshed["external_resource_cases"] = count
    return refreshed


def _safe_feedback(feedback: dict[str, Any]) -> dict[str, Any]:
    safe = {key: copy.deepcopy(value) for key, value in feedback.items() if key in FEEDBACK_FIELDS}
    serialized = json.dumps(safe, ensure_ascii=False)
    for token in ("#answer", "correct_feedback_ok", "wrong_feedback_ok", "machine_ok"):
        serialized = serialized.replace(token, "[redacted]")
    return json.loads(serialized)


def build_browser_repair_prompt(
    *,
    title: str,
    problem: str,
    family: str,
    strategy: str,
    input_data: Any,
    expected: Any,
    previous_html: str,
    feedback: dict[str, Any],
    round_index: int,
) -> str:
    safe_feedback = _safe_feedback(feedback)
    previous_excerpt = previous_html[-18000:]
    return "\n".join(
        [
            f"这是 Direct HTML 的第 {round_index} 次浏览器反馈修复。请只输出修复后的完整单文件 HTML，不要 markdown。",
            f"题目：{title}",
            f"描述：{problem}",
            f"算法族：{family}",
            f"策略提示：{strategy}",
            f"输入 JSON：{json.dumps(input_data, ensure_ascii=False)}",
            f"期望输出 JSON：{json.dumps(expected, ensure_ascii=False)}",
            "通用浏览器观察：",
            json.dumps(safe_feedback, ensure_ascii=False, indent=2),
            "修复要求：",
            "1. 保持完整的算法教学体验：可见步骤、状态、代码、解释、前后导航、时间线、预测问题、即时反馈、提示、显示答案与学习记录。",
            "2. 页面首屏应明确展示最终返回值，并保证所有教学内容与给定输入和期望输出一致。",
            "3. 修复控制台错误和没有产生可见变化的交互；所有交互必须在离线打开时工作。",
            "4. 不引用网络字体、脚本、样式、图片或其他外部资源；所有 CSS 和 JavaScript 内联。",
            "5. 输出应尽量紧凑，保留至少两个有意义的算法步骤，并完整闭合 HTML。",
            "上一版 HTML 末尾摘录：",
            previous_excerpt,
        ]
    )


def build_budget_report(final_report: dict[str, Any], call_budget: int) -> dict[str, Any]:
    if call_budget < 1:
        raise ValueError("call_budget must be >= 1")
    rows: list[dict[str, Any]] = []
    for source in final_report.get("results") or []:
        attempts = sorted(
            (item for item in source.get("attempts") or [] if int(item.get("call_index") or 0) <= call_budget),
            key=lambda item: int(item.get("call_index") or 0),
        )
        selected = attempts[-1] if attempts else {}
        selected_html = _repo_path(str(selected.get("html") or ""))
        selected_urls = copy.deepcopy(selected.get("external_resource_urls") or [])
        if selected_html.is_file():
            selected_urls = external_resource_urls(selected_html.read_text(encoding="utf-8"))
        observed_requests = _observed_external_requests(selected)
        row = {key: copy.deepcopy(value) for key, value in source.items() if key != "attempts"}
        row.update(
            {
                "condition": f"direct_browser_repair_{call_budget}",
                "baseline": "direct_browser_repair",
                "call_budget": call_budget,
                "selected_call_index": int(selected.get("call_index") or 0),
                "html": selected.get("html", ""),
                "json": selected.get("json", ""),
                "ok": bool(selected.get("html")),
                "model_calls": [
                    copy.deepcopy(attempt.get("model_call"))
                    for attempt in attempts
                    if isinstance(attempt.get("model_call"), dict)
                ],
                "external_resource_urls": selected_urls,
                "observed_external_requests": observed_requests,
            }
        )
        rows.append(row)
    report = {key: copy.deepcopy(value) for key, value in final_report.items() if key != "results"}
    report.update(
        {
            "kind": "llm_benchmark_report",
            "condition": f"direct_browser_repair_{call_budget}",
            "call_budget": call_budget,
            "total": len(rows),
            "passed": sum(1 for row in rows if row.get("ok")),
            "failed": sum(1 for row in rows if not row.get("ok")),
            "results": rows,
        }
    )
    return report


def _source_initial_html(row: dict[str, Any]) -> Path:
    final_html = _repo_path(str(row.get("html") or ""))
    calls = row.get("model_calls") or []
    if len(calls) <= 1:
        return final_html
    failed = final_html.with_name(final_html.stem + ".failed.html")
    return failed if failed.exists() else Path()


def _ensure_feedback(attempt: dict[str, Any], *, timeout_ms: int) -> dict[str, Any]:
    metadata_path = _repo_path(str(attempt["json"]))
    html_path = _repo_path(str(attempt["html"]))
    feedback_path = metadata_path.with_name(metadata_path.stem + ".feedback.json")
    screenshot_path = metadata_path.with_name(metadata_path.stem + ".png")
    actual_urls = (
        external_resource_urls(html_path.read_text(encoding="utf-8"))
        if html_path.is_file()
        else list(attempt.get("external_resource_urls") or [])
    )
    if feedback_path.exists():
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
    else:
        feedback = collect_browser_feedback(
            html_path,
            screenshot_path=screenshot_path,
            timeout_ms=timeout_ms,
        )
    feedback["external_resource_urls"] = actual_urls
    attempt["external_resource_urls"] = actual_urls
    _write_json(feedback_path, feedback)
    attempt["feedback"] = _display_path(feedback_path)
    attempt["screenshot"] = _display_path(screenshot_path)
    _write_json(metadata_path, attempt)
    return feedback


def _initial_attempt(
    *,
    row: dict[str, Any],
    case: BenchmarkCase,
    output_dir: Path,
    model: str,
) -> dict[str, Any]:
    case_dir = output_dir / "cases" / case.id
    html_path = case_dir / "attempt_01.html"
    metadata_path = case_dir / "attempt_01.json"
    prompt_path = case_dir / "attempt_01.prompt.txt"
    if metadata_path.exists() and html_path.exists():
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    sample = BenchmarkInput(input_data=row.get("input_data"), expected=row.get("expected"))
    prompt = _user_prompt(case, sample, expected_visible_to_model=True)
    source_path = _source_initial_html(row)
    model_call = (row.get("model_calls") or [{}])[0]
    source_kind = "frozen_original_first_call"
    raw_response_path = ""
    if source_path and source_path.exists():
        html = source_path.read_text(encoding="utf-8")
    else:
        response = chat_text_with_metadata(_system_prompt(), prompt, model=model, kind="direct_browser_repair_initial")
        raw = str(response.get("content") or "")
        html = extract_html(raw)
        model_call = response.get("model_call") or {}
        source_kind = "regenerated_first_call"
        raw_path = case_dir / "attempt_01.raw.txt"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw, encoding="utf-8")
        raw_response_path = _display_path(raw_path)
    if not html:
        html = "<!doctype html><html><body><p>Generation returned no HTML.</p></body></html>"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    prompt_path.write_text(prompt, encoding="utf-8")
    attempt = {
        "call_index": 1,
        "round_index": 0,
        "kind": "direct_html",
        "source_kind": source_kind,
        "source_html": _display_path(source_path) if source_path and source_path.exists() else "",
        "prompt": _display_path(prompt_path),
        "prompt_sha256": _sha256_text(prompt),
        "raw_response": raw_response_path,
        "html": _display_path(html_path),
        "html_sha256": _sha256_text(html),
        "html_chars": len(html),
        "json": _display_path(metadata_path),
        "model_call": copy.deepcopy(model_call),
        "external_resource_urls": external_resource_urls(html),
    }
    _write_json(metadata_path, attempt)
    return attempt


def _repair_attempt(
    *,
    row: dict[str, Any],
    case: BenchmarkCase,
    previous: dict[str, Any],
    feedback: dict[str, Any],
    call_index: int,
    output_dir: Path,
    model: str,
) -> dict[str, Any]:
    case_dir = output_dir / "cases" / case.id
    html_path = case_dir / f"attempt_{call_index:02d}.html"
    metadata_path = case_dir / f"attempt_{call_index:02d}.json"
    prompt_path = case_dir / f"attempt_{call_index:02d}.prompt.txt"
    raw_path = case_dir / f"attempt_{call_index:02d}.raw.txt"
    if metadata_path.exists() and html_path.exists():
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    previous_html = _repo_path(str(previous["html"])).read_text(encoding="utf-8")
    prompt = build_browser_repair_prompt(
        title=case.title,
        problem=case.problem,
        family=case.family,
        strategy=case.strategy,
        input_data=row.get("input_data"),
        expected=row.get("expected"),
        previous_html=previous_html,
        feedback=feedback,
        round_index=call_index - 1,
    )
    started = time.time()
    response = chat_text_with_metadata(_system_prompt(), prompt, model=model, kind="direct_browser_repair")
    raw = str(response.get("content") or "")
    html = extract_html(raw)
    if not html:
        html = previous_html
    case_dir.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    raw_path.write_text(raw, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    attempt = {
        "call_index": call_index,
        "round_index": call_index - 1,
        "kind": "direct_browser_repair",
        "prompt": _display_path(prompt_path),
        "prompt_sha256": _sha256_text(prompt),
        "raw_response": _display_path(raw_path),
        "html": _display_path(html_path),
        "html_sha256": _sha256_text(html),
        "html_chars": len(html),
        "json": _display_path(metadata_path),
        "model_call": copy.deepcopy(response.get("model_call") or {}),
        "duration_s": round(time.time() - started, 3),
        "external_resource_urls": external_resource_urls(html),
        "fallback_to_previous_html": not bool(extract_html(raw)),
    }
    _write_json(metadata_path, attempt)
    return attempt


def _case_result(row: dict[str, Any], attempts: list[dict[str, Any]], *, token_target: int) -> dict[str, Any]:
    total_tokens = sum(
        int((attempt.get("model_call") or {}).get("total_tokens") or 0)
        for attempt in attempts
    )
    return {
        **{key: copy.deepcopy(value) for key, value in row.items() if key not in {"html", "json", "model_calls"}},
        "condition": "direct_browser_repair_5",
        "baseline": "direct_browser_repair",
        "ok": bool(attempts and attempts[-1].get("html")),
        "html": attempts[-1].get("html", "") if attempts else "",
        "json": attempts[-1].get("json", "") if attempts else "",
        "attempts": attempts,
        "calls_completed": len(attempts),
        "total_tokens": total_tokens,
        "token_budget_target": token_target,
        "over_token_target": total_tokens > token_target if total_tokens else False,
    }


def run_case(
    row: dict[str, Any],
    *,
    case: BenchmarkCase,
    output_dir: Path,
    max_calls: int,
    model: str,
    browser_timeout_ms: int,
    token_target: int,
) -> dict[str, Any]:
    case_result_path = output_dir / "cases" / case.id / "case_result.json"
    if case_result_path.exists():
        existing = json.loads(case_result_path.read_text(encoding="utf-8"))
        if int(existing.get("calls_completed") or 0) >= max_calls:
            return existing
    attempts = [_initial_attempt(row=row, case=case, output_dir=output_dir, model=model)]
    while len(attempts) < max_calls:
        previous = attempts[-1]
        feedback = _ensure_feedback(previous, timeout_ms=browser_timeout_ms)
        attempts.append(
            _repair_attempt(
                row=row,
                case=case,
                previous=previous,
                feedback=feedback,
                call_index=len(attempts) + 1,
                output_dir=output_dir,
                model=model,
            )
        )
    _ensure_feedback(attempts[-1], timeout_ms=browser_timeout_ms)
    result = _case_result(row, attempts, token_target=token_target)
    _write_json(case_result_path, result)
    return result


def _write_reports(
    *,
    output_dir: Path,
    source_report: Path,
    results: list[dict[str, Any]],
    budgets: list[int],
    max_calls: int,
    model: str,
    token_target: int,
    repair_max_tokens: int,
    started_at: str,
) -> dict[str, Any]:
    ordered = sorted(results, key=lambda row: str(row.get("case_id") or ""))
    final_report = refresh_external_resource_annotations({
        "kind": "direct_browser_repair_report",
        "started_at": started_at,
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "source_report": _display_path(source_report),
        "config": {
            "model": model,
            "max_calls": max_calls,
            "budgets": budgets,
            "token_budget_target_per_case": token_target,
            "repair_max_tokens": repair_max_tokens,
            "external_requests_blocked": True,
            "feedback_scope": "generic_browser_only",
            "llm": llm_config(),
        },
        "total": len(ordered),
        "complete": sum(1 for row in ordered if int(row.get("calls_completed") or 0) >= max_calls),
        "external_resource_cases_final": sum(
            1 for row in ordered if (row.get("attempts") or [{}])[-1].get("external_resource_urls")
        ),
        "results": ordered,
    })
    _write_json(output_dir / "direct_browser_repair_report.json", final_report)
    for budget in budgets:
        budget_report = build_budget_report(final_report, budget)
        _write_json(output_dir / "budget_reports" / f"calls_{budget}" / "llm_benchmark_report.json", budget_report)
    return final_report


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 Direct-BrowserRepair-5 等预算基线")
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-calls", type=int, default=5)
    parser.add_argument("--budgets", default="1,2,3,5")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--model", default="")
    parser.add_argument("--browser-timeout-ms", type=int, default=15000)
    parser.add_argument("--token-budget-target", type=int, default=80000)
    parser.add_argument("--repair-max-tokens", type=int, default=12000)
    args = parser.parse_args()
    if args.max_calls < 1 or args.max_calls > 5:
        raise SystemExit("--max-calls 必须在 1..5")
    budgets = sorted({int(item) for item in args.budgets.split(",") if item.strip()})
    if not budgets or any(item < 1 or item > args.max_calls for item in budgets):
        raise SystemExit("--budgets 必须位于 1..max-calls")
    source_report = _repo_path(args.source_report)
    output_dir = _repo_path(args.output_dir)
    source = json.loads(source_report.read_text(encoding="utf-8"))
    wanted = set(args.case)
    rows = [row for row in source.get("results") or [] if not wanted or row.get("case_id") in wanted]
    case_map = {case.id: case for case in benchmark_cases()}
    missing = sorted({str(row.get("case_id")) for row in rows} - set(case_map))
    if missing:
        raise SystemExit("源报告包含未知 case：" + ", ".join(missing))
    model = args.model or str((source.get("config") or {}).get("model") or _model_name())
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().isoformat(timespec="seconds")
    previous_max_tokens = os.environ.get("ALGOLAB_LLM_MAX_TOKENS")
    os.environ["ALGOLAB_LLM_MAX_TOKENS"] = str(args.repair_max_tokens)
    results: list[dict[str, Any]] = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
            futures = {
                executor.submit(
                    run_case,
                    row,
                    case=case_map[str(row["case_id"])],
                    output_dir=output_dir,
                    max_calls=args.max_calls,
                    model=model,
                    browser_timeout_ms=args.browser_timeout_ms,
                    token_target=args.token_budget_target,
                ): str(row["case_id"])
                for row in rows
            }
            for future in concurrent.futures.as_completed(futures):
                case_id = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {
                        "case_id": case_id,
                        "ok": False,
                        "calls_completed": 0,
                        "error": f"{type(exc).__name__}: {exc}",
                        "attempts": [],
                    }
                results.append(result)
                _write_reports(
                    output_dir=output_dir,
                    source_report=source_report,
                    results=results,
                    budgets=budgets,
                    max_calls=args.max_calls,
                    model=model,
                    token_target=args.token_budget_target,
                    repair_max_tokens=args.repair_max_tokens,
                    started_at=started_at,
                )
                print(f"DONE {case_id} calls={result.get('calls_completed', 0)}", flush=True)
    finally:
        if previous_max_tokens is None:
            os.environ.pop("ALGOLAB_LLM_MAX_TOKENS", None)
        else:
            os.environ["ALGOLAB_LLM_MAX_TOKENS"] = previous_max_tokens
    final_report = _write_reports(
        output_dir=output_dir,
        source_report=source_report,
        results=results,
        budgets=budgets,
        max_calls=args.max_calls,
        model=model,
        token_target=args.token_budget_target,
        repair_max_tokens=args.repair_max_tokens,
        started_at=started_at,
    )
    print(json.dumps({"report": _display_path(output_dir / "direct_browser_repair_report.json"), "total": final_report["total"], "complete": final_report["complete"]}, ensure_ascii=False))
    return 0 if final_report["complete"] == final_report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
